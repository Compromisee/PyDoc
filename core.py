#!/usr/bin/env python3
"""
PyDoc · core
====================
All the pure (GUI-free) logic so it can be unit-tested headless and reused by
the pywebview host:

  * single-folder shortcut scanning  + custom shortcuts.json
  * unified metadata store (pin / group / alias / per-item hotkey / usage)
  * fuzzy search with usage (frequency + recency) ranking
  * inline calculator (safe AST eval)
  * inline web-search / open-URL suggestions
  * Windows auto-start (HKCU ...\\Run)
  * launching targets cross-platform
"""

import os
import re
import ast
import sys
import json
import time
import math
import operator
import subprocess

# --------------------------------------------------------------------------- #
#  App metadata
# --------------------------------------------------------------------------- #
APP_NAME    = "PyDoc"
APP_VERSION = "1.0.0"
APP_CHANNEL = "Stable"
APP_TITLE   = f"{APP_NAME} v{APP_VERSION} {APP_CHANNEL}"   # PyDoc v1.0.0 Stable

# --------------------------------------------------------------------------- #
#  Paths
#  When frozen by PyInstaller, read-only bundled assets (web/, themes.json)
#  live in sys._MEIPASS, while user data (config, shortcuts, profiles, …) must
#  live next to the executable so it persists across runs.
# --------------------------------------------------------------------------- #
if getattr(sys, "frozen", False):
    DATA_DIR  = os.path.dirname(sys.executable)          # writable, next to .exe
    BUNDLE_DIR = getattr(sys, "_MEIPASS", DATA_DIR)      # read-only bundle
else:
    DATA_DIR  = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = DATA_DIR
APP_DIR      = DATA_DIR

SHORTCUT_DIR = os.path.join(DATA_DIR, "Shortcuts")
WEB_DIR      = os.path.join(BUNDLE_DIR, "web")          # bundled front-end
ICON_DIR     = os.path.join(DATA_DIR, "Icons")          # downloaded/custom icons
SHOT_DIR     = os.path.join(DATA_DIR, "Screenshots")    # saved screen captures
CONFIG_PATH  = os.path.join(DATA_DIR, "config.json")
# prefer a user themes.json; fall back to the bundled default
THEMES_PATH  = os.path.join(DATA_DIR, "themes.json")
if not os.path.exists(THEMES_PATH) and os.path.exists(os.path.join(BUNDLE_DIR, "themes.json")):
    THEMES_PATH = os.path.join(BUNDLE_DIR, "themes.json")
PROFILES_DIR = os.path.join(DATA_DIR, "Profiles")       # per-password data lives here

# These four are the ACTIVE profile's data paths. They start on the default
# profile and are reassigned by activate_profile() when an alternate or secret
# password is used to unlock. core functions read them as globals at call time.
CUSTOM_PATH  = os.path.join(APP_DIR, "shortcuts.json")
STORE_PATH   = os.path.join(APP_DIR, "store.json")
CMDHIST_PATH = os.path.join(APP_DIR, "cmd_history.json")   # pinned cmds persist here

# remember the default-profile paths so we can switch back
_DEFAULT_SHORTCUT_DIR = SHORTCUT_DIR
_DEFAULT_CUSTOM_PATH  = CUSTOM_PATH
_DEFAULT_STORE_PATH   = STORE_PATH
_DEFAULT_CMDHIST_PATH = CMDHIST_PATH
ACTIVE_PROFILE = "default"

QLLINK_EXT   = ".qllink"   # tiny JSON link file we drop into Shortcuts/
MAX_PROFILES = 10          # alternate password-protected profiles

# --------------------------------------------------------------------------- #
#  Defaults
# --------------------------------------------------------------------------- #
DEFAULT_THEMES = {
    "Windows 11 Dark":  {"mode": "dark",  "primary": "#4cc2ff"},
    "Windows 11 Light": {"mode": "light", "primary": "#0067c0"},
    "Graphite":         {"mode": "dark",  "primary": "#9aa0a6"},
    "Nord":             {"mode": "dark",  "primary": "#88c0d0"},
    "Mint":             {"mode": "dark",  "primary": "#34d399"},
    "Sunset":           {"mode": "dark",  "primary": "#fb923c"},
}

DEFAULT_CONFIG = {
    "theme": "Windows 11 Dark",
    "hotkey": "ctrl+windows+n",        # open / toggle the launcher (Win+Ctrl+N)
    "hotkey_add": "ctrl+windows+a",    # open the "add shortcut" form
    "show_path_subtext": True,
    "autostart": True,                 # run as a background tray app by default
    "show_on_launch": False,           # start hidden in the tray
    "hide_on_blur": True,              # close/hide the window when it loses focus
    "max_results": 9,
    "enable_calculator": True,
    "enable_websearch": True,
    "enable_screenshot": True,          # show screenshot actions in results
    "hotkey_screenshot": "ctrl+windows+s",   # global region-capture hotkey
    "screenshot_copy": True,            # also copy captures to the clipboard
    "enable_runcmd": True,              # show the "Run command" action
    "hotkey_runcmd": "ctrl+windows+r",  # global hotkey to open the command runner
    "cmd_autocorrect": True,            # suggest fixes for typo'd commands
    "cmd_shell": "",                    # "" = auto (cmd/powershell/sh); or a shell path
    "web_search_url": "https://www.google.com/search?q={q}",
    "active_group": "All",
    "lock_enabled": False,              # require a password to search/launch
    "lock_hash": "",                   # sha256(salt + main password)  (default profile)
    "lock_salt": "",
    "master_hash": "",                 # sha256(salt + master password) — recovery
    "master_salt": "",
    "profiles": [],                    # list of alternate profiles (see add_profile)
    "secret": {},                      # the single hidden "secret" profile
    "clear_on_hide": True,             # clear the search box each time it hides
    "max_recent": 6,                   # recent/frequent items shown on empty search
}

DEFAULT_CUSTOM = {
    "_comment": "Base definition for custom shortcuts. Extra metadata "
                "(pinned/group/alias/hotkey/usage) lives in store.json and is "
                "editable from the in-app Settings window.",
    "shortcuts": [
        {"name": "Google",                "target": "https://www.google.com", "image": "ms:language"},
        {"name": "Calculator",            "target": "calc",                   "image": "ms:calculate"},
        {"name": "Open Shortcuts Folder", "target": "@open_shortcut_folder",  "image": "ms:folder"},
    ],
}

