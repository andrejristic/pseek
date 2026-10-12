#!/usr/bin/env bash
# Build pseek_<version>_amd64.deb (self-contained PyInstaller bundle, GUI).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(dirname "$HERE")"
PY="${PYTHON:-$REPO/.venv/bin/python}"
VERSION="${1:-0.1.0}"; ARCH="${ARCH:-amd64}"; PKG="pseek"
STAGE="$HERE/stage"; OUT="$REPO/dist"
COLLECT="--collect-submodules apply --collect-submodules arms --collect-submodules billing --collect-submodules chat --collect-submodules guardian --collect-submodules gui --collect-submodules inquiry --collect-submodules jobs --collect-submodules learning --collect-submodules llm --collect-submodules mailarm --collect-submodules mode2 --collect-submodules pse_kernel --collect-submodules reply --collect-submodules research --collect-submodules tracking "
HIDDEN="--hidden-import configure_source_key --hidden-import configure_user_email --hidden-import discovery --hidden-import physician --hidden-import pool --hidden-import settings --hidden-import synthesis --hidden-import theta --hidden-import workspace "
echo "== PyInstaller bundle"
rm -rf "$REPO/build/pyi" "$STAGE"
"$PY" -m PyInstaller --noconfirm --clean --onedir --name "$PKG" \
  --paths "$REPO" $COLLECT $HIDDEN \
  --distpath "$REPO/build/pyi/dist" --workpath "$REPO/build/pyi/work" --specpath "$REPO/build/pyi" \
  "$REPO/run_pseek.py"
APPDIR="$STAGE/opt/$PKG"; mkdir -p "$APPDIR"
cp -a "$REPO/build/pyi/dist/$PKG/." "$APPDIR/"
cp "$REPO/LICENSE" "$APPDIR/LICENSE"; cp "$REPO/NOTICE" "$APPDIR/NOTICE"
mkdir -p "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/256x256/apps" "$STAGE/usr/share/doc/$PKG" "$STAGE/DEBIAN"
ln -s "/opt/$PKG/$PKG" "$STAGE/usr/bin/$PKG"
cp "$HERE/$PKG.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/$PKG.png"
cp "$REPO/LICENSE" "$STAGE/usr/share/doc/$PKG/LICENSE"; cp "$REPO/NOTICE" "$STAGE/usr/share/doc/$PKG/NOTICE"
cat > "$STAGE/usr/share/applications/$PKG.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=PSEEK
Comment=A guarded job-search operator
Exec=$PKG
Icon=$PKG
Terminal=false
Categories=Office;Utility;
DESK
SIZE="$(du -sk "$STAGE/opt" "$STAGE/usr" | awk '{s+=$1} END{print s}')"
cat > "$STAGE/DEBIAN/control" <<CTL
Package: $PKG
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Installed-Size: $SIZE
Maintainer: Andrej Ristic <andrej.s.ristic@gmail.com>
Depends: libc6 (>= 2.34), libgl1, libegl1, libfontconfig1, libxkbcommon0, libdbus-1-3
Homepage: https://github.com/andrejristic/pseek
Description: PSEEK - a guarded job-search operator
 A desktop job-search assistant with a PSE Guardian over its file access and
 network egress: it harvests postings, drafts applications and tracks replies,
 keeping each workspace isolated and your keys off the wire.
CTL
echo "== dpkg-deb"; mkdir -p "$OUT"
DEB="$OUT/${PKG}_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "$DEB"; echo "built $DEB"
