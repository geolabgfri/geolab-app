"""Upis istrazivackog projekta — upisuje administrator ili osoba u znanstveno-nastavnom
zvanju (prijava obavezna); odobrava administrator na stranici Odobravanje.

Upis ide u 'projekti' (vrsta='istrazivacki', status_odobrenja='na_cekanju').
Klijent = financijer (HRZZ, NPOO, JICA ...), obicno tipa 'interni'.
Nakon odobrenja projekt se moze birati u Prijemu uzorka, Zahtjevu za opremu
i Unosu opreme (projekt nabave = akronim).
Strucni posao za klijenta otvara se na stranici Novi posao.
Voditelj se bira iz osoblja sa znanstveno-nastavnim zvanjem ili upisuje rucno
(vanjski voditelj). Voditelj i suradnici upisuju se
u projekt_suradnici (osnova za buduci dnevnik koristenja opreme na projektu).
"""
import os, sys

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada
from obavijest import posalji, prikazi_status, email_osobe
from auth import trazi_prijavu

st.set_page_config(page_title="Istrazivacki projekt", page_icon="🗂️")
prikazi_verziju()

# 🔒 administrator ili znanstveno-nastavno zvanje
tko = trazi_prijavu("Upis projekta", razina="projekti")


@st.cache_data(ttl=300)
def ucitaj_osoblje():
    """(id, ime, znanstveno_zvanje) aktivnog osoblja."""
    return fetch("""SELECT id, ime_prezime, znanstveno_zvanje FROM osoblje
                    WHERE aktivan = TRUE ORDER BY ime_prezime;""")


@st.cache_data(ttl=120)
def ucitaj_financijere():
    """Financijeri = klijenti tipa 'interni'."""
    return fetch("SELECT id, naziv FROM klijenti WHERE tip = 'interni' ORDER BY naziv;")


@st.cache_data(ttl=120)
def ucitaj_projekte():
    return fetch("""SELECT p.oznaka, coalesce(p.akronim, p.naziv), k.naziv,
                           p.status_odobrenja, p.voditelj
                    FROM projekti p JOIN klijenti k ON k.id = p.klijent_id
                    WHERE p.vrsta = 'istrazivacki'
                      AND p.status_odobrenja IN ('na_cekanju','odobreno')
                    ORDER BY p.id DESC;""")


