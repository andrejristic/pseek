#!/usr/bin/env python3
# Cross-platform PyInstaller build for the current OS. Produces:
#   Linux -> dist/pseek ; Windows -> dist/pseek.exe ; macOS -> dist/PSEEK.app
import subprocess, sys, shutil, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if shutil.which("pyinstaller") is None:
    print("PyInstaller not installed. Run: pip install pyinstaller"); sys.exit(1)
sys.exit(subprocess.call(["pyinstaller", "--noconfirm", "packaging/pseek.spec"]))
