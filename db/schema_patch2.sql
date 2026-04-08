-- ══════════════════════════════════════════════════════════════
--  SCMA Calendar Dashboard — Schema Patch 2
--  Run in: Supabase → SQL Editor → New Query
--  Safe to re-run (uses IF NOT EXISTS / IF EXISTS guards).
-- ══════════════════════════════════════════════════════════════


-- ── ISSUE 1: Resolve clients table conflict ───────────────────
-- schema.sql has a lean clients table (client_name, email, phone…)
-- schema_clients.sql defines a richer one (full_name, sensitive…)
-- Resolution: rename the old table, then schema_clients.sql wins.

DO $$ BEGIN
  IF EXISTS (
      SELECT 1 FROM pg_tables
      WHERE tablename = 'clients' AND schemaname = 'public'
  ) AND NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name   = 'clients'
        AND column_name  = 'full_name'
  ) THEN
    -- Old lean table present, no full_name → rename it
    ALTER TABLE public.clients RENAME TO clients_old;
    RAISE NOTICE 'Renamed old clients table to clients_old';
  END IF;
END $$;

-- ── ISSUE 4: Make event_id nullable on teams & squad ──────────
ALTER TABLE public.teams ALTER COLUMN event_id DROP NOT NULL;
ALTER TABLE public.squad ALTER COLUMN event_id DROP NOT NULL;

-- ── ISSUE 9: Add designation column to profiles ───────────────
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS designation TEXT DEFAULT '';

-- ── ISSUE 15: Add match_datetime column to matches ────────────
ALTER TABLE public.matches ADD COLUMN IF NOT EXISTS match_datetime TIMESTAMPTZ;

-- ── Ensure schema_clients tables exist (idempotent) ───────────
-- (schema_clients.sql creates clients + client_sensitive;
--  run schema_clients.sql after this if not already applied)

-- ══════════════════════════════════════════════════════════════
--  DONE.
--  After running this, also run db/schema_clients.sql
--  if the clients / client_sensitive tables don't exist yet.
-- ══════════════════════════════════════════════════════════════
