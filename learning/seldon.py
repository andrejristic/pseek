# =============================================================================
# PSE-JOBS — SELDON ENGINE (macro strategy analysis)
# The corpus's Seldon Engine, applied to the job hunt: it reads the accumulated
# application outcomes and asks which strategies actually survive — which profile
# gets responses, interviews, offers. Deterministic rates over the tracker's
# history. Its recommendation feeds back as a preference: the system gets better
# because it learns what works.
# =============================================================================


class SeldonEngine:
    RESPONSE_STATES = {"REPLIED", "INTERVIEW", "OFFER"}

    @staticmethod
    def _rate(n, d):
        return round(n / d, 3) if d else 0.0

    def analyze(self, tracker):
        overall = {"sent": 0, "responded": 0, "interview": 0, "offer": 0}
        by_profile = {}
        for a in tracker.all():
            reached = {h["state"] for h in a["history"]}
            if "SENT" not in reached:
                continue                        # only sent applications inform strategy
            prof = a.get("profile") or "?"
            d = by_profile.setdefault(prof, {"sent": 0, "responded": 0,
                                             "interview": 0, "offer": 0})
            for bucket in (d, overall):
                bucket["sent"] += 1
                if reached & self.RESPONSE_STATES:
                    bucket["responded"] += 1
                if "INTERVIEW" in reached:
                    bucket["interview"] += 1
                if "OFFER" in reached:
                    bucket["offer"] += 1

        for d in list(by_profile.values()) + [overall]:
            d["response_rate"] = self._rate(d["responded"], d["sent"])
            d["interview_rate"] = self._rate(d["interview"], d["sent"])
            d["offer_rate"] = self._rate(d["offer"], d["sent"])

        recommend = None
        if by_profile:
            recommend = max(by_profile,
                            key=lambda p: (by_profile[p]["response_rate"],
                                           by_profile[p]["offer_rate"],
                                           by_profile[p]["sent"]))
        return {"overall": overall, "by_profile": by_profile,
                "recommend_profile": recommend}
