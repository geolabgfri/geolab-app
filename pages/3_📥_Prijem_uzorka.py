"""
Prijem uzorka — Streamlit forma spojena na Supabase.

Zaprima uzorak i vezuje ga na projekt (postojeci ILI novi u letu).
Novi projekt trazi klijenta (postojeci ili novi); klijent ima tip komercijalni/interni.
Sve se upisuje atomarno (u jednoj transakciji).

Secrets: [supabase].
"""

from datetime import datetime, date

import streamlit as st

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada
from auth import trazi_prijavu

st.set_page_config(page_title="Prijem uzorka", page_icon="📥")
prikazi_verziju()

# 🔒 samo voditelj/laborant
tko = trazi_prijavu("Prijem uzorka")


@st.cache_data(ttl=120)
def ucitaj_projekte():
    return fetch("SELECT id, oznaka, naziv FROM projekti ORDER BY id DESC;")


@st.cache_data(ttl=120)
def ucitaj_klijente():
    return fetch("SELECT id, naziv, tip FROM klijenti ORDER BY tip, naziv;")


@st.cache_data(ttl=120)
def ucitaj_osoblje():
    return fetch(
        "SELECT id, ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;"
    )


def predlozi_oznaku():
    god = sada().year
    try:
        n = (fetch("SELECT count(*) FROM uzorci;")[0][0] or 0) + 1
    except Exception:
        n = 1
    return f"U-{god}-{n:04d}"


def spremi_sve(uzorak, projekt_mode, projekt_id, novi_projekt,
               klijent_mode, klijent_id, novi_klijent_naziv, novi_klijent_tip):
    """Sve u jednoj transakciji: (klijent) -> (projekt) -> uzorak."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if projekt_mode == "novi":
                if klijent_mode == "novi":
                    cur.execute(
                        "INSERT INTO klijenti (naziv, tip) VALUES (%s, %s) RETURNING id;",
                        (novi_klijent_naziv, novi_klijent_tip),
                    )
                    klijent_id = cur.fetchone()[0]
                cur.execute(
                    """INSERT INTO projekti (klijent_id, oznaka, naziv, gradiliste)
                       VALUES (%s,%s,%s,%s) RETURNING id;""",
                    (klijent_id, novi_projekt["oznaka"],
                     novi_projekt["naziv"] or None, novi_projekt["gradiliste"] or None),
                )
                projekt_id = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO uzorci
                   (oznaka_uzorka, projekt_id, zaprimio, datum_prijema, vrsta,
                    lokacija_uzorkovanja, dubina_m, dostavio, stanje_pri_prijemu,
                    uvjeti_skladistenja, mjesto_pohrane, napomena)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);""",
                (uzorak["oznaka"], projekt_id, uzorak["zaprimio"], uzorak["datum"],
                 uzorak["vrsta"], uzorak["lokacija"], uzorak["dubina"],
                 uzorak["dostavio"], uzorak["stanje"], uzorak["uvjeti"],
                 uzorak["pohrana"], uzorak["napomena"]),
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------- SUCELJE ----------------------------
st.title("📥 Prijem uzorka")
st.caption("Zaprimi uzorak i vezi ga na postojeci ili novi projekt.")

try:
    projekti = ucitaj_projekte()
    klijenti = ucitaj_klijente()
    osobe = ucitaj_osoblje()
except Exception as e:
    st.error("Ne mogu se spojiti na bazu. Provjeri Secrets ([supabase]).")
    st.caption(f"Detalj: {e}")
    st.stop()

if not osobe:
    st.warning("Nema aktivnog osoblja u bazi.")
    st.stop()

oznaka = st.text_input("Oznaka uzorka", value=predlozi_oznaku(),
                       help="Jedinstvena oznaka; prijedlog mozes promijeniti.")

# --- Projekt ---
st.subheader("Projekt (posao)")
opcije_proj = (["Postojeci", "Novi projekt"] if projekti else ["Novi projekt"])
projekt_mode_lbl = st.radio("Projekt", opcije_proj, horizontal=True,
                            label_visibility="collapsed")

projekt_id = None
novi_projekt = {"oznaka": "", "naziv": "", "gradiliste": ""}
klijent_mode = "id"
klijent_id = None
novi_klijent_naziv = ""
novi_klijent_tip = "komercijalni"

