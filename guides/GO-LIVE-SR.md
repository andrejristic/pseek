# PSEEK — Go-live checklist (šta ubacuješ)

PSEEK radi odmah na besplatnim izvorima, lokalnom/heurističkom modelu, dry-run
apliciranju i Square test-modu. Da otključaš punu snagu, ubaci svoje ključeve/naloge.
Sve se čuva **šifrovano u tvom workspace vaultu** — ništa se ne dijeli.

Koristi istu **workspace lozinku** svaki put:
```bash
export PSEEK_PASSPHRASE='tvoja-jaka-lozinka'
```

## 1) Poveži svoj email (da se prijave stварно ŠALJU)
Tvoja adresa; apliciraš s nje. Vidi **CONNECT-EMAIL-SR.md**.
```bash
python3 configure_user_email.py <user-id> ti@gmail.com
```
Dok nije povezan, „Apliciraj" pravi **draft** (dry-run).

## 2) LLM ključ ili lokalni model (bogatiji chat + generisanje)
Opciono — bez toga radi lokalna/heuristička podloga. Dodaj **besplatan** ključ ILI GGUF:
```bash
# besplatan online ključ (biraš jedan)
python3 configure_source_key.py <user-id> groq_api_key   <TVOJ_GROQ_KLJUC>
python3 configure_source_key.py <user-id> mistral_api_key <TVOJ_MISTRAL_KLJUC>
python3 configure_source_key.py <user-id> anthropic_api_key <TVOJ_CLAUDE_KLJUC>
# ili lokalni GGUF model (radi offline; PII nikad ne napušta mašinu)
export PSEEK_GGUF_MODEL=/putanja/do/model.gguf
```
PSEEK štedljivo koristi besplatni cloud i automatski pada na lokalni.

## 3) Više izvora poslova (opciono)
Besplatni boardovi su uvijek uključeni. Dodaj:
- **User-defined keyed API** (LinkedIn/Indeed preko tvog RapidAPI/SerpAPI, Adzuna…):
  sačuvaj svoj ključ, pa ga referenciraj u `sources_config.json` pod `user_apis`
  (ili `adzuna_app_id`/`adzuna_app_key`), i dodaj host pod `allow_hosts`.
  ```bash
  python3 configure_source_key.py <user-id> my_jobs_api_key <TVOJ_KLJUC>
  ```
- **RSS feedovi** (npr. HigherEdJobs) — dodaj pod `rss` u `sources_config.json`.
- **Greenhouse/Lever** company boardovi — dodaj slugove pod `greenhouse`/`lever`.

## 4) Square (samo prodavac — stварna naplata)
Samo prodavac ovo postavlja, app-side, da naplaćuje nivoe $4.95 / $9.95:
```bash
python3 configure_source_key.py <seller-id> square_access_token <TOKEN>
python3 configure_source_key.py <seller-id> square_location_id  <LOCATION_ID>
```
Do tada entitlements rade u test-modu (bez naplate). Kupovina je uvijek korisnikova
eksplicitna odluka.

## Smislen redoslijed
1. Poveži email → stварne prijave. 2. (Opciono) LLM ključ/GGUF → pametniji chat.
3. (Opciono) source ključevi → više poslova. 4. (Prodavac) Square → naplata.
