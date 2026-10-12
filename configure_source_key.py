#!/usr/bin/env python3
# =============================================================================
# PSEEK — store a USER-DEFINED job-source API key in your workspace vault
# Some sources (LinkedIn/Indeed via a RapidAPI/SerpAPI endpoint, Adzuna, …) need
# an API key. That key is YOURS — it goes encrypted into YOUR workspace vault,
# not the seller's. Reference the key by name in your sources_config.json under
# "user_apis" (key_name) or as adzuna_app_id / adzuna_app_key.
#
#   PSEEK_PASSPHRASE=... python3 configure_source_key.py <user-id> <key_name> <value>
#   python3 configure_source_key.py --show <user-id> <key_name>
# =============================================================================
import getpass
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from workspace import Workspace                                  # noqa: E402

BASE = os.environ.get("PSEEK_WORKSPACES", os.path.join(ROOT, "workspaces"))


def _ws(user):
    p = os.environ.get("PSEEK_PASSPHRASE") or getpass.getpass("Workspace passphrase: ")
    return Workspace(BASE, user, p)


def main():
    args = sys.argv[1:]
    if "--show" in args:
        rest = [a for a in args if a != "--show"]
        w = _ws(rest[0]); name = rest[1]
        print(f"{name} configured:", w.guardian.has_secret(name))
        return
    if len(args) < 3:
        print("usage: python3 configure_source_key.py <user-id> <key_name> <value>")
        sys.exit(1)
    user, name, value = args[0], args[1], args[2]
    w = _ws(user)
    w.guardian.put_secret(name, value)
    print(f"Stored '{name}' encrypted in {user}'s vault. Reference it in "
          f"sources_config.json (user_apis[].key_name).")


if __name__ == "__main__":
    main()
