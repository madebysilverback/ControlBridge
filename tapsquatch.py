"""
Tapsquatch - prototype
Made by Silverback

Plays keyboard-and-mouse-only PC games with a PS5 DualSense controller,
using the button layout the PlayStation version of the game used.

How it works:
  * Reads the DualSense (USB or Bluetooth) through SDL (pygame-ce).
  * Watches which program is in front. When it matches a game in the
    "profiles" folder, that game's PlayStation-style layout switches on.
  * Buttons become key presses / mouse clicks, the left stick becomes
    movement keys, the right stick becomes mouse movement.
  * Input is only sent while the game window is in front, so it never
    types into other programs.

Run:   python tapsquatch.py

"""

import ctypes
import json
import math
import os
import sys
import time
from ctypes import wintypes

# Let SDL read the controller even when our console window is not in front.
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

try:
    import pygame
except ImportError:
    print("pygame-ce is not installed. Run Start.bat, it installs it for you.")
    input("Press Enter to close...")
    sys.exit(1)

if getattr(sys, "frozen", False):          # running as installed Tapsquatch.exe
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
PROFILE_DIR = os.path.join(APP_DIR, "profiles")
LAYOUT_FILE = os.path.join(APP_DIR, "controller_layout.json")
LOOP_HZ = 250

IS_WINDOWS = sys.platform == "win32"

# --------------------------------------------------------------------------
# Windows input sending (SendInput with hardware scan codes, which works
# with old DirectInput games as well as newer ones)
# --------------------------------------------------------------------------

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 0x1, 0x2, 0x8
MOUSEEVENTF_MOVE = 0x0001
MOUSE_BUTTON_FLAGS = {
    "MOUSE_LEFT": (0x0002, 0x0004),
    "MOUSE_RIGHT": (0x0008, 0x0010),
    "MOUSE_MIDDLE": (0x0020, 0x0040),
}
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120

# Scan codes (set 1). (code, extended?)
SCANCODES = {
    "ESCAPE": (0x01, False), "1": (0x02, False), "2": (0x03, False),
    "3": (0x04, False), "4": (0x05, False), "5": (0x06, False),
    "6": (0x07, False), "7": (0x08, False), "8": (0x09, False),
    "9": (0x0A, False), "0": (0x0B, False), "MINUS": (0x0C, False),
    "EQUALS": (0x0D, False), "BACKSPACE": (0x0E, False), "TAB": (0x0F, False),
    "Q": (0x10, False), "W": (0x11, False), "E": (0x12, False),
    "R": (0x13, False), "T": (0x14, False), "Y": (0x15, False),
    "U": (0x16, False), "I": (0x17, False), "O": (0x18, False),
    "P": (0x19, False), "LBRACKET": (0x1A, False), "RBRACKET": (0x1B, False),
    "ENTER": (0x1C, False), "LCTRL": (0x1D, False), "A": (0x1E, False),
    "S": (0x1F, False), "D": (0x20, False), "F": (0x21, False),
    "G": (0x22, False), "H": (0x23, False), "J": (0x24, False),
    "K": (0x25, False), "L": (0x26, False), "SEMICOLON": (0x27, False),
    "APOSTROPHE": (0x28, False), "GRAVE": (0x29, False),
    "LSHIFT": (0x2A, False), "BACKSLASH": (0x2B, False), "Z": (0x2C, False),
    "X": (0x2D, False), "C": (0x2E, False), "V": (0x2F, False),
    "B": (0x30, False), "N": (0x31, False), "M": (0x32, False),
    "COMMA": (0x33, False), "PERIOD": (0x34, False), "SLASH": (0x35, False),
    "RSHIFT": (0x36, False), "NUMPAD_MULTIPLY": (0x37, False),
    "LALT": (0x38, False), "SPACE": (0x39, False), "CAPSLOCK": (0x3A, False),
    "F1": (0x3B, False), "F2": (0x3C, False), "F3": (0x3D, False),
    "F4": (0x3E, False), "F5": (0x3F, False), "F6": (0x40, False),
    "F7": (0x41, False), "F8": (0x42, False), "F9": (0x43, False),
    "F10": (0x44, False), "NUMLOCK": (0x45, False),
    "SCROLLLOCK": (0x46, False), "NUMPAD7": (0x47, False),
    "NUMPAD8": (0x48, False), "NUMPAD9": (0x49, False),
    "NUMPAD_MINUS": (0x4A, False), "NUMPAD4": (0x4B, False),
    "NUMPAD5": (0x4C, False), "NUMPAD6": (0x4D, False),
    "NUMPAD_PLUS": (0x4E, False), "NUMPAD1": (0x4F, False),
    "NUMPAD2": (0x50, False), "NUMPAD3": (0x51, False),
    "NUMPAD0": (0x52, False), "NUMPAD_PERIOD": (0x53, False),
    "F11": (0x57, False), "F12": (0x58, False),
    # extended keys
    "NUMPAD_ENTER": (0x1C, True), "RCTRL": (0x1D, True),
    "NUMPAD_DIVIDE": (0x35, True), "RALT": (0x38, True),
    "HOME": (0x47, True), "UP": (0x48, True), "PAGEUP": (0x49, True),
    "LEFT": (0x4B, True), "RIGHT": (0x4D, True), "END": (0x4F, True),
    "DOWN": (0x50, True), "PAGEDOWN": (0x51, True), "INSERT": (0x52, True),
    "DELETE": (0x53, True),
}
OUTPUT_NAMES = set(SCANCODES) | set(MOUSE_BUTTON_FLAGS) | {"WHEEL_UP", "WHEEL_DOWN", "NONE"}

if IS_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT


def _send(inp):
    if IS_WINDOWS:
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_key(name, down):
    code, extended = SCANCODES[name]
    flags = KEYEVENTF_SCANCODE | (0 if down else KEYEVENTF_KEYUP)
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.u.ki = KEYBDINPUT(0, code, flags, 0, 0)
    _send(inp)


def send_mouse_button(name, down):
    down_flag, up_flag = MOUSE_BUTTON_FLAGS[name]
    inp = INPUT(type=INPUT_MOUSE)
    inp.u.mi = MOUSEINPUT(0, 0, 0, down_flag if down else up_flag, 0, 0)
    _send(inp)


def send_mouse_move(dx, dy):
    inp = INPUT(type=INPUT_MOUSE)
    inp.u.mi = MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, 0)
    _send(inp)


def send_wheel(steps):
    inp = INPUT(type=INPUT_MOUSE)
    inp.u.mi = MOUSEINPUT(0, 0, (steps * WHEEL_DELTA) & 0xFFFFFFFF, MOUSEEVENTF_WHEEL, 0, 0)
    _send(inp)


FOREGROUND_PATH = [None]   # full path of the last program seen in front


def foreground_exe():
    """Name of the program whose window is in front, e.g. 'splintercell2.exe'."""
    if not IS_WINDOWS:
        return None
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return "__self__"          # our own overlay: ignore
    handle = kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            FOREGROUND_PATH[0] = buf.value
            return os.path.basename(buf.value).lower()
    finally:
        kernel32.CloseHandle(handle)
    return None


# --------------------------------------------------------------------------
# Output state: remembers what is held so nothing gets "stuck"
# --------------------------------------------------------------------------

