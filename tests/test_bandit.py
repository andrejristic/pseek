# =============================================================================
# PSEEK — P6 TESTS: query/discovery bandit (real, no stubs)
# UCB explores an un-pulled arm before an already-pulled one, then favours the
# arm with the best reward; query expansion leans into terms from accepted jobs
# and prunes reject-only terms; the bandit persists per user.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jobs.domain import Job
from learning import OrganelleRegistry
from learning.bandit import QueryBandit, suggest_queries

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


def test_explores_unpulled_then_exploits_best():
    d = tempfile.mkdtemp(prefix="pseek_ban_")
    try:
        reg = OrganelleRegistry(os.path.join(d, "o.json"))
        b = QueryBandit(reg)
        b.add_arm("remoteok:python"); b.add_arm("adzuna:sales")
        # pull both so they have finite UCB
        b.update("remoteok:python", 1.0); b.update("adzuna:sales", 0.0)
        b.add_arm("greenhouse:ml")                     # brand-new, unpulled
        check("un-pulled arm is explored before pulled ones",
              b.select() == "greenhouse:ml", b.select())
        # once all are pulled, the best-rewarded arm wins
        b.update("greenhouse:ml", 0.0)
        b.update("remoteok:python", 1.0)               # keep rewarding python
        check("favours the arm with the best reward", b.select() == "remoteok:python",
              str(b.stats()))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_query_expansion():
    acc = [Job("1", "Python Developer", "A", "python django rest api postgresql"),
           Job("2", "Backend Engineer", "B", "python api microservices")]
    rej = [Job("3", "Sales Rep", "C", "sales crm quota cold calling")]
    terms = suggest_queries(acc, rej)
    check("expands into accepted-job terms", "python" in terms and "api" in terms)
    check("prunes reject-only terms", "sales" not in terms and "quota" not in terms,
          str(terms))
    return True


def test_persists():
    d = tempfile.mkdtemp(prefix="pseek_ban2_")
    try:
        path = os.path.join(d, "o.json")
        b = QueryBandit(OrganelleRegistry(path))
        b.add_arm("x"); b.update("x", 1.0); b.update("x", 1.0)
        b2 = QueryBandit(OrganelleRegistry(path))
        check("bandit state persists across sessions",
              b2.arms.get("x", {}).get("pulls") == 2, str(b2.arms))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_explores_unpulled_then_exploits_best, test_query_expansion, test_persists]

if __name__ == "__main__":
    print("PSEEK · P6 query bandit tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
