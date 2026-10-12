# PSEEK — How to use it

You drive PSEEK by **talking** to the chat panel on the right, or with the sidebar
tabs. It searches many job sources, combines your documents into the best honest
pitch per job, applies for you, and learns you. **You make the decisions** — it
does everything else.

## The tabs (left sidebar)
- **Dashboard** — the θ gauge (self/other balance) + overview.
- **Poslovi (Jobs)** — search results as a table: verdict · title · company ·
  location · fit. Two **opt-in options** (both OFF by default) and three action
  buttons (below).
- **Dokumenti** — your résumés & cover letters (add files to `docs/` or generate
  them in chat).
- **Prijave (Applications)** — the lifecycle of everything you applied to.
- **Strategija** — what the system learned: outcomes, best sources, your preferences.
- **Settings** — what to plug in (keys/email) + font (A− / A+, default 20) + theme.

## Chat commands (type these in the right panel)
| Command | What it does |
|---|---|
| `nađi poslove` / `find jobs` | search ALL sources → fills the Jobs tab |
| `izvori` | list sources + which work best for you |
| `lista` | list current results |
| `zašto 3` | explain job #3 (verdict, θ, fit, location) |
| `apliciraj 2` | apply to job #2 (draft/send, behind consent) |
| `generiši rezime: fact1; fact2; …` | build a truthful résumé from your facts → `docs/` |
| `generiši cover: …` | build a cover letter the same way |
| `dokumenti` / `prijave` / `strategija` | summarise those tabs |

Anything else goes to the LLM (or the local floor if no model is connected).

## Applying (from the Jobs tab)
Select a job → **✉ Apliciraj**. PSEEK builds the best **combination** of your
résumés + cover paragraphs for that job (truthful — only your real lines), then:
- if your email is connected → sends from **your** address (this click is your consent);
- if not → prepares a **draft (dry-run)**, nothing is sent.
It's recorded in **Prijave**.

## Learning (opt-in — you turn it on)
- **☐ Auto-pretraga** — PSEEK re-searches on its own on an interval. OFF by default.
- **☐ Uči iz mojih ocjena** — the **✅ Odobri / ✕ Odbij** buttons reward the source
  and teach your preferences. OFF by default; while off, those buttons do nothing.

## Safety (always on)
- **Truthful by construction** — every claim traces to one of your document lines;
  it cannot invent.
- **You decide** — applying, sending, replying, paying always wait for your click.
- **θ** keeps each pitch balanced (not over-selling you, not contorting to the employer).

See **GO-LIVE-EN.md** for the keys/accounts you plug in to unlock full power.
