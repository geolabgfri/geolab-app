"""
Zauzetost opreme — preklapanje termina za isti uredaj.

  preklapanja(oprema_id, od, do, iskljuci_id=None)
      -> [(id, status, vrijeme_od, vrijeme_do, osoba)] za statuse 'odobreno' i 'na_cekanju'
  zauzeti_termini(oprema_id, dana=30)
      -> nadolazeci termini (odobreno + na cekanju) za prikaz u formi
  opis(r) -> kratki tekst termina

Termini se dodiruju bez preklapanja (kraj jednog = pocetak drugog je dopusten).
Otkazani i odbijeni zahtjevi ne zauzimaju uredaj.
"""
from db import fetch, lokalno


def preklapanja(oprema_id, od, do, iskljuci_id=None):
    return fetch("""
        SELECT k.id, k.status, k.vrijeme_od, k.vrijeme_do,
               coalesce(k.provoditelj, k.podnositelj)
        FROM koristenje_opreme k
        WHERE k.oprema_id = %s
          AND k.status IN ('odobreno', 'na_cekanju')
          AND k.vrijeme_od < %s AND k.vrijeme_do > %s
          AND (%s IS NULL OR k.id <> %s)
        ORDER BY k.vrijeme_od;""", (oprema_id, do, od, iskljuci_id, iskljuci_id))


def zauzeti_termini(oprema_id, dana=30):
    return fetch(f"""
        SELECT k.id, k.status, k.vrijeme_od, k.vrijeme_do,
               coalesce(k.provoditelj, k.podnositelj)
        FROM koristenje_opreme k
        WHERE k.oprema_id = %s
          AND k.status IN ('odobreno', 'na_cekanju')
          AND k.vrijeme_do > now() AND k.vrijeme_od < now() + interval '{int(dana)} days'
        ORDER BY k.vrijeme_od;""", (oprema_id,))


def opis(r):
    _id, status, od, do, osoba = r
    od, do = lokalno(od), lokalno(do)
    kraj = f"{do:%H:%M}" if od.date() == do.date() else f"{do:%d.%m. %H:%M}"
    st_ = "odobreno" if status == "odobreno" else "na cekanju"
    return f"#{_id} · {od:%d.%m. %H:%M} – {kraj} · {osoba or '—'} · {st_}"


def razvrstaj(rows):
    """-> (odobreni, na_cekanju)"""
    return ([r for r in rows if r[1] == "odobreno"], [r for r in rows if r[1] == "na_cekanju"])
