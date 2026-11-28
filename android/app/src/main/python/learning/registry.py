# =============================================================================
# PSE-JOBS — ORGANELLE REGISTRY (the system learns about Andrej)
# The PSE Organelle Registry, applied to the job hunt: a persistent store of
# what the system has absorbed about the user — stated preferences, feedback,
# corrections. Every preference Andrej states in chat becomes an organelle here,
# so the self-model grows and later runs behave better. JSON-backed; survives
# sessions. This is the concrete mechanism behind "learns about you".
# =============================================================================
import json
import os
import time


class OrganelleRegistry:
    def __init__(self, path):
        self.path = path
        self._data = {"organelles": [], "prefs": {}}
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self._data = json.load(fh)

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    # ---- organelles (absorbed facts about the user) ------------------------
    def add_organelle(self, kind, text, data=None):
        o = {"id": len(self._data["organelles"]), "kind": kind, "text": text,
             "data": data or {}, "ts": time.time()}
        self._data["organelles"].append(o)
        self._save()
        return o

    def organelles(self, kind=None):
        return [o for o in self._data["organelles"]
                if kind is None or o["kind"] == kind]

    def count(self):
        return len(self._data["organelles"])

    # ---- preferences (the actionable distillate) ---------------------------
    def set_pref(self, key, value):
        self._data["prefs"][key] = value
        self._save()

    def get_pref(self, key, default=None):
        return self._data["prefs"].get(key, default)

    def prefs(self):
        return dict(self._data["prefs"])
