"""Novi posao / projekt — cijeli tok: upit -> ponuda -> narudzbenica -> izvjestaj.

Uz svaki dokument: broj, datum i link (GitHub). Klijent postojeci ili novi
(komercijalni / interni). Postojeci projekt se moze i dopuniti.
"""
import os, sys
from datetime import date

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada
from auth import trazi_prijavu

st.set_page_config(page_title="Novi posao", page_icon="📝")
prikazi_verziju()

# 🔒 samo voditelj/laborant
tko = trazi_prijavu("Novi posao")

FAZE = ["upit", "ponuda", "narudzba", "izvjestaj", "zavrseno"]


@st.cache_data(ttl=60)
def ucitaj_klijente():
    return fetch("SELECT id, naziv, tip FROM klijenti ORDER BY tip, naziv;")


@st.cache_data(ttl=60)
def ucitaj_projekte():
    return fetch("""SELECT p.id, p.oznaka, p.naziv, k.naziv, p.faza
                    FROM projekti p JOIN klijenti k ON k.id = p.klijent_id
                    ORDER BY p.id DESC;""")


def spremi_projekt(novi, d, klijent_mode, klijent_id, nk_naziv, nk_tip, projekt_id=None):
    """Novi projekt (uz eventualnog novog klijenta) ili azuriranje postojeceg."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if novi:
                if klijent_mode == "novi":
                    cur.execute("INSERT INTO klijenti (naziv, tip) VALUES (%s,%s) RETURNING id;",
                                (nk_naziv, nk_tip))
                    klijent_id = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO projekti
                        (klijent_id, oznaka, naziv, gradiliste, faza,
                         broj_upita, datum_upita, link_upita,
                         broj_ponude, datum_ponude, link_ponude,
                         broj_narudzbenice, datum_narudzbenice, link_narudzbenice,
                         broj_izvjestaja, datum_izvjestaja, link_izvjestaja)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;""",
                    (klijent_id, d["oznaka"], d["naziv"], d["gradiliste"], d["faza"],
                     d["b_upit"], d["d_upit"], d["l_upit"],
                     d["b_pon"], d["d_pon"], d["l_pon"],
                     d["b_nar"], d["d_nar"], d["l_nar"],
                     d["b_izv"], d["d_izv"], d["l_izv"]))
                pid = cur.fetchone()[0]
            else:
                cur.execute("""
                    UPDATE projekti SET
                        faza=%s,
                        broj_upita=%s, datum_upita=%s, link_upita=%s,
                        broj_ponude=%s, datum_ponude=%s, link_ponude=%s,
                        broj_narudzbenice=%s, datum_narudzbenice=%s, link_narudzbenice=%s,
                        broj_izvjestaja=%s, datum_izvjestaja=%s, link_izvjestaja=%s
                    WHERE id=%s;""",
                    (d["faza"],
                     d["b_upit"], d["d_upit"], d["l_upit"],
                     d["b_pon"], d["d_pon"], d["l_pon"],
                     d["b_nar"], d["d_nar"], d["l_nar"],
                     d["b_izv"], d["d_izv"], d["l_izv"], projekt_id))
                pid = projekt_id
        conn.commit()
        return pid
    finally:
        conn.close()


def blok_dokumenta(naslov, kljuc, postojeci=None):
    """Broj + datum + link za jedan dokument. Vraca (broj, datum, link)."""
    with st.expander(naslov, expanded=(postojeci is None)):
        c1, c2 = st.columns([2, 1])
        broj = c1.text_input("Broj / oznaka", key=f"b_{kljuc}",
                             value=(postojeci[0] or "") if postojeci else "")
        ima = c2.checkbox("Datum", key=f"dc_{kljuc}",
                          value=bool(postojeci and postojeci[1]))
        datum = None
        if ima:
            datum = c2.date_input("Datum", key=f"d_{kljuc}",
                                  value=(postojeci[1] if postojeci and postojeci[1] else date.today()),
                                  label_visibility="collapsed")
        link = st.text_input("Link na dokument (GitHub)", key=f"l_{kljuc}",
                             value=(postojeci[2] or "") if postojeci else "",
                             placeholder="https://github.com/...")
    return (broj or None), datum, (link or None)


# ---------------------------- SUCELJE ----------------------------
st.title("📝 Novi posao / projekt")
st.caption("Tok: upit → ponuda → narudžbenica → izvještaj")

try:
    klijenti = ucitaj_klijente()
    projekti = ucitaj_projekte()
except Exception as e:
    st.error("Nema veze s bazom."); st.caption(f"Detalj: {e}"); st.stop()

