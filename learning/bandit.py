# =============================================================================
# PSEEK — QUERY / DISCOVERY BANDIT (Loop B: learn WHERE and HOW to search)
# Each search "angle" (source × query × location) is a bandit arm. We spend more
# searches on angles that yield approvals/responses using UCB1 (deterministic —
# unpulled arms are explored first, then reward-mean + exploration bonus). We also
# expand queries from the keywords of accepted jobs and prune terms that only ever
# come from rejects. Persisted per-user, so discovery gets better over time.
# =============================================================================
import math
from collections import Counter

from jobs.domain import tokens


class QueryBandit:
    def __init__(self, registry=None, key="query_bandit"):
        self.registry = registry
        self.key = key
        self.arms = dict(registry.get_pref(key, {})) if registry else {}

    def _save(self):
        if self.registry is not None:
            self.registry.set_pref(self.key, self.arms)

    def add_arm(self, arm):
        self.arms.setdefault(arm, {"pulls": 0, "reward": 0.0})
        self._save()

    def _total(self):
        return sum(a["pulls"] for a in self.arms.values())

    def _ucb(self, arm, total):
        d = self.arms[arm]
        if d["pulls"] == 0:
            return float("inf")             # explore unpulled arms first
        mean = d["reward"] / d["pulls"]
        return mean + math.sqrt(2.0 * math.log(max(1, total)) / d["pulls"])

    def select(self):
        if not self.arms:
            return None
        total = self._total()
        # tie-break deterministically by arm name
        return max(sorted(self.arms), key=lambda a: self._ucb(a, total))

    def update(self, arm, reward):
        d = self.arms.setdefault(arm, {"pulls": 0, "reward": 0.0})
        d["pulls"] += 1
        d["reward"] += float(reward)
        self._save()

    def stats(self):
        return {a: {"pulls": d["pulls"],
                    "mean": round(d["reward"] / d["pulls"], 3) if d["pulls"] else 0.0}
                for a, d in self.arms.items()}


def suggest_queries(accepted_jobs, rejected_jobs=None, top=8):
    """Terms frequent in accepted jobs and not dominated by rejects — the queries
    the search should lean into next."""
    acc, rej = Counter(), Counter()
    for j in accepted_jobs:
        acc.update(j.keywords)
    for j in (rejected_jobs or []):
        rej.update(j.keywords)
    return [t for t, _ in acc.most_common() if acc[t] >= rej[t]][:top]
