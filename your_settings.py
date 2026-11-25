"""
ControlBridge - your own settings per game (camera speed, stick feel, button changes).

Saved in profiles/your_settings.json, separate from the game's layout file, so
library updates never wipe them. Applied on top of the layout every time the
game starts.
"""

import json
import os

FILE_NAME = "your_settings.json"

# Tk key names -> ControlBridge key names, for "press a key to change it"
TK_KEYS = {
    "space": "SPACE", "shift_l": "LSHIFT", "shift_r": "RSHIFT", "control_l": "LCTRL", "control_r": "RCTRL",
    "alt_l": "LALT", "alt_r": "RALT", "return": "ENTER", "kp_enter": "NUMPAD_ENTER", "escape": "ESCAPE",
    "tab": "TAB", "backspace": "BACKSPACE", "caps_lock": "CAPSLOCK", "delete": "DELETE", "insert": "INSERT",
    "home": "HOME", "end": "END", "prior": "PAGEUP", "next": "PAGEDOWN", "up": "UP", "down": "DOWN",
    "left": "LEFT", "right": "RIGHT", "minus": "MINUS", "equal": "EQUALS", "bracketleft": "LBRACKET",
    "bracketright": "RBRACKET", "semicolon": "SEMICOLON", "apostrophe": "APOSTROPHE", "grave": "GRAVE",
    "backslash": "BACKSLASH", "comma": "COMMA", "period": "PERIOD", "slash": "SLASH",
    "kp_multiply": "NUMPAD_MULTIPLY", "kp_subtract": "NUMPAD_MINUS", "kp_add": "NUMPAD_PLUS",
    "kp_decimal": "NUMPAD_PERIOD", "kp_delete": "NUMPAD_PERIOD", "kp_divide": "NUMPAD_DIVIDE",
    "kp_insert": "NUMPAD0", "kp_end": "NUMPAD1", "kp_down": "NUMPAD2", "kp_next": "NUMPAD3",
    "kp_left": "NUMPAD4", "kp_begin": "NUMPAD5", "kp_right": "NUMPAD6", "kp_home": "NUMPAD7",
    "kp_up": "NUMPAD8", "kp_prior": "NUMPAD9",
}
for _n in range(10):
    TK_KEYS[f"kp_{_n}"] = f"NUMPAD{_n}"
MOUSE_BUTTONS = {1: "MOUSE_LEFT", 2: "MOUSE_MIDDLE", 3: "MOUSE_RIGHT"}


def key_from_tk(keysym):
    """'a' -> 'A', 'Shift_L' -> 'LSHIFT', 'F5' -> 'F5'. None if not usable."""
    k = (keysym or "").lower()
    if k in TK_KEYS:
        return TK_KEYS[k]
    if len(k) == 1 and k.isascii() and (k.isalpha() or k.isdigit()):
        return k.upper()
    if k.startswith("f") and k[1:].isdigit() and 1 <= int(k[1:]) <= 12:
        return k.upper()
    return None


def profile_id(profile):
    import re
    return profile.get("id") or re.sub(r"[^a-z0-9]+", "_", profile.get("name", "game").lower()).strip("_")


def load(profile_dir):
    try:
        with open(os.path.join(profile_dir, FILE_NAME), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def save(profile_dir, data):
    os.makedirs(profile_dir, exist_ok=True)
    path = os.path.join(profile_dir, FILE_NAME)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(path + ".tmp", path)


def apply(profile, report, settings):
    """Put the player's own choices on top of a resolved layout."""
    mine = settings.get(profile_id(profile), {})
    for btn, key in mine.get("buttons", {}).items():
        if btn in profile.get("buttons", {}):
            profile["buttons"][btn]["key"] = key
            profile["buttons"][btn].pop("check", None)
            report[btn] = "yours"
    rs = profile.setdefault("right_stick", {})
    for k in ("sensitivity", "curve", "deadzone", "invert_y"):
        if k in mine.get("right_stick", {}):
            rs[k] = mine["right_stick"][k]
    ls = profile.setdefault("left_stick", {})
    mls = mine.get("left_stick", {})
    if "deadzone" in mls:
        ls["deadzone"] = mls["deadzone"]
    if "analog_speed" in mls:
        ls.setdefault("analog_speed", {}).update(mls["analog_speed"])
    return profile, report
