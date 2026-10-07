"""Zajednicko spajanje na Supabase + verzija aplikacije + vrijeme."""
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import psycopg2

# Hrvatska vremenska zona (sama racuna ljetno/zimsko vrijeme)
TZ = ZoneInfo("Europe/Zagreb")


def sada():
    """Trenutno vrijeme u hrvatskoj zoni (server je u UTC)."""
    return datetime.now(TZ)


def lokalno(dt):
    """Vrijeme iz baze -> prikaz u hrvatskoj zoni."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(TZ)

# ---------------------------------------------------------------
#  VERZIJA APLIKACIJE
#  Format: glavna.manja.zakrpa
#    zakrpa (1.0.X) -> popravak sitnice
#    manja  (1.X.0) -> nova funkcija / stranica
#    glavna (X.0.0) -> veca promjena strukture baze
# ---------------------------------------------------------------
VERZIJA = "1.5.0"
DATUM_VERZIJE = "2026-07-14"


def prikazi_verziju():
    """Verzija u bocnoj traci — pozvati na svakoj stranici."""
    st.sidebar.caption(f"Laboratorij · v{VERZIJA} · {DATUM_VERZIJE}")


def get_conn():
    s = st.secrets["supabase"]
    return psycopg2.connect(
        host=s["host"], port=s["port"], dbname=s["dbname"],
        user=s["user"], password=s["password"],
        sslmode="require", connect_timeout=10,
    )


def fetch(query, params=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


def execute(query, params=None, returning=False):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            val = cur.fetchone()[0] if returning else None
        conn.commit()
        return val
    finally:
        conn.close()


def provjeri_vezu():
    """Vrati (True, '') ili (False, poruka)."""
    try:
        fetch("SELECT 1;")
        return True, ""
    except Exception as e:
        return False, str(e)
