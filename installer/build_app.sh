#!/bin/sh
# PSEEK macOS build (.app). Run on macOS with Python + PySide6 installed.
pip3 install pyinstaller PySide6
pyinstaller --noconfirm packaging/pseek.spec
echo "Output: dist/PSEEK.app"
