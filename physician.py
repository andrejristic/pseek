# =============================================================================
# PSEEK — THE PHYSICIAN (decision authority = the user)
# In the PSE corpus a clinical unit defers to, and escalates to, a physician.
# In PSEEK the physician is the USER: the app "does everything except decisions."
# This module names the DECISION CLASSES — the actions the swarm may PREPARE but
# never execute on its own — and gates them: without the user's explicit approval
# they escalate (human_review), never proceed. This is the consent floor, made
# explicit for every outward/irreversible action, including money.
# =============================================================================

# Actions that are always the physician's (the user's) call:
DECISION_CLASSES = {
    "apply",            # submitting a job application
    "send_email",       # sending any email
    "reply_employer",   # replying to an employer
    "accept_offer",     # accepting an offer
    "purchase",         # any payment / upgrade (Square)
    "connect_email",    # connecting an email account (grants access)
    "delete_docs",      # destructive changes to the document pool
}

# Actions the swarm may do on its own (prepare / analyse / research):
AUTONOMOUS = {"search", "harvest", "triage", "draft", "synthesize", "research",
              "rank", "explain", "learn"}


class PhysicianGate:
    def __init__(self, guardian=None):
        self.guardian = guardian
        self.pending = []          # decisions awaiting the physician

    def requires_human(self, action_type):
        return action_type in DECISION_CLASSES

    def check(self, action_type, approved=False, detail=""):
        """Return ('proceed', None) or ('escalate', reason). A decision-class
        action only proceeds when the user has explicitly approved it."""
        if self.requires_human(action_type) and not approved:
            reason = f"'{action_type}' je odluka — čeka korisnika (physician)"
            self.pending.append({"action": action_type, "detail": detail})
            if self.guardian is not None:
                self.guardian.escalate("physician_decision",
                                       f"{action_type}: {detail}")
            return ("escalate", reason)
        return ("proceed", None)

    def pending_decisions(self):
        return list(self.pending)
