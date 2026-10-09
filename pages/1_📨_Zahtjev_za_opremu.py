"""Zahtjev za koristenje opreme -> upis u koristenje_opreme (status 'na_cekanju')."""
import os, sys, tempfile
from datetime import datetime

import streamlit as st
from openpyxl import Workbook

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada
from obavijest import posalji, prikazi_status, email_osobe

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


@st.cache_data(ttl=300)
def ucitaj_ist_projekte():
    """Odobreni, nezavrseni projekti (istrazivacki prvi); prazno ako baza nije nadogradena."""
    try:
        return fetch("""SELECT id, coalesce(akronim, oznaka),
                               CASE WHEN vrsta = 'istrazivacki' THEN 'istrazivacki'
                                    ELSE 'strucni: ' || coalesce(naziv, '') END
                        FROM projekti
                        WHERE status_odobrenja = 'odobreno'
                          AND coalesce(faza, '') <> 'zavrseno'
                        ORDER BY (vrsta = 'istrazivacki') DESC, id DESC;""")
    except Exception:
        return []


def spremi_zahtjev(oprema_id, v_od, v_do, materijal, potreba, opis, podnositelj, sati,
                   ip_id=None, provoditelj=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO koristenje_opreme
                    (oprema_id, vrijeme_od, vrijeme_do, materijal,
                     potrebe_ispitivanja, opis, podnositelj, sati_koristenja, status,
                     projekt_id, provoditelj)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'na_cekanju',%s,%s);""",
                (oprema_id, v_od, v_do, materijal, potreba, opis, podnositelj, sati,
                 ip_id, provoditelj))
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
            f"SUMMARY:{z['Oprema']} - {z['Provoditelj']}\n"
            "LOCATION:Laboratorij za geotehniku, Rijeka\n"
            f"DESCRIPTION:Provoditelj: {z['Provoditelj']}\\nPodnositelj: {z['Podnositelj']}"
            f"\\nMaterijal: {z['Materijal']}\\nPotreba: {z['Potreba']}\n"
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

ist_projekti = ucitaj_ist_projekte()
ip_id, ip_akr = None, ""
if ist_projekti:
    ip_opcije = ["— nije vezano uz projekt —"] + [f"{a}  ·  {n}" for (_i, a, n) in ist_projekti]
    ipi = st.selectbox("Projekt", range(len(ip_opcije)),
                       format_func=lambda i: ip_opcije[i],
                       help="Za koji se projekt ispitivanje radi (istrazivacki: HRZZ, NPOO, "
                            "JICA ... ili strucni posao). Oprema moze biti nabavljena "
                            "na drugom projektu.")
    if ipi > 0:
        ip_id, ip_akr = ist_projekti[ipi - 1][0], ist_projekti[ipi - 1][1]

st.subheader("⏱️ Vrijeme")
c1, c2 = st.columns(2)
with c1:
    d1 = st.date_input("Datum pocetka"); t1 = st.time_input("Vrijeme pocetka")
with c2:
    d2 = st.date_input("Datum zavrsetka"); t2 = st.time_input("Vrijeme zavrsetka")

opis = st.text_area("Kratki opis ispitivanja")

st.subheader("👤 Tko")
podnositelj = st.selectbox("Podnositelj", osobe + ["Ostalo (upisi)"],
                           help="Tko podnosi zahtjev i odgovara za njega.")
mail_podnositelja = email_osobe(podnositelj)
if podnositelj == "Ostalo (upisi)":
    podnositelj = st.text_input("Ime podnositelja")
    mail_podnositelja = st.text_input("Vas e-mail za kopiju (nije obavezno)",
                                      placeholder="ime.prezime@...")

isti = st.checkbox("Podnositelj je ujedno i provoditelj ispitivanja", value=True)
provoditelj, mail_provoditelja = None, None
if not isti:
    DRUGI = "Drugi — upisi (student, doktorand, vanjski suradnik)"
    p_opcije = [o for o in osobe if o != podnositelj] + [DRUGI]
    provoditelj = st.selectbox("Provoditelj ispitivanja", p_opcije,
                               help="Tko ce raditi na uredaju.")
    mail_provoditelja = email_osobe(provoditelj)
    if provoditelj == DRUGI:
        provoditelj = st.text_input("Ime i prezime provoditelja")

v_od = datetime.combine(d1, t1); v_do = datetime.combine(d2, t2)
sati = round(max((v_do - v_od).total_seconds() / 3600, 0), 2)
st.info(f"Trajanje: **{sati} h**")

st.divider()
if st.button("📨 Posalji zahtjev", type="primary"):
    if v_do <= v_od:
        st.error("Zavrsetak mora biti nakon pocetka.")
    elif not podnositelj:
        st.error("Upisi podnositelja.")
    elif not isti and not (provoditelj or "").strip():
        st.error("Upisi provoditelja ispitivanja.")
    else:
        prov = (provoditelj or "").strip() or None
        try:
            spremi_zahtjev(oid, v_od, v_do, materijal, potreba, opis, podnositelj, sati,
                           ip_id, prov)
            z = {
                "Inv. br.": inv_br or "", "Oprema": naziv_opreme,
                "Odgovorna osoba": odg or "", "Materijal": materijal,
                "Potreba": potreba, "Projekt": ip_akr,
                "Datum od": v_od.strftime("%Y-%m-%d %H:%M"),
                "Datum do": v_do.strftime("%Y-%m-%d %H:%M"), "Sati": sati,
                "Opis": opis, "Podnositelj": podnositelj,
                "Provoditelj": prov or podnositelj, "Status": "na_cekanju"}
            st.session_state["zapis"] = z
            st.success("✅ Zahtjev poslan i ceka odobrenje.")
            st.dataframe([z], use_container_width=True)
            # --- automatska obavijest (voditelj + laborant, kopija podnositelju/provoditelju)
            posalji("mail_zahtjev",
                    f"Novi zahtjev (na cekanju): {z['Oprema']}",
                    (f"Novi zahtjev za koristenje opreme.\n\n"
                     f"Podnositelj: {z['Podnositelj']}\n"
                     f"Provoditelj: {z['Provoditelj']}\n"
                     f"Oprema: {z['Oprema']} (inv. {z['Inv. br.']})\n"
                     f"Projekt: {z.get('Projekt') or '—'}\n"
                     f"Vrijeme: {z['Datum od']} - {z['Datum do']} ({z['Sati']} h)\n"
                     f"Opis: {z['Opis']}\n\n"
                     f"Zahtjev ceka odobrenje voditelja ili laboranta."),
                    prilozi=[napravi_excel(z), napravi_ics(z, v_od, v_do)],
                    cc=[mail_podnositelja, mail_provoditelja])
        except Exception as e:
            st.error(f"Greska: {e}")

prikazi_status("mail_zahtjev")
