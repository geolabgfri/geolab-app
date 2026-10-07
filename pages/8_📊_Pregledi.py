"""Pregledi — sto se dogada u laboratoriju. Sve se moze preuzeti kao CSV."""
import os, sys
from datetime import date, timedelta

import streamlit as st
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, prikazi_verziju, lokalno
from auth import trazi_prijavu

st.set_page_config(page_title="Pregledi", page_icon="📊", layout="wide")
prikazi_verziju()

tko = trazi_prijavu("Pregledi")


def df(rows, stupci):
    return pd.DataFrame(rows, columns=stupci) if rows else pd.DataFrame(columns=stupci)


def preuzmi(data, ime):
    if not data.empty:
        st.download_button("⬇️ Preuzmi CSV",
                           data.to_csv(index=False).encode("utf-8-sig"),
                           file_name=ime, mime="text/csv", key=ime)


st.title("📊 Pregledi")

# ---------------------- RAZDOBLJE ----------------------
danas = date.today()


def raspon(izbor):
    g = danas.year
    if izbor == "Ovaj mjesec":
        return danas.replace(day=1), danas
    if izbor == "Prosli mjesec":
        prvi = danas.replace(day=1)
        zadnji_prosli = prvi - timedelta(days=1)
        return zadnji_prosli.replace(day=1), zadnji_prosli
    if izbor == "Zadnja 3 mjeseca":
        return danas - timedelta(days=90), danas
    if izbor == "Ova godina":
        return date(g, 1, 1), danas
    if izbor == "Prosla godina":
        return date(g - 1, 1, 1), date(g - 1, 12, 31)
    if izbor == "Sve":
        return date(2000, 1, 1), date(2100, 12, 31)
    return None, None  # rucno


izbori = ["Ovaj mjesec", "Prosli mjesec", "Zadnja 3 mjeseca",
          "Ova godina", "Prosla godina", "Sve", "Rucni odabir"]
izbor = st.radio("Razdoblje", izbori, index=2, horizontal=True)

if izbor == "Rucni odabir":
    c1, c2 = st.columns(2)
    od = c1.date_input("Od", value=danas - timedelta(days=90))
    do = c2.date_input("Do", value=danas)
else:
    od, do = raspon(izbor)

if izbor == "Sve":
    st.caption("Prikazuje **sve** zapise, bez vremenskog ogranicenja.")
else:
    st.caption(f"Razdoblje: **{od:%d.%m.%Y.} – {do:%d.%m.%Y.}**")

if od > do:
    st.error("Datum 'Od' mora biti prije datuma 'Do'.")
    st.stop()

tabs = st.tabs(["🔧 Oprema", "📋 Poslovi", "🧪 Uzorci", "🛠️ Kvarovi"])

# ============================ OPREMA ============================
with tabs[0]:
    st.subheader("Iskoristenost opreme (odobreni zahtjevi)")
    rows = fetch("""
        SELECT o.naziv, o.interna_oznaka,
               count(*) AS broj_koristenja,
               round(sum(coalesce(k.sati_koristenja,0))::numeric, 1) AS ukupno_sati
        FROM koristenje_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        WHERE k.status = 'odobreno'
          AND k.vrijeme_od::date BETWEEN %s AND %s
        GROUP BY o.naziv, o.interna_oznaka
        ORDER BY ukupno_sati DESC NULLS LAST;""", (od, do))
    d = df(rows, ["Oprema", "Inv. br.", "Broj koristenja", "Ukupno sati"])
    if d.empty:
        st.info("Nema odobrenih koristenja u ovom razdoblju.")
    else:
        c1, c2 = st.columns([2, 3])
        c1.dataframe(d, use_container_width=True, hide_index=True)
        top = d.head(10).set_index("Oprema")["Ukupno sati"]
        c2.bar_chart(top)
        preuzmi(d, "iskoristenost_opreme.csv")

    st.divider()
    st.subheader("Stanje opreme (trenutno)")
    rows = fetch("SELECT status, count(*) FROM oprema GROUP BY status ORDER BY status;")
    d = df(rows, ["Status", "Broj"])
    c1, c2 = st.columns([1, 2])
    c1.dataframe(d, use_container_width=True, hide_index=True)
    if not d.empty:
        c2.bar_chart(d.set_index("Status")["Broj"])

    st.divider()
    st.subheader("⚠️ Umjeravanje istjece / isteklo")
    rows = fetch("""
        SELECT interna_oznaka, naziv, umjerena_do,
               (umjerena_do - CURRENT_DATE) AS dana_do_isteka, status
        FROM oprema
        WHERE umjerena_do IS NOT NULL
          AND umjerena_do <= CURRENT_DATE + 60
        ORDER BY umjerena_do;""")
    d = df(rows, ["Inv. br.", "Oprema", "Umjerena do", "Dana do isteka", "Status"])
    if d.empty:
        st.success("Nema opreme kojoj umjeravanje istjece u sljedecih 60 dana.")
    else:
        st.warning(f"{len(d)} uredaj(a) — provjeri umjeravanje!")
        st.dataframe(d, use_container_width=True, hide_index=True)
        preuzmi(d, "umjeravanje.csv")

