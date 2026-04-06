# app.py  —  SCMA Calendar Dashboard (Sophie Agency)
# ══════════════════════════════════════════════════════════════
#  AUTH ORDER (non-negotiable):
#    1. handle_oauth_callback()  → no-op stub (OAuth removed)
#    2. hydrate_session()        → restore Supabase user on rerun
#    3. Profile gate             → pending/rejected/setup screens
#    4. Dashboard                → calendar is DEFAULT page
# ══════════════════════════════════════════════════════════════

import streamlit as st

st.set_page_config(
    page_title = "SCMA Calendar",
    page_icon  = "🏏",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

from config.styles import inject
inject()

from db.auth import (
    handle_oauth_callback, hydrate_session,
    is_supabase_authenticated, is_logged_in,
    get_supabase_user, current_email, current_name,
    get_role, can_edit, is_admin, logout,
)

# ── Auth steps ────────────────────────────────────────────────
handle_oauth_callback()   # no-op — kept so import chain is stable
hydrate_session()

# ── No Supabase user → login ──────────────────────────────────
if not is_supabase_authenticated():
    from views.login import render as login_page
    login_page()
    st.stop()

# ── Supabase user → check profile ────────────────────────────
from db.operations import get_profile

user = get_supabase_user()

if not st.session_state.get("profile_checked"):
    profile = get_profile(user.id)
    st.session_state["profile_checked"]  = True
    st.session_state["_cached_profile"]  = profile
    if profile:
        st.session_state["user_name"]      = profile.get("name","")
        st.session_state["user_role"]      = profile.get("role","viewer")
        st.session_state["user_status"]    = profile.get("status","pending")
        st.session_state["authenticated"]  = (profile.get("status") == "approved")

profile = st.session_state.get("_cached_profile")
status  = st.session_state.get("user_status","")

if profile is None:
    from views.profile import render_setup
    render_setup(); st.stop()

if status == "pending":
    from views.profile import render_pending
    render_pending(); st.stop()

if status == "rejected":
    from views.profile import render_rejected
    render_rejected(); st.stop()

if not is_logged_in():
    st.error("Access check failed. Please log out and try again.")
    if st.button("Log Out"):
        logout(); st.rerun()
    st.stop()

# ── Approved — load pages ─────────────────────────────────────
from views import (
    dashboard, calendar_view, search,
    add_squad, conflicts, availability, timeline,
    event_manager, csv_upload, profile_settings, admin,
)
from db.operations import load_events, load_teams, load_squad
from utils.conflicts import detect_event_overlaps, detect_player_conflicts

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 1.2rem;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
                    color:#f0b429;letter-spacing:.06em;line-height:1;">
            SCMA CALENDAR
        </div>
        <div style="font-size:.72rem;color:#8b949e;letter-spacing:.12em;margin-top:.15rem;">
            SOPHIE AGENCY
        </div>
    </div>""", unsafe_allow_html=True)

    # User card
    role      = get_role()
    role_cls  = {"admin":"role-admin","editor":"role-editor","viewer":"role-viewer"}.get(role,"role-viewer")
    role_icon = {"admin":"👑","editor":"✏️","viewer":"👁"}.get(role,"👁")

    st.markdown(f"""
    <div style="background:#1c2128;border:1px solid #30363d;border-radius:10px;
                padding:.7rem .9rem;margin-bottom:1rem;">
        <div style="font-size:.84rem;font-weight:600;color:#e6edf3;
                    margin-bottom:.12rem;">{current_name() or "—"}</div>
        <div style="font-size:.7rem;color:#8b949e;overflow:hidden;
                    text-overflow:ellipsis;white-space:nowrap;
                    margin-bottom:.32rem;">{current_email()}</div>
        <span class="role-pill {role_cls}">{role_icon} {role}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Navigation — Calendar is index 0 (default)
    nav_options = [
        "Calendar",
        "Dashboard",
        "Search",
        "Conflicts",
        "Availability",
        "Timeline",
        "My Profile",
    ]
    if can_edit():
        nav_options += ["Event Manager", "Add Team", "Add Squad", "CSV Upload"]
    if is_admin():
        nav_options += ["Admin"]

    page = st.radio("NAVIGATE", nav_options)

    st.markdown("---")

    # Quick stats
    events_df = load_events()
    teams_df  = load_teams()
    squad_df  = load_squad()

    total_events  = len(events_df)
    total_teams   = teams_df["team_name"].nunique() if not teams_df.empty else 0
    total_players = squad_df["player_name"].nunique() if not squad_df.empty else 0
    eo = detect_event_overlaps(events_df)
    pc = detect_player_conflicts(squad_df)

    stat_rows = "".join(
        f'<div style="background:#1c2128;border:1px solid #30363d;border-radius:8px;'
        f'padding:.42rem .82rem;display:flex;align-items:center;gap:.7rem;">'
        f'<span style="font-family:\'Bebas Neue\',sans-serif;font-size:1.3rem;'
        f'color:{c};min-width:1.6rem;text-align:right;">{v}</span>'
        f'<span style="font-size:.66rem;font-weight:700;letter-spacing:.07em;'
        f'text-transform:uppercase;color:#8b949e;">{l}</span></div>'
        for v, l, c in [
            (total_events,  "Events",          "#f0b429"),
            (total_teams,   "Teams",            "#3fb950"),
            (total_players, "Players",          "#58a6ff"),
            (len(eo), "Date Conflicts",   "#f85149" if eo else "#3fb950"),
            (len(pc), "Player Conflicts", "#f85149" if pc else "#3fb950"),
        ]
    )
    st.markdown(f"""
    <div style="font-size:.58rem;font-weight:800;letter-spacing:.14em;
                text-transform:uppercase;color:#8b949e;margin-bottom:.55rem;">
        QUICK STATS
    </div>
    <div style="display:flex;flex-direction:column;gap:.32rem;">
        {stat_rows}
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Log Out", use_container_width=True, key="logout_btn"):
        logout(); st.rerun()

    st.markdown("""
    <div style="font-size:.6rem;color:#8b949e;margin-top:.6rem;
                line-height:1.7;text-align:center;">
        SCMA · Powered by Supabase + Streamlit<br>
        Internal use only
    </div>""", unsafe_allow_html=True)


# ── Page router ───────────────────────────────────────────────
from views.add_team import render as add_team_render

ROUTES = {
    "Calendar":     calendar_view.render,
    "Dashboard":    dashboard.render,
    "Search":       search.render,
    "Conflicts":    conflicts.render,
    "Availability": availability.render,
    "Timeline":     timeline.render,
    "My Profile":   profile_settings.render,
    "Event Manager":event_manager.render,
    "Add Team":     add_team_render,
    "Add Squad":    add_squad.render,
    "CSV Upload":   csv_upload.render,
    "Admin":        admin.render,
}

if page in ROUTES:
    ROUTES[page]()
