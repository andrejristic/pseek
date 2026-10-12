@echo off
REM PSEEK Windows build (.exe). Run on Windows with Python + PySide6 installed.
pip install pyinstaller PySide6
pyinstaller --noconfirm packaging\pseek.spec
echo Output: dist\pseek.exe
