# PyDoc — Full Feature List

**PyDoc v1.0.0 Stable** — a fast, beautiful, keyboard-first app launcher for
Windows (also runs on macOS & Linux), built with Python + pywebview and a
Windows 11–style web UI.

---

## 🚀 Launcher core
- **Single-folder model** — only shortcuts in the `Shortcuts/` folder (+ `shortcuts.json`) are listed; nothing else is indexed.
- **Fuzzy search** with prefix/exact boosts and live **match highlighting**.
- **Usage ranking** — most-used & recently-used shortcuts float to the top automatically.
- **Folder expansion** — make a folder a shortcut and the files *inside* it also become searchable.
- **Pins** — pin favourites to the top (`Ctrl+P` or the pin button).
- **Groups** — tag shortcuts into groups and filter with chips.
- **Aliases** — give any shortcut a keyword (e.g. `vsc` → VS Code).
- **Per-item global hotkeys** — bind a key combo to launch any single shortcut.
- **Alt + 1…9** — instantly launch the Nth visible result.
- **Clear button** in the search bar; **Esc** to hide.

## ➕ Adding shortcuts
- **Drag & drop** any file, folder, or link onto the window → saved as a tiny `.qllink` file.
- **Add dialog** (`+` button or **Ctrl+Win+A**) with name, target, group, alias, hotkey & icon.
- **Custom entries** for URLs / commands / system apps via `shortcuts.json` or the in-app editor.
- **Delete** with `Ctrl+D` (confirmation prompt).

## 🎨 Icon system (Google Material, offline)
- **4,200+ Material Symbols** bundled as an offline font — searchable picker.
- Choose **Default** (auto-guessed from file type / URL), a **Material icon**, an **emoji/character**, or **your own image** (`.ico / .svg / .png / …`, copied into `Icons/`).
- No emoji clutter — clean Fluent-style glyphs throughout.

## 🧮 Inline tools
- **Calculator** — type `23*7+1`, `sqrt(144)`, `(1+2)^3`, `50%`… and press Enter to copy the result (safe AST evaluation, no `eval`).
- **Web search / open URL** — type a query to search the web (configurable engine) or a domain to open it directly.

## 🖥️ Command runner
- Open with the **terminal button**, by typing `cmd` / `run` / `> <command>`, or **Ctrl+Win+R**.
- Runs real shell commands (`cmd.exe` on Windows, `sh` elsewhere; configurable shell) with captured output.
- **Colored output** — errors red, warnings amber, success green, paths blue, numbers/IPs highlighted; the command line is syntax-highlighted.
- **Auto-correction** — "Did you mean `ipconfig`?" suggestions (Levenshtein, learns from your history). Toggleable.
- **History** — pinned commands persist to `cmd_history.json`; unpinned session commands clear on reboot. Copy / pin / reuse from the list; `↑/↓` to scroll.

## 📸 Screenshots
- Type `screenshot` / `snip` / `capture`, use **Ctrl+Win+S**, or the tray menu.
- Three modes: **region snip**, **whole screen** (all monitors), **active window**.
- Saves a timestamped PNG to `Screenshots/` and (optionally) **copies to the clipboard**.
- Uses the OS-native snipper where available (Windows Snip & Sketch, macOS `screencapture`, Linux spectacle/gnome-screenshot/scrot); falls back to Pillow `ImageGrab`.
- The launcher hides itself first so it's never in the shot.

## 🔒 Security — password lock & spaces
- **Password lock** — require a salted-SHA-256 password to search or launch (enforced server-side, not just visual). Re-arms whenever the window hides.
- **Segmented PIN field** — one box per typed character, with a show/hide eye and Caps-Lock warning.
- **Master (recovery) password** — unlocks (and can disable) the lock if you forget your password; surfaced after a couple of failed attempts.
- **Alternate / hidden spaces (up to 10)** — each alternate password reveals its **own separate set of shortcuts** stored in its own `Profiles/<id>/` folder. They never appear in any list; just **type that password on the lock screen to drop straight into that space**. Great for work/personal separation or sensitive links.
- Spaces auto-revert to the default on hide/re-lock.

