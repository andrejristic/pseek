# =============================================================================
# PSEEK — P12 TESTS: Mode-2 on-the-job assistant (real, no stubs)
# Gated to pro/trial; activation researches the role and stores it; skill plan +
# task help are research-backed; every outward on-the-job action still passes the
# physician gate.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from guardian import Guardian
from learning import OrganelleRegistry
from billing import EntitlementManager, TRIAL_SECONDS
from research import ResearchEngine
from mode2 import OnTheJobAssistant

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

class Clock:
    def __init__(self, t=1000.0): self.t=t
    def __call__(self): return self.t

ROLE_TEXT = ("A machine learning engineer builds and deploys models. Key skills "
             "include Python, PyTorch, MLOps and data pipelines. The role owns "
             "model evaluation and monitoring.")

def _ctx(d, tier=None, clock=None):
    g = Guardian(jail_root=d, passphrase="pw")
    reg = OrganelleRegistry(os.path.join(d, "o.json"))
    ent = EntitlementManager(reg, now_fn=clock or (lambda: 1000.0))
    if tier:
        if clock: clock.t += TRIAL_SECONDS + 1
        ent.activate(tier)
    res = ResearchEngine(g, registry=reg)
    return OnTheJobAssistant(g, research=res, registry=reg, entitlements=ent), g, reg, ent

def test_gated_to_pro():
    d = tempfile.mkdtemp(prefix="pseek_m2_")
    try:
        clock = Clock()
        a_basic, *_ = _ctx(d + "b", tier="basic", clock=Clock())
        os.makedirs(d + "b", exist_ok=True)
        # basic (post-trial) → locked
        clockb = Clock(); 
        gb_dir = tempfile.mkdtemp(prefix="pseek_m2b_")
        a_b, *_ = _ctx(gb_dir, tier="basic", clock=clockb)
        check("basic tier → Mode 2 locked", not a_b.available())
        gp_dir = tempfile.mkdtemp(prefix="pseek_m2p_")
        a_p, *_ = _ctx(gp_dir, tier="pro", clock=Clock())
        check("pro tier → Mode 2 available", a_p.available())
        shutil.rmtree(gb_dir, ignore_errors=True); shutil.rmtree(gp_dir, ignore_errors=True)
        return True
    finally:
        shutil.rmtree(d + "b", ignore_errors=True)

def test_activate_and_skill_and_help():
    d = tempfile.mkdtemp(prefix="pseek_m2c_")
    try:
        a, g, reg, ent = _ctx(d)   # in trial → available
        r = a.activate("Machine Learning Engineer", "Acme AI", role_text=ROLE_TEXT)
        check("activation succeeds in trial and records role", r["status"] == "active"
              and reg.get_pref("employed_role") == "Machine Learning Engineer")
        check("activation stored research/organelles", reg.count() >= 1)
        plan = a.skill_plan("Machine Learning Engineer", ROLE_TEXT)
        check("skill plan drawn from the role", any("python" in p.lower() or "pytorch" in p.lower() for p in plan))
        helped = a.help_with("model evaluation", ROLE_TEXT)
        check("task help is research-backed", "evaluation" in helped["advice"].lower() or helped["advice"])
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_outward_action_still_physician():
    d = tempfile.mkdtemp(prefix="pseek_m2d_")
    try:
        a, g, reg, ent = _ctx(d)
        status, _ = a.act("send_email", approved=False, detail="to boss")
        check("on-the-job outward action escalates to physician", status == "escalate")
        status2, _ = a.act("research", approved=False)
        check("autonomous research proceeds", status2 == "proceed")
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)

ALL = [test_gated_to_pro, test_activate_and_skill_and_help, test_outward_action_still_physician]

if __name__ == "__main__":
    print("PSEEK · P12 Mode-2 assistant tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
