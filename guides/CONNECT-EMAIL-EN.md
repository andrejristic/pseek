# PSEEK — Connect your email (user guide)

PSEEK applies for you **from your own email address**. To enable that, you connect
your email once. This guide tells you exactly what to do.

## Why it works this way
- Applications go from **your** address — the employer sees you, not a shared account.
- Your data stays **yours**: the password is stored **encrypted in your personal
  vault**; no one else (not us, not other users) can see it.
- **Nothing is sent without your approval** — you confirm every email.

## Step 1 — Create an "app password" (NOT your main password)
Don't use your main password. Create a dedicated app password:

- **Gmail:** turn on 2-Step Verification → Google Account → Security → *App
  passwords* → create one → copy the 16 characters.
- **Outlook/Hotmail:** enable 2FA → Security → *App passwords* → create.
- **Zoho:** Settings → Security → *App Passwords* → generate.

## Step 2 — Connect it in PSEEK
**In the app:** open **Settings → Connect email**, enter your address and the app
password. IMAP/SMTP hosts are detected **automatically** for Gmail/Outlook/Zoho.

**Or from the terminal** (same effect):
```bash
cd ~/Desktop/PSEEK
PSEEK_PASSPHRASE='your-workspace-passphrase' \
python3 configure_user_email.py your-id your.email@gmail.com
# you'll be prompted for the app password
python3 configure_user_email.py --show your-id     # verify
```
For a provider not on the list, set the hosts:
```bash
PSEEK_IMAP_HOST=imap.your.provider PSEEK_SMTP_HOST=smtp.your.provider ...
```

## Step 3 — Done
From now on PSEEK can **prepare** an application and, once you **approve** it, send
it from your address. You read employer replies inside the app.

## Security in one line
App password (not your main password) · encrypted in your vault · revocable at
your provider anytime · sending always behind your click (consent).

## Trouble?
- **"connect your email first"** → you haven't connected an email; redo Step 2.
- **Sending fails** → check the app password is correct and your provider allows
  SMTP; redo Step 1 if needed.

## What it enables
Once connected, the **✉ Apliciraj** button (and `apliciraj N` in chat) sends the
application from your address. Until then it prepares a draft (dry-run).
