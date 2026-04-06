# pages/profile_settings.py  —  SCMA User Profile
import streamlit as st
from db.auth import get_supabase_user, current_email, current_name, logout
from db.operations import get_profile, update_profile_details

# IANA timezones relevant to SCMA's user base
TIMEZONES = [
    "UTC",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Amsterdam",
    "Asia/Kolkata",
    "Asia/Colombo",
    "Asia/Dubai",
    "Asia/Karachi",
    "Asia/Dhaka",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
    "America/Guyana",
    "America/Port_of_Spain",
    "America/St_Lucia",
    "America/Barbados",
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Sao_Paulo",
    "Africa/Johannesburg",
    "Africa/Lagos",
    "Africa/Nairobi",
]


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>MY PROFILE</h1>
        <p>Manage your account details and timezone</p></div>
    </div>""", unsafe_allow_html=True)

    user = get_supabase_user()
    if not user:
        st.error("Not authenticated.")
        return

    profile = get_profile(user.id) or {}
    role    = st.session_state.get("user_role", "viewer")
    rc      = {"admin":"role-admin","editor":"role-editor","viewer":"role-viewer"}.get(role,"role-viewer")
    ri      = {"admin":"👑","editor":"✏️","viewer":"👁"}.get(role,"👁")

    # Profile card
    st.markdown(f"""
    <div class="card" style="display:flex;gap:1.4rem;align-items:center;flex-wrap:wrap;margin-bottom:1.5rem;">
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
    </div>""", unsafe_allow_html=True)

    # Two columns: edit form | password info
    col_form, col_pass = st.columns([3, 2])

    with col_form:
        st.markdown('<div class="card-title">EDIT DETAILS</div>', unsafe_allow_html=True)

        current_tz = profile.get("timezone", "UTC") or "UTC"
        tz_index   = TIMEZONES.index(current_tz) if current_tz in TIMEZONES else 0

        with st.form("profile_edit_form"):
            name_val = st.text_input(
                "Full Name",
                value=profile.get("name","") or current_name(),
            )
            phone_val = st.text_input("Phone", value=profile.get("phone",""))
            loc_val   = st.text_input("Location / Office", value=profile.get("location",""))
            tz_val    = st.selectbox(
                "Timezone (IANA)",
                TIMEZONES,
                index=tz_index,
                help="All calendar times are stored in UTC and converted to your local timezone.",
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
                    st.success("Profile updated.")
                    # Clear cached profile so it reloads on next nav
                    st.session_state.pop("_cached_profile", None)
                    st.session_state.pop("profile_checked", None)
                else:
                    st.error(msg)

    with col_pass:
        st.markdown('<div class="card-title">PASSWORD & SECURITY</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="alert-box alert-info">
            <div class="icon">ℹ️</div>
            <div class="body">
                <div class="title">Password Management</div>
                Passwords are managed securely via Supabase Auth.<br><br>
                To change your password:<br>
                1. Log out<br>
                2. Click "Create Account" → use same email<br>
                3. Or contact your administrator to send a reset link via
                   Supabase Dashboard → Authentication → Users
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card-sm" style="margin-top:.8rem;">
            <div style="font-size:.7rem;font-weight:700;letter-spacing:.1em;
                        text-transform:uppercase;color:#8b949e;margin-bottom:.5rem;">
                Account Info
            </div>
            <div class="detail-row">
                <span class="detail-label">Email</span>
                <span class="detail-val">{current_email()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">User ID</span>
                <span class="detail-val" style="font-size:.72rem;font-family:'DM Mono',monospace;">
                    {str(user.id)[:18]}…
                </span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Timezone</span>
                <span class="detail-val">{current_tz}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # Logout
    st.markdown("---")
    c1, _ = st.columns([1, 4])
    with c1:
        if st.button("Log Out", use_container_width=True, key="prof_logout"):
            logout()
            st.rerun()
