# =============================================================================
# PSEEK — LLM BACKENDS (Groq · Mistral · Claude · local GGUF via llama.cpp)
# One interface, four real backends. The seller supplies only FREE-tier online
# keys, so each cloud backend tracks its free call budget; local GGUF (llama.cpp)
# is the workhorse and needs no key or egress. A HeuristicBackend is the always-
# available floor so the app keeps working with no model and no keys. Every cloud
# call goes through the Guardian egress wall; keys come from the vault, so no
# agent ever sees them raw.
# =============================================================================
import json
import os
import urllib.request


class Backend:
    name = "base"
    is_local = False
    free_limit = None          # None = no tracked limit
    key_name = None

    def __init__(self, guardian):
        self.g = guardian
        self.calls = 0

    def available(self):
        return False

    def within_quota(self):
        return self.free_limit is None or self.calls < self.free_limit

    def complete(self, messages, max_tokens=512):
        raise NotImplementedError


# ---- cloud backends (real HTTP; activate when a free key is in the vault) ---
class _OpenAICompatible(Backend):
    """Groq and Mistral both speak the OpenAI chat-completions shape."""
    host = ""
    path = "/v1/chat/completions"
    model = ""

    def available(self):
        return self.g.has_secret(self.key_name)

    def complete(self, messages, max_tokens=512):
        url = f"https://{self.host}{self.path}"
        self.g.guard_egress(url)
        key = self.g.secret(self.key_name)
        body = json.dumps({"model": self.model, "messages": messages,
                           "max_tokens": max_tokens}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read())
        self.calls += 1
        return data["choices"][0]["message"]["content"]


class GroqBackend(_OpenAICompatible):
    name = "groq"
    host = "api.groq.com"
    path = "/openai/v1/chat/completions"
    model = "llama-3.1-8b-instant"
    free_limit = 1000
    key_name = "groq_api_key"


class MistralBackend(_OpenAICompatible):
    name = "mistral"
    host = "api.mistral.ai"
    model = "mistral-small-latest"
    free_limit = 500
    key_name = "mistral_api_key"


class ClaudeBackend(Backend):
    name = "claude"
    host = "api.anthropic.com"
    model = "claude-haiku-4-5-20251001"
    free_limit = 300
    key_name = "anthropic_api_key"

    def available(self):
        return self.g.has_secret(self.key_name)

    def complete(self, messages, max_tokens=512):
        url = f"https://{self.host}/v1/messages"
        self.g.guard_egress(url)
        key = self.g.secret(self.key_name)
        system = " ".join(m["content"] for m in messages if m.get("role") == "system")
        turns = [m for m in messages if m.get("role") != "system"]
        body = json.dumps({"model": self.model, "max_tokens": max_tokens,
                           "system": system, "messages": turns}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read())
        self.calls += 1
        return "".join(b.get("text", "") for b in data.get("content", []))


# ---- local GGUF via llama.cpp (the workhorse) ------------------------------
class LlamaCppBackend(Backend):
    name = "local-gguf"
    is_local = True

    def __init__(self, guardian, model_path=None):
        super().__init__(guardian)
        self.model_path = model_path or os.environ.get("PSEEK_GGUF_MODEL")
        self._llm = None

    def available(self):
        try:
            import llama_cpp  # noqa: F401
        except Exception:
            return False
        return bool(self.model_path and os.path.exists(self.model_path))

    def complete(self, messages, max_tokens=512):
        if self._llm is None:
            from llama_cpp import Llama
            self._llm = Llama(model_path=self.model_path, n_ctx=4096, verbose=False)
        out = self._llm.create_chat_completion(messages=messages, max_tokens=max_tokens)
        self.calls += 1
        return out["choices"][0]["message"]["content"]


# ---- always-available floor ------------------------------------------------
class HeuristicBackend(Backend):
    """No model, no key: keeps the app functional. It does not invent free-form
    prose; it returns a concise, honest acknowledgement, and the generators
    (llm/generate.py) assemble documents deterministically from the user's own
    stated facts when this floor is in use."""
    name = "heuristic"
    is_local = True

    def available(self):
        return True

    def complete(self, messages, max_tokens=512):
        last = messages[-1]["content"] if messages else ""
        return ("[lokalni odgovor — poveži GGUF model ili besplatan API ključ za "
                "bogatiji razgovor]\n" + last[:280])
