"""Zahtjev za koristenje opreme -> upis u koristenje_opreme (status 'na_cekanju')."""
import os, sys, tempfile
from datetime import datetime

import streamlit as st
from openpyxl import Workbook

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada

st.set_page_config(page_title="Zahtjev za opremu", page_icon="📨")
prikazi_verziju()


@st.cache_data(ttl=300)
def ucitaj_opremu():
    return fetch("""
        SELECT o.id, o.interna_oznaka, o.naziv, s.ime_prezime
        FROM oprema o
        LEFT JOIN osoblje s ON s.id = o.odgovorna_osoba
        WHERE o.status = 'u_uporabi'
        ORDER BY o.naziv;""")


@st.cache_data(ttl=300)
def ucitaj_osoblje():
    return [r[0] for r in fetch(
        "SELECT ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;")]


def spremi_zahtjev(oprema_id, v_od, v_do, materijal, potreba, opis, podnositelj, sati):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO koristenje_opreme
                    (oprema_id, vrijeme_od, vrijeme_do, materijal,
                     potrebe_ispitivanja, opis, podnositelj, sati_koristenja, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'na_cekanju');""",
                (oprema_id, v_od, v_do, materijal, potreba, opis, podnositelj, sati))
        conn.commit()
    finally:
        conn.close()


def napravi_excel(z):
    p = os.path.join(tempfile.gettempdir(), "zahtjev.xlsx")
    wb = Workbook(); ws = wb.active; ws.title = "Zahtjev"
    ws.append(list(z.keys())); ws.append(list(z.values())); wb.save(p)
    return p


def napravi_ics(z, v_od, v_do):
    p = os.path.join(tempfile.gettempdir(), "zahtjev.ics")
    with open(p, "w", encoding="utf-8") as f:
        f.write(
            "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Lab Geotehnika//HR\nBEGIN:VEVENT\n"
            f"UID:{sada().strftime('%Y%m%d%H%M%S')}@lab.geotehnika.hr\n"
            f"DTSTAMP:{sada().strftime('%Y%m%dT%H%M%S')}\n"
            f"DTSTART:{v_od.strftime('%Y%m%dT%H%M%S')}\n"
            f"DTEND:{v_do.strftime('%Y%m%dT%H%M%S')}\n"
            f"SUMMARY:{z['Oprema']} - {z['Podnositelj']}\n"
            "LOCATION:Laboratorij za geotehniku, Rijeka\n"
            f"DESCRIPTION:Materijal: {z['Materijal']}\\nPotreba: {z['Potreba']}\n"
            "BEGIN:VALARM\nTRIGGER:-PT30M\nACTION:DISPLAY\n"
            "DESCRIPTION:Podsjetnik\nEND:VALARM\nEND:VEVENT\nEND:VCALENDAR\n")
    return p


st.title("📨 Zahtjev za koristenje opreme")
st.caption("Nakon slanja zahtjev ceka odobrenje.")

try:
    oprema_rows = ucitaj_opremu(); osobe = ucitaj_osoblje()
except Exception as e:
    st.error("Nema veze s bazom."); st.caption(f"Detalj: {e}"); st.stop()

if not oprema_rows:
    st.warning("Nema dostupne opreme (sva je van uporabe ili u servisu)."); st.stop()

labele = [f"{n}  ·  inv. {i or '—'}" for (_id, i, n, _o) in oprema_rows]
idx = st.selectbox("Oprema", range(len(labele)), format_func=lambda i: labele[i])
oid, inv_br, naziv_opreme, odg = oprema_rows[idx]

materijal = st.selectbox("Vrsta materijala",
                         ["Glina", "Prah", "Pijesak", "Sljunak", "Stijena", "Ostalo"])
potreba = st.selectbox("Za koje potrebe",
                       ["Nastava", "Zavrsni rad", "Diplomski rad", "Doktorski rad",
                        "Znanstveni rad", "Struka", "Ostalo"])

st.subheader("⏱️ Vrijeme")
c1, c2 = st.columns(2)
with c1:
    d1 = st.date_input("Datum pocetka"); t1 = st.time_input("Vrijeme pocetka")
with c2:
    d2 = st.date_input("Datum zavrsetka"); t2 = st.time_input("Vrijeme zavrsetka")

opis = st.text_area("Kratki opis ispitivanja")
podnositelj = st.selectbox("Podnositelj", osobe + ["Ostalo (upisi)"])
if podnositelj == "Ostalo (upisi)":
    podnositelj = st.text_input("Ime podnositelja")

v_od = datetime.combine(d1, t1); v_do = datetime.combine(d2, t2)
sati = round(max((v_do - v_od).total_seconds() / 3600, 0), 2)
st.info(f"Trajanje: **{sati} h**")

st.divider()
if st.button("📨 Posalji zahtjev", type="primary"):
    if v_do <= v_od:
        st.error("Zavrsetak mora biti nakon pocetka.")
    elif not podnositelj:
        st.error("Upisi podnositelja.")
    else:
        try:
            spremi_zahtjev(oid, v_od, v_do, materijal, potreba, opis, podnositelj, sati)
            st.session_state["zapis"] = {
                "Inv. br.": inv_br or "", "Oprema": naziv_opreme,
                "Odgovorna osoba": odg or "", "Materijal": materijal,
                "Potreba": potreba, "Datum od": v_od.strftime("%Y-%m-%d %H:%M"),
                "Datum do": v_do.strftime("%Y-%m-%d %H:%M"), "Sati": sati,
                "Opis": opis, "Podnositelj": podnositelj, "Status": "na_cekanju"}
            st.session_state["v_od"] = v_od; st.session_state["v_do"] = v_do
            st.success("✅ Zahtjev poslan i ceka odobrenje.")
            st.dataframe([st.session_state["zapis"]], use_container_width=True)
        except Exception as e:
            st.error(f"Greska: {e}")

st.divider()
st.subheader("📧 Obavijest e-mailom")
if "email" not in st.secrets:
    st.info("E-mail nije konfiguriran.")
elif "zapis" not in st.session_state:
    st.caption("Prvo posalji zahtjev.")
else:
    if st.button("📧 Posalji e-mail voditelju i laborantu"):
        try:
            import yagmail
            z = st.session_state["zapis"]
            xlsx = napravi_excel(z)
            ics = napravi_ics(z, st.session_state["v_od"], st.session_state["v_do"])
            rec = list(st.secrets["email"]["recipients"])
            yag = yagmail.SMTP(st.secrets["email"]["sender"],
                               st.secrets["email"]["app_password"])
            yag.send(to=rec, subject=f"Novi zahtjev (na cekanju): {z['Oprema']}",
                     contents=(f"Novi zahtjev za koristenje opreme.\n\n"
                               f"Podnositelj: {z['Podnositelj']}\n"
                               f"Oprema: {z['Oprema']} (inv. {z['Inv. br.']})\n"
                               f"Vrijeme: {z['Datum od']} - {z['Datum do']} ({z['Sati']} h)\n"
                               f"Opis: {z['Opis']}\n\nOdobrite na stranici Odobravanje."),
                     attachments=[xlsx, ics])
            st.success(f"📤 Poslano na: {', '.join(rec)}")
        except Exception as e:
            st.error(f"Greska pri slanju: {e}")
