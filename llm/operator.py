# =============================================================================
# PSEEK — LLM OPERATOR (quota-aware routing + PII safety)
# Picks a backend per request. PII stays LOCAL (never to a cloud model). For
# non-PII work it prefers a free cloud backend within its budget and, on any
# error or exhausted free quota, FALLS BACK automatically — down to local GGUF,
# and finally the heuristic floor so the app never dies. Cloud inputs are
# redacted first. The model is always a proposer; the physician/floors still
# gate any action its output implies.
# =============================================================================
import re

from .backends import (LlamaCppBackend, GroqBackend, MistralBackend,
                       ClaudeBackend, HeuristicBackend)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact(text):
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    return text


def redact_messages(messages):
    return [{**m, "content": redact(m.get("content", ""))} for m in messages]


class LLMOperator:
    def __init__(self, guardian, prefer=("groq", "mistral", "claude")):
        self.g = guardian
        self.local = LlamaCppBackend(guardian)
        self.cloud = {"groq": GroqBackend(guardian),
                      "mistral": MistralBackend(guardian),
                      "claude": ClaudeBackend(guardian)}
        self.prefer = prefer
        self.heuristic = HeuristicBackend(guardian)

    def _order(self, contains_pii):
        # local GGUF first (free workhorse); then preferred free cloud backends —
        # but if the payload is PII, cloud is skipped entirely.
        seq = [self.local]
        if not contains_pii:
            seq += [self.cloud[n] for n in self.prefer if n in self.cloud]
        return seq

    def complete(self, messages, contains_pii=False, max_tokens=512):
        for b in self._order(contains_pii):
            if not b.available() or not b.within_quota():
                continue
            payload = messages if b.is_local else redact_messages(messages)
            try:
                text = b.complete(payload, max_tokens)
                return {"text": text, "backend": b.name, "redacted": not b.is_local}
            except Exception as e:                 # quota / network / API error
                self.g.escalate("llm_backend_failed", f"{b.name}: {e}")
                continue
        text = self.heuristic.complete(messages, max_tokens)
        return {"text": text, "backend": self.heuristic.name, "redacted": False}

    def status(self):
        return {"local_gguf": self.local.available(),
                **{n: b.available() for n, b in self.cloud.items()}}
