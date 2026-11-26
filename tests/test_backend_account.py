# =============================================================================
# PSEEK — BACKEND ACCOUNT TESTS (real HTTP against an in-process fake backend)
# The app holds no seller secrets: entitlements come from the backend, signed
# (Ed25519) and verified offline; one device per email (device_replaced logs this
# device out and drops it to Free); buying/cancelling stay physician decisions;
# each build offers only its store's payment provider; the seller's LLM keys are
# reached only through the backend (and never for PII).
# =============================================================================
import base64, json, os, shutil, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from guardian import Guardian
from learning import OrganelleRegistry
from billing import (Account, BackendClient, BackendError, BillingRouter, EntitlementManager,
                     SquareCheckout, verify_token)
from billing import ed25519
from llm import LLMOperator

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

SEED = bytes(range(32))
PUB_B64 = base64.b64encode(ed25519.public_key(SEED)).decode()


def b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class FakeBackend:
    """Just enough of billing-backend/src/worker.js for the client: same routes and shapes."""
    def __init__(self):
        self.users, self.sessions, self.codes, self.calls = {}, {}, {}, []
        self.config = {"billing_provider": "square", "offline_hours": 72}

    def token(self, u):
        now = int(time.time())
        p = {"v": 1, "email": u["email"], "device_id": u["device"], "tier": "x",
             "paid_tier": u.get("tier"), "until": u.get("until", 0), "trial_until": u["trial_until"],
             "iat": now, "exp": now + 72 * 3600}
        body = b64url(json.dumps(p).encode())
        return body + "." + b64url(ed25519.sign(SEED, body.encode())), p

    def handle(self, method, path, body, headers):
        self.calls.append((method, path, body))
        if path == "/config":
            return 200, self.config
        if path == "/auth/start":
            self.codes[body["email"]] = ("123456", body["device_id"])
            return 200, {"sent": True}
        if path == "/auth/verify":
            code, dev = self.codes.get(body["email"], (None, None))
            if body["code"] != code or body["device_id"] != dev:
                return 400, {"error": "code_invalid"}
            u = self.users.setdefault(body["email"], {"email": body["email"], "trial_until": int(time.time()) + 86400})
            switched = "device" in u and u["device"] != dev
            u["device"] = dev
            s = os.urandom(32).hex()
            self.sessions = {k: v for k, v in self.sessions.items() if v != body["email"]}
            self.sessions[s] = body["email"]
            tok, p = self.token(u)
            return 200, {"session": s, "switched": switched, "entitlement": {"token": tok, "tier": "trial", **p}}
        auth = headers.get("Authorization", "")
        email = self.sessions.get(auth.replace("Bearer ", ""))
        if not email or self.users[email]["device"] != headers.get("X-Device-Id"):
            return 409, {"error": "device_replaced"}
        u = self.users[email]
        if path == "/entitlement":
            tok, p = self.token(u)
            return 200, {"token": tok, **p}
        if path == "/checkout":
            return 200, {"checkout_id": "chk-" + os.urandom(4).hex(), "url": "https://square.link/u/x"}
        if path == "/cancel":
            return 200, {"status": "CANCELED", "access_until": u.get("until", 0)}
        if path == "/llm":
            return 200, {"provider": "groq", "text": "cloud says hi"}
        return 404, {"error": "not_found"}


def serve(fake):
    class H(BaseHTTPRequestHandler):
        def _do(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n)) if n else None
            status, data = fake.handle(method, self.path, body, self.headers)
            out = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        def do_GET(self): self._do("GET")
        def do_POST(self): self._do("POST")
        def log_message(self, *a): pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _ctx(d, url, sub="a"):
    g = Guardian(jail_root=os.path.join(d, sub), passphrase="pw")
    reg = OrganelleRegistry(os.path.join(d, sub, "o.json"))
    acc = Account(g, reg, BackendClient(g, url), public_key_b64=PUB_B64)
    return g, reg, acc


def test_signed_entitlement_and_login():
    d = tempfile.mkdtemp(prefix="pseek_acc_")
    fake = FakeBackend(); srv, url = serve(fake)
    try:
        g, reg, acc = _ctx(d, url)
        ent = EntitlementManager(reg, account=acc)
        check("not signed in -> Free (no local trial when a backend is connected)", ent.effective_tier() == "free")
        acc.start_login("Ana@Example.com")
        r = acc.verify_code("123456")
        check("login with the emailed code -> trial from the backend", r["status"] == "ok" and ent.effective_tier() == "trial")
        check("session is in the encrypted vault, not in prefs",
              g.has_secret("pseek_session") and "pseek_session" not in json.dumps(reg.prefs()))
        tok = reg.get_pref("entitlement_token")
        body, sig = tok.split(".")
        forged = b64url(json.dumps({**json.loads(base64.urlsafe_b64decode(body + "==")), "paid_tier": "pro",
                                    "until": 2 ** 40}).encode()) + "." + sig
        reg.set_pref("entitlement_token", forged)
        check("a hand-edited entitlement (fake Pro) is rejected -> Free", ent.effective_tier() == "free")
        check("verify_token raises on the forged token", _raises(lambda: verify_token(forged, PUB_B64)))
        r = acc.refresh()
        check("refresh restores the genuine entitlement", r["status"] == "ok" and ent.effective_tier() == "trial")
        fake.users["ana@example.com"].update(tier="pro", until=int(time.time()) + 30 * 86400)
        acc.refresh()
        check("Square webhook activation shows up as Pro after refresh", ent.effective_tier() == "pro")
        check("can_use follows the signed tier", ent.can_use("combination_engine"))
        return True
    finally:
        srv.shutdown(); shutil.rmtree(d, ignore_errors=True)


