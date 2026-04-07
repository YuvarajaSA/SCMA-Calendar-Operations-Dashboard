-- ══════════════════════════════════════════════════════════════
--  SCMA Clients Module — SQL Schema Patch
--  Run in: Supabase → SQL Editor → New Query
--  Run AFTER schema.sql has been applied.
-- ══════════════════════════════════════════════════════════════

-- ── 1. CLIENTS (public data — all approved users can read) ────
CREATE TABLE IF NOT EXISTS public.clients (
    id              BIGSERIAL   PRIMARY KEY,
    full_name       TEXT        NOT NULL,
    first_name      TEXT        NOT NULL DEFAULT '',
    last_name       TEXT        NOT NULL DEFAULT '',
    dob             DATE,
    citizenship     TEXT                 DEFAULT '',
    client_type     TEXT        NOT NULL DEFAULT 'Player'
                                CHECK (client_type IN
                                    ('Player','Coach','Commentator','Analyst','Other')),
    player_role     TEXT                 DEFAULT '',
    batting_style   TEXT                 DEFAULT '',
    bowling_style   TEXT                 DEFAULT '',
    shirt_number    TEXT                 DEFAULT '',
    espn_link       TEXT                 DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Prevent exact duplicate: same full_name + dob
    UNIQUE (full_name, dob)
);

CREATE INDEX IF NOT EXISTS idx_clients_name ON public.clients (full_name);
CREATE INDEX IF NOT EXISTS idx_clients_type ON public.clients (client_type);

-- ── 2. CLIENT_SENSITIVE (restricted — admin only reads) ────────
--  Editors INSERT but cannot SELECT after saving.
--  Admins can SELECT, UPDATE, DELETE.
CREATE TABLE IF NOT EXISTS public.client_sensitive (
    id                  BIGSERIAL   PRIMARY KEY,
    client_id           BIGINT      NOT NULL
                                    REFERENCES public.clients(id) ON DELETE CASCADE,
    email               TEXT                 DEFAULT '',
    phone               TEXT                 DEFAULT '',
    passport_number     TEXT                 DEFAULT '',
    passport_expiry     DATE,
    visa_details        TEXT                 DEFAULT '',
    departure_airport   TEXT                 DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id)  -- one sensitive record per client
);

CREATE INDEX IF NOT EXISTS idx_sensitive_client ON public.client_sensitive (client_id);

-- ── RLS — clients (public data) ───────────────────────────────
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clients_select"
    ON public.clients FOR SELECT TO authenticated
    USING (public.auth_is_approved());

CREATE POLICY "clients_insert"
    ON public.clients FOR INSERT TO authenticated
    WITH CHECK (public.auth_can_edit());

CREATE POLICY "clients_update"
    ON public.clients FOR UPDATE TO authenticated
    USING (public.auth_can_edit());

CREATE POLICY "clients_delete"
    ON public.clients FOR DELETE TO authenticated
    USING (public.auth_is_admin());

-- ── RLS — client_sensitive ────────────────────────────────────
--  CRITICAL: Editors can INSERT but NOT SELECT after saving.
--  Only admins can read sensitive records.
ALTER TABLE public.client_sensitive ENABLE ROW LEVEL SECURITY;

-- Admins read all
CREATE POLICY "sensitive_select_admin"
    ON public.client_sensitive FOR SELECT TO authenticated
    USING (public.auth_is_admin());

-- Editors (and admins) can insert
CREATE POLICY "sensitive_insert"
    ON public.client_sensitive FOR INSERT TO authenticated
    WITH CHECK (public.auth_can_edit());

-- Only admins update or delete sensitive records
CREATE POLICY "sensitive_update_admin"
    ON public.client_sensitive FOR UPDATE TO authenticated
    USING (public.auth_is_admin());

CREATE POLICY "sensitive_delete_admin"
    ON public.client_sensitive FOR DELETE TO authenticated
    USING (public.auth_is_admin());

-- ══════════════════════════════════════════════════════════════
--  DONE. Tables: clients, client_sensitive
--  Sensitive data: admin-read-only. Editors can add, not view.
-- ══════════════════════════════════════════════════════════════
