-- ══════════════════════════════════════════════════════════════
--  SCMA Calendar Dashboard — Complete Schema (Single File)
--  Run once in: Supabase → SQL Editor → New Query
--
--  Safe to re-run: uses CREATE TABLE IF NOT EXISTS everywhere.
--  ORDER: profiles → leagues → events → teams → squad → ...
-- ══════════════════════════════════════════════════════════════


-- ════════════════════════════════════════════════════════════
--  STEP 1: DROP ALL OLD POLICIES & LEGACY TABLES
-- ════════════════════════════════════════════════════════════

-- Drop old helper functions (may cause recursion if left in place)
DROP FUNCTION IF EXISTS public.is_approved()       CASCADE;
DROP FUNCTION IF EXISTS public.is_admin()          CASCADE;
DROP FUNCTION IF EXISTS public.can_edit()          CASCADE;
DROP FUNCTION IF EXISTS public.auth_is_approved()  CASCADE;
DROP FUNCTION IF EXISTS public.auth_is_admin()     CASCADE;
DROP FUNCTION IF EXISTS public.auth_can_edit()     CASCADE;

-- Drop legacy tables from old systems
DROP TABLE IF EXISTS public.user_roles      CASCADE;
DROP TABLE IF EXISTS public.allowed_users   CASCADE;
DROP TABLE IF EXISTS public.access_requests CASCADE;

-- Drop old policies on tables that may or may not exist yet
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename='profiles' AND schemaname='public') THEN
        DROP POLICY IF EXISTS "users_read_own_profile"     ON public.profiles;
        DROP POLICY IF EXISTS "users_insert_own_profile"   ON public.profiles;
        DROP POLICY IF EXISTS "users_update_own_profile"   ON public.profiles;
        DROP POLICY IF EXISTS "admins_read_all_profiles"   ON public.profiles;
        DROP POLICY IF EXISTS "admins_update_all_profiles" ON public.profiles;
        DROP POLICY IF EXISTS "profile_select_own"         ON public.profiles;
        DROP POLICY IF EXISTS "profile_select_admin"       ON public.profiles;
        DROP POLICY IF EXISTS "profile_insert_own"         ON public.profiles;
        DROP POLICY IF EXISTS "profile_update_own_safe"    ON public.profiles;
        DROP POLICY IF EXISTS "profile_update_admin"       ON public.profiles;
        DROP POLICY IF EXISTS "profile_delete_admin"       ON public.profiles;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename='events' AND schemaname='public') THEN
        DROP POLICY IF EXISTS "allow_all_events"        ON public.events;
        DROP POLICY IF EXISTS "auth_read_events"        ON public.events;
        DROP POLICY IF EXISTS "editors_write_events"    ON public.events;
        DROP POLICY IF EXISTS "editors_update_events"   ON public.events;
        DROP POLICY IF EXISTS "editors_update_events2"  ON public.events;
        DROP POLICY IF EXISTS "admins_delete_events"    ON public.events;
        DROP POLICY IF EXISTS "admins_delete_events2"   ON public.events;
        DROP POLICY IF EXISTS "approved_read_events"    ON public.events;
        DROP POLICY IF EXISTS "editors_insert_events"   ON public.events;
        DROP POLICY IF EXISTS "events_select"           ON public.events;
        DROP POLICY IF EXISTS "events_insert"           ON public.events;
        DROP POLICY IF EXISTS "events_update"           ON public.events;
        DROP POLICY IF EXISTS "events_delete"           ON public.events;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename='teams' AND schemaname='public') THEN
        DROP POLICY IF EXISTS "allow_all_teams"         ON public.teams;
        DROP POLICY IF EXISTS "auth_read_teams"         ON public.teams;
        DROP POLICY IF EXISTS "editors_write_teams"     ON public.teams;
        DROP POLICY IF EXISTS "editors_update_teams"    ON public.teams;
        DROP POLICY IF EXISTS "editors_update_teams2"   ON public.teams;
        DROP POLICY IF EXISTS "admins_delete_teams"     ON public.teams;
        DROP POLICY IF EXISTS "approved_read_teams"     ON public.teams;
        DROP POLICY IF EXISTS "editors_insert_teams"    ON public.teams;
        DROP POLICY IF EXISTS "teams_select"            ON public.teams;
        DROP POLICY IF EXISTS "teams_insert"            ON public.teams;
        DROP POLICY IF EXISTS "teams_update"            ON public.teams;
        DROP POLICY IF EXISTS "teams_delete"            ON public.teams;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename='squad' AND schemaname='public') THEN
        DROP POLICY IF EXISTS "allow_all_squad"         ON public.squad;
        DROP POLICY IF EXISTS "auth_read_squad"         ON public.squad;
        DROP POLICY IF EXISTS "editors_write_squad"     ON public.squad;
        DROP POLICY IF EXISTS "editors_update_squad"    ON public.squad;
        DROP POLICY IF EXISTS "editors_update_squad2"   ON public.squad;
        DROP POLICY IF EXISTS "admins_delete_squad"     ON public.squad;
        DROP POLICY IF EXISTS "approved_read_squad"     ON public.squad;
        DROP POLICY IF EXISTS "editors_insert_squad"    ON public.squad;
        DROP POLICY IF EXISTS "squad_select"            ON public.squad;
        DROP POLICY IF EXISTS "squad_insert"            ON public.squad;
        DROP POLICY IF EXISTS "squad_update"            ON public.squad;
        DROP POLICY IF EXISTS "squad_delete"            ON public.squad;
    END IF;
