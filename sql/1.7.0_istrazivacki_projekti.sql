-- =============================================================
--  v1.7.0 — Istrazivacki projekti u postojecoj tablici 'projekti'
--
--  'projekti' sada ima vrstu:
--     strucni      — posao za klijenta (Novi posao: upit -> ponuda -> ... )
--     istrazivacki — znanstveni projekt (HRZZ, NPOO, JICA ...); klijent = financijer
--  Istrazivacki projekt predlaze osoba iz 'osoblje', odobrava voditelj/laborant.
--  Na projekt se vezu: uzorci (kao i dosad), oprema nabavljena na projektu
--  (oprema.projekt_nabave = akronim) i koristenje opreme (koristenje_opreme.projekt_id).
--
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run. Postojeci retci ostaju
--  kakvi jesu (vrsta = 'strucni', status_odobrenja = 'odobreno').
-- =============================================================

-- 1) Nova polja u 'projekti'
ALTER TABLE projekti
    ADD COLUMN IF NOT EXISTS vrsta TEXT NOT NULL DEFAULT 'strucni'
        CHECK (vrsta IN ('strucni','istrazivacki')),
    ADD COLUMN IF NOT EXISTS akronim          TEXT,
    ADD COLUMN IF NOT EXISTS sifra            TEXT,          -- broj ugovora / sifra
    ADD COLUMN IF NOT EXISTS voditelj         TEXT,          -- ime iz 'osoblje'
    ADD COLUMN IF NOT EXISTS datum_pocetka    DATE,
    ADD COLUMN IF NOT EXISTS datum_zavrsetka  DATE,
    ADD COLUMN IF NOT EXISTS opis             TEXT,
    ADD COLUMN IF NOT EXISTS status_odobrenja TEXT NOT NULL DEFAULT 'odobreno'
        CHECK (status_odobrenja IN ('na_cekanju','odobreno','odbijeno')),
    ADD COLUMN IF NOT EXISTS predlozio        TEXT,
    ADD COLUMN IF NOT EXISTS odobrio          TEXT,
    ADD COLUMN IF NOT EXISTS datum_odobrenja  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS napomena_odluke  TEXT;

-- 2) Koristenje opreme moze se vezati na projekt (nije obavezno)
ALTER TABLE koristenje_opreme
    ADD COLUMN IF NOT EXISTS projekt_id BIGINT REFERENCES projekti(id);

-- 3) Postojeci istrazivacki projekt
UPDATE projekti SET vrsta = 'istrazivacki', akronim = 'REMOK'
WHERE oznaka = 'NPOO-2026-REMOK';

-- 4) Ciscenje ranijih pokusaja (1.6.0 i prva inacica 1.7.0), ako postoje.
--    Ako si u 1.6.0 testu ODOBRIO prijedlog, u 'projekti' je nastao probni posao:
--      SELECT id, oznaka, naziv FROM projekti ORDER BY id DESC LIMIT 5;
--      DELETE FROM projekti WHERE id = <id>;
ALTER TABLE koristenje_opreme DROP COLUMN IF EXISTS istrazivacki_projekt_id;
DROP TABLE IF EXISTS istrazivacki_projekti;
DROP TABLE IF EXISTS prijedlozi_projekata;
