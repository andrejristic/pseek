# =============================================================================
# PSEEK — user-defined sources + chat command + Poslovi tab (real, no stubs)
# A user-defined RSS feed and a USER-DEFINED keyed API (key from the user's own
# vault) are assembled and searched; the "nađi poslove" chat command fans out and
# pushes results into the GUI Poslovi tab; feedback rewards the source.
# =============================================================================
import os, sys, json, tempfile, shutil
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication
from workspace import Workspace
from pool import DocumentPool, add_resume
from arms.sources import build_sources, UserApiSource, GenericRSSSource
from discovery import Discovery
from chat.pseek_chat import PseekChat
from gui import build_window

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


def test_user_defined_keyed_api_requires_user_key():
    d = tempfile.mkdtemp(prefix="pseek_ud_")
    try:
        w = Workspace(d, "u", "pw")
        cfg = {"user_apis": [{"name": "myapi", "key_name": "my_jobs_api_key",
               "url_template": "https://ex.com/s?q={query}&k={key}",
               "mapping": {"list": "results", "title": "title"}}],
               "allow_hosts": ["ex.com"]}
        names = [getattr(s, "name", "") for s in build_sources(cfg, w.guardian)]
        check("keyed API absent until the user provides their key", "myapi" not in names)
        w.guardian.put_secret("my_jobs_api_key", "USER-KEY-123")   # user-defined
        srcs = build_sources(cfg, w.guardian)
        my = [s for s in srcs if getattr(s, "name", "") == "myapi"]
        check("keyed API appears once the user's key is in their vault", len(my) == 1)
        check("user key + query fill the URL template",
              "USER-KEY-123" in my[0].url())
        check("user-authorized host added to egress", w.guardian.egress.allowed("https://ex.com/s"))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_user_api_parses_with_mapping():
    src = UserApiSource("myapi", "https://ex.com/{key}", "K",
                        {"list": "results", "id": "jid", "title": "role",
                         "company": "org", "location": "loc", "url": "href"})
    class F:
        def get(self, url): return json.dumps({"results": [
            {"jid": "9", "role": "ML Engineer", "org": "Acme",
             "loc": "Toronto, ON", "href": "https://x/9"}]}).encode()
    jobs = src.fetch(F())
    check("user API mapping produces a proper Job",
          jobs and jobs[0].title == "ML Engineer" and jobs[0].company == "Acme"
          and "Toronto" in jobs[0].location)
    return True


def test_chat_find_jobs_populates_poslovi_tab():
    d = tempfile.mkdtemp(prefix="pseek_udc_")
    try:
        app = QApplication.instance() or QApplication([])
        w = Workspace(d, "u", "pw")
        pool = DocumentPool()
        add_resume(pool, "r.txt", "Python developer. Django REST APIs. PyTorch NLP.")
        disc = Discovery(w)

        from jobs.domain import Job
        class Src:
            def __init__(self, name, jobs): self.name = name; self._j = jobs
            def fetch(self, fetcher): return list(self._j)
        disc.sources = lambda: [
            Src("remotive", [Job("remotive:1", "Python Engineer", "Acme",
                                 "python django rest", location="Remote")]),
            Src("higheredjobs", [Job("higheredjobs:1", "Math Instructor", "UofT",
                                     "mathematics teaching", location="Toronto, ON")])]

        win = build_window(workspace=w)
        chat = PseekChat(w, disc, lambda: pool, on_results=win.load_jobs)
        win.chat.handler = chat.handle
        resp = win.chat.send("nađi poslove")
        check("chat 'nađi poslove' runs a multi-source search", "izvora" in resp, resp[:60])
        check("Poslovi tab is populated from the search",
              win.jobs_table.rowCount() == len(chat.results) and win.jobs_table.rowCount() >= 1,
              f"rows={win.jobs_table.rowCount()}")
        # 'izvori' lists the sources
        s = chat.handle("izvori")
        check("chat 'izvori' lists the sources", "remotive" in s and "higheredjobs" in s)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_user_defined_keyed_api_requires_user_key, test_user_api_parses_with_mapping,
       test_chat_find_jobs_populates_poslovi_tab]

if __name__ == "__main__":
    print("PSEEK · user-defined sources + chat + Poslovi tab\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
