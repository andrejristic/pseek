# =============================================================================
# PSEEK — P13 TESTS: GUI shell (real PySide6, offscreen, no stubs)
# The window builds with a left sidebar, a center stack, and an always-open right
# chat panel; it renders non-blank; the θ gauge paints; the font-size control
# changes and persists (default 20); the window fits within a given screen size;
# sidebar switches pages; the paywall dialog builds for a free tier.
# =============================================================================
import os, sys, tempfile, shutil
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication
from workspace import Workspace
from learning import OrganelleRegistry
from billing import EntitlementManager, TRIAL_SECONDS
from gui import build_window, ThetaGauge

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


def _nonblank(img, need=60):
    seen = set()
    for y in range(0, img.height(), 6):
        for x in range(0, img.width(), 6):
            seen.add(img.pixel(x, y))
            if len(seen) > need:
                return True
    return len(seen) > need


def test_shell_layout_and_render():
    base = tempfile.mkdtemp(prefix="pseek_gui_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(base, "user1", "pw")
        win = build_window(workspace=w)
        win.show(); app.processEvents()
        check("has left sidebar with 6 nav items", win.nav.count() == 6)
        check("center is a stacked widget of pages", win.stack.count() == 6)
        check("right chat panel present and always open", win.chat.isVisible())
        img = win.grab().toImage()
        check("window renders non-blank", _nonblank(img), f"{img.width()}x{img.height()}")
        os.makedirs(os.path.join(ROOT, "previews"), exist_ok=True)
        win.grab().save(os.path.join(ROOT, "previews", "shell.png"))
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_theta_gauge_renders():
    app = QApplication.instance() or QApplication([])
    g = ThetaGauge(); g.resize(240, 150); g.set_theta(62.0); g.show(); app.processEvents()
    img = g.grab().toImage()
    check("θ gauge paints (non-blank)", _nonblank(img, need=8))


def test_font_default_20_change_persist():
    base = tempfile.mkdtemp(prefix="pseek_gui2_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(base, "user1", "pw")
        win = build_window(workspace=w)
        check("font default is 20", win.settings.font_size == 20)
        win.change_font(+3)
        check("font size increases and persists", win.settings.font_size == 23
              and w.settings.font_size == 23)
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_window_fits_screen():
    base = tempfile.mkdtemp(prefix="pseek_gui3_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(base, "user1", "pw")
        win = build_window(workspace=w)
        win.fit_to_screen(1024, 640)          # small display
        check("window clamps to fit within the screen",
              win.width() <= 1024 and win.height() <= 640,
              f"{win.width()}x{win.height()}")
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_sidebar_switches_pages():
    base = tempfile.mkdtemp(prefix="pseek_gui4_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(base, "user1", "pw")
        win = build_window(workspace=w)
        win.nav.setCurrentRow(2)
        check("selecting a nav item switches the center page",
              win.stack.currentIndex() == 2)
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_paywall_builds_for_free_tier():
    base = tempfile.mkdtemp(prefix="pseek_gui5_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(base, "user1", "pw")
        reg = OrganelleRegistry(os.path.join(base, "o.json"))
        clock = [1000.0]
        ent = EntitlementManager(reg, now_fn=lambda: clock[0])
        clock[0] += TRIAL_SECONDS + 1                     # out of trial → free
        win = build_window(workspace=w, entitlements=ent)
        dlg = win.maybe_show_paywall()
        check("paywall dialog is shown for a free (post-trial) user", dlg is not None)
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


ALL = [test_shell_layout_and_render, test_theta_gauge_renders,
       test_font_default_20_change_persist, test_window_fits_screen,
       test_sidebar_switches_pages, test_paywall_builds_for_free_tier]

if __name__ == "__main__":
    print("PSEEK · P13 GUI shell tests (offscreen)\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
