# =============================================================================
# PSEEK — ACCOUNT (email + this device) against the PSEEK backend
# The backend (billing-backend/, a Cloudflare Worker) holds every seller secret:
# Square token, LLM keys. The app only has: the user's email, a random device id,
# a session (in the encrypted vault) and the latest SIGNED entitlement, which it
# verifies offline with the backend's public key (Ed25519). One active device per
# email: signing in on another device ends this device's session ("device_replaced").
# All traffic goes through the Guardian egress wall.
# =============================================================================
import base64
import json
import secrets
import time
import urllib.error
import urllib.request

from guardian.egress import host_of
from . import ed25519

# Public key of the backend's ENTITLEMENT_SIGNING_KEY (not a secret).
ENTITLEMENT_PUBLIC_KEY = "Nv7nqIs9JIyLLGI0rPa0bhucDcPXNpOzHRfnmnuRiWU="
SESSION_SECRET = "pseek_session"


class BackendError(Exception):
    def __init__(self, status, code, message=""):
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message


def _b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def verify_token(token, public_key_b64=ENTITLEMENT_PUBLIC_KEY):
    """Returns the payload of a backend-signed entitlement, or raises ValueError."""
    try:
        body, sig = token.split(".")
        ok = ed25519.verify(base64.b64decode(public_key_b64), body.encode(), _b64url_decode(sig))
    except Exception as e:
        raise ValueError(f"malformed entitlement: {e}")
    if not ok:
        raise ValueError("entitlement signature invalid")
    return json.loads(_b64url_decode(body))


class BackendClient:
    def __init__(self, guardian, base_url, timeout=30):
        self.g = guardian
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        guardian.egress.add(host_of(self.base))     # the seller's own backend

    def request(self, method, path, body=None, session=None, device_id=None):
        url = self.base + path
        self.g.guard_egress(url)
        headers = {"Accept": "application/json", "User-Agent": "PSEEK"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if session:
            headers["Authorization"] = f"Bearer {session}"
        if device_id:
            headers["X-Device-Id"] = device_id
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read() or b"{}")
            except Exception:
                err = {}
            raise BackendError(e.code, err.get("error", "http_error"), err.get("message", ""))

    def config(self):
        return self.request("GET", "/config")


class Account:
    def __init__(self, guardian, registry, client=None, public_key_b64=ENTITLEMENT_PUBLIC_KEY,
                 now_fn=time.time):
        self.g = guardian
        self.registry = registry
        self.client = client
        self.public_key = public_key_b64
        self.now = now_fn
        self._config = None

    # ---- identity ----------------------------------------------------------
    def configured(self):
        return self.client is not None

    @property
    def device_id(self):
        dev = self.registry.get_pref("device_id")
        if not dev:
            dev = "pseek-" + secrets.token_hex(16)
            self.registry.set_pref("device_id", dev)
        return dev

    @property
    def email(self):
        return self.registry.get_pref("account_email")

    def logged_in(self):
        return self.g.has_secret(SESSION_SECRET)

    def _session(self):
        return self.g.secret(SESSION_SECRET)

    def logout(self, reason="logout"):
        self.g.vault.delete(SESSION_SECRET)
        self.registry.set_pref("entitlement_token", None)
        self.g.ledger.append({"event": "account_logout", "reason": reason})

    # ---- sign-in / restore (6-digit code by email) -------------------------
    def start_login(self, email, lang="sr"):
        email = email.strip().lower()
        self.registry.set_pref("account_email", email)
        return self.client.request("POST", "/auth/start",
                                   {"email": email, "device_id": self.device_id, "lang": lang})

    def verify_code(self, code):
        resp = self.client.request("POST", "/auth/verify", {
            "email": self.email, "device_id": self.device_id, "code": str(code).strip()})
        self.g.put_secret(SESSION_SECRET, resp["session"])
        self._store_token(resp["entitlement"]["token"])
        self.g.ledger.append({"event": "account_login", "switched": bool(resp.get("switched"))})
        return {"status": "ok", "switched": bool(resp.get("switched")),
                "tier": resp["entitlement"]["tier"]}

    # ---- entitlement --------------------------------------------------------
    def _store_token(self, token):
        payload = verify_token(token, self.public_key)          # never store an unverified token
        if payload.get("device_id") != self.device_id:
            raise ValueError("entitlement is for another device")
        self.registry.set_pref("entitlement_token", token)
        return payload

    def entitlement(self):
        """The cached signed entitlement if valid for this device and not expired, else None."""
        token = self.registry.get_pref("entitlement_token")
        if not token:
            return None
        try:
            payload = verify_token(token, self.public_key)
        except ValueError:
            return None
        if payload.get("device_id") != self.device_id or payload.get("exp", 0) < self.now():
            return None
        return payload

    def _call(self, method, path, body=None):
        if not (self.configured() and self.logged_in()):
            raise BackendError(401, "not_logged_in")
        try:
            return self.client.request(method, path, body, session=self._session(), device_id=self.device_id)
        except BackendError as e:
            if e.code in ("device_replaced",) or e.status == 401:
                self.logout(reason=e.code)
            raise

    def refresh(self):
        """Fetch a fresh signed entitlement. Offline keeps the cached one (valid for offline_hours)."""
        try:
            data = self._call("GET", "/entitlement")
        except BackendError as e:
            if e.code == "device_replaced":
                return {"status": "device_replaced"}
            return {"status": "error", "code": e.code}
        except OSError:
            return {"status": "offline", "cached": self.entitlement() is not None}
        payload = self._store_token(data["token"])
        return {"status": "ok", "tier": payload["tier"]}

    # ---- purchases / AI ------------------------------------------------------
    def billing_config(self, refresh=False):
        if self._config is None or refresh:
            try:
                self._config = self.client.config()
            except (BackendError, OSError):
                self._config = None
        return self._config

    def checkout(self, tier, kind="monthly"):
        return self._call("POST", "/checkout", {"tier": tier, "kind": kind})

    def cancel(self):
        return self._call("POST", "/cancel", {})

    def llm(self, messages, system=None, max_tokens=1024, provider=None):
        body = {"messages": messages, "max_tokens": max_tokens}
        if system:
            body["system"] = system
        if provider:
            body["provider"] = provider
        return self._call("POST", "/llm", body)["text"]
