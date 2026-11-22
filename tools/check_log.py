"""Summarize the latest 7DTD client log for this mod.

Prints the game version, the [MODS] load lines, and every ERR/EXC line plus any
WRN line that mentions XML, XPath, Localization or the mod.

Usage: python tools/check_log.py [path-to-log]
"""
import os
import re
import sys
from pathlib import Path

LOG_DIR = Path(os.environ.get("APPDATA", "")) / "7DaysToDie" / "logs"
MOD = "FerroEngrenagem"
KEYWORDS = re.compile(r"xml|xpath|locali|feTest|fe[A-Z]\w+|" + MOD, re.I)
# Seen in a vanilla run (3.4.0 b10, no mods besides TFP_Harmony): not ours.
BASELINE = ("Retrieving remote news file", "E_XBL_NOT_INITIALIZED",
            "[Discord][Log]", "Failed to fetch Twitch entitlements")


def latest_log() -> Path:
    logs = sorted(LOG_DIR.glob("output_log_client__*.txt"), key=lambda p: p.stat().st_mtime)
    if not logs:
        sys.exit(f"No client log in {LOG_DIR}")
    return logs[-1]


def main() -> int:
    log = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_log()
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"Log: {log}  ({len(lines)} lines)")
    errs = 0
    mod_loaded = False
    for n, line in enumerate(lines, 1):
        if " INF Version:" in line:
            print(f"  {n}: {line.strip()}")
        elif "[MODS]" in line and ("Loaded Mod" in line or "Trying to load" in line or "Failed" in line or MOD in line):
            print(f"  {n}: {line.strip()}")
            if "Loaded Mod" in line and MOD in line:
                mod_loaded = True
        elif f"[{MOD}]" in line or ("[MODS]" in line and "code in mod" in line and MOD in line):
            print(f"  {n}: {line.strip()[:300]}")
        elif any(b in line for b in BASELINE):
            continue
        elif " ERR " in line or " EXC " in line or (" WRN " in line and KEYWORDS.search(line)):
            print(f"! {n}: {line.strip()[:300]}")
            errs += 1
    print(f"\nMod '{MOD}' loaded: {'YES' if mod_loaded else 'NO'}; flagged lines: {errs}")
    return 0 if mod_loaded and errs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