def test_one_device_per_email():
    d = tempfile.mkdtemp(prefix="pseek_acc2_")
    fake = FakeBackend(); srv, url = serve(fake)
    try:
        _, regA, accA = _ctx(d, url, "a")
        _, regB, accB = _ctx(d, url, "b")
        accA.start_login("ana@example.com"); accA.verify_code("123456")
        accB.start_login("ana@example.com"); rB = accB.verify_code("123456")
        check("second device signs in and is told it replaced the first", rB["switched"] is True)
        r = accA.refresh()
        check("first device learns it was replaced", r["status"] == "device_replaced")
        check("first device is logged out and drops to Free",
              not accA.logged_in() and EntitlementManager(regA, account=accA).effective_tier() == "free")
        check("second device keeps working", accB.refresh()["status"] == "ok")
        return True
    finally:
        srv.shutdown(); shutil.rmtree(d, ignore_errors=True)


def test_checkout_cancel_physician_and_no_secrets():
    d = tempfile.mkdtemp(prefix="pseek_acc3_")
    fake = FakeBackend(); srv, url = serve(fake)
    try:
        g, reg, acc = _ctx(d, url)
        sq = SquareCheckout(g, account=acc)
        check("not signed in -> test mode, no money moves",
              sq.create_checkout("pro", approved=True)["status"] == "unconfigured")
        acc.start_login("ana@example.com"); acc.verify_code("123456")
        check("buying without approval -> physician escalate", sq.create_checkout("pro")["status"] == "escalate")
        c1 = sq.create_checkout("pro", approved=True, kind="pass30")
        c2 = sq.create_checkout("basic", approved=True, kind="monthly")
        check("approved checkout returns the backend's Square link", c1["status"] == "checkout" and c1["url"].startswith("https://square.link/"))
        check("each checkout is its own (unique id from the backend)", c1["checkout_id"] != c2["checkout_id"])
        sent = [b for m, p, b in fake.calls if p == "/checkout"]
        check("the app sends only tier + kind (no token, no idempotency key, no price)",
              sent[0] == {"tier": "pro", "kind": "pass30"})
        check("cancel without approval -> physician escalate", sq.cancel()["status"] == "escalate")
        check("approved cancel goes through the backend", sq.cancel(approved=True)["status"] == "cancelled")
        check("bad kind is refused", sq.create_checkout("pro", approved=True, kind="weekly")["status"] == "error")
        check("no Square secret anywhere in the vault",
              not any("square" in n for n in g.vault.names()))
        return True
    finally:
        srv.shutdown(); shutil.rmtree(d, ignore_errors=True)


def test_billing_switch_per_build():
    d = tempfile.mkdtemp(prefix="pseek_acc4_")
    fake = FakeBackend(); srv, url = serve(fake)
    try:
        g, reg, acc = _ctx(d, url)
        acc.start_login("ana@example.com"); acc.verify_code("123456")
        check("desktop + square -> square", BillingRouter(g, acc, platform="desktop").active() == "square")
        fake.config["billing_provider"] = "google_play"; acc.billing_config(refresh=True)
        check("Play build + google_play -> google_play", BillingRouter(g, acc, platform="android_play").active() == "google_play")
        check("APK/desktop never offer Google Play (stays Square)",
              BillingRouter(g, acc, platform="android_apk").active() == "square")
        r = BillingRouter(g, acc, platform="android_play").checkout("pro", approved=True)
        check("Play build hands the purchase to Google Play Billing", r["status"] == "google_play")
        fake.config["billing_provider"] = "square"; acc.billing_config(refresh=True)
        check("Play build never offers Square, even if the backend says square",
              BillingRouter(g, acc, platform="android_play").active() == "google_play")
        fake.config["billing_provider"] = "off"; acc.billing_config(refresh=True)
        check("off switches buying off everywhere",
              BillingRouter(g, acc, platform="desktop").checkout("pro", approved=True)["status"] == "billing_off")
        return True
    finally:
        srv.shutdown(); shutil.rmtree(d, ignore_errors=True)


def test_llm_proxy_routing():
    d = tempfile.mkdtemp(prefix="pseek_acc5_")
    fake = FakeBackend(); srv, url = serve(fake)
    try:
        g, reg, acc = _ctx(d, url)
        op = LLMOperator(g, account=acc)
        r0 = op.complete([{"role": "user", "content": "hi"}])
        check("signed out: no seller cloud, heuristic floor", r0["backend"] == "heuristic")
        acc.start_login("ana@example.com"); acc.verify_code("123456")
        r = op.complete([{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}])
        check("signed in: seller's keys via the backend", r["backend"] == "pseek-cloud" and r["text"] == "cloud says hi")
        sent = [b for m, p, b in fake.calls if p == "/llm"][-1]
        check("system prompt sent separately, chat roles only", sent["system"] == "be brief"
              and [m["role"] for m in sent["messages"]] == ["user"])
        r2 = op.complete([{"role": "user", "content": "my email is ana@example.com"}], contains_pii=True)
        check("PII never goes to the seller cloud", r2["backend"] == "heuristic")
        check("operator status reports pseek_cloud", op.status()["pseek_cloud"] is True)
        return True
    finally:
        srv.shutdown(); shutil.rmtree(d, ignore_errors=True)


def _raises(f):
    try:
        f()
    except Exception:
        return True
    return False


ALL = [test_signed_entitlement_and_login, test_one_device_per_email,
       test_checkout_cancel_physician_and_no_secrets, test_billing_switch_per_build,
       test_llm_proxy_routing]

if __name__ == "__main__":
    print("PSEEK · backend account / billing / LLM proxy tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
