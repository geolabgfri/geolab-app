# Dnevnik verzija — Laboratorij za geotehniku

Verzija se postavlja u `db.py` (`VERZIJA`, `DATUM_VERZIJE`)
i prikazuje se u bočnoj traci na svakoj stranici.

Format: `glavna.manja.zakrpa`
- **zakrpa** (0.1.**X**) — popravak sitnice
- **manja** (0.**X**.0) — nova funkcija ili stranica
- **glavna** (**X**.0.0) — veća promjena strukture baze

**0.x.x je razvojna faza.** Verzija 1.0.0 bit će prva službena, javna verzija.

---

## 0.10.0 — 2026-10-09
- Nova stranica **👤 Moj pregled** (svaka prijavljena osoba): zahtjevi u kojima je osoba
  podnositelj ili provoditelj (`osoba_id`)
  - brojke: na čekanju, odobreno-predstoji, odrađeno (12 mj.), sati na opremi
  - **matrica po danima** (kao GitHub): sati korištenja odrađenih zahtjeva, zadnjih 12 mjeseci
  - zadnjih 15 zahtjeva sa statusom (na čekanju / odobreno · predstoji / odrađeno · sati)
  - administrator može odabrati bilo koju osobu
- `auth.trazi_prijavu` — nova razina `prijava` (bilo koja prijavljena osoba)
- Baza: bez promjena

## 0.9.1 — 2026-10-09
- **✅ Odobravanje → Nedavno odobreno** — zadnjih 5 zahtjeva; umjesto statusa prikazuje
  vrijeme **Od – Do** i sate iz zahtjeva
- **✅ Odobravanje → Ispravak trajanja pokusa** — za odobrene zahtjeve (zadnjih 90 dana)
  upisuje se stvarni početak i završetak; sati se preračunaju. Prvotno planirano vrijeme
  ostaje u `plan_vrijeme_od / plan_vrijeme_do`, bilježi se tko je i kada ispravio
- **📨 Zahtjev za opremu** — podnositelj koji nije na popisu mora upisati ispravan e-mail
- **Popravak vremenske zone** — vrijeme zahtjeva sprema se kao hrvatsko vrijeme; ranije se
  zahtjev za 08:00 prikazivao kao 10:00. Postojeći zapisi ispravljaju se SQL skriptom
- **`koristenje_opreme.osoba_id`** — stupac koji je postojao od početka, ali se nije koristio,
  sada je **provoditelj pokusa** iz tablice `osoblje` (veza na `osoblje.id`); popunjava se
  automatski, za vanjske osobe ostaje prazan (ime je u `provoditelj`). Osnova za budući dnevnik
- Baza: `sql/0.9.1_ispravak_trajanja.sql` (uključuje vezu `osoba_id → osoblje` i popunu
  postojećih zapisa)

## 0.9.0 — 2026-10-09
- **📨 Zahtjev za opremu — podnositelj i provoditelj**: kvačica „Podnositelj je ujedno i
  provoditelj ispitivanja” (zadano DA); inače se bira provoditelj iz osoblja ili upisuje
  (student, doktorand, vanjski suradnik). Novi stupac `koristenje_opreme.provoditelj`
  (prazno = isti kao podnositelj). Provoditelj u Odobravanju, e-mailu, kalendaru i Pregledima
- **Automatske e-mail obavijesti** — Zahtjev za opremu, Prijava kvara i Upis projekta
  šalju e-mail odmah pri spremanju (nema više posebnog gumba). Ako slanje ne uspije, zapis
  ostaje spremljen, a nudi se „Pošalji e-mail ponovno”. Zajednički modul `obavijest.py`
- **Kopija (cc)** — podnositelju, provoditelju, prijavitelju kvara, odnosno predlagatelju
  i voditelju projekta, ako su u tablici `osoblje`. Podnositelj „Ostalo” može upisati
  svoj e-mail za kopiju
- Baza: `sql/0.9.0_provoditelj_i_email.sql` — stupac `osoblje.email`, popunjen po pravilu
  `ime.prezime@gradri.uniri.hr` (mala slova, bez dijakritika, prvo prezime); iznimke se
  ispravljaju ručno u Table Editoru

## 0.8.4 — 2026-10-08
- Istraživački projekti dobivaju fazu **`u_tijeku`** (od upisa) → **`zavrseno`**
  (gumb „Završen” u Odobravanju); više nemaju besmislenu fazu `upit`
