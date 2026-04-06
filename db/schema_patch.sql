-- ══════════════════════════════════════════════════════════════
--  SCMA Calendar Dashboard — Incremental Schema Patch
--  Run in: Supabase → SQL Editor → New Query
--  Run AFTER schema.sql has been applied.
-- ══════════════════════════════════════════════════════════════

-- Phase 1: allow standalone matches / registrations / auctions
ALTER TABLE public.matches       ALTER COLUMN event_id DROP NOT NULL;
ALTER TABLE public.registrations ALTER COLUMN event_id DROP NOT NULL;
ALTER TABLE public.auctions      ALTER COLUMN event_id DROP NOT NULL;

-- Ensure timezone column exists on profiles (safe to re-run)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC';