class Output:
    def __init__(self):
        self.held = {}          # output name -> number of sources holding it
        self.wheel_queue = []   # +1 / -1 ticks, sent one at a time
        self.next_wheel = 0.0
        self.mouse_rem = [0.0, 0.0]

    def press(self, name):
        if name == "NONE":
            return
        if name in ("WHEEL_UP", "WHEEL_DOWN"):
            self.wheel_queue.append(1 if name == "WHEEL_UP" else -1)
            return
        count = self.held.get(name, 0)
        self.held[name] = count + 1
        if count == 0:
            self._raw(name, True)

    def release(self, name):
        if name in ("NONE", "WHEEL_UP", "WHEEL_DOWN"):
            return
        count = self.held.get(name, 0)
        if count <= 1:
            self.held.pop(name, None)
            if count == 1:
                self._raw(name, False)
        else:
            self.held[name] = count - 1

    def _raw(self, name, down):
        if name in MOUSE_BUTTON_FLAGS:
            send_mouse_button(name, down)
        else:
            send_key(name, down)

    def move_mouse(self, fx, fy):
        self.mouse_rem[0] += fx
        self.mouse_rem[1] += fy
        dx, dy = int(self.mouse_rem[0]), int(self.mouse_rem[1])
        if dx or dy:
            self.mouse_rem[0] -= dx
            self.mouse_rem[1] -= dy
            send_mouse_move(dx, dy)

    def tick(self, now):
        # One wheel notch every ~15 ms so the game counts each one.
        if self.wheel_queue and now >= self.next_wheel:
            send_wheel(self.wheel_queue.pop(0))
            self.next_wheel = now + 0.015

    def release_all(self):
        for name in list(self.held):
            self._raw(name, False)
        self.held.clear()
        self.wheel_queue.clear()


# --------------------------------------------------------------------------
# Controller reading
# --------------------------------------------------------------------------

BUTTON_NAMES = ["cross", "circle", "square", "triangle", "l1", "r1", "l2", "r2",
                "l3", "r3", "create", "options", "ps", "touchpad",
                "dpad_up", "dpad_down", "dpad_left", "dpad_right"]

