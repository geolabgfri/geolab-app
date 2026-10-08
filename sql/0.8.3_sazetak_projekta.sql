-- =============================================================
--  v0.8.3 — Sazetak istrazivackog projekta
--  Pokreni JEDNOM u Supabase -> SQL Editor -> Run (prije objave 0.8.3).
-- =============================================================
ALTER TABLE projekti ADD COLUMN IF NOT EXISTS sazetak TEXT;
