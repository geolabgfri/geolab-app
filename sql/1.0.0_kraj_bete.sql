-- =============================================================
--  v1.0.0 — KRAJ BETE (pokrenuti tek kod prelaska na sluzbenu verziju)
--
--  Novi zapisi od tada vise nisu beta (DEFAULT FALSE).
--  Za beta zapise iz prijelaznog razdoblja odaberi JEDNU opciju:
--    A) zadrzi ih kao stvarne podatke  (beta -> FALSE)
--    B) obrisi ih kao testne           (nepovratno! prije toga napravi backup)
-- =============================================================

-- 1) Novi zapisi vise nisu beta
DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'koristenje_opreme', 'kvarovi_opreme', 'uzorci', 'ispitivanja',
        'projekti', 'projekt_suradnici', 'klijenti', 'oprema', 'komponente'
    ]
    LOOP
        IF to_regclass('public.' || t) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I ALTER COLUMN beta SET DEFAULT FALSE', t);
        END IF;
    END LOOP;
END $$;

-- 2A) Zadrzi beta zapise kao stvarne (makni oznaku)
-- DO $$
-- DECLARE t TEXT;
-- BEGIN
--     FOREACH t IN ARRAY ARRAY['koristenje_opreme','kvarovi_opreme','uzorci','ispitivanja',
--                              'projekti','projekt_suradnici','klijenti','oprema','komponente']
--     LOOP
--         IF to_regclass('public.' || t) IS NOT NULL THEN
--             EXECUTE format('UPDATE %I SET beta = FALSE WHERE beta', t);
--         END IF;
--     END LOOP;
-- END $$;

-- 2B) Obrisi beta zapise (redoslijed: prvo ovisni zapisi, pa oni na koje se vezu)
-- DELETE FROM ispitivanja       WHERE beta;
-- DELETE FROM koristenje_opreme WHERE beta;
-- DELETE FROM kvarovi_opreme    WHERE beta;
-- DELETE FROM uzorci            WHERE beta;
-- DELETE FROM projekt_suradnici WHERE beta;
-- DELETE FROM projekti          WHERE beta;
-- DELETE FROM klijenti          WHERE beta;
-- DELETE FROM komponente        WHERE beta;
-- DELETE FROM oprema            WHERE beta;
