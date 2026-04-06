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

    # Ensure every required column exists before any caller touches them
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
) -> tuple[bool, str]:
    sb = get_client()
    try:
        payload = {
            "event_name": name, "event_type": etype, "category": category,
            "format": fmt, "start_date": str(start), "end_date": str(end),
            "country": country, "gender": gender, "notes": notes,
        }
        if user_id:
            payload["created_by"] = user_id
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
#  PROFILES — profiles table only, no legacy tables
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
                           phone: str = "", location: str = "") -> tuple[bool, str]:
    """Users update ONLY name / phone / location — never status or role."""
    sb = get_client()
    try:
        sb.table("profiles").update({
            "name":     name.strip(),
            "phone":    phone.strip(),
            "location": location.strip(),
        }).eq("id", user_id).execute()
        return True, "ok"
    except Exception as e:
        return False, f"db_error:{e}"


def update_user_status(user_id: str, status: str) -> tuple[bool, str]:
    """Admin only. Validated before DB call."""
    if status not in ("pending", "approved", "rejected"):
        return False, "Invalid status."
    sb = get_client()
    try:
        sb.table("profiles").update({"status": status}).eq("id", user_id).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def update_user_role(user_id: str, role: str) -> tuple[bool, str]:
    """Admin only. Validated before DB call."""
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
        sb.table("leagues").insert({"league_name": league_name.strip(), "country": country.strip()}).execute()
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
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def load_matches(event_id: int | None = None) -> pd.DataFrame:
    try:
        sb = get_client()
        q  = sb.table("matches").select(
            "*, events(event_name, gender, category), "
            "team1:teams!matches_team1_id_fkey(team_name), "
            "team2:teams!matches_team2_id_fkey(team_name)"
        ).order("match_date")
        if event_id:
            q = q.eq("event_id", event_id)
        df = pd.DataFrame(q.execute().data or [])
    except Exception:
        df = pd.DataFrame()

    if not df.empty and "match_date" in df.columns:
        df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
        df = df.dropna(subset=["match_date"])
    return df


def add_match(
    event_id: int, match_name: str, match_date: date,
    team1_id: int | None = None, team2_id: int | None = None,
    venue: str = "", notes: str = "",
) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("matches").insert({
            "event_id":   event_id,
            "match_name": match_name.strip(),
            "match_date": str(match_date),
            "team1_id":   team1_id,
            "team2_id":   team2_id,
            "venue":      venue.strip(),
            "notes":      notes.strip(),
        }).execute()
        load_matches.clear()
        return True, f"Match **{match_name}** added."
    except APIError as e:
        return False, str(e)


def bulk_add_matches(rows: list[dict]) -> tuple[int, list[str]]:
    """rows: list of dicts with keys: event_id, match_name, match_date, team1_id, team2_id, venue"""
    success, warns = 0, []
    for r in rows:
        ok, msg = add_match(
            r["event_id"], r.get("match_name",""), r["match_date"],
            r.get("team1_id"), r.get("team2_id"), r.get("venue",""),
        )
        if ok:
            success += 1
        else:
            warns.append(msg)
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


def add_registration(event_id: int, start_date: date, deadline: date,
                     notes: str = "", user_id: str | None = None) -> tuple[bool, str]:
    sb = get_client()
    try:
        payload = {
            "event_id":   event_id,
            "start_date": str(start_date),
            "deadline":   str(deadline),
            "notes":      notes.strip(),
        }
        if user_id:
            payload["created_by"] = user_id
        sb.table("registrations").insert(payload).execute()
        load_registrations.clear()
        return True, "Registration window added."
    except APIError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  AUCTIONS
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def load_auctions() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("auctions").select("*, events(event_name)").order("auction_date").execute()
        df   = pd.DataFrame(resp.data or [])
    except Exception:
        df = pd.DataFrame()

    if not df.empty and "auction_date" in df.columns:
        df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce")
        df = df.dropna(subset=["auction_date"])
    return df


