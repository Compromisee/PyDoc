#!/usr/bin/env python3
"""
PyDoc · host
====================
pywebview window that renders the windows-ui-fabric (Fluent) front-end and
exposes a Python API bridge.  Adds:

  * system-tray icon          (pystray + pillow, optional)
  * global hotkey  Alt+Space  (keyboard, optional)
  * per-shortcut global hotkeys (keyboard, optional)
  * Windows auto-start on login
  * single-folder shortcut model + all logic from core.py

Run:  python launcher.py
Extras:  pip install -r requirements.txt   (pywebview + tray + hotkey)
"""

import os
import sys
import json
import time
import threading

if sys.version_info < (3, 11):
    print("PyDoc requires Python 3.11 or newer "
          f"(you have {sys.version.split()[0]}).")
    sys.exit(1)

import core as C

try:
    import webview            # pywebview
except Exception:
    webview = None


# --------------------------------------------------------------------------- #
#  JS API exposed to the web UI  (window.pywebview.api.*)
# --------------------------------------------------------------------------- #
class Api:
    def __init__(self):
        self.config = C.load_json(C.CONFIG_PATH, C.DEFAULT_CONFIG)
        self.themes = C.load_json(C.THEMES_PATH, C.DEFAULT_THEMES)
        # keep config keys current
        for k, v in C.DEFAULT_CONFIG.items():
            self.config.setdefault(k, v)
        self._window = None
        self._host = None        # back-ref to Host for hotkeys etc.
        self._unlocked = not C.is_locked()   # session unlock state

    # ---- password lock + profiles ---------------------------------------
    def lock_status(self):
        return {"enabled": C.is_locked(), "unlocked": self._unlocked,
                "profile": C.ACTIVE_PROFILE, "has_master": C.has_master()}

    def unlock(self, password):
        """Unlock with any valid password and switch to its profile."""
        kind, pid = C.resolve_password(password)
        if kind is None:
            return {"ok": False}
        C.activate_profile(pid)
        self._unlocked = True
        if self._host:
            self._host.register_hotkeys()
        return {"ok": True, "kind": kind, "profile": pid}

    def relock(self):
        """Re-arm the lock and return to the default profile when hidden."""
        if C.is_locked():
            self._unlocked = False
            C.activate_profile("default")
        return True

    def set_password(self, password):
        res = C.set_lock_password(password)
        if res.get("ok"):
            self.config = C.load_json(C.CONFIG_PATH, C.DEFAULT_CONFIG)
            C.activate_profile("default")
            self._unlocked = True
        return res

    def disable_lock(self, password):
        ok = C.disable_lock(password)
        if ok:
            self.config = C.load_json(C.CONFIG_PATH, C.DEFAULT_CONFIG)
            C.activate_profile("default")
            self._unlocked = True
        return ok

    def set_master_password(self, password):
        res = C.set_master_password(password)
        if res.get("ok"):
            self.config = C.load_json(C.CONFIG_PATH, C.DEFAULT_CONFIG)
        return res

    def list_profiles(self):
        return C.list_profiles()

    def add_profile(self, name, password, secret=False):
        res = C.add_profile(name, password, secret)
        if res.get("ok"):
            self.config = C.load_json(C.CONFIG_PATH, C.DEFAULT_CONFIG)
        return res

    def delete_profile(self, pid):
        ok = C.delete_profile(pid)
        self.config = C.load_json(C.CONFIG_PATH, C.DEFAULT_CONFIG)
        return ok

    def has_secret(self):
        return bool(self.config.get("secret", {}).get("hash"))

    # ---- state -----------------------------------------------------------
    def get_state(self):
        return {
            "config": self.config,
            "themes": self.themes,
            "autostart_supported": sys.platform.startswith("win"),
            "autostart_enabled": C.is_autostart_enabled(),
            "has_keyboard": _has("keyboard"),
            "has_tray": _has("pystray") and _has("PIL"),
            "winui_icons": C.winui_icon_names(),
            "lock_enabled": C.is_locked(),
            "unlocked": self._unlocked,
            "app_name": C.APP_NAME,
            "app_version": C.APP_VERSION,
            "app_channel": C.APP_CHANNEL,
            "app_title": C.APP_TITLE,
        }

    # ---- search ----------------------------------------------------------
    def search(self, query, group="All"):
        if C.is_locked() and not self._unlocked:
            return {"results": [], "special": [], "groups": ["All"], "locked": True}
        items = C.collect_shortcuts()
        if group and group != "All":
            items = [it for it in items if it.group == group]
        results, special = C.search_items(query, items, self.config)
        return {
            "results": results,
            "special": special,
            "groups": C.all_groups(C.collect_shortcuts()),
        }

    def groups(self):
        return C.all_groups(C.collect_shortcuts())

    # ---- launching -------------------------------------------------------
    def launch(self, key):
        if C.is_locked() and not self._unlocked:
            return False
        items = {it.key: it for it in C.collect_shortcuts()}
        it = items.get(key)
        if not it:
            return False
        C.record_usage(key)
        return C.launch_target(it.target)

    def launch_special(self, target):
        if C.is_locked() and not self._unlocked:
            return False
        return C.launch_target(target)

    # ---- screenshots -----------------------------------------------------
    def screenshot(self, mode="full"):
        """Hide the launcher, capture, then report back to the UI."""
        if C.is_locked() and not self._unlocked:
            return None
        if self._host:
            return self._host.do_screenshot(mode)
        return C.take_screenshot(mode)

    def open_screenshot_folder(self):
        return C.open_screenshot_folder()

    # ---- command runner --------------------------------------------------
    def run_command(self, cmd):
        if C.is_locked() and not self._unlocked:
            return {"ok": False, "stderr": "Locked.", "code": -1,
                    "cmd": cmd, "stdout": "", "suggestion": ""}
        return C.run_command(cmd)

    def suggest_command(self, cmd):
        return C.suggest_command(cmd)

    def cmd_history(self):
        return C.get_cmd_history()

    def pin_command(self, cmd):
        return C.pin_command(cmd)

    def unpin_command(self, cmd):
        return C.unpin_command(cmd)

    def clear_cmd_history(self):
        return C.clear_session_history()

    def open_folder(self):
        return C.open_folder()

    # ---- metadata / pins -------------------------------------------------
    def toggle_pin(self, key):
        return C.toggle_pin(key)

    def meta_for(self, key):
        store = C.load_json(C.STORE_PATH, C.DEFAULT_STORE)
        return store.get("meta", {}).get(key, {})

    def set_meta(self, key, group="", alias="", hotkey="", icon="", image=""):
        C.set_meta(key, group=group, alias=alias, hotkey=hotkey,
                   icon=icon, image=image)
        if self._host:
            self._host.register_hotkeys()
        return True

    # ---- custom shortcuts ------------------------------------------------
    def list_custom(self):
        data = C.load_json(C.CUSTOM_PATH, C.DEFAULT_CUSTOM)
        return [s for s in data.get("shortcuts", []) if isinstance(s, dict)]

    def add_custom(self, name, target, icon="•", image=""):
        return C.add_custom(name, target, icon, image)

    def update_custom(self, index, name, target, icon="•", image=""):
        return C.update_custom(int(index), name, target, icon, image)

    def delete_custom(self, index):
        return C.delete_custom(int(index))

    # ---- drag-and-drop / delete -----------------------------------------
    def add_dropped(self, path):
        """Create a shortcut from a dropped file/folder path."""
        res = C.add_dropped_path(path)
        if self._host:
            self._host.register_hotkeys()
        return res

    def add_dropped_url(self, url, name=""):
        return C.add_dropped_url(url, name)

    def create_qllink(self, name, target, icon="", image=""):
        path = C.create_qllink(name, target, icon, image)
        if self._host:
            self._host.register_hotkeys()
        return os.path.basename(path)

    def delete_shortcut(self, key):
        ok = C.delete_shortcut(key)
        if ok and self._host:
            self._host.register_hotkeys()
        return ok

    # ---- icon system -----------------------------------------------------
    def search_icons(self, query, limit=60):
        return C.search_icons(query, int(limit))

    def fetch_material_icon(self, name):
        img = C.fetch_material_icon(name)
        return {"image": img, "url": C.resolve_image(img)} if img else None

    def resolve_image(self, image):
        return C.resolve_image(image)

    def pick_icon_file(self):
        """Open a native file dialog to choose an icon, import it."""
        if not self._window:
            return None
        if self._host:
            self._host._suppress_blur = True
        try:
            sel = self._window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False,
                file_types=("Images (*.ico;*.svg;*.png;*.jpg;*.jpeg;*.gif;*.webp)",
                            "All files (*.*)"))
        except Exception as exc:
            print(f"[PyDoc] icon dialog error: {exc}")
            return None
        finally:
            if self._host:
                self._host._clear_blur_suppress()
        if not sel:
            return None
        path = sel[0] if isinstance(sel, (list, tuple)) else sel
        img = C.import_custom_icon(path)
        return {"image": img, "url": C.resolve_image(img)} if img else None

    def pick_target_file(self):
        """Open a native file dialog to choose a program/file target."""
        if not self._window:
            return None
        if self._host:
            self._host._suppress_blur = True
        try:
            sel = self._window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False)
        except Exception:
            return None
        finally:
            if self._host:
                self._host._clear_blur_suppress()
        if not sel:
            return None
        return sel[0] if isinstance(sel, (list, tuple)) else sel

    # ---- config / theme --------------------------------------------------
    def set_theme(self, name):
        self.config["theme"] = name
        C.save_json(C.CONFIG_PATH, self.config)
        if self._host:
            self._host.update_tray_icon()
        return True

    def save_config(self, partial):
        if isinstance(partial, str):
            partial = json.loads(partial)
        prev_hotkey = self.config.get("hotkey")
        prev_add = self.config.get("hotkey_add")
        prev_shot = self.config.get("hotkey_screenshot")
        prev_run = self.config.get("hotkey_runcmd")
        prev_auto = self.config.get("autostart")
        self.config.update(partial or {})
        C.save_json(C.CONFIG_PATH, self.config)
        # apply side-effects
        if self._host and (self.config.get("hotkey") != prev_hotkey
                          or self.config.get("hotkey_add") != prev_add
                          or self.config.get("hotkey_screenshot") != prev_shot
                          or self.config.get("hotkey_runcmd") != prev_run):
            self._host.register_hotkeys()
        if sys.platform.startswith("win") and self.config.get("autostart") != prev_auto:
            C.set_autostart(bool(self.config.get("autostart")))
        if self._host:
            self._host.update_tray_icon()
        return True

    # ---- window ----------------------------------------------------------
    def hide(self):
        if self._host:
            self._host.hide_window()
        return True

    def hide_on_blur(self):
        """Called by the front-end when the window loses focus."""
        if not self.config.get("hide_on_blur", True):
            return False
        if self._host:
            return self._host.hide_on_blur()
        return False

    def quit(self):
        if self._host:
            self._host.quit_app()
        return True


