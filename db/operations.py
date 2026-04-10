# db/operations.py
from __future__ import annotations

import pandas as pd
import streamlit as st
from datetime import date
from postgrest.exceptions import APIError

from db.supabase_client import get_client

_REQUIRED_EVENT_COLS = [
    "event_name", "event_type", "category", "format",
    "start_date", "end_date", "country", "gender",
]


# ═══════════════════════════════════════════════════════════════
#  READ — events / teams / squad
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def load_events(gender: str | None = None, category: str | None = None) -> pd.DataFrame:
    """
    Always returns a valid DataFrame.
    Guarantees required columns exist.
    Never raises KeyError.
    """
    try:
        sb = get_client()
        q  = sb.table("events").select("*").order("start_date")
        if gender:
            q = q.eq("gender", gender)
        if category:
            q = q.eq("category", category)
        data = q.execute().data or []
        df   = pd.DataFrame(data)
    except Exception:
        df = pd.DataFrame()

    for col in _REQUIRED_EVENT_COLS:
        if col not in df.columns:
            df[col] = ""

    if not df.empty:
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["end_date"]   = pd.to_datetime(df["end_date"],   errors="coerce")
        df = df.dropna(subset=["start_date", "end_date"]).reset_index(drop=True)

    return df


@st.cache_data(ttl=60, show_spinner=False)
def load_teams() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("teams").select("*").execute()
        return pd.DataFrame(resp.data or [])
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def load_squad() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("squad").select("*").order("start_date").execute()
        df   = pd.DataFrame(resp.data or [])
    except Exception:
        df = pd.DataFrame()

    if not df.empty:
        for col in ["start_date", "end_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df.dropna(subset=["start_date", "end_date"]).reset_index(drop=True)

    return df


def search_events(query: str, year: int | None = None) -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("events").select("*").ilike("event_name", f"%{query}%").execute()
        df   = pd.DataFrame(resp.data or [])
    except Exception:
        df = pd.DataFrame()

    for col in _REQUIRED_EVENT_COLS:
        if col not in df.columns:
            df[col] = ""

    if not df.empty:
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["end_date"]   = pd.to_datetime(df["end_date"],   errors="coerce")
        df = df.dropna(subset=["start_date", "end_date"]).reset_index(drop=True)
        if year:
            df = df[
                (df["start_date"].dt.year == year) |
                (df["end_date"].dt.year   == year)
            ]
    return df


def event_names() -> list[str]:
    df = load_events()
    return df["event_name"].tolist() if not df.empty else []


def teams_for_event(event_name: str) -> list[str]:
    df = load_teams()
    if df.empty or "event_name" not in df.columns:
        return []
    return df[df["event_name"] == event_name]["team_name"].tolist()


# ═══════════════════════════════════════════════════════════════
#  WRITE — events / teams / squad
# ═══════════════════════════════════════════════════════════════

def add_event(
    name: str, etype: str, category: str, fmt: str,
    start: date, end: date, country: str, gender: str,
    notes: str = "", user_id: str | None = None,
    league_id: int | None = None,
    timezone: str = "UTC",   # ✅ ADD THIS
) -> tuple[bool, str]:
    sb = get_client()
    try:
        payload = {
            "event_name": name,
            "event_type": etype,
            "category": category,
            "format": fmt,
            "start_date": str(start),
            "end_date": str(end),
            "country": country,
            "gender": gender,
            "notes": notes,
            "timezone": timezone,   # ✅ ADD THIS
        }
        if user_id:
            payload["created_by"] = user_id
        if league_id is not None:
            payload["league_id"] = league_id
        sb.table("events").insert(payload).execute()
        load_events.clear()
        return True, f"✅ Event **{name}** added."
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, f"Event **{name}** already exists."
        return False, f"Database error: {e}"


def update_event(event_id: int, payload: dict) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("events").update(payload).eq("id", event_id).execute()
        load_events.clear()
        return True, "Event updated."
    except APIError as e:
        return False, str(e)


def delete_event(event_id: int) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("events").delete().eq("id", event_id).execute()
        load_events.clear()
        return True, "Event deleted."
    except APIError as e:
        return False, str(e)


def add_team(event_name: str, team_name: str) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("teams").insert({
            "event_name": event_name, "team_name": team_name,
        }).execute()
        load_teams.clear()
        return True, f"✅ **{team_name}** added to *{event_name}*."
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, f"**{team_name}** already in *{event_name}*."
        return False, f"Database error: {e}"


def add_teams_bulk(event_name: str, team_names: list[str]) -> tuple[int, list[str]]:
    ok_count, warns = 0, []
    for t in team_names:
        t = t.strip()
        if not t:
            continue
        ok, msg = add_team(event_name, t)
        if ok:
            ok_count += 1
        else:
            warns.append(msg)
    return ok_count, warns


def add_player_to_squad(player: str, event_name: str, team: str) -> tuple[bool, str]:
    sb = get_client()
    try:
        resp = (
            sb.table("events")
            .select("*")
            .eq("event_name", event_name)
            .single()
            .execute()
        )
        ev = resp.data
    except Exception as e:
        return False, f"Event not found: {e}"

    try:
        sb.table("squad").insert({
            "player_name": player.strip(),
            "event_name":  event_name,
            "event_type":  ev["event_type"],
            "category":    ev["category"],
            "format":      ev["format"],
            "start_date":  ev["start_date"],
            "end_date":    ev["end_date"],
            "team":        team,
            "gender":      ev["gender"],
            "country":     ev["country"],
        }).execute()
        load_squad.clear()
        return True, f"✅ **{player}** added to {team} / {event_name}."
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, f"**{player}** already in {team} / {event_name}."
        return False, f"Database error: {e}"


def bulk_add_players(players: list[str], event_name: str, team: str) -> tuple[int, list[str]]:
    success, warns = 0, []
    for p in players:
        ok, msg = add_player_to_squad(p, event_name, team)
        if ok:
            success += 1
        else:
            warns.append(msg)
    return success, warns


# ═══════════════════════════════════════════════════════════════
#  PROFILES
# ═══════════════════════════════════════════════════════════════

def get_profile(user_id: str) -> dict | None:
    sb = get_client()
    try:
        resp = (
            sb.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return resp.data
    except Exception:
        return None


def create_profile(user_id: str, email: str, name: str,
                   phone: str = "", location: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("profiles").insert({
            "id":       user_id,
            "email":    email.strip().lower(),
            "name":     name.strip(),
            "phone":    phone.strip(),
            "location": location.strip(),
            "status":   "pending",
            "role":     "viewer",
        }).execute()
        return True, "ok"
    except APIError as e:
        if "23505" in str(e) or "unique" in str(e).lower():
            return False, "profile_exists"
        return False, f"db_error:{e}"
    except Exception as e:
        return False, f"db_error:{e}"


def update_profile_details(user_id: str, name: str,
                           phone: str = "", location: str = "",
                           timezone: str = "UTC") -> tuple[bool, str]:
    """Users update ONLY name / phone / location / timezone — never status or role."""
    sb = get_client()
    try:
        sb.table("profiles").update({
            "name":     name.strip(),
            "phone":    phone.strip(),
            "location": location.strip(),
            "timezone": timezone or "UTC",
        }).eq("id", user_id).execute()
        return True, "ok"
    except Exception as e:
        return False, f"db_error:{e}"


def update_user_status(user_id: str, status: str) -> tuple[bool, str]:
    if status not in ("pending", "approved", "rejected"):
        return False, "Invalid status."
    sb = get_client()
    try:
        sb.table("profiles").update({"status": status}).eq("id", user_id).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def update_user_role(user_id: str, role: str) -> tuple[bool, str]:
    if role not in ("admin", "editor", "viewer"):
        return False, "Invalid role."
    sb = get_client()
    try:
        sb.table("profiles").update({"role": role}).eq("id", user_id).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def get_all_users() -> list[dict]:
    sb = get_client()
    try:
        resp = (
            sb.table("profiles")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


def get_pending_users() -> list[dict]:
    sb = get_client()
    try:
        resp = (
            sb.table("profiles")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


def get_user_timezone(user_id: str) -> str:
    """Return the IANA timezone string for a user, defaulting to UTC."""
    profile = get_profile(user_id)
    return (profile or {}).get("timezone", "UTC") or "UTC"


# ═══════════════════════════════════════════════════════════════
#  LEAGUES
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=120, show_spinner=False)
def load_leagues() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("leagues").select("*").order("league_name").execute()
        return pd.DataFrame(resp.data or [])
    except Exception:
        return pd.DataFrame()


def add_league(league_name: str, country: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("leagues").insert({
            "league_name": league_name.strip(),
            "country":     country.strip(),
        }).execute()
        load_leagues.clear()
        return True, f"League **{league_name}** added."
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, f"League **{league_name}** already exists."
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  PLAYERS
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=120, show_spinner=False)
def load_players() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("players").select("*").order("player_name").execute()
        return pd.DataFrame(resp.data or [])
    except Exception:
        return pd.DataFrame()


def add_player(player_name: str, country: str = "", role: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("players").insert({
            "player_name": player_name.strip(),
            "country":     country.strip(),
            "role":        role.strip(),
        }).execute()
        load_players.clear()
        return True, f"Player **{player_name}** added."
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, f"Player **{player_name}** already exists."
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  MATCHES
#  match_datetime (TIMESTAMPTZ) is the source of truth.
#  match_date     (DATE)        is kept for filtering/grouping.
#  ALL callers must provide match_time + tz_name so this module
#  can derive match_datetime via datetime_utils.to_utc().
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def load_matches(event_id: int | None = None) -> pd.DataFrame:
    """
    Load matches. event_id optional — None returns all (incl. standalones).
    Guarantees match_datetime is always a UTC-aware Timestamp (never NaT):
    existing records without match_datetime fall back to match_date at 00:00 UTC.
    """
    from utils.datetime_utils import normalize_datetime

    try:
        sb = get_client()
        q  = sb.table("matches").select("*").order("match_date")
        if event_id is not None:
            q = q.eq("event_id", event_id)
        df = pd.DataFrame(q.execute().data or [])
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return df

    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df = df.dropna(subset=["match_date"]).reset_index(drop=True)

    # Normalize match_datetime: parse UTC-aware, then backfill from match_date
    if "match_datetime" not in df.columns:
        df["match_datetime"] = pd.NaT
    else:
        df["match_datetime"] = pd.to_datetime(
            df["match_datetime"], utc=True, errors="coerce"
        )

    df["match_datetime"] = df.apply(
        lambda r: normalize_datetime(r["match_date"], r["match_datetime"]),
        axis=1,
    )

    return df


def add_match(
    event_id: int | None,
    match_name: str,
    match_date: date,
    team1_id: int | None = None,
    team2_id: int | None = None,
    venue: str = "",
    notes: str = "",
    # ── datetime fields (new) ──────────────────────────────
    match_time: str = "00:00",
    tz_name: str = "UTC",
) -> tuple[bool, str]:
    """
    Add a match with full datetime precision.

    match_date  (DATE)       — kept for grouping/filtering.
    match_time  (str HH:MM)  — combined with match_date + tz_name.
    tz_name     (IANA str)   — user's local timezone at input time.
    match_datetime is derived via datetime_utils.to_utc() and stored as UTC.
    """
    from utils.datetime_utils import to_utc

    sb = get_client()

    if event_id is not None:
        try:
            ev_check = (
                sb.table("events").select("id")
                .eq("id", event_id).maybe_single().execute()
            )
            if not ev_check.data:
                return False, "Referenced event not found."
        except Exception as e:
            return False, f"Event validation failed: {e}"

    # Duplicate guard: same date + both teams
    if team1_id and team2_id:
        try:
            dup = (
                sb.table("matches").select("id")
                .eq("match_date", str(match_date))
                .eq("team1_id", team1_id)
                .eq("team2_id", team2_id)
                .maybe_single().execute()
            )
            if dup.data:
                return False, "A match with these teams on this date already exists."
        except Exception:
            pass

    # ── STEP 1: fetch event timezone ─────────────────────
    event_tz = None

    if event_id:
        try:
            ev = (
                sb.table("events")
                .select("timezone")
                .eq("id", event_id)
                .maybe_single()
                .execute()
            )
            if ev.data and ev.data.get("timezone"):
                event_tz = ev.data["timezone"]
        except Exception:
            pass

    # ── STEP 2: decide final timezone ────────────────────
    if tz_name:
        final_tz = tz_name
    elif event_tz:
        final_tz = event_tz
    else:
        final_tz = "UTC"

    # ── STEP 3: convert to UTC ───────────────────────────
    match_datetime_utc = to_utc(
        match_date,
        match_time or "00:00",
        final_tz
    )

    try:
        payload: dict = {
            "match_name":     match_name.strip(),
            "match_date":     str(match_date),
            "match_datetime": match_datetime_utc.isoformat(),
            "team1_id":       team1_id,
            "team2_id":       team2_id,
            "venue":          venue.strip(),
            "notes":          notes.strip(),
        }
        if event_id is not None:
            payload["event_id"] = event_id
        sb.table("matches").insert(payload).execute()
        load_matches.clear()
        return True, f"Match **{match_name}** added."
    except APIError as e:
        return False, str(e)


def bulk_add_matches(rows: list[dict]) -> tuple[int, list[str]]:
    """
    Bulk insert matches from CSV or other sources.

    Each dict may contain:
        Required : event_id, match_name, match_date (date object)
        Optional : match_time (str HH:MM, default "00:00")
                   timezone   (IANA str, default "UTC")
                   team1_id, team2_id, venue

    match_datetime is derived from match_date + match_time + timezone
    via datetime_utils.to_utc(). No time is ever silently discarded.
    """
    success, warns = 0, []
    for i, r in enumerate(rows):
        match_date = r.get("match_date")
        if match_date is None:
            warns.append(f"Row {i+1}: missing match_date — skipped.")
            continue

        ok, msg = add_match(
            event_id   = r.get("event_id"),
            match_name = r.get("match_name", ""),
            match_date = match_date,
            team1_id   = r.get("team1_id"),
            team2_id   = r.get("team2_id"),
            venue      = r.get("venue", ""),
            notes      = r.get("notes", ""),
            match_time = r.get("match_time", "00:00") or "00:00",
            tz_name    = r.get("timezone")  # allow fallback logic
        )
        if ok:
            success += 1
        else:
            warns.append(f"Row {i+1}: {msg}")

    return success, warns


# ═══════════════════════════════════════════════════════════════
#  REGISTRATIONS
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def load_registrations() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("registrations").select("*, events(event_name)").order("start_date").execute()
        df   = pd.DataFrame(resp.data or [])
    except Exception:
        df = pd.DataFrame()

    if not df.empty:
        for c in ["start_date", "deadline"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def add_registration(event_id: int | None, start_date: date, deadline: date,
                     notes: str = "", user_id: str | None = None) -> tuple[bool, str]:
    if start_date > deadline:
        return False, "Deadline must be on or after start date."
    sb = get_client()
    try:
        payload: dict = {
            "start_date": str(start_date),
            "deadline":   str(deadline),
            "notes":      notes.strip(),
        }
        if event_id is not None:
            payload["event_id"] = event_id
        if user_id:
            payload["created_by"] = user_id
        sb.table("registrations").insert(payload).execute()
        load_registrations.clear()
        return True, "Registration window added."
    except APIError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  AUCTIONS
#  auction_datetime (TIMESTAMPTZ) is the source of truth.
#  auction_date     (DATE)        is kept for filtering/grouping.
#  franchise_name column is NOT removed (backward compat with DB)
#  but is no longer written or read by this codebase.
#  New column needed: auction_name (TEXT), auction_datetime (TIMESTAMPTZ).
#
#  SQL migration (run once in Supabase SQL Editor):
#  ─────────────────────────────────────────────────
#  ALTER TABLE public.auctions
#      ADD COLUMN IF NOT EXISTS auction_name     TEXT        DEFAULT '',
#      ADD COLUMN IF NOT EXISTS auction_datetime TIMESTAMPTZ,
#      ADD COLUMN IF NOT EXISTS location         TEXT        DEFAULT '',
#      ADD COLUMN IF NOT EXISTS notes            TEXT        DEFAULT '';
#  -- franchise_name is intentionally left in place (existing rows).
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def load_auctions() -> pd.DataFrame:
    """
    Load auctions with a guaranteed UTC-aware auction_datetime column.
    Existing rows with NULL auction_datetime fall back to auction_date at 00:00 UTC.
    """
    from utils.datetime_utils import normalize_datetime

    try:
        sb   = get_client()
        resp = sb.table("auctions").select("*, events(event_name)").order("auction_date").execute()
        df   = pd.DataFrame(resp.data or [])
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return df

    df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce")
    df = df.dropna(subset=["auction_date"]).reset_index(drop=True)

    if "auction_datetime" not in df.columns:
        df["auction_datetime"] = pd.NaT
    else:
        df["auction_datetime"] = pd.to_datetime(
            df["auction_datetime"], utc=True, errors="coerce"
        )

    df["auction_datetime"] = df.apply(
        lambda r: normalize_datetime(r["auction_date"], r["auction_datetime"]),
        axis=1,
    )

    # Derive display name: prefer auction_name, fall back to franchise_name for old rows
    if "auction_name" not in df.columns:
        df["auction_name"] = ""
    if "franchise_name" in df.columns:
        df["auction_name"] = df["auction_name"].where(
            df["auction_name"].str.strip() != "", df.get("franchise_name", "")
        )

    return df


def add_auction(
    event_id: int | None,
    auction_name: str,
    auction_date: date,
    location: str = "",
    notes: str = "",
    # ── datetime fields ────────────────────────────────────
    auction_time: str = "00:00",
    tz_name: str = "UTC",
) -> tuple[bool, str]:
    """
    Add an auction with full datetime precision.

    auction_date    (DATE)      — kept for grouping/filtering.
    auction_time    (str HH:MM) — combined with auction_date + tz_name.
    tz_name         (IANA str)  — user's local timezone at input time.
    auction_datetime is derived via datetime_utils.to_utc() → stored as UTC.

    franchise_name is NOT written; the column is kept for DB backward compat.
    """
    from utils.datetime_utils import to_utc

    if not auction_name.strip():
        return False, "Auction name is required."

    auction_datetime_utc = to_utc(
        auction_date,
        auction_time or "00:00",
        tz_name or "UTC",
    )

    sb = get_client()
    try:
        payload: dict = {
            "auction_name":     auction_name.strip(),
            "auction_date":     str(auction_date),
            "auction_datetime": auction_datetime_utc.isoformat(),
            "location":         location.strip(),
            "notes":            notes.strip(),
        }
        if event_id is not None:
            payload["event_id"] = event_id
        sb.table("auctions").insert(payload).execute()
        load_auctions.clear()
        return True, f"Auction **{auction_name}** added."
    except APIError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  CLIENTS
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=120, show_spinner=False)
def load_clients() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("clients").select("*").order("full_name").execute()
        return pd.DataFrame(resp.data or [])
    except Exception:
        return pd.DataFrame()


def add_client_full(
    full_name: str, first_name: str, last_name: str,
    dob, citizenship: str, client_type: str,
    player_role: str = "", batting_style: str = "",
    bowling_style: str = "", shirt_number: str = "",
    espn_link: str = "",
    email: str = "", phone: str = "",
    passport_number: str = "", passport_expiry=None,
    visa_details: str = "", departure_airport: str = "",
) -> tuple[bool, str]:
    sb = get_client()

    try:
        dup = (
            sb.table("clients").select("id")
            .eq("full_name", full_name.strip())
            .maybe_single().execute()
        )
        if dup.data and dob:
            dup2 = (
                sb.table("clients").select("id")
                .eq("full_name", full_name.strip())
                .eq("dob", str(dob))
                .maybe_single().execute()
            )
            if dup2.data:
                return False, f"Client **{full_name}** with this date of birth already exists."
    except Exception:
        pass

    try:
        resp = sb.table("clients").insert({
            "full_name":     full_name.strip(),
            "first_name":    first_name.strip(),
            "last_name":     last_name.strip(),
            "dob":           str(dob) if dob else None,
            "citizenship":   citizenship.strip(),
            "client_type":   client_type,
            "player_role":   player_role.strip(),
            "batting_style": batting_style.strip(),
            "bowling_style": bowling_style.strip(),
            "shirt_number":  shirt_number.strip(),
            "espn_link":     espn_link.strip(),
        }).execute()
        client_id = resp.data[0]["id"] if resp.data else None
    except APIError as e:
        if "23505" in str(e) or "unique" in str(e).lower():
            return False, f"Client **{full_name}** already exists."
        return False, f"DB error: {e}"
    except Exception as e:
        return False, f"Error saving client: {e}"

    if client_id is None:
        return False, "Client saved but ID not returned."

    has_sensitive = any([email, phone, passport_number, passport_expiry,
                         visa_details, departure_airport])
    if has_sensitive:
        try:
            sb.table("client_sensitive").insert({
                "client_id":         client_id,
                "email":             email.strip(),
                "phone":             phone.strip(),
                "passport_number":   passport_number.strip(),
                "passport_expiry":   str(passport_expiry) if passport_expiry else None,
                "visa_details":      visa_details.strip(),
                "departure_airport": departure_airport.strip(),
            }).execute()
        except Exception as e:
            load_clients.clear()
            return True, f"Client saved (ID {client_id}), but sensitive data failed: {e}"

    load_clients.clear()
    return True, f"Client **{full_name}** added successfully."


def load_client_sensitive(client_id: int) -> dict | None:
    from db.auth import is_admin as _is_admin
    if not _is_admin():
        return None
    sb = get_client()
    try:
        resp = (
            sb.table("client_sensitive").select("*")
            .eq("client_id", client_id).maybe_single().execute()
        )
        return resp.data
    except Exception:
        return None


def bulk_add_clients(rows: list[dict]) -> tuple[int, list[str]]:
    success, warns = 0, []
    for r in rows:
        full = r.get("full_name", "").strip()
        if not full:
            warns.append("Row skipped: full_name is empty.")
            continue
        ok, msg = add_client_full(
            full_name     = full,
            first_name    = r.get("first_name", ""),
            last_name     = r.get("last_name", ""),
            dob           = r.get("dob"),
            citizenship   = r.get("citizenship", ""),
            client_type   = r.get("client_type", "Player"),
            player_role   = r.get("player_role", ""),
            batting_style = r.get("batting_style", ""),
            bowling_style = r.get("bowling_style", ""),
            shirt_number  = r.get("shirt_number", ""),
            espn_link     = r.get("espn_link", ""),
        )
        if ok:
            success += 1
        else:
            warns.append(f"{full}: {msg}")
    return success, warns


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

def get_pending_notifications() -> list[dict]:
    from datetime import datetime, timezone as tz
    sb = get_client()
    try:
        now  = datetime.now(tz.utc).isoformat()
        resp = (
            sb.table("notifications").select("*")
            .eq("status", "pending")
            .lte("scheduled_at", now)
            .order("scheduled_at").execute()
        )
        return resp.data or []
    except Exception:
        return []


def mark_notification_sent(notif_id: int) -> None:
    from datetime import datetime, timezone as tz
    sb = get_client()
    try:
        sb.table("notifications").update({
            "status":  "sent",
            "sent_at": datetime.now(tz.utc).isoformat(),
        }).eq("id", notif_id).execute()
    except Exception:
        pass


def mark_notification_failed(notif_id: int) -> None:
    sb = get_client()
    try:
        sb.table("notifications").update({"status": "failed"}).eq("id", notif_id).execute()
    except Exception:
        pass


def create_notification(
    user_email: str, notif_type: str, entity_id: int,
    entity_type: str, message: str, scheduled_at,
) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("notifications").insert({
            "user_email":   user_email,
            "type":         notif_type,
            "entity_id":    entity_id,
            "entity_type":  entity_type,
            "message":      message,
            "status":       "pending",
            "scheduled_at": str(scheduled_at),
        }).execute()
        return True, "ok"
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, "duplicate"
        return False, str(e)


def get_all_notifications(limit: int = 200) -> list[dict]:
    sb = get_client()
    try:
        resp = (
            sb.table("notifications").select("*")
            .order("created_at", desc=True).limit(limit).execute()
        )
        return resp.data or []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  ACTIVITY LOGS
# ═══════════════════════════════════════════════════════════════

def log_activity(user_id: str | None, user_email: str, action: str,
                 entity_type: str = "", entity_id: int | None = None,
                 details: dict | None = None) -> None:
    sb = get_client()
    try:
        sb.table("activity_logs").insert({
            "user_id":     user_id,
            "user_email":  user_email,
            "action":      action,
            "entity_type": entity_type,
            "entity_id":   entity_id,
            "details":     details or {},
        }).execute()
    except Exception:
        pass


def get_activity_logs(limit: int = 300) -> list[dict]:
    sb = get_client()
    try:
        resp = (
            sb.table("activity_logs").select("*")
            .order("created_at", desc=True).limit(limit).execute()
        )
        return resp.data or []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  MULTI-ENTITY CALENDAR AGGREGATOR
#  match_datetime and auction_datetime are used for time display.
#  start_date / end_date remain the grid-placement key (date-only).
# ═══════════════════════════════════════════════════════════════

def load_calendar_items(
    gender: str | None = None,
    category: str | None = None,
    event_id: int | None = None,
) -> pd.DataFrame:
    """
    Aggregate events, matches, registrations, auctions into one normalised
    DataFrame with columns:
        id, type, title, start_date, end_date, metadata (dict)

    metadata for matches  includes: match_datetime_utc (ISO str), event, venue
    metadata for auctions includes: auction_datetime_utc (ISO str), event, location
    """
    rows: list[dict] = []

    # ── Events ────────────────────────────────────────────────
    ev = load_events(gender=gender, category=category)
    if event_id and not ev.empty and "id" in ev.columns:
        ev = ev[ev["id"] == event_id]
    for _, r in ev.iterrows():
        rows.append({
            "id":         int(r["id"]) if "id" in r and pd.notna(r.get("id")) else 0,
            "type":       "event",
            "title":      r.get("event_name", ""),
            "start_date": r["start_date"],
            "end_date":   r["end_date"],
            "metadata": {
                "format":   r.get("format", ""),
                "category": r.get("category", ""),
                "gender":   r.get("gender", ""),
                "country":  r.get("country", ""),
            },
        })

    # ── Matches — use match_datetime as the time-of-day truth ─
    ma = load_matches(event_id=event_id)
    for _, r in ma.iterrows():
        ev_name = ""
        if isinstance(r.get("events"), dict):
            ev_name = r["events"].get("event_name", "")
        title = r.get("match_name", "") or "Match"
        # match_datetime is guaranteed UTC-aware by load_matches()
        mdt = r.get("match_datetime")
        rows.append({
            "id":         int(r["id"]) if pd.notna(r.get("id")) else 0,
            "type":       "match",
            "title":      title,
            "start_date": r["match_date"],
            "end_date":   r["match_date"],
            "metadata": {
                "event":              ev_name,
                "venue":              r.get("venue", ""),
                "match_datetime_utc": mdt.isoformat() if mdt is not None else None,
            },
        })

    # ── Registrations ─────────────────────────────────────────
    reg = load_registrations()
    if event_id and not reg.empty and "event_id" in reg.columns:
        reg = reg[reg["event_id"] == event_id]
    for _, r in reg.iterrows():
        ev_name = ""
        if isinstance(r.get("events"), dict):
            ev_name = r["events"].get("event_name", "")
        rows.append({
            "id":         int(r["id"]) if pd.notna(r.get("id")) else 0,
            "type":       "registration",
            "title":      f"Registration: {ev_name}" if ev_name else "Registration Window",
            "start_date": r["start_date"],
            "end_date":   r["deadline"],
            "metadata": {
                "event":    ev_name,
                "deadline": str(r["deadline"].date()) if pd.notna(r.get("deadline")) else "",
            },
        })

    # ── Auctions — use auction_datetime as time-of-day truth ──
    au = load_auctions()
    if event_id and not au.empty and "event_id" in au.columns:
        au = au[au["event_id"] == event_id]
    for _, r in au.iterrows():
        ev_name = ""
        if isinstance(r.get("events"), dict):
            ev_name = r["events"].get("event_name", "")
        adt = r.get("auction_datetime")
        title = r.get("auction_name", "") or "Auction"
        rows.append({
            "id":         int(r["id"]) if pd.notna(r.get("id")) else 0,
            "type":       "auction",
            "title":      title,
            "start_date": r["auction_date"],
            "end_date":   r["auction_date"],
            "metadata": {
                "event":               ev_name,
                "location":            r.get("location", ""),
                "auction_datetime_utc": adt.isoformat() if adt is not None else None,
            },
        })

    if not rows:
        return pd.DataFrame(columns=["id", "type", "title", "start_date", "end_date", "metadata"])

    df = pd.DataFrame(rows)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"]   = pd.to_datetime(df["end_date"],   errors="coerce")
    df = df.dropna(subset=["start_date"]).sort_values("start_date").reset_index(drop=True)
    return df


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATION SCHEDULING HELPERS
# ═══════════════════════════════════════════════════════════════

def schedule_notifications_for_event(event_row: dict, recipients: list[str]) -> None:
    from datetime import datetime, time, timezone as tz
    start = event_row.get("start_date")
    if not start:
        return
    if isinstance(start, str):
        start = pd.to_datetime(start)
    send_at = datetime.combine(start.date(), time(7, 0), tzinfo=tz.utc)
    for email in recipients:
        create_notification(
            user_email   = email,
            notif_type   = "event_start",
            entity_id    = event_row["id"],
            entity_type  = "event",
            message      = f"Event starting today: {event_row.get('event_name', '')}",
            scheduled_at = send_at,
        )


def schedule_notifications_for_match(match_row: dict, recipients: list[str]) -> None:
    """
    Schedule notification based on match_datetime (UTC) if present,
    otherwise fall back to match_date at 07:00 UTC.
    """
    from utils.datetime_utils import normalize_datetime
    from datetime import datetime, time, timezone as tz

    match_date = match_row.get("match_date")
    mdt = match_row.get("match_datetime")
    match_datetime_utc = normalize_datetime(match_date, mdt)

    # Send 2 hours before match, defaulting to 07:00 UTC if time is midnight (fallback)
    if match_datetime_utc.hour == 0 and match_datetime_utc.minute == 0:
        send_at = match_datetime_utc.replace(hour=7)
    else:
        from datetime import timedelta
        send_at = match_datetime_utc - timedelta(hours=2)

    for email in recipients:
        create_notification(
            user_email   = email,
            notif_type   = "match_start",
            entity_id    = match_row["id"],
            entity_type  = "match",
            message      = f"Match today: {match_row.get('match_name', 'Match')}",
            scheduled_at = send_at,
        )


# ═══════════════════════════════════════════════════════════════
#  DELETE HELPERS (admin only — enforced by RLS)
# ═══════════════════════════════════════════════════════════════

def delete_match(match_id: int) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("matches").delete().eq("id", match_id).execute()
        load_matches.clear()
        return True, "Match deleted."
    except APIError as e:
        return False, str(e)


def delete_team(team_id: int) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("teams").delete().eq("id", team_id).execute()
        load_teams.clear()
        return True, "Team deleted."
    except APIError as e:
        return False, str(e)


def delete_squad_entry(squad_id: int) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("squad").delete().eq("id", squad_id).execute()
        load_squad.clear()
        return True, "Squad entry deleted."
    except APIError as e:
        return False, str(e)


# ── Travel / Visa / Unavailability — unchanged pass-through ──

def load_travel_plans(player_id: int | None = None) -> pd.DataFrame:
    try:
        sb = get_client()
        q  = sb.table("travel_plans").select(
            "*, players(player_name), events(event_name)"
        ).order("departure_date")
        if player_id:
            q = q.eq("player_id", player_id)
        df = pd.DataFrame(q.execute().data or [])
    except Exception:
        df = pd.DataFrame()
    if not df.empty:
        for c in ["departure_date", "arrival_date"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def add_travel_plan(player_id: int, event_id: int | None, departure_date,
                    arrival_date, from_country: str = "",
                    to_country: str = "", notes: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("travel_plans").insert({
            "player_id":      player_id, "event_id": event_id,
            "departure_date": str(departure_date) if departure_date else None,
            "arrival_date":   str(arrival_date)   if arrival_date   else None,
            "from_country":   from_country.strip(),
            "to_country":     to_country.strip(),
            "notes":          notes.strip(),
        }).execute()
        return True, "Travel plan added."
    except APIError as e:
        return False, str(e)


def load_visa_status(player_id: int | None = None) -> pd.DataFrame:
    try:
        sb = get_client()
        q  = sb.table("visa_status").select("*, players(player_name)").order("created_at", desc=True)
        if player_id:
            q = q.eq("player_id", player_id)
        df = pd.DataFrame(q.execute().data or [])
    except Exception:
        df = pd.DataFrame()
    if not df.empty and "expiry_date" in df.columns:
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
    return df


def add_visa_status(player_id: int, country: str, visa_type: str = "",
                    status: str = "pending", expiry_date=None) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("visa_status").insert({
            "player_id":   player_id, "country": country.strip(),
            "visa_type":   visa_type.strip(), "status": status,
            "expiry_date": str(expiry_date) if expiry_date else None,
        }).execute()
        return True, "Visa status added."
    except APIError as e:
        return False, str(e)


def load_unavailability(player_id: int | None = None) -> pd.DataFrame:
    try:
        sb = get_client()
        q  = sb.table("player_unavailability").select(
            "*, players(player_name)"
        ).order("start_date")
        if player_id:
            q = q.eq("player_id", player_id)
        df = pd.DataFrame(q.execute().data or [])
    except Exception:
        df = pd.DataFrame()
    if not df.empty:
        for c in ["start_date", "end_date"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def add_unavailability(player_id: int, start_date: date,
                       end_date: date, reason: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("player_unavailability").insert({
            "player_id":  player_id, "start_date": str(start_date),
            "end_date":   str(end_date), "reason": reason.strip(),
        }).execute()
        return True, "Unavailability period added."
    except APIError as e:
        return False, str(e)
