# =============================================================================
# PSE-JOBS — DRAFT ARM + CONSENT FLOW
# Assembles an application (cover letter + claims) using ONLY résumé-backed
# bullets — every sentence traces to a line, so the truthfulness floor holds by
# construction. Nothing becomes sendable here: `ready_to_send` stays False until
# a human approves at the gate, at which point the kernel's SUBMIT verdict must
# clear the consent floor. That is the consent floor, enforced end to end.
# =============================================================================
from dataclasses import dataclass, field

from pse_kernel import NullAudit
from jobs.domain import Application, Claim
from jobs.evaluate import triage
from jobs.records import parse_candidate


@dataclass
class DraftedApplication:
    arr: object                      # ApplicationReadyRecord
    application: Application
    cover_letter: str
    claims_manifest: list            # [{claim, line_id, line_text}]
    draft_verdict: str               # kernel verdict of the (unsent) draft
    submit_verdict: str = "CONSENT_BLOCK"   # verdict of a submit attempt
    ready_to_send: bool = False      # flips True only after human approval


def _cover_letter(arr, candidate, bullets):
    company = arr.company or "your team"
    lines = [
        f"Dear {company} Hiring Team,",
        "",
        f"I am writing to apply for the {arr.title} position. My background is a "
        f"strong, direct match for this role.",
        "",
        "Relevant experience from my record:",
    ]
    lines += [f"  • {b.text}" for b in bullets]
    lines += [
        "",
        "I would welcome the chance to discuss how this experience fits your needs.",
        "",
        "Sincerely,",
        candidate.name,
        candidate.email or "",
    ]
    return "\n".join(l for l in lines if l is not None)


class DraftArm:
    def __init__(self, ctx, profiles, audit=None):
        self.ctx = ctx
        self.profiles = profiles
        self.audit = audit or NullAudit()

    def draft(self, arr, candidate=None):
        candidate = candidate or parse_candidate(self.profiles)
        profile = self.profiles[arr.best_profile]
        self.ctx.register_job(arr.job)

        claims = [Claim(b.text, b.source_line_id) for b in arr.bullets]
        app = Application(
            app_id=f"app-{arr.job_id}", job=arr.job, profile_key=arr.best_profile,
            claims=claims,
            rationale=f"Relevant experience, strong match for {arr.title}.")
        self.ctx.register_application(app)

        manifest = []
        for c in claims:
            line = profile.line(c.line_id)
            manifest.append({"claim": c.text, "line_id": c.line_id,
                             "line_text": line.text if line else None})

        cover = _cover_letter(arr, candidate, arr.bullets)
        draft_res = triage(app, self.ctx, self.audit, tool="draft")
        submit_res = triage(app, self.ctx, self.audit, tool="submit")   # unapproved
        return DraftedApplication(
            arr=arr, application=app, cover_letter=cover,
            claims_manifest=manifest, draft_verdict=draft_res.verdict.code,
            submit_verdict=submit_res.verdict.code, ready_to_send=False)

    def approve(self, drafted, guardian=None):
        """The consent gate. A human calls this; only then can it send."""
        self.ctx.approve(drafted.application.app_id)
        res = triage(drafted.application, self.ctx, self.audit, tool="submit")
        drafted.submit_verdict = res.verdict.code
        drafted.ready_to_send = (res.verdict.code == "APPLY")
        if guardian is not None:
            guardian.ledger.append({"event": "application_approved",
                                    "app": drafted.application.app_id,
                                    "job": drafted.arr.job_id,
                                    "verdict": res.verdict.code})
        return res

    def reject(self, drafted, guardian=None):
        drafted.ready_to_send = False
        drafted.submit_verdict = "REJECTED"
        if guardian is not None:
            guardian.ledger.append({"event": "application_rejected",
                                    "app": drafted.application.app_id})
