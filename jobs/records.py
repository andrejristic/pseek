# =============================================================================
# PSE-JOBS — APPLICATION-READY RECORD
# What the Harvest arm produces per job: everything needed to fill an application,
# packaged and PROVENANCED. Every datum knows where it came from — a posting URL
# or a specific résumé line — so nothing in an application is untraceable, and the
# truthfulness floor can point at the exact line behind each claim.
# =============================================================================
from dataclasses import dataclass, field, asdict
import re


@dataclass
class Candidate:
    """The applicant's identity for autofill. Seeded from the résumés (each
    field carries the résumé line it was parsed from)."""
    name: str
    email: str = None
    phone: str = None
    location: str = None
    provenance: dict = field(default_factory=dict)


def parse_candidate(profiles, name="Andrej Ristic"):
    email = phone = location = None
    prov = {}
    for p in profiles.values():
        for ln in p.lines:
            if email is None:
                m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", ln.text)
                if m:
                    email = m.group(0); prov["email"] = ln.line_id
            if phone is None:
                m = re.search(r"\+?\d[\d\s().-]{8,}\d", ln.text)
                if m:
                    phone = m.group(0).strip(); prov["phone"] = ln.line_id
            if location is None:
                m = re.search(r"\b([A-Z][a-z]+,\s*ON)\b", ln.text)
                if m:
                    location = m.group(1); prov["location"] = ln.line_id
    return Candidate(name, email, phone, location, prov)


@dataclass
class AutofillField:
    key: str
    value: str
    source: str            # "resume:coding:0002" | "posting" | "config"


@dataclass
class Bullet:
    text: str
    source_line_id: str    # the résumé line this tailored bullet is drawn from


@dataclass
class ApplicationReadyRecord:
    job_id: str
    title: str
    company: str
    source_url: str
    how_to_apply: dict          # {method, contact, url, deadline}
    requirements: dict          # {keywords, stack}
    company_ctx: dict           # {description_excerpt, ...}
    comp: str
    fit_by_profile: dict        # {"coding": .., "teaching": ..}
    best_profile: str
    verdict_code: str           # kernel triage verdict of the auto-draft
    autofill: list              # list[AutofillField]
    bullets: list               # list[Bullet], each provenanced to a résumé line
    provenance: dict            # field -> source
    # kernel geometry of the truthful auto-draft (for the Live Simplex)
    state: tuple = (0.0, 0.0, 0.0)    # (w_s, w_o, w_f)
    auth_level: float = 0.0
    nearest: tuple = ("", 0.0)        # (attractor_name, distance)
    job: object = None                # the source Job (for the Draft arm)

    def to_dict(self):
        return asdict(self)
