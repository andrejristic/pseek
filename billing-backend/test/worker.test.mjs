// Backend tests: node --test test/*.test.mjs   (Node 20+, no packages needed)
// In-memory KV + a fake fetch that plays Square, Groq and Resend.
import assert from "node:assert/strict";
import { beforeEach, describe, test } from "node:test";
import worker from "../src/worker.js";

class MemKV {
  constructor() { this.m = new Map(); }
  async get(k) { return this.m.has(k) ? this.m.get(k) : null; }
  async put(k, v) { this.m.set(k, String(v)); }
  async delete(k) { this.m.delete(k); }
}

const b64 = (buf) => Buffer.from(buf).toString("base64");
const keys = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
const PRIVATE = b64(await crypto.subtle.exportKey("pkcs8", keys.privateKey));

let env;
let calls;
let fakes;

function installFetch() {
  calls = [];
  globalThis.fetch = async (url, init = {}) => {
    const u = String(url);
    const body = init.body ? JSON.parse(init.body) : undefined;
    calls.push({ url: u, method: init.method || "GET", body, headers: init.headers });
    for (const [prefix, handler] of fakes) {
      if (u.startsWith(prefix)) {
        const [status, data] = handler(u, body);
        return new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
      }
    }
    throw new Error(`unexpected fetch ${u}`);
  };
}

beforeEach(() => {
  env = {
    KV: new MemKV(),
    ENTITLEMENT_SIGNING_KEY: PRIVATE,
    DEV_SHOW_CODE: "1",
    SQUARE_ENV: "sandbox",
    SQUARE_ACCESS_TOKEN: "sq-token",
    SQUARE_LOCATION_ID: "LOC1",
    SQUARE_WEBHOOK_SIGNATURE_KEY: "whkey",
    SQUARE_WEBHOOK_URL: "https://api.example.test/square/webhook",
    ADMIN_TOKEN: "admin-secret",
    GROQ_API_KEY: "groq-key",
  };
  fakes = [
    ["https://connect.squareupsandbox.com/v2/online-checkout/payment-links", (u, b) =>
      [200, { payment_link: { url: `https://square.link/u/${b.idempotency_key.slice(0, 8)}` } }]],
    ["https://connect.squareupsandbox.com/v2/orders/", () => [200, { order: { reference_id: fakes.orderRef } }]],
    ["https://connect.squareupsandbox.com/v2/customers/", () => [200, { customer: { email_address: "Ana@Example.com" } }]],
    ["https://connect.squareupsandbox.com/v2/subscriptions/", (u) =>
      [200, { subscription: { id: "SUB1", status: u.endsWith("/cancel") ? "CANCELED" : "ACTIVE" } }]],
    ["https://api.groq.com/", () => [200, { choices: [{ message: { content: "hello from groq" } }] }]],
  ];
  installFetch();
});

async function call(method, path, { body, token, device, admin, headers = {} } = {}) {
  const h = { ...headers };
  if (body !== undefined) h["content-type"] = "application/json";
  if (token) h.authorization = `Bearer ${token}`;
  if (admin) h.authorization = `Bearer ${admin}`;
  if (device) h["x-device-id"] = device;
  const res = await worker.fetch(new Request(`https://api.example.test${path}`, {
    method, headers: h, body: body === undefined ? undefined : (typeof body === "string" ? body : JSON.stringify(body)),
  }), env);
  return { status: res.status, data: await res.json() };
}

const DEV_A = "device-aaaaaaaaaaaaaaaa";
const DEV_B = "device-bbbbbbbbbbbbbbbb";

async function login(email, device) {
  const s = await call("POST", "/auth/start", { body: { email, device_id: device } });
  assert.equal(s.status, 200);
  const v = await call("POST", "/auth/verify", { body: { email, device_id: device, code: s.data.dev_code } });
  assert.equal(v.status, 200, JSON.stringify(v.data));
  return v.data;
}

async function verifyToken(token) {
  const [body, sig] = token.split(".");
  const fromB64url = (s) => Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64");
  const ok = await crypto.subtle.verify({ name: "Ed25519" }, keys.publicKey, fromB64url(sig), new TextEncoder().encode(body));
  return { ok, payload: JSON.parse(fromB64url(body).toString()) };
}

async function squareSigned(event) {
  const raw = JSON.stringify(event);
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode("whkey"), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(env.SQUARE_WEBHOOK_URL + raw));
  return call("POST", "/square/webhook", { body: raw, headers: { "x-square-hmacsha256-signature": b64(mac) } });
}

