-- =============================================================
--  v0.11.0 — Uredivanje zahtjeva (administrator) + trag izmjena (ISO)
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run (prije objave 0.11.0).
-- =============================================================

-- 1) Novi status 'otkazano' (zahtjev ostaje u evidenciji, ne ulazi u sate)
DO $$
DECLARE c RECORD;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'koristenje_opreme'::regclass AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%status%'
    LOOP
        EXECUTE format('ALTER TABLE koristenje_opreme DROP CONSTRAINT %I', c.conname);
    END LOOP;
END $$;

ALTER TABLE koristenje_opreme ADD CONSTRAINT koristenje_opreme_status_check
    CHECK (status IN ('na_cekanju', 'odobreno', 'odbijeno', 'otkazano'));

-- 2) Trag izmjena: jedan redak po promijenjenom polju; retci se nikad ne mijenjaju
CREATE TABLE IF NOT EXISTS koristenje_opreme_izmjene (
    id          BIGSERIAL PRIMARY KEY,
    zahtjev_id  BIGINT NOT NULL REFERENCES koristenje_opreme(id) ON DELETE CASCADE,
    polje       TEXT NOT NULL,
    staro       TEXT,
    novo        TEXT,
    napomena    TEXT NOT NULL,
    izmijenio   TEXT NOT NULL,
    vrijeme     TIMESTAMPTZ NOT NULL DEFAULT now(),
    beta        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS koristenje_opreme_izmjene_zahtjev_idx
    ON koristenje_opreme_izmjene (zahtjev_id);

ALTER TABLE koristenje_opreme_izmjene ENABLE ROW LEVEL SECURITY;
