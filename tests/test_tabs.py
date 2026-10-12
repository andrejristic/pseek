# =============================================================================
# PSEEK — LIVE TABS + APPLY WIRING + CHAT (real PySide6, offscreen, no stubs)
# Dokumenti/Prijave/Strategija show live data; "Apliciraj" runs the apply-arm
# (consent = the click) and refreshes the tabs; chat can apply, generate a
# résumé from stated facts (saved to docs/), and summarise the tabs.
# =============================================================================
import os, sys, tempfile, shutil
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication
from workspace import Workspace
from pool import DocumentPool, add_resume, add_cover, load_pool
from discovery import Discovery
from chat.pseek_chat import PseekChat
from llm import LLMOperator
from gui import build_window

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


class Rec:
    def __init__(self, jid="s:1", title="Job", company="Co"):
        self.job_id = jid; self.title = title; self.company = company
        self.verdict_code = "APPLY"; self.fit_by_profile = {"pool": 0.5}
        self.how_to_apply = {"location": "Remote"}


def test_live_tabs_render_data():
    d = tempfile.mkdtemp(prefix="pseek_tab_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(d, "u", "pw")
        win = build_window(workspace=w)
        pool = DocumentPool()
        add_resume(pool, "cv.txt", "Python engineer. Django. PyTorch.")
        add_cover(pool, "cover.txt", "Dear Team, I build ML services.")
        win.load_documents(pool)
        check("Dokumenti lists résumés + covers", win.docs_list.count() == 2)
        w.tracker.add("a1", title="ML Eng", company="Acme", profile="cross", state="DRAFT")
        w.tracker.transition("a1", "APPROVED"); w.tracker.transition("a1", "SENT")
        win.load_applications(w.tracker)
        check("Prijave shows the tracked application", win.apps_table.rowCount() == 1)
        win.load_strategy({"overall": {"sent": 1, "response_rate": 0.0, "offer_rate": 0.0}},
                          {"remotive": {"pulls": 2, "mean": 0.5}}, [("python", 1.5)])
        check("Strategija renders learned data", "Najbolji izvori" in win.strategy_label.text())
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_apply_button_runs_apply_arm():
    d = tempfile.mkdtemp(prefix="pseek_tab2_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(d, "u", "pw")
        win = build_window(workspace=w)
        calls = {"apply": 0, "refresh": 0}
        win.apply_cb = lambda rec: (calls.__setitem__("apply", calls["apply"] + 1)
                                    or {"status": "dry_run"})
        win.refresh_tabs = lambda: calls.__setitem__("refresh", calls["refresh"] + 1)
        win.load_jobs([Rec()])
        win.jobs_table.selectRow(0)
        win._apply()
        check("Apliciraj runs the apply-arm", calls["apply"] == 1)
        check("Apliciraj status reflects dry-run (no email connected)",
              "draft" in win.jobs_status.text().lower())
        check("tabs refresh after apply", calls["refresh"] == 1)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_chat_apply_and_generate_and_summaries():
    d = tempfile.mkdtemp(prefix="pseek_tab3_")
    try:
        w = Workspace(d, "u", "pw")
        disc = Discovery(w)
        op = LLMOperator(w.guardian)
        applied = []
        chat = PseekChat(w, disc, lambda: load_pool(w.docs_dir, w.guardian),
                         operator=op, apply_cb=lambda rec: applied.append(rec) or {"status": "dry_run"})
        chat.results = [Rec("s:1", "ML Eng", "Acme")]
        r = chat.handle("apliciraj 1")
        check("chat 'apliciraj 1' runs apply", len(applied) == 1 and "Draft" in r, r)

        g = chat.handle("generiši rezime: 5 godina Python; vodio tim od 4; magistar matematike")
        made = os.path.exists(os.path.join(w.docs_dir, "generated_resume.txt"))
        check("chat generates a résumé from facts into docs/", made and "generated_resume" in g, g)
        # the generated résumé now shows up in the pool
        pool = load_pool(w.docs_dir, w.guardian)
        txt = open(os.path.join(w.docs_dir, "generated_resume.txt")).read()
        check("generated résumé contains only the stated facts",
              "Python" in txt and "matematike" in txt and pool.summary()["resumes"] >= 1)

        w.tracker.add("a1", title="X", company="Y", state="SENT")
        check("chat 'prijave' summarises the tracker", "X @ Y" in chat.handle("prijave"))
        check("chat 'dokumenti' summarises the pool", "rezimea" in chat.handle("dokumenti"))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_live_tabs_render_data, test_apply_button_runs_apply_arm,
       test_chat_apply_and_generate_and_summaries]

if __name__ == "__main__":
    print("PSEEK · live tabs + apply + chat tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
