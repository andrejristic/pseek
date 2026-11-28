# =============================================================================
# PSEEK — CHAT ROUTER (drive the system by talking)
# Deterministic commands first (so it works with no LLM), LLM fallback otherwise.
# "nađi poslove" fans out across every source (Discovery), pushes results to the
# GUI Poslovi tab via on_results, and teaches the source bandit + preferences on
# feedback. Governed: proposals still pass θ / the floors / the physician.
# =============================================================================
import re


class PseekChat:
    def __init__(self, workspace, discovery, pool_provider, operator=None,
                 on_results=None, apply_cb=None):
        self.ws = workspace
        self.disc = discovery
        self.pool_provider = pool_provider
        self.operator = operator
        self.on_results = on_results
        self.apply_cb = apply_cb
        self.results = []

    def handle(self, text):
        low = text.lower().strip()
        if re.search(r"na[dđ]?i poslove|tra[zž]i poslove|find jobs|search jobs|"
                     r"^na[dđ]i$|^tra[zž]i$|^search$", low):
            return self._search()
        if re.search(r"\bizvor|sources\b", low):
            return self._sources()
        m = re.search(r"apliciraj\s*#?(\d+)", low)
        if m:
            return self._apply(int(m.group(1)))
        m = re.search(r"generi[sš]i\s+(rezime|cv|cover|propratno)", low)
        if m:
            return self._generate(m.group(1), text)
        if re.search(r"\bdokument", low):
            return self._documents()
        if re.search(r"\bprijav", low):
            return self._applications()
        if re.search(r"strategij|strategy", low):
            return self._strategy()
        if re.search(r"lista|list jobs|prika[zž]i poslove|^poslovi$", low):
            return self._list()
        m = re.search(r"(za[sš]to|why)\s*#?(\d+)", low)
        if m:
            return self._why(int(m.group(2)))
        if self.operator is not None:
            return self.operator.complete([{"role": "user", "content": text}])["text"]
        return ("Komande: nađi poslove · izvori · lista · zašto N · apliciraj N · "
                "generiši rezime: … · dokumenti · prijave · strategija")

    def _search(self):
        pool = self.pool_provider()
        if not pool.resumes:
            return "Prvo dodaj bar jedan rezime (docs/ ili generiši u chatu)."
        focus = self.ws.registry.get_pref("location_focus", "toronto_remote")
        try:
            self.results = self.disc.search(pool, location_focus=focus)
        except Exception as e:
            return f"Pretraga nije uspjela: {e}"
        if self.on_results:
            self.on_results(self.results)
        n = len(self.results)
        top = "\n".join(f"{i+1}. [{r.verdict_code}] {r.title} @ {r.company}"
                        for i, r in enumerate(self.results[:5]))
        return (f"Pretražio {len(self.disc.sources())} izvora → {n} poslova "
                f"(fokus: {focus}).\n{top}" + ("\n…" if n > 5 else ""))

    def _sources(self):
        names = [getattr(s, "name", str(s)) for s in self.disc.sources()]
        best = self.disc.best_sources()
        return (f"Izvori ({len(names)}): {', '.join(names)}.\n"
                f"Najbolji za tebe (uči se): {', '.join(best) if best else '—'}")

    def _list(self):
        if not self.results:
            return "Nema rezultata — reci 'nađi poslove'."
        return "\n".join(f"{i+1}. [{r.verdict_code}] {r.title} @ {r.company} "
                         f"· {r.how_to_apply.get('location','')}"
                         for i, r in enumerate(self.results[:15]))

    def _why(self, n):
        i = n - 1
        if not (0 <= i < len(self.results)):
            return f"Nema posla #{n}."
        r = self.results[i]
        ws_, wo_, wf_ = r.state
        return (f"#{n} {r.title} @ {r.company}: {r.verdict_code}, "
                f"state=({ws_:.2f},{wo_:.2f},{wf_:.2f}), fit {max(r.fit_by_profile.values()):.2f}, "
                f"lokacija {r.how_to_apply.get('location','')}.")

    def feedback(self, n, action):
        i = n - 1
        if 0 <= i < len(self.results):
            self.disc.record_feedback(self.results[i], action)

    # ---- apply / generate / tab summaries ----------------------------------
    def _apply(self, n):
        i = n - 1
        if not (0 <= i < len(self.results)):
            return f"Nema posla #{n} — prvo 'nađi poslove'."
        if self.apply_cb is None:
            return "Apply nije povezan."
        res = self.apply_cb(self.results[i])
        st = res.get("status") if isinstance(res, dict) else res
        return {"sent": "Poslato ✉ (prati u Prijave).",
                "dry_run": "Draft spreman (poveži email da se stварno pošalje).",
                "escalate": "Čeka tvoje odobrenje."}.get(st, f"Apliciraj: {st}")

    def _generate(self, kind, text):
        import os
        from llm.generate import generate_resume, generate_cover
        body = text.split(":", 1)[1] if ":" in text else ""
        facts = [f.strip() for f in re.split(r"[;\n]", body) if len(f.strip()) > 3]
        if not facts:
            return ("Reci činjenice, npr: 'generiši rezime: 5 godina Python; "
                    "vodio tim od 4; magistar matematike'")
        name = self.ws.registry.get_pref("name", "Candidate")
        if kind in ("cover", "propratno"):
            out = generate_cover(self.operator, name, "", "the role", facts)
            fn = "generated_cover.txt"
        else:
            out = generate_resume(self.operator, name, facts)
            fn = "generated_resume.txt"
        path = os.path.join(self.ws.docs_dir, fn)
        self.ws.guardian.guard_write(path)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out["text"])
        return (f"Napravljen {fn} (u docs/, iz tvojih činjenica; ušao u pool). "
                f"Backend: {out['backend']}.")

    def _documents(self):
        pool = self.pool_provider()
        s = pool.summary()
        names = [r.name for r in pool.resumes] + [c.name for c in pool.covers]
        return f"Dokumenti: {s['resumes']} rezimea, {s['covers']} covera. {', '.join(names) or '—'}"

    def _applications(self):
        apps = self.ws.tracker.all()
        if not apps:
            return "Nema prijava još."
        return "\n".join(f"• {a['title']} @ {a['company']} — {a['state']}" for a in apps[:15])

    def _strategy(self):
        from learning import SeldonEngine
        a = SeldonEngine().analyze(self.ws.tracker)
        o = a.get("overall", {})
        best = self.disc.best_sources()
        return (f"Ishodi: poslato {o.get('sent',0)}, response "
                f"{int(o.get('response_rate',0)*100)}%. Najbolji izvori: "
                f"{', '.join(best) if best else '—'}.")
