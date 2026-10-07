# Dnevnik verzija — Laboratorij za geotehniku

Verzija se postavlja u `db.py` (`VERZIJA`, `DATUM_VERZIJE`)
i prikazuje se u bočnoj traci na svakoj stranici.

Format: `glavna.manja.zakrpa`
- **zakrpa** (1.0.**X**) — popravak sitnice
- **manja** (1.**X**.0) — nova funkcija ili stranica
- **glavna** (**X**.0.0) — veća promjena strukture baze

---

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
