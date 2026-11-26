// PSEEK backend (Cloudflare Worker). Holds the seller's secrets so the apps never do.
//
// Public:   GET /health, GET /config, POST /square/webhook
// Account:  POST /auth/start {email, device_id, lang}      -> 6-digit code by email
//           POST /auth/verify {email, device_id, code}     -> session + signed entitlement
//                (one active device per email: verifying on a new device unbinds the old one)
// Session (Authorization: Bearer <session>, X-Device-Id: <id>):
//           GET /entitlement, POST /checkout {tier, kind}, POST /cancel, POST /llm
// Admin (Authorization: Bearer <ADMIN_TOKEN>):
//           GET|POST /admin/config, POST /admin/square/setup, GET /admin/user?email=, POST /admin/user
import { sendCode } from "./email.js";
import { complete } from "./llm.js";
import { signEntitlement } from "./sign.js";
import { cancelSubscription, createCheckout, handleWebhookEvent, setupPlans, squareConfigured, verifyWebhook } from "./square.js";
import { effectiveTier, getConfig, getJson, getUser, newUser, putJson, putUser } from "./store.js";
import {
  error, HttpError, json, normalizeEmail, nowSec, randomCode, randomHex, readJson, requireDeviceId,
  sha256hex, timingSafeEqual,
} from "./util.js";

const CODE_TTL = 15 * 60;
const CODE_MAX_ATTEMPTS = 5;
const CODE_SENDS_PER_HOUR = 5;

async function entitlementFor(env, cfg, user) {
  const now = nowSec();
  const payload = {
    v: 1,
    email: user.email,
    device_id: user.device_id,
    tier: effectiveTier(user, now),
    paid_tier: user.tier,
    until: user.until,
    trial_until: user.trial_until,
    kind: user.kind,
    subscription: Boolean(user.subscription_id),
    billing_provider: cfg.billing_provider,
    iat: now,
    exp: now + cfg.offline_hours * 3600,
  };
  return { token: await signEntitlement(env, payload), ...payload };
}

async function authed(request, env) {
  const m = /^Bearer\s+([a-f0-9]{64})$/i.exec(request.headers.get("authorization") || "");
  if (!m) throw new HttpError(401, "unauthorized");
  const device = requireDeviceId(request.headers.get("x-device-id"));
  const hash = await sha256hex(m[1]);
  const email = await env.KV.get(`session:${hash}`);
  const user = email ? await getUser(env, email) : null;
  if (!user || user.session_hash !== hash) {
    throw new HttpError(409, "device_replaced", "This account was activated on another device.");
  }
  if (user.device_id !== device) throw new HttpError(409, "device_replaced");
  return user;
}

function requireAdmin(request, env) {
  if (!env.ADMIN_TOKEN) throw new HttpError(503, "admin_not_configured");
  const m = /^Bearer\s+(.+)$/.exec(request.headers.get("authorization") || "");
  if (!m || !timingSafeEqual(m[1], env.ADMIN_TOKEN)) throw new HttpError(401, "unauthorized");
}

// ---- account -----------------------------------------------------------------

async function authStart(request, env) {
  const body = await readJson(request);
  const email = normalizeEmail(body.email);
  const device = requireDeviceId(body.device_id);
  const rlKey = `rl:code:${email}`;
  const sent = parseInt((await env.KV.get(rlKey)) || "0", 10);
  if (sent >= CODE_SENDS_PER_HOUR) throw new HttpError(429, "too_many_codes");
  await env.KV.put(rlKey, String(sent + 1), { expirationTtl: 3600 });
  const code = randomCode();
  await putJson(env.KV, `code:${email}`, {
    code_hash: await sha256hex(`${email}:${code}`), device_id: device, attempts: 0, exp: nowSec() + CODE_TTL,
  }, CODE_TTL);
  const delivery = await sendCode(env, email, code, body.lang === "sr" ? "sr" : "en");
  return json({ sent: true, ...delivery });
}

async function authVerify(request, env) {
  const body = await readJson(request);
  const email = normalizeEmail(body.email);
  const device = requireDeviceId(body.device_id);
  const pending = await getJson(env.KV, `code:${email}`);
  const now = nowSec();
  if (!pending || pending.exp < now) throw new HttpError(400, "code_invalid");
  if (pending.attempts >= CODE_MAX_ATTEMPTS) throw new HttpError(429, "too_many_attempts");
  const ok = pending.device_id === device
    && timingSafeEqual(await sha256hex(`${email}:${String(body.code ?? "").trim()}`), pending.code_hash);
  if (!ok) {
    pending.attempts += 1;
    await putJson(env.KV, `code:${email}`, pending, Math.max(60, pending.exp - now));
    throw new HttpError(400, "code_invalid");
  }
  await env.KV.delete(`code:${email}`);

  const cfg = await getConfig(env);
  const user = (await getUser(env, email)) ?? newUser(email);
  let switched = false;
  if (user.device_id && user.device_id !== device) {
    const recent = (user.switches || []).filter((t) => t > now - 30 * 86400);
    if (recent.length >= cfg.device_switch_limit) throw new HttpError(429, "switch_limit", "Too many device changes this month.");
    user.switches = [...recent, now];
    switched = true;
  }
  if (user.session_hash) await env.KV.delete(`session:${user.session_hash}`); // old device / old session out
  const session = randomHex(32);
  user.session_hash = await sha256hex(session);
  user.device_id = device;
  if (!user.trial_until) user.trial_until = now + cfg.trial_hours * 3600; // one trial per email
  await putUser(env, user);
  await env.KV.put(`session:${user.session_hash}`, email);
  return json({ session, switched, entitlement: await entitlementFor(env, cfg, user) });
}

