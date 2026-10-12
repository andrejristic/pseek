# =============================================================================
# PSEEK — USER MAILER (each user sends from THEIR OWN email)
# Unlike PSE-Jobs (one shared robot account), PSEEK sends from the user's own
# connected address. Credentials live only in that user's vault (user_email /
# user_email_password); the IMAP/SMTP hosts are derived from the address domain
# unless the user overrode them. The three send gates are unchanged, in order:
# CONSENT (approved) → kill-switch → egress allowlist.
# =============================================================================
import smtplib
import ssl
from email.message import EmailMessage

from .robot import RobotMailer, EmailError

PROVIDER_HOSTS = {
    "gmail.com":   ("imap.gmail.com", "smtp.gmail.com"),
    "googlemail.com": ("imap.gmail.com", "smtp.gmail.com"),
    "outlook.com": ("outlook.office365.com", "smtp.office365.com"),
    "hotmail.com": ("outlook.office365.com", "smtp.office365.com"),
    "live.com":    ("outlook.office365.com", "smtp.office365.com"),
    "zoho.com":    ("imap.zoho.com", "smtp.zoho.com"),
}


class UserMailer(RobotMailer):
    def __init__(self, guardian):
        super().__init__(guardian)
        g = guardian
        if g.has_secret("user_email"):
            addr = g.secret("user_email")
            self.from_addr = addr
            dom = addr.split("@")[-1].lower()
            imap, smtp = PROVIDER_HOSTS.get(dom, (None, None))
            self.imap_host = g.secret("user_imap_host") if g.has_secret("user_imap_host") else (imap or self.imap_host)
            self.smtp_host = g.secret("user_smtp_host") if g.has_secret("user_smtp_host") else (smtp or self.smtp_host)

    def _creds(self):
        if not (self.g.has_secret("user_email") and self.g.has_secret("user_email_password")):
            self.g.escalate("email_unconfigured", "no user email connected")
            raise EmailError("connect your email first (Settings → Connect email)")
        return self.g.secret("user_email"), self.g.secret("user_email_password")

    def compose_application(self, job, cover_letter, to_addr=None):
        m = EmailMessage()
        m["To"] = to_addr or (job.contact or "")
        m["From"] = self.from_addr or (self.g.secret("user_email")
                                       if self.g.has_secret("user_email") else "(unset)")
        m["Subject"] = f"Application: {job.title} — {job.company}"
        m.set_content(cover_letter)
        return m

    def send_application(self, job, cover_letter, approved, to_addr=None, dry_run=False):
        # 1) consent floor
        if not approved:
            self.g.escalate("consent_floor", f"send blocked (unapproved): {job.job_id}")
            raise EmailError("consent floor: application not approved")
        # 2) kill-switch, 3) egress
        self.g.assert_active()
        self.g.guard_egress(self.smtp_host)
        msg = self.compose_application(job, cover_letter, to_addr)
        if dry_run:
            return {"sent": False, "dry_run": True, "message": msg}
        user, pw = self._creds()
        del msg["From"]; msg["From"] = user
        ctx = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, pw)
            s.send_message(msg)
        self.g.ledger.append({"event": "email_sent", "to": msg["To"], "job": job.job_id})
        return {"sent": True, "message": msg}
