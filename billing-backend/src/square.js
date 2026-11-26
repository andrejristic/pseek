// Square: checkout links (monthly subscription or 30-day pass), signed webhooks that activate
// the buyer's account, cancellation, and one-time creation of the subscription plans.
// Secrets (Cloudflare): SQUARE_ACCESS_TOKEN, SQUARE_LOCATION_ID, SQUARE_WEBHOOK_SIGNATURE_KEY.
// Vars: SQUARE_ENV (sandbox | production), SQUARE_WEBHOOK_URL (exact URL registered in Square).
import { getJson, getUser, newUser, putJson, putUser } from "./store.js";
import { enc, HttpError, nowSec, randomHex, timingSafeEqual } from "./util.js";

// Sandbox and production have different catalogs, so their plan ids are kept apart.
export const plansKey = (env) => `square:plans:${env.SQUARE_ENV === "production" ? "production" : "sandbox"}`;

export const SQUARE_VERSION = "2024-01-18";
const TIERS = ["basic", "pro"];
const KINDS = ["monthly", "pass30"];

function base(env) {
  return env.SQUARE_ENV === "production" ? "https://connect.squareup.com" : "https://connect.squareupsandbox.com";
}

export function squareConfigured(env) {
  return Boolean(env.SQUARE_ACCESS_TOKEN && env.SQUARE_LOCATION_ID);
}

