# =============================================================================
# PSEEK — COMBINATORIAL SYNTHESIS ENGINE (CSE)  ← the core
# For a given job, search over COMBINATIONS of the user's documents: which résumé
# lines (possibly mixed across several résumés) + which cover-letter paragraphs to
# assemble into one honest pitch. Each candidate is scored on the kernel simplex;
# θ governs the self/other balance of the combination and the attractors are the
# guardrails — a combination that leans Narcissistic (over-self) or Codependent
# (over-other) is deranked/flagged. Everything is drawn from real document lines
# (truthfulness holds by construction). The engine RECOMMENDS; the human decides
# whether to apply (physician).
# =============================================================================
from dataclasses import dataclass

from pse_kernel import NullAudit
from jobs.domain import Claim, Application, tokens
from jobs.context import JobsContext
from jobs.evaluate import triage
from theta import theta_from_state, in_band, band_label


@dataclass
class Combination:
    label: str
    line_ids: list          # the résumé lines assembled
    resume_ids: list        # distinct résumés mixed (the "combine 2 résumés" part)
    cover_id: str           # chosen cover letter
    cover_para_ids: list    # chosen paragraphs
    claims: list            # Claim objects (each provenanced)
    fit: float              # job-keyword coverage of the assembled lines
    state: tuple            # (w_s, w_o, w_f)
    theta: float            # self/other allocation
    theta_in_band: bool
    theta_label: str
    verdict_code: str       # kernel verdict of the combination
    nearest: tuple          # (attractor, distance)


def _combo_fit(lines, jk):
    kw = set()
    for ln in lines:
        kw |= ln.toks
    return len(jk & kw) / len(jk) if jk else 0.0


def _best_cover(pool, jk, top=1):
    best, best_score, best_paras = None, -1, []
    for cd in pool.covers:
        paras = sorted(cd.paragraphs, key=lambda p: len(tokens(p[1]) & jk), reverse=True)
        score = sum(len(tokens(p[1]) & jk) for p in paras[:top])
        if score > best_score:
            best, best_score, best_paras = cd, score, paras[:top]
    return (best.doc_id if best else None), best_paras


def synthesize(job, pool, top_lines=5, extra_framing=""):
    """Return candidate Combinations for `job`, ranked best-first. The recommended
    combination is result[0]. Does NOT apply — that's the user's decision."""
    profile = pool.as_profile()
    ctx = JobsContext({"pool": profile})
    ctx.register_job(job)
    jk = job.keywords

    ranked = sorted(profile.lines, key=lambda ln: len(ln.toks & jk), reverse=True)
    relevant = [ln for ln in ranked if len(ln.toks & jk) > 0]

    # per-résumé grouping, to offer a single-résumé alternative for comparison
    by_doc = {}
    for ln in relevant:
        by_doc.setdefault(ln.profile, []).append(ln)
    best_doc = max(by_doc, key=lambda d: sum(len(l.toks & jk) for l in by_doc[d])) \
        if by_doc else None

    candidates = [
        ("cross-combination", relevant[:top_lines]),          # mixes résumés
        ("single-résumé", (by_doc.get(best_doc, []))[:top_lines]),
        ("lean", relevant[:3]),
    ]

    cover_id, cover_paras = _best_cover(pool, jk)
    cover_text = " ".join(p[1] for p in cover_paras)

    out, seen = [], set()
    for i, (label, lines) in enumerate(candidates):
        key = tuple(ln.line_id for ln in lines)
        if not lines or key in seen:
            continue
        seen.add(key)
        claims = [Claim(" ".join(ln.text.split()[:12]), ln.line_id) for ln in lines]
        rationale = (f"Honest match for {job.title}. {cover_text[:180]} {extra_framing}").strip()
        app = Application(f"cse-{job.job_id}-{i}", job, "pool", claims=claims,
                          rationale=rationale)
        res = triage(app, ctx, NullAudit(), tool="draft")
        th = theta_from_state(res.state)
        out.append(Combination(
            label=label,
            line_ids=[ln.line_id for ln in lines],
            resume_ids=sorted({ln.profile for ln in lines}),
            cover_id=cover_id, cover_para_ids=[p[0] for p in cover_paras],
            claims=claims, fit=round(_combo_fit(lines, jk), 3),
            state=res.state, theta=round(th, 1), theta_in_band=in_band(th),
            theta_label=band_label(th), verdict_code=res.verdict.code,
            nearest=res.nearest))

    # rank: healthy verdict first, then θ in band, then best coverage, then richer mix
    out.sort(key=lambda c: (c.verdict_code != "APPLY", not c.theta_in_band,
                            -c.fit, -len(c.resume_ids)))
    return out


def recommend(job, pool):
    combos = synthesize(job, pool)
    return combos[0] if combos else None