PRETTY = {"cross": "Cross (X)", "circle": "Circle", "square": "Square",
          "triangle": "Triangle", "l1": "L1", "r1": "R1", "l2": "L2", "r2": "R2",
          "l3": "L3 (press left stick)", "r3": "R3 (press right stick)",
          "create": "Create", "options": "Options", "ps": "PS button",
          "touchpad": "Touchpad click", "dpad_up": "D-pad Up",
          "dpad_down": "D-pad Down", "dpad_left": "D-pad Left",
          "dpad_right": "D-pad Right"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Pad:
    def __init__(self, joystick, layouts):
        self.js = joystick
        self.name = joystick.get_name()
        nb, nh = joystick.get_numbuttons(), joystick.get_numhats()
        # SDL's own DualSense driver gives 16+ buttons and no hat.
        key = "sdl" if (nb >= 15 and nh == 0) else "directinput"
        self.layout_name = key
        self.layout = layouts[key]
        self.trigger_threshold = layouts.get("trigger_threshold", 0.6)

    def _button(self, idx):
        return idx is not None and idx < self.js.get_numbuttons() and self.js.get_button(idx)

    def _axis(self, idx):
        if idx is None or idx >= self.js.get_numaxes():
            return 0.0
        return self.js.get_axis(idx)

    def read(self):
        b = self.layout["buttons"]
        a = self.layout["axes"]
        state = {name: bool(self._button(b.get(name))) for name in BUTTON_NAMES}
        hat = self.layout.get("dpad_hat")
        if hat is not None and hat < self.js.get_numhats():
            hx, hy = self.js.get_hat(hat)
            state["dpad_left"], state["dpad_right"] = hx < 0, hx > 0
            state["dpad_up"], state["dpad_down"] = hy > 0, hy < 0
        l2 = (self._axis(a.get("l2")) + 1) / 2
        r2 = (self._axis(a.get("r2")) + 1) / 2
        state["l2"] = state["l2"] or l2 > self.trigger_threshold
        state["r2"] = state["r2"] or r2 > self.trigger_threshold
        sticks = (self._axis(a["lx"]), self._axis(a["ly"]),
                  self._axis(a["rx"]), self._axis(a["ry"]))
        return state, sticks, (l2, r2)


# --------------------------------------------------------------------------
# Profiles
# --------------------------------------------------------------------------

def as_list(value):
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def validate_profile(p, path):
    problems = []
    for btn, m in p.get("buttons", {}).items():
        if btn not in BUTTON_NAMES:
            problems.append(f"unknown button '{btn}'")
        for k in as_list(m.get("key")) + as_list(m.get("default_key")):
            if k not in OUTPUT_NAMES:
                problems.append(f"{btn}: unknown key '{k}'")
    ls = p.get("left_stick", {})
    if ls.get("mode") == "keys":
        for d in ("up", "down", "left", "right"):
            for k in as_list(ls.get(d)) + as_list(ls.get(f"{d}_default")):
                if k not in OUTPUT_NAMES:
                    problems.append(f"left_stick {d}: unknown key '{k}'")
    for prob in problems:
        print(f"  ! {os.path.basename(path)}: {prob}")
    return not problems


def _profile_files():
    """Your own profiles first, then the downloaded library."""
    out = []
    for folder, source in ((PROFILE_DIR, "yours"), (os.path.join(PROFILE_DIR, "library"), "library")):
        if os.path.isdir(folder):
            for fn in sorted(os.listdir(folder)):
                if fn.lower().endswith(".json") and not fn.startswith("_"):
                    out.append((os.path.join(folder, fn), source))
    return out


def load_profiles():
    profiles = {}
    for path, source in _profile_files():
        try:
            p = load_json(path)
        except Exception as e:  # noqa: BLE001
            print(f"  ! Could not read {os.path.basename(path)}: {e}")
            continue
        if not validate_profile(p, path):
            continue
        p["_file"], p["_source"] = path, source
        for exe in p.get("exe", []):
            profiles.setdefault(exe.lower(), p)      # your own profile wins
    return profiles


def profiles_stamp():
    return sum(os.path.getmtime(path) for path, _ in _profile_files())


def print_profile(p):
    print()
    print("=" * 64)
    print(f" {p.get('name', 'Game')}  -  PlayStation layout ON")
    print("=" * 64)
    for btn in BUTTON_NAMES:
        m = p.get("buttons", {}).get(btn)
        if not m or as_list(m.get("key")) in ([], ["NONE"]):
            continue
        keys = " + ".join(as_list(m["key"]))
        flag = "   <- check" if m.get("check") else ""
        print(f"  {PRETTY[btn]:<24} {m.get('action', ''):<24} [{keys}]{flag}")
    ls = p.get("left_stick", {})
    rs = p.get("right_stick", {})
    if ls:
        extra = " + analog speed (mouse wheel)" if ls.get("analog_speed", {}).get("enabled") else ""
        print(f"  {'Left stick':<24} {'Move':<24} [{'/'.join(as_list(ls.get('up')) + as_list(ls.get('left')) + as_list(ls.get('down')) + as_list(ls.get('right')))}]{extra}")
    if rs:
        print(f"  {'Right stick':<24} {'Camera':<24} [mouse]")
    print("-" * 64)
    print("  Keys marked 'check' are best guesses: compare with the game's")
    print("  Options > Controls screen and edit the profile file if needed.")
    print()


# --------------------------------------------------------------------------
# Mapping engine
# --------------------------------------------------------------------------

def radial(x, y, deadzone):
    mag = math.hypot(x, y)
    if mag <= deadzone:
        return 0.0, 0.0, 0.0
    scaled = min(1.0, (mag - deadzone) / (1 - deadzone))
    return x / mag, y / mag, scaled


class Mapper:
    def __init__(self, profile, out):
        self.p = profile
        self.out = out
        self.prev = {name: False for name in BUTTON_NAMES}
        self.move_held = set()
        ls = profile.get("left_stick", {})
        sp = ls.get("analog_speed", {})
        self.speed_on = bool(sp.get("enabled"))
        self.levels = max(1, int(sp.get("levels", 5)))
        self.rezero = bool(sp.get("rezero_on_release", True))
        self.speed_level = None     # unknown until we zero it
        self.speed_pending = None
        self.speed_since = 0.0
        self.was_moving = False
        self.rest_since = None
        self.sector, self.sector_since = None, 0.0
        if self.speed_on:
            self.zero_speed()

    def zero_speed(self):
        for _ in range(self.levels + 1):
            self.out.press("WHEEL_DOWN")
        self.speed_level = 0

    def update(self, state, sticks, dt, now):
        buttons = self.p.get("buttons", {})
        for name in BUTTON_NAMES:
            m = buttons.get(name)
            if not m:
                continue
            keys = as_list(m.get("key"))
            if state[name] and not self.prev[name]:
                for k in keys:
                    self.out.press(k)
            elif not state[name] and self.prev[name]:
                for k in keys:
                    self.out.release(k)
        self.prev = dict(state)
        self._left_stick(sticks[0], sticks[1], now)
        self._right_stick(sticks[2], sticks[3], dt)

    def _left_stick(self, x, y, now):
        ls = self.p.get("left_stick", {})
        if ls.get("mode") != "keys":
            return
        dx, dy, mag = radial(x, y, ls.get("deadzone", 0.2))
        # 8 steady directions. A direction only changes when the stick is
        # clearly in the next one (no flicker on the edge), and each direction
        # is held long enough for the game to notice it - this is what makes
        # keyboard-style lockpicking work while you rotate the stick.
        hyst = ls.get("hysteresis_deg", 10)
        min_hold = ls.get("min_hold_ms", 90) / 1000
        sector = None
        if mag > 0:
            ang = math.degrees(math.atan2(dy, dx))
            if self.sector is not None:
                diff = (ang - self.sector * 45 + 180) % 360 - 180
                sector = self.sector if abs(diff) <= 22.5 + hyst else round(ang / 45) % 8
            else:
                sector = round(ang / 45) % 8
        if sector != self.sector and self.sector is not None and sector is not None \
                and now - self.sector_since < min_hold:
            sector = self.sector                      # keep the last one a moment longer
        if sector != self.sector:
            self.sector, self.sector_since = sector, now
        want = set()
        if sector is not None:
            if sector in (5, 6, 7): want.update(as_list(ls.get("up")))
            if sector in (1, 2, 3): want.update(as_list(ls.get("down")))
            if sector in (3, 4, 5): want.update(as_list(ls.get("left")))
            if sector in (7, 0, 1): want.update(as_list(ls.get("right")))
        for k in self.move_held - want:
            self.out.release(k)
        for k in want - self.move_held:
            self.out.press(k)
        self.move_held = want

        if not self.speed_on:
            return
        if mag == 0:
            if self.was_moving:
                self.rest_since = now
                self.was_moving = False
            if self.rezero and self.rest_since is not None and now - self.rest_since >= 0.3:
                self.zero_speed()                     # only after a real rest, not a quick wiggle
                self.rest_since = None
            self.speed_pending = None
            return
        self.was_moving = True
        self.rest_since = None
        target = min(self.levels - 1, int(mag * self.levels))
        if target == self.speed_level:
            self.speed_pending = None
            return
        if target != self.speed_pending:
            self.speed_pending, self.speed_since = target, now
            return
        if now - self.speed_since >= 0.06:   # stable for 60 ms
            diff = target - self.speed_level
            for _ in range(abs(diff)):
                self.out.press("WHEEL_UP" if diff > 0 else "WHEEL_DOWN")
            self.speed_level = target
            self.speed_pending = None

    def _right_stick(self, x, y, dt):
        rs = self.p.get("right_stick", {})
        if rs.get("mode") != "mouse":
            return
        dx, dy, mag = radial(x, y, rs.get("deadzone", 0.12))
        if mag == 0:
            return
        speed = (mag ** rs.get("curve", 2.0)) * rs.get("sensitivity", 18) * dt * 60
        if rs.get("invert_y"):
            dy = -dy
        self.out.move_mouse(dx * speed, dy * speed)

    def stop(self):
        for k in self.move_held:
            self.out.release(k)
        self.move_held = set()
        self.out.release_all()



import threading  # noqa: E402
import webbrowser  # noqa: E402

import library  # noqa: E402
import your_settings  # noqa: E402
from bindings import installed_steam_games, resolve_profile  # noqa: E402
from prompts_patcher import steam_libraries  # noqa: E402

SOURCE_TEXT = {"game": ("From your game", "#2d6a3e"), "default": ("Normal key", "#6a5a48"),
               "yours": ("Your setting", "#2d6a3e"), "missing": ("Not found, check in game", "#8a5a00")}


# --------------------------------------------------------------------------
# Look and feel (matches the website: off-white, off-black, strip blue)
# --------------------------------------------------------------------------

INK, WHITE, PAPER, LINE = "#2e4a3b", "#f3e8cd", "#e6d6b2", "#d6c49e"
OFF, CARD = "#efe3c6", "#f8efda"
APP_VERSION = "0.9.2"
MUTED, SOFT, BLUE, CHECK = "#6a5a48", "#c9b593", "#c15f2c", "#8a5a00"
ASSETS = os.path.join(APP_DIR, "assets")
FONT_DIR = os.path.join(APP_DIR, "fonts")


def register_fonts():
    """Load the bundled Open Sans / Exo 2 files for this program only."""
    if not (IS_WINDOWS and os.path.isdir(FONT_DIR)):
        return
    for fn in os.listdir(FONT_DIR):
        if fn.lower().endswith((".ttf", ".otf")):
            ctypes.windll.gdi32.AddFontResourceExW(os.path.join(FONT_DIR, fn), 0x10, 0)


def pick_fonts(tkfont):
    fams = set(tkfont.families())
    body = next((f for f in ("Open Sans", "Segoe UI", "Arial") if f in fams), "TkDefaultFont")
    disp = next((f for f in ("Exo 2 ExtraBold", "Exo 2", "Open Sans ExtraBold", "Segoe UI Black")
                 if f in fams), body)
    return body, disp


# Where each button sits on assets/controller.png, in logo units (240 x 128,
# starting 12 units down). ("o", cx, cy, r) circle, ("r", x0, y0, x1, y1) box.
SPOTS = {
    "triangle": ("o", 185, 50, 7.4), "cross": ("o", 185, 78, 7.4),
    "square": ("o", 171, 64, 7.4), "circle": ("o", 199, 64, 7.4),
    "dpad_up": ("r", 49, 43, 61, 56), "dpad_down": ("r", 49, 72, 61, 85),
    "dpad_left": ("r", 34, 58, 47, 70), "dpad_right": ("r", 63, 58, 76, 70),
    "l3": ("o", 109, 81, 6.6), "r3": ("o", 131, 81, 6.6),
    "create": ("r", 86, 38, 91, 50), "options": ("r", 149, 38, 154, 50),
    "ps": ("o", 120, 69, 3.6), "touchpad": ("r", 102, 35, 138, 62),
    "l1": ("r", 52, 27.5, 88, 32), "r1": ("r", 152, 27.5, 188, 32),
    "l2": ("r", 54, 19, 86, 24), "r2": ("r", 154, 19, 186, 24),
}


class Overlay:
    """Hold-PS button list: a click-through panel that never takes focus."""

    def __init__(self, master, body, disp):
        import tkinter as tk
        self.tk, self.body, self.disp = tk, body, disp
        self.visible = False
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.0)
        self.win.configure(bg=INK)
        self.win.geometry("+40+40")
        self.frame = tk.Frame(self.win, bg=INK, padx=22, pady=18,
                              highlightthickness=1, highlightbackground="#243a2e")
        self.frame.pack()
        self.win.update_idletasks()
        if IS_WINDOWS:
            hwnd = user32.GetAncestor(self.win.winfo_id(), 2)
            style = user32.GetWindowLongW(hwnd, -20)
            user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x08000000 | 0x8)

    def set_profile(self, p):
        tk = self.tk
        for w in self.frame.winfo_children():
            w.destroy()
        tk.Label(self.frame, text=p.get("name", ""), fg=WHITE, bg=INK, font=(self.disp, 15, "bold"),
                 anchor="w").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        rows = [(PRETTY[b].split(" (")[0], m.get("action", "")) for b in BUTTON_NAMES
                for m in [p.get("buttons", {}).get(b)] if m and m.get("action")]
        rows += [("Left stick", "Move, push further to go faster"), ("Right stick", "Camera")]
        for i, (btn, action) in enumerate(rows, 1):
            tk.Label(self.frame, text=btn, fg=WHITE, bg=INK, font=(self.body, 11, "bold"),
                     anchor="w").grid(row=i, column=0, sticky="w", pady=1)
            tk.Label(self.frame, text=action, fg="#e6d6b2", bg=INK, font=(self.body, 11),
                     anchor="w").grid(row=i, column=1, sticky="w", padx=(18, 0), pady=1)

    def show(self, on):
        if on == self.visible:
            return
        self.visible = on
        self.win.attributes("-alpha", 0.94 if on else 0.0)
        if on and IS_WINDOWS:
            hwnd = user32.GetAncestor(self.win.winfo_id(), 2)
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)


