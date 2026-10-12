# =============================================================================
# PSEEK — P11 TESTS: entitlements + Square checkout (real, no stubs)
# 24h trial unlocks everything; after it, free locks core features (paywall);
# basic allows apply + single doc but NOT the combination engine; pro unlocks the
# combination engine + unlimited uploads; buying escalates to the physician and,
# with no seller keys, runs in test mode; Square host is egress-allowlisted;
# prices are $4.95 / $9.95.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from guardian import Guardian
from learning import OrganelleRegistry
from billing import EntitlementManager, SquareCheckout, PRICES, TRIAL_SECONDS

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


class Clock:
    def __init__(self, t=1000.0): self.t = t
    def __call__(self): return self.t


def _reg(d):
    return OrganelleRegistry(os.path.join(d, "o.json"))


def test_trial_unlocks_everything_then_free_locks():
    d = tempfile.mkdtemp(prefix="pseek_bil_")
    try:
        clock = Clock(1000.0)
        reg = _reg(d)
        ent = EntitlementManager(reg, now_fn=clock)
        check("during 24h trial the combination engine is unlocked",
              ent.can_use("combination_engine") and ent.effective_tier() == "trial")
        check("trial uploads are unlimited", ent.upload_limit() is None)
        clock.t += TRIAL_SECONDS + 1                # trial expires
        check("after trial, free tier locks the combination engine (paywall)",
              not ent.can_use("combination_engine") and not ent.can_use("apply")
              and ent.effective_tier() == "free")
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_basic_vs_pro():
    d = tempfile.mkdtemp(prefix="pseek_bil2_")
    try:
        clock = Clock(1000.0)
        reg = _reg(d)
        ent = EntitlementManager(reg, now_fn=clock)
        clock.t += TRIAL_SECONDS + 1               # out of trial
        ent.activate("basic")
        check("basic: apply yes, combination engine no",
              ent.can_use("apply") and not ent.can_use("combination_engine"))
        check("basic: uploads limited to 1 résumé + 1 cover",
              ent.upload_limit() == {"resumes": 1, "covers": 1})
        ent.activate("pro")
        check("pro: combination engine + unlimited uploads",
              ent.can_use("combination_engine") and ent.upload_limit() is None)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_purchase_is_physician_decision_and_testmode():
    d = tempfile.mkdtemp(prefix="pseek_bil3_")
    try:
        g = Guardian(jail_root=d, passphrase="pw")
        sq = SquareCheckout(g)
        r0 = sq.create_checkout("pro", approved=False)
        check("buying without approval → physician escalate", r0["status"] == "escalate")
        r1 = sq.create_checkout("pro", approved=True)
        check("approved but no seller keys → test mode (no charge)",
              r1["status"] == "unconfigured" and r1["amount"] == 9.95)
        check("Square host on egress allowlist",
              g.egress.allowed("https://connect.squareup.com/v2/online-checkout/payment-links"))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_prices():
    check("prices are $4.95 (basic) and $9.95 (pro)",
          PRICES["basic"] == 4.95 and PRICES["pro"] == 9.95)


ALL = [test_trial_unlocks_everything_then_free_locks, test_basic_vs_pro,
       test_purchase_is_physician_decision_and_testmode, test_prices]

if __name__ == "__main__":
    print("PSEEK · P11 entitlements + Square tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
