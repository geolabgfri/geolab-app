"""Upis istrazivackog projekta — upisuje administrator ili osoba u znanstveno-nastavnom
zvanju (prijava obavezna); odobrava administrator na stranici Odobravanje.

Upis ide u 'projekti' (vrsta='istrazivacki', status_odobrenja='na_cekanju').
Klijent = financijer (HRZZ, NPOO, JICA ...), obicno tipa 'interni'.
Nakon odobrenja projekt se moze birati u Prijemu uzorka, Zahtjevu za opremu
i Unosu opreme (projekt nabave = akronim).
Strucni posao za klijenta otvara se na stranici Novi posao.
Voditelj mora imati znanstveno-nastavno zvanje. Voditelj i suradnici upisuju se
u projekt_suradnici (osnova za buduci dnevnik koristenja opreme na projektu).
"""
import os, sys

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada
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
def ucitaj_klijente():
    return fetch("SELECT id, naziv, tip FROM klijenti ORDER BY tip DESC, naziv;")


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
                     datum_pocetka, datum_zavrsetka, opis,
                     status_odobrenja, predlozio, datum_otvaranja)
                VALUES (%s,%s,%s,'istrazivacki',%s,%s,%s,%s,%s,%s,'na_cekanju',%s,%s)
                RETURNING id;""",
                (klijent_id, d["oznaka"], d["naziv"], d["akronim"], d["sifra"],
                 d["voditelj"], d["od"], d["do"], d["opis"], d["predlozio"],
                 sada().date()))
            pid = cur.fetchone()[0]
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
    klijenti = ucitaj_klijente()
    postojeci = ucitaj_projekte()
except Exception as e:
    st.error("Nema veze s bazom ili baza jos nije nadogradena "
             "(sql/1.7.0_istrazivacki_projekti.sql).")
    st.caption(f"Detalj: {e}")
    st.stop()

voditelji = [o for o in osobe if o[2]]
if not voditelji:
    st.warning("Nitko u tablici osoblje nema oznaceno znanstveno-nastavno zvanje "
               "(stupac znanstveno_zvanje) — javi voditelju laboratorija.")
    st.stop()

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

st.markdown("**Financijer**")
opcije = (["Postojeci", "Novi financijer"] if klijenti else ["Novi financijer"])
fmod = st.radio("Financijer", opcije, horizontal=True, label_visibility="collapsed")
klijent_id, nk_naziv, fin_txt = None, "", ""
if fmod == "Postojeci":
    lab = [f"{n}  ·  {t}" for (_i, n, t) in klijenti]
    ki = st.selectbox("Odaberi financijera", range(len(lab)), format_func=lambda i: lab[i],
                      help="Financijeri se vode kao klijenti tipa 'interni'.")
    klijent_id, fin_txt = klijenti[ki][0], klijenti[ki][1]
else:
    nk_naziv = st.text_input("Naziv financijera *", placeholder="npr. HRZZ")
    fin_txt = nk_naziv

c1, c2 = st.columns(2)
sifra = c1.text_input("Sifra / broj ugovora", placeholder="npr. IP-2022-10-1234")
oznaka = c2.text_input("Predlozena oznaka", placeholder="npr. NPOO-2026-REMOK",
                       help="Ako ostane prazno, predlaze se FINANCIJER-GODINA-AKRONIM. "
                            "Konacnu oznaku potvrduje tko odobrava.")

imena_vod = [o[1] for o in voditelji]
vi = st.selectbox("Voditelj projekta *", range(len(voditelji)),
                  format_func=lambda i: imena_vod[i],
                  index=imena_vod.index(tko) if tko in imena_vod else 0,
                  help="Samo osoblje u znanstveno-nastavnom zvanju (doc., izv. prof., prof.).")
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

opis = st.text_area("Opis — koja ispitivanja / oprema su predvideni u laboratoriju")

st.divider()
if st.button("📨 Upisi projekt", type="primary"):
    greske = []
    if not akronim.strip():
        greske.append("Upisi akronim projekta.")
    if not naziv.strip():
        greske.append("Upisi puni naziv projekta.")
    if fmod != "Postojeci" and not nk_naziv.strip():
        greske.append("Upisi naziv financijera.")
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
             "sifra": sifra.strip() or None, "voditelj": voditelj,
             "od": datum_od, "do": datum_do, "opis": opis.strip() or None,
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
        except Exception as e:
            poruka = str(e).lower()
            if "duplicate" in poruka or "unique" in poruka:
                st.error(f"Oznaka '{konacna}' vec postoji. Upisi drugu predlozenu oznaku.")
            else:
                st.error(f"Greska: {e}")

st.divider()
st.subheader("📧 Obavijest e-mailom")
if "email" not in st.secrets:
    st.info("E-mail nije konfiguriran.")
elif "prijedlog_ip" not in st.session_state:
    st.caption("Prvo upisi projekt.")
elif st.button("📧 Posalji e-mail voditelju i laborantu"):
    try:
        import yagmail
        p = st.session_state["prijedlog_ip"]
        rec = list(st.secrets["email"]["recipients"])
        yag = yagmail.SMTP(st.secrets["email"]["sender"],
                           st.secrets["email"]["app_password"])
        yag.send(to=rec,
                 subject=f"Novi istrazivacki projekt (na cekanju): {p['akronim']}",
                 contents=(f"Upisan istrazivacki projekt {p['oznaka']} (ceka odobrenje).\n\n"
                           f"Akronim: {p['akronim']}\nNaziv: {p['naziv']}\n"
                           f"Financijer: {p['financijer']}  ·  sifra: {p['sifra'] or '—'}\n"
                           f"Voditelj: {p['voditelj']}\nSuradnici: {p['suradnici']}\n"
                           f"Trajanje: {p['trajanje']}\n"
                           f"Predlozio: {p['predlozio']}\nOpis: {p['opis'] or '—'}\n\n"
                           f"Odobrite na stranici Odobravanje."))
        st.success(f"📤 Poslano na: {', '.join(rec)}")
    except Exception as e:
        st.error(f"Greska pri slanju: {e}")
