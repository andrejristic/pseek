# =============================================================================
# PSE-JOBS — JOB SOURCES (Toronto-capable, structured, legal)
# Real APIs with clean JSON, no brittle HTML scraping and no ToS grey areas:
#   • Adzuna    — aggregator with a `where=Toronto` location search (needs a free
#                 app_id/app_key; the path to ONSITE Toronto postings).
#   • Greenhouse— public per-company board JSON (no key); location included.
#   • Lever     — public per-company board JSON (no key); location included.
# Each source parses to jobs.domain.Job (with `location` set) so the Toronto +
# Remote focus filter works. Every fetch still goes through the Guardian egress
# wall (hosts are on the allowlist).
# =============================================================================
import html
import json
import re
from urllib.parse import quote

from jobs.domain import Job, tokens


def _strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()

def _kw(title):
    return list(tokens(title))[:12]


# ---- Adzuna ----------------------------------------------------------------
def parse_adzuna(json_bytes):
    data = json.loads(json_bytes)
    jobs = []
    for it in data.get("results", []):
        jobs.append(Job(
            job_id=f"adzuna:{it.get('id')}",
            title=it.get("title", ""),
            company=(it.get("company") or {}).get("display_name", ""),
            description=_strip_html(it.get("description", "")),
            keyword_hints=_kw(it.get("title", "")),
            apply_method="url",
            contact=it.get("redirect_url"),
            source_url=it.get("redirect_url"),
            location=(it.get("location") or {}).get("display_name", ""),
        ))
    return jobs


class AdzunaSource:
    name = "adzuna"

    def __init__(self, app_id, app_key, where="Toronto", country="ca",
                 what=None, results=25):
        self.app_id = app_id
        self.app_key = app_key
        self.where = where
        self.country = country
        self.what = what
        self.results = results

    def url(self):
        u = (f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
             f"?app_id={quote(self.app_id)}&app_key={quote(self.app_key)}"
             f"&results_per_page={self.results}&where={quote(self.where)}")
        if self.what:
            u += f"&what={quote(self.what)}"
        return u

    def fetch(self, fetcher):
        return parse_adzuna(fetcher.get(self.url()))


# ---- Greenhouse ------------------------------------------------------------
def parse_greenhouse(json_bytes, company):
    data = json.loads(json_bytes)
    jobs = []
    for it in data.get("jobs", []):
        jobs.append(Job(
            job_id=f"gh:{company}:{it.get('id')}",
            title=it.get("title", ""),
            company=company,
            description=_strip_html(it.get("content", "")),
            keyword_hints=_kw(it.get("title", "")),
            apply_method="url",
            contact=it.get("absolute_url"),
            source_url=it.get("absolute_url"),
            location=(it.get("location") or {}).get("name", ""),
        ))
    return jobs


class GreenhouseSource:
    name = "greenhouse"

    def __init__(self, company):
        self.company = company

    def url(self):
        return (f"https://boards-api.greenhouse.io/v1/boards/"
                f"{self.company}/jobs?content=true")

    def fetch(self, fetcher):
        return parse_greenhouse(fetcher.get(self.url()), self.company)


# ---- Lever -----------------------------------------------------------------
def parse_lever(json_bytes, company):
    data = json.loads(json_bytes)
    jobs = []
    for it in data:
        cats = it.get("categories") or {}
        jobs.append(Job(
            job_id=f"lever:{company}:{it.get('id')}",
            title=it.get("text", ""),
            company=company,
            description=_strip_html(it.get("descriptionPlain") or it.get("description", "")),
            keyword_hints=_kw(it.get("text", "")),
            apply_method="url",
            contact=it.get("applyUrl") or it.get("hostedUrl"),
            source_url=it.get("hostedUrl"),
            location=cats.get("location", ""),
        ))
    return jobs


class LeverSource:
    name = "lever"

    def __init__(self, company):
        self.company = company

    def url(self):
        return f"https://api.lever.co/v0/postings/{self.company}?mode=json"

    def fetch(self, fetcher):
        return parse_lever(fetcher.get(self.url()), self.company)


