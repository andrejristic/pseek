# PyInstaller spec for PSEEK — build the native binary on each OS:
#   Linux : pyinstaller pseek.spec           -> dist/pseek
#   Windows: pyinstaller pseek.spec          -> dist\pseek.exe   (.exe output)
#   macOS : pyinstaller pseek.spec           -> dist/PSEEK.app    (.app output)
# Run from the project root.
block_cipher = None
a = Analysis(
    ['run_pseek.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['PySide6', 'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtCore'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
          name='pseek', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=True, console=False)
app = BUNDLE(exe, name='PSEEK.app', icon=None, bundle_identifier='com.zeravatech.pseek')
