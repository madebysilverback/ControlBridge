"""
Tapsquatch - Button Prompts patcher (prototype)
Made by Silverback

Changes the key names the game shows on screen ("Press Space") into the
PlayStation buttons from the game's profile ("Press Cross").

* Only edits the game's text files (.int). Originals are backed up first
  and can be put back at any time (option 3).
* Uses plain words (Cross, Circle, Triangle, Square, L1...) because old
  game fonts can't draw the PlayStation symbols.
* Always shows a preview before changing anything.
"""

import json
import os
import re
import shutil
import sys

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(APP_DIR, "profiles")
BACKUP_DIR = os.path.join(APP_DIR, "backups")

BUTTON_LABELS = {
    "cross": "Cross", "circle": "Circle", "square": "Square",
    "triangle": "Triangle", "l1": "L1", "r1": "R1", "l2": "L2", "r2": "R2",
    "l3": "L3", "r3": "R3", "create": "Create", "options": "Options",
    "ps": "PS", "touchpad": "Touchpad", "dpad_up": "D-pad Up",
    "dpad_down": "D-pad Down", "dpad_left": "D-pad Left",
    "dpad_right": "D-pad Right",
}

# How PC games tend to spell each key in their text.
KEY_ALIASES = {
    "SPACE": ["Space", "Spacebar", "Space Bar", "SPACE"],
    "LSHIFT": ["Shift", "Left Shift", "LShift", "SHIFT"],
    "RSHIFT": ["Right Shift", "RShift"],
    "LCTRL": ["Ctrl", "Control", "Left Ctrl", "Left Control", "LCtrl", "CTRL"],
    "RCTRL": ["Right Ctrl", "Right Control", "RCtrl"],
    "LALT": ["Alt", "Left Alt"],
    "ESCAPE": ["Esc", "Escape", "ESC"],
    "ENTER": ["Enter", "Return", "ENTER"],
    "TAB": ["Tab", "TAB"],
    "DELETE": ["Delete", "Del", "DEL"],
    "INSERT": ["Insert", "Ins"],
    "HOME": ["Home"],
    "END": ["End", "END"],
    "PAGEUP": ["PageUp", "Page Up", "PgUp"],
    "PAGEDOWN": ["PageDown", "Page Down", "PgDn"],
    "MOUSE_LEFT": ["LeftMouse", "Left Mouse Button", "Left Mouse", "Left Click",
                   "Left Button", "LMB", "Mouse1"],
    "MOUSE_RIGHT": ["RightMouse", "Right Mouse Button", "Right Mouse",
                    "Right Click", "Right Button", "RMB", "Mouse2"],
    "MOUSE_MIDDLE": ["MiddleMouse", "Middle Mouse Button", "Middle Mouse",
                     "Mouse Wheel Button", "MMB", "Mouse3"],
}
for n in range(10):
    KEY_ALIASES[f"NUMPAD{n}"] = [f"NumPad{n}", f"NumPad {n}", f"Num {n}",
                                 f"Keypad {n}", f"KP {n}", f"KP{n}"]
for n in range(1, 13):
    KEY_ALIASES[f"F{n}"] = [f"F{n}"]

# Words that also appear in normal sentences: only changed when clearly a
# key, e.g. [End], "End", <End>.
RISKY = {"Control", "Return", "Enter", "End", "Home", "Escape", "Delete",
         "Insert", "Alt", "Tab", "Space", "Shift"}

BEFORE = r"(?:(?<=\bpress )|(?<=\bPress )|(?<=\bPRESS )|(?<=\bhold )|(?<=\bHold )|(?<=\bhit )|(?<=\bHit ))"
WRAPPED = [("[", "]"), ("<", ">"), ("(", ")"), ("'", "'"), ('"', '"')]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def as_list(v):
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


# ------------------------------------------------------------------ rules