- Faze stručnih poslova (Novi posao) ostaju: upit → ponuda → narudžba → izvještaj → završeno
- **📊 Pregledi → Istraživački projekti** — status „u tijeku” / „završen”
- Baza: `sql/0.8.4_faza_u_tijeku.sql` (dopuna CHECK ograničenja za `faza`,
  postojeći istraživački projekti → `u_tijeku`)

## 0.8.3 — 2026-10-08
- **🗂️ Upis projekta**
  - **Financijer** — padajući izbornik postojećih financijera (klijenti tipa `interni`)
    ili „Drugi — upiši”
  - **Voditelj** — padajući izbornik osoblja u znanstveno-nastavnom zvanju ili
    „Drugi — upiši” (vanjski voditelj; ne upisuje se u `projekt_suradnici`)
  - novo polje **Sažetak projekta**; dosadašnji opis preimenovan u
    „Laboratorij — koja ispitivanja / oprema su predviđeni”
- **✅ Odobravanje** — prikazuje sažetak projekta
- Baza: `sql/0.8.3_sazetak_projekta.sql` (stupac `projekti.sazetak`)

## 0.8.2 — 2026-10-08
- **🗂️ Prijedlog projekta → Upis projekta** (naziv stranice, gumb „Upiši projekt”, poruke)
- **✅ Odobravanje** — odbijeni zahtjev za opremu se **briše iz baze** (uz potvrdu);
  u evidenciji korištenja ostaju samo zahtjevi na čekanju i odobreni.
  Povijest prikazuje nedavno odobrene zahtjeve
- Baza: bez promjene strukture; postojeće odbijene zahtjeve po želji obriši s
  `sql/0.8.2_brisanje_odbijenih.sql`

## 0.8.1 — 2026-10-07
- **Oznaka BETA** — stupac `beta` u tablicama s unosima (korištenje opreme, kvarovi,
  uzorci, ispitivanja, projekti, suradnici, klijenti, oprema, komponente).
  Postojeći (stvarni) zapisi: `FALSE`; svaki novi zapis: `TRUE` — postavlja baza sama
- U bočnoj traci upozorenje **BETA — prijelazno razdoblje do 1. 1. 2027.**
  (prikazuje se dok je verzija 0.x.x)
- Baza: `sql/0.8.1_beta_oznaka.sql`; za kraj bete pripremljen `sql/1.0.0_kraj_bete.sql`
  (novi zapisi više nisu beta; beta zapisi se zadržavaju ili brišu — odluka tada)

## 0.8.0 — 2026-10-07
- **Uloge u aplikaciji** — novi stupci u `osoblje`: `administrator` (voditelj, laborant)
  i `znanstveno_zvanje` (doc., izv. prof., prof.); postavljaju se kvačicom u Table Editoru
- **Osobna prijava** — svaka osoba ima svoju lozinku u Secrets `[pristup]`;
  uloge se čitaju iz `osoblje` pri prijavi
- **Izbornik prema ulozi** — svi vide Zahtjev za opremu i Prijavu kvara;
  *Prijedlog projekta* vide administratori i osobe u zvanju; ostalo samo administratori
  (stranice bez ovlasti ne vide se u izborniku). U bočnoj traci: tko je prijavljen i uloga
- **🗂️ Prijedlog projekta** — samo uz prijavu; predlagatelj je prijavljena osoba,
  voditelj mora imati znanstveno-nastavno zvanje, biraju se **suradnici** iz `osoblje`
- Nova tablica **`projekt_suradnici`** (projekt, osoba, voditelj/suradnik) — osnova za
  budući dnevnik korištenja opreme na projektu; suradnici se vide u Odobravanju i Pregledima
- Baza: `sql/0.8.0_uloge_i_suradnici.sql`

## 0.7.1 — 2026-10-07
- Prenumeriranje verzija: dosadašnje 1.x.x → **0.x.x** (razvojna faza);
  1.0.0 bit će prva službena verzija. SQL skripte zadržavaju izvorna imena.

## 0.7.0 — 2026-10-07
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
- Baza: `sql/1.7.0_istrazivacki_projekti.sql`; tablica `prijedlozi_projekata` iz 0.6.0
  se briše

