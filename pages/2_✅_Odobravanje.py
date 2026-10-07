"""Odobravanje zahtjeva — voditelj/laborant odobrava ili odbija (biljezi tko i kada)."""
import os, sys
from datetime import datetime

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, execute, prikazi_verziju, sada, lokalno
from auth import trazi_prijavu

st.set_page_config(page_title="Odobravanje", page_icon="✅")
prikazi_verziju()

# 🔒 samo voditelj/laborant
tko = trazi_prijavu("Odobravanje")


def zahtjevi(status):
    return fetch("""
        SELECT k.id, o.naziv, o.interna_oznaka, k.podnositelj,
               k.vrijeme_od, k.vrijeme_do, k.sati_koristenja,
               k.materijal, k.potrebe_ispitivanja, k.opis
        FROM koristenje_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        WHERE k.status = %s
        ORDER BY k.vrijeme_od;""", (status,))


def osoblje():
    return [r[0] for r in fetch(
        "SELECT ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;")]


def odluci(zid, novi_status, tko):
    execute("""UPDATE koristenje_opreme
               SET status = %s, odobrio = %s, datum_odobrenja = %s
               WHERE id = %s;""", (novi_status, tko, sada(), zid))


st.title("✅ Odobravanje zahtjeva")

st.caption(f"Odluke se biljeze na ime: **{tko}**")
st.divider()
lista = zahtjevi("na_cekanju")

if not lista:
    st.success("🎉 Nema zahtjeva na cekanju.")
else:
    st.caption(f"Na cekanju: **{len(lista)}**")

for (zid, naziv, inv, podn, v_od, v_do, sati, mat, potr, opis) in lista:
    with st.container(border=True):
        st.markdown(f"**{naziv}**  ·  inv. {inv or '—'}")
        c1, c2 = st.columns(2)
        c1.write(f"👤 Podnositelj: **{podn or '—'}**")
        c1.write(f"🧱 Materijal: {mat or '—'}")
        c1.write(f"🎯 Potreba: {potr or '—'}")
        c2.write(f"🕒 Od: {lokalno(v_od):%Y-%m-%d %H:%M}" if v_od else "🕒 Od: —")
        c2.write(f"🕒 Do: {lokalno(v_do):%Y-%m-%d %H:%M}" if v_do else "🕒 Do: —")
        c2.write(f"⏳ Trajanje: {sati or 0} h")
        if opis:
            st.caption(f"📝 {opis}")

        b1, b2, _ = st.columns([1, 1, 3])
        if b1.button("✅ Odobri", key=f"ok{zid}", type="primary"):
            odluci(zid, "odobreno", tko)
            st.success(f"Zahtjev #{zid} odobren ({tko}).")
            st.rerun()
        if b2.button("❌ Odbij", key=f"no{zid}"):
            odluci(zid, "odbijeno", tko)
            st.warning(f"Zahtjev #{zid} odbijen ({tko}).")
            st.rerun()

# --- Povijest ---
st.divider()
with st.expander("📜 Nedavno odluceno"):
    povijest = fetch("""
        SELECT k.id, o.naziv, k.podnositelj, k.status, k.odobrio, k.datum_odobrenja
        FROM koristenje_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        WHERE k.status IN ('odobreno','odbijeno')
        ORDER BY k.datum_odobrenja DESC NULLS LAST
        LIMIT 20;""")
    if povijest:
        st.dataframe(
            [{"#": r[0], "Oprema": r[1], "Podnositelj": r[2], "Status": r[3],
              "Odlucio": r[4], "Kada": (lokalno(r[5]).strftime("%Y-%m-%d %H:%M") if r[5] else "—")}
             for r in povijest],
            use_container_width=True, hide_index=True)
    else:
        st.caption("Jos nema odluka.")
