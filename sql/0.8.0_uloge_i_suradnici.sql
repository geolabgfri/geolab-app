-- =============================================================
--  v0.8.0 — Uloge u aplikaciji + suradnici na projektima
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run (prije objave 0.8.0).
-- =============================================================

-- 1) Uloge osoblja (mijenjaju se kvacicom u Table Editoru, bez diranja koda)
--    administrator     — voditelj / laborant: odobravanje, oprema, uzorci, poslovi,
--                        pregledi; smije i predlagati projekte
--    znanstveno_zvanje — doc. / izv. prof. / prof.: smije predlagati istrazivacke projekte
ALTER TABLE osoblje
    ADD COLUMN IF NOT EXISTS administrator     BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS znanstveno_zvanje BOOLEAN NOT NULL DEFAULT FALSE;

-- voditelj i laborant su administratori (prema dosadasnjem stupcu 'uloga')
UPDATE osoblje SET administrator = TRUE
WHERE uloga ILIKE '%voditelj%' OR uloga ILIKE '%laborant%';

-- znanstveno-nastavno zvanje — oznaci stvarne osobe, npr.:
-- UPDATE osoblje SET znanstveno_zvanje = TRUE
-- WHERE ime_prezime IN ('Ime Prezime', 'Ime Prezime');

-- 2) Suradnici na projektu (osnova za buduci dnevnik: tko smije unositi
--    koristenje opreme na projektu)
CREATE TABLE IF NOT EXISTS projekt_suradnici (
    id          BIGSERIAL PRIMARY KEY,
    projekt_id  BIGINT  NOT NULL REFERENCES projekti(id) ON DELETE CASCADE,
    osoblje_id  BIGINT  NOT NULL REFERENCES osoblje(id),
    uloga       TEXT    NOT NULL DEFAULT 'suradnik'
                CHECK (uloga IN ('voditelj','suradnik')),
    UNIQUE (projekt_id, osoblje_id)
);

ALTER TABLE projekt_suradnici ENABLE ROW LEVEL SECURITY;

-- postojeci istrazivacki projekti: voditelj (ako je upisan) ide i u suradnike
INSERT INTO projekt_suradnici (projekt_id, osoblje_id, uloga)
SELECT p.id, o.id, 'voditelj'
FROM projekti p JOIN osoblje o ON o.ime_prezime = p.voditelj
WHERE p.vrsta = 'istrazivacki'
ON CONFLICT (projekt_id, osoblje_id) DO NOTHING;
