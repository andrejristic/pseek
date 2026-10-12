# =============================================================================
# PSEEK — P8 TESTS: self-inquiry engine (real, no stubs)
# Asks the highest-value question within a budget; a gap answer sets the pref and
# the question stops recurring; a behaviour/preference contradiction is surfaced;
# an out-of-band combination triggers an uncertainty question; answers persist as
# organelles.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jobs.domain import Job
from learning import OrganelleRegistry
from inquiry import SelfInquiryEngine

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


class FakeCombo:            # a combination shape the engine reads
    def __init__(self, label, in_band, theta, verdict="APPLY"):
        self.label = label; self.theta_in_band = in_band; self.theta = theta
        self.theta_label = "healthy" if in_band else "codependent-lean"
        self.verdict_code = verdict


def test_budget_and_gap_then_stops():
    d = tempfile.mkdtemp(prefix="pseek_inq_")
    try:
        reg = OrganelleRegistry(os.path.join(d, "o.json"))
        eng = SelfInquiryEngine(reg)
        q1 = eng.ask(budget=1)
        check("asks exactly one question within budget=1", len(q1) == 1, str(len(q1)))
        check("asks the highest-impact gap first (salary_floor)",
              q1[0].qid == "gap:salary_floor", q1[0].qid)
        eng.record_answer("gap:salary_floor", "90000")
        check("answered gap sets the preference", reg.get_pref("salary_floor") == "90000")
        later = [q.qid for q in eng.ask(budget=5)]
        check("answered gap no longer asked", "gap:salary_floor" not in later, str(later))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_contradiction_surfaced():
    d = tempfile.mkdtemp(prefix="pseek_inq2_")
    try:
        reg = OrganelleRegistry(os.path.join(d, "o.json"))
        reg.set_pref("location_focus", "remote")
        eng = SelfInquiryEngine(reg)
        onsite = Job("j1", "Onsite Analyst", "Acme", "data analysis", location="Toronto, ON")
        qs = eng.ask(budget=3, recent_actions=[(onsite, "approve")])
        check("contradiction (remote-only vs onsite approval) is surfaced",
              any(q.kind == "contradiction" for q in qs), [q.kind for q in qs])
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_uncertainty_from_out_of_band_combo():
    d = tempfile.mkdtemp(prefix="pseek_inq3_")
    try:
        reg = OrganelleRegistry(os.path.join(d, "o.json"))
        # fill all gaps so only uncertainty remains
        for k in ("salary_floor", "work_authorization", "deal_breakers", "availability"):
            reg.set_pref(k, "x")
        eng = SelfInquiryEngine(reg)
        combo = FakeCombo("cross-combination", in_band=False, theta=62.0)
        qs = eng.ask(budget=2, combos=[combo])
        check("out-of-band combination triggers an uncertainty question",
              any(q.kind == "uncertainty" for q in qs), [q.kind for q in qs])
        eng.record_answer(qs[0].qid, "manje krojenja")
        check("answer stored as organelle", reg.organelles("self_inquiry"))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_budget_and_gap_then_stops, test_contradiction_surfaced,
       test_uncertainty_from_out_of_band_combo]

if __name__ == "__main__":
    print("PSEEK · P8 self-inquiry tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
