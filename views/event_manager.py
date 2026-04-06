# pages/event_manager.py  —  SCMA Event & Match Management
from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import date

from db.auth import can_edit, get_supabase_user, current_email
from db.operations import (
    load_events, load_teams, event_names, teams_for_event,
    add_event, load_leagues, add_league,
    add_match, load_matches,
    add_registration, load_registrations,
    add_auction, load_auctions,
    log_activity,
)


def _event_search_select(key: str) -> tuple[int | None, str]:
    """Search-box for event selection. Returns (event_id, event_name)."""
    ev_df = load_events()
    if ev_df.empty:
        st.warning("No events found. Add a Tournament/Series first.")
        return None, ""

    search = st.text_input("Search event", placeholder="Type to filter…", key=f"es_{key}")
    names  = ev_df["event_name"].tolist()
    if search:
        names = [n for n in names if search.lower() in n.lower()]

    if not names:
        st.warning("No matches. Try a different search term.")
        return None, ""

    sel_name = st.radio("Select", names[:15], key=f"er_{key}", label_visibility="collapsed")
    row = ev_df[ev_df["event_name"] == sel_name]
    if row.empty:
        return None, ""
    ev_id = int(row.iloc[0]["id"]) if "id" in row.columns else None
    return ev_id, sel_name