export async function squareApi(env, method, path, body) {
  if (!squareConfigured(env)) throw new HttpError(503, "square_not_configured");
  const res = await fetch(base(env) + path, {
    method,
    headers: {
      Authorization: `Bearer ${env.SQUARE_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
      "Square-Version": SQUARE_VERSION,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data.errors ?? []).map((e) => `${e.code}: ${e.detail ?? ""}`).join("; ");
    throw new HttpError(502, "square_error", `Square ${method} ${path} -> ${res.status} ${detail}`);
  }
  return data;
}

const tierName = (t) => (t === "pro" ? "Pro" : "Basic");

/** Creates a hosted Square checkout for `email`. Every checkout has its own idempotency key. */
export async function createCheckout(env, cfg, email, tier, kind) {
  if (!TIERS.includes(tier)) throw new HttpError(400, "bad_tier");
  if (!KINDS.includes(kind)) throw new HttpError(400, "bad_kind");
  const amount = cfg.prices_cents[tier];
  const money = { amount, currency: cfg.currency };
  const checkoutId = crypto.randomUUID();
  const common = {
    idempotency_key: checkoutId,
    pre_populated_data: { buyer_email: email },
    checkout_options: env.CHECKOUT_REDIRECT_URL ? { redirect_url: env.CHECKOUT_REDIRECT_URL } : {},
  };
  let body;
  if (kind === "pass30") {
    body = {
      ...common,
      order: {
        location_id: env.SQUARE_LOCATION_ID,
        reference_id: checkoutId,
        line_items: [{ name: `PSEEK ${tierName(tier)} (${cfg.pass_days} days)`, quantity: "1", base_price_money: money }],
      },
    };
  } else {
    const plans = await getJson(env.KV, plansKey(env));
    const variation = plans?.[tier];
    if (!variation) throw new HttpError(503, "plans_not_set_up", "run POST /admin/square/setup first");
    body = {
      ...common,
      quick_pay: { name: `PSEEK ${tierName(tier)} (monthly)`, price_money: money, location_id: env.SQUARE_LOCATION_ID },
      checkout_options: { ...common.checkout_options, subscription_plan_id: variation },
    };
  }
  await putJson(env.KV, `checkout:${checkoutId}`, { email, tier, kind, created: nowSec() }, 30 * 86400);
  const data = await squareApi(env, "POST", "/v2/online-checkout/payment-links", body);
  return { checkout_id: checkoutId, url: data.payment_link?.url ?? data.payment_link?.long_url, amount_cents: amount, kind, tier };
}

// ---- webhooks ---------------------------------------------------------------

/** Square signs base64(HMAC-SHA256(signatureKey, notificationUrl + rawBody)). */
export async function verifyWebhook(env, rawBody, signatureHeader) {
  if (!env.SQUARE_WEBHOOK_SIGNATURE_KEY || !env.SQUARE_WEBHOOK_URL) throw new HttpError(503, "webhook_not_configured");
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(env.SQUARE_WEBHOOK_SIGNATURE_KEY), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(env.SQUARE_WEBHOOK_URL + rawBody));
  const expected = btoa(String.fromCharCode(...new Uint8Array(mac)));
  return Boolean(signatureHeader) && timingSafeEqual(expected, signatureHeader);
}

async function extendPass(env, cfg, checkout) {
  const user = (await getUser(env, checkout.email)) ?? newUser(checkout.email);
  const now = nowSec();
  const start = user.tier === checkout.tier && user.until > now ? user.until : now;
  user.tier = checkout.tier;
  user.until = start + cfg.pass_days * 86400;
  if (user.kind !== "monthly") user.kind = "pass30";
  await putUser(env, user);
  return user;
}

function endOfDay(dateStr) {
  // charged_through_date is YYYY-MM-DD; keep access until the end of that day (UTC) + 1 day grace.
  return Math.floor(Date.parse(`${dateStr}T23:59:59Z`) / 1000) + 86400;
}

async function applySubscription(env, sub) {
  const plans = (await getJson(env.KV, plansKey(env))) ?? {};
  const tier = Object.keys(plans).find((t) => plans[t] === sub.plan_variation_id);
  if (!tier) return { ignored: "unknown_plan" };
  const cust = await squareApi(env, "GET", `/v2/customers/${sub.customer_id}`);
  const email = String(cust.customer?.email_address ?? "").trim().toLowerCase();
  if (!email) return { ignored: "customer_without_email" };
  const user = (await getUser(env, email)) ?? newUser(email);
  user.subscription_id = sub.id;
  user.kind = "monthly";
  user.tier = tier;
  if (sub.charged_through_date) user.until = Math.max(user.until, endOfDay(sub.charged_through_date));
  else if (sub.status === "ACTIVE") user.until = Math.max(user.until, nowSec() + 31 * 86400);
  if (sub.status === "CANCELED" || sub.status === "DEACTIVATED") user.subscription_id = null;
  await putUser(env, user);
  return { email, tier, until: user.until, status: sub.status };
}

/** Handles one verified webhook event. Idempotent per event_id. */
export async function handleWebhookEvent(env, cfg, event) {
  const id = event.event_id;
  if (id && (await env.KV.get(`evt:${id}`))) return { duplicate: true };
  let result = { ignored: event.type };
  const obj = event.data?.object ?? {};
  if ((event.type === "payment.updated" || event.type === "payment.created") && obj.payment?.status === "COMPLETED") {
    const orderId = obj.payment.order_id;
    if (orderId) {
      const order = await squareApi(env, "GET", `/v2/orders/${orderId}`);
      const ref = order.order?.reference_id;
      const checkout = ref ? await getJson(env.KV, `checkout:${ref}`) : null;
      if (checkout?.kind === "pass30") {
        const user = await extendPass(env, cfg, checkout);
        result = { email: user.email, tier: user.tier, until: user.until, kind: "pass30" };
      }
    }
  } else if (event.type === "subscription.created" || event.type === "subscription.updated") {
    if (obj.subscription) result = await applySubscription(env, obj.subscription);
  } else if (event.type === "invoice.payment_made") {
    const subId = obj.invoice?.subscription_id;
    if (subId) {
      const sub = await squareApi(env, "GET", `/v2/subscriptions/${subId}`);
      if (sub.subscription) result = await applySubscription(env, sub.subscription);
    }
  }
  if (id) await env.KV.put(`evt:${id}`, "1", { expirationTtl: 14 * 86400 });
  return result;
}

export async function cancelSubscription(env, user) {
  if (!user.subscription_id) throw new HttpError(409, "no_subscription");
  const data = await squareApi(env, "POST", `/v2/subscriptions/${user.subscription_id}/cancel`, {});
  return { status: data.subscription?.status ?? "CANCELED", access_until: user.until };
}

/** One-time: creates the "PSEEK" subscription plan with Basic and Pro monthly variations. */
export async function setupPlans(env, cfg) {
  const existing = await getJson(env.KV, plansKey(env));
  if (existing?.basic && existing?.pro) return { ...existing, created: false };
  const plan = await squareApi(env, "POST", "/v2/catalog/object", {
    idempotency_key: randomHex(16),
    object: { type: "SUBSCRIPTION_PLAN", id: "#pseek-plan", subscription_plan_data: { name: "PSEEK" } },
  });
  const planId = plan.catalog_object.id;
  const out = { plan_id: planId };
  for (const tier of TIERS) {
    const v = await squareApi(env, "POST", "/v2/catalog/object", {
      idempotency_key: randomHex(16),
      object: {
        type: "SUBSCRIPTION_PLAN_VARIATION",
        id: `#pseek-${tier}`,
        subscription_plan_variation_data: {
          name: `PSEEK ${tierName(tier)} monthly`,
          subscription_plan_id: planId,
          phases: [{
            cadence: "MONTHLY",
            ordinal: 0,
            pricing: { type: "STATIC", price_money: { amount: cfg.prices_cents[tier], currency: cfg.currency } },
          }],
        },
      },
    });
    out[tier] = v.catalog_object.id;
  }
  await putJson(env.KV, plansKey(env), out);
  return { ...out, created: true };
}
