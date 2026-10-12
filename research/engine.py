# =============================================================================
# PSEEK — WEB-RESEARCH ENGINE (Guardian-gated)
# The app studies the internet to help the search: company background, role norms,
# salary ranges, interview prep. Every fetch passes the Guardian egress wall.
# Fetched pages are UNTRUSTED DATA — they are summarised, never obeyed; nothing a
# page "says to do" becomes an action (research has no action path, and any
# action elsewhere still passes the membrane/physician). Findings are stored as
# organelles so the advice accumulates and the system gets better.
# =============================================================================
import json
import re
import urllib.parse

from arms.harvest import Fetcher
from jobs.domain import tokens


def _strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


class ResearchEngine:
    def __init__(self, guardian, operator=None, registry=None):
        self.g = guardian
        self.op = operator
        self.registry = registry
        self.fetcher = Fetcher(guardian, user_agent="PSEEK-research/1.0")

    # ---- fetch (egress-gated) ----------------------------------------------
    def fetch_text(self, url):
        return _strip_html(self.fetcher.get(url).decode("utf-8", "ignore"))

    # ---- deterministic extractive summary (works with no LLM) --------------
    def summarize(self, text, question, k=3):
        qk = tokens(question)
        sents = re.split(r"(?<=[.!?])\s+", text)
        scored = sorted(sents, key=lambda s: len(tokens(s) & qk), reverse=True)
        picked = [s.strip() for s in scored if len(tokens(s) & qk) > 0][:k]
        return " ".join(picked)

    def _store(self, kind, subject, summary):
        finding = {"kind": kind, "subject": subject, "summary": summary}
        if self.registry is not None:
            self.registry.add_organelle("research", f"{kind}: {subject} — {summary}",
                                        {"kind": kind, "subject": subject})
        return finding

    # ---- research a body of text (offline / already-fetched) ---------------
    def research_from_text(self, kind, subject, text, question):
        summary = self.summarize(text, question)
        return self._store(kind, subject, summary)

    # ---- live research (needs network; egress-gated) -----------------------
    def research_company(self, name):
        url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
               + urllib.parse.quote(name.replace(" ", "_")))
        data = json.loads(self.fetcher.get(url))
        extract = data.get("extract", "")
        return self._store("company", name,
                           self.summarize(extract, f"{name} company products industry")
                           or extract[:300])

    def research_role(self, title):
        url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
               + urllib.parse.quote(title.replace(" ", "_")))
        data = json.loads(self.fetcher.get(url))
        return self._store("role", title,
                           self.summarize(data.get("extract", ""), title) or "")
