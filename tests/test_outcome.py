# =============================================================================
# PSEEK — P7 TESTS: outcome learning + résumé/cover edit suggestions (no stubs)
# The signal separates responded from ghosted keywords; a response-linked keyword
# buried in the pool yields a "lead with it" suggestion; an absent one yields a
# truthful "consider adding IF TRUE"; nothing fabricates.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jobs.domain import Job
from learning import OrganelleRegistry, OutcomeLearner
from pool import DocumentPool, add_resume

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

RESPONDED = [Job("r1", "ML Engineer", "A", "python kubernetes pytorch nlp"),
             Job("r2", "Backend", "B", "python kubernetes docker")]
GHOSTED = [Job("g1", "Sales", "C", "sales crm quota"),
           Job("g2", "Clerk", "D", "filing admin data entry")]

# a résumé where 'kubernetes' is buried far below the first lines
RESUME = ("Summary line one about teaching.\nSecond line about mathematics.\n"
          "Third line about tutoring students.\nFourth line about lesson plans.\n"
          "Deployed services with Kubernetes and Docker in production.\n"
          "Python programming for data pipelines.")


def _pool():
    p = DocumentPool()
    add_resume(p, "resume.txt", RESUME)
    return p


def test_response_signal_separates():
    learner = OutcomeLearner()
    sig = learner.response_signal(RESPONDED, GHOSTED)
    check("signal keeps response keywords", "python" in sig and "kubernetes" in sig)
    check("signal drops ghost-only keywords", "sales" not in sig and "crm" not in sig,
          str(sig[:6]))
    return True


def test_lead_with_buried_keyword():
    d = tempfile.mkdtemp(prefix="pseek_out_")
    try:
        reg = OrganelleRegistry(os.path.join(d, "o.json"))
        learner = OutcomeLearner(reg)
        sug = learner.suggest_edits(_pool(), RESPONDED, GHOSTED)
        lead = [s for s in sug if s["type"] == "lead_with"]
        check("suggests leading with a buried, response-linked line",
              any(s["keyword"] == "kubernetes" for s in lead),
              str([s["keyword"] for s in lead]))
        # every 'lead_with' points at a real line that exists in the pool
        ids = {ln.line_id for ln in _pool().all_lines()}
        check("lead-with suggestions reference real résumé lines",
              all(s["line_id"] in ids for s in lead))
        check("advice recorded as an organelle", reg.count() >= 1)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_consider_adding_absent_keyword_is_truthful():
    learner = OutcomeLearner()
    # 'pytorch' and 'nlp' are response keywords absent from the résumé
    sug = learner.suggest_edits(_pool(), RESPONDED, GHOSTED)
    adds = [s for s in sug if s["type"] == "consider_adding"]
    check("absent response keyword → 'consider adding IF TRUE' (no fabrication)",
          any(s["keyword"] in ("pytorch", "nlp") for s in adds)
          and all("IF TRUE" in s["why"] for s in adds), str([s["keyword"] for s in adds]))
    return True


ALL = [test_response_signal_separates, test_lead_with_buried_keyword,
       test_consider_adding_absent_keyword_is_truthful]

if __name__ == "__main__":
    print("PSEEK · P7 outcome learning tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