def build_rules(profile, game_dir=None):
    """List of (game spelling, PlayStation label, risky?)."""
    labels = dict(BUTTON_LABELS)
    labels.update(profile.get("prompt_labels", {}))
    key_to_label = {}
    binds = []
    if game_dir:
        from bindings import read_bindings
        binds = read_bindings(game_dir)
    from bindings import find_key
    for btn, m in profile.get("buttons", {}).items():
        keys = as_list(m.get("key")) or as_list(find_key(m.get("commands", []), binds)) \
            or as_list(m.get("default_key"))
        if len(keys) == 1 and keys[0] not in ("NONE", "WHEEL_UP", "WHEEL_DOWN"):
            key_to_label.setdefault(keys[0], labels.get(btn, btn))
    ls = profile.get("left_stick", {})
    if ls.get("mode") == "keys":
        for d, word in (("up", "Up"), ("down", "Down"), ("left", "Left"), ("right", "Right")):
            for k in as_list(ls.get(d)) or as_list(find_key(ls.get(f"{d}_commands", []), binds)) \
                    or as_list(ls.get(f"{d}_default")):
                key_to_label.setdefault(k, f"Left Stick {word}")
    rules = []
    for key, label in key_to_label.items():
        aliases = KEY_ALIASES.get(key, [])
        if len(key) == 1:               # single letters and digits
            aliases = [key]
        for a in aliases:
            risky = len(a) <= 1 or a in RISKY
            rules.append((a, label, risky, key))
    rules.sort(key=lambda r: -len(r[0]))   # longest first: "Left Shift" before "Shift"
    return rules, key_to_label


def patch_value(text, rules):
    # Labels go in as placeholders first so a new label is never changed again.
    placed = []

    def tok(label):
        placed.append(label)
        return f"\x01{len(placed) - 1}\x02"

    for alias, label_text, risky, _ in rules:
        label = tok(label_text)
        esc = re.escape(alias)
        # wrapped forms are always safe: [Space] -> [Cross]
        for o, c in WRAPPED:
            text = text.replace(f"{o}{alias}{c}", f"{o}{label}{c}")
        if risky:
            # "Press E" / "press E." only, exact case, no letter after
            text = re.sub(BEFORE + esc + r"(?![A-Za-z0-9])", lambda m: label, text)
            continue
        # "Space key" -> "Cross button"
        text = re.sub(r"(?<![\w])" + esc + r"(\s+)(?:key|Key|KEY)\b",
                      lambda m: f"{label}{m.group(1)}button", text)
        text = re.sub(BEFORE + esc + r"(?![\w])", lambda m: label, text)
        text = re.sub(r"(?<![\w])" + esc + r"(?=\s+(?:button|Button|BUTTON)\b)", lambda m: label, text)
    return re.sub("\x01(\\d+)\x02", lambda m: placed[int(m.group(1))], text)


def patch_line(line, rules, key_to_label):
    """Returns the changed line (or the same line)."""
    body = line.rstrip("\r\n")
    ending = line[len(body):]
    if "=" not in body or body.lstrip().startswith((";", "[")):
        return line
    k, v = body.split("=", 1)
    # Key-name tables, e.g.  Space=Space   or   IK_Space="Space"
    name = k.strip()
    if name.upper().startswith("IK_"):
        name = name[3:]
    vclean = v.strip().strip('"')
    for alias, label, _, key in rules:
        if name.lower() in (alias.lower(), key.lower()) and vclean.lower() == alias.lower():
            quoted = v.strip().startswith('"')
            return f'{k}={chr(34) if quoted else ""}{label}{chr(34) if quoted else ""}{ending}'
    new_v = patch_value(v, rules)
    return f"{k}={new_v}{ending}"


# ------------------------------------------------------------------ files

def read_text(path):
    raw = open(path, "rb").read()
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le"), "utf-16-le", b"\xff\xfe"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "utf-8", b"\xef\xbb\xbf"
    try:
        return raw.decode("utf-8"), "utf-8", b""
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252", b""


def write_text(path, text, enc, bom):
    with open(path, "wb") as f:
        f.write(bom + text.encode(enc))


