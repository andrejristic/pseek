# =============================================================================
# PSEEK — SELF-INQUIRY ENGINE (the app probes the user to serve them better)
# The PSE Boundary Organ doesn't only absorb the other — it PROBES it. PSEEK asks
# questions, but only high-value ones: uncertainty (a borderline / out-of-band
# combination → ask instead of guess), contradiction (behaviour vs a stated
# preference), and gaps (decision-changing facts still missing). Each candidate
# has info_gain × impact; a per-session BUDGET (θ = attention spent on the other)
# keeps it to ≤1–2, so it never nags. Every answer becomes an organelle, so the
# self-model sharpens.
# =============================================================================
from dataclasses import dataclass, field

from jobs.geo import is_remote


@dataclass
class Question:
    qid: str
    kind: str
    text: str
    info_gain: float
    impact: float
    options: list = field(default_factory=list)

    @property
    def value(self):
        return self.info_gain * self.impact


class SelfInquiryEngine:
    # decision-changing facts, with how much each moves ranking (impact)
    GAP_FACTS = [
        ("salary_floor", "Koja ti je minimalna prihvatljiva plata?", 0.9),
        ("work_authorization", "Imaš li radnu dozvolu za ciljanu lokaciju?", 0.85),
        ("deal_breakers", "Šta su ti deal-breakeri (što nikad ne prihvataš)?", 0.8),
        ("availability", "Kad si dostupan za početak?", 0.5),
    ]
    MIN_VALUE = 0.5

    def __init__(self, registry):
        self.registry = registry

    def gap_questions(self):
        return [Question(f"gap:{k}", "gap", text, info_gain=1.0, impact=imp)
                for k, text, imp in self.GAP_FACTS
                if self.registry.get_pref(k) is None]

    def uncertainty_questions(self, combos):
        qs = []
        for c in combos or []:
            if getattr(c, "verdict_code", "") == "BORDERLINE" or not getattr(c, "theta_in_band", True):
                qs.append(Question(
                    f"unc:{c.label}", "uncertainty",
                    f"Kombinacija '{c.label}' je {c.theta_label} (θ={c.theta}). "
                    f"Je li krojenje pod ovaj posao plus ili minus za tebe?",
                    info_gain=0.8, impact=0.7,
                    options=["manje krojenja (ostani svoj)", "više krojenja (ka poslu)"]))
        return qs

    def contradiction_questions(self, recent_actions):
        qs = []
        loc = self.registry.get_pref("location_focus")
        for job, action in (recent_actions or []):
            if action == "approve" and loc == "remote" and not is_remote(job):
                qs.append(Question(
                    f"contra:{job.job_id}", "contradiction",
                    f"Rekao si remote-only, a odobrio si onsite '{job.title}'. "
                    f"Čemu da vjerujem?", info_gain=0.95, impact=1.0,
                    options=["ostani remote-only", "dozvoli i onsite"]))
        return qs

    def ask(self, budget=1, combos=None, recent_actions=None):
        cands = (self.gap_questions() + self.uncertainty_questions(combos)
                 + self.contradiction_questions(recent_actions))
        cands = [q for q in cands if q.value >= self.MIN_VALUE]
        cands.sort(key=lambda q: q.value, reverse=True)
        return cands[:max(0, budget)]

    def record_answer(self, qid, answer):
        kind, _, key = qid.partition(":")
        if kind == "gap":
            self.registry.set_pref(key, answer)
        elif kind == "contra" and "remote" not in str(answer).lower():
            self.registry.set_pref("location_focus", "toronto_remote")
        self.registry.add_organelle("self_inquiry", f"{qid} → {answer}",
                                    {"qid": qid, "answer": answer})
        return True
