# =============================================================================
# PSEEK — APP SETTINGS (per-workspace, persisted)
# User-adjustable preferences that the GUI reads. Font size is user-controllable
# in-app (default 20). The window-fit behaviour (never overflow the screen) is
# enforced by the GUI shell using screen geometry, but the preferred size lives
# here too so it survives sessions.
# =============================================================================
import json
import os

DEFAULTS = {
    "font_size": 20,          # Andrej's requested default; user-adjustable in-app
    "font_min": 10,
    "font_max": 32,
    "theme": "dark",          # "dark" | "light"
    "window_w": 1280,         # preferred; GUI clamps to available screen
    "window_h": 800,
}


class AppSettings:
    def __init__(self, path):
        self.path = path
        self._data = dict(DEFAULTS)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self._data.update(json.load(fh))

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        os.replace(tmp, self.path)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    # ---- font size (clamped to [font_min, font_max]) -----------------------
    @property
    def font_size(self):
        return int(self._data.get("font_size", 20))

    def set_font_size(self, size):
        size = max(self._data["font_min"], min(self._data["font_max"], int(size)))
        self.set("font_size", size)
        return size

    def bump_font(self, delta):
        return self.set_font_size(self.font_size + delta)
