"""Rjesavanje kvarova — zatvori kvar i vrati uredaj u upotrebu (jednim klikom)."""
import os, sys
from datetime import datetime

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada, lokalno
from auth import trazi_prijavu

st.set_page_config(page_title="Rjesavanje kvarova", page_icon="🔧")
prikazi_verziju()

# 🔒 samo voditelj/laborant
tko = trazi_prijavu("Rjesavanje kvarova")

STATUSI_KVARA = ["prijavljen", "u_popravku", "popravljen", "otpisan"]


def otvoreni_kvarovi():
    return fetch("""
        SELECT k.id, o.id, o.naziv, o.interna_oznaka, o.status,
               k.opis_kvara, k.hitnost, k.prijavio, k.datum_prijave, k.status,
               coalesce(kmp.naziv, k.komponenta_opis) AS komponenta,
               coalesce(kmp.serijski_broj, k.serijski_broj_dijela) AS serijski,
               k.sustav_upotrebljiv, k.zamijenjeno_s
        FROM kvarovi_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        LEFT JOIN komponente kmp ON kmp.id = k.komponenta_id
        WHERE k.status IN ('prijavljen','u_popravku')
        ORDER BY
            CASE k.hitnost WHEN 'visoka' THEN 1 WHEN 'srednja' THEN 2 ELSE 3 END,
            k.datum_prijave;""")


def rijesi_kvar(kvar_id, oprema_id, novi_status_kvara, rjesenje, vrati_u_uporabu):
    """Zatvori kvar i (po zelji) vrati uredaj u upotrebu — u jednoj transakciji."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE kvarovi_opreme
                SET status = %s, rjesenje = %s, datum_rjesenja = %s
                WHERE id = %s;""",
                (novi_status_kvara, rjesenje or None, sada(), kvar_id))
            if vrati_u_uporabu:
                cur.execute("UPDATE oprema SET status = 'u_uporabi' WHERE id = %s;",
                            (oprema_id,))
            elif novi_status_kvara == "otpisan":
                cur.execute("UPDATE oprema SET status = 'rashodovana' WHERE id = %s;",
                            (oprema_id,))
        conn.commit()
    finally:
        conn.close()


def oznaci_u_popravku(kvar_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE kvarovi_opreme SET status = 'u_popravku' WHERE id = %s;",
                        (kvar_id,))
        conn.commit()
    finally:
        conn.close()


st.title("🔧 Rjesavanje kvarova")
st.caption("Zatvori kvar i vrati uredaj u upotrebu.")

try:
    lista = otvoreni_kvarovi()
except Exception as e:
    st.error("Nema veze s bazom."); st.caption(f"Detalj: {e}"); st.stop()

if not lista:
    st.success("🎉 Nema otvorenih kvarova.")
else:
    st.caption(f"Otvoreno: **{len(lista)}**")

BOJE = {"visoka": "🔴", "srednja": "🟡", "niska": "🟢"}

for (kid, oid, naziv, inv, status_opreme, opis, hitnost, prijavio, datum,
     status_kvara, komponenta, serijski, sustav_ok, zamijenjeno) in lista:
    with st.container(border=True):
        st.markdown(f"{BOJE.get(hitnost,'⚪')} **{naziv}**  ·  inv. {inv or '—'}")
        if komponenta:
            st.markdown(f"🔩 Komponenta: **{komponenta}**  ·  s/n **{serijski or '—'}**")
        else:
            st.caption("🔩 Kvar cijelog uredaja")
        if sustav_ok:
            st.success(f"✅ Sustav RADI dalje"
                       + (f" — zamijenjeno: **{zamijenjeno}**" if zamijenjeno else ""))
        elif sustav_ok is False:
            st.error("⛔ Sustav se NE moze koristiti")
        c1, c2 = st.columns(2)
        c1.write(f"👤 Prijavio: **{prijavio or '—'}**")
        c1.write(f"⚠️ Hitnost: **{hitnost}**")
        c2.write(f"📅 {lokalno(datum):%Y-%m-%d %H:%M}" if datum else "📅 —")
        c2.write(f"📌 Kvar: **{status_kvara}**  ·  Oprema: **{status_opreme}**")
        st.caption(f"📝 {opis}")

        if status_kvara == "prijavljen":
            if st.button("🔧 Oznaci 'u popravku'", key=f"pop{kid}"):
                oznaci_u_popravku(kid)
                st.rerun()

        with st.expander("✅ Zatvori kvar"):
            rjesenje = st.text_area("Sto je napravljeno?", key=f"rj{kid}",
                                    placeholder="npr. zamijenjen senzor, umjeren")
            ishod = st.radio("Ishod", ["Popravljen", "Otpisan (rashodovati)"],
                             key=f"is{kid}", horizontal=True)
            vrati = False
            if ishod == "Popravljen":
                vrati = st.checkbox("Vrati uredaj U UPOTREBU", value=True,
                                    key=f"vr{kid}",
                                    help="Uredaj se opet nudi u zahtjev-formi.")
            if st.button("✅ Spremi rjesenje", key=f"sp{kid}", type="primary"):
                if not rjesenje.strip():
                    st.error("Upisi sto je napravljeno.")
                else:
                    try:
                        novi = "popravljen" if ishod == "Popravljen" else "otpisan"
                        rijesi_kvar(kid, oid, novi, rjesenje.strip(), vrati)
                        if vrati:
                            st.success(f"Kvar zatvoren. '{naziv}' je opet U UPOTREBI.")
                        elif novi == "otpisan":
                            st.warning(f"Kvar zatvoren. '{naziv}' je RASHODOVAN.")
                        else:
                            st.info("Kvar zatvoren. Uredaj ostaje van upotrebe.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Greska: {e}")

# --- Povijest ---
st.divider()
with st.expander("📜 Zatvoreni kvarovi"):
    povijest = fetch("""
        SELECT k.id, o.naziv,
               coalesce(kmp.naziv, k.komponenta_opis, 'cijeli uredaj') AS komponenta,
               k.hitnost, k.status, k.rjesenje, k.datum_rjesenja
        FROM kvarovi_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        LEFT JOIN komponente kmp ON kmp.id = k.komponenta_id
        WHERE k.status IN ('popravljen','otpisan')
        ORDER BY k.datum_rjesenja DESC NULLS LAST
        LIMIT 20;""")
    if povijest:
        st.dataframe(
            [{"#": r[0], "Oprema": r[1], "Komponenta": r[2], "Hitnost": r[3],
              "Ishod": r[4], "Rjesenje": r[5],
              "Kada": (lokalno(r[6]).strftime("%Y-%m-%d %H:%M") if r[6] else "—")}
             for r in povijest],
            use_container_width=True, hide_index=True)
    else:
        st.caption("Jos nema zatvorenih kvarova.")