END $$;


-- ════════════════════════════════════════════════════════════
--  STEP 2: CREATE TABLES (correct dependency order)
-- ════════════════════════════════════════════════════════════

-- ── 1. PROFILES (extends auth.users) ─────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
    id         UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email      TEXT        NOT NULL UNIQUE,
    name       TEXT        NOT NULL DEFAULT '',
    phone      TEXT                 DEFAULT '',
    location   TEXT                 DEFAULT '',
    timezone   TEXT        NOT NULL DEFAULT 'UTC',
    status     TEXT        NOT NULL DEFAULT 'pending'
                           CHECK (status IN ('pending','approved','rejected')),
    role       TEXT        NOT NULL DEFAULT 'viewer'
                           CHECK (role IN ('admin','editor','viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email  ON public.profiles (email);
CREATE INDEX IF NOT EXISTS idx_profiles_status ON public.profiles (status);

-- ── 2. LEAGUES ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.leagues (
    id          BIGSERIAL   PRIMARY KEY,
    league_name TEXT        NOT NULL UNIQUE,
    country     TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 3. EVENTS (tournaments / series) ─────────────────────────
CREATE TABLE IF NOT EXISTS public.events (
    id          BIGSERIAL   PRIMARY KEY,
    league_id   BIGINT      REFERENCES public.leagues(id) ON DELETE SET NULL,
    event_name  TEXT        NOT NULL UNIQUE,
    event_type  TEXT        NOT NULL DEFAULT 'tournament'
                            CHECK (event_type IN ('series','tournament')),
    category    TEXT        NOT NULL DEFAULT 'International'
                            CHECK (category IN ('International','Domestic','League')),
    format      TEXT        NOT NULL DEFAULT 'T20',
    gender      TEXT        NOT NULL DEFAULT 'Male'
                            CHECK (gender IN ('Male','Female','Mixed')),
    country     TEXT        NOT NULL DEFAULT '',
    start_date  DATE        NOT NULL,
    end_date    DATE        NOT NULL,
    notes       TEXT                 DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_event_dates CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_events_dates    ON public.events (start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_events_gender   ON public.events (gender);
CREATE INDEX IF NOT EXISTS idx_events_category ON public.events (category);
CREATE INDEX IF NOT EXISTS idx_events_league   ON public.events (league_id);

-- ── 4. TEAMS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.teams (
    id          BIGSERIAL   PRIMARY KEY,
    event_id    BIGINT      REFERENCES public.events(id) ON DELETE CASCADE,
    event_name  TEXT        NOT NULL DEFAULT '',
    team_name   TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (event_name, team_name)
);

CREATE INDEX IF NOT EXISTS idx_teams_event_id ON public.teams (event_id);

-- ── 5. PLAYERS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.players (
    id          BIGSERIAL   PRIMARY KEY,
    player_name TEXT        NOT NULL UNIQUE,
    country     TEXT                 DEFAULT '',
    role        TEXT                 DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 6. SQUAD ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.squad (
    id          BIGSERIAL   PRIMARY KEY,
    event_id    BIGINT      REFERENCES public.events(id)  ON DELETE CASCADE,
    team_id     BIGINT      REFERENCES public.teams(id)   ON DELETE CASCADE,
    player_id   BIGINT      REFERENCES public.players(id) ON DELETE CASCADE,
    -- denormalised columns kept for backwards compatibility
    player_name TEXT        DEFAULT '',
    event_name  TEXT        DEFAULT '',
    event_type  TEXT        DEFAULT '',
    category    TEXT        DEFAULT '',
    format      TEXT        DEFAULT '',
    start_date  DATE,
    end_date    DATE,
    team        TEXT        DEFAULT '',
    gender      TEXT        DEFAULT '',
    country     TEXT        DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_name, event_name, team)
);

CREATE INDEX IF NOT EXISTS idx_squad_event_id ON public.squad (event_id);
CREATE INDEX IF NOT EXISTS idx_squad_player   ON public.squad (player_id);
CREATE INDEX IF NOT EXISTS idx_squad_dates    ON public.squad (start_date, end_date);

-- ── 7. MATCHES ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.matches (
    id          BIGSERIAL   PRIMARY KEY,
    event_id    BIGINT      NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    match_name  TEXT        NOT NULL DEFAULT '',
    match_date  DATE        NOT NULL,
    team1_id    BIGINT      REFERENCES public.teams(id) ON DELETE SET NULL,
    team2_id    BIGINT      REFERENCES public.teams(id) ON DELETE SET NULL,
    venue       TEXT                 DEFAULT '',
    notes       TEXT                 DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_event ON public.matches (event_id);
CREATE INDEX IF NOT EXISTS idx_matches_date  ON public.matches (match_date);

-- ── 8. REGISTRATIONS ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.registrations (
    id          BIGSERIAL   PRIMARY KEY,
    event_id    BIGINT      NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    start_date  DATE        NOT NULL,
    deadline    DATE        NOT NULL,
    notes       TEXT                 DEFAULT '',
    created_by  UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reg_dates CHECK (deadline >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_reg_event ON public.registrations (event_id);
CREATE INDEX IF NOT EXISTS idx_reg_dates ON public.registrations (start_date, deadline);

-- ── 9. AUCTIONS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.auctions (
    id              BIGSERIAL   PRIMARY KEY,
    event_id        BIGINT      NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    franchise_name  TEXT        NOT NULL DEFAULT '',
    auction_date    DATE        NOT NULL,
    location        TEXT                 DEFAULT '',
    notes           TEXT                 DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auctions_event ON public.auctions (event_id);
CREATE INDEX IF NOT EXISTS idx_auctions_date  ON public.auctions (auction_date);

-- ── 10. CLIENTS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.clients (
    id          BIGSERIAL   PRIMARY KEY,
    client_name TEXT        NOT NULL,
    email       TEXT                 DEFAULT '',
    phone       TEXT                 DEFAULT '',
    country     TEXT                 DEFAULT '',
    citizenship TEXT                 DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 11. CLIENT ↔ PLAYER MAP ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.client_player_map (
    client_id   BIGINT NOT NULL REFERENCES public.clients(id)  ON DELETE CASCADE,
    player_id   BIGINT NOT NULL REFERENCES public.players(id)  ON DELETE CASCADE,
    PRIMARY KEY (client_id, player_id)
);

-- ── 12. CLIENT ↔ EVENT MAP ────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.client_event_map (
    client_id   BIGINT NOT NULL REFERENCES public.clients(id)  ON DELETE CASCADE,
    event_id    BIGINT NOT NULL REFERENCES public.events(id)   ON DELETE CASCADE,
    PRIMARY KEY (client_id, event_id)
);

-- ── 13. TRAVEL PLANS ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.travel_plans (
    id              BIGSERIAL   PRIMARY KEY,
    player_id       BIGINT      NOT NULL REFERENCES public.players(id) ON DELETE CASCADE,
    event_id        BIGINT      REFERENCES public.events(id) ON DELETE SET NULL,
    departure_date  DATE,
    arrival_date    DATE,
    from_country    TEXT                 DEFAULT '',
    to_country      TEXT                 DEFAULT '',
    notes           TEXT                 DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_travel_player ON public.travel_plans (player_id);
CREATE INDEX IF NOT EXISTS idx_travel_event  ON public.travel_plans (event_id);

-- ── 14. VISA STATUS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.visa_status (
    id          BIGSERIAL   PRIMARY KEY,
    player_id   BIGINT      NOT NULL REFERENCES public.players(id) ON DELETE CASCADE,
    country     TEXT        NOT NULL DEFAULT '',
    visa_type   TEXT                 DEFAULT '',
    status      TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','approved','rejected')),
    expiry_date DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visa_player ON public.visa_status (player_id);

-- ── 15. PLAYER UNAVAILABILITY ─────────────────────────────────
CREATE TABLE IF NOT EXISTS public.player_unavailability (
    id          BIGSERIAL   PRIMARY KEY,
    player_id   BIGINT      NOT NULL REFERENCES public.players(id) ON DELETE CASCADE,
    start_date  DATE        NOT NULL,
    end_date    DATE        NOT NULL,
    reason      TEXT                 DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_unavail_dates CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_unavail_player ON public.player_unavailability (player_id);
CREATE INDEX IF NOT EXISTS idx_unavail_dates  ON public.player_unavailability (start_date, end_date);

-- ── 16. NOTIFICATIONS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.notifications (
    id           BIGSERIAL   PRIMARY KEY,
    user_email   TEXT        NOT NULL,
    type         TEXT        NOT NULL
                             CHECK (type IN ('event_start','match_start','registration','auction')),
    entity_id    BIGINT      NOT NULL,
    entity_type  TEXT        NOT NULL
                             CHECK (entity_type IN ('event','match','registration','auction')),
    message      TEXT        NOT NULL DEFAULT '',
    status       TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','sent','failed')),
    scheduled_at TIMESTAMPTZ NOT NULL,
    sent_at      TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_email, type, entity_id, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_notif_status    ON public.notifications (status);
CREATE INDEX IF NOT EXISTS idx_notif_scheduled ON public.notifications (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_notif_email     ON public.notifications (user_email);

-- ── 17. ACTIVITY LOGS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id          BIGSERIAL   PRIMARY KEY,
    user_id     UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    user_email  TEXT                 DEFAULT '',
    action      TEXT        NOT NULL,
    entity_type TEXT                 DEFAULT '',
    entity_id   BIGINT,
    details     JSONB                DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_user    ON public.activity_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_logs_created ON public.activity_logs (created_at DESC);


-- ════════════════════════════════════════════════════════════
--  STEP 3: SECURITY DEFINER HELPER FUNCTIONS
--  These run with postgres privileges so policies on `profiles`
--  can call them without causing infinite recursion.
-- ════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION public.auth_is_approved()
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND status = 'approved'
    );
$$;

CREATE OR REPLACE FUNCTION public.auth_is_admin()
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND status = 'approved' AND role = 'admin'
    );
$$;

CREATE OR REPLACE FUNCTION public.auth_can_edit()
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND status = 'approved' AND role IN ('admin','editor')
    );
$$;


-- ════════════════════════════════════════════════════════════
--  STEP 4: ENABLE RLS + CREATE POLICIES
-- ════════════════════════════════════════════════════════════

-- ── profiles ──────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profile_select_own"
    ON public.profiles FOR SELECT TO authenticated
    USING (id = auth.uid());

CREATE POLICY "profile_select_admin"
    ON public.profiles FOR SELECT TO authenticated
    USING (public.auth_is_admin());

CREATE POLICY "profile_insert_own"
    ON public.profiles FOR INSERT TO authenticated
    WITH CHECK (id = auth.uid() AND status = 'pending' AND role = 'viewer');

-- Users may update only name/phone/location/timezone — status and role are frozen
CREATE POLICY "profile_update_own_safe"
    ON public.profiles FOR UPDATE TO authenticated
    USING (id = auth.uid())
    WITH CHECK (
        id     = auth.uid()
        AND status = (SELECT p.status FROM public.profiles p WHERE p.id = auth.uid())
        AND role   = (SELECT p.role   FROM public.profiles p WHERE p.id = auth.uid())
    );

CREATE POLICY "profile_update_admin"
    ON public.profiles FOR UPDATE TO authenticated
    USING (public.auth_is_admin());

CREATE POLICY "profile_delete_admin"
    ON public.profiles FOR DELETE TO authenticated
    USING (public.auth_is_admin());

-- ── All other tables: one loop ────────────────────────────────
DO $$ DECLARE t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
      'events','teams','squad','leagues','matches','players',
      'registrations','auctions','clients',
      'client_player_map','client_event_map',
      'travel_plans','visa_status','player_unavailability',
      'notifications','activity_logs'
  ]) LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);

    EXECUTE format(
      'CREATE POLICY "%s_select" ON public.%I FOR SELECT TO authenticated USING (public.auth_is_approved())',
      t, t
    );
    EXECUTE format(
      'CREATE POLICY "%s_insert" ON public.%I FOR INSERT TO authenticated WITH CHECK (public.auth_can_edit())',
      t, t
    );
    EXECUTE format(
      'CREATE POLICY "%s_update" ON public.%I FOR UPDATE TO authenticated USING (public.auth_can_edit())',
      t, t
    );
    EXECUTE format(
      'CREATE POLICY "%s_delete" ON public.%I FOR DELETE TO authenticated USING (public.auth_is_admin())',
      t, t
    );
  END LOOP;
END $$;


-- ════════════════════════════════════════════════════════════
--  DONE — all tables, indexes, functions and policies created.
--
--  Next step: seed your first admin user.
--  1. Sign up or sign in to the app once (creates auth.users row)
--  2. Go to Supabase → Authentication → Users → copy your UUID
--  3. Run the INSERT below (replace both values):
--
--  INSERT INTO public.profiles (id, email, name, status, role)
--  VALUES (
--      'paste-your-uuid-here',
--      'your@email.com',
--      'Your Name',
--      'approved',
--      'admin'
--  )
--  ON CONFLICT (id) DO UPDATE
--      SET status = 'approved', role = 'admin';
-- ════════════════════════════════════════════════════════════
