# pages/login.py  —  SCMA Calendar Dashboard
import streamlit as st
from db.auth import login_with_password, signup_with_password


def render() -> None:
    st.markdown("""
    <style>
    .stApp {
        background:
            radial-gradient(ellipse at 20% 60%, rgba(26,111,181,.1) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 10%, rgba(240,180,41,.07) 0%, transparent 50%),
            #0d1117 !important;
    }
    section[data-testid="stSidebar"] { display:none !important; }
    .main .block-container { padding-top:0 !important; max-width:100% !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown("<div style='min-height:7vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])

    with mid:
        # Header card
        st.markdown("""
        <div style="background:#161b22; border:1px solid #30363d; border-radius:16px;
                    padding:2.6rem 2.4rem 2rem; max-width:440px; margin:0 auto;
                    box-shadow:0 8px 40px rgba(0,0,0,.5);">
            <div style="text-align:center; margin-bottom:2rem;">
                <div style="font-size:2.6rem; line-height:1; margin-bottom:.5rem;">🏏</div>
                <div style="font-family:'Bebas Neue',sans-serif; font-size:2rem;
                            color:#f0b429; letter-spacing:.06em; line-height:1.1;">
                    SCMA CALENDAR
                </div>
                <div style="font-size:.82rem; color:#8b949e; margin-top:.35rem;">
                    Sophie Agency — Internal Staff Portal
                </div>
                <div style="margin-top:.7rem;">
                    <span style="display:inline-block; padding:.18rem .75rem;
                        background:rgba(248,81,73,.08); border:1px solid rgba(248,81,73,.22);
                        border-radius:20px; font-size:.64rem; font-weight:700;
                        letter-spacing:.1em; text-transform:uppercase; color:#f85149;">
                        Restricted Access
                    </span>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        err = st.session_state.pop("auth_error", None)
        if err:
            st.markdown(f"""
            <div style="background:rgba(248,81,73,.08); border:1px solid rgba(248,81,73,.28);
                        border-radius:8px; padding:.75rem 1rem; margin-bottom:.8rem;
                        font-size:.83rem; color:#f85149;">{err}</div>""",
                        unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign In", "Create Account"])

        with tab_in:
            st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
            email = st.text_input(
                "Email", placeholder="you@sophieagency.com",
                key="si_email", label_visibility="collapsed",
            )
            password = st.text_input(
                "Password", type="password", placeholder="Password",
                key="si_pass", label_visibility="collapsed",
            )
            if st.button("Sign In", use_container_width=True, key="btn_signin"):
                if not email.strip() or not password:
                    st.error("Enter your email and password.")
                else:
                    with st.spinner("Signing in…"):
                        ok, msg = login_with_password(email.strip(), password)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_up:
            st.caption("New accounts require admin approval before access is granted.")
            email_up = st.text_input(
                "Email", placeholder="you@sophieagency.com",
                key="su_email", label_visibility="collapsed",
            )
            pass_up = st.text_input(
                "Password", type="password", placeholder="Minimum 6 characters",
                key="su_pass", label_visibility="collapsed",
            )
            name_up = st.text_input(
                "Full name", placeholder="Full name",
                key="su_name", label_visibility="collapsed",
            )
            if st.button("Create Account", use_container_width=True, key="btn_signup"):
                if not email_up.strip() or not pass_up or not name_up.strip():
                    st.error("All fields are required.")
                elif len(pass_up) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account…"):
                        ok, reason = signup_with_password(
                            email_up.strip(), pass_up, name_up.strip()
                        )
                    if ok and reason == "confirmed":
                        st.rerun()
                    elif ok and reason == "confirm_email":
                        st.success("Account created. Check your email to confirm, then sign in.")
                    else:
                        st.error(reason)

        st.markdown("""
        <div style="text-align:center; margin-top:1.6rem; font-size:.7rem; color:#8b949e;">
            Secured by Supabase Auth &nbsp;·&nbsp; Internal use only
        </div>""", unsafe_allow_html=True)
