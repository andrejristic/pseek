// LLM proxy: the seller's keys stay here; the app sends messages, gets text back.
// Secrets: GROQ_API_KEY, MISTRAL_API_KEY, ANTHROPIC_API_KEY (any subset).
// Vars: LLM_ORDER (default "groq,mistral,anthropic"), GROQ_MODEL, MISTRAL_MODEL,
//       ANTHROPIC_MODEL (default claude-opus-5-5), ANTHROPIC_EFFORT (default medium).
import { HttpError } from "./util.js";

const MAX_TOKENS_CAP = 4096;

const OPENAI_COMPAT = {
  groq: { url: "https://api.groq.com/openai/v1/chat/completions", key: "GROQ_API_KEY", model: "GROQ_MODEL", dflt: "llama-3.3-70b-versatile" },
  mistral: { url: "https://api.mistral.ai/v1/chat/completions", key: "MISTRAL_API_KEY", model: "MISTRAL_MODEL", dflt: "mistral-small-latest" },
};

export function configuredProviders(env) {
  const order = String(env.LLM_ORDER || "groq,mistral,anthropic").split(",").map((s) => s.trim()).filter(Boolean);
  return order.filter((p) => (p === "anthropic" ? env.ANTHROPIC_API_KEY : env[OPENAI_COMPAT[p]?.key]));
}

function validate(req) {
  const messages = Array.isArray(req.messages) ? req.messages : null;
  if (!messages || messages.length === 0 || messages.length > 50) throw new HttpError(400, "bad_messages");
  for (const m of messages) {
    if (!["user", "assistant"].includes(m.role) || typeof m.content !== "string") throw new HttpError(400, "bad_messages");
  }
  const system = typeof req.system === "string" ? req.system : undefined;
  const maxTokens = Math.min(Math.max(parseInt(req.max_tokens ?? 1024, 10) || 1024, 16), MAX_TOKENS_CAP);
  return { messages, system, maxTokens };
}

async function callOpenAICompat(env, name, { messages, system, maxTokens }) {
  const p = OPENAI_COMPAT[name];
  const res = await fetch(p.url, {
    method: "POST",
    headers: { Authorization: `Bearer ${env[p.key]}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: env[p.model] || p.dflt,
      max_tokens: maxTokens,
      messages: system ? [{ role: "system", content: system }, ...messages] : messages,
    }),
  });
  if (!res.ok) throw new HttpError(res.status === 429 ? 429 : 502, "provider_error", `${name} ${res.status}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content ?? "";
}

async function callAnthropic(env, { messages, system, maxTokens }) {
  const { default: Anthropic } = await import("@anthropic-ai/sdk");
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const response = await client.beta.messages.create({
    model: env.ANTHROPIC_MODEL || "claude-opus-5-5",
    max_tokens: maxTokens,
    betas: ["server-side-fallback-2026-07-01"],
    fallbacks: "default", // a policy decline is retried server-side on a fallback model
    output_config: { effort: env.ANTHROPIC_EFFORT || "medium" },
    ...(system ? { system } : {}),
    messages,
  });
  if (response.stop_reason === "refusal") throw new HttpError(422, "refused", "the model declined this request");
  return response.content.filter((b) => b.type === "text").map((b) => b.text).join("");
}

/** Tries the requested provider first, then the configured order; returns {provider, text}. */
export async function complete(env, req) {
  const input = validate(req);
  let providers = configuredProviders(env);
  if (providers.length === 0) throw new HttpError(503, "llm_not_configured");
  if (req.provider && providers.includes(req.provider)) {
    providers = [req.provider, ...providers.filter((p) => p !== req.provider)];
  }
  let last;
  for (const p of providers) {
    try {
      const text = p === "anthropic" ? await callAnthropic(env, input) : await callOpenAICompat(env, p, input);
      return { provider: p, text };
    } catch (e) {
      last = e;
      if (e.code === "refused" || e.code === "bad_messages") throw e;
    }
  }
  throw last ?? new HttpError(502, "provider_error");
}