DEFAULT_STORE = {"usage": {}, "meta": {}}

# Default icons: Google Material Symbol ligature names (rendered with the
# bundled font, prefixed "ms:" in image strings). No emojis anywhere.
ICONS_BY_EXT = {
    ".exe": "rocket_launch", ".lnk": "link", ".url": "language", ".bat": "terminal",
    ".cmd": "terminal", ".ps1": "terminal", ".sh": "terminal", ".py": "code",
    ".js": "code", ".html": "code", ".css": "code", ".json": "data_object",
    ".txt": "description", ".md": "article", ".pdf": "picture_as_pdf",
    ".doc": "description", ".docx": "description", ".xls": "table_chart",
    ".xlsx": "table_chart", ".ppt": "slideshow", ".pptx": "slideshow",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
    ".svg": "image", ".webp": "image", ".ico": "image",
    ".mp3": "music_note", ".wav": "music_note", ".flac": "music_note",
    ".mp4": "movie", ".mkv": "movie", ".avi": "movie", ".mov": "movie",
    ".zip": "folder_zip", ".rar": "folder_zip", ".7z": "folder_zip",
}
DEFAULT_FILE_ICON = "draft"
FOLDER_ICON = "folder"
URL_ICON = "language"


# --------------------------------------------------------------------------- #
#  JSON helpers
# --------------------------------------------------------------------------- #
def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return json.loads(json.dumps(default))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return json.loads(json.dumps(default))


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return True
    except Exception as exc:
        print(f"[PyDoc] save error ({path}): {exc}")
        return False


# --------------------------------------------------------------------------- #
#  Auto-start on Windows login
# --------------------------------------------------------------------------- #
RUN_KEY   = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "PyDoc"


def _autostart_command():
    # When frozen, autostart the .exe directly; otherwise pythonw launcher.py
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.join(APP_DIR, "launcher.py")
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    return f'"{exe}" "{script}"'


def is_autostart_enabled():
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg  # type: ignore
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            val, _ = winreg.QueryValueEx(key, RUN_VALUE)
            return bool(val)
    except Exception:
        return False


def set_autostart(enable):
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg  # type: ignore
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ,
                                  _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except FileNotFoundError:
                    pass
        return True
    except Exception as exc:
        print(f"[PyDoc] autostart error: {exc}")
        return False


# --------------------------------------------------------------------------- #
#  Password lock + profiles  (sha256 with per-entry salt; stored in config.json)
#
#  Profiles let one password reveal one set of shortcuts and another password
#  reveal a completely different set:
#    * default profile  -> Shortcuts/ , shortcuts.json , store.json
#    * alternate profile -> Profiles/<id>/ (up to MAX_PROFILES)
#    * secret profile    -> Profiles/__secret__/  (hidden; for sensitive links)
#  Each profile has its own folder, custom-shortcuts file, store + cmd history.
# --------------------------------------------------------------------------- #
def _hash_password(password, salt):
    import hashlib
    return hashlib.sha256((salt + (password or "")).encode("utf-8")).hexdigest()


def _new_salt():
    import secrets
    return secrets.token_hex(16)


def _profile_paths(pid):
    """Return the data paths for a profile id ('default' or a profile id)."""
    if pid == "default":
        return {"dir": _DEFAULT_SHORTCUT_DIR, "custom": _DEFAULT_CUSTOM_PATH,
                "store": _DEFAULT_STORE_PATH, "cmd": _DEFAULT_CMDHIST_PATH}
    base = os.path.join(PROFILES_DIR, pid)
    return {"dir": os.path.join(base, "Shortcuts"),
            "custom": os.path.join(base, "shortcuts.json"),
            "store": os.path.join(base, "store.json"),
            "cmd": os.path.join(base, "cmd_history.json")}


def activate_profile(pid):
    """Point the active data globals at the given profile and create its dirs."""
    global SHORTCUT_DIR, CUSTOM_PATH, STORE_PATH, CMDHIST_PATH, ACTIVE_PROFILE
    p = _profile_paths(pid)
    os.makedirs(p["dir"], exist_ok=True)
    SHORTCUT_DIR = p["dir"]
    CUSTOM_PATH  = p["custom"]
    STORE_PATH   = p["store"]
    CMDHIST_PATH = p["cmd"]
    ACTIVE_PROFILE = pid
    invalidate_cache()
    clear_session_history()
    return pid


# ---- main (default) password ---------------------------------------------
PIN_LENGTH = 6   # all passwords are exactly 6 digits


def _valid_pin(password):
    return bool(re.fullmatch(r"\d{%d}" % PIN_LENGTH, password or ""))


def password_in_use(password, exclude=None):
    """Return True if this exact 6-digit code already guards another space.
    `exclude` is an id/kind to skip: 'default', 'master', or a profile id."""
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    import hmac

    def matches(salt, h):
        return bool(h) and hmac.compare_digest(_hash_password(password, salt), h)

    if exclude != "default" and matches(cfg.get("lock_salt", ""), cfg.get("lock_hash", "")):
        return True
    if exclude != "master" and matches(cfg.get("master_salt", ""), cfg.get("master_hash", "")):
        return True
    for p in cfg.get("profiles", []):
        if p.get("id") == exclude:
            continue
        if matches(p.get("salt", ""), p.get("hash", "")):
            return True
    sec = cfg.get("secret", {})
    if exclude != "__secret__" and matches(sec.get("salt", ""), sec.get("hash", "")):
        return True
    return False


def set_lock_password(password):
    """Set the main 6-digit code. Returns {'ok':bool, 'error':str}."""
    if not _valid_pin(password):
        return {"ok": False, "error": "Password must be exactly 6 digits."}
    if password_in_use(password, exclude="default"):
        return {"ok": False, "error": "That code is already used by another space."}
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    salt = _new_salt()
    cfg["lock_salt"] = salt
    cfg["lock_hash"] = _hash_password(password, salt)
    cfg["lock_enabled"] = True
    save_json(CONFIG_PATH, cfg)
    return {"ok": True}


def disable_lock(password):
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    if not cfg.get("lock_enabled"):
        return True
    if not (verify_password(password) or verify_master(password)):
        return False
    cfg["lock_enabled"] = False
    cfg["lock_hash"] = ""
    cfg["lock_salt"] = ""
    save_json(CONFIG_PATH, cfg)
    return True


