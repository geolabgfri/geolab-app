"""Odobravanje — voditelj/laborant odobrava ili odbija (biljezi tko i kada).

Dvije kartice:
  * Zahtjevi za opremu        (koristenje_opreme)
  * Istrazivacki projekti     (projekti.vrsta='istrazivacki':
                               status_odobrenja na_cekanju -> odobreno / odbijeno;
                               faza: u_tijeku -> zavrseno)
"""
import os, sys

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime

from db import fetch, execute, prikazi_verziju, sada, lokalno, TZ
from auth import trazi_prijavu

st.set_page_config(page_title="Odobravanje", page_icon="✅")
prikazi_verziju()

# 🔒 samo administrator
tko = trazi_prijavu("Odobravanje")


# =================== ZAHTJEVI ZA OPREMU ===================
def zahtjevi(status):
    return fetch("""
        SELECT k.id, o.naziv, o.interna_oznaka, k.podnositelj,
               k.vrijeme_od, k.vrijeme_do, k.sati_koristenja,
               k.materijal, k.potrebe_ispitivanja, k.opis,
               coalesce(pr.akronim, pr.oznaka), k.provoditelj
        FROM koristenje_opreme k
        JOIN oprema o ON o.id = k.oprema_id
        LEFT JOIN projekti pr ON pr.id = k.projekt_id
        WHERE k.status = %s
        ORDER BY k.vrijeme_od;""", (status,))


def odluci(zid, novi_status, tko):
    execute("""UPDATE koristenje_opreme
               SET status = %s, odobrio = %s, datum_odobrenja = %s
               WHERE id = %s;""", (novi_status, tko, sada(), zid))


def obrisi_zahtjev(zid):
    """Odbijeni zahtjev se brise iz baze (ne ostaje u evidenciji koristenja)."""
    execute("DELETE FROM koristenje_opreme WHERE id = %s AND status = 'na_cekanju';", (zid,))


