# =============================================================================
# PSE-JOBS — HARVEST / DISCOVERY ARM
# The machine finds jobs itself and packages each into an Application-Ready
# Record. Every network fetch goes THROUGH the Guardian's egress allowlist —
# a source can only be reached if its host is approved. Live fetching uses
# urllib; source adapters parse structured feeds (RemoteOK's public JSON here)
# into Jobs. The ARR builder then auto-drafts a TRUTHFUL application (bullets
# drawn only from résumé lines) and runs the kernel to attach a verdict.
# =============================================================================
import html
import json
import re
import urllib.request

from pse_kernel import NullAudit
from jobs.domain import Job, Claim, Application, tokens
from jobs.records import (ApplicationReadyRecord, AutofillField, Bullet,
                          parse_candidate)
from jobs.evaluate import triage
from jobs.geo import location_ok, location_label


def _strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


# ---- fetcher: every request passes the Guardian egress wall ----------------
class Fetcher:
    def __init__(self, guardian, user_agent="PSE-Jobs/1.0 (job-search)"):
        self.guardian = guardian
        self.ua = user_agent

    def get(self, url, timeout=20):
        self.guardian.guard_egress(url)      # refuses non-allowlisted hosts first
        req = urllib.request.Request(url, headers={"User-Agent": self.ua})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()


# ---- source adapters -------------------------------------------------------
def parse_remoteok(json_bytes):
    """RemoteOK public feed: a JSON list whose first element is a legal notice,
    the rest are jobs. https://remoteok.com/api"""
    data = json.loads(json_bytes)
    jobs = []
    for it in data:
        if not isinstance(it, dict) or "position" not in it or "id" not in it:
            continue                         # skip the legal/meta header element
        jobs.append(Job(
            job_id=f"remoteok:{it['id']}",
            title=it.get("position", ""),
            company=it.get("company", ""),
            description=_strip_html(it.get("description", "")),
            keyword_hints=[t for t in it.get("tags", []) if t],
            apply_method="url",
            contact=it.get("apply_url") or it.get("url"),
            source_url=it.get("url"),
            # RemoteOK is a remote-jobs board — every posting is remote; keep any
            # stated city too so Toronto/GTA remote roles still rank as Toronto.
            location=("Remote" + (f" · {it['location']}" if it.get("location") else "")),
        ))
    return jobs


class RemoteOKSource:
    name = "remoteok"
    url = "https://remoteok.com/api"

    def fetch(self, fetcher):
        return parse_remoteok(fetcher.get(self.url))


# ---- Application-Ready Record builder --------------------------------------
def build_bullets(job, profile, ctx, k=4):
    """Pick the résumé lines that best match this job; each becomes a truthful,
    provenanced bullet (and a backed Claim for the kernel to score)."""
    jk = job.keywords
    scored = sorted(profile.lines, key=lambda ln: len(ln.toks & jk), reverse=True)
    chosen = [ln for ln in scored if len(ln.toks & jk) > 0][:k]
    return [Bullet(ln.text, ln.line_id) for ln in chosen]


def build_arr(job, profiles, ctx, candidate=None, audit=None):
    """Turn one Job into an Application-Ready Record: identity + how-to-apply +
    requirements + fit + kernel verdict + provenanced autofill and bullets."""
    ctx.register_job(job)
    candidate = candidate or parse_candidate(profiles)
    audit = audit or NullAudit()

    best_k, best_v = ctx.best_fit(job)
    profile = profiles[best_k]
    bullets = build_bullets(job, profile, ctx)

    # auto-draft a TRUTHFUL application from the bullets, then let the kernel judge
    app = Application(
        app_id=f"arr-{job.job_id}",
        job=job, profile_key=best_k,
        claims=[Claim(b.text, b.source_line_id) for b in bullets],
        rationale=f"Relevant experience, strong match for {job.title}.")
    result = triage(app, ctx, audit)

    autofill = [
        AutofillField("full_name", candidate.name, "config"),
        AutofillField("email", candidate.email or "", f"resume:{candidate.provenance.get('email','')}"),
        AutofillField("phone", candidate.phone or "", f"resume:{candidate.provenance.get('phone','')}"),
        AutofillField("location", candidate.location or "", f"resume:{candidate.provenance.get('location','')}"),
        AutofillField("why_this_role",
                      bullets[0].text if bullets else "",
                      f"resume:{bullets[0].source_line_id}" if bullets else "config"),
    ]

    return ApplicationReadyRecord(
        job_id=job.job_id, title=job.title, company=job.company,
        source_url=job.source_url or "",
        how_to_apply={"method": job.apply_method, "contact": job.contact,
                      "url": job.source_url, "deadline": None,
                      "location": location_label(job)},
        requirements={"keywords": sorted(job.keywords & profile.keywords)[:20],
                      "stack": sorted(k for k in job.keyword_hints)},
        company_ctx={"description_excerpt": job.description[:280]},
        comp=None,
        fit_by_profile={k: round(p.fit(job), 3) for k, p in profiles.items()},
        best_profile=best_k,
        verdict_code=result.verdict.code,
        autofill=autofill,
        bullets=bullets,
        provenance={"job": job.source_url or job.job_id,
                    "bullets": [b.source_line_id for b in bullets]},
        state=result.state,
        auth_level=result.auth_level,
        nearest=result.nearest,
        job=job,
    )


# ---- top-level harvest -----------------------------------------------------
def harvest(sources, fetcher, profiles, ctx, min_fit=0.0, location_focus="toronto_remote"):
    """Fetch from each source, keep jobs passing the location focus, build an ARR
    per job, keep those that fit a profile at least `min_fit`. Toronto/GTA jobs
    are ranked above generic remote. Returns records sorted best-first."""
    records = []
    for src in sources:
        try:
            jobs = src.fetch(fetcher)
        except Exception as e:                # a dead source must not sink the run
            fetcher.guardian.escalate("harvest_source_failed",
                                      f"{getattr(src,'name',src)}: {e}")
            continue
        for job in jobs:
            if not location_ok(job, location_focus):     # Toronto + Remote gate
                continue
            arr = build_arr(job, profiles, ctx)
            if max(arr.fit_by_profile.values()) >= min_fit:
                records.append(arr)
    # rank: Toronto/GTA first, then by best fit
    records.sort(key=lambda r: ("Toronto" not in r.how_to_apply.get("location", ""),
                                -max(r.fit_by_profile.values())))
    return records