def _has(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
#  Host: window lifecycle, tray, hotkeys
# --------------------------------------------------------------------------- #
class Host:
    def __init__(self):
        self.api = Api()
        self.api._host = self        # private so pywebview won't serialize it
        self.window = None
        self.tray = None
        self._tray_thread = None
        self._visible = True
        self._started_once = False
        self._start_hidden = False
        self._suppress_blur = False   # set while a native dialog is open

    # ---------------------------------------------------------------- window
    def build_window(self):
        index = os.path.join(C.WEB_DIR, "index.html")
        # Start hidden when running as a background tray app, so there's no
        # flash and we never have to race a show()->hide() during startup.
        can_revive = _has("pystray") and _has("PIL") or _has("keyboard")
        self._start_hidden = (not self.api.config.get("show_on_launch", False)
                              and can_revive)
        # NOTE: WebView2 (Windows) doesn't reliably support a transparent
        # window background (it showed up as a white box). We give the window
        # the dark card colour and let the card fill it edge-to-edge; Windows 11
        # rounds app-window corners automatically.
        self.window = webview.create_window(
            "PyDoc",
            url=index,
            js_api=self.api,
            width=680, height=560,
            resizable=False, frameless=True,
            easy_drag=False, on_top=True,
            hidden=self._start_hidden,
            background_color="#202020",
            text_select=False,
        )
        self._visible = not self._start_hidden
        self.api._window = self.window
        for ev, cb in (("closing", self._on_closing),
                       ("loaded", self._on_loaded),
                       ("shown", self._on_shown)):
            try:
                getattr(self.window.events, ev).__iadd__(cb)
            except Exception:
                pass

    def _on_shown(self):
        if not self._start_hidden:
            self._center()

    def _on_loaded(self):
        """GUI-thread setup once the DOM is ready: tray, hotkeys, drop handler."""
        if not self._started_once:
            self._started_once = True
            self.build_tray()
            self.register_hotkeys()
        self._register_drop()

    def _register_drop(self):
        """Register a native drag-and-drop handler on the document body."""
        try:
            from webview.dom import DOMEventHandler
        except Exception:
            return

        def on_drop(e):
            paths = []
            for f in (e.get("dataTransfer", {}) or {}).get("files", []) or []:
                p = f.get("pywebviewFullPath") or f.get("name")
                if p:
                    paths.append(p)
            added = []
            for p in paths:
                name = C.add_dropped_path(p)
                if name:
                    added.append(name)
            # also accept dropped text/URLs
            if not paths:
                txt = (e.get("dataTransfer", {}) or {}).get("text", "")
                if txt and ("://" in txt):
                    C.add_dropped_url(txt)
                    added.append(txt)
            if added:
                self.register_hotkeys()
                self._eval_js(
                    "window.qlOnDrop && window.qlOnDrop(%s)" % json.dumps(added))

        try:
            body = self.window.dom.get_elements("body")
            if body:
                body[0].events.drop += DOMEventHandler(
                    on_drop, prevent_default=True, stop_propagation=True)
                # also prevent default dragover so drop fires
                body[0].events.dragover += DOMEventHandler(
                    lambda e: None, prevent_default=True)
                print("[PyDoc] drag-and-drop ready.")
        except Exception as exc:
            print(f"[PyDoc] drop registration failed: {exc}")

    def _on_closing(self):
        # Hide instead of close when a tray exists; otherwise really quit.
        if self.tray is not None:
            self.hide_window()
            return False
        return True

    def show_window(self):
        try:
            self._center()
            self.window.show()
            self.window.on_top = True
            self._visible = True
            self._force_foreground()
            self._eval_js("window.qlOnShow && window.qlOnShow()")
        except Exception as exc:
            print(f"[PyDoc] show error: {exc}")

    def _force_foreground(self):
        """On Windows, reliably pull the window to the foreground and give it
        keyboard focus even when summoned via a global hotkey (Windows normally
        blocks SetForegroundWindow from background processes)."""
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            from ctypes import wintypes
            u = ctypes.windll.user32
            k = ctypes.windll.kernel32
            hwnd = u.FindWindowW(None, "PyDoc")
            if not hwnd:
                return
            SW_RESTORE = 9
            u.ShowWindow(hwnd, SW_RESTORE)
            # attach our thread input to the current foreground thread so the
            # SetForegroundWindow call is permitted, then detach.
            fg = u.GetForegroundWindow()
            cur_tid = k.GetCurrentThreadId()
            fg_tid = u.GetWindowThreadProcessId(fg, None)
            tgt_tid = u.GetWindowThreadProcessId(hwnd, None)
            for t in {fg_tid, tgt_tid}:
                if t and t != cur_tid:
                    u.AttachThreadInput(cur_tid, t, True)
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
            u.SetFocus(hwnd)
            for t in {fg_tid, tgt_tid}:
                if t and t != cur_tid:
                    u.AttachThreadInput(cur_tid, t, False)
        except Exception as exc:
            print(f"[PyDoc] foreground error: {exc}")

    def hide_window(self):
        try:
            self.window.hide()
            self._visible = False
            self.api.relock()   # re-arm the password lock when hidden
        except Exception:
            pass

    def hide_on_blur(self):
        """Hide when the window loses focus (like Flow Launcher / PowerToys Run),
        unless a native dialog (file picker) is open."""
        if self._suppress_blur or not self._visible:
            return False
        self.hide_window()
        return True

    def _clear_blur_suppress(self):
        """Re-enable blur-hide a moment after a native dialog closes, so the
        focus bouncing back to the window doesn't immediately hide it."""
        def _reset():
            time.sleep(0.4)
            self._suppress_blur = False
        threading.Thread(target=_reset, daemon=True).start()

    def _eval_js(self, code):
        """Best-effort JS eval that never raises on the calling thread."""
        try:
            self.window.evaluate_js(code)
        except Exception:
            pass

    def toggle_window(self):
        if self._visible:
            self.hide_window()
        else:
            self.show_window()

    def _center(self):
        """Place the window horizontally centred and ~22% from the top of the
        active monitor. Screen coords and move() are both in logical pixels."""
        try:
            screens = webview.screens or []
            if not screens:
                return
            s = self._active_screen(screens)
            w = getattr(self.window, "width", 680) or 680
            h = getattr(self.window, "height", 560) or 560
            sx = getattr(s, "x", 0) or 0
            sy = getattr(s, "y", 0) or 0
            x = sx + (s.width - w) // 2
            y = sy + int(s.height * 0.22)
            # keep fully on-screen
            x = max(sx, min(x, sx + s.width - w))
            y = max(sy, min(y, sy + s.height - h))
            self.window.move(int(x), int(y))
        except Exception as exc:
            print(f"[PyDoc] center error: {exc}")

    def _active_screen(self, screens):
        """Pick the monitor under the mouse cursor (where the user is looking),
        falling back to the primary/first screen."""
        try:
            if sys.platform.startswith("win"):
                import ctypes
                class _PT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = _PT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                # GetCursorPos is physical px; compare against physical bounds
                for s in screens:
                    px, py = s.physical_x, s.physical_y
                    if (px <= pt.x < px + s.physical_width
                            and py <= pt.y < py + s.physical_height):
                        return s
        except Exception:
            pass
        return screens[0]

    # ----------------------------------------------------------------- tray
    def _make_tray_image(self):
        from PIL import Image, ImageDraw
        name = self.api.config.get("theme", "Windows 11 Dark")
        accent = self.api.themes.get(name, {}).get("primary", "#4cc2ff")
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([4, 4, size - 4, size - 4], radius=14,
                            fill="#2b2b2b", outline=accent, width=3)
        d.ellipse([20, 18, 40, 38], outline=accent, width=4)
        d.line([37, 35, 48, 46], fill=accent, width=5)
        return img

    def build_tray(self):
        try:
            import pystray
            from PIL import Image  # noqa: F401
        except Exception:
            print("[PyDoc] Tip: 'pip install pystray pillow' for a tray icon.")
            return
        try:
            img = self._make_tray_image()
        except Exception as exc:
            print(f"[PyDoc] tray image error: {exc}")
            return

        def menu():
            import pystray
            return pystray.Menu(
                pystray.MenuItem("Open PyDoc",
                                 lambda i, it: self.show_window(), default=True),
                pystray.MenuItem("Run command…",
                                 lambda i, it: self.trigger_runcmd()),
                pystray.MenuItem("Screenshot (region)",
                                 lambda i, it: self.trigger_screenshot("region")),
                pystray.MenuItem("Screenshot (full screen)",
                                 lambda i, it: self.trigger_screenshot("full")),
                pystray.MenuItem("Reload shortcuts",
                                 lambda i, it: self._reload()),
                pystray.MenuItem("Open Shortcuts Folder",
                                 lambda i, it: C.open_folder()),
                pystray.MenuItem("Open Screenshots Folder",
                                 lambda i, it: C.open_screenshot_folder()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", lambda i, it: self.quit_app()),
            )

        import pystray
        self.tray = pystray.Icon("PyDoc", img, "PyDoc", menu())
        self._tray_thread = threading.Thread(target=self.tray.run, daemon=True)
        self._tray_thread.start()
        print("[PyDoc] system-tray icon active.")

    def update_tray_icon(self):
        if self.tray is None:
            return
        try:
            self.tray.icon = self._make_tray_image()
        except Exception:
            pass

    def _reload(self):
        self._eval_js("window.qlOnShow && window.qlOnShow()")

    # ------------------------------------------------------------- screenshots
    def do_screenshot(self, mode="full"):
        """Hide the window so it isn't captured, take the shot, notify the UI."""
        was_visible = self._visible
        if was_visible:
            self.hide_window()

        def _run():
            time.sleep(0.35)   # let the window finish hiding
            try:
                path = C.take_screenshot(mode)
            except Exception as exc:
                print(f"[PyDoc] screenshot error: {exc}")
                path = None
            # report result to the UI (toast); region snips go to clipboard
            label = path if path and path != "@clipboard" else "clipboard"
            self._eval_js("window.qlOnScreenshot && window.qlOnScreenshot(%s)"
                          % json.dumps({"ok": bool(path), "path": label, "mode": mode}))
            # bring the launcher back for full/window captures (not region)
            if mode != "region" and was_visible:
                self.show_window()

        threading.Thread(target=_run, daemon=True).start()
        return True

    def trigger_screenshot(self, mode="region"):
        """Global-hotkey entry point for a quick capture."""
        self.do_screenshot(mode)

    # ------------------------------------------------------------- hotkeys
    def register_hotkeys(self):
        try:
            import keyboard
        except Exception:
            print("[PyDoc] Tip: 'pip install keyboard' for global hotkeys.")
            return
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        # main toggle hotkey
        hk = self.api.config.get("hotkey", "alt+space")
        try:
            keyboard.add_hotkey(hk, lambda: self.toggle_window())
            print(f"[PyDoc] toggle hotkey: {hk}")
        except Exception as exc:
            print(f"[PyDoc] hotkey '{hk}' failed: {exc}")
        # "add shortcut" hotkey  (default Ctrl+Win+N)
        hk_add = self.api.config.get("hotkey_add", "ctrl+windows+n")
        if hk_add:
            try:
                keyboard.add_hotkey(hk_add, lambda: self.trigger_add())
                print(f"[PyDoc] add-shortcut hotkey: {hk_add}")
            except Exception as exc:
                print(f"[PyDoc] hotkey '{hk_add}' failed: {exc}")
        # screenshot hotkey (default Ctrl+Win+S → region snip)
        hk_shot = self.api.config.get("hotkey_screenshot", "ctrl+windows+s")
        if hk_shot and self.api.config.get("enable_screenshot", True):
            try:
                keyboard.add_hotkey(hk_shot, lambda: self.trigger_screenshot("region"))
                print(f"[PyDoc] screenshot hotkey: {hk_shot}")
            except Exception as exc:
                print(f"[PyDoc] hotkey '{hk_shot}' failed: {exc}")
        # command-runner hotkey (default Ctrl+Win+R)
        hk_run = self.api.config.get("hotkey_runcmd", "ctrl+windows+r")
        if hk_run and self.api.config.get("enable_runcmd", True):
            try:
                keyboard.add_hotkey(hk_run, lambda: self.trigger_runcmd())
                print(f"[PyDoc] run-command hotkey: {hk_run}")
            except Exception as exc:
                print(f"[PyDoc] hotkey '{hk_run}' failed: {exc}")
        # per-item hotkeys
        self._register_item_hotkeys(keyboard)

    def trigger_add(self):
        """Show the window and open the 'add shortcut' form (from a hotkey)."""
        self.show_window()
        self._eval_js("window.qlAddShortcut && window.qlAddShortcut()")

    def trigger_runcmd(self):
        """Show the window and open the command runner (from a hotkey)."""
        self.show_window()
        self._eval_js("window.qlRunCommand && window.qlRunCommand()")

    def _register_item_hotkeys(self, keyboard):
        for it in C.collect_shortcuts():
            if it.hotkey:
                target, key = it.target, it.key
                try:
                    keyboard.add_hotkey(
                        it.hotkey,
                        (lambda t=target, k=key:
                         (C.record_usage(k), C.launch_target(t))))
                    print(f"[PyDoc]   · {it.name}: {it.hotkey}")
                except Exception as exc:
                    print(f"[PyDoc]   · {it.name} hotkey failed: {exc}")

    # -------------------------------------------------------------- quit
    def quit_app(self):
        try:
            if self.tray is not None:
                self.tray.stop()
        except Exception:
            pass
        try:
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass

    # --------------------------------------------------------------- run
    def run(self):
        if webview is None:
            print("ERROR: pywebview is not installed.\n"
                  "Install it with:  pip install pywebview\n"
                  "(plus optional:   pip install pystray pillow keyboard)")
            sys.exit(1)

        # keep autostart registry in sync with config (Windows)
        if sys.platform.startswith("win"):
            want = bool(self.api.config.get("autostart", False))
            if want != C.is_autostart_enabled():
                C.set_autostart(want)

        self.build_window()
        # Tray, hotkeys and the drop handler are set up in _on_loaded(), which
        # fires on the GUI thread once the window/DOM is ready. The window is
        # created hidden in background-app mode, so there's no startup race.
        webview.start(gui=_preferred_gui(), debug=False)


def _preferred_gui():
    """Pick a transparent-capable backend when possible."""
    if sys.platform.startswith("win"):
        return "edgechromium"
    if sys.platform == "darwin":
        return None        # default cocoa
    return None            # gtk/qt auto


if __name__ == "__main__":
    Host().run()