def _tab_tournament() -> None:
    st.markdown('<div class="card-title">ADD TOURNAMENT / SERIES</div>', unsafe_allow_html=True)

    leagues_df = load_leagues()
    league_options = {"(None)": None}
    if not leagues_df.empty:
        league_options.update({r["league_name"]: int(r["id"]) for _, r in leagues_df.iterrows()})

    with st.form("add_event_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ev_name     = st.text_input("Event Name *", placeholder="ICC T20 World Cup 2026")
            ev_type     = st.selectbox("Type *", ["tournament","series"])
            ev_category = st.selectbox("Category *", ["International","Domestic","League"])
            ev_league   = st.selectbox("League", list(league_options.keys()))
        with c2:
            ev_country  = st.text_input("Country / Host *", placeholder="India")
            ev_gender   = st.selectbox("Gender *", ["Male","Female","Mixed"])
            ev_format   = st.selectbox("Format *", ["T20","ODI","Test","The Hundred","Mixed","Other"])

        c3, c4 = st.columns(2)
        with c3:
            ev_start = st.date_input("Start Date *", value=date.today())
        with c4:
            ev_end   = st.date_input("End Date *",   value=date.today())
        ev_notes = st.text_area("Notes", placeholder="Optional details…")
        submitted = st.form_submit_button("Add Event", use_container_width=True)

    if submitted:
        errs = []
        if not ev_name.strip():   errs.append("Event name required.")
        if not ev_country.strip(): errs.append("Country required.")
        if ev_start > ev_end:     errs.append("Start must be before End.")
        if errs:
            for e in errs: st.error(e)
        else:
            u = get_supabase_user()
            ok, msg = add_event(
                ev_name.strip(), ev_type, ev_category, ev_format,
                ev_start, ev_end, ev_country.strip(), ev_gender,
                ev_notes.strip(), user_id=u.id if u else None,
            )
            if ok:
                st.success(msg)
                log_activity(u.id if u else None, current_email(), "create", "event", details={"name": ev_name})
            else:
                st.error(msg)

    # ── Quick add league ──────────────────────────────────────
    with st.expander("Add a new League"):
        with st.form("add_league_form", clear_on_submit=True):
            lg_name    = st.text_input("League Name", placeholder="IPL")
            lg_country = st.text_input("Country",     placeholder="India")
            if st.form_submit_button("Add League"):
                if lg_name.strip():
                    ok, msg = add_league(lg_name.strip(), lg_country.strip())
                    if ok: st.success(msg)
                    else:  st.error(msg)

    # ── Existing events ───────────────────────────────────────
    ev_df = load_events()
    if not ev_df.empty:
        st.markdown('<br><div class="card-title">EXISTING EVENTS</div>', unsafe_allow_html=True)
        disp = ev_df[["event_name","event_type","category","format","start_date","end_date","country","gender"]].copy()
        disp["start_date"] = disp["start_date"].dt.date
        disp["end_date"]   = disp["end_date"].dt.date
        disp.columns = ["Event","Type","Category","Format","Start","End","Country","Gender"]
        st.dataframe(disp, use_container_width=True, hide_index=True)


def _tab_matches() -> None:
    st.markdown('<div class="card-title">ADD MATCH</div>', unsafe_allow_html=True)

    ev_id, ev_name = _event_search_select("match")
    if ev_id is None:
        return

    # Teams for this event
    teams  = teams_for_event(ev_name)
    teams_df = load_teams()
    team_ids: dict[str, int] = {}
    if not teams_df.empty and "event_name" in teams_df.columns:
        ev_teams = teams_df[teams_df["event_name"] == ev_name]
        if not ev_teams.empty and "id" in ev_teams.columns:
            team_ids = {r["team_name"]: int(r["id"]) for _, r in ev_teams.iterrows()}

    with st.form("add_match_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            match_name = st.text_input("Match Name / Label", placeholder="Match 1")
            match_date = st.date_input("Match Date *", value=date.today())
        with c2:
            venue = st.text_input("Venue", placeholder="Eden Gardens")
            notes = st.text_area("Notes", height=68)

        if teams:
            t1 = st.selectbox("Team 1", ["—"]+teams, key="m_t1")
            t2 = st.selectbox("Team 2", ["—"]+teams, key="m_t2")
        else:
            st.info("No teams for this event yet. Add teams first.")
            t1 = t2 = "—"

        submitted = st.form_submit_button("Add Match", use_container_width=True)

    if submitted:
        t1_id = team_ids.get(t1) if t1 != "—" else None
        t2_id = team_ids.get(t2) if t2 != "—" else None
        ok, msg = add_match(ev_id, match_name.strip() or f"{t1} vs {t2}",
                            match_date, t1_id, t2_id, venue.strip(), notes.strip())
        if ok:
            st.success(msg)
            u = get_supabase_user()
            log_activity(u.id if u else None, current_email(), "create", "match",
                         entity_id=ev_id, details={"event": ev_name})
        else:
            st.error(msg)

    # ── Existing matches ──────────────────────────────────────
    ma_df = load_matches(event_id=ev_id)
    if not ma_df.empty:
        st.markdown('<br><div class="card-title">MATCHES</div>', unsafe_allow_html=True)
        disp = ma_df[["match_name","match_date","venue"]].copy()
        disp["match_date"] = disp["match_date"].dt.date
        disp.columns = ["Match","Date","Venue"]
        st.dataframe(disp, use_container_width=True, hide_index=True)


def _tab_registration() -> None:
    st.markdown('<div class="card-title">ADD REGISTRATION WINDOW</div>', unsafe_allow_html=True)

    ev_id, ev_name = _event_search_select("reg")
    if ev_id is None:
        return

    with st.form("add_reg_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            reg_start = st.date_input("Registration Opens *", value=date.today())
        with c2:
            reg_dead  = st.date_input("Deadline *", value=date.today())
        notes = st.text_area("Notes", height=68)
        submitted = st.form_submit_button("Add Registration Window", use_container_width=True)

    if submitted:
        if reg_start > reg_dead:
            st.error("Deadline must be after start.")
        else:
            u  = get_supabase_user()
            ok, msg = add_registration(ev_id, reg_start, reg_dead, notes.strip(),
                                       user_id=u.id if u else None)
            if ok:
                st.success(msg)
                log_activity(u.id if u else None, current_email(), "create", "registration",
                             entity_id=ev_id, details={"event": ev_name})
            else:
                st.error(msg)

    reg_df = load_registrations()
    if not reg_df.empty and "event_id" in reg_df.columns:
        ev_regs = reg_df[reg_df["event_id"] == ev_id]
        if not ev_regs.empty:
            st.markdown('<br><div class="card-title">EXISTING WINDOWS</div>', unsafe_allow_html=True)
            d = ev_regs[["start_date","deadline","notes"]].copy()
            d["start_date"] = d["start_date"].dt.date
            d["deadline"]   = d["deadline"].dt.date
            d.columns = ["Opens","Deadline","Notes"]
            st.dataframe(d, use_container_width=True, hide_index=True)


def _tab_auction() -> None:
    st.markdown('<div class="card-title">ADD AUCTION</div>', unsafe_allow_html=True)

    ev_id, ev_name = _event_search_select("auction")
    if ev_id is None:
        return

    with st.form("add_auction_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            franchise = st.text_input("Franchise Name *", placeholder="Mumbai Indians")
            auc_date  = st.date_input("Auction Date *", value=date.today())
        with c2:
            location = st.text_input("Location", placeholder="Mumbai")
            notes    = st.text_area("Notes", height=68)
        submitted = st.form_submit_button("Add Auction", use_container_width=True)

    if submitted:
        if not franchise.strip():
            st.error("Franchise name required.")
        else:
            ok, msg = add_auction(ev_id, franchise.strip(), auc_date,
                                   location.strip(), notes.strip())
            if ok:
                st.success(msg)
                u = get_supabase_user()
                log_activity(u.id if u else None, current_email(), "create", "auction",
                             entity_id=ev_id, details={"event": ev_name})
            else:
                st.error(msg)

    au_df = load_auctions()
    if not au_df.empty and "event_id" in au_df.columns:
        ev_au = au_df[au_df["event_id"] == ev_id]
        if not ev_au.empty:
            st.markdown('<br><div class="card-title">EXISTING AUCTIONS</div>', unsafe_allow_html=True)
            d = ev_au[["franchise_name","auction_date","location"]].copy()
            d["auction_date"] = d["auction_date"].dt.date
            d.columns = ["Franchise","Date","Location"]
            st.dataframe(d, use_container_width=True, hide_index=True)


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>EVENT MANAGER</h1>
        <p>Tournaments · Matches · Registrations · Auctions</p></div>
    </div>""", unsafe_allow_html=True)

    if not can_edit():
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">🔒</div>
            <div class="body"><div class="title">View-Only Access</div>
            Contact an admin to request edit access.</div>
        </div>""", unsafe_allow_html=True)
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "Tournament / Series", "Matches", "Registration", "Auctions"
    ])
    with tab1: _tab_tournament()
    with tab2: _tab_matches()
    with tab3: _tab_registration()
    with tab4: _tab_auction()
