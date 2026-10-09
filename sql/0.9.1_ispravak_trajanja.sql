-- =============================================================
--  v0.9.1 — Ispravak trajanja pokusa + popravak vremenske zone
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run (prije objave 0.9.1).
-- =============================================================

-- 1) Jednokratni popravak vremena zahtjeva upisanih do sada.
--    Do v0.9.0 aplikacija je vrijeme slala bez vremenske zone, a baza (UTC) ga je
--    spremila kao UTC: zahtjev za 08:00 prikazivao se kao 10:00 (zimi 09:00).
--    Popravak se izvodi SAMO pri prvom pokretanju (dok stupac plan_vrijeme_od ne
--    postoji) i samo ako je baza u UTC — ponovno pokretanje nista ne pomice.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'koristenje_opreme'
                     AND column_name = 'plan_vrijeme_od')
       AND current_setting('TimeZone') IN ('UTC', 'Etc/UTC', 'GMT')
    THEN
        UPDATE koristenje_opreme
        SET vrijeme_od = (vrijeme_od AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Zagreb',
            vrijeme_do = (vrijeme_do AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Zagreb';
        RAISE NOTICE 'Vremena zahtjeva ispravljena (UTC -> Europe/Zagreb).';
    END IF;
END $$;

-- 2) Ispravak trajanja: prvotno planirano vrijeme + tko je i kada ispravio
ALTER TABLE koristenje_opreme
    ADD COLUMN IF NOT EXISTS plan_vrijeme_od TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS plan_vrijeme_do TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS izmijenio       TEXT,
    ADD COLUMN IF NOT EXISTS datum_izmjene   TIMESTAMPTZ;

-- 3) osoba_id = provoditelj pokusa iz tablice osoblje (prazno za vanjske osobe)
--    Stupac postoji od pocetka, ali ga aplikacija nije koristila (bio je prazan).
--    Osiguraj da pokazuje na osoblje(id), pa popuni postojece zapise.
DO $$
DECLARE c RECORD;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'koristenje_opreme' AND column_name = 'osoba_id') THEN
        ALTER TABLE koristenje_opreme ADD COLUMN osoba_id BIGINT;
    END IF;
    -- makni postojece veze stupca osoba_id (ako ih ima) i postavi vezu na osoblje
    FOR c IN
        SELECT con.conname FROM pg_constraint con
        JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
        WHERE con.conrelid = 'koristenje_opreme'::regclass AND con.contype = 'f'
          AND a.attname = 'osoba_id'
    LOOP
        EXECUTE format('ALTER TABLE koristenje_opreme DROP CONSTRAINT %I', c.conname);
    END LOOP;
    ALTER TABLE koristenje_opreme
        ADD CONSTRAINT koristenje_opreme_osoba_id_fkey
        FOREIGN KEY (osoba_id) REFERENCES osoblje(id);
END $$;

UPDATE koristenje_opreme k
SET osoba_id = o.id
FROM osoblje o
WHERE k.osoba_id IS NULL
  AND o.ime_prezime = coalesce(k.provoditelj, k.podnositelj);

-- Provjera:
-- SELECT id, podnositelj, provoditelj, osoba_id FROM koristenje_opreme ORDER BY id;
