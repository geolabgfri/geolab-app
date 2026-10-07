"""Odobravanje — voditelj/laborant odobrava ili odbija (biljezi tko i kada).

Dvije kartice:
  * Zahtjevi za opremu        (koristenje_opreme)
  * Istrazivacki projekti     (projekti.vrsta='istrazivacki':
                               status_odobrenja na_cekanju -> odobreno / odbijeno;
                               zavrsen = faza 'zavrseno')
"""
import os, sys

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import fetch, execute, prikazi_verziju, sada, lokalno
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
               k.materijal, k.potrebe_ispitivanja, k.opis,
               coalesce(pr.akronim, pr.oznaka)
        FROM koristenje_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        LEFT JOIN projekti pr ON pr.id = k.projekt_id
        WHERE k.status = %s
        ORDER BY k.vrijeme_od;""", (status,))


def odluci(zid, novi_status, tko):
    execute("""UPDATE koristenje_opreme
               SET status = %s, odobrio = %s, datum_odobrenja = %s
               WHERE id = %s;""", (novi_status, tko, sada(), zid))


# =================== ISTRAZIVACKI PROJEKTI ===================
def projekti_na_cekanju():
    return fetch("""
        SELECT p.id, p.oznaka, p.akronim, p.naziv, p.sifra, k.naziv, p.voditelj,
               p.datum_pocetka, p.datum_zavrsetka, p.opis, p.predlozio
        FROM projekti p JOIN klijenti k ON k.id = p.klijent_id
        WHERE p.vrsta = 'istrazivacki' AND p.status_odobrenja = 'na_cekanju'
        ORDER BY p.id;""")


def projekti_aktivni():
    return fetch("""
        SELECT p.id, p.oznaka, coalesce(p.akronim, p.naziv), k.naziv, p.voditelj,
               p.datum_zavrsetka
        FROM projekti p JOIN klijenti k ON k.id = p.klijent_id
        WHERE p.vrsta = 'istrazivacki' AND p.status_odobrenja = 'odobreno'
          AND coalesce(p.faza, '') <> 'zavrseno'
        ORDER BY p.oznaka;""")


def odluci_projekt(pid, novi_status, tko, napomena, oznaka=None, akronim=None):
    if novi_status == "odobreno":
        execute("""UPDATE projekti
                   SET status_odobrenja='odobreno', odobrio=%s, datum_odobrenja=%s,
                       napomena_odluke=%s, oznaka=%s, akronim=%s
                   WHERE id=%s;""", (tko, sada(), napomena, oznaka, akronim, pid))
    else:
        execute("""UPDATE projekti
                   SET status_odobrenja='odbijeno', odobrio=%s, datum_odobrenja=%s,
                       napomena_odluke=%s
                   WHERE id=%s;""", (tko, sada(), napomena, pid))


def zatvori_projekt(pid):
    execute("UPDATE projekti SET faza='zavrseno' WHERE id=%s;", (pid,))


# ---------------------------- SUCELJE ----------------------------
st.title("✅ Odobravanje")
st.caption(f"Odluke se biljeze na ime: **{tko}**")

lista = zahtjevi("na_cekanju")
try:
    lista_ip = projekti_na_cekanju()
    ip_greska = None
except Exception as e:
    lista_ip, ip_greska = [], str(e)

tab_op, tab_ip = st.tabs([f"📨 Zahtjevi za opremu ({len(lista)})",
                          f"🗂️ Istrazivacki projekti ({len(lista_ip)})"])

# ---------- kartica: oprema ----------
with tab_op:
    if not lista:
        st.success("🎉 Nema zahtjeva na cekanju.")
    else:
        st.caption(f"Na cekanju: **{len(lista)}**")

    for (zid, naziv, inv, podn, v_od, v_do, sati, mat, potr, opis, ip_akr) in lista:
        with st.container(border=True):
            st.markdown(f"**{naziv}**  ·  inv. {inv or '—'}")
            c1, c2 = st.columns(2)
            c1.write(f"👤 Podnositelj: **{podn or '—'}**")
            c1.write(f"🧱 Materijal: {mat or '—'}")
            c1.write(f"🎯 Potreba: {potr or '—'}")
            if ip_akr:
                c1.write(f"🗂️ Projekt: **{ip_akr}**")
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
            SELECT k.id, o.naziv, k.podnositelj, coalesce(pr.akronim, pr.oznaka), k.status,
                   k.odobrio, k.datum_odobrenja
            FROM koristenje_opreme k
            JOIN oprema o ON o.id = k.oprema_id
            LEFT JOIN projekti pr ON pr.id = k.projekt_id
            WHERE k.status IN ('odobreno','odbijeno')
            ORDER BY k.datum_odobrenja DESC NULLS LAST
            LIMIT 20;""")
        if povijest:
            st.dataframe(
                [{"#": r[0], "Oprema": r[1], "Podnositelj": r[2], "Projekt": r[3] or "—",
                  "Status": r[4], "Odlucio": r[5],
                  "Kada": (lokalno(r[6]).strftime("%Y-%m-%d %H:%M") if r[6] else "—")}
                 for r in povijest],
                use_container_width=True, hide_index=True)
        else:
            st.caption("Jos nema odluka.")

