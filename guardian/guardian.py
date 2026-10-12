# =============================================================================
# PSE-JOBS GUARDIAN — the host-protecting PSE unit, turned inward
# One privileged process that stands ABOVE the job swarm. It holds every secret,
# is the only path to the filesystem and the network, keeps a tamper-evident
# ledger, and can freeze the whole swarm with a kill-switch. Job agents never
# touch secrets, disk, or sockets directly — they ask the Guardian, which
# refuses anything outside the jail / allowlist and logs every decision.
# =============================================================================
import os
from .fs_jail import FSJail
from .egress import EgressPolicy
from .ledger import HashChainedLedger
from .vault import Vault
from .errors import GuardianViolation


class Guardian:
    def __init__(self, jail_root, passphrase, allow_hosts=None, read_roots=None,
                 vault_path=None, ledger_path=None):
        self.jail_root = os.path.realpath(os.path.abspath(jail_root))
        self.fs = FSJail(self.jail_root, read_roots)
        self.egress = EgressPolicy(allow_hosts)
        self.ledger = HashChainedLedger(
            ledger_path or os.path.join(self.jail_root, "audit", "guardian_ledger.jsonl"))
        self.vault = Vault(
            vault_path or os.path.join(self.jail_root, "registry", "vault.enc"), passphrase)
        self._active = True
        self._escalations = []
        self.ledger.append({"event": "guardian_start", "jail": self.jail_root,
                            "vault_backend": self.vault.backend})

    # ---- kill-switch -------------------------------------------------------
    @property
    def active(self):
        return self._active

    def assert_active(self):
        if not self._active:
            raise GuardianViolation("guardian kill-switch is tripped — swarm frozen")

    def trip(self, reason="manual"):
        self._active = False
        self.ledger.append({"event": "killswitch_trip", "reason": reason})

    def reset(self, reason="manual"):
        self._active = True
        self.ledger.append({"event": "killswitch_reset", "reason": reason})

    # ---- filesystem --------------------------------------------------------
    def guard_write(self, path):
        self.assert_active()
        try:
            p = self.fs.guard_write(path)
        except GuardianViolation as e:
            self.ledger.append({"event": "write_blocked", "path": str(path), "why": str(e)})
            raise
        self.ledger.append({"event": "write", "path": p})
        return p

    def guard_read(self, path):
        try:
            p = self.fs.guard_read(path)
        except GuardianViolation as e:
            self.ledger.append({"event": "read_blocked", "path": str(path), "why": str(e)})
            raise
        return p

    # ---- network -----------------------------------------------------------
    def guard_egress(self, url_or_host):
        self.assert_active()
        try:
            host = self.egress.guard(url_or_host)
        except GuardianViolation as e:
            self.ledger.append({"event": "egress_blocked", "target": str(url_or_host), "why": str(e)})
            raise
        self.ledger.append({"event": "egress", "host": host})
        return host

    # ---- secrets (agents get values only through here) ---------------------
    def secret(self, name):
        self.assert_active()
        val = self.vault.get(name)                       # raises if missing
        self.ledger.append({"event": "secret_access", "name": name})  # never the value
        return val

    def put_secret(self, name, value):
        self.vault.set(name, value)
        self.ledger.append({"event": "secret_store", "name": name})

    def has_secret(self, name):
        return self.vault.has(name)

    # ---- escalation queue (things that hit a floor wait for Andrej) ---------
    def escalate(self, kind, detail):
        item = {"kind": kind, "detail": detail}
        self._escalations.append(item)
        self.ledger.append({"event": "escalation", "kind": kind, "detail": detail})
        return item

    def escalations(self):
        return list(self._escalations)

    # ---- integrity ---------------------------------------------------------
    def verify_ledger(self):
        return self.ledger.verify()
