# =============================================================================
# PSE-JOBS GUARDIAN — EGRESS ALLOWLIST
# The swarm may only reach approved hosts: job boards, the LLM API endpoints,
# and localhost. Everything else is refused. A host matches an allowlist entry
# if it equals it or is a subdomain of it (so "linkedin.com" allows
# "www.linkedin.com" but NOT "linkedin.com.evil.com").
# =============================================================================
from urllib.parse import urlparse
from .errors import GuardianViolation

# Sensible defaults; the real allowlist is configured per deployment.
DEFAULT_ALLOW = [
    # LLM endpoints (Groq / Mistral / Claude; local GGUF needs no egress)
    "api.anthropic.com", "anthropic.com", "api.mistral.ai", "mistral.ai",
    "api.groq.com", "groq.com", "localhost", "127.0.0.1",
    # job boards / aggregators (free JSON/RSS sources the system searches)
    "linkedin.com", "indeed.com", "wellfound.com", "higheredjobs.com",
    "glassdoor.com", "ziprecruiter.com", "remoteok.com", "weworkremotely.com",
    "remotive.com", "jobicy.com", "arbeitnow.com", "remotasks.com",
    # structured job APIs (Toronto-capable): Adzuna (aggregator, has location),
    # Greenhouse + Lever (public company boards, no key)
    "adzuna.com", "greenhouse.io", "lever.co",
    # web-research sources (company/role/salary background)
    "wikipedia.org", "levels.fyi",
    # payments (Square)
    "squareup.com", "squareupsandbox.com",
    # robot-account mail providers (Option A: throwaway account -> forwards to Proton)
    "gmail.com", "outlook.com", "office365.com", "zoho.com",
]


def host_of(url_or_host):
    s = str(url_or_host).strip()
    if "//" not in s:
        s = "//" + s               # let urlparse treat a bare host as netloc
    net = urlparse(s).netloc or urlparse(s).path
    return net.split("@")[-1].split(":")[0].lower().rstrip(".")


class EgressPolicy:
    def __init__(self, allow=None):
        self.allow = [h.lower().lstrip(".") for h in (allow or DEFAULT_ALLOW)]

    def _matches(self, host):
        return any(host == a or host.endswith("." + a) for a in self.allow)

    def allowed(self, url_or_host):
        return self._matches(host_of(url_or_host))

    def guard(self, url_or_host):
        host = host_of(url_or_host)
        if not self._matches(host):
            raise GuardianViolation(
                f"egress blocked: {host!r} not on the allowlist ({url_or_host!r})")
        return host

    def add(self, host):
        h = host.lower().lstrip(".")
        if h not in self.allow:
            self.allow.append(h)
