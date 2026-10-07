"""Odobravanje — voditelj/laborant odobrava ili odbija (biljezi tko i kada).

Dvije kartice:
  * Zahtjevi za opremu   (koristenje_opreme)
  * Prijedlozi projekata (prijedlozi_projekata -> po odobrenju upis u projekti)
"""
import os, sys
from datetime import datetime

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, execute, get_conn, prikazi_verziju, sada, lokalno
from auth import trazi_prijavu

st.set_page_config(page_title="Odobravanje", page_icon="✅")
prikazi_verziju()

# 🔒 samo voditelj/laborant
tko = trazi_prijavu("Odobravanje")


# =================== ZAHTJEVI ZA OPREMU ===================
def zahtjevi(status):
    return fetch("""
        SELECT k.id, o.naziv, o.interna_oznaka, k.podnositelj,
               k.vrijeme_od, k.vrijeme_do, k.sati_koristenja,
               k.materijal, k.potrebe_ispitivanja, k.opis
        FROM koristenje_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        WHERE k.status = %s
        ORDER BY k.vrijeme_od;""", (status,))


def odluci(zid, novi_status, tko):
    execute("""UPDATE koristenje_opreme
               SET status = %s, odobrio = %s, datum_odobrenja = %s
               WHERE id = %s;""", (novi_status, tko, sada(), zid))


# =================== PRIJEDLOZI PROJEKATA ===================
def prijedlozi():
    return fetch("""
        SELECT p.id, p.predlagatelj, p.predlozena_oznaka, p.naziv, p.gradiliste,
               p.opis, p.klijent_id, k.naziv, k.tip,
               p.novi_klijent_naziv, p.novi_klijent_tip, p.vrijeme_prijave
        FROM prijedlozi_projekata p
        LEFT JOIN klijenti k ON k.id = p.klijent_id
        WHERE p.status = 'na_cekanju'
        ORDER BY p.vrijeme_prijave;""")


def predlozi_oznaku_projekta():
    god = sada().year
    n = fetch("SELECT count(*) FROM projekti WHERE oznaka LIKE %s;",
              (f"P-{god}-%",))[0][0] or 0
    return f"P-{god}-{n + 1:03d}"


