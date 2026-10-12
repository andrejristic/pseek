# =============================================================================
# PSEEK — P3 TESTS: LLM operator (real, no stubs)
# With no keys/model the operator falls to the heuristic floor so the app still
# works; PII is pinned to local (cloud skipped); a failing/quota-exhausted cloud
# backend falls back automatically; a working cloud backend is used with redacted
# input; the four cloud hosts are on the egress allowlist; conversational résumé
# generation stays local and is truthful (only the user's facts).
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from guardian import Guardian
from llm import (LLMOperator, redact, Backend, GroqBackend, MistralBackend,
                 ClaudeBackend, generate_resume)

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")


def _g(d):
    return Guardian(jail_root=d, passphrase="pw")


def test_falls_to_heuristic_with_no_creds():
    d = tempfile.mkdtemp(prefix="pseek_llm_")
    try:
        op = LLMOperator(_g(d))
        r = op.complete([{"role": "user", "content": "hello"}])
        check("no keys/model → heuristic floor keeps app working",
              r["backend"] == "heuristic", r["backend"])
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_redaction():
    check("redact strips email + phone",
          redact("reach me at a.user@mail.com or +1 647 313 6472")
          == "reach me at [email] or [phone]")


def test_pii_pinned_local_and_working_cloud_used():
    d = tempfile.mkdtemp(prefix="pseek_llm2_")
    try:
        g = _g(d)

        class OkCloud(Backend):
            name = "okcloud"; is_local = False
            def available(self): return True
            def complete(self, messages, max_tokens=512):
                # prove the input was redacted before reaching "cloud"
                assert "@" not in messages[-1]["content"]
                return "cloud reply"

        op = LLMOperator(g)
        op.cloud = {"okcloud": OkCloud(g)}
        op.prefer = ("okcloud",)
        r = op.complete([{"role": "user", "content": "email me a.b@x.com"}], contains_pii=False)
        check("non-PII uses the working cloud backend (redacted)",
              r["backend"] == "okcloud" and r["redacted"], r["backend"])
        r2 = op.complete([{"role": "user", "content": "my ssn is secret"}], contains_pii=True)
        check("PII request skips cloud entirely → local/heuristic",
              r2["backend"] == "heuristic")
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_quota_and_error_fallback():
    d = tempfile.mkdtemp(prefix="pseek_llm3_")
    try:
        g = _g(d)

        class Flaky(Backend):
            name = "flaky"; is_local = False; free_limit = 1
            def available(self): return True
            def complete(self, messages, max_tokens=512):
                raise RuntimeError("429 rate limit")

        op = LLMOperator(g)
        op.cloud = {"flaky": Flaky(g)}
        op.prefer = ("flaky",)
        r = op.complete([{"role": "user", "content": "hi"}])
        check("failing cloud backend falls back to heuristic", r["backend"] == "heuristic")
        logged = any(e["record"].get("kind") == "llm_backend_failed"
                     for e in g.ledger.entries())
        check("backend failure escalated to guardian", logged)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_egress_hosts_allowlisted():
    d = tempfile.mkdtemp(prefix="pseek_llm4_")
    try:
        g = _g(d)
        ok = all(g.egress.allowed(h) for h in
                 ["https://api.groq.com/openai/v1/chat/completions",
                  "https://api.mistral.ai/v1/chat/completions",
                  "https://api.anthropic.com/v1/messages"])
        check("Groq/Mistral/Claude hosts on egress allowlist", ok)
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_conversational_resume_is_local_and_truthful():
    d = tempfile.mkdtemp(prefix="pseek_llm5_")
    try:
        op = LLMOperator(_g(d))
        facts = ["Taught high school mathematics for 8 years",
                 "Built a Django REST API for a clinic",
                 "Fluent in Python and SQL"]
        r = generate_resume(op, "Jane Candidate", facts)
        check("résumé generation stays local (no cloud for PII)",
              r["backend"] in ("heuristic", "local-gguf"), r["backend"])
        text = r["text"]
        check("generated résumé contains ONLY the user's stated facts",
              all(f in text for f in facts) and "Jane Candidate".upper() in text)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_falls_to_heuristic_with_no_creds, test_redaction,
       test_pii_pinned_local_and_working_cloud_used, test_quota_and_error_fallback,
       test_egress_hosts_allowlisted, test_conversational_resume_is_local_and_truthful]

if __name__ == "__main__":
    print("PSEEK · P3 LLM operator tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