def steam_libraries():
    roots = []
    try:
        import winreg
        for hive, sub in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, sub) as h:
                    for val in ("SteamPath", "InstallPath"):
                        try:
                            roots.append(winreg.QueryValueEx(h, val)[0])
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    roots += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    libs = []
    for r in roots:
        r = os.path.normpath(r)
        if r not in libs and os.path.isdir(r):
            libs.append(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            for m in re.finditer(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf-8", errors="ignore").read()):
                p = os.path.normpath(m.group(1).replace("\\\\", "\\"))
                if p not in libs and os.path.isdir(p):
                    libs.append(p)
    return libs


def find_game(profile):
    """The game's folder: exact match by Steam ID first, then by name words."""
    appid = str(profile.get("steam_appid") or "")
    libs = steam_libraries()
    if appid:
        for lib in libs:
            acf = os.path.join(lib, "steamapps", f"appmanifest_{appid}.acf")
            if os.path.isfile(acf):
                m = re.search(r'"installdir"\s+"([^"]+)"', open(acf, encoding="utf-8", errors="ignore").read())
                if m:
                    folder = os.path.join(lib, "steamapps", "common", m.group(1))
                    if os.path.isdir(folder):
                        return folder
    gf = profile.get("game_files", {})
    words = [w.lower() for w in gf.get("folder_contains", [])]
    for lib in libs:
        common = os.path.join(lib, "steamapps", "common")
        if not os.path.isdir(common):
            continue
        for d in os.listdir(common):
            if words and all(w in d.lower() for w in words):
                return os.path.join(common, d)
    return None


def text_files(game_dir, profile):
    files = []
    for folder in profile.get("game_files", {}).get("text_folders", ["system"]):
        full = os.path.join(game_dir, *folder.split("/"))
        if not os.path.isdir(full):
            continue
        for fn in sorted(os.listdir(full)):
            if fn.lower().endswith(".int"):
                files.append(os.path.join(full, fn))
    return files


def backup_path(profile, game_dir, path):
    rel = os.path.relpath(path, game_dir)
    return os.path.join(BACKUP_DIR, slug(profile["name"]), rel)


def hide_user(path):
    home = os.path.expanduser("~")
    return path.replace(home, "%USERPROFILE%") if home and home != "~" else path


# ------------------------------------------------------------------ actions

def compute_changes(profile, game_dir):
    rules, key_to_label = build_rules(profile, game_dir)
    changes = []   # (path, source_path, new_text, enc, bom, [(lineno, old, new)])
    for path in text_files(game_dir, profile):
        bpath = backup_path(profile, game_dir, path)
        source = bpath if os.path.isfile(bpath) else path   # always patch the original
        text, enc, bom = read_text(source)
        lines = text.splitlines(keepends=True)
        diffs, out = [], []
        for i, line in enumerate(lines, 1):
            new = patch_line(line, rules, key_to_label)
            if new != line:
                diffs.append((i, line.strip(), new.strip()))
            out.append(new)
        changes.append((path, source, "".join(out), enc, bom, diffs))
    return changes


def preview(profile, game_dir):
    changes = compute_changes(profile, game_dir)
    total = 0
    for path, _, _, _, _, diffs in changes:
        if not diffs:
            continue
        print(f"\n--- {os.path.relpath(path, game_dir)}  ({len(diffs)} changes)")
        for n, old, new in diffs[:40]:
            print(f"  line {n}:\n    before: {old[:110]}\n    after:  {new[:110]}")
        if len(diffs) > 40:
            print(f"  ... and {len(diffs) - 40} more")
        total += len(diffs)
    print(f"\nTotal: {total} lines would change in "
          f"{sum(1 for c in changes if c[5])} files.")
    return changes, total


def apply(profile, game_dir):
    changes, total = preview(profile, game_dir)
    if total == 0:
        print("\nNothing to change. Use option 4 and send me the report.")
        return
    if input("\nApply these changes? Type Y and press Enter: ").strip().lower() != "y":
        print("Cancelled - nothing changed.")
        return
    for path, source, new_text, enc, bom, diffs in changes:
        bpath = backup_path(profile, game_dir, path)
        if not os.path.isfile(bpath):
            os.makedirs(os.path.dirname(bpath), exist_ok=True)
            shutil.copy2(path, bpath)
        if diffs:
            write_text(path, new_text, enc, bom)
        elif source == bpath:
            shutil.copy2(bpath, path)   # file no longer needs changes: put original back
    print("\nDone. Start the game to see the new prompts.")
    print("Originals are saved in the 'backups' folder (option 3 restores them).")


def restore(profile, game_dir):
    root = os.path.join(BACKUP_DIR, slug(profile["name"]))
    if not os.path.isdir(root):
        print("No backups found - the game's files were never changed.")
        return
    count = 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            b = os.path.join(dirpath, fn)
            target = os.path.join(game_dir, os.path.relpath(b, root))
            shutil.copy2(b, target)
            count += 1
    print(f"Restored {count} original files. The game shows keyboard keys again.")


def report(profile, game_dir):
    rules, key_to_label = build_rules(profile, game_dir)
    out_path = os.path.join(APP_DIR, "prompt_scan_report.txt")
    lines = [f"Tapsquatch prompt scan report - {profile['name']}",
             f"Game folder: {hide_user(game_dir)}", ""]
    # Current key bindings
    for folder in profile.get("game_files", {}).get("text_folders", []):
        sysdir = os.path.join(game_dir, *folder.split("/"))
        if not os.path.isdir(sysdir):
            continue
        for fn in os.listdir(sysdir):
            if fn.lower().endswith("user.ini"):
                text, _, _ = read_text(os.path.join(sysdir, fn))
                m = re.search(r"\[Engine\.Input\](.*?)(?:\n\[|\Z)", text, re.S | re.I)
                lines.append(f"=== Key bindings in {folder}/{fn} ===")
                if m:
                    lines += [l for l in m.group(1).splitlines()
                              if "=" in l and l.split("=", 1)[1].strip()]
                lines.append("")
    # Text files and lines that mention keys
    words = sorted({a for a, *_ in rules}, key=len, reverse=True)
    pat = re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in words) + r")(?![\w])")
    for path in text_files(game_dir, profile):
        bpath = backup_path(profile, game_dir, path)
        text, enc, _ = read_text(bpath if os.path.isfile(bpath) else path)
        hits = []
        section = ""
        for i, l in enumerate(text.splitlines(), 1):
            s = l.strip()
            if s.startswith("["):
                section = s
            elif "=" in s and pat.search(s.split("=", 1)[1]):
                hits.append(f"  {section} line {i}: {s[:160]}")
        lines.append(f"=== {os.path.relpath(path, game_dir)} ({enc}, {len(hits)} lines mention keys) ===")
        lines += hits[:150]
        lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report saved: {out_path}")
    print("Send me that file and I can fine-tune the patch for this game.")


