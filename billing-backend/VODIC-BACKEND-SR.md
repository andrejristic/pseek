# PSEEK backend — vodič za Andreja

Backend (`billing-backend/`, Cloudflare Worker `pseek-api`) čuva **sve tvoje tajne**: Square token,
LLM ključeve, ključ za potpis pretplata. Aplikacije (desktop i Android) nemaju nijednu od njih.

**Tajne koje je Claude već napravio:** SD kartica → `11CODE/pseek/PSEEK-BACKEND-TAJNE.txt`
(`ENTITLEMENT_SIGNING_KEY`, `ADMIN_TOKEN`). Napravi rezervnu kopiju u password manageru.

Redosled: **1 → 2 → 3** su potrebni da backend proradi. **4, 5, 6** radiš kad stigneš.
Do koraka 5 sve radi u **Square sandbox** test modu: niko ne plaća pravim novcem.

---

## 1. Cloudflare nalog i dva GitHub Secreta (oko 10 min)

1. Otvori **dash.cloudflare.com/sign-up**, registruj se sa **andrej.s.ristic@gmail.com** i potvrdi email.
2. **Account ID:** levo **Workers & Pages**. Desno piše **Account ID**: klikni da ga kopiraš.
3. **API token:** gore desno ikonica profila → **My Profile** → **API Tokens** → **Create Token** →
   pored šablona **Edit Cloudflare Workers** klikni **Use template** →
   *Account Resources*: **Include → tvoj nalog**; *Zone Resources*: **All zones** →
   **Continue to summary** → **Create Token** → **kopiraj token** (prikazuje se samo jednom).
4. GitHub: repo **andrejristic/pseek** → **Settings** → **Secrets and variables** → **Actions** →
   **New repository secret**, dva puta:
   - Name `CLOUDFLARE_API_TOKEN`, Secret: token iz koraka 3
   - Name `CLOUDFLARE_ACCOUNT_ID`, Secret: Account ID iz koraka 2
5. Javi Claudeu **„cloudflare spreman“**. On pokreće objavu i šalje ti **adresu backenda**
   (`https://pseek-api.<nešto>.workers.dev`).
   Ili sam: repo → **Actions** → **deploy-backend** → **Run workflow**. Adresa je u logu, pod „PSEEK backend URL“.

## 2. Tajne u Cloudflare (oko 5 min, posle prve objave)

**Workers & Pages** → **pseek-api** → **Settings** → **Variables and Secrets** → **Add**:

| Type | Name | Value |
|---|---|---|
| Secret | `ENTITLEMENT_SIGNING_KEY` | iz `PSEEK-BACKEND-TAJNE.txt` |
| Secret | `ADMIN_TOKEN` | iz `PSEEK-BACKEND-TAJNE.txt` |
| Text | `SQUARE_WEBHOOK_URL` | adresa backenda + `/square/webhook` |
| Text | `DEV_SHOW_CODE` | `1` (samo dok ne podesiš korak 3; kod se tada vidi u aplikaciji umesto da stigne mejlom) |

Posle svake izmene klikni **Deploy** (ili **Save and deploy**).

## 3. Resend: slanje kodova na email (oko 10 min + čekanje DNS-a)

1. **resend.com** → registracija sa andrej.s.ristic@gmail.com.
2. **Domains** → **Add Domain** → `zeravatech.ca`. Resend pokaže 2–3 DNS zapisa (TXT/MX).
3. Kod svog registrara domena (gde je zeravatech.ca) dodaj te DNS zapise, pa u Resend-u klikni **Verify**.
   Može da potraje od par minuta do nekoliko sati.
4. **API Keys** → **Create API Key** (*Sending access*) → kopiraj.
5. Cloudflare (kao u koraku 2): Secret `RESEND_API_KEY` = taj ključ. **Obriši `DEV_SHOW_CODE`.**

Kodovi stižu sa `PSEEK <noreply@zeravatech.ca>` (promena: Text promenljiva `MAIL_FROM`).

## 4. Square (kad nađeš lozinku)

1. **developer.squareup.com** → prijava tvojim Square nalogom → **Applications** → **+** → ime `PSEEK`.
2. Gore je prekidač **Sandbox / Production**. Prvo sve uradi u **Sandbox**-u:
   - **Credentials** → *Sandbox Access token* → Cloudflare Secret `SQUARE_ACCESS_TOKEN`
   - **Locations** → *Location ID* → Cloudflare Secret `SQUARE_LOCATION_ID`
   - **Webhooks** → **Subscriptions** → **Add subscription**:
     URL = adresa backenda + `/square/webhook`;
     događaji: `payment.updated`, `subscription.created`, `subscription.updated`, `invoice.payment_made`
     → **Save** → kopiraj **Signature key** → Cloudflare Secret `SQUARE_WEBHOOK_SIGNATURE_KEY`
3. Jednom pokreni pravljenje mesečnih planova (ili javi Claudeu):
   `PSEEK_BACKEND_URL=<adresa> python3 tools/pseek_admin.py setup-square`
4. Probna kupovina u aplikaciji sa Square test karticom `4111 1111 1111 1111`, bilo koji budući datum, CVV `111`.
5. **Pravi novac:** prebaci na **Production** i ponovi korak 2 sa *Production* vrednostima,
   promeni Text `SQUARE_ENV` na `production`, pa ponovo pokreni `setup-square`.
   Novac ide na bankovni račun povezan sa tvojim Square nalogom.

## 5. Tvoji LLM ključevi (kad hoćeš)

Cloudflare Secrets, bilo koji od ovih:
- `GROQ_API_KEY`: console.groq.com/keys
- `MISTRAL_API_KEY`: console.mistral.ai/api-keys
- `ANTHROPIC_API_KEY`: platform.claude.com/settings/keys

Claude model je podrazumevano `claude-opus-5-5` (Text `ANTHROPIC_MODEL` ga menja), sa uključenim
*server-side fallback*-om: ako model odbije zahtev, Anthropic ga automatski pokuša drugim modelom.
Redosled provajdera: Text `LLM_ORDER` (podrazumevano `groq,mistral,anthropic`).
Dnevni limit poziva po paketu: `trial 50`, `basic 100`, `pro 400`, `free 0`. Menjaš ga komandom ispod.

## 6. Komande za tebe („na naredbu“)

```bash
export PSEEK_BACKEND_URL=https://pseek-api.<nešto>.workers.dev
python3 tools/pseek_admin.py config                        # trenutna podešavanja
python3 tools/pseek_admin.py set-billing square            # square | google_play | off
python3 tools/pseek_admin.py set-limit pro 400             # dnevni AI limit za paket
python3 tools/pseek_admin.py user ana@example.com          # pogledaj kupca
python3 tools/pseek_admin.py grant ana@example.com pro 30  # poklon: 30 dana Pro
python3 tools/pseek_admin.py reset-device ana@example.com  # odveži uređaj (kad kupac zaglavi)
```
Komanda traži `ADMIN_TOKEN` (iz `PSEEK-BACKEND-TAJNE.txt`) i nigde ga ne čuva.

## Pravila koja backend sprovodi

- **Jedan uređaj po emailu.** Prijava na novom uređaju briše vezu sa starim; najviše 3 promene u 30 dana.
- **Probni period:** 24 h, jednom po emailu (ne resetuje se reinstalacijom).
- **Bez interneta** aplikacija radi do **72 h** sa poslednjom potpisanom pretplatom.
- **Kupovina:** mesečna pretplata (obnavlja se sama, otkazuje se iz aplikacije) ili jednokratnih 30 dana.
  Aktivira se sama, kad Square javi uplatu (potpisani webhook).
