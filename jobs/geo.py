# =============================================================================
# PSE-JOBS — LOCATION TARGETING (Toronto + Remote focus)
# Classifies a posting as remote and/or Toronto/GTA, and gates jobs by the
# user's location focus. Deterministic keyword logic over the posting's title,
# description and location field. Andrej's default focus is "toronto_remote".
# =============================================================================
import re

GTA = ("toronto", "north york", "scarborough", "etobicoke", "east york",
       "mississauga", "vaughan", "markham", "brampton", "richmond hill",
       "oakville", "burlington", "pickering", "ajax", "gta", "york region")

REMOTE_HINTS = ("remote", "work from home", "wfh", "anywhere", "distributed",
                "fully remote", "remote-first", "telecommute")

FOCUS_VALUES = ("toronto_remote", "toronto", "remote", "anywhere")


def _blob(job):
    return " ".join([job.title or "", job.description or "",
                     getattr(job, "location", "") or ""]).lower()


def is_remote(job):
    return any(k in _blob(job) for k in REMOTE_HINTS)


def is_toronto(job):
    b = _blob(job)
    if any(c in b for c in GTA):
        return True
    return bool(re.search(r",\s*on\b", b) or "ontario" in b)


def location_label(job):
    r, t = is_remote(job), is_toronto(job)
    if t and r:
        return "Toronto/Remote"
    if t:
        return "Toronto/GTA"
    if r:
        return "Remote"
    return (job.location or "onsite").strip() or "onsite"


def location_ok(job, focus):
    """Does this job pass the user's location focus?"""
    if not focus or focus == "anywhere":
        return True
    r, t = is_remote(job), is_toronto(job)
    if focus == "remote":
        return r
    if focus == "toronto":
        return t
    if focus == "toronto_remote":
        return r or t
    return True
