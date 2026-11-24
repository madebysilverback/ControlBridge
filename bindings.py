"""
ControlBridge - reading key bindings from a game's own files.

Shared by the app (to find each player's real keys when a game starts)
and by the Profile Maker.

Library profiles describe buttons by ACTION, not by key:
    "triangle": {"action": "Jump", "commands": ["Jump"], "default_key": "LSHIFT"}
When the game starts, ControlBridge reads the player's settings files, finds
which key does "Jump" on their copy, and uses that. If nothing is found it
falls back to default_key. A plain "key" (set by the player) always wins.
"""

import os
import re

from prompts_patcher import KEY_ALIASES, read_text

# Our key name -> extra spellings games use.
EXTRA = {
    "LSHIFT": ["LeftShift", "LShift", "Shift"], "RSHIFT": ["RightShift", "RShift"],
    "LCTRL": ["LeftControl", "LControl", "LeftCtrl", "Ctrl", "Control"],
    "RCTRL": ["RightControl", "RControl", "RightCtrl"],
    "LALT": ["LeftAlt", "LAlt", "Alt"], "RALT": ["RightAlt", "RAlt"],
    "ENTER": ["Enter", "Return"], "NUMPAD_ENTER": ["NumPadEnter", "KP_Enter"],
    "BACKSPACE": ["Backspace", "BackSpace"], "CAPSLOCK": ["CapsLock", "Caps"],
    "UP": ["Up", "UpArrow"], "DOWN": ["Down", "DownArrow"],
    "LEFT": ["Left", "LeftArrow"], "RIGHT": ["Right", "RightArrow"],
    "WHEEL_UP": ["MouseWheelUp", "MWheelUp", "Mouse Wheel Up"],
    "WHEEL_DOWN": ["MouseWheelDown", "MWheelDown", "Mouse Wheel Down"],
    "NUMPAD_PERIOD": ["NumPadPeriod", "NumPad.", "KP_Del", "Decimal"],
    "NUMPAD_PLUS": ["GreyPlus", "NumPadPlus", "KP_Plus"],
    "NUMPAD_MINUS": ["GreyMinus", "NumPadMinus", "KP_Minus"],
    "NUMPAD_MULTIPLY": ["GreyStar", "NumPadMultiply"], "NUMPAD_DIVIDE": ["GreySlash", "NumPadDivide"],
    "MINUS": ["Minus"], "EQUALS": ["Equals"], "COMMA": ["Comma"], "PERIOD": ["Period"],
    "SLASH": ["Slash"], "BACKSLASH": ["Backslash"], "SEMICOLON": ["Semicolon"],
    "APOSTROPHE": ["SingleQuote", "Apostrophe"], "GRAVE": ["Tilde", "Grave"],
    "LBRACKET": ["LeftBracket"], "RBRACKET": ["RightBracket"],
}


def _build_lookup():
    look = {}
    for ours, spellings in list(KEY_ALIASES.items()) + list(EXTRA.items()):
        for sp in spellings:
            look.setdefault(sp.lower().replace(" ", ""), ours)
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        look[c.lower()] = c
    for n in range(10):
        look[f"kp_{n}"] = f"NUMPAD{n}"
    return look


KEY_LOOKUP = _build_lookup()


def our_key(raw):
    """'LeftMouse' -> 'MOUSE_LEFT', 'Shift' -> 'LSHIFT', 'q' -> 'Q'. None if unknown."""
    if raw is None:
        return None
    k = str(raw).strip().strip('"').strip("'")
    if k.upper().startswith("IK_"):
        k = k[3:]
    return KEY_LOOKUP.get(k.lower().replace(" ", ""))


def walk_limited(root, depth=4):
    root_depth = root.rstrip("\\/").count(os.sep)
    for dirpath, dirs, files in os.walk(root):
        if dirpath.count(os.sep) - root_depth >= depth:
            dirs[:] = []
        yield dirpath, files


def read_bindings_file(path, rel=None):
    out = []
    try:
        if os.path.getsize(path) > 2_000_000:
            return out
        text, _, _ = read_text(path)
    except Exception:  # noqa: BLE001
        return out
    section = ""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith((";", "//", "#")):
            continue
        if s.startswith("[") and s.endswith("]"):
            section = s.lower()
            continue
        m = re.match(r'bind\s+"?([^"\s]+)"?\s+"?([^"]+?)"?\s*$', s, re.I)   # Quake / Source style
        if m:
            raw, cmd = m.group(1), m.group(2)
        elif "=" in s:
            raw, cmd = (p.strip() for p in s.split("=", 1))
            in_input = any(w in section for w in ("input", "key", "bind", "control"))
            if not in_input and our_key(raw) is None:
                continue
        else:
            continue
        key = our_key(raw)
        cmd = cmd.strip().strip('"')
        if key and cmd:
            out.append({"key": key, "raw": raw, "command": cmd, "file": rel or path})
    return out