def odobri_projekt(pr_id, oznaka, klijent_id, nk_naziv, nk_tip,
                   naziv, gradiliste, tko, napomena):
    """Jedna transakcija: (novi klijent) -> projekt -> prijedlog 'odobreno'."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if klijent_id is None:
                cur.execute("SELECT id FROM klijenti WHERE lower(naziv) = lower(%s) LIMIT 1;",
                            (nk_naziv,))
                r = cur.fetchone()
                if r:
                    klijent_id = r[0]
                else:
                    cur.execute("INSERT INTO klijenti (naziv, tip) VALUES (%s,%s) RETURNING id;",
                                (nk_naziv, nk_tip or "interni"))
                    klijent_id = cur.fetchone()[0]
            cur.execute("""INSERT INTO projekti (klijent_id, oznaka, naziv, gradiliste)
                           VALUES (%s,%s,%s,%s) RETURNING id;""",
                        (klijent_id, oznaka, naziv, gradiliste))
            projekt_id = cur.fetchone()[0]
            cur.execute("""UPDATE prijedlozi_projekata
                           SET status='odobreno', odobrio=%s, datum_odobrenja=%s,
                               napomena_odluke=%s, projekt_id=%s, klijent_id=%s
                           WHERE id=%s;""",
                        (tko, sada(), napomena, projekt_id, klijent_id, pr_id))
        conn.commit()
        return projekt_id
    finally:
        conn.close()


def odbij_projekt(pr_id, tko, napomena):
    execute("""UPDATE prijedlozi_projekata
               SET status='odbijeno', odobrio=%s, datum_odobrenja=%s, napomena_odluke=%s
               WHERE id=%s;""", (tko, sada(), napomena, pr_id))


# ---------------------------- SUCELJE ----------------------------
st.title("✅ Odobravanje")
st.caption(f"Odluke se biljeze na ime: **{tko}**")

lista = zahtjevi("na_cekanju")
try:
    lista_pr = prijedlozi()
    pr_greska = None
except Exception as e:
    lista_pr, pr_greska = [], str(e)

tab_op, tab_pr = st.tabs([f"📨 Zahtjevi za opremu ({len(lista)})",
                          f"🗂️ Prijedlozi projekata ({len(lista_pr)})"])

# ---------- kartica: oprema ----------
with tab_op:
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

# ---------- kartica: projekti ----------
with tab_pr:
    if pr_greska:
        st.error("Tablica prijedloga nije dostupna — pokreni sql/1.6.0_prijedlozi_projekata.sql.")
        st.caption(f"Detalj: {pr_greska}")
    elif not lista_pr:
        st.success("🎉 Nema prijedloga projekata na cekanju.")
    else:
        st.caption(f"Na cekanju: **{len(lista_pr)}**")
        prijedlog_oznake = predlozi_oznaku_projekta()

    for (pid, predl, p_ozn, p_naziv, grad, p_opis, kid, k_naziv, k_tip,
         nk_naziv, nk_tip, v_prij) in lista_pr:
        with st.container(border=True):
            st.markdown(f"**{p_naziv}**  ·  prijedlog #{pid}")
            c1, c2 = st.columns(2)
            c1.write(f"👤 Predlagatelj: **{predl}**")
            c1.write(f"📍 Gradiliste: {grad or '—'}")
            if kid:
                c2.write(f"🏢 Klijent: {k_naziv} · {k_tip}")
            else:
                c2.write(f"🏢 Klijent: **{nk_naziv}** · {nk_tip}  (novi)")
            c2.write(f"🕒 Prijavljeno: {lokalno(v_prij):%Y-%m-%d %H:%M}" if v_prij else "🕒 —")
            if p_opis:
                st.caption(f"📝 {p_opis}")

            oznaka = st.text_input("Oznaka projekta *", key=f"pozn{pid}",
                                   value=p_ozn or prijedlog_oznake,
                                   help="Mora biti jedinstvena. Prijedlog mozes promijeniti.")
            napomena = st.text_input("Napomena uz odluku", key=f"pnap{pid}")

            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("✅ Odobri", key=f"pok{pid}", type="primary"):
                if not oznaka.strip():
                    st.error("Upisi oznaku projekta.")
                else:
                    try:
                        novi_id = odobri_projekt(pid, oznaka.strip(), kid, nk_naziv, nk_tip,
                                                 p_naziv, grad, tko, napomena.strip() or None)
                        st.cache_data.clear()
                        st.success(f"Projekt {oznaka.strip()} otvoren (id {novi_id}).")
                        st.rerun()
                    except Exception as e:
                        poruka = str(e).lower()
                        if "duplicate" in poruka or "unique" in poruka:
                            st.error("Projekt s tom oznakom vec postoji. Promijeni oznaku.")
                        else:
                            st.error(f"Greska: {e}")
            if b2.button("❌ Odbij", key=f"pno{pid}"):
                odbij_projekt(pid, tko, napomena.strip() or None)
                st.warning(f"Prijedlog #{pid} odbijen ({tko}).")
                st.rerun()

    if not pr_greska:
        st.divider()
        with st.expander("📜 Nedavno odluceno"):
            pov = fetch("""
                SELECT p.id, p.naziv, p.predlagatelj, p.status, pr.oznaka,
                       p.odobrio, p.datum_odobrenja, p.napomena_odluke
                FROM prijedlozi_projekata p
                LEFT JOIN projekti pr ON pr.id = p.projekt_id
                WHERE p.status IN ('odobreno','odbijeno')
                ORDER BY p.datum_odobrenja DESC NULLS LAST
                LIMIT 20;""")
            if pov:
                st.dataframe(
                    [{"#": r[0], "Naziv": r[1], "Predlagatelj": r[2], "Status": r[3],
                      "Oznaka": r[4] or "—", "Odlucio": r[5],
                      "Kada": (lokalno(r[6]).strftime("%Y-%m-%d %H:%M") if r[6] else "—"),
                      "Napomena": r[7] or ""}
                     for r in pov],
                    use_container_width=True, hide_index=True)
            else:
                st.caption("Jos nema odluka.")
