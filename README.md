# Laboratorij za geotehniku — aplikacija

Streamlit aplikacija povezana sa Supabase (PostgreSQL) bazom.
Ulazna datoteka: **`Pocetna.py`** (gradi izbornik prema ulozi prijavljene osobe).

## Stranice
| Stranica | Čemu služi | Tko vidi |
|---|---|---|
| 📨 Zahtjev za opremu | podnošenje zahtjeva za korištenje uređaja (po želji vezano uz projekt) | svi |
| 👤 Moj pregled | moji zahtjevi (podnositelj ili provoditelj), statusi, matrica korištenja po danima | prijavljeni |
| 🛠️ Prijava kvara | brza prijava kvara — uređaj ide `u_servisu` | svi |
| 🗂️ Upis projekta | upis istraživačkog projekta (HRZZ, NPOO, JICA ...) sa suradnicima | admin, zvanje |
| ✅ Odobravanje | zahtjevi za opremu (odbijeni se brišu) i istraživački projekti | admin |
| 📥 Prijem uzorka | zaprimanje uzorka na odobreni projekt | admin |
| ➕ Unos opreme | dodavanje novog uređaja u inventar | admin |
| 🔧 Rješavanje kvarova | zatvaranje kvara — uređaj se vraća `u_uporabi` | admin |
| 📝 Novi posao | stručni posao: upit → ponuda → narudžbenica → izvještaj | admin |
| 📊 Pregledi | oprema, poslovi, uzorci, kvarovi, istraživački projekti (+ izvoz CSV) | admin |

## Uloge
Stupci u tablici `osoblje` (kvačica u Supabase Table Editoru; vrijedi od sljedeće prijave):

| Stupac | Tko | Što dobiva |
|---|---|---|
| — (bez prijave) | svi | Zahtjev za opremu, Prijava kvara |
| `znanstveno_zvanje` | doc., izv. prof., prof. | + Upis projekta; može biti voditelj projekta |
| `administrator` | voditelj, laborant | + Upis projekta i sve administrativne stranice |

Stranice bez ovlasti ne vide se u izborniku; svaka zaštićena stranica i sama provjerava
ulogu (`auth.trazi_prijavu`).

## Secrets (Streamlit Cloud → App → Settings → Secrets)
```toml
[supabase]
host = "aws-1-eu-west-2.pooler.supabase.com"
port = "5432"
dbname = "postgres"
user = "postgres.xxxxxxxx"
password = "LOZINKA"

[email]                       # nije obavezno
sender = "posiljatelj@gmail.com"
app_password = "GOOGLE-APP-PASSWORD"
recipients = ["voditelj@...", "laborant@..."]

[pristup]                     # svaka osoba svoju lozinku
"Vedran Jagodnik" = "lozinka"
"Juraj Stella"    = "lozinka"
"Ime Prezime"     = "lozinka"
```
**Ime u `[pristup]` mora biti TOČNO kao u tablici `osoblje`** — po njemu se čitaju uloge
i bilježi tko je odobrio / riješio.

## E-mail obavijesti
Zahtjev za opremu, Prijava kvara i Upis projekta šalju obavijest automatski pri spremanju
(`obavijest.py`): primatelji su `[email] recipients`, a kopiju dobivaju uključene osobe
prema stupcu `osoblje.email` (pravilo `ime.prezime@gradri.uniri.hr`; iznimke ručno).

## Projekti — jedna tablica, dvije vrste (`projekti.vrsta`)
- `strucni` — posao za klijenta, otvara se kroz *Novi posao*
- `istrazivacki` — znanstveni projekt, upisuje se kroz *Upis projekta*, odobrava u
  *Odobravanju*; klijent = financijer (tip `interni`); voditelj i suradnici u `projekt_suradnici`

Na oba se vežu uzorci (*Prijem uzorka*) i korištenje opreme (*Zahtjev za opremu*).
Oprema nabavljena na istraživačkom projektu: `oprema.projekt_nabave` = akronim projekta.

## Korištenje opreme — tko je tko (`koristenje_opreme`)
| Stupac | Značenje |
|---|---|
| `podnositelj` | ime osobe koja podnosi zahtjev i odgovara za njega (tekst) |
| `provoditelj` | ime osobe koja radi na uređaju, ako nije podnositelj (tekst; prazno = podnositelj) — može biti i vanjska osoba (student, doktorand) |
| `osoba_id` | provoditelj pokusa kao veza na `osoblje.id`; popunjava se automatski, prazno za vanjske osobe. Koristi se za provjere po osobi (npr. suradnici na projektu u `projekt_suradnici`) |
| `odobrio`, `datum_odobrenja` | tko je i kada odobrio zahtjev |
| `vrijeme_od`, `vrijeme_do`, `sati_koristenja` | stvarno vrijeme korištenja (po potrebi ispravljeno u Odobravanju) |
| `plan_vrijeme_od`, `plan_vrijeme_do` | prvotno planirano vrijeme iz zahtjeva — popunjava se tek pri prvom ispravku trajanja |
| `izmijenio`, `datum_izmjene` | tko je i kada ispravio trajanje |

Odbijeni zahtjevi se brišu; u tablici ostaju samo zahtjevi na čekanju i odobreni.
Vrijeme se sprema kao hrvatsko vrijeme (Europe/Zagreb).

## Promjene baze
SQL skripte su u mapi `sql/`. Pokreću se jednom u Supabase → SQL Editor, **prije**
objave te verzije aplikacije. Skripte prije prenumeriranja zadržale su stara imena.
- `sql/1.6.0_prijedlozi_projekata.sql` (= 0.6.0) — zamijenjeno u 0.7.0
- `sql/1.7.0_istrazivacki_projekti.sql` (= 0.7.0) — vrste projekata, `status_odobrenja`,
  `koristenje_opreme.projekt_id`
- `sql/0.8.0_uloge_i_suradnici.sql` — uloge u `osoblje`, tablica `projekt_suradnici`
- `sql/0.8.1_beta_oznaka.sql` — stupac `beta` (novi zapisi u prijelaznom razdoblju = testni)
- `sql/0.8.2_brisanje_odbijenih.sql` — jednokratno brisanje ranije odbijenih zahtjeva (po želji)
- `sql/0.8.3_sazetak_projekta.sql` — stupac `projekti.sazetak`
- `sql/0.8.4_faza_u_tijeku.sql` — faza `u_tijeku` za istraživačke projekte
- `sql/0.9.0_provoditelj_i_email.sql` — `koristenje_opreme.provoditelj`, `osoblje.email`
- `sql/0.9.1_ispravak_trajanja.sql` — ispravak trajanja, popravak vremenske zone
- `sql/1.0.0_kraj_bete.sql` — **pokrenuti tek kod prelaska na 1.0.0**

## Verzija
Postavlja se u `db.py` (`VERZIJA`). Vidi `CHANGELOG.md`.
**0.x.x = razvojna faza (BETA)**; 1.0.0 bit će prva službena, javna verzija.
Dok traje beta, svaki novi zapis u bazi ima `beta = TRUE`; pri prelasku na 1.0.0
(`sql/1.0.0_kraj_bete.sql`) odlučuje se hoće li se ti zapisi zadržati ili obrisati.
