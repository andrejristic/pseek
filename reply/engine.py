# =============================================================================
# PSEEK — EMPLOYER-RESPONSE ARM (read → advise → draft reply → interview prep)
# When an employer replies, PSEEK reads the message AS DATA (never as
# instructions), classifies it, advises how to behave toward the employer, drafts
# a reply, and — for an interview invite — prepares talking points from the job +
# accumulated research. θ keeps the reply authentic: it does NOT over-accommodate
# (Codependent) — e.g. it never accepts an offer on the spot; accepting is the
# user's decision (physician). Sending the reply is the `reply_employer` decision
# class, so it escalates for approval.
# =============================================================================
from mailarm.robot import RobotMailer
from physician import PhysicianGate


def classify_response(text):
    t = (text or "").lower()
    if any(k in t for k in ("unfortunately", "not moving forward", "other candidates",
                            "won't be proceeding", "decided not to", "regret to")):
        return "rejection"
    if any(k in t for k in ("pleased to offer", "offer letter", "compensation",
                            "we would like to offer", "start date")):
        return "offer"
    if any(k in t for k in ("interview", "schedule", "availability", "hop on a call",
                            "meet", "chat with", "next steps", "phone screen")):
        return "interview"
    if any(k in t for k in ("could you", "please provide", "a few questions",
                            "clarify", "send us", "share your")):
        return "question"
    return "other"


ADVICE = {
    "interview": "Pozitivno i konkretno: potvrdi interes, ponudi 2–3 termina, "
                 "kratko istakni relevantno iskustvo. Entuzijazam bez pretjerivanja (θ zdravo).",
    "rejection": "Zahvali profesionalno, zatraži kratak feedback, ostavi vrata "
                 "otvorena za buduće uloge.",
    "offer":     "Zahvali i pokaži uzbuđenje, ali zatraži vrijeme za razmatranje "
                 "detalja. NE prihvataj odmah — prihvatanje je tvoja odluka.",
    "question":  "Odgovori tačno i sažeto, samo na pitano, bez naduvavanja.",
    "other":     "Odgovori ljubazno i kratko.",
}

_TEMPLATES = {
    "interview": "Thank you for the invitation to interview for {role}. I'm very "
                 "interested and available at the following times: [propose 2–3 slots]. "
                 "Please let me know what works best.",
    "rejection": "Thank you for letting me know, and for considering my application. "
                 "If you have any brief feedback I'd welcome it, and I hope we can stay "
                 "in touch for future roles.",
    "offer":     "Thank you very much for the offer for {role} — I'm excited about it. "
                 "Could I have a short time to review the details before confirming?",
    "question":  "Thank you for your message. [Answer the specific question concisely.]",
    "other":     "Thank you for your message. [Reply here.]",
}


class EmployerResponseArm:
    def __init__(self, guardian, operator=None, registry=None, physician=None):
        self.g = guardian
        self.op = operator
        self.registry = registry
        self.physician = physician or PhysicianGate(guardian)

    def read(self, raw_or_text):
        if isinstance(raw_or_text, (bytes, bytearray)):
            return RobotMailer.parse_message(raw_or_text)
        return {"from": "", "subject": "", "snippet": str(raw_or_text),
                "body": str(raw_or_text)}

    def handle(self, raw_or_text, job=None):
        parsed = self.read(raw_or_text)
        text = parsed.get("snippet") or parsed.get("body") or ""
        kind = classify_response(text)
        role = job.title if job else "the role"
        reply = _TEMPLATES[kind].format(role=role)
        result = {"kind": kind, "advice": ADVICE[kind], "reply_draft": reply,
                  "from": parsed.get("from", ""), "interview_prep": None}
        if kind == "interview":
            result["interview_prep"] = self.interview_prep(job)
        if self.registry is not None:
            self.registry.add_organelle("employer_response",
                                        f"{kind} from {parsed.get('from','')}",
                                        {"kind": kind})
        return result

    def interview_prep(self, job):
        points = ["Ukratko ispričaj zašto baš ova uloga i firma (2 rečenice)."]
        if job is not None:
            for kw in list(job.keywords)[:5]:
                points.append(f"Pripremi konkretan primjer za: {kw}")
        if self.registry is not None:
            for o in self.registry.organelles("research")[:3]:
                points.append(f"Iskoristi istraženo: {o['text'][:80]}")
        points.append("Pripremi 2–3 pitanja za njih (pokaži interes, θ zdravo).")
        return points

    def send_reply(self, job, reply_text, mailer, approved=False, dry_run=None):
        # sending a reply is a physician decision
        status, reason = self.physician.check("reply_employer", approved=approved,
                                              detail=job.job_id if job else "")
        if status == "escalate":
            return {"status": "escalate", "reason": reason}
        configured = self.g.has_secret("user_email")
        do_dry = (not configured) if dry_run is None else dry_run
        res = mailer.send_application(job, reply_text, approved=True, dry_run=do_dry)
        return {"status": "sent" if res.get("sent") else "dry_run",
                "message": res.get("message")}
