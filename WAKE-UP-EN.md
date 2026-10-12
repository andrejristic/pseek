# PSEEK — Good morning ☀️  What Claude did & what's left for YOU

This is the short list of everything you (Andrej) need to do. Everything a machine
could do without your private keys is **already done and verified**. Each step
below is copy-paste. Run them from `~/Desktop/PSEEK`.

---

## ✅ Done overnight (already working, nothing for you to do here)
- **Local GGUF "workhorse" is LIVE.** Installed `llama-cpp-python`; PSEEK now
  **auto-finds your model** with zero config (env → `PSEEK/models/` →
  `~/Downloads`). It currently points to
  `~/Desktop/2222/11/gut_ai/models/Qwen2.5-7B-Instruct-Q6_K.gguf`.
  `selfcheck` shows `local_gguf: True`.
- **All tests green: 20/20 files.** PSE kernel untouched (byte-identical moat).
- **GUI launches and wires end-to-end** (verified headless).
- **`.deb` rebuilt** with the new code → `dist/pseek_0.1.0_all.deb`.

Quick re-check anytime:
```bash
cd ~/Desktop/PSEEK
python3 run_pseek.py --selfcheck        # expect local_gguf: True, tier: trial
```

---

## What's left — only things that need YOUR secrets/decisions

> Pick a **workspace passphrase** and a **user id** and use the SAME ones every
> time. Example uses `andrej`. Everything is stored **encrypted** in your vault.

```bash
export PSEEK_PASSPHRASE='choose-a-strong-passphrase'   # <-- set this first, every session
export PSEEK_USER='andrej'
```

### 1) Connect your email → send REAL applications  *(most important)*
Until you do this, "Apliciraj" only makes a **draft** (dry-run).

1. Make an **app password** (NOT your main password):
   - Gmail: 2-Step Verification → Google Account → Security → **App passwords** → copy the 16 chars.
   - Outlook/Zoho: enable 2FA → Security → **App passwords** → create.
2. Connect it:
```bash
cd ~/Desktop/PSEEK
python3 configure_user_email.py andrej your.email@gmail.com
# it will prompt for the app password (paste the 16 chars)
python3 configure_user_email.py --show andrej          # verify: email connected: True
```
(IMAP/SMTP auto-detected for Gmail/Outlook/Zoho. Other provider? prefix with
`PSEEK_IMAP_HOST=... PSEEK_SMTP_HOST=...`.)

### 2) (Optional) Free cloud LLM keys → richer chat/generation
Local GGUF already works, so this is optional. Add any FREE key you have:
```bash
python3 configure_source_key.py andrej groq_api_key      <YOUR_GROQ_KEY>
python3 configure_source_key.py andrej mistral_api_key   <YOUR_MISTRAL_KEY>
python3 configure_source_key.py andrej anthropic_api_key <YOUR_CLAUDE_KEY>
```
PSEEK uses them sparingly and falls back to local automatically. PII never leaves
the machine (pinned to local).

### 3) (SELLER — you) Square keys → real payments
Only needed to actually charge the $4.95 / $9.95 tiers. Until set, billing runs in
test mode (no charge). Use your **seller** id:
```bash
python3 configure_source_key.py andrej square_access_token <YOUR_SQUARE_TOKEN>
python3 configure_source_key.py andrej square_location_id  <YOUR_LOCATION_ID>
```

### 4) (Optional) More job sources
Free boards (RemoteOK, Remotive, Jobicy, Arbeitnow, WeWorkRemotely) are always on.
To add Adzuna / a keyed API / RSS / Greenhouse-Lever, edit
`sources_config.json` and store any key with:
```bash
python3 configure_source_key.py andrej my_jobs_api_key <YOUR_KEY>
```
(Then reference `my_jobs_api_key` under `user_apis` and add the host to `allow_hosts`.)

---

## Run the app
```bash
cd ~/Desktop/PSEEK
python3 run_pseek.py
```
Left nav · center content · right chat panel. Try in chat: `nađi poslove`,
`izvori`, `apliciraj 1`, `generiši rezime: …`.

## The two builds a Linux box CAN'T make (need their OS or CI)
- **Windows `.exe`:** on a Windows machine → `pip install pyinstaller pyside6` →
  `pyinstaller packaging/pseek.spec` (or run `packaging/build_exe.bat`). Guide: `guides/INSTALL-EXE-*`.
- **macOS `.app`:** on a Mac → `pyinstaller packaging/pseek.spec` (or `packaging/build_app.sh`).
  Guide: `guides/INSTALL-APP-*`.
- **`.deb`** is already built in `dist/`. Test it: `sudo dpkg -i dist/pseek_0.1.0_all.deb`.

---

## Recommended order
1. `export PSEEK_PASSPHRASE=... PSEEK_USER=...`
2. **Connect email** (step 1) → real applications.
3. Run the app, do a real search + one apply.
4. (Optional) cloud keys · (Seller) Square · more sources.
5. Later: build `.exe`/`.app` on Windows/macOS or CI.

Full detail per topic: `guides/GO-LIVE-EN.md`, `guides/CONNECT-EMAIL-EN.md`,
`guides/USING-EN.md`.
