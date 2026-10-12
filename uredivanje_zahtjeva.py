"""
Uredivanje zahtjeva za koristenje opreme (samo administrator, stranica Odobravanje).

  * filtri: osoba (podnositelj ili provoditelj), uredaj, razdoblje, status
  * izmjena polja: uredaj, projekt, podnositelj, provoditelj, pocetak, zavrsetak,
    materijal, namjena, opis  (obavezna napomena)
  * otkazivanje (status 'otkazano') i ponovno aktiviranje (novi termin -> 'odobreno')
  * svaka izmjena -> redak u koristenje_opreme_izmjene (trag za ISO; nikad se ne brise)
"""
from datetime import datetime, timedelta

import streamlit as st

from db import fetch, get_conn, lokalno, sada, TZ
import zauzetost as zz

MATERIJALI = ["Glina", "Prah", "Pijesak", "Sljunak", "Stijena", "Ostalo"]
NAMJENE = ["Nastava", "Zavrsni rad", "Diplomski rad", "Doktorski rad",
           "Znanstveni rad", "Struka", "Ostalo"]
STATUSI = ["na_cekanju", "odobreno", "otkazano"]
NAZIVI_POLJA = {
    "oprema_id": "uredaj", "projekt_id": "projekt", "podnositelj": "podnositelj",
    "provoditelj": "provoditelj", "vrijeme_od": "pocetak", "vrijeme_do": "zavrsetak",
    "materijal": "materijal", "potrebe_ispitivanja": "namjena", "opis": "opis",
    "status": "status",
}
UPISI = "✏️ Drugi — upisi"
PRAZNO = "—"
ISTI = "— isti kao podnositelj —"


def _f(t):
    return lokalno(t).strftime("%d.%m.%Y. %H:%M") if t else "—"


@st.cache_data(ttl=120)
def _sifrarnici():
    oprema = fetch("SELECT id, naziv, interna_oznaka FROM oprema ORDER BY naziv;")
    osobe = fetch("SELECT id, ime_prezime FROM osoblje WHERE aktivan = TRUE ORDER BY ime_prezime;")
    projekti = fetch("""SELECT id, coalesce(akronim, oznaka) FROM projekti
                        WHERE status_odobrenja = 'odobreno' ORDER BY 2;""")
    return oprema, osobe, projekti


def _izbor(mjesto, label, opcije, trenutno, key):
    """selectbox s trenutnom vrijednoscu (dodaje je ako je nema na popisu)."""
    opc = list(opcije)
    if trenutno is None:
        opc = [PRAZNO] + opc            # prazno polje ostaje prazno dok se ne odabere
        trenutno = PRAZNO
    elif trenutno not in opc:
        opc = [trenutno] + opc
    v = mjesto.selectbox(label, opc, index=opc.index(trenutno), key=key)
    return None if v == PRAZNO else v


