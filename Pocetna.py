"""
Laboratorij za geotehniku — glavna aplikacija (ulazna datoteka).

Izbornik se gradi prema ulozi prijavljene osobe (st.navigation):
  svi             — Pocetna, Zahtjev za opremu, Prijava kvara
  projekti        — + Prijedlog projekta     (administrator ili znanstveno zvanje)
  administrator   — + sve administrativne stranice
Stranice koje osoba ne smije koristiti ne vide se u izborniku.
"""
import streamlit as st

from db import fetch, provjeri_vezu, prikazi_verziju, VERZIJA
from auth import (forma_prijave, odjava, prijavljen, je_admin, smije_projekte)

st.set_page_config(page_title="Laboratorij — geotehnika", page_icon="🧪", layout="wide")


# ---------------------------- POCETNA ----------------------------
def pocetna():
    prikazi_verziju()
    st.title("🧪 Laboratorij za geotehniku")
    st.caption(f"Odaberi radnju u izborniku lijevo.  ·  verzija {VERZIJA}")

    ok, poruka = provjeri_vezu()
    if not ok:
        st.error("Nema veze s bazom. Provjeri Secrets ([supabase]).")
        st.caption(f"Detalj: {poruka}")
        st.stop()

    if not je_admin():
        st.markdown(
            "- **📨 Zahtjev za opremu** — zahtjev za koristenje uredaja\n"
            "- **🛠️ Prijava kvara** — prijava kvara uredaja ili komponente\n"
            "- **🗂️ Prijedlog projekta** — za administratore i osoblje u "
            "znanstveno-nastavnom zvanju (potrebna prijava)")
        if not prijavljen():
            st.caption("Ostale stranice vide se nakon prijave, prema ulozi.")
        return

    st.success("Veza s bazom je uspostavljena.")
    st.subheader("Pregled")
    try:
        c1, c2, c3, c4, c5 = st.columns(5)
        na_cekanju = fetch(
            "SELECT count(*) FROM koristenje_opreme WHERE status = 'na_cekanju';")[0][0]
        c1.metric("Zahtjevi na cekanju", na_cekanju)
        u_servisu = fetch("SELECT count(*) FROM oprema WHERE status = 'u_servisu';")[0][0]
        c2.metric("Oprema u servisu", u_servisu)
        c3.metric("Ukupno opreme", fetch("SELECT count(*) FROM oprema;")[0][0])
        c4.metric("Uzoraka u bazi", fetch("SELECT count(*) FROM uzorci;")[0][0])
        kvarovi = fetch("SELECT count(*) FROM kvarovi_opreme "
                        "WHERE status IN ('prijavljen','u_popravku');")[0][0]
        c5.metric("Otvoreni kvarovi", kvarovi)

        if na_cekanju:
            st.warning(f"⏳ {na_cekanju} zahtjev(a) ceka odobrenje "
                       f"— vidi stranicu **Odobravanje**.")
        if kvarovi:
            st.error(f"🔧 {kvarovi} otvoren(ih) kvar(ova) "
                     f"— vidi stranicu **Rjesavanje kvarova**.")
    except Exception as e:
        st.info("Pregled trenutno nije dostupan.")
        st.caption(f"Detalj: {e}")

    try:
        prijedlozi = fetch(
            "SELECT count(*) FROM projekti "
            "WHERE vrsta = 'istrazivacki' AND status_odobrenja = 'na_cekanju';")[0][0]
        if prijedlozi:
            st.warning(f"🗂️ {prijedlozi} istrazivacki projekt(a) ceka odobrenje "
                       f"— vidi stranicu **Odobravanje**.")
    except Exception:
        pass

    st.divider()
    st.markdown(
        """
| Stranica | Cemu sluzi | Tko vidi |
|---|---|---|
| 📨 Zahtjev za opremu | podnosenje zahtjeva za koristenje uredaja | svi |
| 🛠️ Prijava kvara | prijava kvara uredaja ili komponente | svi |
| 🗂️ Prijedlog projekta | prijedlog istrazivackog projekta (HRZZ, NPOO, JICA ...) | admin, zvanje |
| ✅ Odobravanje | zahtjevi za opremu i istrazivacki projekti | admin |
| 📥 Prijem uzorka | zaprimanje uzorka | admin |
| ➕ Unos opreme | dodavanje uredaja u inventar | admin |
| 🔧 Rjesavanje kvarova | zatvaranje kvara, povratak u upotrebu | admin |
| 📝 Novi posao | strucni posao: upit → ponuda → narudzbenica → izvjestaj | admin |
| 📊 Pregledi | oprema, poslovi, uzorci, kvarovi, istrazivacki projekti (+CSV) | admin |
"""
    )
    st.caption("admin = stupac *administrator* u tablici osoblje; "
               "zvanje = stupac *znanstveno_zvanje* (doc., izv. prof., prof.).")


def stranica_prijave():
    prikazi_verziju()
    forma_prijave()


# ---------------------------- IZBORNIK ----------------------------
def P(datoteka, naslov, ikona):
    return st.Page(f"pages/{datoteka}", title=naslov, icon=ikona)


opce = [
    st.Page(pocetna, title="Pocetna", icon="🧪", default=True),
    P("1_📨_Zahtjev_za_opremu.py", "Zahtjev za opremu", "📨"),
    P("4_🛠️_Prijava_kvara.py", "Prijava kvara", "🛠️"),
]
izbornik = {"": opce}

if smije_projekte():
    izbornik["Projekti"] = [P("9_🗂️_Prijedlog_projekta.py", "Prijedlog projekta", "🗂️")]

if je_admin():
    izbornik["Administracija"] = [
        P("2_✅_Odobravanje.py", "Odobravanje", "✅"),
        P("3_📥_Prijem_uzorka.py", "Prijem uzorka", "📥"),
        P("5_➕_Unos_opreme.py", "Unos opreme", "➕"),
        P("6_🔧_Rjesavanje_kvarova.py", "Rjesavanje kvarova", "🔧"),
        P("7_📝_Novi_posao.py", "Novi posao", "📝"),
        P("8_📊_Pregledi.py", "Pregledi", "📊"),
    ]

if not prijavljen():
    izbornik[""].append(st.Page(stranica_prijave, title="Prijava", icon="🔒",
                                url_path="prijava"))

with st.sidebar:
    if prijavljen():
        uloge = ([("administrator")] if st.session_state.get("admin") else []) + \
                (["znanstveno zvanje"] if st.session_state.get("zvanje") else [])
        st.success(f"👤 {st.session_state['korisnik']}")
        st.caption("Uloga: " + (", ".join(uloge) if uloge else "bez posebnih ovlasti"))
        if st.button("Odjava"):
            odjava()
            st.rerun()

st.navigation(izbornik).run()