def spremi(d, klijent_id, nk_naziv, voditelj_id, suradnici_ids):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if klijent_id is None:
                cur.execute("SELECT id FROM klijenti WHERE lower(naziv) = lower(%s) LIMIT 1;",
                            (nk_naziv,))
                r = cur.fetchone()
                if r:
                    klijent_id = r[0]
                else:
                    cur.execute("INSERT INTO klijenti (naziv, tip) VALUES (%s,'interni') "
                                "RETURNING id;", (nk_naziv,))
                    klijent_id = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO projekti
                    (klijent_id, oznaka, naziv, vrsta, akronim, sifra, voditelj,
                     datum_pocetka, datum_zavrsetka, sazetak, opis,
                     status_odobrenja, predlozio, datum_otvaranja, faza)
                VALUES (%s,%s,%s,'istrazivacki',%s,%s,%s,%s,%s,%s,%s,'na_cekanju',%s,%s,'u_tijeku')
                RETURNING id;""",
                (klijent_id, d["oznaka"], d["naziv"], d["akronim"], d["sifra"],
                 d["voditelj"], d["od"], d["do"], d["sazetak"], d["opis"], d["predlozio"],
                 sada().date()))
            pid = cur.fetchone()[0]
            if voditelj_id:   # vanjski voditelj (upisan rucno) nije u tablici osoblje
                cur.execute("""INSERT INTO projekt_suradnici (projekt_id, osoblje_id, uloga)
                               VALUES (%s,%s,'voditelj');""", (pid, voditelj_id))
            for oid in suradnici_ids:
                cur.execute("""INSERT INTO projekt_suradnici (projekt_id, osoblje_id, uloga)
                               VALUES (%s,%s,'suradnik')
                               ON CONFLICT (projekt_id, osoblje_id) DO NOTHING;""",
                            (pid, oid))
        conn.commit()
        return pid
    finally:
        conn.close()


st.title("🗂️ Upis istrazivackog projekta")
st.caption("Znanstveni projekt (HRZZ, NPOO, JICA, EU ...). Aktivan je kad ga odobri "
           "voditelj ili laborant. Strucni posao za klijenta otvara se na stranici Novi posao.")

try:
    osobe = ucitaj_osoblje()
    financijeri = ucitaj_financijere()
    postojeci = ucitaj_projekte()
except Exception as e:
    st.error("Nema veze s bazom ili baza jos nije nadogradena "
             "(sql/1.7.0_istrazivacki_projekti.sql).")
    st.caption(f"Detalj: {e}")
    st.stop()

voditelji = [o for o in osobe if o[2]]
UPISI = "✏️ Drugi — upisi"

if postojeci:
    with st.expander(f"Postojeci istrazivacki projekti ({len(postojeci)}) — "
                     f"provjeri da tvoj vec nije upisan"):
        st.dataframe([{"Oznaka": o, "Akronim": a, "Financijer": k,
                       "Status": s, "Voditelj": v or "—"}
                      for (o, a, k, s, v) in postojeci],
                     use_container_width=True, hide_index=True)

predlozio = tko
st.caption(f"Predlaze: **{tko}**")

st.subheader("Projekt")
c1, c2 = st.columns([1, 2])
akronim = c1.text_input("Akronim *", placeholder="npr. REMOK")
naziv = c2.text_input("Puni naziv *")

fin_opcije = [n for (_i, n) in financijeri] + [UPISI]
fi = st.selectbox("Financijer *", range(len(fin_opcije)), format_func=lambda i: fin_opcije[i],
                  help="Odaberi s popisa ili upisi novog (npr. HRZZ, NPOO, JICA, EU, UNIRI).")
klijent_id, nk_naziv, fin_txt = None, "", ""
if fin_opcije[fi] == UPISI:
    nk_naziv = st.text_input("Naziv financijera *", placeholder="npr. HRZZ")
    fin_txt = nk_naziv
else:
    klijent_id, fin_txt = financijeri[fi][0], financijeri[fi][1]

c1, c2 = st.columns(2)
sifra = c1.text_input("Sifra / broj ugovora", placeholder="npr. IP-2022-10-1234")
oznaka = c2.text_input("Predlozena oznaka", placeholder="npr. NPOO-2026-REMOK",
                       help="Ako ostane prazno, predlaze se FINANCIJER-GODINA-AKRONIM. "
                            "Konacnu oznaku potvrduje tko odobrava.")

vod_opcije = [o[1] for o in voditelji] + [UPISI]
vi = st.selectbox("Voditelj projekta *", range(len(vod_opcije)),
                  format_func=lambda i: vod_opcije[i],
                  index=vod_opcije.index(tko) if tko in vod_opcije else 0,
                  help="Osoblje u znanstveno-nastavnom zvanju, ili upisi voditelja "
                       "koji nije na popisu (npr. s druge institucije).")
if vod_opcije[vi] == UPISI:
    voditelj_id = None
    voditelj = st.text_input("Ime i prezime voditelja *",
                             placeholder="npr. prof. dr. sc. Ime Prezime (institucija)")
else:
    voditelj_id, voditelj = voditelji[vi][0], voditelji[vi][1]

ostali = [o for o in osobe if o[0] != voditelj_id]
sur_idx = st.multiselect("Suradnici na projektu", range(len(ostali)),
                         format_func=lambda i: ostali[i][1],
                         help="Suradnici ce moci unositi koristenje opreme na ovom projektu.")
suradnici = [ostali[i] for i in sur_idx]

c1, c2 = st.columns(2)
ima_od = c1.checkbox("Datum pocetka")
datum_od = c1.date_input("Pocetak", label_visibility="collapsed") if ima_od else None
ima_do = c2.checkbox("Datum zavrsetka")
datum_do = c2.date_input("Zavrsetak", label_visibility="collapsed") if ima_do else None

sazetak = st.text_area("Sazetak projekta", height=150,
                       help="Kratki sazetak: cilj i sadrzaj projekta (moze se kopirati iz prijave).")
opis = st.text_area("Laboratorij — koja ispitivanja / oprema su predvideni")

st.divider()
if st.button("📨 Upisi projekt", type="primary"):
    greske = []
    if not akronim.strip():
        greske.append("Upisi akronim projekta.")
    if not naziv.strip():
        greske.append("Upisi puni naziv projekta.")
    if klijent_id is None and not nk_naziv.strip():
        greske.append("Upisi naziv financijera.")
    if not (voditelj or "").strip():
        greske.append("Upisi ime voditelja projekta.")
    if datum_od and datum_do and datum_do < datum_od:
        greske.append("Zavrsetak mora biti nakon pocetka.")
    if greske:
        for g in greske:
            st.error(g)
    else:
        konacna = oznaka.strip() or (
            f"{fin_txt.strip().split()[0].upper()}-{(datum_od or sada()).year}-"
            f"{akronim.strip().upper()}")
        d = {"oznaka": konacna, "naziv": naziv.strip(), "akronim": akronim.strip(),
             "sifra": sifra.strip() or None, "voditelj": voditelj.strip(),
             "od": datum_od, "do": datum_do, "sazetak": sazetak.strip() or None,
             "opis": opis.strip() or None,
             "predlozio": predlozio}
        try:
            pid = spremi(d, klijent_id, nk_naziv.strip(), voditelj_id,
                         [o[0] for o in suradnici])
            st.session_state["prijedlog_ip"] = {
                **d, "id": pid, "financijer": fin_txt.strip(),
                "suradnici": ", ".join(o[1] for o in suradnici) or "—",
                "trajanje": f"{datum_od or '?'} – {datum_do or '?'}"}
            st.cache_data.clear()
            st.success(f"✅ Projekt {konacna} je upisan i ceka odobrenje.")
            p = st.session_state["prijedlog_ip"]
            posalji("mail_projekt",
                    f"Novi istrazivacki projekt (na cekanju): {p['akronim']}",
                    (f"Upisan istrazivacki projekt {p['oznaka']} (ceka odobrenje).\n\n"
                     f"Akronim: {p['akronim']}\nNaziv: {p['naziv']}\n"
                     f"Financijer: {p['financijer']}  ·  sifra: {p['sifra'] or '—'}\n"
                     f"Voditelj: {p['voditelj']}\nSuradnici: {p['suradnici']}\n"
                     f"Trajanje: {p['trajanje']}\n"
                     f"Predlozio: {p['predlozio']}\n\n"
                     f"Sazetak:\n{p['sazetak'] or '—'}\n\n"
                     f"Laboratorij: {p['opis'] or '—'}\n\n"
                     f"Odobrite na stranici Odobravanje."),
                    cc=[email_osobe(tko), email_osobe(voditelj)])
        except Exception as e:
            poruka = str(e).lower()
            if "duplicate" in poruka or "unique" in poruka:
                st.error(f"Oznaka '{konacna}' vec postoji. Upisi drugu predlozenu oznaku.")
            else:
                st.error(f"Greska: {e}")

prikazi_status("mail_projekt")
