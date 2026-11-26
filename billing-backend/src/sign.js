// Ed25519-signed entitlements. The app holds only the PUBLIC key and verifies offline;
// the private key (PKCS#8, base64) is the Worker secret ENTITLEMENT_SIGNING_KEY.
import { b64decode, b64url, enc, HttpError } from "./util.js";

let cachedKey = null;
let cachedFor = null;

async function signingKey(env) {
  if (!env.ENTITLEMENT_SIGNING_KEY) throw new HttpError(503, "not_configured", "ENTITLEMENT_SIGNING_KEY missing");
  if (cachedKey && cachedFor === env.ENTITLEMENT_SIGNING_KEY) return cachedKey;
  cachedKey = await crypto.subtle.importKey(
    "pkcs8", b64decode(env.ENTITLEMENT_SIGNING_KEY.trim()), { name: "Ed25519" }, false, ["sign"],
  );
  cachedFor = env.ENTITLEMENT_SIGNING_KEY;
  return cachedKey;
}

/** Token format: base64url(JSON payload) + "." + base64url(Ed25519 signature over the first part). */
export async function signEntitlement(env, payload) {
  const body = b64url(enc.encode(JSON.stringify(payload)));
  const sig = await crypto.subtle.sign({ name: "Ed25519" }, await signingKey(env), enc.encode(body));
  return `${body}.${b64url(sig)}`;
}
