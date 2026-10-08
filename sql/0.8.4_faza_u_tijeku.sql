-- =============================================================
--  v0.8.4 — Faza 'u_tijeku' za istrazivacke projekte
--  Istrazivacki projekt: u_tijeku -> zavrseno
--  Strucni posao (Novi posao): upit -> ponuda -> narudzba -> izvjestaj -> zavrseno
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run (prije objave 0.8.4).
-- =============================================================

-- 1) Ako na stupcu 'faza' postoji CHECK ogranicenje, zamijeni ga prosirenim popisom
DO $$
DECLARE c RECORD;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'projekti'::regclass AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%faza%'
    LOOP
        EXECUTE format('ALTER TABLE projekti DROP CONSTRAINT %I', c.conname);
    END LOOP;
END $$;

ALTER TABLE projekti ADD CONSTRAINT projekti_faza_check
    CHECK (faza IS NULL OR faza IN
           ('upit','ponuda','narudzba','izvjestaj','u_tijeku','zavrseno'));

-- 2) Postojeci istrazivacki projekti koji nisu zavrseni -> u_tijeku
UPDATE projekti SET faza = 'u_tijeku'
WHERE vrsta = 'istrazivacki' AND coalesce(faza, '') <> 'zavrseno';
