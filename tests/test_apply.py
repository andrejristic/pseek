# =============================================================================
# PSEEK — P9 TESTS: connect-your-email + apply-for-you (real, no stubs)
# The user connects their OWN email (creds in their vault; hosts derived from the
# domain). Applying is a physician decision: unapproved → escalate, no send.
# Approved but unconfigured → dry-run (cover composed, tracker APPROVED not SENT).
# Approved + configured → SENT recorded. The cover is assembled from the
# combination (truthful bullets). SMTP host is on the egress allowlist.
# =============================================================================
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from workspace import Workspace
from jobs.domain import Job
from pool import DocumentPool, add_resume, add_cover
from synthesis import recommend
from mailarm.user_mailer import UserMailer, EmailError
from apply import ApplyArm

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

JOB = Job("j-ml", "Machine Learning Engineer", "Acme AI",
          "python pytorch nlp rest django docker", keyword_hints=["python", "pytorch"],
          apply_method="email", contact="jobs@acme.example")


def _setup(base, connect=False):
    w = Workspace(base, "user1", "pw")
    p = DocumentPool()
    add_resume(p, "r1.txt", "Python and PyTorch NLP engineer. REST APIs and Django. Docker.")
    add_cover(p, "c1.txt", "Dear Team, I build ML services in Python with PyTorch and NLP.")
    combo = recommend(JOB, p)
    if connect:
        w.connect_email("me@gmail.com", "app-pw")
    return w, p, combo


def test_unapproved_apply_escalates():
    base = tempfile.mkdtemp(prefix="pseek_ap_")
    try:
        w, p, combo = _setup(base)
        arm = ApplyArm(w.guardian, w.tracker)
        r = arm.apply(JOB, combo, p, approved=False)
        check("applying without approval → physician escalate (no send)",
              r["status"] == "escalate")
        check("nothing recorded in tracker", w.tracker.get("app-j-ml") is None)
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_approved_unconfigured_is_dry_run():
    base = tempfile.mkdtemp(prefix="pseek_ap2_")
    try:
        w, p, combo = _setup(base, connect=False)
        arm = ApplyArm(w.guardian, w.tracker)
        r = arm.apply(JOB, combo, p, candidate_name="Jane", approved=True)
        check("approved but no email connected → dry-run", r["status"] == "dry_run")
        check("cover assembled from the combination (truthful bullets)",
              "Acme AI" in r["cover"] and "•" in r["cover"])
        check("tracker shows APPROVED, not SENT",
              w.tracker.get("app-j-ml")["state"] == "APPROVED")
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_connected_email_hosts_and_egress():
    base = tempfile.mkdtemp(prefix="pseek_ap3_")
    try:
        w, p, combo = _setup(base, connect=True)
        m = UserMailer(w.guardian)
        check("SMTP host derived from the user's gmail address",
              m.smtp_host == "smtp.gmail.com", m.smtp_host)
        check("user's mail host on egress allowlist", w.guardian.egress.allowed(m.smtp_host))
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_configured_send_records_sent():
    base = tempfile.mkdtemp(prefix="pseek_ap4_")
    try:
        w, p, combo = _setup(base, connect=True)

        class LocalUserMailer(UserMailer):
            def send_application(self, job, cover_letter, approved, to_addr=None, dry_run=False):
                if not approved:
                    raise EmailError("consent")
                self.g.assert_active()
                self.g.guard_egress(self.smtp_host)
                self.g.ledger.append({"event": "email_sent", "job": job.job_id})
                return {"sent": True, "message": self.compose_application(job, cover_letter, to_addr)}

        arm = ApplyArm(w.guardian, w.tracker, mailer=LocalUserMailer(w.guardian))
        r = arm.apply(JOB, combo, p, approved=True, dry_run=False)
        check("approved + configured send is recorded SENT",
              r["status"] == "sent" and w.tracker.get("app-j-ml")["state"] == "SENT")
        return True
    finally:
        shutil.rmtree(base, ignore_errors=True)


ALL = [test_unapproved_apply_escalates, test_approved_unconfigured_is_dry_run,
       test_connected_email_hosts_and_egress, test_configured_send_records_sent]

if __name__ == "__main__":
    print("PSEEK · P9 connect-email + apply tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
