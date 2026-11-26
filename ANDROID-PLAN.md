# PSEEK — plan: popravka naplate, backend, LLM opcije, Android (APK)

**Cilj:** PSEEK na Android telefonu i Chromebooku: pretraga poslova u pozadini, obaveštenja,
prijave koje se šalju **tek kad ih odobriš** (Physician kartice), tvoj email, učenje preferencija,
LLM po izboru (lokalni GGUF ili online). Desktop (`.deb` / `.exe`) dobija iste popravke naplate
i LLM opcija. Prvo APK (GitHub Releases + repo `andrejristic/APK`), kasnije Google Play.

**Polazno stanje:** ~5000 linija Pythona, skoro sve standardna biblioteka (`urllib`, `smtplib`,
`imaplib`; PDF i DOCX čitanje bez dodatnih paketa; trezor radi i bez `cryptography`). 79 testova.
Interfejs je PySide6 (desktop), a to na Androidu ne radi.

**Pristup:** Python jezgro ostaje i radi unutar aplikacije preko **Chaquopy**-ja. Novi interfejs
je u Kotlinu (Jetpack Compose). Ključ za potpisivanje i CI isti kao kod Attack Mappera.

> **Status (2026-11-26):** faza **B** (backend) gotova, 14 testova; faza **P** (Python jezgro)
> gotova, 32 nova testa + svi postojeći prolaze. Backend čeka tvoj Cloudflare nalog
> (`billing-backend/VODIC-BACKEND-SR.md`). Ostaje za P: ekran za prijavu / „Vrati kupovinu“ /
> „Otkaži“ u desktop GUI-ju (logika postoji, fali dugme). Zatim faze A i L.

---

## Odluke (Andrej, 2026-11-25)

| # | Tema | Odluka |
|---|---|---|
| 1 | Backend | **Cloudflare Worker** (besplatan plan) |
| 2 | LLM | **Što više opcija:** lokalni GGUF na telefonu (provera hardvera + preporuka modela) i online (tvoji ključevi preko backenda + korisnikovi ključevi + bilo koji OpenAI-kompatibilan URL) |
| 3 | Square | **Obe opcije:** automatska mesečna pretplata i jednokratna uplata za 30 dana |
| 4 | Vraćanje kupovine | **Vezano za email kupca, aktivno na samo jednom uređaju.** Aktivacija na novom uređaju briše vezu sa prethodnim. |
| 5 | Probni period | 24 h ostaje, vezan za email (ne resetuje se reinstalacijom) |
| 6 | Package name | Šema **`ca.andrej_zeravatech.<ime>`**: PSEEK = `ca.andrej_zeravatech.pseek`; Attack Mapper se usklađuje na `ca.andrej_zeravatech.attackmapper` pre `v1.0.0` |
| 7 | Redosled | **B + P** (backend i naplata, radi i za desktop) → **A + L** (Android i LLM) → **G** (Google Play) |
| — | Cene | Basic **$4.95** / Pro **$9.95** mesečno (postojeći `billing/entitlements.py`) |

---

## ⚠️ Šta se popravlja i zašto (važi i za desktop)

1. **Square token prodavca je u aplikaciji** (`billing/square.py`). Svako ko izvuče APK dobija
   pristup tvom Square nalogu. Na desktopu kupci ionako **ne mogu da plate**: token postoji
   samo u tvom trezoru, pa njihova kopija ostaje u „test modu“.
2. **Tvoji LLM ključevi su u aplikaciji** (PLAN.md §3b). Neko ih izvuče i troši tvoju kvotu.
3. **`idempotency_key` je isti za sve kupce** (`pseek-pro`), pa bi Square svima vraćao isti checkout.

**Rešenje:** backend drži sve tvoje tajne. Aplikacija nikad ne vidi Square token ni tvoje LLM ključeve.

---

## Faza B: backend (Cloudflare Worker)

