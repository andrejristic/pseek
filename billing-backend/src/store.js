// KV-backed state. Keys:
//   user:<email>          account: device, session hash, tier, until, trial, subscription, switches
//   session:<sha256>      -> email
//   code:<email>          pending 6-digit code (hash), device, attempts (TTL 15 min)
//   rl:code:<email>       code sends in the last hour
//   checkout:<id>         {email, tier, kind}
//   evt:<event_id>        processed Square webhook events (dedupe)
//   quota:<email>:<day>   LLM calls today
//   config                admin overrides (billing provider, limits)
//   square:plans:<env>    {basic: variationId, pro: variationId} (sandbox | production)

export const DEFAULT_CONFIG = {
  billing_provider: "square", // square | google_play | off
  prices_cents: { basic: 495, pro: 995 },
  currency: "USD",
  trial_hours: 24,
  pass_days: 30,
  offline_hours: 72,
  device_switch_limit: 3, // per 30 days
  llm_daily: { free: 0, trial: 50, basic: 100, pro: 400 },
};

export async function getJson(kv, key) {
  const v = await kv.get(key);
  return v ? JSON.parse(v) : null;
}

export async function putJson(kv, key, value, ttlSec) {
  const opts = ttlSec ? { expirationTtl: Math.max(60, Math.floor(ttlSec)) } : undefined;
  await kv.put(key, JSON.stringify(value), opts);
}

export async function getConfig(env) {
  const stored = (await getJson(env.KV, "config")) ?? {};
  const base = { ...DEFAULT_CONFIG, billing_provider: env.BILLING_PROVIDER_DEFAULT || DEFAULT_CONFIG.billing_provider };
  return {
    ...base,
    ...stored,
    prices_cents: { ...base.prices_cents, ...(stored.prices_cents ?? {}) },
    llm_daily: { ...base.llm_daily, ...(stored.llm_daily ?? {}) },
  };
}

export async function getUser(env, email) {
  return getJson(env.KV, `user:${email}`);
}

export async function putUser(env, user) {
  await putJson(env.KV, `user:${user.email}`, user);
}

export function newUser(email) {
  return {
    email,
    device_id: null,
    session_hash: null,
    tier: null, // basic | pro (paid)
    until: 0, // epoch seconds the paid tier lasts until
    kind: null, // monthly | pass30 | manual
    subscription_id: null,
    trial_until: 0,
    switches: [], // epoch seconds of device changes
    created: Math.floor(Date.now() / 1000),
  };
}

/** trial | basic | pro | free, at time `now` (seconds). */
export function effectiveTier(user, now) {
  if (user && (user.tier === "basic" || user.tier === "pro") && user.until > now) return user.tier;
  if (user && user.trial_until > now) return "trial";
  return "free";
}
