# =============================================================================
# PSEEK — PREFERENCE LEARNING (Loop A: the Boundary Organ absorbs the user)
# Every action on a job — open, approve, reject, skip, edit — is a labelled
# signal. We keep a weight per job FEATURE (keywords, company, remote/onsite,
# Toronto) and nudge it by the signal. The learned weights only RE-RANK what the
# user sees; they never touch the floors. Persisted per-user in the registry, so
# the model gets better across sessions.
# =============================================================================
from jobs.domain import tokens
from jobs.geo import is_remote, is_toronto


def job_features(job):
    feats = set(job.keywords)
    if getattr(job, "company", ""):
        feats.add("company:" + job.company.lower())
    feats.add("remote" if is_remote(job) else "onsite")
    if is_toronto(job):
        feats.add("toronto")
    return feats


class PreferenceModel:
    SIGNAL = {"approve": 1.0, "open": 0.2, "edit": 0.3, "skip": -0.3, "reject": -1.0}

    def __init__(self, registry=None, lr=0.5):
        self.registry = registry
        self.lr = lr
        self.w = dict(registry.get_pref("pref_weights", {})) if registry else {}

    def record(self, job, action):
        delta = self.SIGNAL.get(action, 0.0) * self.lr
        if delta == 0.0:
            return
        for f in job_features(job):
            self.w[f] = self.w.get(f, 0.0) + delta
        if self.registry is not None:
            self.registry.set_pref("pref_weights", self.w)

    def score(self, job):
        return sum(self.w.get(f, 0.0) for f in job_features(job))

    def rerank(self, records, keyfn=None):
        keyfn = keyfn or (lambda r: r)
        return sorted(records, key=lambda r: self.score(keyfn(r)), reverse=True)
