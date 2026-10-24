#!/usr/bin/env python3
"""Rebuilds the generated parts of README.md (and assets/stats.svg).

How it works
------------
* Every top-level folder (except scripts/, assets/ and hidden ones) is one machine.
* Difficulty / OS / Date are read from the header table at the top of the
  folder's README.md:

      | Field      | Details                |
      |------------|------------------------|
      | Difficulty | Easy                   |
      | OS         | Linux                  |
      | Date       | June 29, 2026          |

* Anything missing falls back to scripts/overrides.csv and, for the date only,
  to the date of the first git commit that touched the folder.
* Only the blocks between <!-- X:START --> and <!-- X:END --> in README.md are
  rewritten. Everything else in README.md is yours to edit.

Usage
-----
    python scripts/update_readme.py             # rebuild README + stats card
    python scripts/update_readme.py --init-csv  # add every folder to overrides.csv
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SVG_PATH = ROOT / "assets" / "stats.svg"
OVERRIDES = Path(__file__).resolve().parent / "overrides.csv"
SKIP_DIRS = {"scripts", "assets", "node_modules", "venv"}

# name, colour (hex, no #), emoji
LEVELS = [
    ("Easy", "9fef00", "🟢"),
    ("Medium", "ffaf00", "🟠"),
    ("Hard", "ff3e3e", "🔴"),
    ("Insane", "a335ee", "🟣"),
]
OS_ICON = {"Linux": "🐧", "Windows": "🪟", "BSD": "😈", "Other": "💻"}
OS_COLOR = {"Windows": "58a6ff", "Linux": "f0883e", "BSD": "d2a8ff", "Other": "8b949e"}
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# English + Azerbaijani month prefixes (your write-ups may use either)
MONTHS = {
    "jan": 1, "yan": 1, "feb": 2, "fev": 2, "mar": 3, "apr": 4, "may": 5,
    "jun": 6, "jul": 7, "aug": 8, "avq": 8, "sep": 9, "sen": 9,
    "oct": 10, "okt": 10, "nov": 11, "noy": 11, "dec": 12, "dek": 12,
}


@dataclass
class Machine:
    name: str
    link: str
    difficulty: str | None
    os: str | None
    solved: date | None


# --------------------------------------------------------------------------- parsing
def field(head: str, key: str) -> str | None:
    """Value of `key` from a markdown table row or a 'Key: value' / '**Key:** value' line."""
    m = re.search(rf"^\|\s*\**{key}\**\s*\|\s*(.+?)\s*\|?\s*$", head, re.I | re.M)
    if not m:
        m = re.search(rf"^[-*>\s]*\**{key}[\s*]*:[\s*]*(.+?)\s*$", head, re.I | re.M)
    return m.group(1).strip().strip("*").strip() if m else None


def norm_difficulty(text: str | None) -> str | None:
    if not text:
        return None
    hits = [n for n, *_ in LEVELS if re.search(rf"\b{n}\b", text, re.I)]
    return hits[0] if len(hits) == 1 else None  # "Easy / Medium / Hard" = unfilled template


def norm_os(text: str | None) -> str | None:
    if not text:
        return None
    t = text.lower()
    win = "windows" in t
    lin = bool(re.search(r"linux|ubuntu|debian|centos|fedora|kali", t))
    bsd = "bsd" in t
    n = win + lin + bsd
    if n == 0:
        return "Other"
    if n > 1:
        return None  # "Linux / Windows" = unfilled template
    return "Windows" if win else "Linux" if lin else "BSD"


def _month(word: str) -> int | None:
    w = "".join(c for c in unicodedata.normalize("NFKD", word.lower()) if not unicodedata.combining(c))
    if w.startswith("iyun"):
        return 6
    if w.startswith("iyul"):
        return 7
    return MONTHS.get(w[:3])


def _date(y: int, m: int | None, d: int) -> date | None:
    try:
        return date(y, m, d) if m else None
    except ValueError:
        return None


def parse_date(text: str | None) -> date | None:
    if not text:
        return None
    s = text.strip()
    if m := re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s):
        return _date(int(m[1]), int(m[2]), int(m[3]))
    if m := re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", s):
        return _date(int(m[3]), int(m[2]), int(m[1]))
    if m := re.search(r"([^\W\d_]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", s):  # June 29, 2026
        return _date(int(m[3]), _month(m[1]), int(m[2]))
    if m := re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([^\W\d_]+)\.?,?\s+(\d{4})", s):  # 29 June 2026
        return _date(int(m[3]), _month(m[2]), int(m[1]))
    return None


def git_first_date(folder: Path) -> date | None:
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--format=%as", "--", folder.name],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
        return date.fromisoformat(out[0]) if out else None
    except Exception:
        return None


def find_notes(folder: Path) -> Path | None:
    for n in ("README.md", "readme.md", "Readme.md"):
        if (folder / n).is_file():
            return folder / n
    mds = sorted(folder.glob("*.md"))
    return mds[0] if mds else None


def load_overrides() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if OVERRIDES.is_file():
        with OVERRIDES.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                name = (r.get("name") or "").strip()
                if name:
                    rows[name.lower()] = r
    return rows


def collect() -> list[Machine]:
    overrides = load_overrides()
    machines: list[Machine] = []
    for folder in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir() or folder.name.startswith(".") or folder.name in SKIP_DIRS:
            continue
        notes = find_notes(folder)
        text = notes.read_text(encoding="utf-8", errors="replace") if notes else ""
        head = "\n".join(text.splitlines()[:60])  # metadata lives at the top
        ov = overrides.get(folder.name.lower(), {})
        machines.append(Machine(
            name=folder.name,
            link=quote((notes or folder).relative_to(ROOT).as_posix()),
            difficulty=norm_difficulty(field(head, "Difficulty")) or norm_difficulty(ov.get("difficulty")),
            os=norm_os(field(head, "OS")) or norm_os(ov.get("os")),
            solved=parse_date(field(head, "Date")) or parse_date(ov.get("date")) or git_first_date(folder),
        ))
    return machines


# --------------------------------------------------------------------------- rendering helpers
def bar(n: int, total: int, width: int = 20) -> str:
    if not total:
        return "▱" * width
    filled = round(width * n / total)
    if n and not filled:
        filled = 1
    return "▰" * filled + "▱" * (width - filled)


def pct(n: int, total: int) -> str:
    return f"{round(100 * n / total)}%" if total else "0%"


def newest_first(ms: list[Machine]) -> list[Machine]:
    return sorted(ms, key=lambda m: (m.solved is None, -(m.solved.toordinal() if m.solved else 0), m.name.lower()))


def fmt_date(d: date | None) -> str:
    return f"{MONTH_ABBR[d.month - 1]} {d.day}, {d.year}" if d else "—"


def os_cell(m: Machine) -> str:
    return f"{OS_ICON[m.os]} {m.os}" if m.os else "—"


def esc(s: str) -> str:  # shields.io path escaping
    return quote(str(s).replace("-", "--").replace("_", "__").replace(" ", "_"), safe="_-")


def badge(label: str, msg: str, color: str, logo: str = "") -> str:
    url = f"https://img.shields.io/badge/{esc(label)}-{esc(msg)}-{color}?style=for-the-badge&labelColor=161b22"
    if logo:
        url += f"&logo={logo}&logoColor=white"
    return f'<img src="{url}" alt="{label}: {msg}">'


# --------------------------------------------------------------------------- README blocks
def block_badges(ms: list[Machine]) -> str:
    diff = {n: sum(m.difficulty == n for m in ms) for n, *_ in LEVELS}
    osc = {o: sum(m.os == o for m in ms) for o in OS_ICON}
    row1 = [badge("Machines", str(len(ms)), "58a6ff", "hackthebox")]
    row1 += [badge(n, str(diff[n]), c) for n, c, _ in LEVELS]
    row2 = [badge(o, str(c), OS_COLOR[o]) for o, c in osc.items() if c]
    dated = newest_first([m for m in ms if m.solved])
    if dated:
        row2.append(badge("Latest", dated[0].name, "238636"))
    return '<p align="center">\n' + "\n".join(row1) + "<br>\n" + "\n".join(row2) + "\n</p>"


def block_stats(ms: list[Machine]) -> str:
    total = len(ms)
    out = ['<p align="center"><img src="assets/stats.svg" alt="HTB progress card" width="820"></p>\n']
    out += ["| Difficulty | Machines | Share |", "|:--|:-:|:--|"]
    for n, _, e in LEVELS:
        c = sum(m.difficulty == n for m in ms)
        out.append(f"| {e} **{n}** | {c} | `{bar(c, total)}` {pct(c, total)} |")
    unrated = sum(m.difficulty is None for m in ms)
    if unrated:
        out.append(f"| ⚪ Unrated | {unrated} | `{bar(unrated, total)}` {pct(unrated, total)} |")
    out.append(f"| **Total** | **{total}** | |")

    months: dict[tuple[int, int], int] = {}
    for m in ms:
        if m.solved:
            months[(m.solved.year, m.solved.month)] = months.get((m.solved.year, m.solved.month), 0) + 1
    if months:
        y, mo = max(months)
        seq = []
        for _ in range(6):
            seq.append((y, mo))
            mo -= 1
            if mo == 0:
                y, mo = y - 1, 12
        seq.reverse()
        peak = max(months.get(k, 0) for k in seq) or 1
        out += ["", "**📅 Activity — last 6 months**\n", "| Month | Solved | |", "|:--|:-:|:--|"]
        for k in seq:
            c = months.get(k, 0)
            out.append(f"| {MONTH_ABBR[k[1] - 1]} {k[0]} | {c} | `{bar(c, peak, 16)}` |")
    return "\n".join(out)


def block_recent(ms: list[Machine]) -> str:
    recent = [m for m in newest_first(ms) if m.solved][:5]
    if not recent:
        return "_Nothing dated yet — add a `Date` row to your write-up header._"
    rows = ["| Machine | Difficulty | OS | Solved |", "|:--|:-:|:-:|:-:|"]
    for m in recent:
        lvl = next((f"{e} {n}" for n, _, e in LEVELS if n == m.difficulty), "⚪ —")
        rows.append(f"| **[{m.name}]({m.link})** | {lvl} | {os_cell(m)} | {fmt_date(m.solved)} |")
    return "\n".join(rows)


def block_machines(ms: list[Machine]) -> str:
    groups = [(n, e, [m for m in ms if m.difficulty == n]) for n, _, e in LEVELS]
    groups.append(("Unrated", "⚪", [m for m in ms if m.difficulty is None]))
    parts = []
    for n, e, items in groups:
        if not items:
            continue
        rows = ["| Machine | OS | Solved |", "|:--|:-:|:-:|"]
        for m in newest_first(items):
            rows.append(f"| [{m.name}]({m.link}) | {os_cell(m)} | {fmt_date(m.solved)} |")
        parts.append(
            f"<details>\n<summary><b>{e} {n}</b> — {len(items)} machine{'s' if len(items) != 1 else ''}</summary>\n\n"
            + "\n".join(rows) + "\n\n</details>"
        )
    return "\n\n".join(parts) if parts else "_No write-ups yet._"


def replace_block(text: str, tag: str, content: str) -> str:
    pat = re.compile(rf"(<!-- {tag}:START -->)(.*?)(<!-- {tag}:END -->)", re.S)
    if not pat.search(text):
        sys.exit(f"README.md is missing the <!-- {tag}:START --> / <!-- {tag}:END --> markers")
    return pat.sub(lambda m: f"{m[1]}\n{content}\n{m[3]}", text)


# --------------------------------------------------------------------------- stats card (SVG)
def build_svg(ms: list[Machine]) -> str:
    total = len(ms)
    counts = {n: sum(m.difficulty == n for m in ms) for n, *_ in LEVELS}
    unrated = sum(m.difficulty is None for m in ms)
    osc = {o: sum(m.os == o for m in ms) for o in OS_ICON if any(m.os == o for m in ms)}
    dated = newest_first([m for m in ms if m.solved])
    sub = f"Latest: {dated[0].name} · {fmt_date(dated[0].solved)}" if dated else "Hack The Box write-ups"

    W, H = 820, 318
    track_x, track_w = 380, 340
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif" role="img" aria-label="HTB progress">',
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="#0d1117" stroke="#30363d" stroke-width="2"/>',
        '<text x="36" y="52" font-size="24" font-weight="700" fill="#e6edf3">HTB Progress</text>',
        f'<text x="36" y="76" font-size="13" fill="#8b949e">{sub}</text>',
        f'<text x="34" y="176" font-size="84" font-weight="800" fill="#9fef00">{total}</text>',
        '<text x="38" y="204" font-size="15" fill="#8b949e">machines pwned</text>',
    ]
    if unrated:
        s.append(f'<text x="38" y="226" font-size="13" fill="#6e7681">{unrated} not rated yet</text>')
    for i, (n, color, _) in enumerate(LEVELS):
        y = 104 + i * 38
        c = counts[n]
        w = 0 if not total or not c else max(14, round(track_w * c / total))
        s.append(f'<text x="300" y="{y + 12}" font-size="15" font-weight="600" fill="#e6edf3">{n}</text>')
        s.append(f'<rect x="{track_x}" y="{y}" width="{track_w}" height="14" rx="7" fill="#21262d"/>')
        if w:
            s.append(f'<rect x="{track_x}" y="{y}" width="{w}" height="14" rx="7" fill="#{color}"/>')
        s.append(f'<text x="{track_x + track_w + 20}" y="{y + 12}" font-size="15" font-weight="700" fill="#{color}">{c}</text>')

    s.append('<text x="36" y="262" font-size="13" font-weight="600" fill="#8b949e">OPERATING SYSTEMS</text>')
    s.append(f'<rect x="36" y="272" width="{W - 72}" height="12" rx="6" fill="#21262d"/>')
    os_total = sum(osc.values())
    x = 36.0
    full = W - 72
    for o, c in osc.items():
        seg = full * c / os_total
        s.append(f'<rect x="{x:.1f}" y="272" width="{max(seg, 6):.1f}" height="12" rx="6" fill="#{OS_COLOR[o]}"/>')
        x += seg
    lx = 36
    for o, c in osc.items():
        s.append(f'<circle cx="{lx + 5}" cy="300" r="5" fill="#{OS_COLOR[o]}"/>')
        s.append(f'<text x="{lx + 16}" y="305" font-size="13" fill="#e6edf3">{o} · {c}</text>')
        lx += 150
    s.append("</svg>")
    return "\n".join(s) + "\n"


# --------------------------------------------------------------------------- commands
def init_csv() -> None:
    existing = load_overrides()
    ms = collect()
    new = [m for m in ms if m.name.lower() not in existing]
    write_header = not OVERRIDES.is_file()
    with OVERRIDES.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["name", "difficulty", "os", "date"])
        for m in new:
            w.writerow([m.name, m.difficulty or "", m.os or "", ""])
    print(f"overrides.csv: added {len(new)} folder(s)")


def write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    if "--init-csv" in sys.argv:
        init_csv()
        return
    ms = collect()
    text = README.read_text(encoding="utf-8")
    for tag, body in (
        ("BADGES", block_badges(ms)),
        ("STATS", block_stats(ms)),
        ("RECENT", block_recent(ms)),
        ("MACHINES", block_machines(ms)),
    ):
        text = replace_block(text, tag, body)
    changed = write_if_changed(README, text)
    changed |= write_if_changed(SVG_PATH, build_svg(ms))
    print(f"{len(ms)} machines · README {'updated' if changed else 'already up to date'}")
    for m in ms:
        if not m.difficulty:
            print(f"::warning::{m.name} has no Difficulty (add it to the write-up header or scripts/overrides.csv)")


if __name__ == "__main__":
    main()
