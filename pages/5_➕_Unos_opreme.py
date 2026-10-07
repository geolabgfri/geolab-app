"""
Unos nove opreme — Streamlit forma spojena na Supabase.

Rjesava rucni unos u Supabase Table Editoru:
  - id se dodjeljuje sam (SERIAL),
  - status je padajuci izbornik (nema vise NULL greske),
  - odgovorna osoba se bira po imenu (ne po id-u),
  - interna_oznaka: predlaze sljedeci slobodan broj (mozes prepisati pravim),
  - projekt_nabave: akronim projekta iz kojeg je oprema nabavljena,
  - provjerava duplikat inventarnog broja PRIJE spremanja.

Secrets: [supabase].
"""

from datetime import date

import streamlit as st

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju
from auth import trazi_prijavu

st.set_page_config(page_title="Unos opreme", page_icon="➕")
prikazi_verziju()

# 🔒 samo voditelj/laborant
tko = trazi_prijavu("Unos opreme")

STATUSI = ["u_uporabi", "van_uporabe", "u_servisu", "rashodovana"]


@st.cache_data(ttl=120)
def ucitaj_osoblje():
    return fetch(
        "SELECT id, ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;"
    )


@st.cache_data(ttl=120)
def ucitaj_projekte_nabave():
    rows = fetch(
        "SELECT DISTINCT projekt_nabave FROM oprema "
        "WHERE projekt_nabave IS NOT NULL ORDER BY projekt_nabave;"
    )
    return [r[0] for r in rows]


@st.cache_data(ttl=60)
def predlozi_inv_broj():
    """Sljedeci slobodan broj = max(numericki inv. broj) + 1."""
    rows = fetch(
        """SELECT max(CAST(interna_oznaka AS INTEGER))
           FROM oprema
           WHERE interna_oznaka ~ '^[0-9]+$';"""
    )
    maks = rows[0][0] if rows and rows[0][0] is not None else 0
    return str(maks + 1)


def postoji_inv(inv):
    return bool(fetch("SELECT 1 FROM oprema WHERE interna_oznaka = %s;", (inv,)))


def spremi_opremu(p):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO oprema
                   (interna_oznaka, naziv, proizvodjac, model, serijski_broj,
                    mjerni_raspon, tocnost, projekt_nabave, datum_nabave,
                    interval_umjeravanja_mj, umjerena_do, status, odgovorna_osoba)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING id;""",
                (p["inv"], p["naziv"], p["proizvodjac"], p["model"], p["serijski"],
                 p["raspon"], p["tocnost"], p["projekt_nabave"], p["nabava"],
                 p["interval"], p["umjerena_do"], p["status"], p["odg_id"]),
            )
            novi_id = cur.fetchone()[0]
        conn.commit()
        return novi_id
    finally:
        conn.close()


# ---------------------------- SUCELJE ----------------------------
st.title("➕ Unos nove opreme")
st.caption("id se dodjeljuje sam. Status i odgovorna osoba biraju se iz izbornika.")

try:
    osobe = ucitaj_osoblje()
    projekti_nabave = ucitaj_projekte_nabave()
    prijedlog_inv = predlozi_inv_broj()
except Exception as e:
    st.error("Ne mogu se spojiti na bazu. Provjeri Secrets ([supabase]).")
    st.caption(f"Detalj: {e}")
    st.stop()

if not osobe:
    st.warning("Nema aktivnog osoblja u bazi.")
    st.stop()

st.subheader("Osnovno")
c1, c2 = st.columns(2)
with c1:
    inv = st.text_input("Inventarni broj *", value=prijedlog_inv,
                        help="Prijedlog je sljedeci slobodan broj — prepisi stvarnim "
                             "inventarnim brojem ako ga uredaj vec ima.")
with c2:
    status = st.selectbox("Status *", STATUSI, index=0)

naziv = st.text_input("Naziv uredaja *")

oi = st.selectbox("Odgovorna osoba *", range(len(osobe)),
                  format_func=lambda i: osobe[i][1])
odg_id = osobe[oi][0]

# projekt nabave: postojeci akronim ili novi
pn_opcije = projekti_nabave + ["➕ Novi projekt nabave"]
pi_ = st.selectbox("Projekt nabave (akronim) *", range(len(pn_opcije)),
                   format_func=lambda i: pn_opcije[i],
                   help="Iz kojeg je projekta oprema nabavljena (npr. LG 1, GF Ri).")
if pn_opcije[pi_] == "➕ Novi projekt nabave":
    projekt_nabave = st.text_input("Akronim novog projekta", placeholder="npr. LG 6")
else:
    projekt_nabave = pn_opcije[pi_]

with st.expander("Dodatni podaci (nije obavezno)"):
    d1, d2 = st.columns(2)
    with d1:
        proizvodjac = st.text_input("Proizvodjac")
        serijski = st.text_input("Serijski broj")
        raspon = st.text_input("Mjerni raspon")
    with d2:
        model = st.text_input("Model")
        tocnost = st.text_input("Tocnost / rezolucija")
        interval = st.number_input("Interval umjeravanja (mjeseci)",
                                   min_value=0, step=1, value=0)

    e1, e2 = st.columns(2)
    with e1:
        ima_nabavu = st.checkbox("Upisi datum nabave")
        nabava = st.date_input("Datum nabave", value=date.today()) if ima_nabavu else None
    with e2:
        ima_umjer = st.checkbox("Upisi 'umjerena do'")
        umjerena_do = st.date_input("Umjerena do", value=date.today()) if ima_umjer else None

st.divider()
if st.button("➕ Spremi opremu", type="primary"):
    greske = []
    if not inv.strip():
        greske.append("Upisi inventarni broj.")
    if not naziv.strip():
        greske.append("Upisi naziv uredaja.")
    if not projekt_nabave:
        greske.append("Odaberi ili upisi akronim projekta nabave.")

    if not greske and postoji_inv(inv.strip()):
        greske.append(f"Inventarni broj '{inv.strip()}' vec postoji u bazi. "
                      f"Prijedlog slobodnog: {predlozi_inv_broj()}")

    if greske:
        for g in greske:
            st.error(g)
    else:
        try:
            novi_id = spremi_opremu({
                "inv": inv.strip(), "naziv": naziv.strip(),
                "proizvodjac": proizvodjac or None, "model": model or None,
                "serijski": serijski or None, "raspon": raspon or None,
                "tocnost": tocnost or None, "projekt_nabave": projekt_nabave,
                "nabava": nabava, "interval": (interval or None),
                "umjerena_do": umjerena_do, "status": status, "odg_id": odg_id,
            })
            st.success(f"✅ Oprema spremljena (id {novi_id}, inv. {inv.strip()}).")
            if status == "u_uporabi":
                st.info("Uredaj je odmah dostupan u formi za zahtjev koristenja.")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Greska pri spremanju: {e}")
