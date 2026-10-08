-- =============================================================
--  v0.8.2 — Odbijeni zahtjevi za opremu se brisu
--  Od 0.8.2 aplikacija odbijeni zahtjev odmah brise. Ova skripta JEDNOKRATNO
--  brise zahtjeve koji su odbijeni ranije (status 'odbijeno'). Nije obavezna.
--  Pokreni u Supabase -> SQL Editor -> Run.
-- =============================================================

-- Pregled prije brisanja:
-- SELECT id, oprema_id, podnositelj, vrijeme_od, odobrio, datum_odobrenja
-- FROM koristenje_opreme WHERE status = 'odbijeno';

DELETE FROM koristenje_opreme WHERE status = 'odbijeno';