def read_bindings(folder, depth=4):
    """Every key binding in .ini/.cfg files under a folder."""
    found = []
    if not folder or not os.path.isdir(folder):
        return found
    for dirpath, files in walk_limited(folder, depth):
        for fn in files:
            if fn.lower().endswith((".ini", ".cfg")):
                p = os.path.join(dirpath, fn)
                found += read_bindings_file(p, os.path.relpath(p, folder))
    seen, out = set(), []
    for b in found:
        sig = (b["key"], b["command"].lower())
        if sig not in seen:
            seen.add(sig)
            out.append(b)
    return out


# ------------------------------------------------------------- resolving

def _expand(path):
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    path = path.replace("%DOCUMENTS%", docs).replace("%USERDOCS%", docs)
    return os.path.expandvars(os.path.expanduser(path))


def game_root_from_exe(exe_path):
    """The game's folder: the exe's folder, or the folder just inside steamapps/common."""
    if not exe_path:
        return None
    parts = os.path.normpath(exe_path).split(os.sep)
    low = [p.lower() for p in parts]
    if "common" in low:
        i = len(low) - 1 - low[::-1].index("common")
        if i + 1 < len(parts) - 1:
            return os.sep.join(parts[:i + 2])
    d = os.path.dirname(exe_path)
    return os.path.dirname(d) if os.path.basename(d).lower() in ("system", "bin", "binaries", "win32", "win64", "x64", "x86") else d


def player_bindings(profile, exe_path):
    """Bindings from the player's own copy of the game."""
    out = []
    root = game_root_from_exe(exe_path)
    if root:
        out += read_bindings(root, depth=4)
    for hint in profile.get("config_hints", []):
        p = _expand(hint)
        if os.path.isfile(p):
            out += read_bindings_file(p)
        elif os.path.isdir(p):
            out += read_bindings(p, depth=2)
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_key(commands, bindings, exclude=()):
    """Key bound to any of the commands. Exact command first, then a word inside it."""
    wanted = [_norm(c) for c in commands if c]
    if not wanted:
        return None
    for w in wanted:
        for b in bindings:
            if _norm(b["command"]) == w and b["key"] not in exclude:
                return b["key"]
    for w in wanted:
        for b in bindings:
            words = [_norm(x) for x in re.split(r"[\s|;,]+", b["command"]) if x]
            if w in words and b["key"] not in exclude:
                return b["key"]
    return None


def resolve_profile(profile, exe_path):
    """
    Returns (profile with a 'key' on every button, report).
    report: button -> 'yours' (player's own key setting), 'game' (from their game files),
            'default' (the game's normal key) or 'missing'.
    """
    import copy
    p = copy.deepcopy(profile)
    report = {}
    binds = player_bindings(profile, exe_path) if any(
        m.get("commands") for m in profile.get("buttons", {}).values()) else []
    for btn, m in p.get("buttons", {}).items():
        if m.get("key") and m.get("key") != "NONE":
            report[btn] = "yours"
            continue
        k = find_key(m.get("commands", []), binds)
        if k:
            m["key"], report[btn] = k, "game"
        elif m.get("default_key") and m.get("default_key") != "NONE":
            m["key"], report[btn] = m["default_key"], "default"
        else:
            m["key"] = "NONE"
            if m.get("action"):
                report[btn] = "missing"
                m["check"] = True
    ls = p.get("left_stick", {})
    for d in ("up", "down", "left", "right"):
        if ls.get("mode", "keys") == "keys" and not ls.get(d):
            ls[d] = (find_key(ls.get(f"{d}_commands", []), binds) or ls.get(f"{d}_default")
                     or {"up": "W", "down": "S", "left": "A", "right": "D"}[d])
    p["_bindings_found"] = len(binds)
    return p, report


# ------------------------------------------------------------- Steam games

def installed_steam_games(steam_libraries):
    """[{appid, name, folder}] for every installed Steam game."""
    games = []
    for lib in steam_libraries():
        sa = os.path.join(lib, "steamapps")
        if not os.path.isdir(sa):
            continue
        for fn in os.listdir(sa):
            if fn.startswith("appmanifest_") and fn.endswith(".acf"):
                try:
                    t = open(os.path.join(sa, fn), encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                get = lambda k: (re.search(rf'"{k}"\s+"([^"]*)"', t) or [None, ""])[1]
                games.append({"appid": get("appid"), "name": get("name"),
                              "folder": os.path.join(sa, "common", get("installdir"))})
    return games
