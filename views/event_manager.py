
# views/event_manager.py  —  SCMA Event & Match Management
from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import date

from db.auth import can_edit, get_supabase_user, current_email
from db.operations import (
    load_events, load_teams,
    add_event, load_leagues, add_league,
    add_match, load_matches,
    add_registration, load_registrations,
    add_auction, load_auctions,
    log_activity,
)
from utils.datetime_utils import (
    TIMEZONES, time_options, format_display, validate_time_str, resolve_timezone,
)


# ─────────────────────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────────────────────

def _get_user_tz() -> str:
    """Read timezone from cached session profile."""
    profile = st.session_state.get("_cached_profile") or {}
    return profile.get("timezone", "UTC") or "UTC"


def _event_search_select(ev_df: pd.DataFrame, key: str) -> tuple[int | None, str]:
    """
    Searchable dropdown for event selection.
    Accepts a pre-loaded events DataFrame to avoid redundant DB calls.
    Returns (event_id, event_name).
    """
    event_options: dict[str, int | None] = {"(None)": None}
    if (
        not ev_df.empty
        and "event_name" in ev_df.columns
        and "id" in ev_df.columns
    ):
        for _, r in ev_df.iterrows():
            event_options[str(r["event_name"])] = int(r["id"])

    sel_name = st.selectbox(
        "Link to Event", list(event_options.keys()), key=f"es_{key}"
    )
    if sel_name == "(None)":
        return None, ""
    return event_options[sel_name], sel_name


def _resolve_event_tz(
    ev_df: pd.DataFrame,
    ev_id: int | None,
    venue: str,
) -> str:
    """
    Single source of truth for timezone resolution across all tabs.
    Uses resolve_timezone() exclusively — no manual fallback maps.
    Returns the best available timezone string.
    """
    if ev_id is None or ev_df.empty:
        return resolve_timezone(
            tz_name=None,
            event_tz=None,
            country=None,
            venue=venue or None,
        )

    row = ev_df[ev_df["id"] == ev_id]
    if row.empty:
        return resolve_timezone(None, None, None, venue or None)

    event_tz = row.iloc[0].get("timezone") if "timezone" in row.columns else None
    country  = row.iloc[0].get("country")  if "country"  in row.columns else None

    return resolve_timezone(
        tz_name=None,
        event_tz=event_tz,
        country=country,
        venue=venue or None,
    )


def _time_tz_row(form_key: str, default_tz: str) -> tuple[str, str]:
    """
    Render a time + timezone selector row inside a form.
    default_tz drives the pre-selected timezone index.
    Returns (time_str "HH:MM", tz_name).
    """
    tc, tzc = st.columns([1, 2])
    with tc:
        time_opts = time_options(15)
        default_t = "00:00"
        t_idx = time_opts.index(default_t) if default_t in time_opts else 0
        sel_time = st.selectbox(
            "Time (local) *",
            time_opts,
            index=t_idx,
            key=f"time_{form_key}",
        )
    with tzc:
        tz_idx = TIMEZONES.index(default_tz) if default_tz in TIMEZONES else 0
        sel_tz = st.selectbox(
            "Timezone *",
            TIMEZONES,
            index=tz_idx,
            key=f"tz_{form_key}",
            help="All times are stored in UTC. Select the timezone for this input.",
        )
    return sel_time, sel_tz


# ─────────────────────────────────────────────────────────────
#  Tournament / Series Tab
# ─────────────────────────────────────────────────────────────

