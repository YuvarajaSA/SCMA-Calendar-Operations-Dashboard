# app.py  —  SCMA Calendar Dashboard (Sophie Claire M Agency)
import streamlit as st

st.set_page_config(
    page_title="SCMA Calendar",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config.styles import inject
inject()

from db.auth import (
    handle_oauth_callback, hydrate_session,
    is_supabase_authenticated, is_logged_in,
    get_supabase_user, current_email, current_name,
    get_role, can_edit, is_admin, logout,
)

handle_oauth_callback()
hydrate_session()

if not is_supabase_authenticated():
    from views.login import render as login_page
    login_page()
    st.stop()

from db.operations import get_profile

user = get_supabase_user()

if not st.session_state.get("profile_checked"):
    profile = get_profile(user.id)
    st.session_state["profile_checked"] = True
    st.session_state["_cached_profile"] = profile
    if profile:
        st.session_state["user_name"]     = profile.get("name", "")
        st.session_state["user_role"]     = profile.get("role", "viewer")
        st.session_state["user_status"]   = profile.get("status", "pending")
        st.session_state["authenticated"] = (profile.get("status") == "approved")

profile = st.session_state.get("_cached_profile")
status  = st.session_state.get("user_status", "")

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

# ── Page imports ──────────────────────────────────────────────
from views import (
    dashboard, calendar_view, search,
    add_squad, conflicts, availability, timeline,
    event_manager, csv_upload, profile_settings, admin,
)
from views.add_team import render as add_team_render
from db.operations import load_events, load_teams, load_squad
from utils.conflicts import detect_event_overlaps, detect_player_conflicts
import streamlit as st

# ── Navigation structure ──────────────────────────────────────
NAV_MAIN = [
    ("Calendar",     "", calendar_view.render),
    ("Dashboard",    "", dashboard.render),
    ("Search",       "", search.render),
    ("Conflicts",    "", conflicts.render),
    ("Availability", "", availability.render),
    ("Timeline",     "", timeline.render),
]
NAV_EDIT = [
    ("Event Manager","", event_manager.render),
    ("Add Team",     "", add_team_render),
    ("Add Squad",    "", add_squad.render),
    ("CSV Upload",   "", csv_upload.render),
]
NAV_ADMIN = [
    ("Admin",        "🛡", admin.render),
]
NAV_BOTTOM = [
    ("My Profile",   "👤", profile_settings.render),
]

# ── Session-state routing ─────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Calendar"


def _nav_btn(label: str, icon: str) -> None:
    active = st.session_state["current_page"] == label

    btn_style = (
        "background:rgba(240,180,41,.14);color:#f0b429;border:1px solid rgba(240,180,41,.3);"
        if active else
        "background:transparent;color:#c9d1d9;border:1px solid transparent;"
    )

    text = f"{icon}  {label}" if icon else label

    if st.button(
        text,
        key=f"nav_{label}",
        use_container_width=True,
        help=label,
    ):
        st.session_state["current_page"] = label
        st.rerun() 

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    # Logo (from Supabase Storage public bucket "assets")
    logo_url = st.secrets.get("supabase", {}).get("logo_url", "")
    if logo_url:
        try:
            st.image(logo_url, width=170)
        except Exception:
            pass

    # Brand text
    st.markdown("""
    <div style="padding:.5rem 0 .8rem; text-align:center;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;
                    color:#f0b429;letter-spacing:.06em;line-height:1.1;">
            SCMA CALENDAR
        </div>
        <div style="font-size:.65rem;color:#8b949e;letter-spacing:.14em;margin-top:.2rem;">
            SOPHIE CLAIRE M AGENCY
        </div>
    </div>""", unsafe_allow_html=True)

    # User card
    role      = get_role()
    role_cls  = {"admin":"role-admin","editor":"role-editor","viewer":"role-viewer"}.get(role, "role-viewer")
    role_icon = {"admin":"👑","editor":"✏️","viewer":"👁"}.get(role, "👁")

    st.markdown(f"""
    <div style="background:#1c2128;border:1px solid #30363d;border-radius:10px;
                padding:.65rem .85rem;margin-bottom:.8rem;">
        <div style="font-size:.82rem;font-weight:600;color:#e6edf3;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            {current_name() or "—"}
        </div>
        <div style="font-size:.68rem;color:#8b949e;white-space:nowrap;
                    overflow:hidden;text-overflow:ellipsis;margin-bottom:.3rem;">
            {current_email()}
        </div>
        <span class="role-pill {role_cls}">{role_icon} {role}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:.58rem;font-weight:800;letter-spacing:.14em;
                text-transform:uppercase;color:#8b949e;margin-bottom:.4rem;">
        Navigation
    </div>""", unsafe_allow_html=True)

    # Main nav buttons
    for label, icon, _ in NAV_MAIN:
        _nav_btn(label, icon)

    if can_edit():
        st.markdown("""
        <div style="font-size:.56rem;font-weight:800;letter-spacing:.14em;
                    text-transform:uppercase;color:#8b949e;
                    margin:.6rem 0 .3rem;">
            Data Entry
        </div>""", unsafe_allow_html=True)
        for label, icon, _ in NAV_EDIT:
            _nav_btn(label, icon)

    if is_admin():
        st.markdown("""
        <div style="font-size:.56rem;font-weight:800;letter-spacing:.14em;
                    text-transform:uppercase;color:#8b949e;
                    margin:.6rem 0 .3rem;">
            Admin
        </div>""", unsafe_allow_html=True)
        for label, icon, _ in NAV_ADMIN:
            _nav_btn(label, icon)

    # Quick stats
    st.markdown("---")
    events_df = load_events()
    teams_df  = load_teams()
    squad_df  = load_squad()

    total_events  = len(events_df)
    total_teams   = teams_df["team_name"].nunique() if not teams_df.empty else 0
    total_players = squad_df["player_name"].nunique() if not squad_df.empty else 0
    eo = detect_event_overlaps(events_df)
    pc = detect_player_conflicts(squad_df)

    stat_rows = "".join(
        f'<div style="background:#1c2128;border:1px solid #30363d;border-radius:7px;'
        f'padding:.38rem .75rem;display:flex;align-items:center;gap:.65rem;">'
        f'<span style="font-family:\'Bebas Neue\',sans-serif;font-size:1.2rem;'
        f'color:{c};min-width:1.5rem;text-align:right;">{v}</span>'
        f'<span style="font-size:.62rem;font-weight:700;letter-spacing:.06em;'
        f'text-transform:uppercase;color:#8b949e;">{l}</span></div>'
        for v, l, c in [
            (total_events,  "Events",          "#f0b429"),
            (total_teams,   "Teams",            "#3fb950"),
            (total_players, "Players",          "#58a6ff"),
            (len(eo), "Conflicts",        "#f85149" if eo else "#3fb950"),
        ]
    )
    st.markdown(f"""
    <div style="font-size:.55rem;font-weight:800;letter-spacing:.12em;
                text-transform:uppercase;color:#8b949e;margin-bottom:.45rem;">
        Quick Stats
    </div>
    <div style="display:flex;flex-direction:column;gap:.28rem;">
        {stat_rows}
    </div>""", unsafe_allow_html=True)

    # Bottom nav: Profile + Logout
    st.markdown("---")
    for label, icon, _ in NAV_BOTTOM:
        _nav_btn(label, icon)

    if st.button("Log Out", use_container_width=True, key="logout_btn"):
        logout(); st.rerun()

    st.markdown("""
    <div style="font-size:.57rem;color:#8b949e;margin-top:.5rem;
                line-height:1.7;text-align:center;">
        SCMA · Supabase + Streamlit · Internal use only
    </div>""", unsafe_allow_html=True)


# ── Route to active page ──────────────────────────────────────
current = st.session_state.get("current_page", "Calendar")

ALL_ROUTES: dict = {}
for label, _, fn in NAV_MAIN + NAV_EDIT + NAV_ADMIN + NAV_BOTTOM:
    ALL_ROUTES[label] = fn

if current in ALL_ROUTES:
    ALL_ROUTES[current]()
else:
    calendar_view.render()
