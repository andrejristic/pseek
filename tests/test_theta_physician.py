# =============================================================================
# PSEEK — P2 TESTS: θ engine + physician decision-classes (real, no stubs)
# θ reads healthy for a field-anchored state and leaves the band toward the right
# attractor as w_o / w_s grow, with a correction hint; the physician gate lets the
# swarm prepare autonomously but escalates every decision-class action (apply,
# purchase, send…) until the user approves — including logging to the Guardian.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from theta import theta_from_state, in_band, band_label, ThetaEngine, THETA_OPT
from physician import PhysicianGate
from guardian import Guardian

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


def test_theta_maps_states_correctly():
    healthy = theta_from_state((0.0, 0.0, 1.0))
    codep = theta_from_state((0.0, 0.4, 0.6))
    narc = theta_from_state((0.4, 0.0, 0.6))
    check("field-anchored state is healthy θ≈30", in_band(healthy) and abs(healthy - 30) < 0.01,
          f"θ={healthy}")
    check("codependent pull → θ>35 out of band", codep > 35 and not in_band(codep),
          f"θ={codep} ({band_label(codep)})")
    check("narcissistic pull → θ<25 out of band", narc < 25 and not in_band(narc),
          f"θ={narc} ({band_label(narc)})")
    return True


def test_theta_engine_history_and_correction():
    e = ThetaEngine()
    r1 = e.reading((0.0, 0.0, 1.0))
    r2 = e.reading((0.0, 0.5, 0.5))
    check("healthy reading has no correction", r1["correction"] is None and r1["in_band"])
    check("out-of-band reading gives a rebalance hint",
          (r2["correction"] is not None) and not r2["in_band"], f"θ={r2['theta']}")
    check("engine keeps a history for the gauge", len(e.history) == 2)
    return True


def test_physician_gate():
    d = tempfile.mkdtemp(prefix="pseek_phys_")
    try:
        g = Guardian(jail_root=d, passphrase="pw")
        gate = PhysicianGate(guardian=g)
        # autonomous work proceeds
        check("search proceeds autonomously", gate.check("search")[0] == "proceed")
        check("synthesize proceeds autonomously", gate.check("synthesize")[0] == "proceed")
        # decisions escalate until approved
        check("apply escalates without approval", gate.check("apply")[0] == "escalate")
        check("purchase escalates without approval", gate.check("purchase")[0] == "escalate")
        check("send_email escalates without approval", gate.check("send_email")[0] == "escalate")
        check("apply proceeds once approved", gate.check("apply", approved=True)[0] == "proceed")
        # escalations were logged to the Guardian ledger and are pending
        logged = any(e["record"].get("kind") == "physician_decision"
                     for e in g.ledger.entries())
        check("physician escalations logged + pending", logged and len(gate.pending_decisions()) >= 3)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_theta_maps_states_correctly, test_theta_engine_history_and_correction,
       test_physician_gate]

if __name__ == "__main__":
    print("PSEEK · P2 θ engine + physician tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
