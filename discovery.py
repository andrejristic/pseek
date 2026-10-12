# =============================================================================
# PSEEK — DISCOVERY (the system searches MANY sources and learns which pay off)
# One call fans out across every configured job source (free JSON/RSS boards +
# Greenhouse/Lever + Adzuna), all Guardian-gated. Results are scored against the
# user's document pool, de-duplicated across sources, filtered by location focus,
# re-ranked by the learned preference model, and each source is a bandit arm that
# is rewarded when its jobs get approved/applied — so over time the system spends
# its searches on the sources that actually work for THIS user.
# =============================================================================
from arms.harvest import Fetcher, harvest
from arms.sources import build_sources
from jobs.context import JobsContext
from learning import QueryBandit, PreferenceModel


class Discovery:
    def __init__(self, workspace, config=None):
        self.ws = workspace
        self.g = workspace.guardian
        self.registry = workspace.registry
        self.config = config or {}
        self.bandit = QueryBandit(self.registry, key="source_bandit")
        self.prefs = PreferenceModel(self.registry)

    def sources(self):
        return build_sources(self.config, self.g)

    def _dedup(self, recs):
        seen, out = set(), []
        for r in recs:
            k = (r.title.lower().strip(), r.company.lower().strip())
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
        return out

    def search(self, pool, location_focus="toronto_remote", min_fit=0.1, limit=50):
        """Fan out across all sources; return ranked, de-duplicated records."""
        profile = pool.as_profile()
        ctx = JobsContext({"pool": profile})
        srcs = self.sources()
        for s in srcs:
            self.bandit.add_arm(getattr(s, "name", str(s)))
        recs = harvest(srcs, Fetcher(self.g), {"pool": profile}, ctx,
                       min_fit=min_fit, location_focus=location_focus)
        recs = self._dedup(recs)[:limit]
        recs = self.prefs.rerank(recs, keyfn=lambda r: r.job)
        self.registry.add_organelle("discovery",
                                    f"searched {len(srcs)} sources → {len(recs)} jobs",
                                    {"sources": [getattr(s, 'name', '') for s in srcs]})
        return recs

    def record_feedback(self, arr, action):
        """Feed a user action back: teach preferences AND reward the source."""
        self.prefs.record(arr.job, action)
        src = str(arr.job_id).split(":")[0]
        self.bandit.update(src, 1.0 if action in ("approve", "apply") else 0.0)

    def source_stats(self):
        return self.bandit.stats()

    def best_sources(self, k=3):
        stats = self.bandit.stats()
        return sorted(stats, key=lambda s: stats[s]["mean"], reverse=True)[:k]
