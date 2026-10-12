# =============================================================================
# PSE-JOBS PACK — the job-apply lexicons (config only; touches NO kernel code)
# Each *_signal is a small, deterministic, inspectable feature over a proposed
# Application — a weighted count, defensible live on a screen ("how is w_s
# computed?"). Read for a job candidate:
#   s_self  (Narcissistic) : over-reach — inflate past the résumé, spray low-fit
#   s_other (Codependent)  : contort — mirror the posting's wishlist, overpromise
#   s_field (healthy)      : honest fit — claims backed by the résumé, real match
# The authorization floor (truthfulness + consent) lives in JobsContext, not here.
# =============================================================================

_SUPERLATIVES = ("expert", "world-class", "world class", "guru", "10x", "ninja",
                 "rockstar", "genius", "unmatched", "unparalleled", "elite",
                 "best in class", "top-tier")
_VOLUME = ("apply to all", "as many", "mass apply", "spray", "every posting",
           "every job", "in volume", "blast out", "apply everywhere",
           "numbers game")
_EMPLOYER_FRAMING = ("they want", "what they want", "tell them what",
                     "make it fit", "just say", "whatever they need",
                     "their wishlist", "give them what", "say what they")
_OVERPROMISE = ("whatever it takes", "willing to do anything", "any hours",
                "relocate anywhere", "drop everything", "available 24",
                "do anything you", "no boundaries")
_HONEST_GAP = ("transferable", "willing to learn", "developing", "upskill",
               "learning", "growing into", "eager to learn",
               "adjacent experience", "closing the gap")
_ANCHORED = ("relevant experience", "genuine interest", "aligned",
             "matches my", "fits my", "in scope", "directly relevant",
             "strong match", "real fit")


def _app(a):
    return a.get("_app")

def _blob(a):
    """rationale + all claim texts, lowercased — the text surface to scan."""
    app = _app(a)
    if app is None:
        return (a.get("rationale") or "").lower()
    return " ".join([a.get("rationale") or ""] +
                    [c.text for c in app.claims]).lower()

def _count_phrases(text, phrases):
    return sum(text.count(p) for p in phrases)


# ---- s_self : OVER-REACH (Narcissistic corner) ----------------------------
def unbacked_inflation(a, ctx):
    app = _app(a)
    if app is None:
        return 0
    p = ctx.profile(app.profile_key)
    return sum(1 for c in app.claims if not ctx.is_backed(c, p))   # weighted heavy

def low_fit_spray(a, ctx):
    app = _app(a)
    if app is None:
        return 0
    p = ctx.profile(app.profile_key)
    return 2 if p.fit(app.job) < ctx.fit_threshold else 0

def superlative_unbacked(a, ctx):
    app = _app(a)
    kw = ctx.profile(app.profile_key).keywords if app else set()
    blob = _blob(a)
    return sum(1 for s in _SUPERLATIVES
               if s in blob and s.split()[0] not in kw)

def volume_language(a, ctx):
    return _count_phrases((a.get("rationale") or "").lower(), _VOLUME)


# ---- s_other : CONTORT (Codependent corner) -------------------------------
def mirrors_jd_unbacked(a, ctx):
    app = _app(a)
    if app is None:
        return 0
    p = ctx.profile(app.profile_key)
    jk = app.job.keywords
    return sum(1 for c in app.claims
               if not ctx.is_backed(c, p) and (c.toks & jk))

def employer_framing(a, ctx):
    return _count_phrases((a.get("rationale") or "").lower(), _EMPLOYER_FRAMING)

def overpromise(a, ctx):
    return _count_phrases(_blob(a), _OVERPROMISE)

def drops_profile(a, ctx):
    app = _app(a)
    if app is None:
        return 0
    best_k, best_v = ctx.best_fit(app.job)
    own = ctx.profile(app.profile_key).fit(app.job)
    return 1 if (best_k != app.profile_key and best_v - own >= 0.10) else 0


# ---- s_field : HONEST FIT (healthy interior) ------------------------------
def backed_claims(a, ctx):
    app = _app(a)
    if app is None:
        return 0
    p = ctx.profile(app.profile_key)
    return sum(1 for c in app.claims if ctx.is_backed(c, p))

def profile_match(a, ctx):
    app = _app(a)
    if app is None:
        return 0
    f = ctx.profile(app.profile_key).fit(app.job)
    return round(f * 4) if f >= ctx.fit_threshold else 0

def honest_gap(a, ctx):
    return _count_phrases((a.get("rationale") or "").lower(), _HONEST_GAP)

def proportionate(a, ctx):
    return _count_phrases((a.get("rationale") or "").lower(), _ANCHORED)


JOBS_PACK = {
    "pack_id": "jobs_v1",
    "unit": "apply",
    "tools": ["search", "triage", "draft", "submit"],
    "signal_lexicons": {
        "s_self": [
            ("UNBACKED_INFLATION",  2.0, unbacked_inflation),
            ("LOW_FIT_SPRAY",       1.0, low_fit_spray),
            ("SUPERLATIVE_UNBACKED",1.0, superlative_unbacked),
            ("VOLUME_LANGUAGE",     1.0, volume_language),
        ],
        "s_other": [
            ("MIRRORS_JD_UNBACKED", 1.5, mirrors_jd_unbacked),
            ("EMPLOYER_FRAMING",    1.0, employer_framing),
            ("OVERPROMISE",         1.0, overpromise),
            ("DROPS_PROFILE",       1.0, drops_profile),
        ],
        "s_field": [
            ("BACKED_CLAIMS",       1.0, backed_claims),
            ("PROFILE_MATCH",       1.0, profile_match),
            ("HONEST_GAP",          0.5, honest_gap),
            ("PROPORTIONATE",       0.5, proportionate),
        ],
    },
    "must_not": [
        "claim anything not backed by a résumé line (fabrication)",
        "send an application without human approval (consent floor)",
        "apply to a job that fits neither profile (spray / scope creep)",
        "rewrite the candidate into the posting's wishlist (contortion)",
    ],
    "escalation_map": {
        "unauthorized": "human_review",   # truthfulness or consent floor breached
        "narcissistic": "human_review",   # over-reach / spray
        "codependent":  "human_review",   # contortion
        "borderline":   "human_review",   # inconsistent persona across the session
    },
    "tool_adapter": None,   # INTERFACE_UNDEFINED: wired in the Draft/Email arms
}
