# pages/add_event.py
import streamlit as st
from datetime import date
from db.operations import add_event, load_events
from db.auth import current_user, can_edit


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <h1>ADD EVENT</h1>
        <p>Register a new match, series or tournament</p>
    </div>
    """, unsafe_allow_html=True)

    if not can_edit():
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">🔒</div>
            <div class="body"><div class="title">View-Only Access</div>
            You have viewer permissions. Contact an admin to request edit access.</div>
        </div>""", unsafe_allow_html=True)
    else:
        with st.form("add_event_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ev_name     = st.text_input("Event Name *", placeholder="e.g. ICC T20 World Cup 2026")
                ev_type     = st.selectbox("Event Type *", ["match", "series", "tournament"])
                ev_category = st.selectbox("Category *", ["International", "Domestic", "League"])
            with c2:
                ev_country  = st.text_input("Country / Host Nation *", placeholder="e.g. India, West Indies")
                ev_gender   = st.selectbox("Gender *", ["Male", "Female", "Mixed"])
                ev_format   = st.selectbox("Format *", ["T20", "ODI", "Test", "The Hundred", "Mixed / Multiple", "Other"])

            c3, c4 = st.columns(2)
            with c3:
                ev_start = st.date_input("Start Date *", value=date.today())
            with c4:
                ev_end   = st.date_input("End Date *",   value=date.today())

            ev_notes = st.text_area("Notes / Info", placeholder="Optional: teams, qualifiers, etc.")

            submitted = st.form_submit_button("➕  Add Event", use_container_width=True)

        if submitted:
            errs = []
            if not ev_name.strip():    errs.append("Event Name is required.")
            if not ev_country.strip(): errs.append("Country is required.")
            if ev_start > ev_end:      errs.append("Start date must be ≤ End date.")
            if errs:
                for e in errs: st.error(e)
            else:
                u = current_user()
                ok, msg = add_event(
                    ev_name.strip(), ev_type, ev_category, ev_format,
                    ev_start, ev_end, ev_country.strip(), ev_gender,
                    ev_notes.strip(), user_id=u.id if u else None,
                )
                if ok: st.success(msg)
                else:  st.error(msg)

    # ── Existing events ────────────────────────────────────
    events_df = load_events()
    if not events_df.empty:
        st.markdown('<br><div class="card-title">EXISTING EVENTS</div>', unsafe_allow_html=True)

        # Filter controls
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_cat    = st.selectbox("Filter Category", ["All","International","Domestic","League"], key="ae_fcat")
        with fc2:
            f_gender = st.selectbox("Filter Gender",   ["All","Male","Female","Mixed"],             key="ae_fgen")
        with fc3:
            f_fmt    = st.selectbox("Filter Format",   ["All"] + sorted(events_df["format"].unique().tolist()), key="ae_ffmt")

        disp = events_df.copy()
        if f_cat    != "All": disp = disp[disp["category"] == f_cat]
        if f_gender != "All": disp = disp[disp["gender"]   == f_gender]
        if f_fmt    != "All": disp = disp[disp["format"]   == f_fmt]

        disp2 = disp[["event_name","category","event_type","format","start_date","end_date","country","gender"]].copy()
        disp2["start_date"] = disp2["start_date"].dt.date
        disp2["end_date"]   = disp2["end_date"].dt.date
        disp2.columns = ["Event","Category","Type","Format","Start","End","Country","Gender"]
        st.dataframe(disp2, use_container_width=True, hide_index=True)
