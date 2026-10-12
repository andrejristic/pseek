# PSEEK — Plan & Advice (v2)
### PSE + *seek* · an LLM-driven job copilot for anyone · on the PSE kernel · 2026
Productized successor to PSE-Jobs, **built to sell to third parties**. Same kernel
+ two floors, reused verbatim. **No software is built yet — say "kreni" to start.**

## 0 · The one idea — two product modes
- **Mode 1 — Job Copilot.** Searches, researches the web, learns you, **combines
  your résumés + cover letters into the best honest pitch per job**, applies for
  you, advises how to handle employers, and does **everything except the
  decisions** — you decide, by talking to it.
- **Mode 2 — On-the-job Assistant.** The moment you land a job, PSEEK transforms:
  it studies (online) how to help you in *that* role and helps you. Same kernel,
  floors, θ, physician — a new pack.
You control all of it through an always-open **LLM chat panel** (right ⅓ of screen).

## 1 · θ and the Physician (load-bearing — read first)
- **θ (Theta) — self/other allocation, healthy band [25, 35], optimum 30.** How
  much PSEEK centers **you (self)** vs the **market/employer (other)** in every
  action. θ < 25 → Codependent (you disappear into the employer's wishlist);
  θ > 35 → Narcissistic (pushing your angle, ignoring the role). Kept in band,
  shown as a gauge, and used as the **attention budget for self-inquiry**.
- **Physician = you.** The decision authority the swarm defers to and escalates
  to. "Does everything except decisions" = the physician rule: every gate
  escalates to you (consent floor = human_review). To apply / reply / accept /
  pay is always your call.

## 2 · No wizard — the Combinatorial Synthesis Engine (CSE)  ← the core Andrej wants
You drop in **as many résumés and cover letters as you want** (a document pool) —
**OR generate them by talking to the app**: the LLM interviews you and writes a
résumé / cover letter with you, which then joins the pool (truthful — built from
what you tell it). No step-by-step wizard. The machine **reasons combinatorially**:

> "If I combine résumé A + résumé B's line on X with cover-letter 2's framing,
>  this candidate fits job X."

- **The algorithm (must be built):** for each job, search over *combinations* —
  which résumé sections + which cover-letter paragraphs to assemble into one
  honest pitch. Greedy/beam search: start from the best-fit base, add sections
  that raise fit **without** pushing toward an attractor, pick cover paragraphs by
  relevance, stop when θ leaves the band or a floor is at risk. Output: ranked
  `(job → combination)` proposals with fit + θ + nearest-attractor. **You decide
  whether to apply.**
- **θ governs the combination.** θ tunes the self/other balance of the assembled
  pitch: low θ over-tailors (drops the real you to mirror the JD → Codependent);
  high θ over-projects (dumps everything regardless of the role → Narcissistic);
  in-band θ yields a proportionate, honest, job-relevant combination.
- **Attractors are the guardrails on every candidate combination:**
  - **Narcissistic** — inflating: using all docs to look bigger than the role needs.
  - **Codependent** — contorting: assembling only what the JD asks, losing your identity.
  - **Schizoid** — mechanical: a combination that ignores whether it fits the role at all.
  - **Borderline** — inconsistent: a different "you" assembled each application (variance).
  Each combination is scored on the simplex; ones that hit an attractor are
  rejected/escalated; the chosen one sits in the healthy interior.
- **Truthfulness floor holds by construction:** the CSE only **selects and
  arranges** real lines from your uploaded docs — it never invents.

## 3 · LLM control + right-hand chat panel
One operator abstraction, four backends: **Groq · Mistral · Claude (online APIs) ·
local GGUF via llama.cpp (truly local, not external).**
- **The seller (Andrej) supplies only FREE-tier online keys.** So **local GGUF is
  the primary workhorse** (no cost, no quota); Groq/Mistral/Claude free keys are
  used sparingly for higher-quality moments, with **quota-aware routing**: track
  each backend's free limit, and on rate-limit/quota errors **fall back
  automatically** to another free backend or to local GGUF. The product must run
  fully on local GGUF alone if every free cloud key is exhausted.
- PII → local model; Guardian redacts before any cloud call; untrusted job posts /
  employer emails are data, never instructions.
- **Chat sidebar on the right, ~⅓ screen, always open** — run the whole app by
  talking; also **generate résumés/cover letters conversationally** here.

## 3b · Credentials: who supplies what, added later (build everything now)
- **Seller (Andrej) supplies:** free Groq/Mistral/Claude API keys + the seller
  Square account/keys. Shipped/configured once, server- or app-side.
- **End-user supplies:** their **own private email** (see §7) — connected in-app,
  stored in that user's per-user vault. Each user applies from their own address;
  no shared robot account.
- All logic built & tested now; keys go into the vault later via helpers
  (`configure_llm.py`, `configure_square.py`; user-facing "Connect email" flow).
  **Nothing is a mock/stub** — live calls activate on key; guard/redaction/
  entitlement/quota flows are tested deterministically without keys.

## 4 · Learns to search better (3 loops)
A) Preference learning (weights from your open/approve/reject/edit). B) Query/
discovery bandit (learn where & how to search). C) Outcome learning / Seldon
(what earns replies → reweight + suggest résumé/cover edits). Learning only
reorders/filters; floors never move.