def _tab_tournament(ev_df) -> None:
    st.markdown('<div class="card-title">ADD TOURNAMENT / SERIES</div>', unsafe_allow_html=True)

    leagues_df = load_leagues()
    league_options: dict[str, int | None] = {"(None)": None}
    if (
        not leagues_df.empty
        and "league_name" in leagues_df.columns
        and "id" in leagues_df.columns
    ):
        for _, r in leagues_df.iterrows():
            league_options[str(r["league_name"])] = int(r["id"])

    with st.form("add_event_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ev_name     = st.text_input("Event Name *", placeholder="ICC T20 World Cup 2026")
            ev_type     = st.selectbox("Type *", ["tournament", "series"])
            ev_category = st.selectbox("Category *", ["International", "Domestic", "League"])
            ev_league   = st.selectbox("League", list(league_options.keys()))
        with c2:
            ev_country  = st.text_input("Country / Host *", placeholder="India")
            ev_timezone = st.selectbox("Event Timezone *", TIMEZONES)
            ev_gender   = st.selectbox("Gender *", ["Male", "Female", "Mixed"])
            ev_format   = st.selectbox(
                "Format *", ["T20I", "ODI", "Test", "The Hundred","T20","T10","List-A","First-Class" ,"Mixed", "Other"]
            )
            

        c3, c4 = st.columns(2)
        with c3:
            ev_start = st.date_input("Start Date *", value=date.today())
        with c4:
            ev_end = st.date_input("End Date *", value=date.today())

        ev_notes  = st.text_area("Notes", placeholder="Optional details…")
        submitted = st.form_submit_button("Add Event", use_container_width=True)

    if submitted:
        errs = []
        if not ev_name.strip():    errs.append("Event name required.")
        if not ev_country.strip(): errs.append("Country required.")
        if ev_start > ev_end:      errs.append("Start must be before End.")
        if errs:
            for e in errs:
                st.error(e)
            return

        u = get_supabase_user()
        ok, msg = add_event(
            ev_name.strip(), ev_type, ev_category, ev_format,
            ev_start, ev_end, ev_country.strip(), ev_gender,
            ev_notes.strip(),
            user_id   = u.id if u else None,
            league_id = league_options[ev_league],
            timezone  = ev_timezone,
        )
        if ok:
            st.success(msg)
            log_activity(
                u.id if u else None, current_email(),
                "create", "event", details={"name": ev_name},
            )
        else:
            st.error(msg)


    if not ev_df.empty:
        st.markdown('<br><div class="card-title">EXISTING EVENTS</div>', unsafe_allow_html=True)
        display_cols = [
            c for c in
            ["event_name", "event_type", "category", "format",
             "start_date", "end_date", "country", "gender", "timezone"]
            if c in ev_df.columns
        ]
        disp = ev_df[display_cols].copy()
        if "start_date" in disp.columns:
            disp["start_date"] = disp["start_date"].dt.date
        if "end_date" in disp.columns:
            disp["end_date"] = disp["end_date"].dt.date
        disp.columns = [c.replace("_", " ").title() for c in display_cols]
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
#  Matches Tab
# ─────────────────────────────────────────────────────────────

def _tab_matches(ev_df) -> None:
    st.markdown('<div class="card-title">ADD MATCH</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="alert-box alert-info" style="margin-bottom:.8rem;">
        <div class="icon">ℹ</div>
        <div class="body" style="font-size:.82rem;">
            Select a <b>date, time and timezone</b>. The match will be stored in UTC
            and displayed in each user's own timezone.
        </div>
    </div>""", unsafe_allow_html=True)

    user_tz = _get_user_tz()
     # Single load; passed to helpers — no repeated DB calls.

    # ── Step 1: Event selection (outside form for live team updates) ──
    ev_id, ev_name = _event_search_select(ev_df, "match")

    # ── Step 2: Venue (outside form so it can feed timezone resolution) ──
    venue = st.text_input(
        "Venue", placeholder="Eden Gardens, Kolkata", key="match_venue"
    ).strip()

    # ── Step 3: Resolve timezone via single authoritative function ──
    resolved_tz = _resolve_event_tz(ev_df, ev_id, venue)
    st.caption(f"Timezone auto-selected ({resolved_tz}) based on event/location")

    # ── Step 4: Load teams for selected event ──
    team_ids: dict[str, int] = {}
    if ev_id is not None:
        teams_df = load_teams()
        if (
            not teams_df.empty
            and "event_id"   in teams_df.columns
            and "team_name"  in teams_df.columns
            and "id"         in teams_df.columns
            
        ):
            ev_teams = teams_df[teams_df["event_id"] == ev_id]
            
            if not ev_teams.empty:
                team_ids = {
                    str(r["team_name"]): int(r["id"])
                    for _, r in ev_teams.iterrows()
                }
    teams = list(team_ids.keys())

    # ── Step 5: Form ──
    with st.form("add_match_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            match_name = st.text_input(
                "Match Name / Label *", placeholder="Match 1 — India vs Pakistan"
            )
            match_date = st.date_input("Match Date *", value=date.today())
            sel_time, sel_tz = _time_tz_row("match", resolved_tz)
        with c2:
            notes = st.text_area("Notes", height=68)

        t1 = t2 = "—"
        if ev_id is not None:
            if teams:
                tc1, tc2 = st.columns(2)
                with tc1:
                    t1 = st.selectbox("Team 1", ["—"] + teams, key="m_t1")
                with tc2:
                    t2 = st.selectbox("Team 2", ["—"] + teams, key="m_t2")
            else:
                st.info("No teams loaded for this event yet. Add teams first.")

        submitted = st.form_submit_button("Add Match", use_container_width=True)

    # ── Step 6: Submit handling — validate first, exit early on error ──
    if submitted:
        if not match_name.strip():
            st.error("Match name is required.")
            return
        if not validate_time_str(sel_time):
            st.error("Invalid time format.")
            return

        t1_id = team_ids.get(t1) if t1 != "—" else None
        t2_id = team_ids.get(t2) if t2 != "—" else None
        ok, msg = add_match(
            event_id   = ev_id,
            match_name = match_name.strip(),
            match_date = match_date,
            team1_id   = t1_id,
            team2_id   = t2_id,
            venue      = venue,
            notes      = notes.strip(),
            match_time = sel_time,
            tz_name    = sel_tz,
        )
        if ok:
            st.success(msg)
            u = get_supabase_user()
            log_activity(
                u.id if u else None, current_email(), "create", "match",
                entity_id = ev_id,
                details   = {
                    "event":    ev_name or "standalone",
                    "datetime": f"{match_date} {sel_time} {sel_tz}",
                },
            )
        else:
            st.error(msg)

    # ── Step 7: Existing matches ──
    ma_df = load_matches(event_id=ev_id) if ev_id else pd.DataFrame()
    if not ma_df.empty:
        required_cols = ["match_name", "match_date", "match_datetime", "venue"]
        if required_cols.issubset(ma_df.columns):
            st.markdown('<br><div class="card-title">MATCHES</div>', unsafe_allow_html=True)
            disp = ma_df[required_cols].copy()
            disp["match_date"] = disp["match_date"].dt.date
            disp[f"Time ({user_tz})"] = disp["match_datetime"].apply(
                lambda dt: format_display(dt, user_tz, "%H:%M") if dt is not None else "—"
            )
            disp = disp.drop(columns=["match_datetime"])
            disp.columns = ["Match", "Date", "Venue", f"Time ({user_tz})"]
            st.dataframe(disp, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
#  Registration Tab
# ─────────────────────────────────────────────────────────────

def _tab_registration(ev_df) -> None:
    st.markdown('<div class="card-title">ADD REGISTRATION WINDOW</div>', unsafe_allow_html=True)

      # Single load; passed to selector helper.

    # ── Step 1: Event selection (outside form for consistency) ──
    ev_id, ev_name = _event_search_select(ev_df, "reg")

    # ── Step 2: Form ──
    with st.form("add_reg_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            reg_start = st.date_input("Registration Opens *", value=date.today())
        with c2:
            reg_dead = st.date_input("Deadline *", value=date.today())
        notes     = st.text_area("Notes", height=68)
        submitted = st.form_submit_button("Add Registration Window", use_container_width=True)

    # ── Step 3: Submit handling — validate first, exit early on error ──
    if submitted:
        if reg_start > reg_dead:
            st.error("Deadline must be after start.")
            return

        u = get_supabase_user()
        ok, msg = add_registration(
            ev_id, reg_start, reg_dead, notes.strip(),
            user_id=u.id if u else None,
        )
        if ok:
            st.success(msg)
            log_activity(
                u.id if u else None, current_email(),
                "create", "registration",
                entity_id = ev_id,
                details   = {"event": ev_name or "standalone"},
            )
        else:
            st.error(msg)

    # ── Step 4: Existing registration windows ──
    reg_df = load_registrations()
    if not reg_df.empty:
        show_df = reg_df.copy()
        if ev_id and "event_id" in show_df.columns:
            show_df = show_df[show_df["event_id"] == ev_id]
        if not show_df.empty:
            st.markdown('<br><div class="card-title">EXISTING WINDOWS</div>', unsafe_allow_html=True)
            cols = [c for c in ["start_date", "deadline", "notes"] if c in show_df.columns]
            d = show_df[cols].copy()
            if "start_date" in d.columns:
                d["start_date"] = d["start_date"].dt.date
            if "deadline" in d.columns:
                d["deadline"] = d["deadline"].dt.date
            d.columns = [c.replace("_", " ").title() for c in cols]
            st.dataframe(d, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
#  Auctions Tab
# ─────────────────────────────────────────────────────────────

def _tab_auction(ev_df) -> None:
    st.markdown('<div class="card-title">ADD AUCTION</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="alert-box alert-info" style="margin-bottom:.8rem;">
        <div class="icon">ℹ</div>
        <div class="body" style="font-size:.82rem;">
            Auctions can be linked to an existing event or created standalone.
            All times are stored in UTC and converted to each user's timezone on display.
        </div>
    </div>""", unsafe_allow_html=True)

    user_tz = _get_user_tz()
      # Single load; passed to helpers — no repeated DB calls.

    # ── Step 1: Event selection (outside form to feed timezone resolution) ──
    ev_id, ev_name = _event_search_select(ev_df, "auction")

    # ── Step 2: Location (outside form so it can feed timezone resolution) ──
    location = st.text_input(
        "Location", placeholder="e.g. Mumbai, India", key="auction_location"
    ).strip()

    # ── Step 3: Resolve timezone via single authoritative function ──
    resolved_tz = _resolve_event_tz(ev_df, ev_id, location)
    st.caption(f"Timezone: {resolved_tz} (auto-detected, editable)")

    # ── Step 4: Form ──
    with st.form("add_auction_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            auction_name = st.text_input(
                "Auction Name *",
                placeholder="e.g. IPL 2026 Player Auction",
            )
            auc_date = st.date_input("Auction Date *", value=date.today())
        with c2:
            notes = st.text_area("Notes", height=68)

        sel_time, sel_tz = _time_tz_row("auction", resolved_tz)
        submitted = st.form_submit_button("Add Auction", use_container_width=True)

    # ── Step 5: Submit handling — validate first, exit early on error ──
    if submitted:
        if not auction_name.strip():
            st.error("Auction name is required.")
            return
        if not validate_time_str(sel_time):
            st.error("Invalid time format.")
            return

        ok, msg = add_auction(
            event_id     = ev_id,
            auction_name = auction_name.strip(),
            auction_date = auc_date,
            location     = location,
            notes        = notes.strip(),
            auction_time = sel_time,
            tz_name      = sel_tz,
        )
        if ok:
            st.success(msg)
            u = get_supabase_user()
            log_activity(
                u.id if u else None, current_email(),
                "create", "auction",
                entity_id = ev_id,
                details   = {
                    "event":    ev_name or "standalone",
                    "datetime": f"{auc_date} {sel_time} {sel_tz}",
                },
            )
        else:
            st.error(msg)

    # ── Step 6: Existing auctions ──
    au_df = load_auctions()
    if not au_df.empty:
        show_df = au_df.copy()
        if ev_id and "event_id" in show_df.columns:
            show_df = show_df[show_df["event_id"] == ev_id]
        if not show_df.empty:
            required_cols = ["auction_name", "auction_date", "auction_datetime", "location"]
            if required_cols.issubset(show_df.columns):
                st.markdown('<br><div class="card-title">EXISTING AUCTIONS</div>', unsafe_allow_html=True)
                disp = show_df[list(required_cols)].copy()
                disp["auction_date"] = disp["auction_date"].dt.date
                disp[f"Time ({user_tz})"] = disp["auction_datetime"].apply(
                    lambda dt: format_display(dt, user_tz, "%H:%M") if dt is not None else "—"
                )
                disp = disp.drop(columns=["auction_datetime"])
                disp.columns = ["Auction", "Date", "Location", f"Time ({user_tz})"]
                st.dataframe(disp, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
#  Leagues Tab
# ─────────────────────────────────────────────────────────────

def _tab_leagues() -> None:
    st.markdown('<div class="card-title">ADD LEAGUE</div>', unsafe_allow_html=True)

    with st.form("add_league_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            lg_name = st.text_input("League Name *", placeholder="e.g. IPL")
        with c2:
            lg_country = st.text_input("Country", placeholder="e.g. India")
        submitted = st.form_submit_button("Add League", use_container_width=True)

    if submitted:
        if not lg_name.strip():
            st.error("League name is required.")
            return
        ok, msg = add_league(lg_name.strip(), lg_country.strip())
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    leagues_df = load_leagues()
    if not leagues_df.empty:
        st.markdown('<br><div class="card-title">EXISTING LEAGUES</div>', unsafe_allow_html=True)
        display_cols = [c for c in ["league_name", "country"] if c in leagues_df.columns]
        disp = leagues_df[display_cols].copy()
        disp.columns = [c.replace("_", " ").title() for c in display_cols]
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
#  Render
# ─────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>EVENT MANAGER</h1>
        <p>Tournaments · Matches · Registrations · Auctions · Leagues</p></div>
    </div>""", unsafe_allow_html=True)

    if not can_edit():
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">🔒</div>
            <div class="body"><div class="title">View-Only Access</div>
            Contact an admin to request edit access.</div>
        </div>""", unsafe_allow_html=True)
        return
    ev_df = load_events()
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Tournament / Series", "Matches", "Registration", "Auctions", "Leagues"
    ])
    with tab1: _tab_tournament(ev_df)
    with tab2: _tab_matches(ev_df)
    with tab3: _tab_registration(ev_df)
    with tab4: _tab_auction(ev_df)
    with tab5: _tab_leagues()