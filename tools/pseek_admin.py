#!/usr/bin/env python3
# =============================================================================
# PSEEK — seller admin for the backend (billing switch, plans, users)
#
#   export PSEEK_BACKEND_URL=https://pseek-api.<your-subdomain>.workers.dev
#   python3 tools/pseek_admin.py config                      # show live settings
#   python3 tools/pseek_admin.py set-billing square          # square | google_play | off
#   python3 tools/pseek_admin.py set-limit pro 400           # daily AI calls per plan
#   python3 tools/pseek_admin.py setup-square                # once: create Basic/Pro monthly plans
#   python3 tools/pseek_admin.py user ana@example.com        # look up a customer
#   python3 tools/pseek_admin.py grant ana@example.com pro 30   # give 30 days of Pro by hand
#   python3 tools/pseek_admin.py reset-device ana@example.com   # unbind their device
#
# The admin token is read from PSEEK_ADMIN_TOKEN or asked for (never stored).
# Standard library only.
# =============================================================================
import getpass
import json
import os
import sys
import urllib.error
import urllib.request


def call(method, path, body=None):
    base = os.environ.get("PSEEK_BACKEND_URL", "").rstrip("/")
    if not base:
        sys.exit("Set PSEEK_BACKEND_URL first (the Worker URL from the deploy log).")
    token = os.environ.get("PSEEK_ADMIN_TOKEN") or getpass.getpass("ADMIN_TOKEN: ")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "pseek-admin"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")


def main(argv):
    if not argv:
        sys.exit(__doc__ if __doc__ else "see the header of this file")
    cmd, args = argv[0], argv[1:]
    if cmd == "config":
        out = call("GET", "/admin/config")
    elif cmd == "set-billing" and len(args) == 1 and args[0] in ("square", "google_play", "off"):
        out = call("POST", "/admin/config", {"billing_provider": args[0]})
    elif cmd == "set-limit" and len(args) == 2:
        out = call("POST", "/admin/config", {"llm_daily": {args[0]: int(args[1])}})
    elif cmd == "setup-square":
        out = call("POST", "/admin/square/setup")
    elif cmd == "user" and len(args) == 1:
        out = call("GET", f"/admin/user?email={urllib.request.quote(args[0])}")
    elif cmd == "grant" and len(args) == 3:
        out = call("POST", "/admin/user", {"email": args[0], "tier": args[1], "days": float(args[2]), "kind": "manual"})
    elif cmd == "reset-device" and len(args) == 1:
        out = call("POST", "/admin/user", {"email": args[0], "reset_device": True})
    else:
        sys.exit("usage: config | set-billing square|google_play|off | set-limit <tier> <n> | setup-square | "
                 "user <email> | grant <email> <tier> <days> | reset-device <email>")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
