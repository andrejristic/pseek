#!/usr/bin/env python3
# =============================================================================
# PSEEK — connect YOUR OWN email to your workspace (CLI path)
# Stores your email address + app password ENCRYPTED in your personal workspace
# vault. PSEEK applies from your own address; nothing is shared with anyone. The
# in-app "Connect email" screen (GUI) does the same thing — this is the command-
# line equivalent. Hosts are auto-derived from your address domain unless given.
#
#   PSEEK_PASSPHRASE=... PSEEK_EMAIL_APP_PASSWORD=... \
#     python3 configure_user_email.py <user-id> <your-email>
#   python3 configure_user_email.py --show <user-id>
# =============================================================================
import getpass
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from workspace import Workspace                                  # noqa: E402

BASE = os.environ.get("PSEEK_WORKSPACES", os.path.join(ROOT, "workspaces"))


def _ws(user_id):
    passphrase = os.environ.get("PSEEK_PASSPHRASE") or getpass.getpass(
        "Workspace passphrase: ")
    return Workspace(BASE, user_id, passphrase)


def main():
    args = sys.argv[1:]
    if "--show" in args:
        user = next((a for a in args if a != "--show"), None) or input("User id: ")
        w = _ws(user)
        print("email connected:", w.email_connected())
        if w.email_connected():
            print("address:", w.guardian.secret("user_email"))
        return
    if len(args) < 2:
        print("usage: python3 configure_user_email.py <user-id> <your-email>")
        sys.exit(1)
    user_id, address = args[0], args[1]
    w = _ws(user_id)
    pw = os.environ.get("PSEEK_EMAIL_APP_PASSWORD") or getpass.getpass(
        "App password (NOT your main password): ")
    imap = (os.environ.get("PSEEK_IMAP_HOST") or "").strip() or None
    smtp = (os.environ.get("PSEEK_SMTP_HOST") or "").strip() or None
    w.connect_email(address, pw, imap_host=imap, smtp_host=smtp)
    print(f"Connected {address} — stored encrypted in your workspace vault.")
    print("PSEEK will apply from your address, only after you approve each send.")


if __name__ == "__main__":
    main()