// ---- session routes ------------------------------------------------------------

async function quotaCheck(env, cfg, user) {
  const tier = effectiveTier(user, nowSec());
  const limit = cfg.llm_daily[tier] ?? 0;
  if (limit <= 0) throw new HttpError(402, "upgrade_required");
  const key = `quota:${user.email}:${new Date().toISOString().slice(0, 10)}`;
  const used = parseInt((await env.KV.get(key)) || "0", 10);
  if (used >= limit) throw new HttpError(429, "quota_exceeded", "Daily AI limit reached.", { limit });
  await env.KV.put(key, String(used + 1), { expirationTtl: 2 * 86400 });
  return { tier, used: used + 1, limit };
}

async function route(request, env) {
  const url = new URL(request.url);
  const { pathname } = url;
  const method = request.method;

  if (method === "GET" && pathname === "/health") return json({ ok: true });
  if (method === "GET" && pathname === "/config") {
    const cfg = await getConfig(env);
    return json({
      billing_provider: cfg.billing_provider,
      prices_cents: cfg.prices_cents,
      currency: cfg.currency,
      trial_hours: cfg.trial_hours,
      pass_days: cfg.pass_days,
      offline_hours: cfg.offline_hours,
      device_switch_limit: cfg.device_switch_limit,
      llm_daily: cfg.llm_daily,
      square_ready: squareConfigured(env),
    });
  }
  if (method === "POST" && pathname === "/auth/start") return authStart(request, env);
  if (method === "POST" && pathname === "/auth/verify") return authVerify(request, env);

  if (method === "POST" && pathname === "/square/webhook") {
    const raw = await request.text();
    if (!(await verifyWebhook(env, raw, request.headers.get("x-square-hmacsha256-signature")))) {
      throw new HttpError(401, "bad_signature");
    }
    const result = await handleWebhookEvent(env, await getConfig(env), JSON.parse(raw));
    return json({ ok: true, result });
  }

  if (method === "GET" && pathname === "/entitlement") {
    const user = await authed(request, env);
    return json(await entitlementFor(env, await getConfig(env), user));
  }
  if (method === "POST" && pathname === "/checkout") {
    const user = await authed(request, env);
    const cfg = await getConfig(env);
    if (cfg.billing_provider !== "square") {
      throw new HttpError(409, "provider_disabled", `Square checkout is off (billing_provider=${cfg.billing_provider}).`);
    }
    const body = await readJson(request);
    return json(await createCheckout(env, cfg, user.email, body.tier, body.kind || "monthly"));
  }
  if (method === "POST" && pathname === "/cancel") {
    const user = await authed(request, env);
    return json(await cancelSubscription(env, user));
  }
  if (method === "POST" && pathname === "/llm") {
    const user = await authed(request, env);
    const quota = await quotaCheck(env, await getConfig(env), user);
    const out = await complete(env, await readJson(request));
    return json({ ...out, quota });
  }

  if (pathname.startsWith("/admin/")) {
    requireAdmin(request, env);
    if (pathname === "/admin/config" && method === "GET") return json(await getConfig(env));
    if (pathname === "/admin/config" && method === "POST") {
      const patch = await readJson(request);
      if (patch.billing_provider && !["square", "google_play", "off"].includes(patch.billing_provider)) {
        throw new HttpError(400, "bad_billing_provider");
      }
      const stored = (await getJson(env.KV, "config")) ?? {};
      await putJson(env.KV, "config", { ...stored, ...patch });
      return json(await getConfig(env));
    }
    if (pathname === "/admin/square/setup" && method === "POST") return json(await setupPlans(env, await getConfig(env)));
    if (pathname === "/admin/user" && method === "GET") {
      const user = await getUser(env, normalizeEmail(url.searchParams.get("email")));
      if (!user) throw new HttpError(404, "no_user");
      const { session_hash: _omit, ...safe } = user;
      return json({ ...safe, effective_tier: effectiveTier(user, nowSec()) });
    }
    if (pathname === "/admin/user" && method === "POST") {
      const body = await readJson(request);
      const email = normalizeEmail(body.email);
      const user = (await getUser(env, email)) ?? newUser(email);
      if (body.tier !== undefined) user.tier = body.tier;
      if (body.days !== undefined) user.until = nowSec() + Number(body.days) * 86400;
      if (body.kind !== undefined) user.kind = body.kind;
      if (body.reset_device) {
        if (user.session_hash) await env.KV.delete(`session:${user.session_hash}`);
        user.device_id = null;
        user.session_hash = null;
        user.switches = [];
      }
      await putUser(env, user);
      return json({ email, tier: user.tier, until: user.until, effective_tier: effectiveTier(user, nowSec()) });
    }
  }
  throw new HttpError(404, "not_found");
}

export default {
  async fetch(request, env) {
    try {
      return await route(request, env);
    } catch (e) {
      if (e instanceof HttpError) return error(e.status, e.code, e.message, e.extra);
      console.error(e);
      return error(500, "internal");
    }
  },
};
