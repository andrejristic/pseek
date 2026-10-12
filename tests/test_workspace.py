# =============================================================================
# PSEEK — P0 TESTS: per-user workspace + settings (real, no stubs)
# Two users are fully isolated (separate encrypted vaults + jailed writes); the
# font-size setting defaults to 20, is clamped and persists; the kernel moat is
# reused verbatim; nothing depends on a hardcoded person.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from workspace import Workspace
from settings import AppSettings
from guardian import GuardianViolation, VaultError

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

def expect(fn, exc):
    try:
        fn(); return False
    except exc:
        return True
    except Exception:
        return False


def test_users_are_isolated():
    base = tempfile.mkdtemp(prefix="pseek_ws_")
    try:
        a = Workspace(base, "alice@example.com", "pass-A")
        b = Workspace(base, "bob@example.com", "pass-B")
        check("each user gets a separate workspace dir", a.root != b.root
              and os.path.isdir(a.root) and os.path.isdir(b.root))
        # a's email secret is invisible to b (separate vaults)
        a.connect_email("alice@gmail.com", "alice-app-pw")
        check("user A email stored", a.email_connected())
        check("user B cannot see user A's secret", not b.email_connected())
        # alice stored a secret, so her vault exists; a wrong passphrase must fail
        check("vault needs the right passphrase",
              expect(lambda: Workspace(base, "alice@example.com", "WRONG"), VaultError))
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_guardian_jail_confines_to_user_dir():
    base = tempfile.mkdtemp(prefix="pseek_ws2_")
    try:
        a = Workspace(base, "alice", "pw")
        b = Workspace(base, "bob", "pw")
        # alice's guardian may write in her dir, but not into bob's
        check("write inside own workspace allowed",
              bool(a.guardian.guard_write(a.path("data", "x.json"))))
        check("write into another user's workspace blocked",
              expect(lambda: a.guardian.guard_write(os.path.join(b.root, "steal.json")),
                     GuardianViolation))
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_font_setting_default_20_clamp_persist():
    base = tempfile.mkdtemp(prefix="pseek_ws3_")
    try:
        a = Workspace(base, "alice", "pw")
        check("font size defaults to 20", a.settings.font_size == 20)
        a.settings.set_font_size(26)
        check("font size changeable", a.settings.font_size == 26)
        a.settings.set_font_size(999)
        check("font size clamped to max", a.settings.font_size == a.settings.get("font_max"))
        # persists across reopen
        s2 = AppSettings(a.path("settings.json"))
        check("font size persists across sessions", s2.font_size == a.settings.get("font_max"))
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_no_hardcoded_person_and_moat_reused():
    # the kernel is importable and usable without any Andrej-specific path
    from pse_kernel import evaluate, NullAudit, ATTRACTORS
    check("kernel moat reused (attractors present)",
          set(ATTRACTORS) == {"narcissistic", "codependent", "schizoid"})
    # workspace needs no ~/Desktop/123 or any person
    base = tempfile.mkdtemp(prefix="pseek_ws4_")
    try:
        w = Workspace(base, "anyone", "pw")
        check("workspace builds with no hardcoded person / résumé path",
              os.path.isdir(w.docs_dir))
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


ALL = [test_users_are_isolated, test_guardian_jail_confines_to_user_dir,
       test_font_setting_default_20_clamp_persist, test_no_hardcoded_person_and_moat_reused]

if __name__ == "__main__":
    print("PSEEK · P0 workspace + settings tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