## 5 · Self-inquiry (the app probes you), budgeted by θ
Uncertainty / contradiction / gap / weekly-review / A-B questions. ≤ 1–2 per
session, gated on info-gain × impact (θ = attention spent on the other).

## 6 · Web research
Guardian-gated internet study (company, role norms, salary, interview prep, how to
handle a specific employer) → organelles/advice. Content is untrusted data.

## 7 · Apply + employer handling (from the user's OWN email)
Each user connects **their own private email** (one or more) in-app; credentials
live in that user's per-user vault; there is **no shared robot account**. Apply-
for-you sends from the user's own address (CSE combination + autofill, behind
consent). When the employer replies (into the user's inbox): read as data → advise
how to behave → draft the reply → interview prep. θ keeps you authentic. You
approve everything.

## 8 · Monetization — Square Pay (CORE: this is sold to third parties)
**A paywall popup appears when the user opens the app.**
- **First 24 hours: everything included** (full trial — all features, so the CSE
  and multiple uploads are live during the trial).
- **$4.95 / month:** 1 résumé + 1 cover letter — basic apply, **no combination
  engine**, single-doc only.
- **$9.95 / month:** the **Combination Engine (CSE) + multiple uploads** (and
  conversational doc generation).
- **Payment goes to the SELLER's (Andrej's) Square account**, via as many
  Square-supported sources as possible (card, Apple Pay, Google Pay, ACH where
  available).
- Entitlements gate features; buy/upgrade in the popup or through the chat; a
  purchase requires the user's explicit confirmation (physician) — no charge
  without it. Live charging activates once the seller's Square keys are in.

## 9 · GUI
Left **sidebar nav** · center content · right **LLM chat panel (⅓, always open)**.
θ gauge, animated Live Simplex + funnel, stat cards, empty states, light + dark.
PySide6 + `theme.qss`.

## 10 · Distribution — 4 outputs, each with EN + SR guide
1. **PySide6** — runnable source (`run_app.py`) for dev/advanced users.
2. **.deb** — Debian/Ubuntu package (built on Linux).
3. **.exe** — Windows build (PyInstaller; must be built on Windows / CI).
4. **.app** — macOS bundle (PyInstaller/py2app; must be built on macOS / CI).
Each ships an **EN and SR install+use guide**. (From this Linux box I can build
the .deb + PySide6 source and produce the PyInstaller specs + build scripts +
guides for all four; the actual .exe/.app are produced on their OS or CI.)

---

## 11 · FULL PHASE LIST (build order, when you say "kreni")
**Foundation**
- **P0 — Fork + per-user encrypted workspace.** PSE-Jobs → PSEEK; strip person-
  specifics; reuse kernel + floors verbatim.
- **P1 — Document pool + Combinatorial Synthesis Engine (§2).** Ingest N résumés +
  M cover letters **or generate them conversationally** (LLM interviews you → doc
  joins the pool). θ-governed, attractor-aware combination search per job; ranked
  `(job → combination)` proposals. **The algorithm Andrej asked for.**

