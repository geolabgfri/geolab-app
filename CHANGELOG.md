# Dnevnik verzija — Laboratorij za geotehniku

Verzija se postavlja u `db.py` (`VERZIJA`, `DATUM_VERZIJE`)
i prikazuje se u bočnoj traci na svakoj stranici.

Format: `glavna.manja.zakrpa`
- **zakrpa** (1.0.**X**) — popravak sitnice
- **manja** (1.**X**.0) — nova funkcija ili stranica
- **glavna** (**X**.0.0) — veća promjena strukture baze

---

## 1.7.0 — 2026-10-07
- **Istraživački projekti u postojećoj tablici `projekti`** — nova vrsta projekta
  (`strucni` / `istrazivacki`); klijent tipa `interni` je financijer (npr. NPOO za REMOK).
  REMOK (`NPOO-2026-REMOK`) označen kao istraživački
- **🗂️ Prijedlog projekta** — prijedlog istraživačkog projekta: akronim, naziv, financijer,
  šifra, voditelj, trajanje, opis; čeka odobrenje (`status_odobrenja = na_cekanju`)
- **✅ Odobravanje** — kartica *Istraživački projekti*: potvrda oznake i akronima, odobri /
  odbij; aktivni se mogu označiti završenima (faza `zavrseno`)
- **📨 Zahtjev za opremu** — po želji se bira projekt za koji se ispitivanje radi
  (`koristenje_opreme.projekt_id`); oprema može biti nabavljena na drugom projektu
- **➕ Unos opreme** — projekt nabave nudi i akronime odobrenih istraživačkih projekata
- **📥 Prijem uzorka** — nudi samo odobrene, nezavršene projekte (stručne i istraživačke)
- **📝 Novi posao** i **📊 Pregledi → Poslovi** — samo stručni poslovi
- **📊 Pregledi** — kartica *Istraživački projekti*: nabavljena oprema, korištenja, sati,
  uzorci po projektu + detalji i CSV
- Baza: `sql/1.7.0_istrazivacki_projekti.sql`; tablica `prijedlozi_projekata` iz 1.6.0
  se briše

## 1.6.0 — 2026-10-07  *(zamijenjeno u 1.7.0)*
- Nova stranica **🗂️ Prijedlog projekta** (bez prijave) — osoba s popisa
  `osoblje` predlaže projekt: naziv, predložena oznaka, gradilište, opis,
  klijent postojeći ili novi; prijedlog ide u `prijedlozi_projekata` sa statusom `na_cekanju`
- **✅ Odobravanje** podijeljeno na kartice: *Zahtjevi za opremu* i *Prijedlozi projekata*;
  pri odobrenju se određuje konačna oznaka, projekt se otvara u `projekti`
  (novi klijent se stvara ako ne postoji), bilježi se tko je odlučio, kada i napomena
- Početna upozorava na prijedloge projekata na čekanju
- Baza: `sql/1.6.0_prijedlozi_projekata.sql` (nova tablica; postojeće se ne mijenjaju)

## 1.5.0 — 2026-07-14
- Nova stranica **📝 Novi posao** — cijeli tok posla (upit → ponuda → narudžbenica →
  izvještaj) s brojem, datumom i **linkom na dokument**; klijent postojeći ili novi;
  postojeći posao se može **dopuniti** (npr. kad stigne narudžbenica)
- Nova stranica **📊 Pregledi** — iskorištenost opreme (sati, broj korištenja),
  poslovi po fazi, uzorci, kvarovi po uređaju; grafovi + **izvoz u CSV**
- Pregled **upozorava na umjeravanje** koje istječe u sljedećih 60 dana
- Razdoblje pregleda: brzi izbor (**ovaj/prošli mjesec, ova/prošla godina, sve**)
  ili **ručni odabir** bilo kojeg perioda; primjenjuje se na opremu, poslove,
  uzorke i kvarove

## 1.4.0 — 2026-07-14
- **Pristup po ulogama** — administrativne stranice (Odobravanje, Prijem uzorka,
  Unos opreme, Rješavanje kvarova) traže **prijavu imenom i lozinkom**
- **Zahtjev za opremu** i **Prijava kvara** ostaju **otvoreni svima** s linkom
- Svaka ovlaštena osoba ima **svoju lozinku** (u Secrets, blok `[pristup]`) —
  app zna tko je prijavljen, pa se `odobrio` upisuje **automatski** (nema biranja imena)
- Katalog **48 normi/metoda** unesen u bazu (45 laboratorijskih, 3 terenske)

## 1.3.0 — 2026-07-14
- **Sustav i dalje radi?** — pri prijavi kvara komponente bira se može li se sustav
  koristiti (npr. VC ch14 u kvaru, ali radi s VC ch15). Uređaj ide u servis **samo**
  ako sustav nije upotrebljiv.
- Novo polje **„Zamijenjeno s"** — bilježi čime je komponenta premoštena
- **Vremenska zona `Europe/Zagreb`** — vremena više nisu -2 h (server radi u UTC)

## 1.2.0 — 2026-07-14
- **Prijava kvara po komponenti** — uz cijeli uređaj, može se prijaviti i pojedini dio
  (volume controller, senzor, ćelija) sa **serijskim brojem**
- Nova tablica **`komponente`** — samostalne, *nisu* fiksno vezane na uređaj
  (jer se prenose među okvirima); registar **raste sam** pri prijavi kvara
- Rješavanje kvarova prikazuje komponentu i serijski broj
- E-mail obavijest o kvaru sadrži komponentu i s/n — spremno za upit servisu

## 1.1.0 — 2026-07-13
- Sve forme spojene u **jednu aplikaciju** s izbornikom (jedan link)
- Nova stranica **✅ Odobravanje** — odobri/odbij zahtjev, bilježi tko i kada
- Nova stranica **🔧 Rješavanje kvarova** — zatvori kvar, vrati uređaj u upotrebu
- Početna stranica s pregledom stanja (zahtjevi, kvarovi, oprema, uzorci)
- Prikaz verzije u bočnoj traci

## 1.0.0 — 2026-07-10
- Zahtjev za korištenje opreme (upis u bazu, e-mail, status `na_cekanju`)
- Prijem uzorka (projekt i klijent po potrebi "u letu", atomarni upis)
- Prijava kvara (uređaj automatski ide `u_servisu`)
- Unos opreme (auto `id`, status iz izbornika, provjera duplikata inv. broja)
- Baza: Supabase (PostgreSQL) — sljedivost, audit trag, pravilo četiri oka