# ---- more free sources (no key): Remotive, Jobicy, Arbeitnow, WeWorkRemotely ---
def parse_remotive(json_bytes):
    data = json.loads(json_bytes)
    jobs = []
    for it in data.get("jobs", []):
        jobs.append(Job(
            job_id=f"remotive:{it.get('id')}", title=it.get("title", ""),
            company=it.get("company_name", ""),
            description=_strip_html(it.get("description", "")),
            keyword_hints=_kw(it.get("title", "")), apply_method="url",
            contact=it.get("url"), source_url=it.get("url"),
            location="Remote" + (f" · {it.get('candidate_required_location')}"
                                 if it.get("candidate_required_location") else "")))
    return jobs


class RemotiveSource:
    name = "remotive"
    url = "https://remotive.com/api/remote-jobs"
    def fetch(self, fetcher):
        return parse_remotive(fetcher.get(self.url))


def parse_jobicy(json_bytes):
    data = json.loads(json_bytes)
    jobs = []
    for it in data.get("jobs", []):
        jobs.append(Job(
            job_id=f"jobicy:{it.get('id')}", title=it.get("jobTitle", ""),
            company=it.get("companyName", ""),
            description=_strip_html(it.get("jobExcerpt") or it.get("jobDescription", "")),
            keyword_hints=_kw(it.get("jobTitle", "")), apply_method="url",
            contact=it.get("url"), source_url=it.get("url"),
            location="Remote" + (f" · {it.get('jobGeo')}" if it.get("jobGeo") else "")))
    return jobs


class JobicySource:
    name = "jobicy"
    url = "https://jobicy.com/api/v2/remote-jobs"
    def fetch(self, fetcher):
        return parse_jobicy(fetcher.get(self.url))


def parse_arbeitnow(json_bytes):
    data = json.loads(json_bytes)
    jobs = []
    for it in data.get("data", []):
        loc = it.get("location", "")
        if it.get("remote"):
            loc = "Remote" + (f" · {loc}" if loc else "")
        jobs.append(Job(
            job_id=f"arbeitnow:{it.get('slug')}", title=it.get("title", ""),
            company=it.get("company_name", ""),
            description=_strip_html(it.get("description", "")),
            keyword_hints=[t for t in (it.get("tags") or [])] + _kw(it.get("title", "")),
            apply_method="url", contact=it.get("url"), source_url=it.get("url"),
            location=loc))
    return jobs


class ArbeitnowSource:
    name = "arbeitnow"
    url = "https://www.arbeitnow.com/api/job-board-api"
    def fetch(self, fetcher):
        return parse_arbeitnow(fetcher.get(self.url))


def parse_rss(rss_bytes, source="rss", default_location="Remote"):
    """Generic RSS: <item><title>[Company: ]Role</title><link/><description/>."""
    text = rss_bytes.decode("utf-8", "ignore")
    jobs = []
    for i, m in enumerate(re.finditer(r"<item>(.*?)</item>", text, re.S)):
        block = m.group(1)
        def tag(t):
            mm = re.search(rf"<{t}>(.*?)</{t}>", block, re.S)
            return _strip_html(html.unescape(mm.group(1))) if mm else ""
        title = tag("title")
        company, sep, role = title.partition(":")
        jobs.append(Job(
            job_id=f"{source}:{i}", title=(role.strip() if sep else title.strip()),
            company=(company.strip() if sep else ""), description=tag("description"),
            keyword_hints=_kw(title), apply_method="url",
            contact=tag("link"), source_url=tag("link"), location=default_location))
    return jobs


def parse_wwr_rss(rss_bytes):
    return parse_rss(rss_bytes, "wwr", "Remote")


class WeWorkRemotelySource:
    name = "weworkremotely"
    url = "https://weworkremotely.com/remote-jobs.rss"
    def fetch(self, fetcher):
        return parse_rss(fetcher.get(self.url), "wwr", "Remote")