if projekt_mode_lbl == "Postojeci":
    projekt_mode = "id"
    labele = [f"{ozn} — {naziv or ''}".strip(" —") for (_id, ozn, naziv) in projekti]
    pi = st.selectbox("Odaberi projekt", range(len(labele)),
                      format_func=lambda i: labele[i])
    projekt_id = projekti[pi][0]
else:
    projekt_mode = "novi"
    novi_projekt["oznaka"] = st.text_input("Oznaka projekta *", placeholder="npr. P-2026-002")
    novi_projekt["naziv"] = st.text_input("Naziv projekta")
    novi_projekt["gradiliste"] = st.text_input("Gradiliste / lokacija")

    st.markdown("**Klijent** (za koga / za sto se radi)")
    opcije_kli = (["Postojeci", "Novi klijent"] if klijenti else ["Novi klijent"])
    klijent_mode_lbl = st.radio("Klijent", opcije_kli, horizontal=True,
                                label_visibility="collapsed")
    if klijent_mode_lbl == "Postojeci":
        klijent_mode = "id"
        kl_labele = [f"{naziv}  ·  {tip}" for (_id, naziv, tip) in klijenti]
        ki = st.selectbox("Odaberi klijenta", range(len(kl_labele)),
                          format_func=lambda i: kl_labele[i])
        klijent_id = klijenti[ki][0]
    else:
        klijent_mode = "novi"
        novi_klijent_naziv = st.text_input("Naziv novog klijenta *")
        novi_klijent_tip = st.selectbox("Tip klijenta", ["komercijalni", "interni"])

# --- Uzorak ---
st.subheader("Podaci o uzorku")
oi = st.selectbox("Uzorak zaprimio", range(len(osobe)),
                  format_func=lambda i: osobe[i][1])
zaprimio_id = osobe[oi][0]

datum_prijema = st.date_input("Datum prijema", value=date.today())
vrsta_lbl = st.selectbox("Vrsta uzorka", ["Neporemecen", "Poremecen", "Ostalo"])
vrsta = {"Neporemecen": "neporemecen", "Poremecen": "poremecen", "Ostalo": "ostalo"}[vrsta_lbl]

c1, c2 = st.columns(2)
with c1:
    lokacija = st.text_input("Lokacija uzorkovanja")
    dostavio = st.text_input("Dostavio")
    pohrana = st.text_input("Mjesto pohrane")
with c2:
    dubina = st.number_input("Dubina (m)", min_value=0.0, step=0.5, value=0.0)
    uvjeti = st.text_input("Uvjeti skladistenja")

stanje = st.text_area("Stanje pri prijemu")
napomena = st.text_area("Napomena")

st.divider()
if st.button("📥 Zaprimi uzorak", type="primary"):
    greske = []
    if not oznaka.strip():
        greske.append("Upisi oznaku uzorka.")
    if projekt_mode == "novi":
        if not novi_projekt["oznaka"].strip():
            greske.append("Upisi oznaku novog projekta.")
        if klijent_mode == "novi" and not novi_klijent_naziv.strip():
            greske.append("Upisi naziv novog klijenta.")

    if greske:
        for g in greske:
            st.error(g)
    else:
        uzorak = {
            "oznaka": oznaka.strip(), "zaprimio": zaprimio_id,
            "datum": datum_prijema, "vrsta": vrsta,
            "lokacija": lokacija or None, "dubina": (dubina if dubina > 0 else None),
            "dostavio": dostavio or None, "stanje": stanje or None,
            "uvjeti": uvjeti or None, "pohrana": pohrana or None,
            "napomena": napomena or None,
        }
        try:
            spremi_sve(uzorak, projekt_mode, projekt_id, novi_projekt,
                       klijent_mode, klijent_id,
                       novi_klijent_naziv.strip(), novi_klijent_tip)
            st.success(f"✅ Uzorak {oznaka.strip()} je zaprimljen.")
            if projekt_mode == "novi":
                st.info(f"Napravljen i novi projekt: {novi_projekt['oznaka'].strip()}")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            poruka = str(e)
            if "duplicate" in poruka.lower() or "unique" in poruka.lower():
                st.error("Oznaka uzorka ili projekta vec postoji. Promijeni je.")
            else:
                st.error(f"Greska pri spremanju: {poruka}")
