-- =============================================================
--  v0.9.0 — Provoditelj ispitivanja + e-mail adrese osoblja (kopija obavijesti)
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run (prije objave 0.9.0).
-- =============================================================

-- 1) Provoditelj ispitivanja (prazno = isti kao podnositelj)
ALTER TABLE koristenje_opreme ADD COLUMN IF NOT EXISTS provoditelj TEXT;

-- 2) E-mail adrese osoblja
ALTER TABLE osoblje ADD COLUMN IF NOT EXISTS email TEXT;

-- Popuni po pravilu ime.prezime@gradri.uniri.hr
--   mala slova, bez dijakritika (c c s z d), samo PRVO prezime
--   npr. "Martina Vivoda Prodan" -> martina.vivoda@gradri.uniri.hr
-- Puni samo prazna polja, pa rucne ispravke ostaju sacuvane.
UPDATE osoblje
SET email = translate(lower(split_part(trim(ime_prezime), ' ', 1)),
                      'čćšžđČĆŠŽĐ', 'ccszdccszd')
         || '.' ||
            translate(lower(split_part(trim(ime_prezime), ' ', 2)),
                      'čćšžđČĆŠŽĐ', 'ccszdccszd')
         || '@gradri.uniri.hr'
WHERE email IS NULL AND trim(ime_prezime) LIKE '% %';

-- Provjera:
-- SELECT ime_prezime, email FROM osoblje ORDER BY ime_prezime;
