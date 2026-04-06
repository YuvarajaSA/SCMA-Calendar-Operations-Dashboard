# pages/profile.py
# ══════════════════════════════════════════════════════════════
#  Profile Setup & Approval Status Screen
#
#  Shown when a user has authenticated via Supabase Auth but
#  either has no profile yet, or their profile is pending/rejected.
#
#  ROUTES (called from app.py)
#  ───────────────────────────
#  render_setup()    → user has no profile → show name/phone/location form
#  render_pending()  → profile exists, status == "pending"
#  render_rejected() → profile exists, status == "rejected"
# ══════════════════════════════════════════════════════════════

import streamlit as st
from db.auth import get_supabase_user, current_email, logout
from db.operations import create_profile, update_profile_details


def _page_styles() -> None:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display:none !important; }
    .main .block-container {
        padding-top:2rem !important; max-width:680px !important;
    }
    </style>""", unsafe_allow_html=True)


def _logout_btn() -> None:
    if st.button("🚪  Log Out", key="prof_logout"):
        logout()
        st.rerun()


# ── 1. Profile setup form ─────────────────────────────────────

def render_setup() -> None:
    """
    First time a user lands here after OAuth/signup.
    They fill in name, phone, location → creates profile with status=pending.
    """
    _page_styles()

    user  = get_supabase_user()
    email = current_email()

    st.markdown("""
    <div style="text-align:center;margin-bottom:2rem;">
        <div style="font-size:2.5rem;margin-bottom:.5rem;">👋</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;
                    color:#f0b429;letter-spacing:.06em;">Welcome!</div>
        <div style="font-size:.88rem;color:#8b949e;margin-top:.4rem;">
            You're signed in. Complete your profile to request access.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#1c2128;border:1px solid #30363d;border-radius:10px;
                padding:.7rem 1rem;margin-bottom:1.5rem;font-size:.84rem;">
        <span style="color:#8b949e;">Signed in as&nbsp;</span>
        <b style="color:#e6edf3;">{email}</b>
    </div>
    """, unsafe_allow_html=True)

    with st.form("profile_form"):
        st.markdown("**Full Name \\***")
        name = st.text_input("name", placeholder="Jane Smith",
                             label_visibility="collapsed")
        st.markdown("**Phone**")
        phone = st.text_input("phone", placeholder="+1 234 567 8900",
                              label_visibility="collapsed")
        st.markdown("**Location / Office**")
        location = st.text_input("location", placeholder="London, UK",
                                 label_visibility="collapsed")

        submitted = st.form_submit_button(
            "📨  Submit Profile & Request Access",
            use_container_width=True,
        )

    if submitted:
        if not name.strip():
            st.error("Full name is required.")
            return

        ok, reason = create_profile(
            user_id  = user.id,
            email    = email,
            name     = name,
            phone    = phone,
            location = location,
        )

        if ok:
            # Force re-read of profile on next rerun
            st.session_state.pop("profile_checked", None)
            st.rerun()
        elif reason == "profile_exists":
            # Already created in another tab/session — just rerun
            st.session_state.pop("profile_checked", None)
            st.rerun()
        else:
            st.error(f"Could not save profile. {reason}")

    st.markdown("---")
    _logout_btn()


# ── 2. Pending screen ─────────────────────────────────────────

def render_pending() -> None:
    _page_styles()

    email = current_email()

    st.markdown(f"""
    <div style="text-align:center;padding:2rem 0;">
        <div style="font-size:3rem;margin-bottom:1rem;">⏳</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
                    color:#e3b341;letter-spacing:.06em;">Awaiting Approval</div>
        <div style="font-size:.88rem;color:#8b949e;margin-top:.8rem;
                    line-height:1.7;max-width:400px;margin-left:auto;margin-right:auto;">
            Your profile for <b style="color:#e6edf3;">{email}</b> has been submitted.<br>
            An administrator will review and approve your access.<br>
            You'll be able to use the dashboard once approved.
        </div>
    </div>
    <div style="background:rgba(227,179,65,.08);border:1px solid rgba(227,179,65,.25);
                border-radius:12px;padding:1.2rem;margin-top:1.5rem;font-size:.84rem;
                color:#e3b341;text-align:center;">
        💡 Already approved? Click the button below to refresh.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄  Check Status", use_container_width=True):
            # Clear cached profile so app.py re-fetches it
            st.session_state.pop("profile_checked", None)
            st.session_state.pop("user_status", None)
            st.rerun()
    with c2:
        _logout_btn()


# ── 3. Rejected screen ────────────────────────────────────────

def render_rejected() -> None:
    _page_styles()

    email = current_email()

    st.markdown(f"""
    <div style="text-align:center;padding:2rem 0;">
        <div style="font-size:3rem;margin-bottom:1rem;">⛔</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
                    color:#f85149;letter-spacing:.06em;">Access Denied</div>
        <div style="font-size:.88rem;color:#8b949e;margin-top:.8rem;
                    line-height:1.7;max-width:400px;margin-left:auto;margin-right:auto;">
            The access request for <b style="color:#e6edf3;">{email}</b> was not approved.<br>
            If you believe this is an error, contact your system administrator.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    _, c, _ = st.columns([2, 1, 2])
    with c:
        _logout_btn()
