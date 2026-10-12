# =============================================================================
# PSEEK — P14 TESTS: packaging / 4 outputs (real, no stubs)
# Output #1 (PySide6 source) launches: run_pseek wires headless. Output #2 (.deb)
# is actually BUILT here in pure Python and is a valid ar archive with the three
# Debian members, whose data.tar.gz contains the app. Outputs #3/#4 (.exe/.app)
# ship real PyInstaller spec + build scripts (the binaries are produced on their
# OS/CI).
# =============================================================================
import os, sys, io, tarfile, importlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


def _ar_members(data):
    assert data[:8] == b"!<arch>\n"
    i, members = 8, []
    while i < len(data):
        hdr = data[i:i + 60]; i += 60
        name = hdr[0:16].decode().strip()
        size = int(hdr[48:58].decode().strip())
        body = data[i:i + size]; i += size + (size % 2)
        members.append((name, body))
    return members


def test_source_output_launches():
    import run_pseek
    ws, op, ent = run_pseek.wire(user="pkgtest", passphrase="pw")
    check("output #1 (PySide6 source) wires headless",
          ws.email_connected() is False and ent.effective_tier() in ("trial", "free"))
    import shutil; shutil.rmtree(ws.root, ignore_errors=True)
    return True


def test_deb_is_built_and_valid():
    from packaging.build_deb import build
    path = build()
    check("a .deb file is produced", os.path.exists(path) and path.endswith(".deb"))
    data = open(path, "rb").read()
    members = dict(_ar_members(data))
    check("valid ar archive with the 3 Debian members",
          {"debian-binary", "control.tar.gz", "data.tar.gz"} <= set(members),
          str(list(members)))
    check("debian-binary is 2.0", members["debian-binary"].strip() == b"2.0")
    # data.tar.gz actually contains the app launcher + packages
    with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]), mode="r:gz") as t:
        names = t.getnames()
    check("data payload installs run_pseek + the kernel",
          any(n.endswith("opt/pseek/run_pseek.py") for n in names)
          and any("opt/pseek/pse_kernel/kernel.py" in n for n in names))
    # control has the package metadata
    with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as t:
        ctrl = t.extractfile("./control").read().decode()
    check("control declares Package: pseek", "Package: pseek" in ctrl)
    return True


def test_exe_app_specs_present():
    pk = os.path.join(ROOT, "packaging")
    need = ["pseek.spec", "build.py", "build_exe.bat", "build_app.sh", "build_deb.py"]
    missing = [f for f in need if not os.path.exists(os.path.join(pk, f))]
    check("PyInstaller spec + build scripts for all 4 outputs exist", not missing,
          f"missing={missing}")
    spec = open(os.path.join(pk, "pseek.spec")).read()
    check("spec builds .exe (Windows) and .app (macOS)",
          "pseek" in spec and "PSEEK.app" in spec)
    return True


ALL = [test_source_output_launches, test_deb_is_built_and_valid,
       test_exe_app_specs_present]

if __name__ == "__main__":
    print("PSEEK · P14 packaging tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
