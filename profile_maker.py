"""
ControlBridge - Profile Maker (prototype)
Made by Silverback

Makes a game profile with AI help, so games don't have to be mapped by hand:

  1. Finds the game folder and its program (.exe).
  2. Reads the PC key bindings from the game's own settings files
     (.ini / .cfg), so the PC keys come from the game, not from guesses.
  3. Takes the PlayStation controls (pasted from the manual or a guide).
  4. An AI matches each PlayStation button to the PC action it does.
  5. Writes a profile into the profiles folder, marking anything the AI
     was unsure about with "check".

Ways to use the AI (all free except the last):
  * Copy and paste: the tool writes a prompt. Paste it into Claude
    (claude.ai), paste the reply back, and the tool finishes the job.
  * Free Gemini key: automatic, from aistudio.google.com, no card needed.
  * Anthropic API key: automatic, a few pence per game.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from prompts_patcher import steam_libraries, slug  # noqa: E402

PROFILE_DIR = os.path.join(APP_DIR, "profiles")
WORK_DIR = os.path.join(APP_DIR, "profile_maker")
SETTINGS = os.path.join(WORK_DIR, "settings.json")
API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"

BUTTONS = ["cross", "circle", "square", "triangle", "l1", "r1", "l2", "r2", "l3", "r3",
           "create", "options", "touchpad", "dpad_up", "dpad_down", "dpad_left", "dpad_right"]

# ---------------------------------------------------------------- game files

from bindings import our_key, read_bindings, walk_limited  # noqa: E402

SKIP_EXE = ("unins", "setup", "install", "redist", "vcredist", "dxsetup", "directx", "crash",
            "report", "update", "patch", "config", "dotnet", "ue4prereq", "uplay", "ubisoftconnect")


def find_games(words):
    """Steam game folders whose name contains every word."""
    hits = []
    for lib in steam_libraries():
        common = os.path.join(lib, "steamapps", "common")
        if os.path.isdir(common):
            for d in os.listdir(common):
                if all(w in d.lower() for w in words):
                    hits.append(os.path.join(common, d))
    return hits


def find_exes(game_dir, bindings):
    exes = []
    for dirpath, files in walk_limited(game_dir):
        for fn in files:
            if fn.lower().endswith(".exe") and not any(w in fn.lower() for w in SKIP_EXE):
                exes.append(os.path.relpath(os.path.join(dirpath, fn), game_dir))
    bind_dirs = {os.path.dirname(b["file"]).lower() for b in bindings}
    exes.sort(key=lambda e: (os.path.dirname(e).lower() not in bind_dirs, e.lower()))
    return exes


def text_folders(game_dir):
    out = set()
    for dirpath, files in walk_limited(game_dir):
        if any(f.lower().endswith(".int") for f in files):
            out.add(os.path.relpath(dirpath, game_dir).replace(os.sep, "/"))
    return sorted(out)


# ---------------------------------------------------------------- the prompt

def make_prompt(game, ps_version, ps_controls, bindings, exes):
    blines = "\n".join(f"- {b['raw']} = {b['command']}   (file: {b['file']})" for b in bindings[:300])
    elines = "\n".join(f"- {e}" for e in exes[:40])
    return f"""You are making a controller profile for ControlBridge, a Windows app that lets a PS5
DualSense play an old PC game using the button layout of the game's PlayStation version.

GAME: {game}
PLAYSTATION VERSION: {ps_version}

PLAYSTATION CONTROLS (from the manual or a guide):
<<<
{ps_controls.strip()}
>>>

PC KEY BINDINGS read from the PC version's own settings files (key = game command):
<<<
{blines or "(none found)"}
>>>

PROGRAM FILES found in the game folder:
<<<
{elines or "(none found)"}
>>>

Task: for each PlayStation button, find the PC binding that does the same action and give
its key EXACTLY as written on the left of the binding list. Match by meaning (for example
"Interact" on PlayStation = "Interaction" or "Use" on PC). Map D-pad and shoulder buttons too.
If the PlayStation button has no PC equivalent, leave it out. If you are not sure, set
"sure": false. Never invent a key that is not in the binding list; if the action has no
binding, give "pc_key": null and "sure": false.

Also pick the main game program from the program list (the one that runs the game itself,
not a launcher or setup), and the movement keys for the left stick.

