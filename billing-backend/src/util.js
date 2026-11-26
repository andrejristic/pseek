// Small helpers shared by the Worker modules (Web APIs only: runs on Workers and Node 20+).

export const enc = new TextEncoder();

export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });
}

export function error(status, code, message = code, extra = {}) {
  return json({ error: code, message, ...extra }, status);
}

export class HttpError extends Error {
  constructor(status, code, message = code, extra = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.extra = extra;
  }
}

export function nowSec() {
  return Math.floor(Date.now() / 1000);
}

export function b64url(bytes) {
  let s = "";
  const a = new Uint8Array(bytes);
  for (let i = 0; i < a.length; i++) s += String.fromCharCode(a[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function b64decode(b64) {
  const s = atob(b64.replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

export async function sha256hex(text) {
  const d = await crypto.subtle.digest("SHA-256", enc.encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function randomHex(bytes = 32) {
  const a = crypto.getRandomValues(new Uint8Array(bytes));
  return [...a].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function randomCode() {
  // 6 digits, uniform (rejection sampling avoids modulo bias).
  const a = new Uint32Array(1);
  for (;;) {
    crypto.getRandomValues(a);
    if (a[0] < 4294000000) return String(a[0] % 1000000).padStart(6, "0");
  }
}

export function timingSafeEqual(a, b) {
  const x = enc.encode(String(a));
  const y = enc.encode(String(b));
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diff === 0;
}

export function normalizeEmail(e) {
  const s = String(e ?? "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) || s.length > 254) throw new HttpError(400, "bad_email");
  return s;
}

export function requireDeviceId(d) {
  const s = String(d ?? "").trim();
  if (!/^[A-Za-z0-9_-]{16,128}$/.test(s)) throw new HttpError(400, "bad_device_id");
  return s;
}

export async function readJson(request) {
  try {
    return await request.json();
  } catch {
    throw new HttpError(400, "bad_json");
  }
}
