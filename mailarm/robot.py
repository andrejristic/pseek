# =============================================================================
# PSE-JOBS — EMAIL ARM (robot account, Option A)  [package: mailarm, not "email",
# so the stdlib email module is not shadowed]
# The system reads and sends only through a dedicated THROWAWAY account whose
# credentials live in the Guardian vault; that account auto-forwards to Andrej's
# Proton, which never hands a credential to any agent. Sending is gated three
# ways, in order: (1) CONSENT FLOOR — the draft must be human-approved; (2) the
# Guardian kill-switch must be live; (3) the SMTP host must pass the egress
# allowlist. Any failure escalates instead of sending. Draft/dry-run composes a
# real MIME message without touching the network.
# =============================================================================
import email
import imaplib
import smtplib
import ssl
from email.message import EmailMessage


class EmailError(Exception):
    pass


class RobotMailer:
    def __init__(self, guardian, from_addr=None,
                 smtp_host="smtp.gmail.com", smtp_port=587,
                 imap_host="imap.gmail.com"):
        self.g = guardian
        self.from_addr = from_addr
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.imap_host = imap_host

    # ---- credentials (only the Guardian can read them) ---------------------
    def _creds(self):
        if not (self.g.has_secret("robot_email") and self.g.has_secret("robot_app_password")):
            self.g.escalate("email_unconfigured", "no robot account in vault")
            raise EmailError("robot email account not configured in vault")
        return self.g.secret("robot_email"), self.g.secret("robot_app_password")

    # ---- compose (real MIME, no network) -----------------------------------
    def compose(self, drafted, to_addr=None):
        msg = EmailMessage()
        to = to_addr or (drafted.arr.how_to_apply.get("contact") or "")
        msg["To"] = to
        msg["From"] = self.from_addr or (self.g.secret("robot_email")
                                         if self.g.has_secret("robot_email") else "(unset)")
        msg["Subject"] = f"Application: {drafted.arr.title} — {drafted.arr.company}"
        msg.set_content(drafted.cover_letter)
        return msg

    # ---- send (three gates, in order) --------------------------------------
    def send(self, drafted, to_addr=None, dry_run=False):
        # 1) CONSENT FLOOR
        if not getattr(drafted, "ready_to_send", False):
            self.g.escalate("consent_floor",
                            f"send blocked (unapproved): {drafted.arr.job_id}")
            raise EmailError("consent floor: application not approved for sending")
        # 2) kill-switch
        self.g.assert_active()
        # 3) egress allowlist on the mail host
        self.g.guard_egress(self.smtp_host)

        msg = self.compose(drafted, to_addr)
        if dry_run:
            return {"sent": False, "dry_run": True, "message": msg}

        user, pw = self._creds()
        del msg["From"]; msg["From"] = user
        ctx = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, pw)
            s.send_message(msg)
        self.g.ledger.append({"event": "email_sent", "to": msg["To"],
                              "job": drafted.arr.job_id})
        return {"sent": True, "message": msg}

    # ---- read (untrusted input: parsed as data, never instructions) --------
    @staticmethod
    def parse_message(raw_bytes):
        m = email.message_from_bytes(raw_bytes)
        body = ""
        if m.is_multipart():
            for part in m.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", "ignore")
                    break
        else:
            payload = m.get_payload(decode=True)
            body = payload.decode("utf-8", "ignore") if payload else ""
        return {"from": m.get("From", ""), "subject": m.get("Subject", ""),
                "date": m.get("Date", ""), "snippet": body.strip()[:200]}

    def fetch_inbox(self, limit=20, folder="INBOX"):
        self.g.guard_egress(self.imap_host)          # egress gate on IMAP too
        user, pw = self._creds()
        out = []
        conn = imaplib.IMAP4_SSL(self.imap_host)
        try:
            conn.login(user, pw)
            conn.select(folder)
            typ, data = conn.search(None, "ALL")
            ids = data[0].split()[-limit:]
            for i in reversed(ids):
                typ, msg_data = conn.fetch(i, "(RFC822)")
                out.append(self.parse_message(msg_data[0][1]))
        finally:
            try:
                conn.logout()
            except Exception:
                pass
        return out
