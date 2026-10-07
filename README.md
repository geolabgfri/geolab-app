# Laboratorij za geotehniku — aplikacija

Streamlit aplikacija povezana sa Supabase (PostgreSQL) bazom.

## Stranice
| Stranica | Čemu služi |
|---|---|
| 📨 Zahtjev za opremu | podnošenje zahtjeva za korištenje uređaja |
| ✅ Odobravanje | voditelj/laborant odobrava zahtjeve za opremu i istraživačke projekte |
| 📥 Prijem uzorka | zaprimanje uzorka (projekt/klijent po potrebi u letu) |
| 🛠️ Prijava kvara | brza prijava kvara — uređaj ide `u_servisu` |
| ➕ Unos opreme | dodavanje novog uređaja u inventar |
| 🔧 Rješavanje kvarova | zatvaranje kvara — uređaj se vraća `u_uporabi` |
| 📝 Novi posao | otvaranje/dopuna posla: upit → ponuda → narudžbenica → izvještaj |
| 📊 Pregledi | iskorištenost opreme, poslovi, uzorci, kvarovi, istraživački projekti (+ izvoz CSV) |
| 🗂️ Prijedlog projekta | prijedlog istraživačkog projekta (HRZZ, JICA ...); aktivan tek nakon odobrenja |

## Promjene baze
SQL skripte su u mapi `sql/`, nazvane po verziji. Pokreću se jednom u
Supabase → SQL Editor, **prije** objave te verzije aplikacije.
- `sql/1.6.0_prijedlozi_projekata.sql` — tablica `prijedlozi_projekata` (zamijenjeno u 1.7.0)
- `sql/1.7.0_istrazivacki_projekti.sql` — `projekti` dobiva vrstu (`strucni` /
  `istrazivacki`), podatke istraživačkog projekta i `status_odobrenja`;
  `koristenje_opreme.projekt_id`

**Projekti — jedna tablica, dvije vrste** (`projekti.vrsta`):
- `strucni` — posao za klijenta, otvara se kroz *Novi posao* (upit → ponuda → …)
- `istrazivacki` — znanstveni projekt (HRZZ, NPOO, JICA …), predlaže se kroz
  *Prijedlog projekta*, odobrava u *Odobravanju*; klijent = financijer (tip `interni`)

Na oba se vežu uzorci (*Prijem uzorka*) i korištenje opreme (*Zahtjev za opremu*).
Oprema nabavljena na istraživačkom projektu: `oprema.projekt_nabave` = akronim projekta.

## Verzija
Postavlja se u `db.py` (`VERZIJA`). Vidi `CHANGELOG.md`.