KEY_LABELS = {"LSHIFT": "Shift", "RSHIFT": "Right Shift", "LCTRL": "Ctrl", "RCTRL": "Right Ctrl",
              "LALT": "Alt", "RALT": "Right Alt", "SPACE": "Space", "ESCAPE": "Esc", "ENTER": "Enter",
              "MOUSE_LEFT": "Left mouse", "MOUSE_RIGHT": "Right mouse", "MOUSE_MIDDLE": "Middle mouse",
              "WHEEL_UP": "Wheel up", "WHEEL_DOWN": "Wheel down", "PAGEUP": "Page Up", "PAGEDOWN": "Page Down",
              "DELETE": "Delete", "END": "End", "HOME": "Home", "INSERT": "Insert", "BACKSPACE": "Backspace",
              "CAPSLOCK": "Caps Lock", "NUMPAD_PERIOD": "Num .", "NUMPAD_ENTER": "Num Enter"}


def key_label(k):
    if k in KEY_LABELS:
        return KEY_LABELS[k]
    if k.startswith("NUMPAD") and k[6:].isdigit():
        return f"Num {k[6:]}"
    return k.replace("_", " ").title() if len(k) > 1 else k


def _walk2(root):
    """Folders up to three levels down (enough to find a game's .exe)."""
    base = root.rstrip("\\/").count(os.sep)
    for d, dirs, files in os.walk(root):
        if d.count(os.sep) - base >= 3:
            dirs[:] = []
        yield d, files