Reply with ONLY this JSON, nothing else:
{{
  "exe": "<file name only, e.g. Game.exe>",
  "buttons": {{
    "<one of: {', '.join(BUTTONS)}>": {{"action": "<short action name>", "pc_key": "<key from list or null>", "sure": true}}
  }},
  "left_stick": {{"up": "<key>", "down": "<key>", "left": "<key>", "right": "<key>"}},
  "analog_speed_by_mouse_wheel": <true if the PC version sets walking speed with the mouse wheel, else false>,
  "notes": "<one short sentence on anything a player should check>"
}}"""


# ---------------------------------------------------------------- the AI

def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def save_settings(s):
    os.makedirs(WORK_DIR, exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


def ask_api(prompt, key, model):
    body = json.dumps({"model": model, "max_tokens": 4000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"The AI service said: {e.code} {e.read().decode(errors='ignore')[:300]}")
    return "".join(part.get("text", "") for part in data.get("content", []))


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def ask_gemini(prompt, key, model):
    """Google Gemini, free tier: needs only a free key from aistudio.google.com."""
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}).encode()
    req = urllib.request.Request(GEMINI_URL.format(model=model), data=body, method="POST",
                                 headers={"x-goog-api-key": key, "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RuntimeError("The free Gemini limit is used up for now. Try again in a minute, or tomorrow.")
        raise RuntimeError(f"Gemini said: {e.code} {e.read().decode(errors='ignore')[:300]}")
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def parse_reply(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON found in the AI's reply.")
    return json.loads(m.group(0))


# ---------------------------------------------------------------- the profile

def build_profile(game, ps_version, reply, bindings, game_dir):
    known = {b["key"] for b in bindings}
    buttons, unsure = {}, []
    for btn, m in (reply.get("buttons") or {}).items():
        if btn not in BUTTONS or not isinstance(m, dict):
            continue
        key = our_key(m.get("pc_key"))
        cmds = sorted({b["command"] for b in bindings if b["key"] == key}) if key else []
        entry = {"action": str(m.get("action", ""))[:40], "commands": cmds[:3], "default_key": key or "NONE"}
        if not key or key not in known or not m.get("sure", True):
            entry["check"] = True
            unsure.append(btn)
        buttons[btn] = entry
    buttons["ps"] = {"action": "Hold: show this button list", "key": "NONE"}

    ls = reply.get("left_stick") or {}
    move = {d: our_key(ls.get(d)) for d in ("up", "down", "left", "right")}
    defaults = {"up": "W", "down": "S", "left": "A", "right": "D"}
    left = {"mode": "keys",
            **{f"{d}_commands": sorted({b["command"] for b in bindings if b["key"] == move[d]})[:2] for d in move if move[d]},
            **{f"{d}_default": move[d] or defaults[d] for d in move},
            "deadzone": 0.2, "diagonal_threshold": 0.38,
            "analog_speed": {"enabled": bool(reply.get("analog_speed_by_mouse_wheel")),
                             "levels": 5, "rezero_on_release": True}}
    folder = os.path.basename(game_dir.rstrip("\\/")).lower()
    words = [w for w in re.split(r"[^a-z0-9]+", folder) if len(w) > 3][:2] or [folder]
    exe = os.path.basename(str(reply.get("exe") or ""))
    profile = {
        "name": game,
        "playstation_version": ps_version,
        "exe": [exe] if exe else [],
        "overlay_button": "ps",
        "auto_made": True,
        "format": 2,
        "status": "made with AI",
        "_note": "Made by the ControlBridge Profile Maker with AI help. Entries with \"check\": true need a quick test in game. "
                 + str(reply.get("notes", "")),
        "game_files": {"folder_contains": words, "text_folders": text_folders(game_dir) or ["system"]},
        "buttons": buttons,
        "left_stick": left,
        "right_stick": {"mode": "mouse", "sensitivity": 18, "curve": 2.0, "deadzone": 0.12, "invert_y": False},
    }
    return profile, unsure


def save_profile(profile):
    os.makedirs(PROFILE_DIR, exist_ok=True)
    path = os.path.join(PROFILE_DIR, f"{slug(profile['name'])}.json")
    if os.path.exists(path):
        path = path[:-5] + "_auto.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    return path


# ---------------------------------------------------------------- steps

def ask(q, default=None):
    a = input(f"{q}{f' [{default}]' if default else ''}: ").strip()
    return a or (default or "")


def read_multiline(prompt):
    print(prompt)
    print("(Paste it, then type END on its own line and press Enter.)")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def open_file(path):
    if sys.platform == "win32":
        os.startfile(path)


def make_one():
    game = ask("\nGame name (as you'd like it shown)")
    if not game:
        return
    ps_version = ask("PlayStation version it should copy, e.g. PS2 (2004)", "PS2")
    words = [w for w in re.split(r"[^a-z0-9]+", game.lower()) if len(w) > 3][-1:]
    hits = find_games(words) if words else []
    game_dir = hits[0] if len(hits) == 1 else ""
    if len(hits) > 1:
        for i, h in enumerate(hits, 1):
            print(f"  {i}. {h}")
        game_dir = hits[int(ask("Which folder (number)", "1")) - 1]
    if game_dir:
        print(f"Found the game in:\n  {game_dir}")
    else:
        game_dir = ask("Couldn't find it in Steam. Paste the game's folder path").strip('"')
    if not os.path.isdir(game_dir):
        print("That folder doesn't exist.")
        return

    print("\nReading the game's key bindings...")
    bindings = read_bindings(game_dir)
    exes = find_exes(game_dir, bindings)
    print(f"  {len(bindings)} key bindings, {len(exes)} program files found.")
    if not bindings:
        print("  No bindings found. Tip: open the game once, change one key in its Controls")
        print("  menu and back, then quit - many games only write the file after that.")

    ps_file = os.path.join(WORK_DIR, f"{slug(game)}_playstation_controls.txt")
    os.makedirs(WORK_DIR, exist_ok=True)
    if os.path.isfile(ps_file) and ask(f"Use the saved PlayStation controls? (y/n)", "y").lower() == "y":
        ps_controls = open(ps_file, encoding="utf-8").read()
    else:
        ps_controls = read_multiline("\nPaste the PlayStation controls (from the manual, GameFAQs, a wiki...).")
        with open(ps_file, "w", encoding="utf-8") as f:
            f.write(ps_controls)

    prompt = make_prompt(game, ps_version, ps_controls, bindings, exes)
    settings = load_settings()
    gkey = settings.get("gemini_key")
    key = os.environ.get("ANTHROPIC_API_KEY") or settings.get("api_key")
    if gkey:
        print("\nAsking the AI (free Gemini key)...")
        reply_text = ask_gemini(prompt, gkey, settings.get("gemini_model", "gemini-flash-latest"))
    elif key:
        print("\nAsking the AI (Anthropic API key)...")
        reply_text = ask_api(prompt, key, settings.get("model", DEFAULT_MODEL))
    else:
        pfile = os.path.join(WORK_DIR, f"{slug(game)}_prompt.txt")
        rfile = os.path.join(WORK_DIR, f"{slug(game)}_reply.txt")
        with open(pfile, "w", encoding="utf-8") as f:
            f.write(prompt)
        open(rfile, "w", encoding="utf-8").close()
        print("\nFREE MODE")
        print(" 1. Notepad opens with the prompt. Press Ctrl+A, Ctrl+C to copy it.")
        print(" 2. Paste it into Claude (claude.ai) and send.")
        print(" 3. Copy Claude's whole reply, paste it into the second Notepad")
        print("    window (the reply file), and save it.")
        open_file(pfile)
        open_file(rfile)
        input(" 4. Then press Enter here...")
        reply_text = open(rfile, encoding="utf-8").read()

    reply = parse_reply(reply_text)
    profile, unsure = build_profile(game, ps_version, reply, bindings, game_dir)
    path = save_profile(profile)
    print(f"\nSaved: {path}")
    print(f"  {len(profile['buttons']) - 1} buttons mapped, program: {', '.join(profile['exe']) or 'not found'}")
    if unsure:
        print(f"  Please test these in game: {', '.join(unsure)} (shown as 'Check in game').")
    print("ControlBridge picks the new profile up straight away.")
    if ask("\nShare it so everyone gets this game? (y/n)", "y").lower() == "y":
        share(profile)


def share(profile):
    import webbrowser
    import library
    clean = {k: v for k, v in profile.items() if not k.startswith("_") or k == "_note"}
    url = library.share_url(clean)
    if url:
        webbrowser.open(url)
        print("Your browser opens a ready-filled post. Sign in to GitHub and click Submit.")
    else:
        path = os.path.join(WORK_DIR, f"{slug(profile['name'])}_share.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=1)
        webbrowser.open(library.ISSUES_URL)
        print("This profile is too long for a link. Your browser opens a new post:")
        print(f"paste the contents of this file into it, then Submit:\n  {path}")


def set_key():
    print("\nA key lets the tool ask the AI by itself, without copying and pasting.")
    print("  1. Free Gemini key (recommended): aistudio.google.com > Get API key.")
    print("     No card needed. Google may use what's sent to improve its products;")
    print("     the tool only sends game controls and key settings.")
    print("  2. Anthropic API key (paid, a few pence per game): console.anthropic.com")
    print("  3. Remove keys and go back to copy-and-paste mode")
    c = input("Choose 1-3: ").strip()
    s = load_settings()
    if c == "3":
        s.pop("gemini_key", None)
        s.pop("api_key", None)
        print("Removed - copy-and-paste mode will be used.")
    else:
        k = input("Paste the key: ").strip()
        if k:
            s["gemini_key" if c != "2" else "api_key"] = k
            print("Saved.")
    save_settings(s)


def main():
    print("ControlBridge - Profile Maker")
    print("-" * 52)
    while True:
        st = load_settings()
        mode = ("automatic, free Gemini key" if st.get("gemini_key") else
                "automatic, Anthropic key" if (os.environ.get("ANTHROPIC_API_KEY") or st.get("api_key")) else
                "copy and paste into Claude (free)")
        print(f"\nAI mode: {mode}")
        print("  1. Make a profile for a game")
        print("  2. Set or remove an AI key (free Gemini key recommended)")
        print("  3. Quit")
        c = input("Choose 1-3: ").strip()
        try:
            if c == "1":
                make_one()
            elif c == "2":
                set_key()
            elif c == "3":
                return
        except Exception as e:  # noqa: BLE001
            print(f"\nThat didn't work: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
