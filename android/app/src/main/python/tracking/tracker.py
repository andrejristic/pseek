# =============================================================================
# PSE-JOBS — APPLICATION TRACKER (the lifecycle state machine)
# Every application moves through a real state machine: DRAFT → APPROVED → SENT →
# REPLIED → INTERVIEW → OFFER (or REJECTED / GHOSTED). Illegal jumps are refused.
# State + full history persist to JSON, and every transition is written to the
# Guardian ledger. This feeds the Tracker tab, the Dashboard funnel, and the
# Seldon strategy engine (Phase 9).
# =============================================================================
import json
import os
import time

STATES = ["DRAFT", "APPROVED", "SENT", "REPLIED", "INTERVIEW", "OFFER",
          "REJECTED", "GHOSTED"]

ALLOWED = {
    "DRAFT":     {"APPROVED", "REJECTED"},
    "APPROVED":  {"SENT", "REJECTED"},
    "SENT":      {"REPLIED", "GHOSTED", "REJECTED"},
    "REPLIED":   {"INTERVIEW", "REJECTED"},
    "INTERVIEW": {"OFFER", "REJECTED"},
    "OFFER":     set(),
    "REJECTED":  set(),
    "GHOSTED":   set(),
}


class TrackerError(Exception):
    pass


class ApplicationTracker:
    def __init__(self, path, guardian=None):
        self.path = path
        self.guardian = guardian
        self._apps = {}
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self._apps = json.load(fh)

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._apps, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def _log(self, event, **kw):
        if self.guardian is not None:
            self.guardian.ledger.append({"event": event, **kw})

    def add(self, app_id, job_id="", title="", company="", profile="", state="DRAFT"):
        if state not in STATES:
            raise TrackerError(f"unknown state {state}")
        rec = {"app_id": app_id, "job_id": job_id, "title": title,
               "company": company, "profile": profile, "state": state,
               "history": [{"state": state, "ts": time.time()}]}
        self._apps[app_id] = rec
        self._save()
        self._log("track_add", app=app_id, state=state)
        return rec

    def transition(self, app_id, new_state):
        if app_id not in self._apps:
            raise TrackerError(f"unknown application {app_id}")
        cur = self._apps[app_id]["state"]
        if new_state not in ALLOWED.get(cur, set()):
            raise TrackerError(f"illegal transition {cur} -> {new_state}")
        self._apps[app_id]["state"] = new_state
        self._apps[app_id]["history"].append({"state": new_state, "ts": time.time()})
        self._save()
        self._log("track_transition", app=app_id, **{"from": cur, "to": new_state})
        return self._apps[app_id]

    def get(self, app_id):
        return self._apps.get(app_id)

    def all(self):
        return list(self._apps.values())

    def by_state(self, state):
        return [a for a in self._apps.values() if a["state"] == state]

    def funnel(self):
        counts = {s: 0 for s in STATES}
        for a in self._apps.values():
            counts[a["state"]] += 1
        return counts
