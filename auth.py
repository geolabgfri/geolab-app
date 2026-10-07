"""
Prijava i uloge.

Lozinke se NE drze u kodu, nego u Streamlit Secrets — svaka osoba svoju:

    [pristup]
    "Vedran Jagodnik" = "lozinka"
    "Juraj Stella"    = "lozinka"
    "Ime Prezime"     = "lozinka"

Ime mora biti TOCNO kao u tablici 'osoblje' — po njemu se citaju uloge
i biljezi tko je odobrio / rijesio (sljedivost).

Uloge su stupci u tablici 'osoblje' (kvacica u Supabase Table Editoru):
    administrator     — voditelj / laborant: sve administrativne stranice
    znanstveno_zvanje — doc. / izv. prof. / prof.: predlaganje projekata
Uloge se citaju pri prijavi (promjena vrijedi od sljedece prijave).

Otvorene stranice (zahtjev za opremu, prijava kvara) NE zovu ovu zastitu.
"""
import hmac

import streamlit as st

from db import fetch

RAZINE = {
    "admin": "administrator",
    "projekti": "administrator ili znanstveno-nastavno zvanje",
}


def _ovlasteni():
    """Imena i lozinke iz Secrets. Prazno ako [pristup] nije postavljen."""
    if "pristup" not in st.secrets:
        return {}
    return dict(st.secrets["pristup"])


def _ucitaj_uloge(ime):
    """(administrator, znanstveno_zvanje) iz tablice osoblje."""
    try:
        r = fetch("""SELECT administrator, znanstveno_zvanje FROM osoblje
                     WHERE ime_prezime = %s AND aktivan = TRUE;""", (ime,))
        return (bool(r[0][0]), bool(r[0][1])) if r else (False, False)
    except Exception:
        # baza jos nije nadogradena (0.8.0) — ponasanje kao prije: [pristup] = admin
        return True, False


def prijavljen():
    return bool(st.session_state.get("prijavljen"))


def je_admin():
    return prijavljen() and st.session_state.get("admin", False)


def smije_projekte():
    return prijavljen() and (st.session_state.get("admin", False)
                             or st.session_state.get("zvanje", False))


def odjava():
    for k in ("prijavljen", "korisnik", "admin", "zvanje"):
        st.session_state.pop(k, None)


def forma_prijave(naziv_stranice=None):
    """Ekran za prijavu (ime + lozinka). Ne zaustavlja stranicu."""
    ovlasteni = _ovlasteni()
    if not ovlasteni:
        st.error("🔒 Pristup nije konfiguriran.")
        st.caption("Dodaj blok [pristup] u Streamlit Secrets (ime = lozinka).")
        return

    st.title("🔒 Prijava")
    if naziv_stranice:
        st.caption(f"Za pristup ({naziv_stranice}) prijavi se svojim imenom i lozinkom.")
    else:
        st.caption("Prijavi se svojim imenom i lozinkom.")

    ime = st.selectbox("Tko si?", sorted(ovlasteni.keys()))
    lozinka = st.text_input("Lozinka", type="password")

    if st.button("Prijavi se", type="primary"):
        # hmac.compare_digest — usporedba otporna na mjerenje vremena
        if hmac.compare_digest(lozinka, str(ovlasteni.get(ime, ""))):
            admin, zvanje = _ucitaj_uloge(ime)
            st.session_state["prijavljen"] = True
            st.session_state["korisnik"] = ime
            st.session_state["admin"] = admin
            st.session_state["zvanje"] = zvanje
            st.rerun()
        else:
            st.error("Netocna lozinka.")

    st.info("Zahtjev za opremu i Prijava kvara ne trebaju prijavu.")


def trazi_prijavu(naziv_stranice="ova stranica", razina="admin"):
    """
    Zastita stranice. razina: 'admin' ili 'projekti'.
    Vraca ime prijavljene osobe; ako nije prijavljena ili nema ovlast,
    zaustavlja stranicu.
    """
    if not prijavljen():
        forma_prijave(naziv_stranice)
        st.stop()

    ok = je_admin() if razina == "admin" else smije_projekte()
    if not ok:
        st.title("⛔ Nemas pristup")
        st.write(f"Stranica **{naziv_stranice}** trazi ulogu: "
                 f"*{RAZINE.get(razina, razina)}*.")
        st.caption("Uloge postavlja voditelj laboratorija u tablici osoblje.")
        st.stop()

    return st.session_state["korisnik"]
