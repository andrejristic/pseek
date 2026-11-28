# =============================================================================
# PSE-JOBS — DOMAIN MODEL
# The concrete objects the jobs pack scores over. A Profile is a self-model
# built from ONE résumé; its lines are the truthfulness ground truth. A Job is a
# harvested posting. An Application is a proposed action: a set of Claims, each
# of which must trace to a résumé line, plus the chosen profile and a rationale.
#
# Nothing here touches the kernel. This is pack-side domain data only.
# =============================================================================
from dataclasses import dataclass, field
import re

# Small stopword set — enough to make keyword-overlap fit scoring meaningful
# without pulling in a dependency. UNVALIDATED: tune on real postings.
_STOP = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "has", "this", "that", "from", "into", "who", "all", "any", "can", "not",
    "but", "per", "via", "job", "role", "work", "team", "years", "year", "a",
    "an", "of", "to", "in", "on", "at", "as", "or", "by", "is", "be", "we",
}


def tokens(text):
    """Lowercase alphanumeric tokens >= 3 chars, minus stopwords. Deterministic."""
    return {t for t in re.findall(r"[a-z0-9+#]+", (text or "").lower())
            if len(t) >= 3 and t not in _STOP}


@dataclass(frozen=True)
class ResumeLine:
    """One fact from a résumé. `line_id` is stable and citable by a Claim."""
    line_id: str
    text: str
    profile: str            # "teaching" | "coding"

    @property
    def toks(self):
        return tokens(self.text)


@dataclass
class Profile:
    """A self-model built from one résumé. The truthfulness anchor."""
    key: str                # "teaching" | "coding"
    name: str
    lines: list = field(default_factory=list)   # list[ResumeLine]

    @property
    def keywords(self):
        ks = set()
        for ln in self.lines:
            ks |= ln.toks
        return ks

    def line(self, line_id):
        for ln in self.lines:
            if ln.line_id == line_id:
                return ln
        return None

    def fit(self, job):
        """Coverage of the job's keywords by this profile's keywords, in [0,1].
        Deterministic and inspectable: |job_kw ∩ profile_kw| / |job_kw|."""
        jk = job.keywords
        if not jk:
            return 0.0
        return len(jk & self.keywords) / len(jk)


@dataclass
class Job:
    job_id: str
    title: str
    company: str
    description: str = ""
    keyword_hints: list = field(default_factory=list)   # explicit ATS keywords
    apply_method: str = "unknown"      # "email" | "ats" | "form" | "unknown"
    contact: str = None
    source_url: str = None
    location: str = ""                  # free-text location from the posting

    @property
    def keywords(self):
        return tokens(self.title) | tokens(self.description) | {
            k.lower() for k in self.keyword_hints}


@dataclass
class Claim:
    """One assertion an application makes about the candidate. `line_id` is the
    résumé line it is drawn from — None means fabricated (no provenance)."""
    text: str
    line_id: str = None

    @property
    def toks(self):
        return tokens(self.text)


@dataclass
class Application:
    app_id: str
    job: Job
    profile_key: str                    # which self-model is being presented
    claims: list = field(default_factory=list)   # list[Claim]
    rationale: str = ""
    approved: bool = False              # set only by a human at the consent gate
