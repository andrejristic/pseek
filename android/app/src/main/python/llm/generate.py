# =============================================================================
# PSEEK — CONVERSATIONAL DOCUMENT GENERATION
# The app can write a résumé or cover letter WITH the user, by conversation. The
# generated doc then joins the document pool and feeds the CSE. It is a résumé
# with PII, so generation is pinned to LOCAL models (never sent to a cloud LLM).
# When no model is connected, the heuristic floor ASSEMBLES the document
# deterministically from ONLY the facts the user stated — so it is truthful by
# construction, never inventing beyond the user's input.
# =============================================================================


def _assemble_resume(name, facts):
    out = [name.upper(), "", "EXPERIENCE & SKILLS"]
    out += [f"• {f}" for f in facts]
    return "\n".join(out)


def _assemble_cover(name, company, role, facts):
    out = [f"Dear {company or 'Hiring Team'},", "",
           f"I am writing to apply for the {role} position. My relevant background:"]
    out += [f"  • {f}" for f in facts]
    out += ["", "Sincerely,", name]
    return "\n".join(out)


def generate_resume(operator, name, facts):
    msgs = [
        {"role": "system", "content": "You write a truthful résumé using ONLY the "
         "facts the user provides. Never invent anything not stated."},
        {"role": "user", "content": f"Candidate: {name}\nFacts:\n"
         + "\n".join(f"- {f}" for f in facts) + "\n\nWrite a concise résumé from ONLY these facts."},
    ]
    r = operator.complete(msgs, contains_pii=True)      # PII → local only
    text = _assemble_resume(name, facts) if r["backend"] == "heuristic" else r["text"]
    return {"text": text, "backend": r["backend"], "source_facts": list(facts)}


def generate_cover(operator, name, company, role, facts):
    msgs = [
        {"role": "system", "content": "You write a truthful cover letter using ONLY "
         "the facts the user provides. Never invent anything."},
        {"role": "user", "content": f"Candidate: {name}\nCompany: {company}\nRole: "
         f"{role}\nFacts:\n" + "\n".join(f"- {f}" for f in facts)
         + "\n\nWrite a concise cover letter from ONLY these facts."},
    ]
    r = operator.complete(msgs, contains_pii=True)
    text = _assemble_cover(name, company, role, facts) if r["backend"] == "heuristic" else r["text"]
    return {"text": text, "backend": r["backend"], "source_facts": list(facts)}