def add_auction(event_id: int, franchise_name: str, auction_date: date,
                location: str = "", notes: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("auctions").insert({
            "event_id":       event_id,
            "franchise_name": franchise_name.strip(),
            "auction_date":   str(auction_date),
            "location":       location.strip(),
            "notes":          notes.strip(),
        }).execute()
        load_auctions.clear()
        return True, f"Auction for **{franchise_name}** added."
    except APIError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  CLIENTS
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=120, show_spinner=False)
def load_clients() -> pd.DataFrame:
    try:
        sb   = get_client()
        resp = sb.table("clients").select("*").order("client_name").execute()
        return pd.DataFrame(resp.data or [])
    except Exception:
        return pd.DataFrame()


def add_client(client_name: str, email: str = "", phone: str = "",
               country: str = "", citizenship: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("clients").insert({
            "client_name": client_name.strip(),
            "email":       email.strip(),
            "phone":       phone.strip(),
            "country":     country.strip(),
            "citizenship": citizenship.strip(),
        }).execute()
        load_clients.clear()
        return True, f"Client **{client_name}** added."
    except APIError as e:
        return False, str(e)


def tag_client_player(client_id: int, player_id: int) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("client_player_map").insert({"client_id": client_id, "player_id": player_id}).execute()
        return True, "Tagged."
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, "Already tagged."
        return False, str(e)


def tag_client_event(client_id: int, event_id: int) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("client_event_map").insert({"client_id": client_id, "event_id": event_id}).execute()
        return True, "Tagged."
    except APIError as e:
        if "unique" in str(e).lower() or "23505" in str(e):
            return False, "Already tagged."
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  TRAVEL PLANS
# ═══════════════════════════════════════════════════════════════

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


def add_travel_plan(player_id: int, event_id: int | None, departure_date: date | None,
                    arrival_date: date | None, from_country: str = "",
                    to_country: str = "", notes: str = "") -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("travel_plans").insert({
            "player_id":      player_id,
            "event_id":       event_id,
            "departure_date": str(departure_date) if departure_date else None,
            "arrival_date":   str(arrival_date)   if arrival_date   else None,
            "from_country":   from_country.strip(),
            "to_country":     to_country.strip(),
            "notes":          notes.strip(),
        }).execute()
        return True, "Travel plan added."
    except APIError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  VISA STATUS
# ═══════════════════════════════════════════════════════════════

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
                    status: str = "pending", expiry_date: date | None = None) -> tuple[bool, str]:
    sb = get_client()
    try:
        sb.table("visa_status").insert({
            "player_id":   player_id,
            "country":     country.strip(),
            "visa_type":   visa_type.strip(),
            "status":      status,
            "expiry_date": str(expiry_date) if expiry_date else None,
        }).execute()
        return True, "Visa status added."
    except APIError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  PLAYER UNAVAILABILITY
# ═══════════════════════════════════════════════════════════════

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
            "player_id":  player_id,
            "start_date": str(start_date),
            "end_date":   str(end_date),
            "reason":     reason.strip(),
        }).execute()
        return True, "Unavailability period added."
    except APIError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

