#!/usr/bin/env python3
"""
PyDoc · build script
============================
Packages PyDoc into a single Windows .exe with PyInstaller, bundling
the web UI, vendored windows-ui-fabric assets, themes and (optionally) your
Shortcuts/Icons folders.

Usage:
    pip install pyinstaller
    python build.py            # build dist/PyDoc.exe
    python build.py --onedir   # folder build (faster start, easier to debug)
    python build.py --console  # show a console window (for debugging)

Output: dist/PyDoc(.exe)
"""

import os
import sys
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = ";" if os.name == "nt" else ":"   # PyInstaller --add-data separator


def add_data(src, dest):
    return f"--add-data={os.path.join(HERE, src)}{SEP}{dest}"


def main():
    onefile = "--onedir" not in sys.argv
    console = "--console" in sys.argv

    try:
        import PyInstaller  # noqa: F401
    except Exception:
        print("PyInstaller not found. Install it with:\n    pip install pyinstaller")
        sys.exit(1)

    # clean previous artefacts
    for d in ("build", "dist"):
        p = os.path.join(HERE, d)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    spec = os.path.join(HERE, "PyDoc.spec")
    if os.path.exists(spec):
        os.remove(spec)

    args = [
        sys.executable, "-m", "PyInstaller",
        "--name=PyDoc",
        "--noconfirm",
        "--clean",
        "--onefile" if onefile else "--onedir",
        "--windowed" if not console else "--console",
        # bundle the web UI + assets so the exe is self-contained
        add_data("web", "web"),
        add_data("themes.json", "."),
        # hidden imports that PyInstaller may miss
        "--hidden-import=webview",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=keyboard",
        "--collect-all=webview",
    ]

    # optional icon for the exe
    ico = os.path.join(HERE, "Icons", "app.ico")
    if os.path.exists(ico):
        args.append(f"--icon={ico}")

    # include a starter Shortcuts folder if present
    if os.path.isdir(os.path.join(HERE, "Shortcuts")):
        args.append(add_data("Shortcuts", "Shortcuts"))

    args.append(os.path.join(HERE, "launcher.py"))

    print("Running PyInstaller:\n  " + " ".join(args) + "\n")
    rc = subprocess.call(args)
    if rc == 0:
        out = "PyDoc.exe" if os.name == "nt" else "PyDoc"
        print(f"\n✅ Build complete → dist/{out}")
        print("Note: config.json / shortcuts.json / store.json / Shortcuts /")
        print("Icons are created next to the exe at first run.")
    else:
        print(f"\n❌ Build failed (exit {rc}).")
    sys.exit(rc)


if __name__ == "__main__":
    main()