class SettingsWindow:
    """Per-game settings: camera speed, stick feel and button changes, saved separately
    from the layout so library updates never wipe them."""

    def __init__(self, app):
        import copy
        self.app, self.ctk = app, app.ctk
        ctk = self.ctk
        self.copy = copy
        self.games = {}
        for q in app.profiles.values():
            self.games.setdefault(your_settings.profile_id(q), q)
        if not self.games:
            return
        start = app.current or next((q for q in self.games.values() if q.get("name") in app._my_supported_games()),
                                    None) or sorted(self.games.values(), key=lambda q: q.get("name", ""))[0]
        self.win = ctk.CTkToplevel(app.root, fg_color=OFF)
        self.win.title("Tapsquatch settings")
        self.win.geometry("800x740")
        self.win.minsize(720, 600)
        self.win.transient(app.root)
        self.win.after(150, self.win.lift)

        head = ctk.CTkFrame(self.win, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(22, 12))
        app.label(head, "Settings", 22, bold=True, display=True).pack(side="left")
        names = sorted(q.get("name", "?") for q in self.games.values())
        self.picker = ctk.CTkOptionMenu(head, values=names, command=self.pick_game, width=300, height=36,
                                        corner_radius=9, fg_color=CARD, button_color=INK,
                                        button_hover_color="#243a2e", text_color=INK,
                                        font=app.font(13, bold=True), dropdown_font=app.font(13))
        self.picker.pack(side="right")
        app.label(head, "Game", 13, MUTED).pack(side="right", padx=(0, 10))

        foot = ctk.CTkFrame(self.win, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=28, pady=(12, 22))
        app.button(foot, "Save", self.save, primary=True).pack(side="right")
        app.button(foot, "Cancel", self.win.destroy).pack(side="right", padx=(0, 10))
        app.link(foot, "Reset this game", self.reset_all).pack(side="left")

        self.body = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=(22, 14))
        self.picker.set(start.get("name", "?"))
        self.pick_game(start.get("name"))

    # ------------------------------------------------------------ helpers
    def card(self, title, note=""):
        ctk, app = self.ctk, self.app
        c = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=16, border_width=1, border_color=LINE)
        c.pack(fill="x", padx=6, pady=(0, 14))
        app.label(c, title, 16, bold=True).pack(fill="x", padx=22, pady=(18, 0))
        if note:
            app.label(c, note, 12, MUTED, wraplength=640).pack(fill="x", padx=22, pady=(2, 0))
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=(10, 18))
        inner.grid_columnconfigure(1, weight=1)
        return inner

    def slider(self, parent, row, label, low, high, steps, value, fmt, on_change):
        ctk, app = self.ctk, self.app
        app.label(parent, label, 13).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 16))
        out = app.label(parent, fmt(value), 13, bold=True, width=70)
        out.grid(row=row, column=2, sticky="e", pady=8)

        def changed(v):
            out.configure(text=fmt(v))
            on_change(v)
        sl = ctk.CTkSlider(parent, from_=low, to=high, number_of_steps=steps, command=changed, height=18,
                           fg_color="#d6c49e", progress_color=INK, button_color=INK, button_hover_color=BLUE)
        sl.set(value)
        sl.grid(row=row, column=1, sticky="ew", pady=8)

    def switch(self, parent, row, label, value, on_change):
        ctk, app = self.ctk, self.app
        app.label(parent, label, 13).grid(row=row, column=0, columnspan=2, sticky="w", pady=8)
        sw = ctk.CTkSwitch(parent, text="", width=46, progress_color=BLUE, button_color="#f8efda",
                           button_hover_color="#f8efda", fg_color="#dcc8a4",
                           command=lambda: on_change(bool(sw.get())))
        if value:
            sw.select()
        sw.grid(row=row, column=2, sticky="e", pady=8)

    # ------------------------------------------------------------ content
    def pick_game(self, name):
        self.profile = next(q for q in self.games.values() if q.get("name") == name)
        self.pid = your_settings.profile_id(self.profile)
        self.draft = self.copy.deepcopy(self.app.user_settings.get(self.pid, {}))
        if self.app.current and your_settings.profile_id(self.app.current) == self.pid:
            self.resolved = self.app.current
        else:
            self.resolved, _ = resolve_profile(self.profile, None)
        self.capturing = None
        self.render()

    def render(self):
        for w in self.body.winfo_children():
            w.destroy()
        d, p = self.draft, self.resolved
        rs = {**p.get("right_stick", {}), **d.get("right_stick", {})}
        ls = p.get("left_stick", {})
        mls = d.get("left_stick", {})
        sets = lambda part, key: (lambda v: d.setdefault(part, {}).__setitem__(key, v))

        cam = self.card("Camera", "Right stick. Turn it faster or slower, and choose how gentle it is near the centre.")
        self.slider(cam, 0, "Speed", 4, 40, 36, rs.get("sensitivity", 18), lambda v: f"{int(round(v))}",
                    lambda v: sets("right_stick", "sensitivity")(int(round(v))))
        self.slider(cam, 1, "Fine aiming", 1.0, 3.0, 20, rs.get("curve", 2.0), lambda v: f"{v:.1f}",
                    lambda v: sets("right_stick", "curve")(round(v, 1)))
        self.slider(cam, 2, "Deadzone", 0.04, 0.3, 26, rs.get("deadzone", 0.12), lambda v: f"{int(round(v * 100))}%",
                    lambda v: sets("right_stick", "deadzone")(round(v, 2)))
        self.switch(cam, 3, "Invert up and down", rs.get("invert_y", False), sets("right_stick", "invert_y"))

        mv = self.card("Movement", "Left stick.")
        self.slider(mv, 0, "Deadzone", 0.05, 0.5, 45, mls.get("deadzone", ls.get("deadzone", 0.2)),
                    lambda v: f"{int(round(v * 100))}%", lambda v: sets("left_stick", "deadzone")(round(v, 2)))
        if "analog_speed" in ls:
            sp = {**ls["analog_speed"], **mls.get("analog_speed", {})}

            def set_speed(key):
                return lambda v: d.setdefault("left_stick", {}).setdefault("analog_speed", {}).__setitem__(key, v)
            self.switch(mv, 1, "Push further to move faster", sp.get("enabled", False), set_speed("enabled"))
            self.slider(mv, 2, "Speed steps in this game", 2, 8, 6, sp.get("levels", 5), lambda v: f"{int(round(v))}",
                        lambda v: set_speed("levels")(int(round(v))))

        bt = self.card("Buttons", "Click Change, then press the key (or click the mouse button) the game uses.")
        bt.grid_columnconfigure(1, weight=1)
        mine = d.get("buttons", {})
        r = 0
        for btn in BUTTON_NAMES:
            m = p.get("buttons", {}).get(btn)
            if btn == "ps" or not m or not m.get("action"):
                continue
            key = mine.get(btn) or (m.get("key") if m.get("key") not in (None, "NONE") else m.get("default_key"))
            self.app.label(bt, PRETTY[btn].split(" (")[0], 13, bold=True, width=110).grid(row=r, column=0, sticky="w",
                                                                                          pady=6)
            self.app.label(bt, m.get("action", ""), 13, "#3b2e24").grid(row=r, column=1, sticky="w", pady=6)
            cell = self.ctk.CTkFrame(bt, fg_color="transparent")
            cell.grid(row=r, column=2, sticky="e", pady=6)
            if self.capturing == btn:
                box = self.ctk.CTkLabel(cell, text="Press a key, or click here with a mouse button",
                                        font=self.app.font(12, bold=True), text_color="#f8efda", fg_color=BLUE,
                                        corner_radius=7, height=30, cursor="hand2")
                box.pack(side="left", padx=(0, 10))
                for n in (1, 2, 3):
                    box.bind(f"<Button-{n}>", lambda e, n=n: self.captured(MOUSE_BUTTONS_TK[n]))
                box.bind("<MouseWheel>", lambda e: self.captured("WHEEL_UP" if e.delta > 0 else "WHEEL_DOWN"))
                self.win.bind("<KeyPress>", self.on_key)
            else:
                if btn in mine:
                    self.app.link(cell, "Reset", lambda b=btn: self.reset(b)).pack(side="left", padx=(0, 12))
                if key and key != "NONE":
                    self.app.keycap(cell, key_label(key)).pack(side="left", padx=(0, 10))
            small = self.app.button(cell, "Cancel" if self.capturing == btn else "Change",
                                    lambda b=btn: self.start_capture(b))
            small.configure(height=30, width=84)
            small.pack(side="left")
            r += 1

    # ------------------------------------------------------------ button changes
    def start_capture(self, btn):
        self.capturing = None if self.capturing == btn else btn
        if self.capturing is None:
            self.win.unbind("<KeyPress>")
        self.render()

    def on_key(self, event):
        k = your_settings.key_from_tk(event.keysym)
        if k:
            self.captured(k)
        return "break"

    def captured(self, key):
        if self.capturing and key in OUTPUT_NAMES:
            self.draft.setdefault("buttons", {})[self.capturing] = key
        self.capturing = None
        self.win.unbind("<KeyPress>")
        self.render()

    def reset(self, btn):
        self.draft.get("buttons", {}).pop(btn, None)
        self.render()

    def reset_all(self):
        self.draft = {}
        self.render()

    def save(self):
        if self.draft:
            self.app.user_settings[self.pid] = self.draft
        else:
            self.app.user_settings.pop(self.pid, None)
        your_settings.save(PROFILE_DIR, self.app.user_settings)
        self.app.status.configure(text="Settings saved. They apply when you go back to the game.")
        self.win.destroy()


MOUSE_BUTTONS_TK = {1: "MOUSE_LEFT", 2: "MOUSE_MIDDLE", 3: "MOUSE_RIGHT"}


