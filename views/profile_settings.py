# pages/profile_settings.py  —  SCMA User Profile Settings
import streamlit as st
from db.auth import get_supabase_user, current_email, current_name, logout
from db.operations import get_profile, update_profile_details

TIMEZONES = [
    "UTC", "Europe/London", "Europe/Paris", "Europe/Berlin",
    "Asia/Kolkata", "Asia/Colombo", "Asia/Dubai", "Asia/Karachi",
    "Asia/Dhaka", "Asia/Singapore", "Asia/Tokyo",
    "Australia/Sydney", "Pacific/Auckland",
    "America/New_York", "America/Chicago", "America/Los_Angeles",
    "America/Toronto", "America/Sao_Paulo",
    "Africa/Johannesburg", "Africa/Lagos",
]


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>MY PROFILE</h1>
        <p>Manage your account details and preferences</p></div>
    </div>""", unsafe_allow_html=True)

    user = get_supabase_user()
    if not user:
        st.error("Not authenticated.")
        return

    profile = get_profile(user.id)

    # ── Profile card ──────────────────────────────────────────
    role = st.session_state.get("user_role","viewer")
    role_cls = {"admin":"role-admin","editor":"role-editor","viewer":"role-viewer"}.get(role,"role-viewer")
    role_icon = {"admin":"👑","editor":"✏️","viewer":"👁"}.get(role,"👁")

    st.markdown(f"""
    <div class="card" style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap;">
        <div style="width:52px;height:52px;border-radius:50%;
                    background:rgba(240,180,41,.15);border:2px solid #f0b429;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.4rem;flex-shrink:0;">
            {role_icon}
        </div>
        <div>
            <div style="font-size:1.1rem;font-weight:700;color:#e6edf3;">
                {current_name() or "—"}
            </div>
            <div style="font-size:.82rem;color:#8b949e;">{current_email()}</div>
            <div style="margin-top:.4rem;">
                <span class="role-pill {role_cls}">{role_icon} {role}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Edit form ─────────────────────────────────────────────
    st.markdown('<div class="card-title">EDIT DETAILS</div>', unsafe_allow_html=True)

    current_tz = (profile or {}).get("timezone","UTC")
    tz_index   = TIMEZONES.index(current_tz) if current_tz in TIMEZONES else 0

    with st.form("profile_edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            name_val = st.text_input("Full Name *",
                                      value=(profile or {}).get("name","") or current_name())
            phone_val = st.text_input("Phone",
                                       value=(profile or {}).get("phone",""))
        with c2:
            loc_val  = st.text_input("Location / Office",
                                      value=(profile or {}).get("location",""))
            tz_val   = st.selectbox("Timezone", TIMEZONES, index=tz_index)

        submitted = st.form_submit_button("Save Changes", use_container_width=True)

    if submitted:
        if not name_val.strip():
            st.error("Name is required.")
        else:
            from db.supabase_client import get_client
            ok, msg = update_profile_details(user.id, name_val, phone_val, loc_val)
            # Update timezone separately (not in the safe update — admin must do role/status)
            if ok:
                try:
                    sb = get_client()
                    sb.table("profiles").update({"timezone": tz_val}).eq("id", user.id).execute()
                except Exception:
                    pass
                st.session_state["user_name"] = name_val.strip()
                st.success("Profile updated.")
            else:
                st.error(msg)

    # ── Logout ────────────────────────────────────────────────
    st.markdown("---")
    col1, _ = st.columns([1, 3])
    with col1:
        if st.button("Log Out", use_container_width=True, key="prof_logout"):
            logout()
            st.rerun()
