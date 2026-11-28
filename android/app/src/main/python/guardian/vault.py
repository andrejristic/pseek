# =============================================================================
# PSE-JOBS GUARDIAN — CREDENTIAL VAULT
# The ONLY place secrets live (robot-email app password, LLM API keys). Agents
# never see raw secrets — they ask the Guardian, which reads from here. Secrets
# are encrypted at rest with a key derived from a master passphrase (scrypt).
#
# Backend: prefers `cryptography` Fernet (AES-128-CBC + HMAC) when installed;
# otherwise a pure-stdlib authenticated cipher (scrypt KDF -> SHA-256 CTR
# keystream + HMAC-SHA256 tag). Both are real AEAD: a wrong passphrase or a
# tampered file fails the MAC and raises — it does not silently return garbage.
# =============================================================================
import base64
import hashlib
import hmac
import json
import os

try:                                   # prefer battle-tested AEAD when present
    from cryptography.fernet import Fernet, InvalidToken
    _HAVE_FERNET = True
except Exception:                      # pragma: no cover - depends on environment
    _HAVE_FERNET = False


class VaultError(Exception):
    pass


# ---- pure-stdlib authenticated cipher (fallback) --------------------------
def _derive(passphrase, salt, dklen=64):
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt,
                          n=2**14, r=8, p=1, dklen=dklen)

def _keystream(enc_key, nonce, n):
    out, counter = bytearray(), 0
    while len(out) < n:
        out += hashlib.sha256(enc_key + nonce + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:n])

def _stdlib_encrypt(passphrase, salt, plaintext):
    key = _derive(passphrase, salt)
    enc_key, mac_key = key[:32], key[32:]
    nonce = os.urandom(16)
    ct = bytes(a ^ b for a, b in zip(plaintext, _keystream(enc_key, nonce, len(plaintext))))
    tag = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
    return {"nonce": base64.b64encode(nonce).decode(),
            "tag": base64.b64encode(tag).decode(),
            "ct": base64.b64encode(ct).decode()}

def _stdlib_decrypt(passphrase, salt, blob):
    key = _derive(passphrase, salt)
    enc_key, mac_key = key[:32], key[32:]
    nonce = base64.b64decode(blob["nonce"])
    ct = base64.b64decode(blob["ct"])
    tag = base64.b64decode(blob["tag"])
    expect = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expect):
        raise VaultError("vault MAC check failed — wrong passphrase or tampered file")
    return bytes(a ^ b for a, b in zip(ct, _keystream(enc_key, nonce, len(ct))))


def _fernet_key(passphrase, salt):
    return base64.urlsafe_b64encode(_derive(passphrase, salt, dklen=32))


class Vault:
    def __init__(self, path, passphrase):
        if not passphrase:
            raise VaultError("vault requires a non-empty master passphrase")
        self.path = path
        self._pass = passphrase
        self.backend = "fernet" if _HAVE_FERNET else "stdlib-scrypt-hmac"
        self._data = {}
        self._salt = None
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if os.path.exists(path):
            self._load()

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as fh:
            envel = json.load(fh)
        self._salt = base64.b64decode(envel["salt"])
        if envel["backend"] == "fernet":
            if not _HAVE_FERNET:
                raise VaultError("vault written with Fernet but cryptography not installed")
            try:
                pt = Fernet(_fernet_key(self._pass, self._salt)).decrypt(
                    envel["blob"].encode())
            except InvalidToken:
                raise VaultError("wrong passphrase or tampered vault")
        else:
            pt = _stdlib_decrypt(self._pass, self._salt, envel["blob"])
        self._data = json.loads(pt.decode("utf-8"))

    def _save(self):
        if self._salt is None:
            self._salt = os.urandom(16)
        pt = json.dumps(self._data).encode("utf-8")
        if _HAVE_FERNET:
            blob = Fernet(_fernet_key(self._pass, self._salt)).encrypt(pt).decode()
            backend = "fernet"
        else:
            blob = _stdlib_encrypt(self._pass, self._salt, pt)
            backend = "stdlib-scrypt-hmac"
        envel = {"backend": backend,
                 "salt": base64.b64encode(self._salt).decode(),
                 "blob": blob}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(envel, fh)
        os.replace(tmp, self.path)     # atomic
        os.chmod(self.path, 0o600)     # owner-only

    # ---- API ---------------------------------------------------------------
    def set(self, name, secret):
        self._data[name] = secret
        self._save()

    def get(self, name):
        if name not in self._data:
            raise VaultError(f"no secret named {name!r} in vault")
        return self._data[name]

    def has(self, name):
        return name in self._data

    def delete(self, name):
        self._data.pop(name, None)
        self._save()

    def names(self):
        return sorted(self._data.keys())
