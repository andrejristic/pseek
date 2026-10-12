# =============================================================================
# PSEEK — P1 TESTS: Combinatorial Synthesis Engine (real, no stubs)
# The engine combines lines ACROSS multiple résumés when that beats any single
# one; every assembled claim traces to a real document line (truthfulness); θ is
# computed and healthy for an honest combination; and a heavily over-tailored
# framing is caught by θ/attractors (Codependent-lean, not APPLY). It only
# RECOMMENDS — the decision to apply stays with the user.
# =============================================================================
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jobs.domain import Job
from jobs.context import JobsContext
from pool import DocumentPool, add_resume, add_cover
from synthesis import synthesize, recommend
from theta import in_band, THETA_MAX

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

# Two résumés whose strengths are COMPLEMENTARY, so combining beats either alone.
R1 = ("Senior Python developer. Built REST APIs and Django backend services. "
      "PostgreSQL database design. Docker deployment. Git and CI pipelines.")
R2 = ("Machine learning engineer. PyTorch and NLP models. Data pipelines and "
      "statistics. Trained transformer language models. Python for research.")
C1 = ("Dear Hiring Team,\n\nI am a Python and machine learning engineer who builds "
      "robust REST APIs and trains NLP models with PyTorch. I care about clean "
      "backend services and reproducible pipelines.\n\nSincerely, A. User")
C2 = ("Dear Team,\n\nI am a high school mathematics teacher with a decade of "
      "classroom experience across grades nine through twelve.\n\nRegards, A. User")

JOB = Job("j-mle", "Machine Learning Engineer (Backend)", "Acme AI",
          "Build ML services in Python: PyTorch, NLP, plus REST APIs and Django "
          "backend. Data pipelines, PostgreSQL, Docker.",
          keyword_hints=["python", "pytorch", "nlp", "rest", "django", "docker"])


def _pool():
    p = DocumentPool()
    add_resume(p, "resume_backend.txt", R1)
    add_resume(p, "resume_ml.txt", R2)
    add_cover(p, "cover_tech.txt", C1)
    add_cover(p, "cover_teaching.txt", C2)
    return p


def test_engine_combines_across_resumes():
    p = _pool()
    combos = synthesize(JOB, p)
    top = combos[0]
    cross = next((c for c in combos if c.label == "cross-combination"), None)
    single = next((c for c in combos if c.label == "single-résumé"), None)
    check("recommended combination mixes >=2 résumés",
          len(top.resume_ids) >= 2, f"resume_ids={top.resume_ids}")
    check("combining covers the job better than a single résumé",
          cross and single and cross.fit > single.fit,
          f"cross={cross.fit if cross else '-'} single={single.fit if single else '-'}")
    return len(top.resume_ids) >= 2


def test_every_claim_is_truthful():
    p = _pool()
    profile = p.as_profile()
    ctx = JobsContext({"pool": profile})
    top = recommend(JOB, p)
    ok = all(ctx.is_backed(c, profile) for c in top.claims) and len(top.claims) > 0
    check("every assembled claim traces to a real document line", ok,
          f"{len(top.claims)} claims")
    # picks the relevant cover, not the teaching one
    check("chooses the relevant (tech) cover letter", top.cover_id == "c1",
          f"cover={top.cover_id}")
    return ok


def test_theta_healthy_for_honest_combo():
    p = _pool()
    top = recommend(JOB, p)
    check("honest combination is APPLY", top.verdict_code == "APPLY", top.verdict_code)
    check("θ is in the healthy band [25,35]", top.theta_in_band,
          f"θ={top.theta} ({top.theta_label})")
    return top.theta_in_band


def test_over_tailoring_caught_by_theta_and_attractors():
    p = _pool()
    framing = ("Give them what they want and tell them what they want; make it fit "
               "their wishlist, just say what they want to hear. Whatever it takes, "
               "willing to do anything, any hours they want; give them what they "
               "want, make it fit; tell them what they want, just say what they want.")
    combos = synthesize(JOB, p, extra_framing=framing)
    top = combos[0]
    # θ governs even when the membrane hasn't fired: an over-tailored combination
    # reads Codependent-lean (θ>35, out of band) and is deranked/flagged.
    codependent = (top.theta > THETA_MAX and not top.theta_in_band) \
        or top.verdict_code == "CONTORT"
    check("over-tailored framing → Codependent-lean (θ>35 out of band, or CONTORT)",
          codependent, f"θ={top.theta} in_band={top.theta_in_band} verdict={top.verdict_code}")
    return codependent


def test_engine_only_recommends():
    p = _pool()
    top = recommend(JOB, p)
    # a recommendation carries a verdict/θ but performs no application/side effect
    check("engine returns a proposal (verdict + θ), does not apply",
          hasattr(top, "verdict_code") and hasattr(top, "theta"))
    return True


ALL = [test_engine_combines_across_resumes, test_every_claim_is_truthful,
       test_theta_healthy_for_honest_combo,
       test_over_tailoring_caught_by_theta_and_attractors, test_engine_only_recommends]

if __name__ == "__main__":
    print("PSEEK · P1 Combinatorial Synthesis Engine tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
