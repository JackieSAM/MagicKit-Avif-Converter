#!/usr/bin/env bash
# Builds a native MagicKit app/binary on macOS or Linux.
# Run this on the OS you want the build for - PyInstaller does not
# cross-compile (a Windows .exe must be built on Windows; see build_windows.bat).
set -e
cd "$(dirname "$0")"

echo "=== MagicKit build: creating clean virtual environment ==="
python3 -m venv build_venv
source build_venv/bin/activate

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Building MagicKit ==="
pyinstaller --noconfirm --clean MagicKit.spec

echo
echo "=== Done ==="
echo "Your build is in: dist/MagicKit/"
echo "Run it with: ./dist/MagicKit/MagicKit"