# ---------- kartica: istrazivacki projekti ----------
with tab_ip:
    if ip_greska:
        st.error("Baza nije nadogradena — pokreni sql/1.7.0_istrazivacki_projekti.sql.")
        st.caption(f"Detalj: {ip_greska}")
        st.stop()

    if not lista_ip:
        st.success("🎉 Nema prijedloga projekata na cekanju.")
    else:
        st.caption(f"Na cekanju: **{len(lista_ip)}**")

    for (pid, ozn, akr, naziv, sifra, fin, vod, d_od, d_do, opis, predl) in lista_ip:
        with st.container(border=True):
            st.markdown(f"**{akr or ozn}** — {naziv}")
            c1, c2 = st.columns(2)
            c1.write(f"💶 Financijer: {fin}  ·  sifra: {sifra or '—'}")
            c1.write(f"👤 Voditelj: **{vod or '—'}**")
            c1.write(f"✍️ Predlozio: {predl or '—'}")
            c2.write(f"📅 Trajanje: {d_od or '?'} – {d_do or '?'}")
            if opis:
                st.caption(f"📝 {opis}")

            c1, c2 = st.columns([2, 1])
            oznaka = c1.text_input("Oznaka (konacna) *", value=ozn, key=f"iozn{pid}",
                                   help="Pod ovom oznakom projekt se vidi u Prijemu uzorka.")
            akronim = c2.text_input("Akronim *", value=akr or "", key=f"iakr{pid}",
                                    help="Upisuje se kao projekt nabave opreme.")
            napomena = st.text_input("Napomena uz odluku", key=f"inap{pid}")

            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("✅ Odobri", key=f"iok{pid}", type="primary"):
                if not oznaka.strip() or not akronim.strip():
                    st.error("Upisi oznaku i akronim.")
                else:
                    try:
                        odluci_projekt(pid, "odobreno", tko, napomena.strip() or None,
                                       oznaka.strip(), akronim.strip())
                        st.cache_data.clear()
                        st.success(f"Projekt {oznaka.strip()} je odobren.")
                        st.rerun()
                    except Exception as e:
                        poruka = str(e).lower()
                        if "duplicate" in poruka or "unique" in poruka:
                            st.error("Projekt s tom oznakom vec postoji.")
                        else:
                            st.error(f"Greska: {e}")
            if b2.button("❌ Odbij", key=f"ino{pid}"):
                odluci_projekt(pid, "odbijeno", tko, napomena.strip() or None)
                st.warning(f"Prijedlog {akr or ozn} odbijen ({tko}).")
                st.rerun()

    st.divider()
    with st.expander("🟢 Aktivni istrazivacki projekti — oznaci zavrsenim"):
        aktivni = projekti_aktivni()
        if not aktivni:
            st.caption("Nema aktivnih projekata.")
        for (pid, ozn, akr, fin, vod, d_do) in aktivni:
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{akr}** ({ozn})  ·  {fin}  ·  {vod or '—'}  ·  do {d_do or '?'}")
            if c2.button("Zavrsen", key=f"izav{pid}"):
                zatvori_projekt(pid)
                st.cache_data.clear()
                st.rerun()

    with st.expander("📜 Nedavno odluceno"):
        pov = fetch("""
            SELECT oznaka, coalesce(akronim, naziv), predlozio, status_odobrenja,
                   odobrio, datum_odobrenja, napomena_odluke
            FROM projekti
            WHERE vrsta = 'istrazivacki' AND datum_odobrenja IS NOT NULL
            ORDER BY datum_odobrenja DESC
            LIMIT 20;""")
        if pov:
            st.dataframe(
                [{"Oznaka": r[0], "Akronim": r[1], "Predlozio": r[2] or "—", "Status": r[3],
                  "Odlucio": r[4] or "—",
                  "Kada": (lokalno(r[5]).strftime("%Y-%m-%d %H:%M") if r[5] else "—"),
                  "Napomena": r[6] or ""}
                 for r in pov],
                use_container_width=True, hide_index=True)
        else:
            st.caption("Jos nema odluka.")
