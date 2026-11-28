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
    """With `account` (billing.account.Account) connected to the PSEEK backend, the tier
    comes ONLY from the backend-signed entitlement (trial is per email, paid tiers are
    activated by Square webhooks). Without it (dev / no backend yet) the local 24h
    trial + activate() logic below is used, as before."""

    def __init__(self, registry, now_fn=time.time, account=None):
        self.registry = registry
        self.now = now_fn
        self.account = account
        if registry.get_pref("signup_ts") is None:
            registry.set_pref("signup_ts", self.now())

    def _remote(self):
        return self.account is not None and self.account.configured()

    def _remote_tier(self):
        p = self.account.entitlement()
        if not p:
            return "free"                       # not signed in, other device, or offline too long
        now = self.now()
        if p.get("paid_tier") in ("basic", "pro") and p.get("until", 0) > now:
            return p["paid_tier"]
        if p.get("trial_until", 0) > now:
            return "trial"
        return "free"

    # ---- state -------------------------------------------------------------
    def in_trial(self):
        if self._remote():
            return self._remote_tier() == "trial"
        return (self.now() - float(self.registry.get_pref("signup_ts", self.now()))) <= TRIAL_SECONDS

    def tier(self):
        return self.registry.get_pref("tier", "free")

    def subscription_active(self):
        until = self.registry.get_pref("sub_until")
        return until is not None and self.now() <= float(until)

    def effective_tier(self):
        if self._remote():
            return self._remote_tier()
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

    # ---- local activation (dev / admin without a backend; the backend activates real purchases) ----
    def activate(self, tier, months=1):
        if tier not in PRICES:
            raise ValueError(f"unknown tier {tier}")
        self.registry.set_pref("tier", tier)
        self.registry.set_pref("sub_until", self.now() + months * MONTH_SECONDS)
        return self.effective_tier()

    def paywall(self):
        """What the popup shows. Each paid tier can be bought monthly (auto-renewing) or as a 30-day pass."""
        return {
            "in_trial": self.in_trial(),
            "effective_tier": self.effective_tier(),
            "kinds": [{"kind": "monthly", "blurb": "Mesečna pretplata (obnavlja se, otkaži kad hoćeš)"},
                      {"kind": "pass30", "blurb": "Jednokratno, 30 dana"}],
            "account": ({"email": self.account.email, "logged_in": self.account.logged_in()}
                        if self._remote() else None),
            "options": [
                {"tier": "trial", "price": 0.0, "blurb": "Prvih 24h sve uključeno"},
                {"tier": "basic", "price": PRICES["basic"],
                 "blurb": "1 rezime + 1 cover, bez combination engine"},
                {"tier": "pro", "price": PRICES["pro"],
                 "blurb": "Combination Engine + višestruki uploads + generisanje"},
            ],
        }
