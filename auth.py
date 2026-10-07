"""
Prijava za administrativne stranice.

Lozinke se NE drze u kodu, nego u Streamlit Secrets:

    [pristup]
    "Vedran Jagodnik" = "lozinka-voditelja"
    "Juraj Stella"    = "lozinka-laboranta"

Ime mora biti TOCNO kao u tablici 'osoblje' — jer se po njemu biljezi
tko je odobrio / rijesio (sljedivost).

Otvorene stranice (zahtjev, prijava kvara) NE zovu ovu zastitu.
"""
import hmac

import streamlit as st


def _ovlasteni():
    """Imena i lozinke iz Secrets. Prazno ako [pristup] nije postavljen."""
    if "pristup" not in st.secrets:
        return {}
    return dict(st.secrets["pristup"])


def trazi_prijavu(naziv_stranice="ova stranica"):
    """
    Zastita administrativne stranice.
    Vraca ime prijavljene osobe; ako nije prijavljena, zaustavlja stranicu.
    """
    ovlasteni = _ovlasteni()

    if not ovlasteni:
        st.error("🔒 Pristup nije konfiguriran.")
        st.caption("Dodaj blok [pristup] u Streamlit Secrets (ime = lozinka).")
        st.stop()

    # vec prijavljen u ovoj sesiji?
    if st.session_state.get("prijavljen"):
        ime = st.session_state["korisnik"]
        with st.sidebar:
            st.success(f"👤 {ime}")
            if st.button("Odjava"):
                st.session_state["prijavljen"] = False
                st.session_state.pop("korisnik", None)
                st.rerun()
        return ime

    # --- ekran za prijavu ---
    st.title("🔒 Prijava")
    st.caption(f"Za pristup ({naziv_stranice}) prijavi se svojim imenom i lozinkom.")

    ime = st.selectbox("Tko si?", sorted(ovlasteni.keys()))
    lozinka = st.text_input("Lozinka", type="password")

    if st.button("Prijavi se", type="primary"):
        # hmac.compare_digest — usporedba otporna na mjerenje vremena
        if hmac.compare_digest(lozinka, str(ovlasteni.get(ime, ""))):
            st.session_state["prijavljen"] = True
            st.session_state["korisnik"] = ime
            st.rerun()
        else:
            st.error("Netocna lozinka.")

    st.info("Zahtjev za opremu i Prijava kvara ne trebaju prijavu — "
            "dostupni su svima u izborniku lijevo.")
    st.stop()