describe("account + one device per email", () => {
  test("login starts the 24h trial once and returns a valid Ed25519-signed entitlement", async () => {
    const r = await login("ana@example.com", DEV_A);
    assert.equal(r.entitlement.tier, "trial");
    const { ok, payload } = await verifyToken(r.entitlement.token);
    assert.ok(ok, "signature verifies with the public key");
    assert.equal(payload.device_id, DEV_A);
    assert.ok(payload.exp - payload.iat === 72 * 3600, "72h offline validity");
    const trialUntil = payload.trial_until;
    const again = await login("ana@example.com", DEV_A);
    assert.equal(again.entitlement.trial_until, trialUntil, "trial is not restarted by logging in again");
  });

  test("wrong code is rejected and attempts are limited", async () => {
    await call("POST", "/auth/start", { body: { email: "b@example.com", device_id: DEV_A } });
    for (let i = 0; i < 5; i++) {
      const v = await call("POST", "/auth/verify", { body: { email: "b@example.com", device_id: DEV_A, code: "000000x" } });
      assert.equal(v.status, 400);
    }
    const v = await call("POST", "/auth/verify", { body: { email: "b@example.com", device_id: DEV_A, code: "123456" } });
    assert.equal(v.status, 429);
  });

  test("activating on a new device unbinds the old one; switches are limited per month", async () => {
    const a = await login("ana@example.com", DEV_A);
    assert.equal((await call("GET", "/entitlement", { token: a.session, device: DEV_A })).status, 200);
    const b = await login("ana@example.com", DEV_B);
    assert.equal(b.switched, true);
    const old = await call("GET", "/entitlement", { token: a.session, device: DEV_A });
    assert.equal(old.status, 409);
    assert.equal(old.data.error, "device_replaced");
    assert.equal((await call("GET", "/entitlement", { token: b.session, device: DEV_B })).status, 200);
    await login("ana@example.com", DEV_A); // switch 2
    await login("ana@example.com", DEV_B); // switch 3
    const s = await call("POST", "/auth/start", { body: { email: "ana@example.com", device_id: DEV_A } });
    const v = await call("POST", "/auth/verify", { body: { email: "ana@example.com", device_id: DEV_A, code: s.data.dev_code } });
    assert.equal(v.status, 429);
    assert.equal(v.data.error, "switch_limit");
  });

  test("a session cannot be used from another device id", async () => {
    const a = await login("ana@example.com", DEV_A);
    assert.equal((await call("GET", "/entitlement", { token: a.session, device: DEV_B })).status, 409);
  });
});

describe("Square checkout + webhooks", () => {
  test("every checkout gets its own idempotency key and the buyer email", async () => {
    const a = await login("ana@example.com", DEV_A);
    const c1 = await call("POST", "/checkout", { token: a.session, device: DEV_A, body: { tier: "pro", kind: "pass30" } });
    const c2 = await call("POST", "/checkout", { token: a.session, device: DEV_A, body: { tier: "pro", kind: "pass30" } });
    assert.equal(c1.status, 200);
    const sq = calls.filter((c) => c.url.includes("payment-links"));
    assert.equal(sq.length, 2);
    assert.notEqual(sq[0].body.idempotency_key, sq[1].body.idempotency_key);
    assert.equal(sq[0].body.pre_populated_data.buyer_email, "ana@example.com");
    assert.equal(sq[0].body.order.line_items[0].base_price_money.amount, 995);
    assert.equal(sq[0].headers.Authorization, "Bearer sq-token");
    assert.ok(c1.data.url.startsWith("https://square.link/"));
    assert.notEqual(c1.data.checkout_id, c2.data.checkout_id);
  });

  test("monthly checkout needs the plans set up, then uses the plan variation", async () => {
    const a = await login("ana@example.com", DEV_A);
    const r = await call("POST", "/checkout", { token: a.session, device: DEV_A, body: { tier: "basic", kind: "monthly" } });
    assert.equal(r.status, 503);
    assert.equal(r.data.error, "plans_not_set_up");
    await env.KV.put("square:plans:sandbox", JSON.stringify({ basic: "VAR_B", pro: "VAR_P" }));
    const ok = await call("POST", "/checkout", { token: a.session, device: DEV_A, body: { tier: "basic", kind: "monthly" } });
    assert.equal(ok.status, 200);
    const last = calls.filter((c) => c.url.includes("payment-links")).at(-1);
    assert.equal(last.body.checkout_options.subscription_plan_id, "VAR_B");
    assert.equal(last.body.quick_pay.price_money.amount, 495);
  });

  test("bad webhook signature is rejected", async () => {
    const r = await call("POST", "/square/webhook", { body: "{}", headers: { "x-square-hmacsha256-signature": "nope" } });
    assert.equal(r.status, 401);
  });

  test("completed 30-day payment activates Pro for the buyer; duplicate events are ignored", async () => {
    const a = await login("ana@example.com", DEV_A);
    const c = await call("POST", "/checkout", { token: a.session, device: DEV_A, body: { tier: "pro", kind: "pass30" } });
    fakes.orderRef = c.data.checkout_id;
    const evt = { event_id: "E1", type: "payment.updated", data: { object: { payment: { status: "COMPLETED", order_id: "O1" } } } };
    const w = await squareSigned(evt);
    assert.equal(w.status, 200);
    assert.equal(w.data.result.tier, "pro");
    const e = await call("GET", "/entitlement", { token: a.session, device: DEV_A });
    assert.equal(e.data.tier, "pro");
    const days = (e.data.until - Math.floor(Date.now() / 1000)) / 86400;
    assert.ok(days > 29.9 && days <= 30, `about 30 days, got ${days}`);
    const dup = await squareSigned(evt);
    assert.equal(dup.data.result.duplicate, true);
  });

  test("subscription.created activates the plan's tier for the customer's email; cancel works", async () => {
    const a = await login("ana@example.com", DEV_A);
    await env.KV.put("square:plans:sandbox", JSON.stringify({ basic: "VAR_B", pro: "VAR_P" }));
    const w = await squareSigned({
      event_id: "E2", type: "subscription.created",
      data: { object: { subscription: { id: "SUB1", customer_id: "C1", plan_variation_id: "VAR_B", status: "ACTIVE", charged_through_date: "2099-01-31" } } },
    });
    assert.equal(w.data.result.email, "ana@example.com");
    const e = await call("GET", "/entitlement", { token: a.session, device: DEV_A });
    assert.equal(e.data.tier, "basic");
    assert.equal(e.data.subscription, true);
    const cancel = await call("POST", "/cancel", { token: a.session, device: DEV_A });
    assert.equal(cancel.status, 200);
    assert.equal(cancel.data.status, "CANCELED");
  });
});

