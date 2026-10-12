# PSEEK — Dobro jutro ☀️  Šta je Claude uradio i šta OSTAJE tebi

Kratak spisak svega što ti (Andrej) treba da uradiš. Sve što je mašina mogla bez
tvojih privatnih ključeva je **već urađeno i provereno**. Svaki korak ispod je
kopiraj-nalepi. Pokreći iz `~/Desktop/PSEEK`.

---

## ✅ Urađeno preko noći (već radi, ovde nemaš šta da diraš)
- **Lokalni GGUF „radni konj" je AKTIVAN.** Instaliran `llama-cpp-python`; PSEEK
  sad **sam pronalazi model** bez ikakvog podešavanja (env → `PSEEK/models/` →
  `~/Downloads`). Trenutno pokazuje na
  `~/Desktop/2222/11/gut_ai/models/Qwen2.5-7B-Instruct-Q6_K.gguf`.
  `selfcheck` prikazuje `local_gguf: True`.
- **Svi testovi zeleni: 20/20 fajlova.** PSE kernel netaknut (bajt-identičan moat).
- **GUI se pokreće i sve je povezano** (provereno bez ekrana).
- **`.deb` rebuildovan** sa novim kodom → `dist/pseek_0.1.0_all.deb`.

Brza provera bilo kad:
```bash
cd ~/Desktop/PSEEK
python3 run_pseek.py --selfcheck        # očekuj local_gguf: True, tier: trial
```

---

## Šta ostaje — samo stvari koje traže TVOJE tajne/odluke

> Izaberi **lozinku workspace-a** i **user id** i koristi ISTE svaki put. Primer
> koristi `andrej`. Sve se čuva **šifrovano** u tvom vault-u.

```bash
export PSEEK_PASSPHRASE='izaberi-jaku-lozinku'   # <-- ovo prvo, u svakoj sesiji
export PSEEK_USER='andrej'
```

### 1) Poveži svoj mejl → šalji PRAVE prijave  *(najvažnije)*
Dok ovo ne uradiš, „Apliciraj" pravi samo **draft** (dry-run).

1. Napravi **app-password** (NE tvoja glavna lozinka):
   - Gmail: 2-Step Verification → Google nalog → Bezbednost → **App passwords** → kopiraj 16 znakova.
   - Outlook/Zoho: uključi 2FA → Bezbednost → **App passwords** → kreiraj.
2. Poveži ga:
```bash
cd ~/Desktop/PSEEK
python3 configure_user_email.py andrej tvoj.mejl@gmail.com
# tražiće app-password (nalepi 16 znakova)
python3 configure_user_email.py --show andrej          # provera: email connected: True
```
(IMAP/SMTP se auto-detektuju za Gmail/Outlook/Zoho. Drugi provajder? dodaj prefiks
`PSEEK_IMAP_HOST=... PSEEK_SMTP_HOST=...`.)

### 2) (Opciono) Besplatni cloud LLM ključevi → bogatiji chat/generisanje
Lokalni GGUF već radi, pa je ovo opciono. Dodaj bilo koji BESPLATAN ključ:
```bash
python3 configure_source_key.py andrej groq_api_key      <TVOJ_GROQ_KEY>
python3 configure_source_key.py andrej mistral_api_key   <TVOJ_MISTRAL_KEY>
python3 configure_source_key.py andrej anthropic_api_key <TVOJ_CLAUDE_KEY>
```
PSEEK ih koristi štedljivo i automatski pada na lokalni. PII nikad ne napušta
mašinu (zakačen za lokalni model).

### 3) (PRODAVAC — ti) Square ključevi → prava naplata
Potrebno samo da bi stvarno naplaćivao tarife $4.95 / $9.95. Dok nije setovano,
naplata je u test modu (bez naplate). Koristi svoj **prodavac** id:
```bash
python3 configure_source_key.py andrej square_access_token <TVOJ_SQUARE_TOKEN>
python3 configure_source_key.py andrej square_location_id  <TVOJ_LOCATION_ID>
```

### 4) (Opciono) Više izvora poslova
Besplatni boardovi (RemoteOK, Remotive, Jobicy, Arbeitnow, WeWorkRemotely) su uvek
uključeni. Za Adzuna / keyed API / RSS / Greenhouse-Lever, izmeni
`sources_config.json` i sačuvaj ključ sa:
```bash
python3 configure_source_key.py andrej my_jobs_api_key <TVOJ_KEY>
```
(Pa referenciraj `my_jobs_api_key` pod `user_apis` i dodaj host u `allow_hosts`.)

---

## Pokreni aplikaciju
```bash
cd ~/Desktop/PSEEK
python3 run_pseek.py
```
Levo meni · sredina sadržaj · desno chat panel. Probaj u chatu: `nađi poslove`,
`izvori`, `apliciraj 1`, `generiši rezime: …`.

## Dva builda koja Linux NE MOŽE da napravi (traže svoj OS ili CI)
- **Windows `.exe`:** na Windows mašini → `pip install pyinstaller pyside6` →
  `pyinstaller packaging/pseek.spec` (ili pokreni `packaging/build_exe.bat`). Vodič: `guides/INSTALL-EXE-*`.
- **macOS `.app`:** na Mac-u → `pyinstaller packaging/pseek.spec` (ili `packaging/build_app.sh`).
  Vodič: `guides/INSTALL-APP-*`.
- **`.deb`** je već napravljen u `dist/`. Testiraj: `sudo dpkg -i dist/pseek_0.1.0_all.deb`.

---

## Preporučen redosled
1. `export PSEEK_PASSPHRASE=... PSEEK_USER=...`
2. **Poveži mejl** (korak 1) → prave prijave.
3. Pokreni app, uradi pravu pretragu + jednu prijavu.
4. (Opciono) cloud ključevi · (Prodavac) Square · više izvora.
5. Kasnije: napravi `.exe`/`.app` na Windows/macOS ili CI.

Detaljno po temi: `guides/GO-LIVE-SR.md`, `guides/CONNECT-EMAIL-SR.md`,
`guides/USING-SR.md`.
