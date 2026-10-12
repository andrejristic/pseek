# PSEEK — Go-live checklist (what you plug in)

PSEEK works out of the box on free sources, the local/heuristic model, dry-run
apply, and Square test-mode. To unlock full power, plug in your own keys/accounts.
Everything is stored **encrypted in your workspace vault** — nothing is shared.

Use the same **workspace passphrase** every time:
```bash
export PSEEK_PASSPHRASE='your-strong-passphrase'
```

## 1) Connect your email (to actually SEND applications)
Your own address; apply from it. See **CONNECT-EMAIL-EN.md**.
```bash
python3 configure_user_email.py <user-id> you@gmail.com
```
Until connected, "Apliciraj" makes a **draft** (dry-run).

## 2) LLM key or local model (richer chat + generation)
Optional — without it, the local/heuristic floor runs. Add a **free** key OR a GGUF:
```bash
# a free online key (choose one)
python3 configure_source_key.py <user-id> groq_api_key   <YOUR_GROQ_KEY>
python3 configure_source_key.py <user-id> mistral_api_key <YOUR_MISTRAL_KEY>
python3 configure_source_key.py <user-id> anthropic_api_key <YOUR_CLAUDE_KEY>
# or a local GGUF model (runs offline; PII never leaves the machine)
export PSEEK_GGUF_MODEL=/path/to/model.gguf
```
PSEEK uses free cloud sparingly and falls back to local automatically.

## 3) More job sources (optional)
Free boards are always on. Add:
- **User-defined keyed API** (LinkedIn/Indeed via your own RapidAPI/SerpAPI, Adzuna…):
  store your key, then reference it in `sources_config.json` under `user_apis`
  (or `adzuna_app_id`/`adzuna_app_key`), and add the host under `allow_hosts`.
  ```bash
  python3 configure_source_key.py <user-id> my_jobs_api_key <YOUR_KEY>
  ```
- **RSS feeds** (e.g. HigherEdJobs) — add under `rss` in `sources_config.json`.
- **Greenhouse/Lever** company boards — add slugs under `greenhouse`/`lever`.

## 4) Square (seller only — real payments)
Only the seller sets this, app-side, to charge the $4.95 / $9.95 tiers:
```bash
python3 configure_source_key.py <seller-id> square_access_token <TOKEN>
python3 configure_source_key.py <seller-id> square_location_id  <LOCATION_ID>
```
Until then, entitlements run in test mode (no charge). Buying is always the user's
explicit decision.

## Order that makes sense
1. Connect email → real applications. 2. (Optional) LLM key/GGUF → smarter chat.
3. (Optional) source keys → more jobs. 4. (Seller) Square → payments.
