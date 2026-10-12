# =============================================================================
# PSEEK — APPLY ARM (apply for the user, from the user's own email)
# Turns a chosen CSE Combination into a truthful application (cover assembled from
# the combination's cover paragraphs + its résumé-backed bullets) and sends it —
# but only after the PHYSICIAN gate (the user's explicit approval) and the three
# mail gates. Until an email is connected it composes a dry-run. Every send is
# recorded in the tracker.
# =============================================================================
from mailarm.user_mailer import UserMailer, EmailError
from physician import PhysicianGate


def build_cover(combination, job, pool, candidate_name="Candidate"):
    parts = [f"Dear {job.company or 'Hiring Team'},", "",
             f"I am writing to apply for the {job.title} position."]
    cov = pool.cover(combination.cover_id) if combination.cover_id else None
    if cov:
        by_id = dict(cov.paragraphs)
        for pid in combination.cover_para_ids:
            if by_id.get(pid):
                parts += ["", by_id[pid]]
    if combination.claims:
        parts += ["", "Relevant experience:"]
        parts += [f"  • {c.text}" for c in combination.claims]
    parts += ["", "Sincerely,", candidate_name]
    return "\n".join(parts)


class ApplyArm:
    def __init__(self, guardian, tracker, mailer=None, physician=None):
        self.g = guardian
        self.tracker = tracker
        self.mailer = mailer or UserMailer(guardian)
        self.physician = physician or PhysicianGate(guardian)

    def apply(self, job, combination, pool, candidate_name="Candidate",
              approved=False, dry_run=None):
        # PHYSICIAN gate — applying is the user's decision
        status, reason = self.physician.check("apply", approved=approved, detail=job.job_id)
        if status == "escalate":
            return {"status": "escalate", "reason": reason}

        cover = build_cover(combination, job, pool, candidate_name)
        configured = self.g.has_secret("user_email")
        do_dry = (not configured) if dry_run is None else dry_run
        try:
            res = self.mailer.send_application(job, cover, approved=True,
                                               to_addr=job.contact, dry_run=do_dry)
        except EmailError as e:
            return {"status": "error", "reason": str(e), "cover": cover}

        aid = f"app-{job.job_id}"
        if self.tracker.get(aid) is None:
            self.tracker.add(aid, job_id=job.job_id, title=job.title,
                             company=job.company, profile=combination.label,
                             state="APPROVED")
        if res.get("sent"):
            self.tracker.transition(aid, "SENT")
        return {"status": "sent" if res.get("sent") else "dry_run",
                "message": res.get("message"), "cover": cover}