def verify_password(password):
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    if not cfg.get("lock_enabled"):
        return True
    expected = cfg.get("lock_hash", "")
    if not expected:
        return True
    import hmac
    return hmac.compare_digest(_hash_password(password, cfg.get("lock_salt", "")),
                               expected)


def is_locked():
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    return bool(cfg.get("lock_enabled") and cfg.get("lock_hash"))


# ---- master (recovery) password ------------------------------------------
def set_master_password(password):
    if not _valid_pin(password):
        return {"ok": False, "error": "Master code must be exactly 6 digits."}
    if password_in_use(password, exclude="master"):
        return {"ok": False, "error": "That code is already used by another space."}
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    salt = _new_salt()
    cfg["master_salt"] = salt
    cfg["master_hash"] = _hash_password(password, salt)
    save_json(CONFIG_PATH, cfg)
    return {"ok": True}


def has_master():
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    return bool(cfg.get("master_hash"))


def verify_master(password):
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    expected = cfg.get("master_hash", "")
    if not expected:
        return False
    import hmac
    return hmac.compare_digest(_hash_password(password, cfg.get("master_salt", "")),
                               expected)


# ---- alternate + secret profiles -----------------------------------------
def list_profiles():
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    return cfg.get("profiles", [])


def add_profile(name, password, secret=False):
    """Create an alternate (or the secret) profile guarded by its own 6-digit
    code. Returns {'ok':bool, 'id':str, 'error':str}."""
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    if not name:
        return {"ok": False, "error": "Name is required."}
    if not _valid_pin(password):
        return {"ok": False, "error": "Code must be exactly 6 digits."}
    if password_in_use(password):
        return {"ok": False, "error": "That code is already used by another space."}
    salt = _new_salt()
    rec = {"name": name, "salt": salt, "hash": _hash_password(password, salt)}
    if secret:
        rec["id"] = "__secret__"
        cfg["secret"] = rec
    else:
        profiles = cfg.get("profiles", [])
        if len(profiles) >= MAX_PROFILES:
            return {"ok": False, "error": f"Limit reached (max {MAX_PROFILES})."}
        # unique id
        existing = {p["id"] for p in profiles}
        i = 1
        while f"profile{i}" in existing:
            i += 1
        rec["id"] = f"profile{i}"
        profiles.append(rec)
        cfg["profiles"] = profiles
    save_json(CONFIG_PATH, cfg)
    os.makedirs(_profile_paths(rec["id"])["dir"], exist_ok=True)
    return {"ok": True, "id": rec["id"]}


def delete_profile(pid):
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    if pid == "__secret__":
        cfg["secret"] = {}
    else:
        cfg["profiles"] = [p for p in cfg.get("profiles", []) if p["id"] != pid]
    save_json(CONFIG_PATH, cfg)
    return True


def resolve_password(password):
    """Figure out which profile a typed password unlocks.
    Returns (kind, profile_id):
      kind in {'default','profile','secret','master', None}
      None  -> password did not match anything."""
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    import hmac
    # default / main
    if cfg.get("lock_hash") and hmac.compare_digest(
            _hash_password(password, cfg.get("lock_salt", "")), cfg["lock_hash"]):
        return ("default", "default")
    # alternate profiles
    for p in cfg.get("profiles", []):
        if hmac.compare_digest(_hash_password(password, p.get("salt", "")),
                               p.get("hash", "")):
            return ("profile", p["id"])
    # secret
    sec = cfg.get("secret", {})
    if sec.get("hash") and hmac.compare_digest(
            _hash_password(password, sec.get("salt", "")), sec["hash"]):
        return ("secret", "__secret__")
    # master (recovery) — unlocks the default profile
    if cfg.get("master_hash") and hmac.compare_digest(
            _hash_password(password, cfg.get("master_salt", "")), cfg["master_hash"]):
        return ("master", "default")
    return (None, None)


# --------------------------------------------------------------------------- #
#  Safe inline calculator
# --------------------------------------------------------------------------- #
_ALLOWED_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_ALLOWED_FUNCS = {
    k: getattr(math, k) for k in (
        "sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log2",
        "log10", "exp", "floor", "ceil", "factorial", "degrees", "radians",
    )
}
_ALLOWED_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max})
_ALLOWED_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("bad constant")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN:
        return _ALLOWED_BIN[type(node.op)](_eval_node(node.left),
                                           _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Name) and node.id in _ALLOWED_NAMES:
        return _ALLOWED_NAMES[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in _ALLOWED_FUNCS:
        args = [_eval_node(a) for a in node.args]
        return _ALLOWED_FUNCS[node.func.id](*args)
    raise ValueError("unsupported expression")


def try_calculate(text):
    """Return a formatted result string, or None if not a math expression."""
    s = text.strip()
    if not s:
        return None
    # must contain a digit and only calculator-safe characters
    if not re.search(r"\d", s):
        return None
    if not re.fullmatch(r"[0-9a-z.,_%\s+\-*/().^]+", s, re.IGNORECASE):
        return None
    expr = s.replace("^", "**").replace(",", "")
    # turn "50%" into "(50/100)"
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", expr)
    try:
        tree = ast.parse(expr, mode="eval")
        val = _eval_node(tree)
    except Exception:
        return None
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val))
        return f"{val:.10g}"
    return str(val)


# --------------------------------------------------------------------------- #
#  Fuzzy scoring
# --------------------------------------------------------------------------- #
def fuzzy_score(query, text):
    q = (query or "").lower()
    t = (text or "").lower()
    if not q:
        return 0
    if t == q:
        return 1000
    if t.startswith(q):
        return 800 - len(t)
    if q in t:
        return 600 - t.index(q)
    qi, score, last = 0, 0, -1
    for i, ch in enumerate(t):
        if qi < len(q) and ch == q[qi]:
            score += 10 - min(9, i - last - 1)
            last = i
            qi += 1
    if qi == len(q):
        return 100 + score
    return None


# --------------------------------------------------------------------------- #
#  Shortcut model + collection
# --------------------------------------------------------------------------- #
def _key_for_file(path):
    return "file:" + os.path.abspath(path)


def _key_for_custom(name):
    return "custom:" + name


