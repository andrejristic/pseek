# =============================================================================
# PSEEK — PER-USER ENCRYPTED WORKSPACE
# PSEEK is sold to third parties, so every user is isolated: their own directory,
# their own encrypted vault (secrets: their email creds; the seller's shared LLM/
# Square keys live app-side), their own registry (what the app learned about
# THEM), tracker, audit, and document pool. The Guardian is scoped to the user's
# directory — its filesystem jail confines all writes to that workspace, so one
# user can never touch another's data.
# =============================================================================
import os
import re

from guardian import Guardian
from learning import OrganelleRegistry
from tracking import ApplicationTracker
from settings import AppSettings


def _safe_id(user_id):
    s = re.sub(r"[^A-Za-z0-9_.-]", "_", str(user_id)).strip("._")
    return s or "user"


class Workspace:
    def __init__(self, base_dir, user_id, passphrase):
        self.user_id = _safe_id(user_id)
        self.root = os.path.join(os.path.abspath(base_dir), self.user_id)
        self.docs_dir = os.path.join(self.root, "docs")        # user's résumés/covers
        for sub in ("docs", "registry", "data", "audit"):
            os.makedirs(os.path.join(self.root, sub), exist_ok=True)

        # Guardian jailed to THIS user's workspace; may read the user's own docs.
        self.guardian = Guardian(
            jail_root=self.root, passphrase=passphrase, read_roots=[self.docs_dir],
            vault_path=os.path.join(self.root, "registry", "vault.enc"),
            ledger_path=os.path.join(self.root, "audit", "guardian_ledger.jsonl"))
        self.registry = OrganelleRegistry(
            os.path.join(self.root, "registry", "organelles.json"))
        self.tracker = ApplicationTracker(
            os.path.join(self.root, "data", "applications.json"),
            guardian=self.guardian)
        self.settings = AppSettings(os.path.join(self.root, "settings.json"))
        self.kernel_audit_path = os.path.join(self.root, "audit", "kernel.jsonl")

    # ---- convenience -------------------------------------------------------
    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def connect_email(self, address, app_password, imap_host=None, smtp_host=None):
        """The user connects THEIR OWN email; creds live only in their vault."""
        self.guardian.put_secret("user_email", address)
        self.guardian.put_secret("user_email_password", app_password)
        if imap_host:
            self.guardian.put_secret("user_imap_host", imap_host)
        if smtp_host:
            self.guardian.put_secret("user_smtp_host", smtp_host)

    def email_connected(self):
        return self.guardian.has_secret("user_email")


def open_workspace(base_dir, user_id, passphrase):
    return Workspace(base_dir, user_id, passphrase)