class App:
    """The Tapsquatch window: rounded cards and buttons, in the website's colours."""

    def __init__(self):
        import customtkinter as ctk
        import tkinter as tk
        import tkinter.font as tkfont
        self.ctk, self.tk = ctk, tk
        register_fonts()
        if IS_WINDOWS:
            ctypes.windll.winmm.timeBeginPeriod(1)
        ctk.set_appearance_mode("light")
        self.root = ctk.CTk(fg_color=OFF)
        self.root.title("Tapsquatch")
        self.root.geometry("1100x720")
        self.root.minsize(960, 640)
        ico = os.path.join(APP_DIR, "icon.ico")
        if IS_WINDOWS and os.path.isfile(ico):
            self.root.after(200, lambda: self.root.iconbitmap(ico))   # CTk sets its own icon first
        self.body, self.disp = pick_fonts(tkfont)
        try:
            self.ui_scale = ctk.ScalingTracker.get_window_scaling(self.root)
        except Exception:  # noqa: BLE001
            self.ui_scale = 1.0

        pygame.init()
        pygame.joystick.init()
        self.layouts = load_json(LAYOUT_FILE)
        self.profiles = load_profiles()
        self.stamp = profiles_stamp()
        self.out = Output()
        self.pad = None
        self.mapper = None
        self.active_exe = None
        self.next_check = 0.0
        self.next_ui = 0.0
        self.last = time.perf_counter()
        self.state = {n: False for n in BUTTON_NAMES}
        self.sticks = (0.0, 0.0, 0.0, 0.0)
        self.current = None
        self._steam_games = None
        self.lib_status = "Checking the library for new games."
        try:
            self.settings = load_json(os.path.join(APP_DIR, "settings.json"))
        except Exception:  # noqa: BLE001
            self.settings = {}
        self.user_settings = your_settings.load(PROFILE_DIR)
        self.next_sync = time.perf_counter() + 6 * 3600
        threading.Thread(target=self._sync_library, daemon=True).start()

        self._build()
        self.overlay = Overlay(self.root, self.body, self.disp)
        self.pad = self._open_pad()
        self._show_game(None)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.after(4, self.tick)

    # ---------------------------------------------------------------- pieces
    def font(self, size, bold=False, display=False):
        return self.ctk.CTkFont(family=self.disp if display else self.body, size=size,
                                weight="bold" if bold else "normal")

    def label(self, parent, text="", size=13, colour=INK, bold=False, display=False, **kw):
        return self.ctk.CTkLabel(parent, text=text, font=self.font(size, bold, display), text_color=colour,
                                 fg_color="transparent", anchor="w", justify="left", **kw)

    def button(self, parent, text, command, primary=False):
        """Rounded button that inverts on hover, like the website's: background AND text swap."""
        ctk = self.ctk
        bg, fg = (INK, OFF) if primary else (CARD, INK)
        hover_bg, hover_fg = (OFF, INK) if primary else (INK, OFF)

        class InvertButton(ctk.CTkButton):
            # The toolkit swaps the background on hover itself; here the text colour swaps
            # in the same moment, straight on the text label, so it can't be undone.
            def _set_text(self, colour):
                lab = getattr(self, "_text_label", None)
                if lab is not None:
                    lab.configure(fg=colour)

            def _on_enter(self, event=None):
                super()._on_enter(event)
                self._set_text(hover_fg)

            def _on_leave(self, event=None):
                super()._on_leave(event)
                self._set_text(fg)

        return InvertButton(parent, text=text, command=command, fg_color=bg, hover_color=hover_bg,
                            text_color=fg, border_width=2, border_color=INK, corner_radius=9,
                            height=38, font=self.font(13, bold=True))

    def keycap(self, parent, text):
        cap = self.ctk.CTkFrame(parent, fg_color="#f8efda", border_width=1, border_color="#dcc8a4",
                                corner_radius=7)
        self.ctk.CTkLabel(cap, text=text, font=self.font(12, bold=True), text_color=INK,
                          fg_color="transparent", height=22).pack(padx=10, pady=2)
        return cap

    # ---------------------------------------------------------------- layout
    def link(self, parent, text, command):
        """Plain text link for the footer: turns blue and underlines on hover."""
        lab = self.ctk.CTkLabel(parent, text=text, font=self.font(13, bold=True), text_color=INK,
                                fg_color="transparent", cursor="hand2")
        under = self.ctk.CTkFont(family=self.body, size=13, weight="bold", underline=True)
        plain = self.font(13, bold=True)
        lab.bind("<Enter>", lambda e: lab.configure(text_color=BLUE, font=under))
        lab.bind("<Leave>", lambda e: lab.configure(text_color=INK, font=plain))
        lab.bind("<Button-1>", lambda e: command())
        return lab

    def _build(self):
        ctk, tk = self.ctk, self.tk
        try:
            from PIL import Image
            logo = Image.open(os.path.join(ASSETS, "logo-header.png"))
        except Exception:  # noqa: BLE001
            logo = None

        # header: logo, name, version badge | controller icon + connection
        head = ctk.CTkFrame(self.root, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(18, 14))
        if logo:
            self.logo_img = ctk.CTkImage(light_image=logo, size=(44, 34))
            ctk.CTkLabel(head, text="", image=self.logo_img).pack(side="left")
        self.label(head, "Tapsquatch", 20, bold=True, display=True).pack(side="left", padx=(12, 10))
        ctk.CTkLabel(head, text=f"v{APP_VERSION} Beta", font=self.font(12, bold=True), text_color="#f8efda",
                     fg_color=BLUE, corner_radius=6, height=22).pack(side="left")
        self.status = self.label(head, "Looking for a controller", 13, "#4a3b2e")
        self.status.pack(side="right")
        try:
            ctrl_small = Image.open(os.path.join(ASSETS, "controller-small.png"))
        except Exception:
            ctrl_small = None
        if ctrl_small:
            self.status_icon = ctk.CTkImage(light_image=ctrl_small, size=(32, 17))
            ctk.CTkLabel(head, text="", image=self.status_icon).pack(side="right", padx=(0, 8))

        # footer: three main buttons | text links
        foot = ctk.CTkFrame(self.root, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=28, pady=(16, 20))
        for text, cmd, primary in (("Button prompts", self.open_prompts, True),
                                   ("Settings", self.open_settings, False),
                                   ("Make a profile", self.open_maker, False)):
            self.button(foot, text, cmd, primary).pack(side="left", padx=(0, 10))
        self.link(foot, "Help", self.open_help).pack(side="right")
        self.link(foot, "Report a problem", self.report_problem).pack(side="right", padx=(0, 22))
        self.link(foot, "Game profiles", self.open_profiles).pack(side="right", padx=(0, 22))

        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=28)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # left card: live controller
        left = ctk.CTkFrame(main, fg_color=INK, corner_radius=18, width=430)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 18))
        left.pack_propagate(False)
        self.label(left, "Live controller", 13, "#c9b593").pack(fill="x", padx=26, pady=(24, 0))
        s = self.ui_scale
        self.pic_w = int(378 * s)
        self.scale = self.pic_w / 240
        self.cv = tk.Canvas(left, width=self.pic_w, height=int(136 * self.scale), bg=INK, highlightthickness=0)
        self.cv.pack(padx=26, pady=(18, 12))
        try:
            from PIL import Image, ImageTk
            img = Image.open(os.path.join(ASSETS, "controller.png"))
            img = img.resize((self.pic_w, int(img.height * self.pic_w / img.width)), Image.LANCZOS)
            self.ctrl_img = ImageTk.PhotoImage(img)
            self.cv.create_image(0, int(8 * self.scale), image=self.ctrl_img, anchor="nw")
        except Exception:  # noqa: BLE001
            self.cv.create_text(self.pic_w // 2, 100, text="(controller picture missing)", fill=SOFT)
        self.spot_ids = {}
        self.label(left, "Pressed", 13, "#c9b593").pack(fill="x", padx=26, pady=(4, 6))
        self.tags = ctk.CTkFrame(left, fg_color="transparent", height=28)
        self.tags.pack(fill="x", padx=26)
        self._shown_tags = None
        tips = ctk.CTkFrame(left, fg_color="transparent")
        tips.pack(side="bottom", fill="x", padx=26, pady=(0, 22))
        ctk.CTkFrame(tips, fg_color="#3e5a4a", height=1, corner_radius=0).pack(fill="x", pady=(0, 12))
        self.label(tips, "Hold PS in game to see the button list.\nPauses when you Alt+Tab away from the game.",
                   12, "#b09a7c").pack(fill="x")

        # right card: the game and its layout
        right = ctk.CTkFrame(main, fg_color=CARD, corner_radius=18, border_width=1, border_color=LINE)
        right.grid(row=0, column=1, sticky="nsew")
        top = ctk.CTkFrame(right, fg_color="transparent")
        top.pack(fill="x", padx=28, pady=(24, 0))
        self.kicker = self.label(top, "", 13, MUTED)
        self.kicker.pack(side="left")
        self.lib_lbl = self.label(top, "", 12, MUTED)
        self.lib_lbl.pack(side="right")
        self.title = self.label(right, "", 24, bold=True, display=True, wraplength=560)
        self.title.pack(fill="x", padx=28, pady=(4, 0))
        self.sub = self.label(right, "", 13, "#4a3b2e", wraplength=560)
        self.sub.pack(fill="x", padx=28, pady=(6, 12))
        self.heads = ctk.CTkFrame(right, fg_color="transparent")
        self.heads.pack(fill="x", padx=32)
        self.heads.grid_columnconfigure(1, weight=1)
        self.label(self.heads, "Button", 12, MUTED, width=120).grid(row=0, column=0, sticky="w")
        self.label(self.heads, "Action", 12, MUTED).grid(row=0, column=1, sticky="w")
        self.label(self.heads, "PC key", 12, MUTED).grid(row=0, column=2, sticky="e")
        ctk.CTkFrame(right, fg_color=LINE, height=1, corner_radius=0).pack(fill="x", padx=28, pady=(6, 0))
        self.table = ctk.CTkScrollableFrame(right, fg_color="transparent", corner_radius=0)
        self.table.pack(fill="both", expand=True, padx=(22, 8), pady=(0, 10))
        self.table.grid_columnconfigure(1, weight=1)

    def _update_tags(self):
        names = [PRETTY[n].split(" (")[0] for n in BUTTON_NAMES if self.state.get(n)]
        if names == self._shown_tags:
            return
        self._shown_tags = names
        for w in self.tags.winfo_children():
            w.destroy()
        if not names:
            self.label(self.tags, "Nothing", 13, "#7a6650").pack(side="left")
        for n in names[:6]:
            self.ctk.CTkLabel(self.tags, text=n, font=self.font(13, bold=True), text_color="#f8efda",
                              fg_color=BLUE, corner_radius=7, height=26).pack(side="left", padx=(0, 8))

    def _to_px(self, x, y):
        return x * self.scale, (y - 12 + 8) * self.scale

    def _draw_spots(self):
        cv = self.cv
        for name, ids in self.spot_ids.items():
            for i in ids:
                cv.delete(i)
        self.spot_ids = {}
        for name, spot in SPOTS.items():
            if not self.state.get(name):
                continue
            if spot[0] == "o":
                _, cx, cy, r = spot
                x, y = self._to_px(cx, cy)
                rr = r * self.scale
                self.spot_ids[name] = [cv.create_oval(x - rr, y - rr, x + rr, y + rr, fill=BLUE, outline="")]
            else:
                _, x0, y0, x1, y1 = spot
                a, b2 = self._to_px(x0, y0)
                c, e = self._to_px(x1, y1)
                self.spot_ids[name] = [cv.create_rectangle(a, b2, c, e, fill=BLUE, outline="")]
        for key, (cx, cy), (sx, sy) in (("ls", (109, 81), self.sticks[0:2]), ("rs", (131, 81), self.sticks[2:4])):
            if math.hypot(sx, sy) > 0.15:
                x, y = self._to_px(cx + sx * 4.5, cy + sy * 4.5)
                d = 4 * self.ui_scale
                self.spot_ids[key] = [cv.create_oval(x - d, y - d, x + d, y + d, fill=BLUE, outline="")]

    def _row(self, r, first, second, right_widget=None, bold_second=False):
        ctk = self.ctk
        self.label(self.table, first, 14, bold=True, width=120).grid(row=r, column=0, sticky="w", padx=(10, 12),
                                                                     pady=(9, 9))
        self.label(self.table, second, 14, "#3b2e24", bold=bold_second).grid(row=r, column=1, sticky="w")
        if right_widget:
            right_widget.grid(row=r, column=2, sticky="e", padx=(8, 10))
        ctk.CTkFrame(self.table, fg_color="#e2d2ad", height=1, corner_radius=0).grid(
            row=r, column=0, columnspan=3, sticky="sew")

    def _show_game(self, p, report=None):
        ctk = self.ctk
        for w in self.table.winfo_children():
            w.destroy()
        self.lib_lbl.configure(text=self.lib_status)
        if p is None:
            self.heads.pack_forget()
            self.kicker.configure(text="Waiting for a game")
            self.title.configure(text="Start a supported game")
            self.sub.configure(text="When its window is in front, its PlayStation layout switches on here.")
            mine = self._my_supported_games()
            self.label(self.table, "Your games with a layout" if mine else "Games in the library", 12,
                       MUTED).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(12, 4))
            names = mine or sorted({q.get("name", "?") for q in self.profiles.values()})[:14]
            if not names:
                self.label(self.table, "None yet. The library downloads when you're online.", 14).grid(
                    row=1, column=0, columnspan=3, sticky="w", padx=10)
            for i, n in enumerate(names, 1):
                q = next((v for v in self.profiles.values() if v.get("name") == n), {})
                tag = self.label(self.table, f"{q.get('playstation_version', '')} layout".strip(), 12, MUTED)
                self.label(self.table, n, 14, bold=True).grid(row=i * 2 - 1 + 1, column=0, columnspan=2,
                                                              sticky="w", padx=10, pady=9)
                tag.grid(row=i * 2, column=2, sticky="e", padx=10)
                ctk.CTkFrame(self.table, fg_color="#e2d2ad", height=1, corner_radius=0).grid(
                    row=i * 2, column=0, columnspan=3, sticky="sew")
            return
        if not self.heads.winfo_ismapped():
            self.heads.pack(fill="x", padx=32, after=self.sub)
        self.kicker.configure(text="Playing now")
        self.title.configure(text=p.get("name", "Game"))
        ps = p.get("playstation_version", "PlayStation")
        speed = " Push the left stick further to move faster." if \
            p.get("left_stick", {}).get("analog_speed", {}).get("enabled") else ""
        self.sub.configure(text=f"{ps} layout.{speed}")
        r = 0
        for btn in BUTTON_NAMES:
            m = p.get("buttons", {}).get(btn)
            if not m or (as_list(m.get("key")) in ([], ["NONE"]) and (report or {}).get(btn) != "missing"):
                continue
            cell = ctk.CTkFrame(self.table, fg_color="transparent")
            src = (report or {}).get(btn)
            if src in SOURCE_TEXT:
                text, colour = SOURCE_TEXT[src]
                ctk.CTkLabel(cell, text=text, font=self.font(12), text_color=colour,
                             fg_color="transparent").pack(side="left", padx=(0, 10))
            keys = [k for k in as_list(m.get("key")) if k != "NONE"]
            if keys:
                self.keycap(cell, " + ".join(key_label(k) for k in keys)).pack(side="left")
            self._row(r, PRETTY[btn].split(" (")[0], m.get("action", ""), cell)
            r += 1

    # --------------------------------------------------------------- actions
    def open_prompts(self):
        import subprocess
        exe = os.path.join(APP_DIR, "Tapsquatch Prompts.exe")
        if os.path.isfile(exe):
            os.startfile(exe)
        else:
            subprocess.Popen([sys.executable, os.path.join(APP_DIR, "prompts_patcher.py")],
                             creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))

    def open_maker(self):
        import subprocess
        exe = os.path.join(APP_DIR, "Tapsquatch Profile Maker.exe")
        if os.path.isfile(exe):
            os.startfile(exe)
        else:
            subprocess.Popen([sys.executable, os.path.join(APP_DIR, "profile_maker.py")],
                             creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))

    def open_settings(self):
        if getattr(self, "settings_win", None) is not None:
            try:
                if self.settings_win.win.winfo_exists():
                    self.settings_win.win.lift()
                    return
            except Exception:  # noqa: BLE001
                pass
        self.settings_win = SettingsWindow(self)

    def open_profiles(self):
        if IS_WINDOWS:
            os.startfile(PROFILE_DIR)

    def report_problem(self):
        p = self.current or next(iter(self.profiles.values()), None)
        if p:
            webbrowser.open(library.report_url(p))
        else:
            webbrowser.open(library.ISSUES_URL)

    def _sync_library(self):
        try:
            count, updated = library.sync(PROFILE_DIR, self.settings.get("library_url", library.LIBRARY_BASE))
            self.lib_status = f"Library: {count} games" + (f", {updated} new or updated." if updated else ", up to date.")
        except Exception:  # noqa: BLE001
            self.lib_status = "Library: offline, using saved layouts."
        self._steam_games = None      # look again now the library may have grown

    def _my_supported_games(self):
        if self._steam_games is None:
            try:
                self._steam_games = installed_steam_games(steam_libraries)
            except Exception:  # noqa: BLE001
                self._steam_games = []
        names = set()
        exes = {q.get("name"): [e.lower() for e in q.get("exe", [])] for q in self.profiles.values()}
        ids = {str(q.get("steam_appid")): q.get("name") for q in self.profiles.values() if q.get("steam_appid")}
        for g in self._steam_games:
            if g["appid"] in ids:
                names.add(ids[g["appid"]])
                continue
            if not os.path.isdir(g["folder"]):
                continue
            here = {f.lower() for _, fs in _walk2(g["folder"]) for f in fs if f.lower().endswith(".exe")}
            for name, ex in exes.items():
                if here & set(ex):
                    names.add(name)
        return sorted(names)

    def open_help(self):
        if IS_WINDOWS:
            os.startfile(os.path.join(APP_DIR, "README.txt"))

    # ------------------------------------------------------------ main loop
    def _open_pad(self):
        for i in range(pygame.joystick.get_count()):
            js = pygame.joystick.Joystick(i)
            js.init()
            pad = Pad(js, self.layouts)
            self.status.configure(text=f"{pad.name.replace(' Wireless Controller', '')} connected", text_color="#4a3b2e")
            return pad
        self.status.configure(text="No controller found. Plug in or pair your DualSense.", text_color=MUTED)
        return None

    def tick(self):
        now = time.perf_counter()
        dt = min(0.05, now - self.last)
        self.last = now
        try:
            for ev in pygame.event.get():
                if ev.type == pygame.JOYDEVICEADDED and self.pad is None:
                    self.pad = self._open_pad()
                elif ev.type == pygame.JOYDEVICEREMOVED and self.pad and \
                        self.pad.js.get_instance_id() == ev.instance_id:
                    self._stop_mapper()
                    self.pad = self._open_pad()

            if now >= self.next_check:
                self.next_check = now + 0.25
                if profiles_stamp() != self.stamp and self.mapper is None:
                    self.stamp = profiles_stamp()           # new layouts: load them, but only
                    self.profiles = load_profiles()         # while no game is being played
                    self._stop_mapper()
                if now >= self.next_sync and self.mapper is None:
                    self.next_sync = now + 6 * 3600
                    threading.Thread(target=self._sync_library, daemon=True).start()
                exe = foreground_exe()
                if exe == "__self__":
                    exe = None                      # Tapsquatch itself is in front: pause
                if exe != self.active_exe:
                    self._stop_mapper()
                    self.active_exe = exe
                    if exe in self.profiles and self.pad:
                        resolved, report = resolve_profile(self.profiles[exe], FOREGROUND_PATH[0])
                        resolved, report = your_settings.apply(resolved, report, self.user_settings)
                        self.current = resolved
                        self.mapper = Mapper(resolved, self.out)
                        self._show_game(resolved, report)
                        self.overlay.set_profile(resolved)

            if self.pad:
                self.state, self.sticks, _ = self.pad.read()
                if self.mapper:
                    self.mapper.update(self.state, self.sticks, dt, now)
                    self.overlay.show(self.state.get(self.mapper.p.get("overlay_button", "ps"), False))
            self.out.tick(now)

            if self.mapper is None and getattr(self, "_shown_status", None) != self.lib_status:
                self._shown_status = self.lib_status
                self._show_game(None)
            if now >= self.next_ui:
                self.next_ui = now + 0.05
                self._draw_spots()
                self._update_tags()
        except Exception as e:  # noqa: BLE001
            self.status.configure(text=f"Problem: {e}", text_color="#b3261e")
        self.root.after(4, self.tick)

    def _stop_mapper(self):
        self.current = None
        if self.mapper:
            self.mapper.stop()
            self.mapper = None
        self.out.release_all()
        self.overlay.show(False)
        self.active_exe = None
        self._show_game(None)

    def quit(self):
        try:
            self._stop_mapper()
        finally:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        try:
            import tkinter.messagebox as mb
            mb.showerror("Tapsquatch", f"Something went wrong:\n{e}")
        except Exception:  # noqa: BLE001
            print(f"Something went wrong: {e}")