class Shortcut:
    def __init__(self, key, name, target, icon="•", subtext="", source="file",
                 image="", removable=False, file_path=""):
        self.key = key
        self.name = name
        self.target = target
        self.icon = icon or ""          # legacy text fallback (unused for icons now)
        self.image = image or ""        # ms:<name> | file:<name> | url | path
        self.subtext = subtext
        self.source = source            # "file" | "custom" | "qllink" | "child"
        self.removable = removable      # can the launcher delete it directly?
        self.file_path = file_path      # backing file (for qllink / file items)
        self.parent = ""                # parent key for child (folder content) items
        # metadata (filled from store)
        self.pinned = False
        self.group = ""
        self.alias = ""
        self.hotkey = ""
        self.count = 0
        self.last = 0

    def to_dict(self):
        return {
            "key": self.key, "name": self.name, "target": self.target,
            "icon": self.icon, "image": resolve_image(self.image),
            "image_raw": self.image, "subtext": self.subtext,
            "source": self.source, "removable": self.removable,
            "pinned": self.pinned, "group": self.group, "alias": self.alias,
            "hotkey": self.hotkey, "count": self.count, "last": self.last,
        }


_SCAN_CACHE = {"items": None, "time": 0.0}
_SCAN_TTL = 1.5   # seconds; keeps typing snappy by not re-scanning disk per keystroke


def invalidate_cache():
    _SCAN_CACHE["items"] = None
    _SCAN_CACHE["time"] = 0.0


def collect_shortcuts(force=False):
    """Cached wrapper around the disk scan so rapid searches stay snappy."""
    now = time.time()
    if (not force and _SCAN_CACHE["items"] is not None
            and (now - _SCAN_CACHE["time"]) < _SCAN_TTL):
        return _SCAN_CACHE["items"]
    items = _scan_shortcuts()
    _SCAN_CACHE["items"] = items
    _SCAN_CACHE["time"] = now
    return items


def _scan_shortcuts():
    """Scan ONLY the Shortcuts folder + shortcuts.json, merge metadata.

    If a shortcut points at a FOLDER, the files directly inside that folder
    are also surfaced as child entries (so a single folder shortcut exposes
    its contents in the launcher).
    """
    store = load_json(STORE_PATH, DEFAULT_STORE)
    usage = store.get("usage", {})
    meta  = store.get("meta", {})
    items = []
    os.makedirs(SHORTCUT_DIR, exist_ok=True)

    # 1) files in the single folder
    try:
        for entry in sorted(os.listdir(SHORTCUT_DIR)):
            if entry.lower() in ("readme.txt", "desktop.ini", ".gitkeep"):
                continue
            full = os.path.join(SHORTCUT_DIR, entry)
            name, ext = os.path.splitext(entry)
            ext = ext.lower()

            if ext == QLLINK_EXT:
                # tiny JSON link file we created (drag-and-drop or "add")
                data = load_json(full, {})
                disp = data.get("name") or name
                target = data.get("target", "")
                image = data.get("image", "") or _guess_image(target)
                items.append(Shortcut(_key_for_file(full), disp, target, "",
                                      subtext=target, source="qllink",
                                      image=image, removable=True,
                                      file_path=full))
                # expand folder targets -> show files inside
                if os.path.isdir(target):
                    items.extend(_expand_folder(target, disp, _key_for_file(full)))
                continue

            if os.path.isdir(full):
                image, disp = "ms:" + FOLDER_ICON, entry
                items.append(Shortcut(_key_for_file(full), disp, full, "",
                                      subtext=full, source="file",
                                      image=image, removable=True, file_path=full))
                items.extend(_expand_folder(full, disp, _key_for_file(full)))
            else:
                image = "ms:" + ICONS_BY_EXT.get(ext, DEFAULT_FILE_ICON)
                disp = name if ext else entry
                items.append(Shortcut(_key_for_file(full), disp, full, "",
                                      subtext=full, source="file",
                                      image=image, removable=True, file_path=full))
    except Exception as exc:
        print(f"[PyDoc] scan error: {exc}")

    # 2) custom entries
    custom = load_json(CUSTOM_PATH, DEFAULT_CUSTOM)
    for sc in custom.get("shortcuts", []):
        if not isinstance(sc, dict):
            continue
        name, target = sc.get("name"), sc.get("target")
        if not name or not target:
            continue
        sub = SHORTCUT_DIR if target == "@open_shortcut_folder" else target
        image = sc.get("image", "") or _guess_image(target)
        items.append(Shortcut(_key_for_custom(name), name, target,
                              "", subtext=sub, source="custom",
                              image=image, removable=True))
        if target not in ("@open_shortcut_folder",) and os.path.isdir(target):
            items.extend(_expand_folder(target, name, _key_for_custom(name)))

    # 3) merge metadata + usage (store can override icon/image too)
    for it in items:
        m = meta.get(it.key, {})
        it.pinned = bool(m.get("pinned", False))
        it.group  = m.get("group", "") or ""
        it.alias  = m.get("alias", "") or ""
        it.hotkey = m.get("hotkey", "") or ""
        if m.get("image"):
            it.image = m["image"]
        u = usage.get(it.key, {})
        it.count = int(u.get("count", 0))
        it.last  = float(u.get("last", 0))

    return items


def _expand_folder(folder, parent_name, parent_key, limit=200):
    """Return child Shortcut entries for files directly inside a folder."""
    out = []
    try:
        for child in sorted(os.listdir(folder))[:limit]:
            cfull = os.path.join(folder, child)
            cname, cext = os.path.splitext(child)
            cext = cext.lower()
            if os.path.isdir(cfull):
                image = "ms:" + FOLDER_ICON
                disp = child
            else:
                image = "ms:" + ICONS_BY_EXT.get(cext, DEFAULT_FILE_ICON)
                disp = cname if cext else child
            sc = Shortcut("child:" + os.path.abspath(cfull), disp, cfull, "",
                          subtext=f"{parent_name} › {child}", source="child",
                          image=image, removable=False, file_path=cfull)
            sc.parent = parent_key
            out.append(sc)
    except Exception as exc:
        print(f"[PyDoc] folder expand error: {exc}")
    return out


def _guess_image(target):
    """Pick a Material-symbol image string for a target path/URL."""
    if not target:
        return "ms:" + DEFAULT_FILE_ICON
    if target == "@open_shortcut_folder":
        return "ms:" + FOLDER_ICON
    if target.startswith(("http://", "https://")):
        return "ms:" + URL_ICON
    if os.path.isdir(target):
        return "ms:" + FOLDER_ICON
    ext = os.path.splitext(target)[1].lower()
    return "ms:" + ICONS_BY_EXT.get(ext, DEFAULT_FILE_ICON)


