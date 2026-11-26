// Sends sign-in / restore codes through Resend (https://resend.com).
// Secret: RESEND_API_KEY. Var: MAIL_FROM, e.g. "PSEEK <noreply@zeravatech.ca>" (domain verified in Resend).
// DEV_SHOW_CODE=1 (sandbox only) returns the code in the API response instead of failing
// when Resend is not configured yet; it must never be set in production.
import { HttpError } from "./util.js";

export function canShowCode(env) {
  return env.DEV_SHOW_CODE === "1" && env.SQUARE_ENV !== "production";
}

export async function sendCode(env, email, code, lang = "en") {
  if (!env.RESEND_API_KEY) {
    if (canShowCode(env)) return { delivered: false, dev_code: code };
    throw new HttpError(503, "email_not_configured");
  }
  const sr = lang === "sr";
  const subject = sr ? `PSEEK kod: ${code}` : `PSEEK code: ${code}`;
  const text = sr
    ? `Tvoj PSEEK kod je ${code}. Važi 15 minuta.\n\nAko ga nisi tražio, ignoriši ovu poruku.`
    : `Your PSEEK code is ${code}. It is valid for 15 minutes.\n\nIf you did not ask for it, ignore this email.`;
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: env.MAIL_FROM || "PSEEK <noreply@zeravatech.ca>", to: [email], subject, text }),
  });
  if (!res.ok) throw new HttpError(502, "email_failed", `Resend ${res.status}`);
  return { delivered: true };
}