| # | Zadatak |
|---|---|
| B1 | `billing-backend/` u repou: Worker + KV skladište, deploy preko GitHub Actions |
| B2 | `POST /checkout`: Square checkout sa **jedinstvenim** ključem; **dve opcije**: mesečna pretplata (Square Subscriptions) i jednokratnih 30 dana |
| B3 | `POST /square/webhook`: proverava Square potpis (HMAC) i **sam aktivira** pretplatu za email kupca |
| B4 | `POST /cancel`: otkazivanje mesečne pretplate iz aplikacije |
| B5 | **Jedan uređaj po emailu:** `POST /restore` šalje šestocifreni kod na email; `POST /restore/verify` vezuje pretplatu za **novi uređaj i briše vezu sa starim**. Stari uređaj pri sledećoj proveri pada na Free. Podrazumevano najviše 3 promene uređaja mesečno, podesivo. |
| B6 | `GET /entitlement`: pretplata **potpisana** (Ed25519), važi offline **72 h** (podesivo), pa se ponovo proverava. Aplikacija proverava potpis javnim ključem. |
| B7 | **Probni period vezan za email:** 24 h jednom po emailu |
| B8 | `POST /llm`: posrednik ka Groq / Mistral / Claude… sa **tvojim** ključevima; dnevni limit po paketu (Free / Basic / Pro) |
| B9 | `GET /config`: **prekidač za naplatu** (`square` / `google_play` / `off`) i limiti; menjaš bez nove verzije aplikacije |
| B10 | Slanje kodova emailom preko **Resend**-a (besplatno do 3000 mesečno) |
| B11 | **Upis tajni bez koda:** Cloudflare dashboard → Worker → **Settings → Variables and Secrets → Add**. Kad nađeš Square podatke, samo ih upišeš. Do tada sve radi u Square **sandbox** test modu. |
| B12 | Testovi: Square sandbox, lažni webhook, potpisi, promena uređaja, limiti |

## Faza P: Python jezgro (desktop + mobilni)

| # | Zadatak |
|---|---|
| P1 | `billing/providers.py`: zajednički interfejs, provajderi `square` (preko backenda), `google_play` (preko Androida), `off` |
| P2 | `billing/square.py` bez tokena; poziva backend. Ispravljen `idempotency_key`. |
| P3 | `EntitlementManager`: potpisana pretplata sa backenda, offline period, „Vrati kupovinu“ (email + kod), paywall sa obe Square opcije |
| P4 | `llm/backends.py`: `ProxyBackend` (backend sa tvojim ključevima) + katalog korisnikovih provajdera (faza L) |
| P5 | Svih 79 postojećih testova + novi za naplatu, vraćanje kupovine i LLM |
| P6 | Desktop `.deb` i `.exe` sa istim popravkama; ažurirani `GO-LIVE` vodiči (SR/EN) |

## Faza A: Android aplikacija

| # | Zadatak |
|---|---|
| A1 | `android/` projekat: Chaquopy (Python 3.11) + Compose, `ca.andrej_zeravatech.pseek`, minSdk 26 |
| A2 | Kotlin ↔ Python most: pretraga, rangiranje, sinteza, prijava, chat, pretplata |
| A3 | Trezor: lozinka trezora se generiše nasumično i čuva u **Android Keystore**-u (korisnik je ne kuca) |
| A4 | Ekrani: **Poslovi** (lista, filteri, ocena), **Dokumenti** (CV / pismo preko Android birača fajlova; PDF i DOCX), **Prijave**, **Chat**, **θ merač**, **Podešavanja** |
| A5 | **Physician kartice:** svaka odluka (prijava, slanje maila, odgovor poslodavcu, prihvatanje ponude, kupovina, povezivanje emaila) je kartica sa **Odobri / Odbij** |
| A6 | **Pretraga u pozadini** (WorkManager, na primer na svakih 6 h) + obaveštenje „3 nova posla, 1 prijava čeka odobrenje“ |
| A7 | Povezivanje emaila (SMTP/IMAP sa app lozinkom, postojeći `mailarm`) |
| A8 | Paywall: Basic / Pro, mesečno ili 30 dana; Square checkout u browseru; aktivacija sama (webhook); **Vrati kupovinu**; **Otkaži pretplatu** |
| A9 | Jezik SR/EN sa prekidačem |
| A10 | Mode 2 (asistent na poslu) |
| A11 | CI: Python testovi + build + potpis, APK i AAB, release, link u repou APK |
| A12 | `VODIC-SR.md` sa svim tvojim koracima (kopija u `11CODE/pseek/`) |

## Faza L: LLM, što više opcija

