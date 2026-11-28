# =============================================================================
# PSEEK — MODE 2: ON-THE-JOB ASSISTANT
# The moment the user lands a job (accepts an offer — a physician decision),
# PSEEK transforms: it studies the web for THAT role and helps the user do it —
# onboarding, tasks, skills. Same kernel/floors/θ/physician: it prepares and
# advises, never decides; θ keeps the user's growth centred, not just the
# employer's wishlist. Gated to the pro tier (or the trial). Findings become
# organelles so the help compounds.
# =============================================================================
from jobs.domain import tokens
from physician import PhysicianGate


class OnTheJobAssistant:
    def __init__(self, guardian, research=None, registry=None, physician=None,
                 entitlements=None):
        self.g = guardian
        self.research = research
        self.registry = registry
        self.physician = physician or PhysicianGate(guardian)
        self.entitlements = entitlements

    def available(self):
        return self.entitlements is None or self.entitlements.can_use("mode2")

    def activate(self, role, company, role_text=None, company_text=None):
        if not self.available():
            return {"status": "locked", "need": "pro tier"}
        findings = []
        if self.research is not None:
            if role_text:
                findings.append(self.research.research_from_text("role", role, role_text, role))
            if company_text:
                findings.append(self.research.research_from_text("company", company,
                                                                 company_text, company))
        if self.registry is not None:
            self.registry.set_pref("employed_role", role)
            self.registry.set_pref("employer", company)
            self.registry.add_organelle("mode2_activation", f"Started at {company} as {role}")
        return {"status": "active", "role": role, "company": company, "findings": findings}

    def skill_plan(self, role, role_text=""):
        kws = list(tokens(f"{role} {role_text}"))[:8]
        return [f"Osnaži: {k}" for k in kws]

    def help_with(self, task, task_text="", approved=False):
        advice = ""
        if self.research is not None and task_text:
            advice = self.research.summarize(task_text, task)
        return {"task": task,
                "advice": advice or f"Za '{task}': razloži na korake i provjeri "
                                    f"primjere; centriraj svoj razvoj (θ zdravo)."}

    def act(self, action_type, approved=False, detail=""):
        """Any outward/irreversible on-the-job action still passes the physician."""
        return self.physician.check(action_type, approved=approved, detail=detail)