## 🪟 Windows 11 look & feel
- Mica-style layered background, rounded window, accent selection bar, smooth pop/fade animations.
- **6 themes** — Windows 11 Dark, Windows 11 Light, Graphite, Nord, Mint, Sunset (live-switch with **Tab** or in Settings); add your own in `themes.json`.
- Flat, Windows-style lock screen.

## ⚙️ System integration
- **System-tray background app** — Open · Run command · Screenshot · Reload · Open folders · Quit.
- **Global hotkeys** (needs the optional `keyboard` package), all rebindable via a click-to-record control:
  | Action | Default |
  |---|---|
  | Open / toggle launcher | `Ctrl+Win+N` |
  | Add new shortcut | `Ctrl+Win+A` |
  | Screenshot (region) | `Ctrl+Win+S` |
  | Run command | `Ctrl+Win+R` |
- **Auto-start on Windows login** (HKCU `Run` key) — one checkbox.
- **Click-away to close** (hide on blur), with native foreground focus-grab so you can type immediately.
- **Reliable cursor focus** on the right field every time the window opens.

## ⌨️ Keyboard cheat-sheet
| Key | Action |
|---|---|
| `↑ / ↓`, `PgUp/PgDn` | Move selection |
| `Enter` | Open selected (calc → copy) |
| `Ctrl+Enter` | Open the Shortcuts folder |
| `Alt+1…9` | Launch the Nth result |
| `Ctrl+P` | Pin / unpin |
| `Ctrl+D` | Remove shortcut |
| `Ctrl+N` | Add shortcut |
| `Ctrl+R` | Command runner |
| `Tab` | Next theme |
| `Ctrl+,` | Settings |
| `Esc` | Hide |

## 🛠️ Settings (in-app)
- **General** — theme, web-search URL, max results, show paths, show on startup, hide on blur, calculator, web search, screenshots (+ copy to clipboard), command runner (+ autocorrect), auto-start.
- **Keybinds** — record any global hotkey.
- **Shortcuts** — add/edit/delete custom entries; set group/alias/hotkey/icon on any item.
- **Security** — enable lock, master password, alternate spaces.
- **Themes** — visual picker.
- **About** — version & summary.

## 📦 Packaging & distribution
- **`PyDoc.spec`** — one-file PyInstaller build (`pyinstaller PyDoc.spec` → `dist/PyDoc.exe`), bundling the web UI, offline font and themes; runtime data is created next to the exe. Frozen-aware paths.
- **`version_info.txt`** — Windows version resource embedded in the exe.
- **`install.cmd` / `uninstall.cmd`** — register/unregister auto-start and Start-Menu shortcut.
- **GitHub Actions**:
  - `pages.yml` — auto-deploy the marketing site (`site/`) to GitHub Pages.
  - `build.yml` — build `PyDoc.exe` on tag pushes and attach it to a Release.

## 🌍 Platform support
| | Window | Tray | Hotkeys | Auto-start | Screenshots |
|---|:--:|:--:|:--:|:--:|:--:|
| **Windows 10/11** | ✅ WebView2 | ✅ | ✅ | ✅ | ✅ |
| **macOS** | ✅ | ✅ | ⚠️ perms | ➖ | ✅ |
| **Linux** | ✅ GTK/Qt | ✅ | ⚠️ root | ➖ | ✅ |

## 🧩 Tech
- Pure-Python logic (`core.py`) + pywebview host (`launcher.py`) + a Windows-11 web UI (`web/`).
- Optional deps: `keyboard` (hotkeys), `pystray` + `pillow` (tray & screenshots), `pyinstaller` (build).
- Requires **Python 3.11+**.
