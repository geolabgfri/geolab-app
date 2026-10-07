"""Prijedlog projekta — osoba s popisa osoblja predlaze projekt; voditelj/laborant ga odobrava.

Upis ide u prijedlozi_projekata (status 'na_cekanju'). Tek nakon odobrenja
(stranica Odobravanje) projekt se stvarno otvara u tablici projekti.
Stranica je otvorena (bez prijave), kao Zahtjev za opremu.
"""
import os, sys

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, execute, prikazi_verziju

st.set_page_config(page_title="Prijedlog projekta", page_icon="🗂️")
prikazi_verziju()


@st.cache_data(ttl=300)
def ucitaj_katedru():
    return [r[0] for r in fetch(
        "SELECT ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;")]


@st.cache_data(ttl=120)
def ucitaj_klijente():
    return fetch("SELECT id, naziv, tip FROM klijenti ORDER BY tip, naziv;")


st.title("🗂️ Prijedlog projekta")
st.caption("Projekt se otvara tek kad ga odobri voditelj ili laborant.")

try:
    katedra = ucitaj_katedru()
    klijenti = ucitaj_klijente()
except Exception as e:
    st.error("Nema veze s bazom ili tablice jos nisu napravljene "
             "(sql/1.6.0_prijedlozi_projekata.sql).")
    st.caption(f"Detalj: {e}")
    st.stop()

if not katedra:
    st.warning("Nema aktivnog osoblja u bazi — javi voditelju laboratorija.")
    st.stop()

predlagatelj = st.selectbox("Predlagatelj", katedra)

st.subheader("Projekt")
naziv = st.text_input("Naziv projekta *")
predlozena_oznaka = st.text_input("Predlozena oznaka", placeholder="npr. P-2026-002",
                                  help="Nije obavezno — konacnu oznaku odredi tko odobrava.")
gradiliste = st.text_input("Gradiliste / lokacija")
opis = st.text_area("Opis i svrha (koja ispitivanja, okvirni opseg, rok)")

st.subheader("Klijent")
opcije = (["Postojeci", "Novi klijent"] if klijenti else ["Novi klijent"])
kmod = st.radio("Klijent", opcije, horizontal=True, label_visibility="collapsed")
klijent_id, nk_naziv, nk_tip = None, None, None
if kmod == "Postojeci":
    lab = [f"{n}  ·  {t}" for (_i, n, t) in klijenti]
    ki = st.selectbox("Odaberi klijenta", range(len(lab)), format_func=lambda i: lab[i])
    klijent_id = klijenti[ki][0]
else:
    nk_naziv = st.text_input("Naziv novog klijenta *")
    nk_tip = st.selectbox("Tip", ["interni", "komercijalni"])

st.divider()
if st.button("📨 Posalji prijedlog", type="primary"):
    greske = []
    if not naziv.strip():
        greske.append("Upisi naziv projekta.")
    if kmod != "Postojeci" and not (nk_naziv or "").strip():
        greske.append("Upisi naziv novog klijenta.")
    if greske:
        for g in greske:
            st.error(g)
    else:
        try:
            pid = execute("""
                INSERT INTO prijedlozi_projekata
                    (predlagatelj, predlozena_oznaka, naziv, gradiliste, opis,
                     klijent_id, novi_klijent_naziv, novi_klijent_tip)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;""",
                (predlagatelj, predlozena_oznaka.strip() or None, naziv.strip(),
                 gradiliste.strip() or None, opis.strip() or None,
                 klijent_id, (nk_naziv or "").strip() or None, nk_tip),
                returning=True)
            klijent_txt = (next(n for (i, n, _t) in klijenti if i == klijent_id)
                           if klijent_id else f"{nk_naziv.strip()} (novi, {nk_tip})")
            st.session_state["prijedlog"] = {
                "id": pid, "predlagatelj": predlagatelj, "naziv": naziv.strip(),
                "oznaka": predlozena_oznaka.strip() or "—", "klijent": klijent_txt,
                "gradiliste": gradiliste.strip() or "—", "opis": opis.strip() or "—"}
            st.success(f"✅ Prijedlog #{pid} je poslan i ceka odobrenje.")
        except Exception as e:
            st.error(f"Greska: {e}")

st.divider()
st.subheader("📧 Obavijest e-mailom")
if "email" not in st.secrets:
    st.info("E-mail nije konfiguriran.")
elif "prijedlog" not in st.session_state:
    st.caption("Prvo posalji prijedlog.")
elif st.button("📧 Posalji e-mail voditelju i laborantu"):
    try:
        import yagmail
        p = st.session_state["prijedlog"]
        rec = list(st.secrets["email"]["recipients"])
        yag = yagmail.SMTP(st.secrets["email"]["sender"],
                           st.secrets["email"]["app_password"])
        yag.send(to=rec, subject=f"Novi prijedlog projekta (na cekanju): {p['naziv']}",
                 contents=(f"Novi prijedlog projekta #{p['id']}.\n\n"
                           f"Predlagatelj: {p['predlagatelj']}\n"
                           f"Naziv: {p['naziv']}\n"
                           f"Predlozena oznaka: {p['oznaka']}\n"
                           f"Klijent: {p['klijent']}\n"
                           f"Gradiliste: {p['gradiliste']}\n"
                           f"Opis: {p['opis']}\n\n"
                           f"Odobrite na stranici Odobravanje."))
        st.success(f"📤 Poslano na: {', '.join(rec)}")
    except Exception as e:
        st.error(f"Greska pri slanju: {e}")
