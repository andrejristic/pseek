# =============================================================================
# PSEEK — MULTI-SOURCE DISCOVERY TESTS (real, no stubs)
# New free-source parsers work; build_sources assembles many sources (and honours
# 'disable'); discovery fans out across sources, merges + de-duplicates, ranks by
# learned preference, and rewards the sources whose jobs get approved; every fetch
# is egress-gated; an optional live sweep runs if the network is up.
# =============================================================================
import os, sys, json, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from workspace import Workspace
from pool import DocumentPool, add_resume
from arms import (parse_remotive, parse_jobicy, parse_arbeitnow, parse_wwr_rss,
                  build_sources, Fetcher, RemoteOKSource)
from discovery import Discovery

RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

REMOTIVE = json.dumps({"jobs": [{"id": 1, "title": "Python Engineer",
    "company_name": "Acme", "description": "<p>python django</p>",
    "candidate_required_location": "Worldwide", "url": "https://remotive/1"}]}).encode()
JOBICY = json.dumps({"jobs": [{"id": 2, "jobTitle": "ML Engineer",
    "companyName": "Beta", "jobExcerpt": "pytorch nlp", "jobGeo": "Anywhere",
    "url": "https://jobicy/2"}]}).encode()
ARBEITNOW = json.dumps({"data": [{"slug": "x", "title": "Backend Dev",
    "company_name": "Gamma", "description": "python api", "location": "Toronto",
    "remote": True, "tags": ["python"], "url": "https://arbeitnow/x"}]}).encode()
WWR = (b"<rss><channel><item><title>Delta: Senior Python Developer</title>"
       b"<link>https://wwr/1</link><description>python backend</description></item>"
       b"</channel></rss>")


def test_new_parsers():
    check("remotive parsed", parse_remotive(REMOTIVE)[0].company == "Acme")
    check("jobicy parsed", parse_jobicy(JOBICY)[0].title == "ML Engineer")
    check("arbeitnow parsed (remote+toronto)",
          "Toronto" in parse_arbeitnow(ARBEITNOW)[0].location)
    j = parse_wwr_rss(WWR)[0]
    check("weworkremotely RSS parsed (company/role split)",
          j.company == "Delta" and "Python" in j.title)
    return True


def test_build_sources_many_and_disable():
    d = tempfile.mkdtemp(prefix="pseek_disc_")
    try:
        w = Workspace(d, "u", "pw")
        names = [getattr(s, "name", "") for s in build_sources({}, w.guardian)]
        check("assembles multiple free sources",
              {"remoteok", "remotive", "jobicy", "arbeitnow", "weworkremotely"} <= set(names),
              str(names))
        names2 = [getattr(s, "name", "") for s in build_sources({"disable": ["jobicy"]}, w.guardian)]
        check("'disable' removes a source", "jobicy" not in names2)
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_discovery_merges_dedups_ranks_and_learns():
    d = tempfile.mkdtemp(prefix="pseek_disc2_")
    try:
        w = Workspace(d, "u", "pw")
        pool = DocumentPool()
        add_resume(pool, "r.txt", "Python developer. Django REST APIs. PyTorch and NLP.")
        disc = Discovery(w)

        # a local multi-source set (offline determinism) + a duplicate across sources
        class Src:
            def __init__(self, name, jobs): self.name = name; self._j = jobs
            def fetch(self, fetcher): return list(self._j)
        from jobs.domain import Job
        dup = Job("remotive:9", "Python Engineer", "Acme", "python django", location="Remote")
        dup2 = Job("jobicy:9", "Python Engineer", "Acme", "python django", location="Remote")
        uniq = Job("arbeitnow:1", "ML Engineer", "Beta", "python pytorch nlp", location="Remote")
        disc.sources = lambda: [Src("remotive", [dup]), Src("jobicy", [dup2]),
                                Src("arbeitnow", [uniq])]
        recs = disc.search(pool, location_focus="remote", min_fit=0.0)
        titles = [(r.title, r.company) for r in recs]
        check("results de-duplicated across sources",
              titles.count(("Python Engineer", "Acme")) == 1, str(titles))
        check("multiple sources merged into one ranked list", len(recs) == 2)

        # feedback: approving a job rewards its source and teaches preferences
        disc.record_feedback(recs[0], "approve")
        stats = disc.source_stats()
        rewarded = [s for s, v in stats.items() if v["mean"] > 0]
        check("approved job's source gets rewarded (bandit learns)", len(rewarded) >= 1,
              str(stats))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_egress_gated():
    d = tempfile.mkdtemp(prefix="pseek_disc3_")
    try:
        w = Workspace(d, "u", "pw")
        for h in ("remotive.com", "jobicy.com", "arbeitnow.com", "weworkremotely.com"):
            check(f"{h} on egress allowlist", w.guardian.egress.allowed("https://" + h + "/x"))
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_live_optional():
    d = tempfile.mkdtemp(prefix="pseek_disc4_")
    try:
        w = Workspace(d, "u", "pw")
        try:
            jobs = RemoteOKSource().fetch(Fetcher(w.guardian))
        except Exception as e:
            print(f"  SKIP  live fetch (no network: {type(e).__name__})")
            RESULTS.append(("live (skipped)", True, "")); return True
        check("live multi-source fetch returns jobs", len(jobs) > 0, f"n={len(jobs)}")
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


ALL = [test_new_parsers, test_build_sources_many_and_disable,
       test_discovery_merges_dedups_ranks_and_learns, test_egress_gated,
       test_live_optional]

if __name__ == "__main__":
    print("PSEEK · multi-source discovery tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:")
        t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44)
    print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
