# =============================================================================
# PSEEK — OPT-IN FEATURES TESTS (real PySide6, offscreen, no stubs)
# Auto-search and feedback-learning are BOTH OFF by default and persist. Toggling
# auto-search on starts a timer whose tick runs the search; off stops it. Table
# feedback rewards the source ONLY when "learn from ratings" is enabled; otherwise
# it is inert. Both toggles survive a reopen.
# =============================================================================
import os, sys, tempfile, shutil
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from workspace import Workspace
from gui import build_window

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


class Rec:                       # a minimal record shape the table/feedback use
    def __init__(self, jid, title="Job", company="Co"):
        self.job_id = jid; self.title = title; self.company = company
        self.verdict_code = "APPLY"; self.fit_by_profile = {"pool": 0.5}
        self.how_to_apply = {"location": "Remote"}


def test_defaults_off():
    d = tempfile.mkdtemp(prefix="pseek_opt_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(d, "u", "pw")
        win = build_window(workspace=w)
        check("auto-search checkbox OFF by default", not win.cb_auto.isChecked())
        check("feedback-learning checkbox OFF by default", not win.cb_learn.isChecked())
        check("auto timer not running at start", not win.auto_timer.isActive())
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_feedback_gated_by_learning_toggle():
    d = tempfile.mkdtemp(prefix="pseek_opt2_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(d, "u", "pw")
        win = build_window(workspace=w)
        got = []
        win.feedback_cb = lambda rec, action: got.append((rec.job_id, action))
        win.load_jobs([Rec("remotive:1")])
        win.jobs_table.selectRow(0)
        # learning OFF → approve does nothing
        win._feedback("approve")
        check("approve does NOTHING while learning is off", got == [], str(got))
        # turn learning ON → approve rewards the source
        win.cb_learn.setChecked(True)
        win._feedback("approve")
        check("approve rewards the source once learning is on",
              got == [("remotive:1", "approve")], str(got))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_auto_search_toggle_runs_and_stops():
    d = tempfile.mkdtemp(prefix="pseek_opt3_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(d, "u", "pw")
        win = build_window(workspace=w)
        ticks = {"n": 0}
        win.search_cb = lambda: ticks.__setitem__("n", ticks["n"] + 1)
        win.cb_auto.setChecked(True)                 # user turns it on
        check("enabling auto-search starts the timer", win.auto_timer.isActive())
        win.auto_timer.setInterval(60)               # speed up for the test
        win.auto_timer.start()
        QTest.qWait(220)
        check("auto-search tick actually runs the search", ticks["n"] >= 1, f"ticks={ticks['n']}")
        win.cb_auto.setChecked(False)                # user turns it off
        check("disabling auto-search stops the timer", not win.auto_timer.isActive())
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_toggles_persist():
    d = tempfile.mkdtemp(prefix="pseek_opt4_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(d, "u", "pw")
        win = build_window(workspace=w)
        win.cb_learn.setChecked(True)
        win.cb_auto.setChecked(True)
        w2 = Workspace(d, "u", "pw")                 # reopen (settings persisted)
        win2 = build_window(workspace=w2)
        check("both toggles restore from saved settings",
              win2.cb_learn.isChecked() and win2.cb_auto.isChecked())
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_defaults_off, test_feedback_gated_by_learning_toggle,
       test_auto_search_toggle_runs_and_stops, test_toggles_persist]

if __name__ == "__main__":
    print("PSEEK · opt-in features tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
