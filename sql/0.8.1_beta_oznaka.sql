-- =============================================================
--  v0.8.1 — Oznaka BETA (prijelazno razdoblje do 1. 1. 2027.)
--
--  Svaki NOVI zapis dobiva beta = TRUE (testni unos iz prijelaznog razdoblja).
--  Sve sto je vec u bazi (stvarni podaci) dobiva beta = FALSE.
--  Aplikacija se ne mijenja — oznaku postavlja sama baza (DEFAULT).
--  Na kraju bete: sql/1.0.0_kraj_bete.sql
--
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run.
-- =============================================================
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'koristenje_opreme', 'kvarovi_opreme', 'uzorci', 'ispitivanja',
        'projekti', 'projekt_suradnici', 'klijenti', 'oprema', 'komponente'
    ]
    LOOP
        IF to_regclass('public.' || t) IS NOT NULL THEN
            -- postojeci retci: FALSE (stvarni podaci)
            EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS beta BOOLEAN NOT NULL DEFAULT FALSE', t);
            -- novi retci od sada: TRUE (testni unos)
            EXECUTE format('ALTER TABLE %I ALTER COLUMN beta SET DEFAULT TRUE', t);
        END IF;
    END LOOP;
END $$;

-- Provjera: koliko je beta zapisa po tablici
-- SELECT 'koristenje_opreme' AS tablica, count(*) FILTER (WHERE beta) AS beta, count(*) AS ukupno FROM koristenje_opreme
-- UNION ALL SELECT 'kvarovi_opreme', count(*) FILTER (WHERE beta), count(*) FROM kvarovi_opreme
-- UNION ALL SELECT 'uzorci',         count(*) FILTER (WHERE beta), count(*) FROM uzorci
-- UNION ALL SELECT 'projekti',       count(*) FILTER (WHERE beta), count(*) FROM projekti
-- UNION ALL SELECT 'oprema',         count(*) FILTER (WHERE beta), count(*) FROM oprema;