| # | Zadatak |
|---|---|
| L1 | **Provera hardvera** pri prvom pokretanju i u Podešavanjima: RAM, slobodan prostor, procesor (ABI, jezgra, SoC), Vulkan/GPU, baterija |
| L2 | **Preporuka lokalnog modela** po hardveru, na primer: <4 GB RAM → ~0.5B (≈0.4 GB); 4–6 GB → 1–1.5B (≈1 GB); 8 GB → 3–4B (≈2–2.5 GB); 12 GB+ → 7–8B (≈4.5 GB). Prikaz očekivane brzine i veličine, upozorenje ako model ne staje |
| L3 | **Lokalni GGUF na telefonu:** llama.cpp preko JNI-ja (build u CI-ju sa NDK-om), preuzimanje na zahtev (nastavak prekinutog preuzimanja, SHA-256 provera), katalog proverenih modela + „dodaj svoj GGUF fajl“ |
| L4 | **Online, tvoji ključevi preko backenda** (B8), sa dnevnim limitom po paketu |
| L5 | **Online, korisnikov ključ:** Groq, Gemini, Mistral, OpenRouter, Claude, OpenAI, xAI, DeepSeek i **bilo koji OpenAI-kompatibilan URL** (pokriva Ollama / LM Studio na kućnom računaru preko Wi-Fi-ja). Katalog iz Divide Readera (`providers/catalog.py`). |
| L6 | **Rutiranje:** postojeće rutiranje po kvotama + automatska zamena; lični podaci idu lokalnom modelu kad postoji; Guardian redakcija pre svakog cloud poziva |
| L7 | Isti izbor LLM-a i na desktopu (lokalni GGUF tamo već postoji) |
| L8 | Licence modela prikazane pre preuzimanja |

## Faza G: Google Play (kasnije)

- Play build ima **samo Google Play Billing** (Play ne dozvoljava Square za digitalne pretplate);
  APK van Play-a ima Square. Prekidač iz B9 bira među dozvoljenima za taj build.
- Basic i Pro postaju Play pretplate; backend proverava Play kupovine. Pravilo „jedan uređaj
  po emailu“ važi i tu.
- Zatvoreno testiranje: 12 testera tokom 14 dana.

## Usklađivanje Attack Mappera (mali zadatak, pre njegovog `v1.0.0`)

- `ca.zeravatech.attackmapper` → **`ca.andrej_zeravatech.attackmapper`**, nov test build.
  Već instalirana test verzija (`…attackmapper.test`) mora se obrisati ručno, jer je to sada druga aplikacija.

---

## Šta radi Andrej

| Kada | Šta | Vreme |
|---|---|---|
| Pre faze B | **Cloudflare nalog** (besplatan) na andrej.s.ristic@gmail.com; Claude daje uputstvo i API token koji ide u GitHub Secrets repoa `pseek` | ~10 min |
| Pre faze B | **Resend nalog** (besplatan) za slanje kodova; API ključ ide u Cloudflare | ~5 min |
| Kad nađeš lozinku | **Square podaci:** *Access token*, *Location ID*, *Webhook signature key* → Cloudflare (B11). Do tada radi sandbox. | ~10 min |
| Kad hoćeš | **Tvoji LLM ključevi** (Groq / Mistral / Claude…) → Cloudflare | ~5 min |
| Pre `v1.0.0` | 4 tajne za potpisivanje u repou `pseek` (iste vrednosti kao za Attack Mapper) | ~10 min |
| Posle builda | Test na telefonu po checklisti iz `VODIC-SR.md` | ~45 min |

## Okvirno trajanje (Claude)

| Faza | Vreme |
|---|---|
| B + P (backend, naplata, desktop) | 4–6 h |
| A (Android) | 10–14 h |
| L (LLM opcije, lokalni GGUF na telefonu) | 5–8 h |
| Usklađivanje Attack Mappera | ~30 min |
| **Ukupno** | **oko 20–28 h rada, 3–4 dana sa čekanjem na CI** |

**Pravilo za fajlove:** repo se razvija u `~/Git/pseek`; sve što se generiše (APK, ključevi,
tajne, vodiči) ide u `/sdcard-storage/11CODE/pseek/`. Ništa se ne instalira lokalno.
