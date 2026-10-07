"""Prijava kvara — cijeli uredaj ILI komponenta (volume controller, senzor...).

Komponente su SAMOSTALNE (prenosive medu okvirima), pa se ne vezu fiksno na uredaj.
Registar komponenti raste sam: kad prijavis novu, zapamti se za sljedeci put.
"""
import os, sys
from datetime import datetime

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, get_conn, prikazi_verziju, sada

st.set_page_config(page_title="Prijava kvara", page_icon="🛠️")
prikazi_verziju()

CIJELI = "— Cijeli uredaj —"
NOVA = "➕ Nova komponenta (upisi)"


@st.cache_data(ttl=120)
def ucitaj_opremu():
    return fetch("SELECT id, interna_oznaka, naziv, status FROM oprema ORDER BY naziv;")


@st.cache_data(ttl=60)
def ucitaj_komponente():
    return fetch("""SELECT id, naziv, serijski_broj, proizvodjac
                    FROM komponente WHERE aktivna = TRUE
                    ORDER BY naziv, serijski_broj;""")


@st.cache_data(ttl=120)
def ucitaj_osoblje():
    return [r[0] for r in fetch(
        "SELECT ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;")]


def prijavi(oprema_id, opis, hitnost, prijavio, sustav_ok, zamijenjeno,
            komp_id, komp_naziv, komp_sn, komp_proiz, nova_komponenta):
    """Sve u jednoj transakciji: (nova komponenta) -> kvar -> (oprema u servis)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # nova komponenta -> upisi u registar (ili nadi postojecu istu)
            if nova_komponenta and komp_naziv:
                cur.execute("""SELECT id FROM komponente
                               WHERE naziv = %s AND coalesce(serijski_broj,'') = coalesce(%s,'');""",
                            (komp_naziv, komp_sn))
                red = cur.fetchone()
                if red:
                    komp_id = red[0]
                else:
                    cur.execute("""INSERT INTO komponente (naziv, serijski_broj, proizvodjac)
                                   VALUES (%s,%s,%s) RETURNING id;""",
                                (komp_naziv, komp_sn or None, komp_proiz or None))
                    komp_id = cur.fetchone()[0]

            cur.execute("""INSERT INTO kvarovi_opreme
                           (oprema_id, opis_kvara, hitnost, prijavio, datum_prijave,
                            stavljen_van_uporabe, sustav_upotrebljiv, zamijenjeno_s,
                            komponenta_id, komponenta_opis, serijski_broj_dijela)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);""",
                        (oprema_id, opis, hitnost, prijavio, sada(),
                         (not sustav_ok), sustav_ok, zamijenjeno or None,
                         komp_id, komp_naziv or None, komp_sn or None))

            # uredaj ide u servis SAMO ako sustav nije upotrebljiv
            if not sustav_ok:
                cur.execute("UPDATE oprema SET status = 'u_servisu' WHERE id = %s;",
                            (oprema_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------- SUCELJE ----------------------------
st.title("🛠️ Prijava kvara")
st.caption("Prijavi kvar cijelog uredaja ili pojedine komponente.")

try:
    oprema_rows = ucitaj_opremu()
    komponente = ucitaj_komponente()
    osobe = ucitaj_osoblje()
except Exception as e:
    st.error("Nema veze s bazom."); st.caption(f"Detalj: {e}"); st.stop()

if not oprema_rows:
    st.warning("U bazi nema opreme."); st.stop()

# 1) Uredaj / sustav
labele = [f"{n}  ·  inv. {i or '—'}  ·  {s or ''}" for (_id, i, n, s) in oprema_rows]
idx = st.selectbox("Uredaj / sustav", range(len(labele)), format_func=lambda i: labele[i],
                   help="Uz koji je uredaj komponenta bila u trenutku kvara.")
oid, inv_br, naziv_opreme, status_opreme = oprema_rows[idx]

# 2) Sto je u kvaru — cijeli uredaj ili komponenta
st.subheader("Sto je u kvaru?")
komp_labele = [CIJELI] + [
    f"{n}  ·  s/n {sn or '—'}" + (f"  ·  {p}" if p else "")
    for (_id, n, sn, p) in komponente
] + [NOVA]

ki = st.selectbox("Komponenta", range(len(komp_labele)),
                  format_func=lambda i: komp_labele[i])
izbor = komp_labele[ki]

komp_id = None
komp_naziv = komp_sn = komp_proiz = None
nova_komponenta = False

if izbor == CIJELI:
    st.caption("Prijavljuje se kvar cijelog uredaja.")
elif izbor == NOVA:
    nova_komponenta = True
    st.info("Nova komponenta ce se zapamtiti u registru za sljedeci put.")
    k1, k2 = st.columns(2)
    with k1:
        komp_naziv = st.text_input("Naziv komponente *",
                                   placeholder="npr. Volume controller (cell pressure)")
    with k2:
        komp_sn = st.text_input("Serijski broj", placeholder="npr. GDS-12345")
    komp_proiz = st.text_input("Proizvodjac", placeholder="npr. GDS Instruments")
else:
    # postojeca komponenta iz registra
    komp = komponente[ki - 1]  # -1 zbog CIJELI na pocetku
    komp_id, komp_naziv, komp_sn, komp_proiz = komp
    st.success(f"Komponenta: **{komp_naziv}**  ·  s/n **{komp_sn or '—'}**"
               + (f"  ·  {komp_proiz}" if komp_proiz else ""))

# 3) Kvar
st.subheader("Opis kvara")
opis = st.text_area("Sto ne radi? *", placeholder="Sto se tocno dogodilo / kako se ocituje?")
hitnost = st.selectbox("Hitnost", ["niska", "srednja", "visoka"], index=1)

prijavio = st.selectbox("Prijavljuje", osobe + ["Ostalo (upisi)"])
if prijavio == "Ostalo (upisi)":
    prijavio = st.text_input("Ime")

st.subheader("Moze li se sustav i dalje koristiti?")
sustav_lbl = st.radio(
    "Stanje sustava",
    ["✅ DA — sustav radi (komponenta zamijenjena/premoscena)",
     "⛔ NE — sustav se ne moze koristiti (ide u servis)"],
    label_visibility="collapsed",
)
sustav_ok = sustav_lbl.startswith("✅")

zamijenjeno = None
if sustav_ok:
    zamijenjeno = st.text_input(
        "Cime je komponenta zamijenjena / kako je premosceno?",
        placeholder="npr. VC ch15 umjesto VC ch14",
        help="Da se poslije zna zasto uredaj radi iako je komponenta u kvaru.")
    st.caption("Uredaj OSTAJE u upotrebi i dalje se nudi u zahtjev-formi.")
else:
    st.caption("Uredaj ce biti stavljen u servis i vise se nece nuditi za koristenje.")

st.divider()
if st.button("🛠️ Prijavi kvar", type="primary"):
    greske = []
    if not opis.strip():
        greske.append("Upisi opis kvara.")
    if not prijavio:
        greske.append("Upisi tko prijavljuje.")
    if nova_komponenta and not (komp_naziv or "").strip():
        greske.append("Upisi naziv nove komponente.")

    if greske:
        for g in greske:
            st.error(g)
    else:
        try:
            prijavi(oid, opis.strip(), hitnost, prijavio, sustav_ok,
                    (zamijenjeno or "").strip() or None,
                    komp_id, (komp_naziv or "").strip() or None,
                    (komp_sn or "").strip() or None,
                    (komp_proiz or "").strip() or None, nova_komponenta)

            st.session_state["kvar"] = {
                "Uredaj": naziv_opreme, "Inv": inv_br or "",
                "Komponenta": komp_naziv or "cijeli uredaj",
                "Serijski broj": komp_sn or "—",
                "Opis": opis.strip(), "Hitnost": hitnost, "Prijavio": prijavio,
                "Sustav radi": "DA" if sustav_ok else "NE",
                "Zamijenjeno s": (zamijenjeno or "—"),
                "Datum": sada().strftime("%Y-%m-%d %H:%M"),
            }
            st.success("✅ Kvar je prijavljen.")
            if sustav_ok:
                st.info(f"'{naziv_opreme}' OSTAJE u upotrebi"
                        + (f" (zamijenjeno: {zamijenjeno})." if zamijenjeno else "."))
            else:
                st.warning(f"'{naziv_opreme}' je stavljen u servis.")
            if nova_komponenta:
                st.info("Komponenta je dodana u registar.")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Greska: {e}")

# --- E-mail (zgodno za slanje upita servisu) ---
st.divider()
st.subheader("📧 Obavijest / upit za popravak")
if "email" not in st.secrets:
    st.info("E-mail nije konfiguriran.")
elif "kvar" not in st.session_state:
    st.caption("Prvo prijavi kvar.")
else:
    if st.button("📧 Posalji e-mail"):
        try:
            import yagmail
            k = st.session_state["kvar"]
            rec = list(st.secrets["email"]["recipients"])
            yag = yagmail.SMTP(st.secrets["email"]["sender"],
                               st.secrets["email"]["app_password"])
            yag.send(to=rec,
                     subject=f"KVAR ({k['Hitnost']}): {k['Uredaj']} — {k['Komponenta']}",
                     contents=(
                         "Prijavljen je kvar.\n\n"
                         f"Uredaj: {k['Uredaj']} (inv. {k['Inv']})\n"
                         f"Komponenta: {k['Komponenta']}\n"
                         f"Serijski broj: {k['Serijski broj']}\n"
                         f"Hitnost: {k['Hitnost']}\n"
                         f"Sustav i dalje radi: {k['Sustav radi']}\n"
                         f"Zamijenjeno s: {k['Zamijenjeno s']}\n"
                         f"Prijavio: {k['Prijavio']} ({k['Datum']})\n\n"
                         f"Opis kvara:\n{k['Opis']}\n"))
            st.success(f"📤 Poslano na: {', '.join(rec)}")
        except Exception as e:
            st.error(f"Greska pri slanju: {e}")