def _guess_icon(target):
    """Back-compat: return a Material symbol name for a target."""
    return _guess_image(target)[3:]


def all_groups(items):
    groups = sorted({it.group for it in items if it.group})
    return ["All"] + groups


def search_items(query, items, config):
    """Return (results, special) where results are dicts and special holds
    calculator / web-search suggestions."""
    q = (query or "").strip()
    now = time.time()

    def rank(it, base):
        # frequency + recency boost
        freq = math.log1p(it.count) * 30
        rec = 0
        if it.last:
            age_h = (now - it.last) / 3600.0
            rec = max(0, 40 - age_h) if age_h < 40 else 0
        pin = 5000 if it.pinned else 0
        child_pen = -25 if it.source == "child" else 0   # folder contents rank below top-level
        return base + freq + rec + pin + child_pen

    if not q:
        # don't flood the empty view with every folder's children
        scored = [(rank(it, 0), it) for it in items if it.source != "child"]
    else:
        scored = []
        for it in items:
            base = fuzzy_score(q, it.name)
            if it.alias:
                a = fuzzy_score(q, it.alias)
                if a is not None:
                    a += 200  # alias matches are strong
                    base = a if base is None else max(base, a)
            if base is None:
                b2 = fuzzy_score(q, os.path.basename(it.subtext))
                if b2 is None:
                    continue
                base = b2 - 50
            scored.append((rank(it, base), it))

    scored.sort(key=lambda x: (-x[0], x[1].name.lower()))
    results = [it.to_dict() for _, it in scored]

    special = []
    # calculator
    if config.get("enable_calculator", True):
        res = try_calculate(q)
        if res is not None and res != q:
            special.append({
                "key": "calc", "name": f"{q} = {res}", "target": res,
                "image": "ms:calculate", "subtext": "Calculator · Enter to copy",
                "kind": "calc", "value": res,
            })
    # screenshot actions (typed)
    if config.get("enable_screenshot", True) and q:
        ql = q.lower()
        if any(ql.startswith(w[:len(ql)]) and len(ql) >= 3
               for w in ("screenshot", "snip", "capture", "screen grab")):
            special.append({"key": "shot:region", "name": "Screenshot — select a region",
                            "target": "region", "image": "ms:screenshot_region", "kind": "shot",
                            "subtext": "Snip an area (saved + copied)"})
            special.append({"key": "shot:full", "name": "Screenshot — whole screen",
                            "target": "full", "image": "ms:fullscreen", "kind": "shot",
                            "subtext": "Capture all monitors"})
            special.append({"key": "shot:window", "name": "Screenshot — active window",
                            "target": "window", "image": "ms:web_asset", "kind": "shot",
                            "subtext": "Capture the focused window"})
    # command runner (typed: "cmd", "run", "terminal", or "> ...")
    if config.get("enable_runcmd", True) and q:
        ql = q.lower()
        run_prefix = q.startswith((">", "$"))
        if run_prefix or any(ql.startswith(w[:len(ql)]) and len(ql) >= 2
                             for w in ("cmd", "run", "terminal", "command", "shell")):
            special.append({
                "key": "runcmd", "name": "Run a command…",
                "target": q.lstrip(">$ ").strip(), "image": "ms:terminal",
                "subtext": "Open the command runner (Enter)", "kind": "runcmd",
            })

    # open URL / web search
    if q and config.get("enable_websearch", True):
        if looks_like_url(q):
            url = q if "://" in q else "https://" + q
            special.append({
                "key": "openurl", "name": f"Open {q}", "target": url,
                "image": "ms:link", "subtext": "Open in browser", "kind": "url",
            })
        else:
            tmpl = config.get("web_search_url", DEFAULT_CONFIG["web_search_url"])
            url = tmpl.replace("{q}", quote(q))
            special.append({
                "key": "websearch", "name": f"Search the web for “{q}”",
                "target": url, "image": "ms:travel_explore",
                "subtext": "Web search", "kind": "url",
            })

    return results, special


def looks_like_url(s):
    s = s.strip()
    if " " in s:
        return False
    if s.startswith(("http://", "https://")):
        return True
    return bool(re.fullmatch(r"[\w-]+(\.[\w-]+)+(/\S*)?", s))


def quote(s):
    from urllib.parse import quote_plus
    return quote_plus(s)


# --------------------------------------------------------------------------- #
#  Mutations (used by the Settings UI / API)
# --------------------------------------------------------------------------- #
def record_usage(key):
    store = load_json(STORE_PATH, DEFAULT_STORE)
    u = store.setdefault("usage", {})
    rec = u.setdefault(key, {"count": 0, "last": 0})
    rec["count"] = int(rec.get("count", 0)) + 1
    rec["last"] = time.time()
    save_json(STORE_PATH, store)
    invalidate_cache()


def set_meta(key, **fields):
    store = load_json(STORE_PATH, DEFAULT_STORE)
    meta = store.setdefault("meta", {})
    rec = meta.setdefault(key, {})
    for k, v in fields.items():
        if v in (None, ""):
            rec.pop(k, None)
        else:
            rec[k] = v
    if not rec:
        meta.pop(key, None)
    save_json(STORE_PATH, store)
    invalidate_cache()


def toggle_pin(key):
    store = load_json(STORE_PATH, DEFAULT_STORE)
    rec = store.setdefault("meta", {}).setdefault(key, {})
    rec["pinned"] = not rec.get("pinned", False)
    if not rec["pinned"]:
        rec.pop("pinned", None)
    save_json(STORE_PATH, store)
    invalidate_cache()
    return rec.get("pinned", False)


def add_custom(name, target, icon="•", image=""):
    data = load_json(CUSTOM_PATH, DEFAULT_CUSTOM)
    entry = {"name": name, "target": target, "icon": icon or "•"}
    if image:
        entry["image"] = image
    data.setdefault("shortcuts", []).append(entry)
    ok = save_json(CUSTOM_PATH, data); invalidate_cache(); return ok