nacin = st.radio("Sto radis?",
                 ["➕ Novi posao", "✏️ Dopuni postojeci posao"],
                 horizontal=True, label_visibility="collapsed")
novi = nacin.startswith("➕")

projekt_id = None
stari = None

if novi:
    st.subheader("Osnovno")
    oznaka = st.text_input("Oznaka posla *", placeholder="npr. P-2026-002")
    naziv = st.text_input("Naziv posla", placeholder="npr. Inklinometarska mjerenja — Rijeka")
    gradiliste = st.text_input("Gradiliste / lokacija")

    st.subheader("Klijent")
    opcije = (["Postojeci", "Novi klijent"] if klijenti else ["Novi klijent"])
    kmod = st.radio("Klijent", opcije, horizontal=True, label_visibility="collapsed")
    klijent_mode, klijent_id, nk_naziv, nk_tip = "id", None, "", "komercijalni"
    if kmod == "Postojeci":
        lab = [f"{n}  ·  {t}" for (_i, n, t) in klijenti]
        ki = st.selectbox("Odaberi klijenta", range(len(lab)), format_func=lambda i: lab[i])
        klijent_id = klijenti[ki][0]
    else:
        klijent_mode = "novi"
        nk_naziv = st.text_input("Naziv novog klijenta *")
        nk_tip = st.selectbox("Tip", ["komercijalni", "interni"])
else:
    if not projekti:
        st.warning("Nema projekata za dopunu."); st.stop()
    lab = [f"{o} — {n or ''}  ·  {k}  ·  [{f or '—'}]" for (_i, o, n, k, f) in projekti]
    pi = st.selectbox("Odaberi posao", range(len(lab)), format_func=lambda i: lab[i])
    projekt_id = projekti[pi][0]
    stari = fetch("""SELECT broj_upita, datum_upita, link_upita,
                            broj_ponude, datum_ponude, link_ponude,
                            broj_narudzbenice, datum_narudzbenice, link_narudzbenice,
                            broj_izvjestaja, datum_izvjestaja, link_izvjestaja, faza
                     FROM projekti WHERE id = %s;""", (projekt_id,))[0]
    klijent_mode, klijent_id, nk_naziv, nk_tip = "id", None, "", ""
    oznaka = naziv = gradiliste = None

st.divider()
st.subheader("Dokumenti")

b_upit, d_upit, l_upit = blok_dokumenta("📩 Upit za ponudu", "upit",
                                        (stari[0], stari[1], stari[2]) if stari else None)
b_pon, d_pon, l_pon = blok_dokumenta("💰 Ponuda", "pon",
                                     (stari[3], stari[4], stari[5]) if stari else None)
b_nar, d_nar, l_nar = blok_dokumenta("📋 Narudzbenica", "nar",
                                     (stari[6], stari[7], stari[8]) if stari else None)
b_izv, d_izv, l_izv = blok_dokumenta("📄 Izvjestaj", "izv",
                                     (stari[9], stari[10], stari[11]) if stari else None)

faza_default = FAZE.index(stari[12]) if (stari and stari[12] in FAZE) else 0
faza = st.selectbox("Faza posla", FAZE, index=faza_default,
                    help="Dokle je posao stigao.")

st.divider()
if st.button("💾 Spremi", type="primary"):
    greske = []
    if novi:
        if not (oznaka or "").strip():
            greske.append("Upisi oznaku posla.")
        if klijent_mode == "novi" and not nk_naziv.strip():
            greske.append("Upisi naziv novog klijenta.")
    if greske:
        for g in greske:
            st.error(g)
    else:
        d = {"oznaka": (oznaka or "").strip() or None,
             "naziv": (naziv or "").strip() or None,
             "gradiliste": (gradiliste or "").strip() or None, "faza": faza,
             "b_upit": b_upit, "d_upit": d_upit, "l_upit": l_upit,
             "b_pon": b_pon, "d_pon": d_pon, "l_pon": l_pon,
             "b_nar": b_nar, "d_nar": d_nar, "l_nar": l_nar,
             "b_izv": b_izv, "d_izv": d_izv, "l_izv": l_izv}
        try:
            pid = spremi_projekt(novi, d, klijent_mode, klijent_id,
                                 nk_naziv.strip(), nk_tip, projekt_id)
            st.success(f"✅ {'Posao je otvoren' if novi else 'Posao je dopunjen'} (id {pid}).")
            if novi and klijent_mode == "novi":
                st.info(f"Napravljen i novi klijent: {nk_naziv.strip()}")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            poruka = str(e)
            if "duplicate" in poruka.lower() or "unique" in poruka.lower():
                st.error("Posao s tom oznakom vec postoji.")
            else:
                st.error(f"Greska: {poruka}")