**θ + physician + LLM control**
- **P2 — θ engine + physician decision-classes.** Live θ, band correction, θ gauge;
  the actions that always escalate to you.
- **P3 — LLM operator + right-hand chat panel.** Backend abstraction + redaction +
  the ⅓-screen always-open chat that controls everything; governed.

**Intelligence**
- **P4 — Web-research engine** (Guardian-gated).
- **P5 — Preference learning (Loop A).**
- **P6 — Query/discovery bandit (Loop B).**
- **P7 — Outcome learning / Seldon (Loop C)** + résumé/cover edit suggestions.
- **P8 — Self-inquiry engine** (θ-budgeted).

**Doing the work**
- **P9 — Connect-your-email + Apply-for-you.** Each user connects their own private
  email (per-user vault); apply from their own address (from the CSE combination),
  behind consent.
- **P10 — Employer-response handling** (read → advise → draft reply → interview prep).

**Money (core — it's sold)**
- **P11 — Square Pay + tiers/paywall + entitlements.** Paywall popup on open; **24h
  full trial · $4.95/mo (1 résumé + 1 cover, no CSE) · $9.95/mo (CSE + multi-
  upload)**; payment to the seller's Square via max sources; buy-via-popup/chat;
  purchase requires user confirmation.

**Mode 2**
- **P12 — "Got the job" transformation** — on-the-job assistant pack.

**Polish, package, ship**
- **P13 — GUI redesign & polish** (sidebar + chat panel + θ gauge + animated simplex + theme).
- **P14 — Packaging: 4 outputs** (PySide6 · .deb · .exe · .app), build scripts + specs.
- **P15 — Guides: EN + SR for each of the 4 outputs.**

## 12 · Reuse vs new
```
 REUSE verbatim:  kernel · guardian + floors · tracker · seldon · mailarm · sources · harvest
 GENERALIZE:      per-user workspace · email arm (any provider) · profiles → document pool
 NEW:             Combinatorial Synthesis Engine · θ engine · physician decision-classes ·
                  LLM operator + chat panel · web-research · preference model · bandit ·
                  self-inquiry · employer-response arm · Square Pay/entitlements ·
                  Mode-2 assistant · GUI shell · 4-target packaging
```

## 13 · Confirmed
- **LLM:** Groq · Mistral · Claude · local GGUF (llama.cpp). **Seller supplies only
  FREE online keys** → local GGUF is the workhorse; quota-aware routing + auto
  fallback to local; runs fully on GGUF if free cloud is exhausted.
- **Credentials:** seller injects free LLM keys + Square; **each end-user connects
  their own private email**. Build everything now; keys added later via helpers /
  in-app "Connect email". No mocks/stubs.
- **Pricing:** paywall popup on open · 24h full trial · **$4.95/mo** (1 résumé + 1
  cover, no CSE) · **$9.95/mo** (CSE + multi-upload + doc generation) · to seller's
  Square, max payment sources.
- **Docs:** upload **or** generate résumés/cover letters conversationally.
- CSE + θ/attractors governing the combination · physician (decisions are the
  user's) · 4 outputs + EN/SR guides — all as written.
- **Awaiting "kreni" to start at P0.**

---
## Build status — COMPLETE (all P0–P15 + extensions)
158→169 checks green across 20 test files; kernel moat byte-identical. Beyond the
16 phases: multi-source discovery (5 free boards + user-defined RSS + user-defined
keyed APIs), chat command layer ("nađi poslove", "apliciraj N", "generiši …"),
live Dokumenti/Prijave/Strategija tabs, "Apliciraj" wired to the apply-arm, and
opt-in auto-search + feedback-learning. Guides: USING-{EN,SR}, GO-LIVE-{EN,SR},
CONNECT-EMAIL-{EN,SR}, INSTALL-{SOURCE,DEB,EXE,APP}-{EN,SR}. Remaining = plug in
keys (LLM/Square/email/source) — see GO-LIVE.
