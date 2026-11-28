# PSEEK — Android APK (grana `pseek-apk`)

## Status (2026-11-28)

- **Test APK:** [`pseek-0.1.0-test.apk`](https://github.com/andrejristic/pseek/releases/download/v0.1.0-test/pseek-0.1.0-test.apk) (72,6 MB) — već je u [APK indeksu](https://github.com/andrejristic/APK).
- CI: `build-apk` zelen (Python testovi jezgra + Gradle build); lokalna kopija APK-a je u `apk-artifacts/`.
- Potpisani `v1.0.0` i backend idu na kraju, kad ti upišeš tajne.

Ovo je **zasebna APK verzija** PSEEK-a. Originalni `main` i grana `mobile-billing`
ostaju netaknuti. Sav rad za APK nalazi se u folderu `/home/a/Desktop/pseek-apk`
i (kad se objavi) na grani `pseek-apk` repoa `andrejristic/pseek`.

## Šta je urađeno

- **Faza A — Android ljuska:** `android/` — Kotlin + Jetpack Compose, Chaquopy
  (Python 3.11), `ca.andrej_zeravatech.pseekapk`, minSdk 26, ABI `arm64-v8a` i `x86_64`.
  PySide6 GUI se ne pakuje; zamenjen je Compose ekranima.
- **Python most:** `android/app/src/main/python/mobile_api.py` — ~30 funkcija nad
  postojećim PSEEK jezgrom (pretraga, dokumenti, sinteza, prijave, chat, napлата).
  Jezgro je ostalo **stdlib-only**, tako da Chaquopy ne treba nijedan pip paket.
- **A13 — prvo pokretanje / Podešavanja:** backend URL se upisuje u aplikaciji
  (ne u rep), radi i prazan → *test režim*; tu su i tvoj LLM ključ (u Android
  Keystore trezoru), email za prijave, „Vrati kupovinu“ i „Otkaži pretplatu“.
- **A3:** lozinka trezora se generiše nasumično i čuva u Android Keystore-u —
  korisnik je ne kuca.
- **A5:** Physician kartice — svaka prijava i kupovina traži eksplicitno
  **Odobri / Odbij**.
- **A6:** WorkManager pretraga svakih 6 h + notifikacija.
- **A9:** SR/EN prekidač i tamna tema.
- **Faza L:** `android/scripts/fetch-llama.sh` preuzima ARM64 `llama-server` u
  `jniLibs`; Kotlin ga pokreće na `127.0.0.1:8765`, a Python koristi
  OpenAI-kompatibilan HTTP most (`AndroidLlamaBackend`). Preporuka modela po RAM-u.
  Ništa ne napušta telefon.
- **CI:** `.github/workflows/build-apk.yml` — testovi jezgra, test APK na svakom
  pushu u `pseek-apk`, potpisani APK + AAB na tagu `vX.Y.Z`.

## Šta je ostalo za tebe (na kraju)

1. Cloudflare nalog + Resend nalog (~15 min) — deploy backenda.
2. Square token / Location ID / webhook secret u **Cloudflare dashboard**
   (~10 min) — ne u APK, ne u GitHub. Dok ih nema, Worker je u sandboxu.
3. Tvoji LLM ključevi u Cloudflare (~5 min).
4. 4 signing secret-a u repo `pseek` (~10 min) — **samo pre potpisanog `v1.0.0`**.
   Test APK se gradi sa throwaway debug ključem i ne traži ih.
5. Instalacija test APK-a i proba: 1) dodaj CV, 2) nađi poslove, 3) pripremi
   prijavu → Odobri, 4) uključi lokalni model ako je GGUF preuzet.

## Kako se gradi

Lokalno nema Android SDK-a — koristi se GitHub Actions:

```bash
git checkout -b pseek-apk            # od mobile-billing
git push -u origin pseek-apk         # CI pravi test APK u artifacts
git tag v0.1.0-test && git push origin v0.1.0-test   # APK u Releases
```

APK se zatim sam pojavljuje u [andrejristic/APK](https://github.com/andrejristic/APK).
Ako je repo i dalje privatan za CI ili želiš drugačije ime granе, javi — workflow
se lako prilagođava.

## Napomene

- Bez backend-a: 24h probni period radi lokalno, naplate nema, heuristički LLM
  održava aplikaciju funkcionalnom. To je namerna „local test mode“ varijanta.
- `pseek` ima postojeće Release objekte sa `.deb`/`.exe` — APK indeks gleda
  samo `.apk`, pa se ne mešaju.
- Play verzija (Google Play Billing) je zaseban kasniji korak; ovaj APK koristi
  Square samo kad je backend povezan.
