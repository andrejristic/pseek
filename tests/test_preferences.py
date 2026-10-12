# =============================================================================
# PSEEK — P5 TESTS: preference learning (real, no stubs)
# Approving Python roles and rejecting sales roles bends the ranking toward
# Python; a brand-new Python job scores above a sales job; the model persists per
# user and reloads.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jobs.domain import Job
from learning import OrganelleRegistry, PreferenceModel

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

PY1 = Job("py1", "Python Engineer", "Acme", "python django backend api", location="Remote")
PY2 = Job("py2", "Backend Python Developer", "Beta", "python postgresql api", location="Remote")
SALES1 = Job("s1", "Sales Rep", "Gamma", "sales quota cold calling crm", location="Remote")
SALES2 = Job("s2", "Account Executive", "Delta", "sales pipeline crm quota", location="Remote")


def test_learns_from_signals_and_reranks():
    d = tempfile.mkdtemp(prefix="pseek_pref_")
    try:
        reg = OrganelleRegistry(os.path.join(d, "org.json"))
        m = PreferenceModel(reg)
        m.record(PY1, "approve")
        m.record(SALES1, "reject")
        # a fresh Python job now outscores a fresh sales job
        check("learned: new Python job scores above new sales job",
              m.score(PY2) > m.score(SALES2),
              f"py={m.score(PY2):.2f} sales={m.score(SALES2):.2f}")
        ranked = m.rerank([SALES2, PY2])
        check("rerank puts the preferred (Python) job first", ranked[0].job_id == "py2")
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_persists_per_user():
    d = tempfile.mkdtemp(prefix="pseek_pref2_")
    try:
        path = os.path.join(d, "org.json")
        reg = OrganelleRegistry(path)
        m = PreferenceModel(reg)
        m.record(PY1, "approve"); m.record(PY1, "approve")
        s_before = m.score(PY2)
        m2 = PreferenceModel(OrganelleRegistry(path))     # reopen
        check("learned weights persist across sessions", abs(m2.score(PY2) - s_before) < 1e-9,
              f"{m2.score(PY2):.2f} vs {s_before:.2f}")
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_only_reranks_never_fabricates():
    # the model returns scores/order only — it has no path to change job content
    d = tempfile.mkdtemp(prefix="pseek_pref3_")
    try:
        m = PreferenceModel(OrganelleRegistry(os.path.join(d, "o.json")))
        out = m.rerank([PY1, SALES1])
        check("rerank returns the same jobs, only reordered",
              {j.job_id for j in out} == {"py1", "s1"} and len(out) == 2)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_learns_from_signals_and_reranks, test_persists_per_user,
       test_only_reranks_never_fabricates]

if __name__ == "__main__":
    print("PSEEK · P5 preference learning tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
