#!/usr/bin/env bash
# Downloads the official llama.cpp Android arm64 release, keeps only what
# llama-server needs, strips debug symbols, and places it in jniLibs so it
# is installed into the app's nativeLibraryDir (and therefore executable).
#
# Used by CI. Env:
#   LLAMA_TAG     llama.cpp release tag (default below — tested on the target Chromebook)
#   LLAMA_SHA256  optional sha256 of the tarball; verified when set
#   ANDROID_NDK_LATEST_HOME / ANDROID_NDK_HOME  for llvm-strip (preinstalled on GitHub runners)
set -euo pipefail

LLAMA_TAG="${LLAMA_TAG:-b12807}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/app/src/main/jniLibs/arm64-v8a"
URL="https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_TAG}/llama-${LLAMA_TAG}-bin-android-arm64.tar.gz"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "Fetching $URL"
curl -fsSL "$URL" -o "$WORK/llama.tgz"
if [ -n "${LLAMA_SHA256:-}" ]; then
  echo "${LLAMA_SHA256}  $WORK/llama.tgz" | sha256sum -c -
fi
tar xzf "$WORK/llama.tgz" -C "$WORK"
SRC="$WORK/llama-${LLAMA_TAG}"

rm -rf "$OUT"
mkdir -p "$OUT"

# The executable must be named lib*.so to be extracted to nativeLibraryDir.
cp "$SRC/llama-server" "$OUT/libllama_server.so"
cp "$SRC"/libllama.so \
   "$SRC"/libllama-common.so \
   "$SRC"/libllama-server-impl.so \
   "$SRC"/libmtmd.so \
   "$SRC"/libggml.so \
   "$SRC"/libggml-base.so \
   "$SRC"/libggml-cpu-android_*.so \
   "$OUT/"

# MIT license text must ship with the binaries.
LIC_DIR="$ROOT/app/src/main/assets/licenses"
mkdir -p "$LIC_DIR"
cp "$SRC/LICENSE" "$LIC_DIR/llama.cpp-LICENSE.txt"

NDK="${ANDROID_NDK_LATEST_HOME:-${ANDROID_NDK_HOME:-}}"
STRIP="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"
if [ -x "$STRIP" ]; then
  "$STRIP" --strip-unneeded "$OUT"/*.so
else
  echo "WARNING: llvm-strip not found, libraries stay unstripped (~260 MB)" >&2
fi

ls -la "$OUT"
du -sh "$OUT"