def update_custom(index, name, target, icon="•", image=""):
    data = load_json(CUSTOM_PATH, DEFAULT_CUSTOM)
    lst = data.setdefault("shortcuts", [])
    if 0 <= index < len(lst):
        entry = {"name": name, "target": target, "icon": icon or "•"}
        if image:
            entry["image"] = image
        lst[index] = entry
        ok = save_json(CUSTOM_PATH, data); invalidate_cache(); return ok
    return False


def delete_custom(index):
    data = load_json(CUSTOM_PATH, DEFAULT_CUSTOM)
    lst = data.setdefault("shortcuts", [])
    if 0 <= index < len(lst):
        del lst[index]
        ok = save_json(CUSTOM_PATH, data); invalidate_cache(); return ok
    return False


# --------------------------------------------------------------------------- #
#  .qllink shortcut files  (drag-and-drop / "Add shortcut")
# --------------------------------------------------------------------------- #
def _safe_filename(name):
    keep = "-_.() "
    cleaned = "".join(c for c in name if c.isalnum() or c in keep).strip()
    return cleaned or "shortcut"


def create_qllink(name, target, icon="", image=""):
    """Write a .qllink file into the Shortcuts folder. Returns the path."""
    os.makedirs(SHORTCUT_DIR, exist_ok=True)
    base = _safe_filename(name)
    path = os.path.join(SHORTCUT_DIR, base + QLLINK_EXT)
    i = 2
    while os.path.exists(path):
        path = os.path.join(SHORTCUT_DIR, f"{base} ({i}){QLLINK_EXT}")
        i += 1
    payload = {"name": name, "target": target}
    if icon:
        payload["icon"] = icon
    if image:
        payload["image"] = image
    save_json(path, payload)
    invalidate_cache()
    return path


def add_dropped_path(path):
    """Drag-and-drop handler: turn a dropped file/folder into a .qllink."""
    path = path.strip().strip('"')
    if not path:
        return None
    if path.startswith("file://"):
        from urllib.parse import unquote, urlparse
        path = unquote(urlparse(path).path)
        if sys.platform.startswith("win") and path.startswith("/"):
            path = path[1:]
    name = os.path.splitext(os.path.basename(path.rstrip("/\\")))[0] or path
    created = create_qllink(name, path, image=_guess_image(path))
    return os.path.basename(created)


def add_dropped_url(url, name=""):
    url = url.strip()
    if not url:
        return None
    if not name:
        from urllib.parse import urlparse
        name = urlparse(url).netloc or url
    return os.path.basename(create_qllink(name, url, image="ms:" + URL_ICON))


def delete_shortcut(key):
    """Remove a shortcut by key. Handles file/qllink (delete file),
    custom (remove from json). Returns True on success."""
    items = {it.key: it for it in collect_shortcuts(force=True)}
    it = items.get(key)
    if not it:
        return False
    # also drop its stored metadata/usage
    _purge_store(key)
    invalidate_cache()
    if it.source == "custom":
        data = load_json(CUSTOM_PATH, DEFAULT_CUSTOM)
        lst = data.get("shortcuts", [])
        for i, sc in enumerate(lst):
            if isinstance(sc, dict) and sc.get("name") == it.name:
                del lst[i]
                ok = save_json(CUSTOM_PATH, data); invalidate_cache(); return ok
        return False
    # file or qllink -> delete the backing file
    if it.file_path and os.path.exists(it.file_path):
        try:
            if os.path.isdir(it.file_path):
                import shutil
                shutil.rmtree(it.file_path)
            else:
                os.remove(it.file_path)
            return True
        except Exception as exc:
            print(f"[PyDoc] delete error: {exc}")
            return False
    return False


def _purge_store(key):
    store = load_json(STORE_PATH, DEFAULT_STORE)
    store.get("meta", {}).pop(key, None)
    store.get("usage", {}).pop(key, None)
    save_json(STORE_PATH, store)


# --------------------------------------------------------------------------- #
#  Icon system  (Google Material Symbols only — no emojis)
#    image string formats:
#      "ms:<name>"    -> Material Symbol ligature, rendered with bundled font
#      "file:<name>"  -> a .ico/.svg/.png imported into the Icons folder
#      "<abs path>"   -> any local image path
#      "<http url>"   -> remote image
# --------------------------------------------------------------------------- #
_MS_CACHE = None