def _spremi(zid, promjene, napomena, tko, novi_status=None, stari_status=None):
    """promjene: {polje: (staro_txt, novo_txt, nova_vrijednost)}; sve u jednoj transakciji."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sets, vals = [], []
            for polje, (_s, _n, v) in promjene.items():
                sets.append(f"{polje} = %s")
                vals.append(v)
            if "vrijeme_od" in promjene or "vrijeme_do" in promjene:
                sets.append("plan_vrijeme_od = coalesce(plan_vrijeme_od, vrijeme_od)")
                sets.append("plan_vrijeme_do = coalesce(plan_vrijeme_do, vrijeme_do)")
            if novi_status:
                sets.append("status = %s")
                vals.append(novi_status)
            sets += ["izmijenio = %s", "datum_izmjene = %s"]
            vals += [tko, sada()]
            # plan_* se mora postaviti PRIJE nove vrijednosti vremena -> dva koraka
            plan = [x for x in sets if x.startswith("plan_")]
            if plan:
                cur.execute(f"UPDATE koristenje_opreme SET {', '.join(plan)} WHERE id = %s;", (zid,))
                sets = [x for x in sets if not x.startswith("plan_")]
            cur.execute(f"UPDATE koristenje_opreme SET {', '.join(sets)} WHERE id = %s;",
                        (*vals, zid))
            if "vrijeme_od" in promjene or "vrijeme_do" in promjene:
                cur.execute("""UPDATE koristenje_opreme
                               SET sati_koristenja = round((extract(epoch FROM
                                   (vrijeme_do - vrijeme_od)) / 3600.0)::numeric, 2)
                               WHERE id = %s;""", (zid,))
            zapisi = [(NAZIVI_POLJA.get(p, p), s, n) for p, (s, n, _v) in promjene.items()
                      if p != "osoba_id"]
            if novi_status:
                zapisi.append(("status", stari_status or "—", novi_status))
            for polje, staro, novo in zapisi:
                cur.execute("""INSERT INTO koristenje_opreme_izmjene
                               (zahtjev_id, polje, staro, novo, napomena, izmijenio)
                               VALUES (%s,%s,%s,%s,%s,%s);""",
                            (zid, polje, staro, novo, napomena, tko))
        conn.commit()
    finally:
        conn.close()


def prikazi(tko):
    oprema, osobe, projekti = _sifrarnici()
    imena = [o[1] for o in osobe]
    id_osobe = {n: i for (i, n) in osobe}

    # ---------- filtri ----------
    c1, c2, c3, c4 = st.columns(4)
    f_osoba = c1.selectbox("Osoba", ["sve osobe"] + imena, key="ur_f_osoba")
    opr_lab = ["svi uredaji"] + [f"{n} · inv. {i or '—'}" for (_x, n, i) in oprema]
    f_opr = c2.selectbox("Uredaj", range(len(opr_lab)), format_func=lambda i: opr_lab[i],
                         key="ur_f_opr")
    danas = sada().date()
    f_raz = c3.date_input("Razdoblje", value=(danas - timedelta(days=60),
                                               danas + timedelta(days=60)), key="ur_f_raz")
    f_stat = c4.multiselect("Status", STATUSI, default=STATUSI, key="ur_f_stat")

    uvjeti, par = ["k.status = ANY(%s)"], [f_stat or STATUSI]
    if f_osoba != "sve osobe":
        uvjeti.append("(k.podnositelj = %s OR k.provoditelj = %s OR k.osoba_id = %s)")
        par += [f_osoba, f_osoba, id_osobe.get(f_osoba)]
    if f_opr > 0:
        uvjeti.append("k.oprema_id = %s")
        par.append(oprema[f_opr - 1][0])
    if isinstance(f_raz, (list, tuple)) and len(f_raz) == 2:
        uvjeti.append("(k.vrijeme_od AT TIME ZONE 'Europe/Zagreb')::date BETWEEN %s AND %s")
        par += list(f_raz)

    rows = fetch(f"""
        SELECT k.id, k.vrijeme_od, k.vrijeme_do, o.naziv,
               coalesce(k.provoditelj, k.podnositelj), k.status
        FROM koristenje_opreme k JOIN oprema o ON o.id = k.oprema_id
        WHERE {' AND '.join(uvjeti)}
        ORDER BY k.vrijeme_od DESC LIMIT 100;""", tuple(par))
    if not rows:
        st.caption("Nema zahtjeva za odabrane filtre.")
        return

    lab = [f"#{r[0]} · {_f(r[1])} – {lokalno(r[2]):%H:%M} · {r[3]} · {r[4]} · {r[5]}"
           if r[1] and r[2] else f"#{r[0]} · {r[3]} · {r[4]} · {r[5]}" for r in rows]
    st.caption(f"Pronadeno: **{len(rows)}**")
    zi = st.selectbox("Zahtjev za uredivanje", range(len(lab)), format_func=lambda i: lab[i],
                      key="ur_zahtjev")
    zid = rows[zi][0]

    z = fetch("""SELECT k.oprema_id, k.projekt_id, k.podnositelj, k.provoditelj,
                        k.vrijeme_od, k.vrijeme_do, k.materijal, k.potrebe_ispitivanja,
                        k.opis, k.status, k.odobrio, k.datum_odobrenja, k.sati_koristenja
                 FROM koristenje_opreme k WHERE k.id = %s;""", (zid,))[0]
    (z_opr, z_proj, z_podn, z_prov, z_od, z_do, z_mat, z_potr, z_opis,
     z_stat, z_odob, z_dodob, z_sati) = z

    with st.container(border=True):
        st.markdown(f"**Zahtjev #{zid}** · status **{z_stat}**"
                    + (f" · odobrio {z_odob} {lokalno(z_dodob):%d.%m.}" if z_odob and z_dodob else ""))
        k = f"ur_{zid}_"

        c1, c2 = st.columns(2)
        opr_map = {f"{n} · inv. {i or '—'}": x for (x, n, i) in oprema}
        opr_nazad = {v: lbl for lbl, v in opr_map.items()}
        n_opr_lbl = c1.selectbox("Uredaj", list(opr_map), key=k + "opr",
                                 index=list(opr_map).index(opr_nazad[z_opr]) if z_opr in opr_nazad else 0)
        n_opr = opr_map[n_opr_lbl]
        BEZ = "— nije vezano uz projekt —"
        proj_map = {BEZ: None, **{a: x for (x, a) in projekti}}
        if z_proj is not None and z_proj not in proj_map.values():
            stari = fetch("SELECT coalesce(akronim, oznaka) FROM projekti WHERE id = %s;", (z_proj,))
            proj_map[stari[0][0] if stari else f"projekt #{z_proj}"] = z_proj
        proj_nazad = {v: lbl for lbl, v in proj_map.items()}
        n_proj_lbl = _izbor(c2, "Projekt", list(proj_map), proj_nazad[z_proj], k + "proj")
        n_proj = proj_map[n_proj_lbl]

        c1, c2 = st.columns(2)
        n_podn = _izbor(c1, "Podnositelj", imena + [UPISI], z_podn, k + "podn")
        if n_podn == UPISI:
            n_podn = c1.text_input("Ime podnositelja", key=k + "podn_txt")
        n_prov = _izbor(c2, "Provoditelj", [ISTI] + imena + [UPISI], z_prov or ISTI, k + "prov")
        if n_prov == UPISI:
            n_prov = c2.text_input("Ime provoditelja", key=k + "prov_txt")
        if n_prov == ISTI:
            n_prov = None

        s_od, s_do = lokalno(z_od), lokalno(z_do)
        c1, c2 = st.columns(2)
        d1 = c1.date_input("Pocetak", value=s_od.date(), key=k + "d1")
        t1 = c1.time_input("Vrijeme pocetka", value=s_od.time(), key=k + "t1",
                           label_visibility="collapsed")
        d2 = c2.date_input("Zavrsetak", value=s_do.date(), key=k + "d2")
        t2 = c2.time_input("Vrijeme zavrsetka", value=s_do.time(), key=k + "t2",
                           label_visibility="collapsed")
        n_od = datetime.combine(d1, t1, tzinfo=TZ)
        n_do = datetime.combine(d2, t2, tzinfo=TZ)
        n_sati = round(max((n_do - n_od).total_seconds() / 3600, 0), 2)

        c1, c2 = st.columns(2)
        n_mat = _izbor(c1, "Materijal", MATERIJALI, z_mat, k + "mat")
        n_potr = _izbor(c2, "Namjena", NAMJENE, z_potr, k + "potr")
        n_opis = st.text_area("Opis", value=z_opis or "", key=k + "opis")

        # --- razlike ---
        def t_opr(x): return opr_nazad.get(x, "—")
        def t_proj(x): return proj_nazad.get(x, "—") if x else "—"
        promjene = {}
        kandidati = [
            ("oprema_id", z_opr, n_opr, t_opr), ("projekt_id", z_proj, n_proj, t_proj),
            ("podnositelj", z_podn, (n_podn or "").strip() or None, str),
            ("provoditelj", z_prov, (n_prov or "").strip() or None, str),
            ("vrijeme_od", s_od, n_od, _f), ("vrijeme_do", s_do, n_do, _f),
            ("materijal", z_mat, n_mat, str), ("potrebe_ispitivanja", z_potr, n_potr, str),
            ("opis", (z_opis or "").strip() or None, n_opis.strip() or None, str),
        ]
        for polje, staro, novo, fmt in kandidati:
            if staro != novo:
                promjene[polje] = (fmt(staro) if staro is not None else "—",
                                   fmt(novo) if novo is not None else "—", novo)
        if "podnositelj" in promjene or "provoditelj" in promjene:
            promjene["osoba_id"] = ("—", "—", id_osobe.get(((n_prov or "").strip() or None)
                                                           or (n_podn or "").strip()))

        vidljive = {p: v for p, v in promjene.items() if p != "osoba_id"}
        if vidljive:
            st.info("Promjene: " + "; ".join(f"**{NAZIVI_POLJA[p]}** {s} → {n}"
                                             for p, (s, n, _v) in vidljive.items())
                    + (f"  ·  trajanje {float(z_sati or 0):.1f} h → **{n_sati} h**"
                       if ("vrijeme_od" in promjene or "vrijeme_do" in promjene) else ""))

        # --- preklapanje s drugim zahtjevima za isti uredaj ---
        pk_odob, pk_cek = zz.razvrstaj(zz.preklapanja(n_opr, n_od, n_do, zid))
        if pk_odob:
            st.error("⛔ Termin se preklapa s odobrenim zahtjevom za isti uredaj:\n\n"
                     + "\n".join(f"- {zz.opis(r)}" for r in pk_odob))
        if pk_cek:
            st.warning("⚠️ Termin trazi i zahtjev na cekanju:\n\n"
                       + "\n".join(f"- {zz.opis(r)}" for r in pk_cek))
        # odobreni (i ponovno aktivirani) zahtjev ne smije se preklapati s odobrenim
        #   (samo ako se mijenja termin/uredaj ili se zahtjev ponovno aktivira)
        mijenja_termin = any(p in promjene for p in ("oprema_id", "vrijeme_od", "vrijeme_do"))
        blokira = bool(pk_odob) and (
            (z_stat == "odobreno" and mijenja_termin) or z_stat == "otkazano")

        napomena = st.text_input("Napomena uz izmjenu *", key=k + "nap",
                                 placeholder="npr. pokus produljen zbog konsolidacije")

        b1, b2, _ = st.columns([1, 1, 2])
        def provjeri(treba_promjene=True):
            if blokira:
                st.error("Odaberi termin ili uredaj koji nije zauzet.")
                return False
            if not napomena.strip():
                st.error("Upisi napomenu uz izmjenu.")
                return False
            if n_do <= n_od:
                st.error("Zavrsetak mora biti nakon pocetka.")
                return False
            if not (n_podn or "").strip():
                st.error("Upisi podnositelja.")
                return False
            if treba_promjene and not vidljive:
                st.warning("Nema promjena za spremiti.")
                return False
            return True

        if z_stat == "otkazano":
            if b1.button("♻️ Ponovno aktiviraj", key=k + "akt", type="primary"):
                if not ("vrijeme_od" in promjene or "vrijeme_do" in promjene):
                    st.error("Za ponovno aktiviranje upisi novi termin.")
                elif provjeri(treba_promjene=False):
                    _spremi(zid, promjene, napomena.strip(), tko,
                            novi_status="odobreno", stari_status=z_stat)
                    st.toast(f"Zahtjev #{zid} ponovno aktiviran ({tko}).")
                    st.rerun()
        else:
            if b1.button("💾 Spremi izmjene", key=k + "spr", type="primary"):
                if provjeri():
                    _spremi(zid, vidljive | ({"osoba_id": promjene["osoba_id"]}
                                             if "osoba_id" in promjene else {}),
                            napomena.strip(), tko)
                    st.toast(f"Zahtjev #{zid} izmijenjen ({tko}).")
                    st.rerun()
            if z_stat == "odobreno" and b2.button("🚫 Otkazi zahtjev", key=k + "otk"):
                if not napomena.strip():
                    st.error("Upisi napomenu (razlog otkazivanja).")
                else:
                    _spremi(zid, {}, napomena.strip(), tko,
                            novi_status="otkazano", stari_status=z_stat)
                    st.toast(f"Zahtjev #{zid} otkazan ({tko}).")
                    st.rerun()

    # ---------- povijest izmjena ----------
    pov = fetch("""SELECT vrijeme, izmijenio, polje, staro, novo, napomena
                   FROM koristenje_opreme_izmjene WHERE zahtjev_id = %s
                   ORDER BY vrijeme DESC;""", (zid,))
    st.markdown(f"**Povijest izmjena · #{zid}**")
    if pov:
        st.dataframe([{"Kada": f"{lokalno(r[0]):%d.%m.%Y. %H:%M}", "Tko": r[1], "Polje": r[2],
                       "Staro → novo": f"{r[3]} → {r[4]}", "Napomena": r[5]} for r in pov],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Zahtjev jos nije mijenjan.")