describe("billing switch + admin", () => {
  test("admin can switch the billing provider; checkout respects it", async () => {
    const a = await login("ana@example.com", DEV_A);
    assert.equal((await call("POST", "/admin/config", { body: { billing_provider: "off" } })).status, 401);
    const set = await call("POST", "/admin/config", { admin: "admin-secret", body: { billing_provider: "google_play" } });
    assert.equal(set.data.billing_provider, "google_play");
    assert.equal((await call("GET", "/config")).data.billing_provider, "google_play");
    const r = await call("POST", "/checkout", { token: a.session, device: DEV_A, body: { tier: "pro", kind: "pass30" } });
    assert.equal(r.status, 409);
    assert.equal(r.data.error, "provider_disabled");
    assert.equal((await call("POST", "/admin/config", { admin: "admin-secret", body: { billing_provider: "bogus" } })).status, 400);
  });

  test("admin can grant days and reset the device binding", async () => {
    const a = await login("ana@example.com", DEV_A);
    const g = await call("POST", "/admin/user", { admin: "admin-secret", body: { email: "ana@example.com", tier: "pro", days: 10, reset_device: true } });
    assert.equal(g.data.effective_tier, "pro");
    assert.equal((await call("GET", "/entitlement", { token: a.session, device: DEV_A })).status, 409);
  });
});

describe("LLM proxy", () => {
  test("uses the seller's key server-side, counts the daily quota per tier", async () => {
    const a = await login("ana@example.com", DEV_A);
    await call("POST", "/admin/config", { admin: "admin-secret", body: { llm_daily: { trial: 2 } } });
    const msg = { messages: [{ role: "user", content: "hi" }] };
    const r1 = await call("POST", "/llm", { token: a.session, device: DEV_A, body: msg });
    assert.equal(r1.status, 200);
    assert.equal(r1.data.text, "hello from groq");
    const groq = calls.find((c) => c.url.startsWith("https://api.groq.com/"));
    assert.equal(groq.headers.Authorization, "Bearer groq-key");
    assert.equal((await call("POST", "/llm", { token: a.session, device: DEV_A, body: msg })).status, 200);
    const r3 = await call("POST", "/llm", { token: a.session, device: DEV_A, body: msg });
    assert.equal(r3.status, 429);
    assert.equal(r3.data.error, "quota_exceeded");
  });

  test("free tier (trial over, nothing bought) must upgrade", async () => {
    const a = await login("ana@example.com", DEV_A);
    const u = JSON.parse(await env.KV.get("user:ana@example.com"));
    u.trial_until = 1;
    await env.KV.put("user:ana@example.com", JSON.stringify(u));
    const r = await call("POST", "/llm", { token: a.session, device: DEV_A, body: { messages: [{ role: "user", content: "hi" }] } });
    assert.equal(r.status, 402);
  });

  test("rejects malformed messages", async () => {
    const a = await login("ana@example.com", DEV_A);
    const r = await call("POST", "/llm", { token: a.session, device: DEV_A, body: { messages: [{ role: "system", content: "x" }] } });
    assert.equal(r.status, 400);
  });
});