# ============================ POSLOVI ============================
with tabs[1]:
    st.subheader("Poslovi po fazi")
    rows = fetch("""SELECT coalesce(faza,'—'), count(*) FROM projekti
                    WHERE datum_otvaranja BETWEEN %s AND %s
                    GROUP BY faza ORDER BY 1;""", (od, do))
    d = df(rows, ["Faza", "Broj"])
    c1, c2 = st.columns([1, 2])
    c1.dataframe(d, use_container_width=True, hide_index=True)
    if not d.empty:
        c2.bar_chart(d.set_index("Faza")["Broj"])

    st.divider()
    st.subheader("Poslovi u razdoblju")
    rows = fetch("""
        SELECT p.oznaka, p.naziv, k.naziv, k.tip, p.faza, p.datum_otvaranja,
               p.broj_ponude, p.broj_izvjestaja,
               (SELECT count(*) FROM uzorci u WHERE u.projekt_id = p.id) AS uzoraka
        FROM projekti p JOIN klijenti k ON k.id = p.klijent_id
        WHERE p.datum_otvaranja BETWEEN %s AND %s
        ORDER BY p.id DESC;""", (od, do))
    d = df(rows, ["Oznaka", "Naziv", "Klijent", "Tip", "Faza", "Otvoren",
                  "Br. ponude", "Br. izvjestaja", "Uzoraka"])
    st.dataframe(d, use_container_width=True, hide_index=True)
    preuzmi(d, "poslovi.csv")

    st.divider()
    st.subheader("Komercijalni vs interni")
    rows = fetch("""
        SELECT k.tip, count(*) FROM projekti p
        JOIN klijenti k ON k.id = p.klijent_id
        WHERE p.datum_otvaranja BETWEEN %s AND %s
        GROUP BY k.tip;""", (od, do))
    d = df(rows, ["Tip", "Broj poslova"])
    if not d.empty:
        st.bar_chart(d.set_index("Tip")["Broj poslova"])

# ============================ UZORCI ============================
with tabs[2]:
    st.subheader("Uzorci po statusu (trenutno)")
    rows = fetch("SELECT status, count(*) FROM uzorci GROUP BY status ORDER BY status;")
    d = df(rows, ["Status", "Broj"])
    c1, c2 = st.columns([1, 2])
    c1.dataframe(d, use_container_width=True, hide_index=True)
    if not d.empty:
        c2.bar_chart(d.set_index("Status")["Broj"])

    st.divider()
    st.subheader("Uzorci u razdoblju")
    rows = fetch("""
        SELECT u.oznaka_uzorka, p.oznaka, u.vrsta, u.status,
               s.ime_prezime, u.datum_prijema,
               (SELECT count(*) FROM ispitivanja i WHERE i.uzorak_id = u.id) AS ispitivanja
        FROM uzorci u
        JOIN projekti p ON p.id = u.projekt_id
        LEFT JOIN osoblje s ON s.id = u.zaprimio
        WHERE u.datum_prijema::date BETWEEN %s AND %s
        ORDER BY u.datum_prijema DESC;""", (od, do))
    d = df(rows, ["Uzorak", "Posao", "Vrsta", "Status", "Zaprimio",
                  "Datum prijema", "Ispitivanja"])
    if not d.empty:
        d["Datum prijema"] = d["Datum prijema"].apply(
            lambda x: lokalno(x).strftime("%Y-%m-%d") if x else "")
    st.dataframe(d, use_container_width=True, hide_index=True)
    preuzmi(d, "uzorci.csv")

# ============================ KVAROVI ============================
with tabs[3]:
    st.subheader("Kvarovi po uredaju")
    rows = fetch("""
        SELECT o.naziv, o.interna_oznaka, count(*) AS broj,
               sum(CASE WHEN k.status IN ('prijavljen','u_popravku') THEN 1 ELSE 0 END) AS otvoreno
        FROM kvarovi_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        WHERE k.datum_prijave::date BETWEEN %s AND %s
        GROUP BY o.naziv, o.interna_oznaka
        ORDER BY broj DESC;""", (od, do))
    d = df(rows, ["Oprema", "Inv. br.", "Ukupno kvarova", "Otvoreno"])
    if d.empty:
        st.success("Nema prijavljenih kvarova u ovom razdoblju.")
    else:
        c1, c2 = st.columns([2, 3])
        c1.dataframe(d, use_container_width=True, hide_index=True)
        c2.bar_chart(d.head(10).set_index("Oprema")["Ukupno kvarova"])
        preuzmi(d, "kvarovi_po_opremi.csv")

    st.divider()
    st.subheader("Kvarovi u razdoblju")
    rows = fetch("""
        SELECT o.naziv,
               coalesce(kmp.naziv, k.komponenta_opis, 'cijeli uredaj') AS komponenta,
               coalesce(kmp.serijski_broj, k.serijski_broj_dijela) AS sn,
               k.hitnost, k.status, k.sustav_upotrebljiv,
               k.prijavio, k.datum_prijave
        FROM kvarovi_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        LEFT JOIN komponente kmp ON kmp.id = k.komponenta_id
        WHERE k.datum_prijave::date BETWEEN %s AND %s
        ORDER BY k.datum_prijave DESC;""", (od, do))
    d = df(rows, ["Oprema", "Komponenta", "Serijski br.", "Hitnost", "Status",
                  "Sustav radi", "Prijavio", "Datum"])
    if not d.empty:
        d["Datum"] = d["Datum"].apply(
            lambda x: lokalno(x).strftime("%Y-%m-%d %H:%M") if x else "")
        d["Sustav radi"] = d["Sustav radi"].map({True: "DA", False: "NE"}).fillna("—")
    st.dataframe(d, use_container_width=True, hide_index=True)
    preuzmi(d, "kvarovi.csv")
