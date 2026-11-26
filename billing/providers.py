# =============================================================================
# PSEEK — BILLING PROVIDER SWITCH
# Which way of paying is live is decided by the backend (GET /config ->
# billing_provider: square | google_play | off), so the seller can switch it at any
# time without a new app version (tools/pseek_admin.py set-billing ...).
# Each build only offers what its store allows:
#   desktop, android_apk  -> square (or off)
#   android_play          -> google_play (or off) — Google Play forbids other
#                            payment systems for digital goods in Play builds.
# =============================================================================
from .square import SquareCheckout

ALLOWED = {
    "desktop": ("square", "off"),
    "android_apk": ("square", "off"),
    "android_play": ("google_play", "off"),
}
DEFAULT = {"desktop": "square", "android_apk": "square", "android_play": "google_play"}


class BillingRouter:
    def __init__(self, guardian, account=None, physician=None, platform="desktop"):
        if platform not in ALLOWED:
            raise ValueError(f"unknown platform {platform}")
        self.platform = platform
        self.account = account
        self.square = SquareCheckout(guardian, physician=physician, account=account)

    def active(self):
        cfg = self.account.billing_config() if (self.account and self.account.configured()) else None
        wanted = (cfg or {}).get("billing_provider", DEFAULT[self.platform])
        if wanted == "off":
            return "off"
        return wanted if wanted in ALLOWED[self.platform] else DEFAULT[self.platform]

    def checkout(self, tier, kind="monthly", approved=False):
        provider = self.active()
        if provider == "off":
            return {"status": "billing_off", "reason": "kupovina je trenutno isključena"}
        if provider == "google_play":
            # The Android app runs Google Play Billing itself; the backend verifies the purchase.
            return {"status": "google_play", "tier": tier, "kind": kind}
        return self.square.create_checkout(tier, approved=approved, kind=kind)

    def cancel(self, approved=False):
        if self.active() == "google_play":
            return {"status": "google_play_manage", "reason": "otkazivanje ide preko Google Play pretplata"}
        return self.square.cancel(approved=approved)