def material_icon_names():
    """All bundled Material Symbol names (for the picker)."""
    global _MS_CACHE
    if _MS_CACHE is not None:
        return _MS_CACHE
    names = []
    path = os.path.join(WEB_DIR, "vendor", "material-icon-names.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            names = json.load(fh)
    except Exception:
        pass
    _MS_CACHE = names
    return names


# kept for backwards-compat with older callers/tests
def winui_icon_names():
    return material_icon_names()


def search_icons(query, limit=80):
    """Return Material-symbol icon suggestions for the picker."""
    q = (query or "").lower().strip().replace(" ", "_")
    names = material_icon_names()
    if q:
        starts = [n for n in names if n.startswith(q)]
        contains = [n for n in names if q in n and not n.startswith(q)]
        hits = starts + contains
    else:
        hits = names
    return [{"image": "ms:" + n, "name": n} for n in hits[:limit]]


def import_custom_icon(src_path):
    """Copy a user-chosen .ico/.svg/.png into the Icons folder.
    Returns an image string 'file:<name>'."""
    os.makedirs(ICON_DIR, exist_ok=True)
    src_path = (src_path or "").strip().strip('"')
    if src_path.startswith("file://"):
        from urllib.parse import unquote, urlparse
        src_path = unquote(urlparse(src_path).path)
        if sys.platform.startswith("win") and src_path.startswith("/"):
            src_path = src_path[1:]
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in (".ico", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return None
    import shutil
    base = _safe_filename(os.path.splitext(os.path.basename(src_path))[0]) + ext
    dst = os.path.join(ICON_DIR, base)
    i = 2
    while os.path.exists(dst) and os.path.abspath(dst) != os.path.abspath(src_path):
        dst = os.path.join(ICON_DIR, f"{os.path.splitext(base)[0]}_{i}{ext}")
        i += 1
    try:
        shutil.copyfile(src_path, dst)
        return "file:" + os.path.basename(dst)
    except Exception as exc:
        print(f"[PyDoc] icon import error: {exc}")
        return None


def material_symbol(name):
    """Validate a Material symbol name; return 'ms:<name>' or None."""
    n = re.sub(r"[^a-z0-9_]+", "_", (name or "").lower()).strip("_")
    if not n:
        return None
    if n in set(material_icon_names()):
        return "ms:" + n
    # accept anyway (font may have it even if our list lags), but flag unknown
    return "ms:" + n


# backwards-compat alias used by older API method
def fetch_material_icon(name):
    img = material_symbol(name)
    return img


def resolve_image(image):
    """Turn an image string into something the web UI can render directly:
       ms:<name>  -> returned as-is (UI renders with the Material font)
       file:<n>   -> a file:// URL to the imported asset
       http url   -> unchanged
       abs path   -> file:// URL."""
    if not image:
        return ""
    if image.startswith("ms:"):
        return image
    if image.startswith(("http://", "https://")):
        return image
    if image.startswith("file:"):
        rel = image[5:]
        p = rel if os.path.isabs(rel) else os.path.join(ICON_DIR, rel)
        return _file_url(p) if os.path.exists(p) else ""
    if os.path.exists(image):
        return _file_url(image)
    return ""


def _file_url(path):
    from urllib.parse import quote
    p = os.path.abspath(path).replace("\\", "/")
    if not p.startswith("/"):
        p = "/" + p
    return "file://" + quote(p)


# --------------------------------------------------------------------------- #
#  Screenshots
#    capture: "full"   -> whole virtual desktop
#             "window" -> the active foreground window (Windows; full elsewhere)
#             "region" -> interactive region select (native tool where possible)
# --------------------------------------------------------------------------- #
def _shot_path():
    os.makedirs(SHOT_DIR, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(SHOT_DIR, f"screenshot_{stamp}.png")
    i = 2
    while os.path.exists(path):
        path = os.path.join(SHOT_DIR, f"screenshot_{stamp}_{i}.png")
        i += 1
    return path


def _copy_image_to_clipboard(path):
    """Best-effort copy of a PNG to the OS clipboard."""
    try:
        if sys.platform.startswith("win"):
            from PIL import Image
            import io
            img = Image.open(path).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "BMP")
            data = buf.getvalue()[14:]   # strip BMP header -> DIB
            buf.close()
            import ctypes
            CF_DIB = 8
            u = ctypes.windll.user32
            k = ctypes.windll.kernel32
            if u.OpenClipboard(0):
                try:
                    u.EmptyClipboard()
                    h = k.GlobalAlloc(0x2000, len(data))   # GMEM_DDESHARE
                    p = k.GlobalLock(h)
                    ctypes.memmove(p, data, len(data))
                    k.GlobalUnlock(h)
                    u.SetClipboardData(CF_DIB, h)
                finally:
                    u.CloseClipboard()
            return True
        elif sys.platform == "darwin":
            script = ('set the clipboard to (read (POSIX file "%s") as '
                      '{«class PNGf»})' % path)
            subprocess.run(["osascript", "-e", script], check=False)
            return True
        else:
            # Linux: try xclip / wl-copy
            for cmd in (["xclip", "-selection", "clipboard", "-t", "image/png", "-i", path],
                        ["wl-copy", "--type", "image/png"]):
                try:
                    if cmd[0] == "wl-copy":
                        with open(path, "rb") as fh:
                            subprocess.run(cmd, stdin=fh, check=False)
                    else:
                        subprocess.run(cmd, check=False)
                    return True
                except FileNotFoundError:
                    continue
    except Exception as exc:
        print(f"[PyDoc] clipboard copy failed: {exc}")
    return False


def take_screenshot(mode="full", copy=None):
    """Capture the screen and save a PNG to the Screenshots folder.
    Returns the saved path, or None on failure."""
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    if copy is None:
        copy = cfg.get("screenshot_copy", True)
    path = _shot_path()

    # 1) Region capture via the OS's native snipping tool (best UX)
    if mode == "region":
        try:
            if sys.platform.startswith("win"):
                # Windows 10/11 Snip & Sketch overlay (saves to clipboard)
                os.startfile("ms-screenclip:")  # type: ignore[attr-defined]
                return "@clipboard"   # user completes the snip; image goes to clipboard
            elif sys.platform == "darwin":
                subprocess.run(["screencapture", "-i", path], check=False)
                if os.path.exists(path):
                    if copy:
                        _copy_image_to_clipboard(path)
                    return path
                return None
            else:
                for cmd in (["spectacle", "-rbn", "-o", path],
                            ["gnome-screenshot", "-a", "-f", path],
                            ["scrot", "-s", path]):
                    try:
                        subprocess.run(cmd, check=False)
                        if os.path.exists(path):
                            return path
                    except FileNotFoundError:
                        continue
        except Exception as exc:
            print(f"[PyDoc] region capture failed: {exc}")
        # fall through to full capture if region tooling unavailable

    # 2) Full / window capture via Pillow's ImageGrab (Windows & macOS)
    try:
        from PIL import ImageGrab
        if mode == "window" and sys.platform.startswith("win"):
            bbox = _active_window_bbox()
            img = ImageGrab.grab(bbox=bbox, all_screens=True) if bbox else ImageGrab.grab(all_screens=True)
        else:
            img = ImageGrab.grab(all_screens=True)
        img.save(path, "PNG")
        if copy:
            _copy_image_to_clipboard(path)
        return path
    except Exception as exc:
        print(f"[PyDoc] screenshot failed (install pillow?): {exc}")

    # 3) Linux fallback without Pillow ImageGrab
    if not sys.platform.startswith(("win", "darwin")):
        for cmd in (["gnome-screenshot", "-f", path], ["scrot", path],
                    ["import", "-window", "root", path]):
            try:
                subprocess.run(cmd, check=False)
                if os.path.exists(path):
                    if copy:
                        _copy_image_to_clipboard(path)
                    return path
            except FileNotFoundError:
                continue
    return None


def _active_window_bbox():
    try:
        import ctypes
        class _R(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                        ("r", ctypes.c_long), ("b", ctypes.c_long)]
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        r = _R()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        return (r.l, r.t, r.r, r.b)
    except Exception:
        return None


def open_screenshot_folder():
    os.makedirs(SHOT_DIR, exist_ok=True)
    return launch_target(SHOT_DIR)


# --------------------------------------------------------------------------- #
#  Command runner  (Run-style box inside the launcher)
#    * runs a shell command and captures stdout/stderr + exit code
#    * history: pinned commands persist to cmd_history.json; unpinned are
#      session-only (kept in memory, lost on reboot)
#    * auto-correction: "did you mean" for common mistyped commands
# --------------------------------------------------------------------------- #
_SESSION_HISTORY = []     # recent unpinned commands this run (most-recent first)
_SESSION_MAX = 50

# common command vocabulary for typo correction (extended with the user's history)
_COMMON_CMDS = [
    "ping", "ipconfig", "ifconfig", "powershell", "cmd",
    "tracert", "traceroute", "nslookup", "netstat", "tasklist", "taskkill",
    "systeminfo", "cls", "clear", "dir", "ls", "cd", "echo", "type", "cat",
    "copy", "move", "del", "rm", "mkdir", "rmdir", "ren", "rename", "whoami",
    "hostname", "shutdown", "restart", "explorer", "notepad", "calc", "code",
    "git", "python", "pip", "node", "npm", "npx", "java", "docker", "kubectl",
    "ssh", "scp", "curl", "wget", "winget", "choco", "chkdsk", "sfc", "diskpart",
    "robocopy", "xcopy", "attrib", "find", "findstr", "grep", "where", "which",
    "set", "setx", "reg", "wmic", "gpupdate", "control", "msconfig", "regedit",
    "services.msc", "devmgmt.msc", "appwiz.cpl", "ncpa.cpl",
]


def _shell_for(cmd):
    """Return a (args, use_shell) tuple appropriate for the platform."""
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    custom = (cfg.get("cmd_shell") or "").strip()
    if custom:
        return ([custom, "-c", cmd] if not sys.platform.startswith("win")
                else [custom, "/c", cmd]), False
    if sys.platform.startswith("win"):
        comspec = os.environ.get("ComSpec", "cmd.exe")
        return [comspec, "/c", cmd], False
    return cmd, True


def run_command(cmd, timeout=20):
    """Execute a shell command, capturing output. Returns a result dict."""
    cmd = (cmd or "").strip()
    if not cmd:
        return {"ok": False, "cmd": cmd, "stdout": "", "stderr": "Empty command.",
                "code": -1, "suggestion": ""}

    # record into session history (deduped, most-recent first)
    _push_session(cmd)

    args, use_shell = _shell_for(cmd)
    try:
        proc = subprocess.run(
            args, shell=use_shell, capture_output=True, text=True,
            timeout=timeout, cwd=os.path.expanduser("~"),
            errors="replace")
        out, err, code = proc.stdout or "", proc.stderr or "", proc.returncode
    except subprocess.TimeoutExpired:
        return {"ok": False, "cmd": cmd, "stdout": "", "code": -1,
                "stderr": f"Command timed out after {timeout}s.", "suggestion": ""}
    except FileNotFoundError as exc:
        return {"ok": False, "cmd": cmd, "stdout": "", "code": 127,
                "stderr": str(exc), "suggestion": suggest_command(cmd)}
    except Exception as exc:
        return {"ok": False, "cmd": cmd, "stdout": "", "code": -1,
                "stderr": str(exc), "suggestion": suggest_command(cmd)}

    suggestion = ""
    if code != 0:
        # common "not recognized / not found" → offer a correction
        low = (err or "").lower()
        if ("not recognized" in low or "not found" in low
                or "no such file" in low or code == 127):
            suggestion = suggest_command(cmd)
    return {"ok": code == 0, "cmd": cmd, "stdout": out, "stderr": err,
            "code": code, "suggestion": suggestion}


def suggest_command(cmd):
    """Return a 'did you mean' full-command suggestion, or '' if none/already ok."""
    cmd = (cmd or "").strip()
    if not cmd:
        return ""
    if not load_json(CONFIG_PATH, DEFAULT_CONFIG).get("cmd_autocorrect", True):
        return ""
    parts = cmd.split(None, 1)
    head = parts[0].lower()
    rest = (" " + parts[1]) if len(parts) > 1 else ""
    vocab = sorted(set(_COMMON_CMDS) | _history_vocab())
    if head in vocab:
        return ""
    best, best_d = None, 999
    for w in vocab:
        d = _levenshtein(head, w)
        # only correct close typos (scaled by length)
        if d < best_d and d <= max(1, len(head) // 3 + 1):
            best, best_d = w, d
    if best and best != head:
        return best + rest
    return ""


def _history_vocab():
    words = set()
    for entry in get_cmd_history():
        c = entry.get("cmd", "").split(None, 1)
        if c:
            words.add(c[0].lower())
    return words


def _levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# ---- command history (pinned persist, session lost on reboot) -------------
def _load_pinned():
    data = load_json(CMDHIST_PATH, {"pinned": []})
    return data.get("pinned", []) if isinstance(data, dict) else []


def _save_pinned(pinned):
    save_json(CMDHIST_PATH, {"pinned": pinned})


def _push_session(cmd):
    global _SESSION_HISTORY
    _SESSION_HISTORY = [c for c in _SESSION_HISTORY if c != cmd]
    _SESSION_HISTORY.insert(0, cmd)
    del _SESSION_HISTORY[_SESSION_MAX:]


def get_cmd_history():
    """Pinned first (in saved order), then recent session commands."""
    pinned = _load_pinned()
    pinned_set = set(pinned)
    out = [{"cmd": c, "pinned": True} for c in pinned]
    out += [{"cmd": c, "pinned": False}
            for c in _SESSION_HISTORY if c not in pinned_set]
    return out


def pin_command(cmd):
    cmd = (cmd or "").strip()
    if not cmd:
        return False
    pinned = _load_pinned()
    if cmd not in pinned:
        pinned.append(cmd)
        _save_pinned(pinned)
    return True


def unpin_command(cmd):
    pinned = [c for c in _load_pinned() if c != (cmd or "").strip()]
    _save_pinned(pinned)
    return True


def clear_session_history():
    global _SESSION_HISTORY
    _SESSION_HISTORY = []
    return True


# --------------------------------------------------------------------------- #
#  Launching
# --------------------------------------------------------------------------- #
def launch_target(target):
    if target == "@open_shortcut_folder":
        target = SHORTCUT_DIR
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            if os.path.exists(target) or target.startswith(("http://", "https://")):
                subprocess.Popen(["xdg-open", target])
            else:
                subprocess.Popen(target, shell=True)
        return True
    except Exception as exc:
        print(f"[PyDoc] launch error '{target}': {exc}")
        return False


def open_folder():
    return launch_target(SHORTCUT_DIR)
