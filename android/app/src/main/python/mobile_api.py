# -*- coding: utf-8 -*-
"""PSEEK Android bridge.

Kotlin (Chaquopy) calls the functions below and gets a JSON string back.
The desktop PySide6 GUI is NOT used here: this is the headless core plus a
small, explicit API for the Compose interface.

Design rules kept from the desktop app:
  * no decision is ever taken without the human (Physician gate);
  * no seller secret lives in the app (Square token / seller LLM keys stay
    on the Cloudflare backend, entered by Andrej in the Cloudflare dashboard);
  * without a backend the app runs in local test mode: the 24h trial works,
    no money moves, and the heuristic LLM floor keeps it usable offline.
"""
from __future__ import annotations

import json
import os
import shutil
import time
import traceback
import urllib.error
import urllib.request

VERSION = "0.1.0-apk"

_BASE = None
_WS = None
_OP = None
_ENT = None
_DISC = None
_POOL = None
_CHAT = None
_RECORDS = []
_PENDING = {}
_BACKEND_URL = ""


# ---------------------------------------------------------------- helpers
def _json(obj):
    return json.dumps(obj, ensure_ascii=False, default=str)


def _ok(**kw):
    return _json(dict(ok=True, **kw))


def _fail(exc):
    return _json({"ok": False, "error": str(exc), "trace": traceback.format_exc()[-800:]})


def _path(*parts):
    return os.path.join(_BASE, *parts)


def _ensure():
    global _BASE, _WS, _OP, _ENT, _DISC, _POOL, _CHAT
    if _WS is not None:
        return
    from workspace import Workspace
    from billing import EntitlementManager
    from llm import LLMOperator

    _BASE = _BASE or _path_default()
    _WS = Workspace(_BASE, "phone", _passphrase_default())
    _ENT = EntitlementManager(_WS.registry, account=None)
    _OP = LLMOperator(_WS.guardian, account=None)
    _reload_pool()
    _reload_backend()


def _path_default():
    # Kotlin always calls init() first; this is a safe fallback for tests.
    return os.environ.get("PSEEK_HOME", os.path.join(os.getcwd(), "pseek-workspace"))


def _passphrase_default():
    return os.environ.get("PSEEK_PASSPHRASE", "pseek-apk-local")


def _reload_pool():
    global _POOL, _DISC, _CHAT
    from pool import load_pool
    from discovery import Discovery

    _POOL = load_pool(_WS.docs_dir, guardian=None)
    _DISC = Discovery(_WS, _config())
    _CHAT = None


def _config():
    p = _path("sources_config.json")
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}


def _reload_backend():
    """Build (or drop) the billing/LLM backend client from the saved URL."""
    global _ENT, _OP, _BACKEND_URL, _CHAT
    from billing import EntitlementManager
    from billing.account import Account, BackendClient
    from llm import LLMOperator

    url = (_BACKEND_URL or "").strip()
    account = Account(_WS.guardian, _WS.registry, BackendClient(_WS.guardian, url)) if url else None
    _ENT = EntitlementManager(_WS.registry, account=account)
    _OP = LLMOperator(_WS.guardian, account=account)
    # Keep a local GGUF backend if one was selected in this session.
    if _LOCAL[0]:
        _OP.local = AndroidLlamaBackend(_WS.guardian, _LOCAL[0])
    _CHAT = None


