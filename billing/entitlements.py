# =============================================================================
# PSEEK — ENTITLEMENTS (tiers + 24h trial; what each user may use)
# The paywall's brain. On first run a 24-hour full trial starts. After that:
#   free  → must buy (core features locked; paywall shown)
#   basic ($4.95/mo) → search + apply, ONE résumé + ONE cover, NO combination engine
#   pro   ($9.95/mo) → the Combination Engine + multiple uploads + generation + more
# State lives per-user in the registry. `now_fn` is injectable so trial expiry is
# deterministic and testable.
# =============================================================================
import time

PRICES = {"basic": 4.95, "pro": 9.95}
TRIAL_SECONDS = 24 * 3600
MONTH_SECONDS = 30 * 24 * 3600

# every gate-able capability
ALL_FEATURES = {"search", "apply", "doc_generation", "web_research",
                "combination_engine", "multi_upload", "mode2"}
BASIC_FEATURES = {"search", "apply", "doc_generation", "web_research"}   # single-doc
PRO_FEATURES = set(ALL_FEATURES)


class EntitlementManager:
    def __init__(self, registry, now_fn=time.time):
        self.registry = registry
        self.now = now_fn
        if registry.get_pref("signup_ts") is None:
            registry.set_pref("signup_ts", self.now())

    # ---- state -------------------------------------------------------------
    def in_trial(self):
        return (self.now() - float(self.registry.get_pref("signup_ts", self.now()))) <= TRIAL_SECONDS

    def tier(self):
        return self.registry.get_pref("tier", "free")

    def subscription_active(self):
        until = self.registry.get_pref("sub_until")
        return until is not None and self.now() <= float(until)

    def effective_tier(self):
        if self.in_trial():
            return "trial"
        if self.tier() in ("basic", "pro") and self.subscription_active():
            return self.tier()
        return "free"

    # ---- gating ------------------------------------------------------------
    def can_use(self, feature):
        t = self.effective_tier()
        if t == "trial":
            return feature in ALL_FEATURES
        if t == "pro":
            return feature in PRO_FEATURES
        if t == "basic":
            return feature in BASIC_FEATURES
        return False                        # free (post-trial): paywall everything

    def upload_limit(self):
        """None = unlimited; else {'resumes':n,'covers':n}."""
        t = self.effective_tier()
        if t in ("trial", "pro"):
            return None
        return {"resumes": 1, "covers": 1}   # basic and free

    # ---- purchase result (called after Square confirms) --------------------
    def activate(self, tier, months=1):
        if tier not in PRICES:
            raise ValueError(f"unknown tier {tier}")
        self.registry.set_pref("tier", tier)
        self.registry.set_pref("sub_until", self.now() + months * MONTH_SECONDS)
        return self.effective_tier()

    def paywall(self):
        """What the popup shows."""
        return {
            "in_trial": self.in_trial(),
            "effective_tier": self.effective_tier(),
            "options": [
                {"tier": "trial", "price": 0.0, "blurb": "Prvih 24h sve uključeno"},
                {"tier": "basic", "price": PRICES["basic"],
                 "blurb": "1 rezime + 1 cover, bez combination engine"},
                {"tier": "pro", "price": PRICES["pro"],
                 "blurb": "Combination Engine + višestruki uploads + generisanje"},
            ],
        }
