"""
Automatske e-mail obavijesti (voditelj + laborant, uz kopiju podnositelju).

  posalji(kljuc, naslov, tekst, prilozi=None, cc=None)
      salje odmah; rezultat pamti u session_state[kljuc]
  prikazi_status(kljuc)
      prikazuje ishod; ako slanje nije uspjelo -> gumb "Posalji e-mail ponovno"
  email_osobe(ime)
      adresa iz tablice osoblje (stupac email), ili None

Primatelji: Secrets [email] recipients. Ako [email] nije postavljen, nista se ne salje.
"""
import streamlit as st

from db import fetch


@st.cache_data(ttl=300)
def _adrese():
    """{ime_prezime: email} iz tablice osoblje; prazno ako stupac jos ne postoji."""
    try:
        return {ime: mail for (ime, mail) in fetch(
            "SELECT ime_prezime, email FROM osoblje WHERE email IS NOT NULL;")}
    except Exception:
        return {}


def email_osobe(ime):
    return _adrese().get(ime) if ime else None


def _cc_lista(cc, primatelji):
    """Bez praznih, duplikata i adresa koje su vec u primateljima."""
    van = {p.lower() for p in primatelji}
    out = []
    for a in cc or []:
        a = (a or "").strip()
        if a and "@" in a and a.lower() not in van and a.lower() not in {x.lower() for x in out}:
            out.append(a)
    return out


def _salji(p):
    import yagmail
    rec = list(st.secrets["email"]["recipients"])
    cc = _cc_lista(p["cc"], rec)
    yag = yagmail.SMTP(st.secrets["email"]["sender"], st.secrets["email"]["app_password"])
    yag.send(to=rec, cc=cc or None, subject=p["naslov"], contents=p["tekst"],
             attachments=p["prilozi"] or None)
    return rec, cc


def posalji(kljuc, naslov, tekst, prilozi=None, cc=None):
    """Posalji odmah i zapamti ishod (za prikaz i ponovni pokusaj)."""
    p = {"naslov": naslov, "tekst": tekst, "prilozi": prilozi or [], "cc": cc or []}
    if "email" not in st.secrets:
        st.session_state[kljuc] = {**p, "ok": None, "poruka": "E-mail nije konfiguriran."}
        return
    try:
        rec, cc_ok = _salji(p)
        poruka = "Obavijest poslana: " + ", ".join(rec)
        if cc_ok:
            poruka += "  ·  kopija: " + ", ".join(cc_ok)
        st.session_state[kljuc] = {**p, "ok": True, "poruka": poruka}
    except Exception as e:
        st.session_state[kljuc] = {**p, "ok": False, "poruka": str(e)}


def prikazi_status(kljuc):
    s = st.session_state.get(kljuc)
    if not s:
        return
    if s["ok"] is True:
        st.success("📧 " + s["poruka"])
    elif s["ok"] is None:
        st.info("📧 " + s["poruka"] + " Zapis je spremljen, obavijest nije poslana.")
    else:
        st.warning("📧 Zapis je spremljen, ali e-mail obavijest NIJE poslana.")
        st.caption(f"Detalj: {s['poruka']}")
        if st.button("📧 Posalji e-mail ponovno", key=f"ponovno_{kljuc}"):
            posalji(kljuc, s["naslov"], s["tekst"], s["prilozi"], s["cc"])
            st.rerun()
