# =============================================================================
# PSE-JOBS — JOBS CONTEXT (the jobs-domain SHARED_LIB)
# The kernel's scoring/membrane are domain-agnostic: they call context.in_scope,
# context.authorized and context.has_provenance by duck-typing. PSE-Jobs supplies
# THIS object instead of pse-kali's EngagementContext, giving those same three
# methods a job-hunt meaning — so the moat runs verbatim over a new domain.
#
#   in_scope(job_id)          -> does the job fit at least one profile? (scope)
#   authorized(job_id, tool)  -> is this action-type permitted for this job?
#   has_provenance(artifact)  -> the TWO FLOORS, folded into the kernel's one
#                                hard gate via a "kind:app_id" artifact:
#          "draft:<app>"  -> every claim traces to a résumé line  (TRUTHFULNESS)
#          "submit:<app>" -> truthful AND approved by a human      (CONSENT)
#     A failing artifact drives authorization_level to 0.0 -> below the floor ->
#     the simplex is truncated -> the action can only escalate. Fabrication and
#     un-consented sending are both geometrically unreachable, kernel untouched.
# =============================================================================
import threading


class JobsContext:
    def __init__(self, profiles, fit_threshold=0.15):
        """
        profiles      : dict[str, Profile] keyed by profile key ("teaching"/"coding")
        fit_threshold : minimum profile.fit(job) for a job to count as in-scope.
                        UNVALIDATED working value; calibrated later on real postings.
        """
        self.engagement_id = "pse-jobs"
        self._profiles = dict(profiles)
        self.fit_threshold = fit_threshold
        self._jobs = {}            # job_id -> Job
        self._apps = {}            # app_id -> Application
        self._findings = []        # SHARED_LIB parity: harvested intel
        self._lock = threading.Lock()

    # ---- registration ------------------------------------------------------
    def register_job(self, job):
        self._jobs[job.job_id] = job
        return job

    def register_application(self, app):
        self._jobs.setdefault(app.job.job_id, app.job)
        self._apps[app.app_id] = app
        return app

    def approve(self, app_id):
        """The consent gate. Only a human path calls this."""
        self._apps[app_id].approved = True

    def profile(self, key):
        return self._profiles.get(key)

    # ---- truthfulness primitive -------------------------------------------
    def is_backed(self, claim, profile):
        """A claim is backed iff it cites a real résumé line AND shares at least
        one content token with it (can't cite an unrelated line to smuggle a lie)."""
        if claim.line_id is None:
            return False
        line = profile.line(claim.line_id)
        if line is None:
            return False
        return len(claim.toks & line.toks) >= 1

    def best_fit(self, job):
        """(profile_key, fit) for the profile that fits this job best."""
        best_k, best_v = None, -1.0
        for k, p in self._profiles.items():
            v = p.fit(job)
            if v > best_v:
                best_k, best_v = k, v
        return best_k, best_v

    # ---- kernel-facing API (duck-typed by scoring.py) ----------------------
    def in_scope(self, target):
        job = self._jobs.get(target)
        if job is None:
            return False
        return self.best_fit(job)[1] >= self.fit_threshold

    def authorized(self, target, tool):
        if tool in ("draft", "search", "triage", None):
            return True
        if tool == "submit":
            # permitted only once a human has approved some application for this job
            return any(a.job.job_id == target and a.approved
                       for a in self._apps.values())
        return False

    def has_provenance(self, artifact):
        if artifact is None:
            return True
        kind, _, app_id = str(artifact).partition(":")
        app = self._apps.get(app_id)
        if app is None:
            return False
        profile = self._profiles.get(app.profile_key)
        if profile is None:
            return False
        all_backed = all(self.is_backed(c, profile) for c in app.claims) and bool(app.claims)
        if kind == "submit":
            return all_backed and app.approved
        return all_backed        # draft / triage

    # ---- SHARED_LIB findings store (units feed each other) -----------------
    def add_finding(self, finding):
        finding = dict(finding)
        with self._lock:
            self._findings.append(finding)
        return finding

    def findings(self, kind=None):
        with self._lock:
            return [dict(f) for f in self._findings
                    if kind is None or f.get("kind") == kind]