# ---------------------------------------------------------------- phase L
class AndroidLlamaBackend:
    """llama.cpp llama-server running as an on-device executable at 127.0.0.1:8765.

    Kotlin starts/stops the server (nativeLibraryDir/libllama_server.so); Python
    only speaks OpenAI-compatible HTTP to it, so no native Python module is
    needed and nothing leaves the phone.
    """

    name = "local-gguf"
    is_local = True

    def __init__(self, guardian, model_path=None):
        self.g = guardian
        self.model_path = model_path
        self.calls = 0

    def available(self):
        return bool(self.model_path) and _server_alive()

    def complete(self, messages, max_tokens=512):
        body = json.dumps({"model": "local", "messages": messages,
                           "max_tokens": max_tokens}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8765/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        self.calls += 1
        return data["choices"][0]["message"]["content"]


_LOCAL = [None]


def _server_alive():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------- lifecycle
def init(base_dir, passphrase, backend_url=""):
    """args: [filesDir path] [random passphrase from Android Keystore] [backend URL]"""
    global _BASE, _BACKEND_URL
    try:
        _BASE = os.path.abspath(base_dir)
        os.makedirs(_BASE, exist_ok=True)
        os.environ["PSEEK_HOME"] = _BASE
        os.environ["PSEEK_PASSPHRASE"] = passphrase
        _BACKEND_URL = (backend_url or "").strip()
        _WS = None
        _ensure()
        if _BACKEND_URL:
            _WS.registry.set_pref("backend_url", _BACKEND_URL)
        return status()
    except Exception as e:
        return _fail(e)


def status():
    try:
        _ensure()
        cfg = _backend_config()
        tier = _ENT.effective_tier() if _ENT else "free"
        return _ok(
            version=VERSION, tier=tier, backend=_BACKEND_URL or None,
            backend_ok=bool(cfg), billing=((cfg or {}).get("billing_provider", "off")),
            email=_WS.email_connected(),
            documents=_POOL.summary(),
            jobs=len(_RECORDS),
            applications=len(_WS.tracker.all()),
            theta=_theta(), llm=_OP.status(),
        )
    except Exception as e:
        return _fail(e)


def _theta():
    try:
        from theta import theta_from_state
        c = _WS.registry.get_pref("care_invariant", {"w_s": 0.4, "w_o": 0.3, "w_f": 0.3})
        return round(theta_from_state(c), 2)
    except Exception:
        return 30.0


def _backend_config():
    if not _BACKEND_URL:
        return None
    try:
        req = urllib.request.Request(_BACKEND_URL.rstrip("/") + "/config")
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return None


def set_backend(url):
    global _BACKEND_URL
    try:
        _ensure()
        _BACKEND_URL = (url or "").strip()
        _WS.registry.set_pref("backend_url", _BACKEND_URL)
        _reload_backend()
        return _ok(backend=_BACKEND_URL or None, backend_ok=bool(_backend_config()))
    except Exception as e:
        return _fail(e)


def test_backend():
    try:
        _ensure()
        cfg = _backend_config()
        return _ok(connected=bool(cfg), config=cfg)
    except Exception as e:
        return _fail(e)


# ---------------------------------------------------------------- documents
def documents():
    try:
        _ensure()
        names = sorted(os.listdir(_WS.docs_dir)) if os.path.isdir(_WS.docs_dir) else []
        return _ok(files=names, summary=_POOL.summary())
    except Exception as e:
        return _fail(e)


def add_document(path, name=""):
    """Import a document selected with the Android file picker."""
    try:
        _ensure()
        base = os.path.basename(path or "document.txt")
        name = (name or base).strip() or base
        safe = "".join(c for c in name if c.isalnum() or c in " ._-")[:120] or "document.txt"
        dst = os.path.join(_WS.docs_dir, safe)
        if os.path.abspath(path) != os.path.abspath(dst):
            shutil.copyfile(path, dst)
        _reload_pool()
        return _ok(name=safe, summary=_POOL.summary())
    except Exception as e:
        return _fail(e)


# ---------------------------------------------------------------- jobs
def _record_view(r, i):
    job = getattr(r, "job", None)
    fit = 0.0
    try:
        fit = max((r.fit_by_profile or {}).values() or [0.0])
    except Exception:
        pass
    return {
        "index": i,
        "job_id": getattr(r, "job_id", ""),
        "title": getattr(r, "title", "") or getattr(job, "title", ""),
        "company": getattr(r, "company", "") or getattr(job, "company", ""),
        "location": getattr(job, "location", ""),
        "fit": round(float(fit), 3),
        "verdict": getattr(r, "verdict_code", ""),
        "source": getattr(job, "source_url", "") or getattr(r, "source_url", ""),
        "description": (getattr(job, "description", "") or "")[:600],
        "bullets": [getattr(b, "text", str(b)) for b in (getattr(r, "bullets", None) or [])][:6],
    }


def search(location="toronto_remote", limit=30):
    """Fan out across job sources; results are kept on the device."""
    try:
        _ensure()
        global _RECORDS
        recs = _DISC.search(_POOL, location_focus=location, min_fit=0.1, limit=limit)
        _RECORDS = list(recs)
        out = [_record_view(r, i) for i, r in enumerate(_RECORDS)]
        with open(_path("data", "jobs.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        return _ok(jobs=out, count=len(out), sources=_DISC.best_sources(3))
    except Exception as e:
        return _fail(e)


def jobs():
    try:
        _ensure()
        p = _path("data", "jobs.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                return _ok(jobs=json.load(fh))
        return _ok(jobs=[_record_view(r, i) for i, r in enumerate(_RECORDS)])
    except Exception as e:
        return _fail(e)


def job(index):
    try:
        _ensure()
        i = int(index)
        if not (0 <= i < len(_RECORDS)):
            return _json({"ok": False, "error": "no such job"})
        return _ok(job=_record_view(_RECORDS[i], i))
    except Exception as e:
        return _fail(e)


# ---------------------------------------------------------------- proposals
def prepare(index):
    """Combinatorial synthesis: propose an honest pitch. Nothing is sent."""
    try:
        _ensure()
        i = int(index)
        if not (0 <= i < len(_RECORDS)):
            return _json({"ok": False, "error": "no such job"})
        from synthesis import recommend

        rec = _RECORDS[i]
        job_obj = getattr(rec, "job", None) or _job_from_record(rec)
        combo = recommend(job_obj, _POOL)
        if combo is None:
            return _json({"ok": False, "error": "no combination from the document pool"})
        pid = "prop-%d-%d" % (i, int(time.time()))
        _PENDING[pid] = {"index": i, "job": job_obj, "combo": combo}
        return _ok(
            id=pid, index=i, title=getattr(rec, "title", ""), company=getattr(rec, "company", ""),
            lines=[getattr(x, "text", str(x)) for x in combo.claims],
            cover_para_ids=list(combo.cover_para_ids), theta=round(float(combo.theta), 2),
            theta_in_band=bool(combo.theta_in_band), verdict=combo.verdict_code,
            note="Predlog je sastavljen samo iz tvojih dokumenata. Slanje ide tek posle tvog odobrenja.",
        )
    except Exception as e:
        return _fail(e)


def _job_from_record(rec):
    from jobs.domain import Job

    return Job(job_id=getattr(rec, "job_id", ""), title=getattr(rec, "title", ""),
               company=getattr(rec, "company", ""),
               source_url=getattr(rec, "source_url", ""),
               description=" ".join(b.text for b in (getattr(rec, "bullets", None) or [])))


def apply_proposal(pid, approved, candidate_name="Candidate"):
    """PHYSICIAN GATE: approved must be True from an explicit UI action."""
    try:
        _ensure()
        prop = _PENDING.get(pid)
        if not prop:
            return _json({"ok": False, "error": "unknown proposal"})
        from apply.apply import ApplyArm, build_cover

        arm = ApplyArm(_WS.guardian, _WS.tracker)
        result = arm.apply(prop["job"], prop["combo"], _POOL,
                           candidate_name=candidate_name, approved=bool(approved))
        if result.get("status") == "applied" or result.get("status") == "sent":
            _DISC.record_feedback(_RECORDS[prop["index"]], "apply")
        return _ok(result=result, approved=bool(approved))
    except Exception as e:
        return _fail(e)


def applications():
    try:
        _ensure()
        return _ok(applications=_WS.tracker.all())
    except Exception as e:
        return _fail(e)


# ---------------------------------------------------------------- chat
def chat(text):
    try:
        _ensure()
        global _CHAT
        if _CHAT is None:
            from chat.pseek_chat import PseekChat

            def on_results(recs):
                global _RECORDS
                _RECORDS = list(recs)

            _CHAT = PseekChat(_WS, _DISC, lambda: _POOL, operator=_OP, on_results=on_results)
        answer = _CHAT.handle(text)
        return _ok(text=answer, jobs=len(_RECORDS))
    except Exception as e:
        return _fail(e)


# ---------------------------------------------------------------- account
def connect_email(address, app_password, imap="", smtp=""):
    try:
        _ensure()
        _WS.connect_email(address, app_password, imap or None, smtp or None)
        return _ok(email=True)
    except Exception as e:
        return _fail(e)


def set_llm_key(provider, key):
    """User's OWN key, kept in the encrypted vault; seller keys never enter the app."""
    try:
        _ensure()
        names = {"groq": "groq_api_key", "mistral": "mistral_api_key",
                 "anthropic": "anthropic_api_key"}
        name = names.get(provider, provider)
        # The vault has no delete method; an empty value means "not configured".
        _WS.guardian.put_secret(name, key or "")
        _reload_backend()
        return _ok(provider=provider, stored=bool(key))
    except Exception as e:
        return _fail(e)


def use_local_model(path):
    """Kotlin has started llama-server for this GGUF; route PII work to it."""
    try:
        _ensure()
        if not _server_alive():
            return _json({"ok": False, "error": "llama-server nije pokrenut (127.0.0.1:8765)"})
        _LOCAL[0] = path
        _OP.local = AndroidLlamaBackend(_WS.guardian, path)
        return _ok(model=path, llm=_OP.status())
    except Exception as e:
        return _fail(e)


def stop_local_model():
    _LOCAL[0] = None
    try:
        _ensure()
        from llm.backends import LlamaCppBackend
        _OP.local = LlamaCppBackend(_WS.guardian)
    except Exception:
        pass
    return _ok(model=None)


# ---------------------------------------------------------------- billing
def checkout(tier="basic", kind="monthly", approved=False):
    """PHYSICIAN GATE for a purchase. Without backend: test mode, no money moves."""
    try:
        _ensure()
        from billing.providers import BillingRouter

        router = BillingRouter(_WS.guardian,
                               account=_ENT.account if hasattr(_ENT, "account") else None,
                               platform="android_apk")
        return _ok(result=router.checkout(tier, kind=kind, approved=bool(approved)))
    except Exception as e:
        return _fail(e)


def restore_start(email):
    """Send a six-digit code to the buyer's email (requires a connected backend)."""
    try:
        _ensure()
        acc = _account()
        if acc is None:
            return _json({"ok": False, "error": "Backend nije povezan"})
        return _ok(result=acc.start_login(email))
    except Exception as e:
        return _fail(e)


def restore_verify(code):
    """Bind the subscription to this device; the old device drops its entitlement."""
    try:
        _ensure()
        acc = _account()
        if acc is None:
            return _json({"ok": False, "error": "Backend nije povezan"})
        result = acc.verify_code(code)
        _reload_backend()
        return _ok(result=result)
    except Exception as e:
        return _fail(e)


def _account():
    from billing.account import Account, BackendClient

    if not _BACKEND_URL:
        return None
    return Account(_WS.guardian, _WS.registry, BackendClient(_WS.guardian, _BACKEND_URL))


def cancel_subscription(approved=False):
    try:
        _ensure()
        from billing.providers import BillingRouter

        router = BillingRouter(_WS.guardian,
                               account=_ENT.account if hasattr(_ENT, "account") else None,
                               platform="android_apk")
        return _ok(result=router.cancel(approved=bool(approved)))
    except Exception as e:
        return _fail(e)
