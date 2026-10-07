"""
Laboratorij za geotehniku — glavna aplikacija.
Sve forme na jednom mjestu; izbornik je lijevo.
"""
import streamlit as st
from db import fetch, provjeri_vezu, prikazi_verziju, VERZIJA

st.set_page_config(page_title="Laboratorij — geotehnika", page_icon="🧪", layout="wide")
prikazi_verziju()

st.title("🧪 Laboratorij za geotehniku")
st.caption(f"Odaberi radnju u izborniku lijevo.  ·  verzija {VERZIJA}")

ok, poruka = provjeri_vezu()
if not ok:
    st.error("Nema veze s bazom. Provjeri Secrets ([supabase]).")
    st.caption(f"Detalj: {poruka}")
    st.stop()

st.success("Veza s bazom je uspostavljena.")

# --- Kratki pregled stanja ---
st.subheader("Pregled")
try:
    c1, c2, c3, c4, c5 = st.columns(5)

    na_cekanju = fetch(
        "SELECT count(*) FROM koristenje_opreme WHERE status = 'na_cekanju';"
    )[0][0]
    c1.metric("Zahtjevi na cekanju", na_cekanju)

    u_servisu = fetch("SELECT count(*) FROM oprema WHERE status = 'u_servisu';")[0][0]
    c2.metric("Oprema u servisu", u_servisu)

    ukupno_opreme = fetch("SELECT count(*) FROM oprema;")[0][0]
    c3.metric("Ukupno opreme", ukupno_opreme)

    uzoraka = fetch("SELECT count(*) FROM uzorci;")[0][0]
    c4.metric("Uzoraka u bazi", uzoraka)

    kvarovi = fetch(
        "SELECT count(*) FROM kvarovi_opreme "
        "WHERE status IN ('prijavljen','u_popravku');"
    )[0][0]
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

st.divider()
st.markdown(
    """
**Stranice (izbornik lijevo):**

| Stranica | Cemu sluzi | Pristup |
|---|---|---|
| 📨 Zahtjev za opremu | podnosenje zahtjeva za koristenje uredaja | 🌐 svi |
| 🛠️ Prijava kvara | prijava kvara uredaja ili komponente | 🌐 svi |
| ✅ Odobravanje | odobravanje / odbijanje zahtjeva | 🔒 prijava |
| 📥 Prijem uzorka | zaprimanje uzorka | 🔒 prijava |
| ➕ Unos opreme | dodavanje uredaja u inventar | 🔒 prijava |
| 🔧 Rjesavanje kvarova | zatvaranje kvara, povratak u upotrebu | 🔒 prijava |
| 📝 Novi posao | otvaranje posla: upit → ponuda → narudzbenica → izvjestaj | 🔒 prijava |
| 📊 Pregledi | iskoristenost opreme, poslovi, uzorci, kvarovi (+CSV) | 🔒 prijava |
"""
)

st.caption("🔒 = potrebna prijava (voditelj / laborant).  "
           "🌐 = dostupno svima s linkom.")
