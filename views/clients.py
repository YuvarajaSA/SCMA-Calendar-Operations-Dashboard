# pages/clients.py  —  SCMA Clients Info Module
# Phases 6/7/8/9: manual entry + CSV/Excel upload
# Sensitive data: editors INSERT only, admins read/update

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import date

from db.auth import can_edit, is_admin, current_email, get_supabase_user
from db.operations import (
    load_clients, add_client_full, bulk_add_clients,
    load_client_sensitive, log_activity,
)

CLIENT_TYPES = ["Player","Coach","Commentator","Analyst","Other"]
BATTING      = ["","Right-hand","Left-hand"]
BOWLING      = ["","Right-arm Fast","Right-arm Medium","Right-arm Off-spin",
                "Right-arm Leg-spin","Left-arm Fast","Left-arm Medium",
                "Left-arm Orthodox","Left-arm Chinaman","N/A"]


# ── Manual Entry Tab ──────────────────────────────────────────

def _tab_manual() -> None:
    st.markdown('<div class="card-title">ADD CLIENT</div>', unsafe_allow_html=True)

    if not can_edit():
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">🔒</div>
            <div class="body">Edit access required to add clients.</div>
        </div>""", unsafe_allow_html=True)
        return

    with st.form("client_manual_form"):
        st.markdown("""
        <div style="font-size:.7rem;font-weight:800;letter-spacing:.1em;
                    text-transform:uppercase;color:#8b949e;margin-bottom:.6rem;">
            Public Information
        </div>""", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            full_name   = st.text_input("Full Name *", placeholder="Joe Root")
            first_name  = st.text_input("First Name *", placeholder="Joe")
            last_name   = st.text_input("Last Name *",  placeholder="Root")
        with c2:
            dob         = st.date_input("Date of Birth", value=None)
            citizenship = st.text_input("Citizenship", placeholder="England")
            client_type = st.selectbox("Client Type *", CLIENT_TYPES)
        with c3:
            player_role   = st.text_input("Player Role", placeholder="Batter / Bowler / WK…")
            batting_style = st.selectbox("Batting Style", BATTING)
            bowling_style = st.selectbox("Bowling Style", BOWLING)

        c4, c5 = st.columns(2)
        with c4:
            shirt_number = st.text_input("Shirt Number", placeholder="66")
        with c5:
            espn_link    = st.text_input("ESPN Cricinfo Link", placeholder="https://espncricinfo.com/…")

        st.markdown("""
        <div style="height:.8rem"></div>
        <div style="font-size:.7rem;font-weight:800;letter-spacing:.1em;
                    text-transform:uppercase;color:#f85149;margin-bottom:.4rem;">
            Sensitive Information
        </div>
        <div class="alert-box alert-warn" style="margin-bottom:.8rem;">
            <div class="icon">⚠</div>
            <div class="body" style="font-size:.8rem;">
                Sensitive data is <b>write-only for editors</b>.
                Once saved, only <b>admins</b> can view it.
            </div>
        </div>""", unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            s_email     = st.text_input("Email",   placeholder="client@email.com")
            s_phone     = st.text_input("Phone",   placeholder="+1 234 567 8900")
            s_passport  = st.text_input("Passport Number", placeholder="AB1234567")
        with sc2:
            s_pp_expiry  = st.date_input("Passport Expiry", value=None)
            s_visa       = st.text_area("Visa Details", height=68, placeholder="Visa type / notes")
            s_airport    = st.text_input("Departure Airport", placeholder="LHR / JFK…")

        # Phase 8: Double confirmation checkbox
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        confirmed = st.checkbox(
            "I confirm all details are correct. "
            "Sensitive data cannot be viewed after saving (editor role).",
        )

        submitted = st.form_submit_button("Save Client", use_container_width=True)

    if submitted:
        errs = []
        if not full_name.strip():  errs.append("Full name is required.")
        if not first_name.strip(): errs.append("First name is required.")
        if not last_name.strip():  errs.append("Last name is required.")
        if not confirmed:          errs.append("Please tick the confirmation checkbox.")

        if errs:
            for e in errs:
                st.error(e)
        else:
            ok, msg = add_client_full(
                full_name     = full_name,
                first_name    = first_name,
                last_name     = last_name,
                dob           = dob,
                citizenship   = citizenship,
                client_type   = client_type,
                player_role   = player_role,
                batting_style = batting_style,
                bowling_style = bowling_style,
                shirt_number  = shirt_number,
                espn_link     = espn_link,
                email         = s_email,
                phone         = s_phone,
                passport_number  = s_passport,
                passport_expiry  = s_pp_expiry,
                visa_details     = s_visa,
                departure_airport= s_airport,
            )
            if ok:
                st.success(msg)
                u = get_supabase_user()
                log_activity(u.id if u else None, current_email(), "create", "client",
                             details={"name": full_name})
            else:
                st.error(msg)


# ── CSV / Excel Upload Tab ─────────────────────────────────────

def _tab_upload() -> None:
    st.markdown('<div class="card-title">BULK UPLOAD</div>', unsafe_allow_html=True)

    if not can_edit():
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">🔒</div>
            <div class="body">Edit access required.</div>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown("""
    <div class="alert-box alert-info">
        <div class="icon">ℹ</div>
        <div class="body" style="font-size:.82rem;">
            <b>Required columns:</b> full_name, first_name, last_name<br>
            <b>Optional:</b> dob, citizenship, client_type, player_role,
            batting_style, bowling_style, shirt_number, espn_link<br>
            Sensitive data (email, passport, etc.) is not supported in bulk upload.
            Add it individually after import.
        </div>
    </div>""", unsafe_allow_html=True)

    file = st.file_uploader("Upload CSV or Excel (.xlsx)", type=["csv","xlsx"], key="client_upload")
    if file is None:
        return

    try:
        if file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    required_cols = ["full_name","first_name","last_name"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    st.markdown(f"**Preview** — {len(df)} rows")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    confirmed = st.checkbox(
        "I confirm this data is correct and ready to import.",
        key="bulk_confirm",
    )

    if st.button("Import Clients", use_container_width=True, key="import_clients"):
        if not confirmed:
            st.error("Tick the confirmation checkbox first.")
        else:
            rows = df.to_dict("records")
            ok_count, warns = bulk_add_clients(rows)
            for w in warns:
                st.warning(w)
            if ok_count:
                st.success(f"Imported {ok_count} client(s).")
                u = get_supabase_user()
                log_activity(u.id if u else None, current_email(), "bulk_import",
                             "client", details={"count": ok_count})


# ── Client List Tab ────────────────────────────────────────────

def _tab_list() -> None:
    clients_df = load_clients()

    if clients_df.empty:
        st.markdown("""
        <div class="alert-box alert-info" style="margin-top:.5rem;">
            <div class="icon">ℹ</div>
            <div class="body">No clients yet. Add one using the Manual Entry tab.</div>
        </div>""", unsafe_allow_html=True)
        return

    # Search + filter
    sc1, sc2 = st.columns(2)
    with sc1:
        search = st.text_input("Search name", placeholder="Filter by name…",
                               key="cl_search", label_visibility="collapsed")
    with sc2:
        type_f = st.selectbox("Type", ["All"] + CLIENT_TYPES,
                              key="cl_type", label_visibility="collapsed")

    disp = clients_df.copy()
    if search.strip():
        disp = disp[disp["full_name"].str.contains(search.strip(), case=False, na=False)]
    if type_f != "All":
        disp = disp[disp["client_type"] == type_f]

    # Public columns
    pub_cols = ["full_name","client_type","citizenship","player_role",
                "batting_style","shirt_number","espn_link","created_at"]
    pub_cols = [c for c in pub_cols if c in disp.columns]
    show = disp[pub_cols].copy()
    if "created_at" in show.columns:
        show["created_at"] = pd.to_datetime(show["created_at"]).dt.strftime("%Y-%m-%d")
    show.columns = [c.replace("_"," ").title() for c in show.columns]

    st.markdown(f"**{len(show)} client(s)**")
    st.dataframe(show, use_container_width=True, hide_index=True)

    # Admin: view sensitive data for selected client
    if is_admin() and not disp.empty:
        st.markdown("---")
        st.markdown('<div class="card-title">SENSITIVE DATA (Admin Only)</div>',
                    unsafe_allow_html=True)
        sel_name = st.selectbox("Select client", disp["full_name"].tolist(),
                                key="cl_admin_sel")
        sel_row = disp[disp["full_name"] == sel_name]
        if not sel_row.empty and "id" in sel_row.columns:
            cid = int(sel_row.iloc[0]["id"])
            if st.button("Load Sensitive Data", key=f"load_sens_{cid}"):
                sens = load_client_sensitive(cid)
                if sens:
                    st.markdown("""
                    <div class="alert-box alert-error" style="margin-bottom:.6rem;">
                        <div class="icon">🔒</div>
                        <div class="body" style="font-size:.8rem;">
                            Sensitive data — do not share screen
                        </div>
                    </div>""", unsafe_allow_html=True)
                    for k, v in sens.items():
                        if k not in ("id","client_id","created_at") and v:
                            st.markdown(
                                f'<div class="detail-row">'
                                f'<span class="detail-label">{k.replace("_"," ").title()}</span>'
                                f'<span class="detail-val">{v}</span></div>',
                                unsafe_allow_html=True,
                            )
                else:
                    st.info("No sensitive record found for this client.")


# ── Main render ───────────────────────────────────────────────

def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>CLIENTS</h1>
        <p>Client profiles — public info and secure sensitive data</p></div>
    </div>""", unsafe_allow_html=True)

    tab_list, tab_add, tab_upload = st.tabs([
        "Client List", "Manual Entry", "Bulk Upload"
    ])
    with tab_list:   _tab_list()
    with tab_add:    _tab_manual()
    with tab_upload: _tab_upload()
