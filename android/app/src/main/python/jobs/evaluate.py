# =============================================================================
# PSE-JOBS — TRIAGE / EVALUATE (the pack's front door)
# Turns an Application into a kernel action, runs the verbatim kernel, and maps
# the resulting Decision onto a job-hunt verdict. This is what the Triage tab,
# the Chat console and the Approval gate all call. No kernel logic here — only
# construction of the action and interpretation of the Decision.
# =============================================================================
from dataclasses import dataclass
from pse_kernel import evaluate, nearest_attractor, ATTRACTORS
from .pack import JOBS_PACK


@dataclass
class Verdict:
    code: str
    emoji: str
    label: str        # Serbian, shown in the GUI
    escalate: bool    # does this need Andrej at the human_review() gate?

VERDICTS = {
    "APPLY":              Verdict("APPLY", "✅", "valja — pošteno se aplicira", False),
    "TRUTHFULNESS_BLOCK": Verdict("TRUTHFULNESS_BLOCK", "⛔", "laž — tvrdnja bez pokrića u rezimeu", True),
    "CONSENT_BLOCK":      Verdict("CONSENT_BLOCK", "⛔", "nema tvog odobrenja za slanje", True),
    "SCOPE_CREEP":        Verdict("SCOPE_CREEP", "⚠️", "scope-creep — posao ne paše nijednom profilu / over-reach", True),
    "CONTORT":            Verdict("CONTORT", "⚠️", "contort — izvrtanje sebe u wishlistu poslodavca", True),
    "BORDERLINE":         Verdict("BORDERLINE", "❓", "borderline — nekonzistentna persona, ti presudi", True),
    "UNAUTHORIZED":       Verdict("UNAUTHORIZED", "⛔", "van autorizacije", True),
}


@dataclass
class TriageResult:
    verdict: Verdict
    tool: str
    state: tuple            # (w_s, w_o, w_f)
    auth_level: float
    nearest: tuple          # (attractor_name, distance)
    fit_by_profile: dict    # {"teaching": .., "coding": ..}
    decision: object        # the raw kernel Decision (record, trace, intervention)

    @property
    def allowed(self):
        return self.verdict.code == "APPLY"


def build_action(app, tool="draft"):
    """Construct the kernel action for an Application. The artifact carries the
    floor semantics: 'submit:'/'draft:' prefix -> consent vs truthfulness gate."""
    art_kind = "submit" if tool == "submit" else "draft"
    return {
        "unit": "apply",
        "tool": tool,
        "target": app.job.job_id,
        "args": [],
        "rationale": app.rationale,
        "artifact": f"{art_kind}:{app.app_id}",
        "user_claims_authorized": False,
        "_app": app,
    }


def _classify_unauthorized(app, ctx, tool):
    p = ctx.profile(app.profile_key)
    unbacked = [c for c in app.claims if not ctx.is_backed(c, p)]
    if tool == "submit" and not app.approved and not unbacked and ctx.in_scope(app.job.job_id):
        return "CONSENT_BLOCK"
    if unbacked:
        return "TRUTHFULNESS_BLOCK"
    if not ctx.in_scope(app.job.job_id):
        return "SCOPE_CREEP"
    return "UNAUTHORIZED"


def _map_verdict(decision, app, ctx, tool):
    if decision.allowed:
        return VERDICTS["APPLY"]
    kind = decision.intervention.kind
    if kind == "unauthorized":
        return VERDICTS[_classify_unauthorized(app, ctx, tool)]
    if kind == "narcissistic":
        return VERDICTS["SCOPE_CREEP"]
    if kind == "codependent":
        return VERDICTS["CONTORT"]
    if kind == "borderline":
        return VERDICTS["BORDERLINE"]
    return VERDICTS["UNAUTHORIZED"]


def triage(app, ctx, audit, trajectory=None, tool="draft"):
    """Score one application. `trajectory` is this session's recent states; pass
    a persistent list to let Borderline (persona variance across the session) be
    detected. Returns a TriageResult ready for the GUI / chat / approval gate."""
    ctx.register_application(app)
    traj = trajectory if trajectory is not None else []
    action = build_action(app, tool)
    decision = evaluate(action, ctx, traj, JOBS_PACK, audit)

    fit = {k: round(p.fit(app.job), 3) for k, p in ctx._profiles.items()}
    return TriageResult(
        verdict=_map_verdict(decision, app, ctx, tool),
        tool=tool,
        state=decision.state,
        auth_level=decision.auth_level,
        nearest=nearest_attractor(decision.state, ATTRACTORS)[:2],
        fit_by_profile=fit,
        decision=decision,
    )