# =================== ISTRAZIVACKI PROJEKTI ===================
def projekti_na_cekanju():
    return fetch("""
        SELECT p.id, p.oznaka, p.akronim, p.naziv, p.sifra, k.naziv, p.voditelj,
               p.datum_pocetka, p.datum_zavrsetka, p.opis, p.predlozio, p.sazetak,
               (SELECT string_agg(o.ime_prezime, ', ' ORDER BY o.ime_prezime)
                  FROM projekt_suradnici ps JOIN osoblje o ON o.id = ps.osoblje_id
                 WHERE ps.projekt_id = p.id AND ps.uloga = 'suradnik')
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

    for (zid, naziv, inv, podn, v_od, v_do, sati, mat, potr, opis, ip_akr, prov) in lista:
        with st.container(border=True):
            st.markdown(f"**{naziv}**  ·  inv. {inv or '—'}")
            c1, c2 = st.columns(2)
            c1.write(f"👤 Podnositelj: **{podn or '—'}**")
            c1.write(f"🔧 Provoditelj: **{prov}**" if prov else "🔧 Provoditelj: isti")
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
            if st.session_state.get("potvrdi_odbij") == zid:
                st.warning("Odbijeni zahtjev se **brise iz baze**. Potvrdi:")
                p1, p2, _ = st.columns([1, 1, 3])
                if p1.button("🗑️ Da, odbij i obrisi", key=f"nook{zid}"):
                    obrisi_zahtjev(zid)
                    st.session_state.pop("potvrdi_odbij", None)
                    st.toast(f"Zahtjev #{zid} odbijen i obrisan ({tko}).")
                    st.rerun()
                if p2.button("Odustani", key=f"nono{zid}"):
                    st.session_state.pop("potvrdi_odbij", None)
                    st.rerun()
            elif b2.button("❌ Odbij", key=f"no{zid}"):
                st.session_state["potvrdi_odbij"] = zid
                st.rerun()

    st.divider()
    with st.expander("📜 Nedavno odobreno (zadnjih 5)"):
        povijest = fetch("""
            SELECT k.id, o.naziv, coalesce(k.provoditelj, k.podnositelj),
                   coalesce(pr.akronim, pr.oznaka), k.vrijeme_od, k.vrijeme_do,
                   k.sati_koristenja, k.odobrio
            FROM koristenje_opreme k
            JOIN oprema o ON o.id = k.oprema_id
            LEFT JOIN projekti pr ON pr.id = k.projekt_id
            WHERE k.status = 'odobreno'
            ORDER BY k.datum_odobrenja DESC NULLS LAST
            LIMIT 5;""")
        fmt = lambda t: lokalno(t).strftime("%d.%m.%Y. %H:%M") if t else "—"
        if povijest:
            st.dataframe(
                [{"#": r[0], "Oprema": r[1], "Provoditelj": r[2], "Projekt": r[3] or "—",
                  "Od": fmt(r[4]), "Do": fmt(r[5]), "Sati": r[6], "Odobrio": r[7]}
                 for r in povijest],
                use_container_width=True, hide_index=True)
        else:
            st.caption("Jos nema odobrenih zahtjeva.")

    # --- ispravak trajanja (pokus traje dulje / krace od planiranog) ---
    with st.expander("✏️ Ispravak trajanja pokusa"):
        st.caption("Za odobrene zahtjeve: upisi stvarno vrijeme. Prvotno planirano vrijeme "
                   "ostaje zapisano u bazi (plan_vrijeme_od / plan_vrijeme_do).")
        try:
            za_ispravak = fetch("""
                SELECT k.id, o.naziv, coalesce(k.provoditelj, k.podnositelj),
                       k.vrijeme_od, k.vrijeme_do
                FROM koristenje_opreme k JOIN oprema o ON o.id = k.oprema_id
                WHERE k.status = 'odobreno'
                  AND k.vrijeme_do >= now() - interval '90 days'
                ORDER BY k.vrijeme_od DESC
                LIMIT 50;""")
        except Exception as e:
            za_ispravak = []
            st.caption(f"Nije dostupno: {e}")
        if not za_ispravak:
            st.caption("Nema odobrenih zahtjeva u zadnjih 90 dana.")
        else:
            fmt = lambda t: lokalno(t).strftime("%d.%m. %H:%M") if t else "—"
            lab = [f"#{r[0]}  ·  {r[1]}  ·  {r[2]}  ·  {fmt(r[3])} – {fmt(r[4])}"
                   for r in za_ispravak]
            ii = st.selectbox("Zahtjev", range(len(lab)), format_func=lambda i: lab[i],
                              key="isp_zahtjev")
            zid, _n, _p, s_od, s_do = za_ispravak[ii]
            s_od, s_do = lokalno(s_od), lokalno(s_do)
            c1, c2 = st.columns(2)
            n_d1 = c1.date_input("Stvarni pocetak", value=s_od.date(), key=f"isp_d1_{zid}")
            n_t1 = c1.time_input("Vrijeme pocetka", value=s_od.time(), key=f"isp_t1_{zid}",
                                 label_visibility="collapsed")
            n_d2 = c2.date_input("Stvarni zavrsetak", value=s_do.date(), key=f"isp_d2_{zid}")
            n_t2 = c2.time_input("Vrijeme zavrsetka", value=s_do.time(), key=f"isp_t2_{zid}",
                                 label_visibility="collapsed")
            n_od = datetime.combine(n_d1, n_t1, tzinfo=TZ)
            n_do = datetime.combine(n_d2, n_t2, tzinfo=TZ)
            n_sati = round(max((n_do - n_od).total_seconds() / 3600, 0), 2)
            st.info(f"Novo trajanje: **{n_sati} h**")
            if st.button("💾 Spremi ispravak", key=f"isp_spremi_{zid}"):
                if n_do <= n_od:
                    st.error("Zavrsetak mora biti nakon pocetka.")
                else:
                    execute("""UPDATE koristenje_opreme
                               SET plan_vrijeme_od = coalesce(plan_vrijeme_od, vrijeme_od),
                                   plan_vrijeme_do = coalesce(plan_vrijeme_do, vrijeme_do),
                                   vrijeme_od = %s, vrijeme_do = %s, sati_koristenja = %s,
                                   izmijenio = %s, datum_izmjene = %s
                               WHERE id = %s;""",
                            (n_od, n_do, n_sati, tko, sada(), zid))
                    st.toast(f"Zahtjev #{zid}: trajanje ispravljeno na {n_sati} h ({tko}).")
                    st.rerun()

# ---------- kartica: istrazivacki projekti ----------
with tab_ip:
    if ip_greska:
        st.error("Baza nije nadogradena — pokreni sql/1.7.0_istrazivacki_projekti.sql.")
        st.caption(f"Detalj: {ip_greska}")
        st.stop()

    if not lista_ip:
        st.success("🎉 Nema upisanih projekata na cekanju.")
    else:
        st.caption(f"Na cekanju: **{len(lista_ip)}**")

    for (pid, ozn, akr, naziv, sifra, fin, vod, d_od, d_do, opis, predl, sazetak, sur) in lista_ip:
        with st.container(border=True):
            st.markdown(f"**{akr or ozn}** — {naziv}")
            c1, c2 = st.columns(2)
            c1.write(f"💶 Financijer: {fin}  ·  sifra: {sifra or '—'}")
            c1.write(f"👤 Voditelj: **{vod or '—'}**")
            c1.write(f"✍️ Predlozio: {predl or '—'}")
            c2.write(f"📅 Trajanje: {d_od or '?'} – {d_do or '?'}")
            c2.write(f"👥 Suradnici: {sur or '—'}")
            if sazetak:
                with st.expander("📄 Sazetak projekta"):
                    st.write(sazetak)
            if opis:
                st.caption(f"🔬 Laboratorij: {opis}")

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
                st.warning(f"Projekt {akr or ozn} odbijen ({tko}).")
                st.rerun()

    st.divider()
    with st.expander("🟢 Istrazivacki projekti u tijeku — oznaci zavrsenim"):
        aktivni = projekti_aktivni()
        if not aktivni:
            st.caption("Nema projekata u tijeku.")
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
