# =============================================================================
# PSEEK — OUTCOME LEARNING (Loop C: which strategies actually earn replies)
# Over accumulated outcomes, find which keywords distinguish jobs that RESPONDED
# from jobs that GHOSTED, then turn that into truthful résumé/cover advice: if a
# response-linked keyword is buried in the document pool, suggest LEADING with the
# exact line; if it's absent, suggest CONSIDERING adding it — only "if true", so
# the truthfulness floor is never crossed. Pairs with the corpus Seldon engine
# (profile-level response rates) for the macro picture.
# =============================================================================
from collections import Counter


class OutcomeLearner:
    def __init__(self, registry=None):
        self.registry = registry

    def response_signal(self, responded_jobs, ghosted_jobs):
        resp, gh = Counter(), Counter()
        for j in responded_jobs:
            resp.update(j.keywords)
        for j in (ghosted_jobs or []):
            gh.update(j.keywords)
        return [t for t, _ in resp.most_common() if resp[t] > gh[t]]

    def suggest_edits(self, pool, responded_jobs, ghosted_jobs=None, lead_n=3, top=8):
        signal = self.response_signal(responded_jobs, ghosted_jobs)
        lines = pool.all_lines()
        suggestions = []
        for kw in signal[:top]:
            hit = next((ln for ln in lines if kw in ln.toks), None)
            if hit:
                doc_lines = [l for l in lines if l.profile == hit.profile]
                if doc_lines.index(hit) >= lead_n:      # buried below the fold
                    suggestions.append({
                        "type": "lead_with", "keyword": kw,
                        "line_id": hit.line_id, "text": hit.text,
                        "why": f"'{kw}' shows up in roles that replied — lead with it."})
            else:
                suggestions.append({
                    "type": "consider_adding", "keyword": kw,
                    "why": f"roles that replied mention '{kw}' — add it IF TRUE."})
        if self.registry is not None and suggestions:
            self.registry.add_organelle(
                "outcome_advice", f"{len(suggestions)} résumé/cover suggestions",
                {"keywords": signal[:top]})
        return suggestions
