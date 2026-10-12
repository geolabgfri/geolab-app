-- =============================================================
--  v0.12.0 — Odobreni termini istog uredaja ne smiju se preklapati
--  (zastita u samoj bazi — vrijedi i za rucne unose u Supabaseu)
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run.
-- =============================================================

-- 1) Pregled postojecih preklapanja (ako ih ima, prvo ih rijesi u aplikaciji:
--    Odobravanje -> Uredivanje zahtjeva -> promijeni termin ili otkazi)
SELECT a.id AS zahtjev, b.id AS preklapa_se_s, a.oprema_id,
       a.vrijeme_od, a.vrijeme_do, b.vrijeme_od AS b_od, b.vrijeme_do AS b_do
FROM koristenje_opreme a
JOIN koristenje_opreme b
  ON a.oprema_id = b.oprema_id AND a.id < b.id
 AND a.status = 'odobreno' AND b.status = 'odobreno'
 AND a.vrijeme_od < b.vrijeme_do AND a.vrijeme_do > b.vrijeme_od;

-- 2) Ogranicenje (doda se samo ako preklapanja nema; inace javi poruku)
CREATE EXTENSION IF NOT EXISTS btree_gist;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint
               WHERE conname = 'koristenje_opreme_bez_preklapanja') THEN
        RAISE NOTICE 'Ogranicenje vec postoji.';
    ELSIF EXISTS (
        SELECT 1 FROM koristenje_opreme a JOIN koristenje_opreme b
          ON a.oprema_id = b.oprema_id AND a.id < b.id
         AND a.status = 'odobreno' AND b.status = 'odobreno'
         AND a.vrijeme_od < b.vrijeme_do AND a.vrijeme_do > b.vrijeme_od) THEN
        RAISE NOTICE 'POSTOJE PREKLAPANJA (vidi upit 1) — ogranicenje NIJE dodano. Rijesi ih pa pokreni skriptu ponovno.';
    ELSE
        ALTER TABLE koristenje_opreme
            ADD CONSTRAINT koristenje_opreme_bez_preklapanja
            EXCLUDE USING gist (
                oprema_id WITH =,
                tstzrange(vrijeme_od, vrijeme_do, '[)') WITH &&
            ) WHERE (status = 'odobreno');
        RAISE NOTICE 'Ogranicenje dodano: odobreni termini istog uredaja ne mogu se preklapati.';
    END IF;
END $$;