## 0.6.0 — 2026-10-07  *(zamijenjeno u 0.7.0)*
- Nova stranica **🗂️ Prijedlog projekta** (bez prijave) — osoba s popisa
  `osoblje` predlaže projekt: naziv, predložena oznaka, gradilište, opis,
  klijent postojeći ili novi; prijedlog ide u `prijedlozi_projekata` sa statusom `na_cekanju`
- **✅ Odobravanje** podijeljeno na kartice: *Zahtjevi za opremu* i *Prijedlozi projekata*;
  pri odobrenju se određuje konačna oznaka, projekt se otvara u `projekti`
  (novi klijent se stvara ako ne postoji), bilježi se tko je odlučio, kada i napomena
- Početna upozorava na prijedloge projekata na čekanju
- Baza: `sql/1.6.0_prijedlozi_projekata.sql` (nova tablica; postojeće se ne mijenjaju)

## 0.5.0 — 2026-07-14
- Nova stranica **📝 Novi posao** — cijeli tok posla (upit → ponuda → narudžbenica →
  izvještaj) s brojem, datumom i **linkom na dokument**; klijent postojeći ili novi;
  postojeći posao se može **dopuniti** (npr. kad stigne narudžbenica)
- Nova stranica **📊 Pregledi** — iskorištenost opreme (sati, broj korištenja),
  poslovi po fazi, uzorci, kvarovi po uređaju; grafovi + **izvoz u CSV**
- Pregled **upozorava na umjeravanje** koje istječe u sljedećih 60 dana
- Razdoblje pregleda: brzi izbor (**ovaj/prošli mjesec, ova/prošla godina, sve**)
  ili **ručni odabir** bilo kojeg perioda; primjenjuje se na opremu, poslove,
  uzorke i kvarove

## 0.4.0 — 2026-07-14
- **Pristup po ulogama** — administrativne stranice (Odobravanje, Prijem uzorka,
  Unos opreme, Rješavanje kvarova) traže **prijavu imenom i lozinkom**
- **Zahtjev za opremu** i **Prijava kvara** ostaju **otvoreni svima** s linkom
- Svaka ovlaštena osoba ima **svoju lozinku** (u Secrets, blok `[pristup]`) —
  app zna tko je prijavljen, pa se `odobrio` upisuje **automatski** (nema biranja imena)
- Katalog **48 normi/metoda** unesen u bazu (45 laboratorijskih, 3 terenske)

## 0.3.0 — 2026-07-14
- **Sustav i dalje radi?** — pri prijavi kvara komponente bira se može li se sustav
  koristiti (npr. VC ch14 u kvaru, ali radi s VC ch15). Uređaj ide u servis **samo**
  ako sustav nije upotrebljiv.
- Novo polje **„Zamijenjeno s"** — bilježi čime je komponenta premoštena
- **Vremenska zona `Europe/Zagreb`** — vremena više nisu -2 h (server radi u UTC)

## 0.2.0 — 2026-07-14
- **Prijava kvara po komponenti** — uz cijeli uređaj, može se prijaviti i pojedini dio
  (volume controller, senzor, ćelija) sa **serijskim brojem**
- Nova tablica **`komponente`** — samostalne, *nisu* fiksno vezane na uređaj
  (jer se prenose među okvirima); registar **raste sam** pri prijavi kvara
- Rješavanje kvarova prikazuje komponentu i serijski broj
- E-mail obavijest o kvaru sadrži komponentu i s/n — spremno za upit servisu

## 0.1.0 — 2026-07-13
- Sve forme spojene u **jednu aplikaciju** s izbornikom (jedan link)
- Nova stranica **✅ Odobravanje** — odobri/odbij zahtjev, bilježi tko i kada
- Nova stranica **🔧 Rješavanje kvarova** — zatvori kvar, vrati uređaj u upotrebu
- Početna stranica s pregledom stanja (zahtjevi, kvarovi, oprema, uzorci)
- Prikaz verzije u bočnoj traci

## 0.0.0 — 2026-07-10
- Zahtjev za korištenje opreme (upis u bazu, e-mail, status `na_cekanju`)
- Prijem uzorka (projekt i klijent po potrebi "u letu", atomarni upis)
- Prijava kvara (uređaj automatski ide `u_servisu`)
- Unos opreme (auto `id`, status iz izbornika, provjera duplikata inv. broja)
- Baza: Supabase (PostgreSQL) — sljedivost, audit trag, pravilo četiri oka