def get_pending_notifications() -> list[dict]:
    from datetime import datetime, timezone as tz
    sb = get_client()
    try:
        now  = datetime.now(tz.utc).isoformat()
        resp = (
            sb.table("notifications")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_at", now)
            .order("scheduled_at")
            .execute()
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
            sb.table("notifications")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
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
    """Fire-and-forget activity log insert."""
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
            sb.table("activity_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#  MULTI-ENTITY CALENDAR AGGREGATOR
# ═══════════════════════════════════════════════════════════════

def load_calendar_items(
    gender: str | None = None,
    category: str | None = None,
    event_id: int | None = None,
    player_id: int | None = None,
) -> pd.DataFrame:
    """
    Aggregate events, matches, registrations, auctions into one
    normalised DataFrame with columns:
        id, type, title, start_date, end_date, metadata (dict)
    """
    rows: list[dict] = []

    # ── Events ────────────────────────────────────────────────
    ev = load_events(gender=gender, category=category)
    if event_id and not ev.empty:
        ev = ev[ev["id"] == event_id]
    for _, r in ev.iterrows():
        rows.append({
            "id":         int(r["id"]) if "id" in r and pd.notna(r.get("id")) else 0,
            "type":       "event",
            "title":      r.get("event_name", ""),
            "start_date": r["start_date"],
            "end_date":   r["end_date"],
            "metadata": {
                "format":   r.get("format",""),
                "category": r.get("category",""),
                "gender":   r.get("gender",""),
                "country":  r.get("country",""),
            },
        })

    # ── Matches ───────────────────────────────────────────────
    ma = load_matches(event_id=event_id)
    for _, r in ma.iterrows():
        ev_name = ""
        if isinstance(r.get("events"), dict):
            ev_name = r["events"].get("event_name","")
        t1 = r.get("team1",{}) or {}
        t2 = r.get("team2",{}) or {}
        t1n = t1.get("team_name","") if isinstance(t1, dict) else ""
        t2n = t2.get("team_name","") if isinstance(t2, dict) else ""
        title = r.get("match_name","") or f"{t1n} vs {t2n}" or "Match"
        rows.append({
            "id":         int(r["id"]) if pd.notna(r.get("id")) else 0,
            "type":       "match",
            "title":      title,
            "start_date": r["match_date"],
            "end_date":   r["match_date"],
            "metadata": {
                "event":  ev_name,
                "team1":  t1n,
                "team2":  t2n,
                "venue":  r.get("venue",""),
            },
        })

    # ── Registrations ─────────────────────────────────────────
    reg = load_registrations()
    if event_id and not reg.empty and "event_id" in reg.columns:
        reg = reg[reg["event_id"] == event_id]
    for _, r in reg.iterrows():
        ev_name = ""
        if isinstance(r.get("events"), dict):
            ev_name = r["events"].get("event_name","")
        rows.append({
            "id":         int(r["id"]) if pd.notna(r.get("id")) else 0,
            "type":       "registration",
            "title":      f"Registration: {ev_name}",
            "start_date": r["start_date"],
            "end_date":   r["deadline"],
            "metadata":   {"event": ev_name, "deadline": str(r["deadline"].date() if pd.notna(r["deadline"]) else "")},
        })

    # ── Auctions ──────────────────────────────────────────────
    au = load_auctions()
    if event_id and not au.empty and "event_id" in au.columns:
        au = au[au["event_id"] == event_id]
    for _, r in au.iterrows():
        ev_name = ""
        if isinstance(r.get("events"), dict):
            ev_name = r["events"].get("event_name","")
        rows.append({
            "id":         int(r["id"]) if pd.notna(r.get("id")) else 0,
            "type":       "auction",
            "title":      f"Auction — {r.get('franchise_name','')}",
            "start_date": r["auction_date"],
            "end_date":   r["auction_date"],
            "metadata":   {"event": ev_name, "location": r.get("location","")},
        })

    if not rows:
        return pd.DataFrame(columns=["id","type","title","start_date","end_date","metadata"])

    df = pd.DataFrame(rows)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"]   = pd.to_datetime(df["end_date"],   errors="coerce")
    df = df.dropna(subset=["start_date"]).sort_values("start_date").reset_index(drop=True)
    return df


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATION SCHEDULING HELPERS
# ═══════════════════════════════════════════════════════════════

def schedule_notifications_for_event(event_row: dict, recipients: list[str]) -> None:
    """Create pending notifications for an event (same-day morning)."""
    from datetime import datetime, time, timezone as tz
    import pytz
    start = event_row.get("start_date")
    if not start:
        return
    if isinstance(start, str):
        start = pd.to_datetime(start)
    send_at = datetime.combine(start.date(), time(7, 0), tzinfo=tz.utc)
    for email in recipients:
        create_notification(
            user_email  = email,
            notif_type  = "event_start",
            entity_id   = event_row["id"],
            entity_type = "event",
            message     = f"Event starting today: {event_row.get('event_name','')}",
            scheduled_at= send_at,
        )


def schedule_notifications_for_match(match_row: dict, recipients: list[str]) -> None:
    from datetime import datetime, time, timezone as tz
    match_date = match_row.get("match_date")
    if not match_date:
        return
    if isinstance(match_date, str):
        match_date = pd.to_datetime(match_date)
    send_at = datetime.combine(match_date.date(), time(7, 0), tzinfo=tz.utc)
    for email in recipients:
        create_notification(
            user_email  = email,
            notif_type  = "match_start",
            entity_id   = match_row["id"],
            entity_type = "match",
            message     = f"Match today: {match_row.get('match_name', 'Match')}",
            scheduled_at= send_at,
        )
