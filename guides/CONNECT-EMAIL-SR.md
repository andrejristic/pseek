# PSEEK — Poveži svoj email (vodič za korisnika)

PSEEK aplicira za tebe **sa tvoje vlastite email adrese**. Da bi to radilo, jednom
povežeš svoj email. Ovaj vodič ti kaže tačno šta da uradiš.

## Zašto ovako
- Prijave idu s **tvoje** adrese — poslodavac vidi tebe, ne neki zajednički nalog.
- Tvoji podaci su **samo tvoji**: lozinka se čuva **šifrovano u tvom ličnom
  sejfu (vault)**; niko drugi (ni mi, ni drugi korisnici) je ne vidi.
- **Ništa se ne šalje bez tvog odobrenja** — svaki mejl potvrđuješ ti.

## Korak 1 — Napravi „app password" (NE glavnu lozinku)
Ne koristiš svoju glavnu lozinku. Umjesto toga napraviš poseban „app password":

- **Gmail:** uključi 2-koračnu verifikaciju → Google nalog → Security → *App
  passwords* → napravi novi → iskopiraj 16 znakova.
- **Outlook/Hotmail:** uključi 2FA → Security → *App passwords* → kreiraj.
- **Zoho:** Settings → Security → *App Passwords* → generiši.

## Korak 2 — Poveži email u PSEEK-u
**U aplikaciji:** otvori **Settings → Connect email**, unesi adresu i app password.
Hostovi (IMAP/SMTP) se **automatski** prepoznaju za Gmail/Outlook/Zoho.

**Ili iz terminala** (isti efekat):
```bash
cd ~/Desktop/PSEEK
PSEEK_PASSPHRASE='tvoja-workspace-lozinka' \
python3 configure_user_email.py tvoj-id tvoj.email@gmail.com
# app password uneseš na upit
python3 configure_user_email.py --show tvoj-id     # provjera
```
Ako koristiš provajdera koji nije na listi, zadaj hostove:
```bash
PSEEK_IMAP_HOST=imap.tvoj.provajder PSEEK_SMTP_HOST=smtp.tvoj.provajder ...
```

## Korak 3 — Gotovo
Od sada PSEEK može da **pripremi** prijavu i, kad je ti **odobriš**, pošalje je s
tvoje adrese. Odgovore poslodavca čitaš u aplikaciji.

## Sigurnost ukratko
- App password (ne glavna lozinka) · šifrovan u tvom vaultu · možeš ga opozvati
  kod provajdera bilo kad · slanje uvijek iza tvog klika (consent).

## Problem?
- **„connect your email first"** → nisi povezao email; ponovi Korak 2.
- **Slanje ne prolazi** → provjeri da je app password ispravan i da provajder
  dozvoljava SMTP; probaj ponovo Korak 1.

## Šta omogućava
Kad povežeš, dugme **✉ Apliciraj** (i `apliciraj N` u chatu) šalje prijavu s tvoje
adrese. Do tada pravi draft (dry-run).
