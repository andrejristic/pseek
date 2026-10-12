#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(dirname "$HERE")"
PY="${PYTHON:-$REPO/.venv/Scripts/python.exe}"
VERSION="${1:-0.1.0}"; PKG="pseek"
STAGE="$HERE/stage-win"; OUT="$REPO/dist"
ISCC="${ISCC:-/c/Program Files (x86)/Inno Setup 6/ISCC.exe}"
COLLECT="--collect-submodules apply --collect-submodules arms --collect-submodules billing --collect-submodules chat --collect-submodules guardian --collect-submodules gui --collect-submodules inquiry --collect-submodules jobs --collect-submodules learning --collect-submodules llm --collect-submodules mailarm --collect-submodules mode2 --collect-submodules pse_kernel --collect-submodules reply --collect-submodules research --collect-submodules tracking "
HIDDEN="--hidden-import configure_source_key --hidden-import configure_user_email --hidden-import discovery --hidden-import physician --hidden-import pool --hidden-import settings --hidden-import synthesis --hidden-import theta --hidden-import workspace "
echo "== PyInstaller bundle"
rm -rf "$REPO/build/pyi" "$STAGE"
"$PY" -m PyInstaller --noconfirm --clean --onedir --windowed --name "$PKG" \
  --icon "$HERE/$PKG.ico" --paths "$REPO" $COLLECT $HIDDEN \
  --distpath "$REPO/build/pyi/dist" --workpath "$REPO/build/pyi/work" --specpath "$REPO/build/pyi" \
  "$REPO/run_pseek.py"
APPDIR="$STAGE/$PKG"; mkdir -p "$APPDIR"
cp -a "$REPO/build/pyi/dist/$PKG/." "$APPDIR/"
cp "$HERE/$PKG.ico" "$APPDIR/"; cp "$REPO/LICENSE" "$APPDIR/LICENSE.txt"; cp "$REPO/NOTICE" "$APPDIR/NOTICE.txt"
echo "== Inno Setup"; mkdir -p "$OUT"
MSYS2_ARG_CONV_EXCL="*" "$ISCC" "/DAppVersion=$VERSION" "/DSourceDir=$(cygpath -w "$APPDIR")" "/DOutDir=$(cygpath -w "$OUT")" \
  "$(cygpath -w "$HERE/$PKG.iss")"
echo "built $OUT/PSEEK-Setup-$VERSION.exe"
