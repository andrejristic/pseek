# PSEEK — Kako se koristi

PSEEK vodiš **razgovorom** u chat panelu desno, ili preko tabova u sidebaru. On
pretražuje mnogo izvora poslova, spaja tvoje dokumente u najbolji **pošten** pitch
po poslu, aplicira za tebe i uči o tebi. **Ti donosiš odluke** — on radi sve ostalo.

## Tabovi (sidebar lijevo)
- **Dashboard** — θ mjerač (balans self/other) + pregled.
- **Poslovi** — rezultati pretrage kao tabela: verdikt · posao · firma · lokacija ·
  fit. Dvije **opt-in opcije** (obje ISKLJUČENE) i tri dugmeta (ispod).
- **Dokumenti** — tvoji rezimei i coveri (dodaj fajlove u `docs/` ili ih generiši u chatu).
- **Prijave** — životni ciklus svega na šta si aplicirao.
- **Strategija** — šta je sistem naučio: ishodi, najbolji izvori, tvoje preference.
- **Settings** — šta ubaciti (ključevi/email) + font (A− / A+, default 20) + tema.

## Chat komande (kucaj ih u desni panel)
| Komanda | Šta radi |
|---|---|
| `nađi poslove` | pretraži SVE izvore → puni Poslovi tab |
| `izvori` | lista izvora + koji ti najbolje rade |
| `lista` | prikaži trenutne rezultate |
| `zašto 3` | objasni posao #3 (verdikt, θ, fit, lokacija) |
| `apliciraj 2` | apliciraj na posao #2 (draft/slanje, iza tvog odobrenja) |
| `generiši rezime: činjenica1; činjenica2; …` | napravi pošten rezime iz tvojih činjenica → `docs/` |
| `generiši cover: …` | isto tako napravi cover letter |
| `dokumenti` / `prijave` / `strategija` | sažmi te tabove |

Sve ostalo ide LLM-u (ili lokalnoj podlozi ako model nije povezan).

## Apliciranje (iz Poslovi taba)
Izaberi posao → **✉ Apliciraj**. PSEEK sklopi najbolju **kombinaciju** tvojih
rezimea + pasusa covera za taj posao (pošteno — samo tvoje prave linije), pa:
- ako je email povezan → šalje s **tvoje** adrese (ovaj klik je tvoje odobrenje);
- ako nije → napravi **draft (dry-run)**, ništa se ne šalje.
Sve se bilježi u **Prijave**.

## Učenje (opt-in — ti ga pališ)
- **☐ Auto-pretraga** — PSEEK sam ponavlja pretragu na interval. ISKLJUČENO po defaultu.
- **☐ Uči iz mojih ocjena** — dugmad **✅ Odobri / ✕ Odbij** nagrađuju izvor i uče
  tvoje preference. ISKLJUČENO po defaultu; dok je isključeno, ta dugmad ne rade ništa.

## Sigurnost (uvijek uključena)
- **Istinito po konstrukciji** — svaka tvrdnja vuče na liniju tvog dokumenta; ne izmišlja.
- **Ti odlučuješ** — apliciranje, slanje, odgovaranje, plaćanje uvijek čekaju tvoj klik.
- **θ** drži svaki pitch u balansu (ne naduvava te, ne izvrće u poslodavčev wishlist).

Vidi **GO-LIVE-SR.md** za ključeve/naloge koje ubacuješ da otključaš punu snagu.
