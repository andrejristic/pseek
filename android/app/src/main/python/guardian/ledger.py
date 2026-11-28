# =============================================================================
# PSE-JOBS GUARDIAN — TAMPER-EVIDENT LEDGER
# The Guardian's own append-only security log, hash-chained: each record carries
# the SHA-256 of (previous hash + this record's canonical bytes). Editing or
# deleting any past line breaks every subsequent hash, so verify() pinpoints the
# first tampered entry. This is the audit the swarm CANNOT quietly rewrite.
# =============================================================================
import hashlib
import json
import os
import threading
import time

GENESIS = "0" * 64


def _canon(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")

def _hash(prev_hash, record):
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(_canon(record))
    return h.hexdigest()


class HashChainedLedger:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def _last_hash(self):
        if not os.path.exists(self.path):
            return GENESIS
        last = GENESIS
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = json.loads(line)["hash"]
        return last

    def append(self, record):
        record = dict(record)
        record.setdefault("ts", time.time())
        with self._lock:
            prev = self._last_hash()
            seq = 0
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as fh:
                    seq = sum(1 for ln in fh if ln.strip())
            entry_core = {"seq": seq, "prev": prev, "record": record}
            digest = _hash(prev, entry_core)
            entry = {**entry_core, "hash": digest}
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, default=str) + "\n")
        return entry

    def verify(self):
        """Re-walk the chain. Returns (ok, first_bad_seq_or_None)."""
        if not os.path.exists(self.path):
            return True, None
        prev = GENESIS
        with open(self.path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                core = {"seq": entry["seq"], "prev": entry["prev"], "record": entry["record"]}
                if entry["prev"] != prev or _hash(prev, core) != entry["hash"]:
                    return False, entry.get("seq", i)
                prev = entry["hash"]
        return True, None

    def entries(self):
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    out.append(json.loads(line))
        return out
