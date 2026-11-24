"""
ControlBridge - the shared online game library.

The library lives in the public GitHub project
madebysilverback/controlbridge-profiles. It is filled automatically by the
profile factory. On start, ControlBridge downloads the index and any profile
that is new or changed into profiles/library/.

Profiles in profiles/ itself (your own, or made with the Profile Maker)
always win over library ones for the same game.
"""

import hashlib
import json
import os
import urllib.parse
import urllib.request

LIBRARY_BASE = "https://raw.githubusercontent.com/madebysilverback/controlbridge-profiles/main/library/"
ISSUES_URL = "https://github.com/madebysilverback/controlbridge-profiles/issues/new"
AGENT = "ControlBridge/0.7 (+https://madebysilverback.com)"


def _get(url, timeout=20):
    if url.startswith("file://") or os.path.isabs(url):
        path = url[7:] if url.startswith("file://") else url
        with open(path, "rb") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def sync(profile_dir, base=LIBRARY_BASE):
    """Download new/changed library profiles. Returns (games_in_library, files_updated)."""
    lib_dir = os.path.join(profile_dir, "library")
    os.makedirs(lib_dir, exist_ok=True)
    index = json.loads(_get(base.rstrip("/") + "/index.json").decode("utf-8"))
    entries = index.get("profiles", [])
    updated = 0
    keep = set()
    for e in entries:
        name = os.path.basename(e["file"])
        if not name.endswith(".json"):
            continue
        keep.add(name)
        dest = os.path.join(lib_dir, name)
        if os.path.isfile(dest):
            with open(dest, "rb") as f:
                if hashlib.sha256(f.read()).hexdigest() == e.get("sha256"):
                    continue
        data = _get(base.rstrip("/") + "/" + e["file"])
        if e.get("sha256") and hashlib.sha256(data).hexdigest() != e["sha256"]:
            continue                      # damaged download: skip, try next time
        json.loads(data.decode("utf-8"))   # must be valid JSON
        with open(dest + ".tmp", "wb") as f:
            f.write(data)
        os.replace(dest + ".tmp", dest)
        updated += 1
    for fn in os.listdir(lib_dir):        # profiles removed from the library
        if fn.endswith(".json") and fn not in keep:
            os.remove(os.path.join(lib_dir, fn))
    with open(os.path.join(lib_dir, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f)
    return len(entries), updated


def report_url(profile, button_hint=""):
    """A ready-filled GitHub post for 'a button is wrong'."""
    pid = profile.get("id") or os.path.splitext(os.path.basename(profile.get("_file", "")))[0]
    title = f"Wrong button: {profile.get('name', 'game')}"
    body = (f"profile: {pid}\n"
            f"game: {profile.get('name', '')}\n"
            f"profile version: {profile.get('updated', 'local')}\n\n"
            f"Which button is wrong? {button_hint}\n\n"
            "What does it do now, and what should it do?\n")
    q = urllib.parse.urlencode({"template": "wrong-button.md", "labels": "wrong-button", "title": title, "body": body})
    return f"{ISSUES_URL}?{q}"


def share_url(profile):
    """A ready-filled GitHub post that offers a profile to the library."""
    text = json.dumps(profile, indent=1)
    body = ("A profile made with the ControlBridge Profile Maker.\n\n"
            f"```json\n{text}\n```\n")
    q = urllib.parse.urlencode({"template": "new-profile.md", "labels": "new-profile",
                                "title": f"New profile: {profile.get('name', '')}", "body": body})
    url = f"{ISSUES_URL}?{q}"
    return url if len(url) < 7800 else None    # too long for a link: copy and paste instead