def all_profile_paths():
    out = []
    for folder in (PROFILE_DIR, os.path.join(PROFILE_DIR, "library")):
        if os.path.isdir(folder):
            out += [os.path.join(folder, f) for f in sorted(os.listdir(folder))
                    if f.endswith(".json") and not f.startswith("_")]
    return out


def choose_profile():
    profs, seen = [], set()
    for path in all_profile_paths():
        p = load_json(path)
        if p.get("game_files") and p.get("name") not in seen:
            seen.add(p.get("name"))
            profs.append(p)
    if not profs:
        print("No profiles with game file info found.")
        sys.exit(1)
    installed = [p for p in profs if find_game(p)]
    profs = installed or profs
    if len(profs) == 1:
        return profs[0]
    for i, p in enumerate(profs, 1):
        print(f"  {i}. {p['name']}")
    return profs[int(input("Game number: ")) - 1]


def main():
    print("Tapsquatch - PlayStation button prompts")
    print("-" * 52)
    profile = choose_profile()
    game_dir = find_game(profile)
    if game_dir:
        print(f"Found {profile['name']} in:\n  {game_dir}")
    else:
        print(f"Couldn't find {profile['name']} automatically.")
        game_dir = input("Paste the game's folder path and press Enter:\n> ").strip().strip('"')
    if not os.path.isdir(game_dir) or not text_files(game_dir, profile):
        print("That folder doesn't contain the game's text files (.int).")
        return
    while True:
        print("\n  1. Preview changes (nothing is changed)")
        print("  2. Apply PlayStation button prompts")
        print("  3. Restore original keyboard prompts")
        print("  4. Make a scan report to send to Claude")
        print("  5. Quit")
        c = input("Choose 1-5: ").strip()
        if c == "1":
            preview(profile, game_dir)
        elif c == "2":
            apply(profile, game_dir)
        elif c == "3":
            restore(profile, game_dir)
        elif c == "4":
            report(profile, game_dir)
        elif c == "5":
            return


def restore_all():
    """Used by the uninstaller: put every game's original text files back."""
    for path in all_profile_paths():
        p = load_json(path)
        if p.get("game_files") and os.path.isdir(os.path.join(BACKUP_DIR, slug(p["name"]))):
            g = find_game(p)
            if g:
                restore(p, g)


if __name__ == "__main__":
    try:
        if "--restore-all" in sys.argv:
            restore_all()
        else:
            main()
    except KeyboardInterrupt:
        pass
    except Exception as e:  # noqa: BLE001
        print(f"\nSomething went wrong: {e}")
        input("Press Enter to close...")
