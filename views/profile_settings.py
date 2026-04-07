# pages/profile_settings.py  —  SCMA User Profile
# Phase 11: logout moved here, password reset via Forgot Password tab

import streamlit as st
from db.auth import get_supabase_user, current_email, current_name, logout
from db.operations import get_profile, update_profile_details

TIMEZONES = [
    "UTC","Europe/London","Europe/Paris","Europe/Berlin","Europe/Amsterdam",
    "Asia/Kolkata","Asia/Colombo","Asia/Dubai","Asia/Karachi","Asia/Dhaka",
    "Asia/Singapore","Asia/Tokyo","Australia/Sydney","Australia/Melbourne",
    "Pacific/Auckland","America/Guyana","America/Port_of_Spain","America/St_Lucia",
    "America/Barbados","America/New_York","America/Chicago",
    "America/Los_Angeles","America/Toronto","America/Sao_Paulo",
    "Africa/Johannesburg","Africa/Lagos","Africa/Nairobi",
]


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>MY PROFILE</h1>
        <p>Account details, timezone and session management</p></div>
    </div>""", unsafe_allow_html=True)

    user = get_supabase_user()
    if not user:
        st.error("Not authenticated.")
        return

    profile    = get_profile(user.id) or {}
    role       = st.session_state.get("user_role", "viewer")
    rc         = {"admin":"role-admin","editor":"role-editor","viewer":"role-viewer"}.get(role, "role-viewer")
    ri         = {"admin":"👑","editor":"✏","viewer":"👁"}.get(role, "👁")
    current_tz = profile.get("timezone", "UTC") or "UTC"

    # Profile card
    st.markdown(f"""
    <div class="card" style="display:flex;gap:1.4rem;align-items:center;
                flex-wrap:wrap;margin-bottom:1.5rem;">
        <div style="width:48px;height:48px;border-radius:50%;
                    background:rgba(240,180,41,.12);border:2px solid #f0b429;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.3rem;flex-shrink:0;">{ri}</div>
        <div>
            <div style="font-size:1.05rem;font-weight:700;color:#e6edf3;">
                {current_name() or profile.get("name","—")}
            </div>
            <div style="font-size:.8rem;color:#8b949e;">{current_email()}</div>
            <div style="margin-top:.35rem;">
                <span class="role-pill {rc}">{ri} {role}</span>
            </div>
        </div>
        <div style="margin-left:auto;font-size:.78rem;color:#8b949e;">
            Timezone: <b style="color:#e6edf3;">{current_tz}</b>
        </div>
    </div>""", unsafe_allow_html=True)

    # Edit form + security info side by side
    col_form, col_sec = st.columns([3, 2])

    with col_form:
        st.markdown('<div class="card-title">EDIT DETAILS</div>', unsafe_allow_html=True)
        tz_index = TIMEZONES.index(current_tz) if current_tz in TIMEZONES else 0

        with st.form("profile_edit_form"):
            name_val  = st.text_input("Full Name",
                                       value=profile.get("name","") or current_name())
            phone_val = st.text_input("Phone",    value=profile.get("phone",""))
            loc_val   = st.text_input("Location / Office", value=profile.get("location",""))
            tz_val    = st.selectbox(
                "Timezone (IANA)",
                TIMEZONES, index=tz_index,
                help="All calendar times are stored in UTC and converted to your timezone.",
            )
            submitted = st.form_submit_button("Save Changes", use_container_width=True)

        if submitted:
            if not name_val.strip():
                st.error("Name is required.")
            else:
                ok, msg = update_profile_details(
                    user.id, name_val, phone_val, loc_val, tz_val
                )
                if ok:
                    st.session_state["user_name"] = name_val.strip()
                    st.session_state.pop("_cached_profile", None)
                    st.session_state.pop("profile_checked", None)
                    st.success("Profile updated.")
                else:
                    st.error(msg)

    with col_sec:
        st.markdown('<div class="card-title">ACCOUNT</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card-sm">
            <div class="detail-row">
                <span class="detail-label">Email</span>
                <span class="detail-val" style="font-size:.8rem;">{current_email()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Role</span>
                <span class="detail-val"><span class="role-pill {rc}">{ri} {role}</span></span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Timezone</span>
                <span class="detail-val" style="font-size:.8rem;">{current_tz}</span>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class="alert-box alert-info" style="margin-top:.6rem;">
            <div class="icon">ℹ</div>
            <div class="body" style="font-size:.8rem;">
                <b>To change your password:</b><br>
                Log out, then use the <b>Forgot Password</b> tab
                on the login screen. A reset link will be sent to your email.
            </div>
        </div>""", unsafe_allow_html=True)

    # Log Out — Phase 11
    st.markdown("---")
    lc1, _ = st.columns([1, 5])
    with lc1:
        if st.button("Log Out", use_container_width=True, key="prof_logout"):
            logout()
            st.rerun()
