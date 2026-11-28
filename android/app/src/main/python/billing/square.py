# =============================================================================
# PSEEK — SQUARE CHECKOUT (payments go to the SELLER's Square account)
# The app holds NO Square credentials. It asks the PSEEK backend (billing-backend/)
# for a hosted checkout link; the backend holds the seller's Square token, gives
# every checkout its own idempotency key, and activates the buyer's account when
# Square's signed webhook confirms payment. Two ways to buy: "monthly"
# (auto-renewing subscription, cancel any time) or "pass30" (one-time, 30 days).
# Buying and cancelling are PHYSICIAN decisions — they escalate for the user's
# explicit confirmation first. Without a connected backend account it runs in
# test mode and no money moves.
# =============================================================================
from physician import PhysicianGate
from .entitlements import PRICES

KINDS = ("monthly", "pass30")


class SquareCheckout:
    def __init__(self, guardian, physician=None, account=None):
        self.g = guardian
        self.physician = physician or PhysicianGate(guardian)
        self.account = account

    def configured(self):
        return bool(self.account and self.account.configured() and self.account.logged_in())

    def create_checkout(self, tier, approved=False, redirect_url=None, kind="monthly"):
        if tier not in PRICES:
            return {"status": "error", "reason": f"unknown tier {tier}"}
        if kind not in KINDS:
            return {"status": "error", "reason": f"unknown kind {kind}"}
        # PHYSICIAN: no purchase without the user's explicit confirmation
        status, reason = self.physician.check("purchase", approved=approved,
                                              detail=f"{tier} {kind} ${PRICES[tier]}")
        if status == "escalate":
            return {"status": "escalate", "reason": reason}
        if not self.configured():
            return {"status": "unconfigured",
                    "note": "not signed in to the PSEEK backend — entitlement test mode",
                    "amount": PRICES[tier], "kind": kind}
        data = self.account.checkout(tier, kind)
        self.g.ledger.append({"event": "checkout_created", "tier": tier, "kind": kind,
                              "checkout_id": data.get("checkout_id")})
        return {"status": "checkout", "url": data.get("url"), "amount": PRICES[tier],
                "kind": kind, "checkout_id": data.get("checkout_id")}

    def cancel(self, approved=False):
        status, reason = self.physician.check("cancel_subscription", approved=approved,
                                              detail="cancel monthly subscription")
        if status == "escalate":
            return {"status": "escalate", "reason": reason}
        if not self.configured():
            return {"status": "unconfigured"}
        data = self.account.cancel()
        self.g.ledger.append({"event": "subscription_cancelled"})
        return {**data, "square_status": data.get("status"), "status": "cancelled"}
