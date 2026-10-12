#!/usr/bin/env python3
# =============================================================================
# PSEEK — build a Debian package (.deb) in PURE PYTHON (no dpkg-deb needed)
# A .deb is an `ar` archive of three members: debian-binary, control.tar.gz,
# data.tar.gz. We stage the app under /opt/pseek, add a /usr/bin/pseek launcher
# and a desktop entry, then assemble a real, installable package.
#
#   python3 packaging/build_deb.py          -> dist/pseek_<ver>_all.deb
# =============================================================================
import io
import os
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "0.1.0"
APP_PKGS = ["pse_kernel", "jobs", "guardian", "arms", "learning", "chat",
            "tracking", "mailarm", "llm", "research", "inquiry", "apply",
            "reply", "billing", "mode2", "gui"]
APP_FILES = ["run_pseek.py", "workspace.py", "settings.py", "theta.py",
             "physician.py", "pool.py", "synthesis.py"]

CONTROL = f"""Package: pseek
Version: {VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pip
Maintainer: ZeravaTech <pseek@zeravatech.example>
Description: PSEEK — an LLM-driven job-search & apply copilot on the PSE kernel.
 Combines your résumés and cover letters into the best honest pitch per job,
 governed by the PSE kernel (θ, physician, two floors). You decide; it does the rest.
"""

POSTINST = """#!/bin/sh
set -e
python3 -m pip install --quiet --upgrade PySide6 >/dev/null 2>&1 || true
echo "PSEEK installed. Run: pseek"
exit 0
"""

LAUNCHER = """#!/bin/sh
exec python3 /opt/pseek/run_pseek.py "$@"
"""

DESKTOP = """[Desktop Entry]
Name=PSEEK
Comment=Job-search & apply copilot
Exec=pseek
Terminal=false
Type=Application
Categories=Utility;
"""


def _ar_header(name, size, mtime=0, mode=0o100644):
    h = name.ljust(16)[:16]
    h += str(mtime).ljust(12)[:12]
    h += "0".ljust(6)          # uid
    h += "0".ljust(6)          # gid
    h += oct(mode)[2:].ljust(8)[:8]
    h += str(size).ljust(10)[:10]
    h += "`\n"
    return h.encode()


def _ar(members):
    out = b"!<arch>\n"
    for name, data in members:
        out += _ar_header(name, len(data))
        out += data
        if len(data) % 2:
            out += b"\n"       # 2-byte alignment
    return out


def _add_bytes(tar, arcname, data, mode=0o644):
    ti = tarfile.TarInfo(arcname)
    ti.size = len(data)
    ti.mtime = 0
    ti.mode = mode
    tar.addfile(ti, io.BytesIO(data))


def _add_tree(tar, src_abs, arc_prefix):
    for dirpath, _dirs, files in os.walk(src_abs):
        if "__pycache__" in dirpath:
            continue
        for fn in files:
            if fn.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, src_abs)
            with open(full, "rb") as fh:
                _add_bytes(tar, f"{arc_prefix}/{rel}", fh.read())


def build():
    # data.tar.gz — the installed tree
    data_buf = io.BytesIO()
    with tarfile.open(fileobj=data_buf, mode="w:gz") as tar:
        for pkg in APP_PKGS:
            p = os.path.join(ROOT, pkg)
            if os.path.isdir(p):
                _add_tree(tar, p, f"./opt/pseek/{pkg}")
        for f in APP_FILES:
            fp = os.path.join(ROOT, f)
            if os.path.isfile(fp):
                _add_bytes(tar, f"./opt/pseek/{f}", open(fp, "rb").read())
        _add_bytes(tar, "./usr/bin/pseek", LAUNCHER.encode(), mode=0o755)
        _add_bytes(tar, "./usr/share/applications/pseek.desktop", DESKTOP.encode())
    data_tar = data_buf.getvalue()

    # control.tar.gz
    ctrl_buf = io.BytesIO()
    with tarfile.open(fileobj=ctrl_buf, mode="w:gz") as tar:
        _add_bytes(tar, "./control", CONTROL.encode())
        _add_bytes(tar, "./postinst", POSTINST.encode(), mode=0o755)
    control_tar = ctrl_buf.getvalue()

    deb = _ar([("debian-binary", b"2.0\n"),
               ("control.tar.gz", control_tar),
               ("data.tar.gz", data_tar)])

    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"pseek_{VERSION}_all.deb")
    with open(out, "wb") as fh:
        fh.write(deb)
    return out


if __name__ == "__main__":
    path = build()
    print("built:", path, f"({os.path.getsize(path)} bytes)")
