# PSEEK

An LLM-driven job-search & apply copilot **for anyone**, built on the PSE kernel
and sold to third parties. It **searches many sources**, combines your résumés and
cover letters into the best **honest** pitch per job (the Combinatorial Synthesis
Engine), **applies for you from your own email**, researches the web, **learns you**,
asks smart questions, and — once you land a job — becomes your on-the-job assistant.
It does everything **except the decisions**: you decide (the *physician*), always.

Governed by the PSE kernel (vendored byte-identical): the **two floors**
(truthfulness + consent) and **θ** (self/other balance) keep every combination
honest and every send behind your approval.

## Run (source)
```bash
pip install PySide6
python3 run_pseek.py            # or: python3 run_pseek.py --selfcheck
```

## Guides
- **USING-EN.md / USING-SR.md** — how to use it (tabs, chat commands, applying, learning).
- **GO-LIVE-EN.md / GO-LIVE-SR.md** — the keys/accounts you plug in for full power.
- **CONNECT-EMAIL-EN.md / -SR.md** — connect your own email (to send).
- **INSTALL-{SOURCE,DEB,EXE,APP}-{EN,SR}.md** — install per distribution output.

## What it does (at a glance)
- **Searches many sources**: RemoteOK, Remotive, Jobicy, Arbeitnow, WeWorkRemotely
  (free) + your Greenhouse/Lever boards, RSS feeds (e.g. HigherEdJobs), and any
  **user-defined keyed API** (LinkedIn/Indeed via your own key). De-duplicated,
  location-filtered, ranked by what you like.
- **Drive by chat**: `nađi poslove`, `izvori`, `zašto N`, `apliciraj N`,
  `generiši rezime: …`, `dokumenti / prijave / strategija`.
- **Live tabs**: Dashboard (θ), Poslovi, Dokumenti, Prijave, Strategija, Settings.
- **Opt-in learning** (OFF by default): auto-search on a timer; reward sources from
  your ✅/✕ ratings.
- **Apply**: ✉ Apliciraj → CSE cover from your real lines → your email (dry-run
  until connected) → tracked in Prijave.

## Four distribution outputs
| Output | How | Guide |
|--------|-----|-------|
| PySide6 source | `python3 run_pseek.py` | `INSTALL-SOURCE-*` |
| `.deb` (Linux) | `python3 packaging/build_deb.py` → `dist/*.deb` | `INSTALL-DEB-*` |
| `.exe` (Windows) | `pyinstaller packaging/pseek.spec` | `INSTALL-EXE-*` |
| `.app` (macOS) | `pyinstaller packaging/pseek.spec` | `INSTALL-APP-*` |

## Pricing (paywall on open)
- **First 24h:** everything (trial). · **$4.95/mo:** 1 résumé + 1 cover (no CSE).
- **$9.95/mo:** Combination Engine + multiple uploads + generation.
Payment via Square to the seller's account. Buying is your decision.

## LLM backends
Groq · Mistral · Claude (free-tier keys, optional) · **local GGUF via llama.cpp**
(the workhorse — offline; PII never leaves the machine). Runs on a local/heuristic
floor with no key at all.

## Tests
```bash
for t in tests/test_*.py; do QT_QPA_PLATFORM=offscreen python3 "$t"; done
# 20 files, all green
```
