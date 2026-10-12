# =============================================================================
# PSEEK — SQUARE CHECKOUT (payments go to the SELLER's Square account)
# Creates a Square hosted checkout link for a tier. The seller supplies the Square
# access token (in the vault, app-side); until then it runs in test mode and no
# money moves. Buying is a PHYSICIAN decision — it escalates for the user's
# explicit confirmation before any checkout is created. Every call is egress-
# gated to Square. On confirmed payment the caller activates the entitlement.
# =============================================================================
import json
import urllib.request

from physician import PhysicianGate
from .entitlements import PRICES


class SquareCheckout:
    HOST = "connect.squareup.com"

    def __init__(self, guardian, physician=None):
        self.g = guardian
        self.physician = physician or PhysicianGate(guardian)

    def configured(self):
        return self.g.has_secret("square_access_token")

    def create_checkout(self, tier, approved=False, redirect_url=None):
        if tier not in PRICES:
            return {"status": "error", "reason": f"unknown tier {tier}"}
        # PHYSICIAN: no purchase without the user's explicit confirmation
        status, reason = self.physician.check("purchase", approved=approved,
                                              detail=f"{tier} ${PRICES[tier]}")
        if status == "escalate":
            return {"status": "escalate", "reason": reason}
        if not self.configured():
            return {"status": "unconfigured",
                    "note": "seller Square keys not set — entitlement test mode",
                    "amount": PRICES[tier]}
        url = f"https://{self.HOST}/v2/online-checkout/payment-links"
        self.g.guard_egress(url)
        token = self.g.secret("square_access_token")
        amount_cents = int(round(PRICES[tier] * 100))
        body = json.dumps({
            "idempotency_key": f"pseek-{tier}",
            "quick_pay": {"name": f"PSEEK {tier} (monthly)",
                          "price_money": {"amount": amount_cents, "currency": "USD"},
                          "location_id": self.g.secret("square_location_id")
                          if self.g.has_secret("square_location_id") else ""},
        }).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json",
            "Square-Version": "2024-01-18"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        link = data.get("payment_link", {}).get("url", "")
        self.g.ledger.append({"event": "checkout_created", "tier": tier})
        return {"status": "checkout", "url": link, "amount": PRICES[tier]}
