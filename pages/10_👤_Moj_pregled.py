"""Moj pregled — zahtjevi za opremu prijavljene osobe (kao podnositelja ili provoditelja).

  * brojke: na cekanju / odobreno-predstoji / odradeno (12 mj.) / sati na opremi
  * matrica po danima (kao GitHub): sati koristenja odradenih zahtjeva, zadnjih 12 mjeseci
  * popis zadnjih zahtjeva sa statusom
Administrator moze odabrati bilo koju osobu.
Status 'odradeno' = odobreno i termin je prosao; 'predstoji' = odobreno, termin nije prosao.
"""
import os, sys
from datetime import timedelta
from html import escape

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, prikazi_verziju, lokalno, sada
from auth import trazi_prijavu, je_admin

st.set_page_config(page_title="Moj pregled", page_icon="👤", layout="wide")
prikazi_verziju()

tko = trazi_prijavu("Moj pregled", razina="prijava")

UVJET = "(k.podnositelj = %s OR k.osoba_id = %s)"
BOJE = ["rgba(128,128,128,0.15)", "#9FE1CB", "#5DCAA5", "#1D9E75", "#0F6E56"]


def razina(h):
    if h <= 0:
        return 0
    return 1 if h <= 2 else 2 if h <= 4 else 3 if h < 8 else 4


@st.cache_data(ttl=60)
def osoblje():
    return fetch("SELECT id, ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;")


st.title("👤 Moj pregled")

osobe = osoblje()
imena = [o[1] for o in osobe]
if je_admin():
    osoba = st.selectbox("Osoba", imena, index=imena.index(tko) if tko in imena else 0,
                         help="Administrator moze pogledati pregled bilo koje osobe.")
else:
    osoba = tko
oid = next((i for (i, n) in osobe if n == osoba), None)
st.caption(f"Zahtjevi u kojima je **{osoba}** podnositelj ili provoditelj.")
p = (osoba, oid)

# --- brojke ---
m = fetch(f"""
    SELECT
      count(*) FILTER (WHERE k.status = 'na_cekanju'),
      count(*) FILTER (WHERE k.status = 'odobreno' AND k.vrijeme_do > now()),
      count(*) FILTER (WHERE k.status = 'odobreno' AND k.vrijeme_do <= now()
                         AND k.vrijeme_od >= now() - interval '365 days'),
      coalesce(sum(k.sati_koristenja) FILTER (WHERE k.status = 'odobreno'
                         AND k.vrijeme_do <= now()
                         AND k.vrijeme_od >= now() - interval '365 days'), 0)
    FROM koristenje_opreme k WHERE {UVJET};""", p)[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Na cekanju", m[0])
c2.metric("Odobreno, predstoji", m[1])
c3.metric("Odradeno (12 mj.)", m[2])
c4.metric("Sati na opremi (12 mj.)", f"{float(m[3]):.1f}")

# --- matrica po danima ---
dani = dict(fetch(f"""
    SELECT (k.vrijeme_od AT TIME ZONE 'Europe/Zagreb')::date, sum(k.sati_koristenja)
    FROM koristenje_opreme k
    WHERE {UVJET} AND k.status = 'odobreno' AND k.vrijeme_do <= now()
      AND k.vrijeme_od >= now() - interval '371 days'
    GROUP BY 1;""", p))

danas = sada().date()
kraj_tj = danas + timedelta(days=6 - danas.weekday())          # nedjelja ovog tjedna
pocetak = kraj_tj - timedelta(weeks=53) + timedelta(days=1)    # ponedjeljak prije 53 tjedna
celije, mjeseci = [], []
d = pocetak
while d <= kraj_tj:
    if d.weekday() == 0 and d.day <= 7:
        mjeseci.append((((d - pocetak).days // 7), d.strftime("%m/%y")))
    h = float(dani.get(d, 0) or 0)
    if d > danas:
        celije.append('<div style="width:11px;height:11px"></div>')
    else:
        celije.append(
            f'<div title="{d:%d.%m.%Y.} · {h:.1f} h" style="width:11px;height:11px;'
            f'border-radius:2px;background:{BOJE[razina(h)]}"></div>')
    d += timedelta(days=1)

oznake = "".join(
    f'<span style="position:absolute;left:{t * 14}px">{escape(lbl)}</span>' for t, lbl in mjeseci)
legenda = "".join(
    f'<span style="display:inline-block;width:11px;height:11px;border-radius:2px;'
    f'background:{b};margin:0 1px"></span>' for b in BOJE)
st.markdown("**Koristenje opreme po danima** (odradeni zahtjevi, zadnjih 12 mjeseci)")
st.html(f"""
<div style="overflow-x:auto;font-family:sans-serif">
 <div style="position:relative;height:14px;margin-left:30px;font-size:11px;opacity:.6">{oznake}</div>
 <div style="display:flex;gap:4px">
  <div style="display:grid;grid-template-rows:repeat(7,11px);gap:3px;font-size:10px;
              line-height:11px;opacity:.6;width:26px">
   <span>pon</span><span></span><span>sri</span><span></span><span>pet</span><span></span><span></span>
  </div>
  <div style="display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,11px);gap:3px">
   {''.join(celije)}
  </div>
 </div>
 <div style="font-size:11px;opacity:.6;margin:6px 0 0 30px">0 h {legenda} 8+ h</div>
</div>""")

# --- popis zahtjeva ---
st.markdown("**Zahtjevi** (zadnjih 15)")
rows = fetch(f"""
    SELECT k.vrijeme_od, k.vrijeme_do, o.naziv, k.podnositelj,
           coalesce(k.provoditelj, k.podnositelj), coalesce(pr.akronim, pr.oznaka),
           k.status, k.sati_koristenja, (k.vrijeme_do <= now())
    FROM koristenje_opreme k
    JOIN oprema o ON o.id = k.oprema_id
    LEFT JOIN projekti pr ON pr.id = k.projekt_id
    WHERE {UVJET}
    ORDER BY k.vrijeme_od DESC
    LIMIT 15;""", p)
if not rows:
    st.info("Jos nema zahtjeva.")
else:
    def status(st_, sati, proslo):
        if st_ == "na_cekanju":
            return "🟡 na cekanju"
        if st_ == "odobreno" and not proslo:
            return "🔵 odobreno · predstoji"
        if st_ == "odobreno":
            return f"🟢 odradeno · {float(sati or 0):.1f} h"
        return st_
    st.dataframe(
        [{"Termin": f"{lokalno(r[0]):%d.%m.%Y. %H:%M} – {lokalno(r[1]):%H:%M}"
                    if r[0] and r[1] else "—",
          "Uredaj": r[2], "Podnositelj": r[3], "Provoditelj": r[4],
          "Projekt": r[5] or "—", "Status": status(r[6], r[7], r[8])}
         for r in rows],
        use_container_width=True, hide_index=True)