class GenericRSSSource:
    """A user-defined RSS feed (e.g. HigherEdJobs for teaching). No key needed."""
    def __init__(self, name, url, default_location=""):
        self.name = name
        self._url = url
        self.default_location = default_location
    def fetch(self, fetcher):
        return parse_rss(fetcher.get(self._url), self.name, self.default_location)


def _dig(obj, path):
    for part in (path or "").split("."):
        if part and isinstance(obj, dict):
            obj = obj.get(part, [])
    return obj


class UserApiSource:
    """A USER-DEFINED keyed JSON job API. The user supplies their own key (from
    their vault) and a small field mapping, so any keyed board they have access to
    (LinkedIn/Indeed via a RapidAPI/SerpAPI endpoint, Adzuna-like, etc.) plugs in
    with NO code. url_template may contain {key} and {query}."""
    def __init__(self, name, url_template, key, mapping, query=""):
        self.name = name
        self.url_template = url_template
        self.key = key
        self.mapping = mapping or {}
        self.query = query

    def url(self):
        return self.url_template.replace("{key}", self.key).replace("{query}", quote(self.query))

    def fetch(self, fetcher):
        m = self.mapping
        data = json.loads(fetcher.get(self.url()))
        items = _dig(data, m.get("list", "")) if m.get("list") else data
        if not isinstance(items, list):
            items = []
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            title = str(it.get(m.get("title", "title"), ""))
            out.append(Job(
                job_id=f"{self.name}:{it.get(m.get('id', 'id'), '')}",
                title=title, company=str(it.get(m.get("company", "company"), "")),
                description=_strip_html(str(it.get(m.get("description", "description"), ""))),
                keyword_hints=_kw(title), apply_method="url",
                contact=it.get(m.get("url", "url")), source_url=it.get(m.get("url", "url")),
                location=str(it.get(m.get("location", "location"), "") or "")))
        return out


# ---- build the source list from config + vault -----------------------------
FREE_SOURCES = None      # lazily built to avoid import cycle


def build_sources(config, guardian):
    """Assemble every source the system will search: the free JSON/RSS boards
    (no key), plus Greenhouse/Lever company boards from config, plus Adzuna if a
    key is in the vault. `config` may set {"greenhouse":[...], "lever":[...],
    "adzuna":{...}, "disable":[names]}."""
    from arms.harvest import RemoteOKSource
    disabled = set(config.get("disable") or [])
    # user-authorized extra hosts (for their own RSS / keyed APIs)
    for h in (config.get("allow_hosts") or []):
        guardian.egress.add(h)

    sources = [RemoteOKSource(), RemotiveSource(), JobicySource(),
               ArbeitnowSource(), WeWorkRemotelySource()]
    for c in (config.get("greenhouse") or []):
        sources.append(GreenhouseSource(c))
    for c in (config.get("lever") or []):
        sources.append(LeverSource(c))
    # user-defined RSS feeds (e.g. HigherEdJobs for teaching)
    for r in (config.get("rss") or []):
        sources.append(GenericRSSSource(r["name"], r["url"], r.get("location", "")))
    # user-defined keyed APIs — the user's OWN key, read from their vault
    for ua in (config.get("user_apis") or []):
        kn = ua.get("key_name")
        if kn and guardian.has_secret(kn):
            sources.append(UserApiSource(ua["name"], ua["url_template"],
                                         guardian.secret(kn), ua.get("mapping", {}),
                                         query=ua.get("query", "")))
    # Adzuna — key is USER-DEFINED (their own, from their vault)
    adz = config.get("adzuna")
    if adz and guardian.has_secret("adzuna_app_id") and guardian.has_secret("adzuna_app_key"):
        sources.append(AdzunaSource(
            guardian.secret("adzuna_app_id"), guardian.secret("adzuna_app_key"),
            where=adz.get("where", "Toronto"), country=adz.get("country", "ca"),
            what=adz.get("what")))
    return [s for s in sources if getattr(s, "name", "") not in disabled]
