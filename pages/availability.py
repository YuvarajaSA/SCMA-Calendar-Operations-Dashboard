# pages/availability.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db.operations import load_squad
from utils.analysis import player_workload, workload_badge_class


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <h1>PLAYER AVAILABILITY</h1>
        <p>Check availability before assigning to events — first priority in workflow</p>
    </div>
    """, unsafe_allow_html=True)

    squad_df = load_squad()
    if squad_df.empty:
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">⚠️</div>
            <div class="body">No squad data. Add players via <b>👥 Add Squad</b>.</div>
        </div>""", unsafe_allow_html=True)
        return

    all_players = sorted(squad_df["player_name"].unique().tolist())

    # ── Desktop: check form + result side by side ──────────
    form_col, result_col = st.columns([1, 2])

    with form_col:
        st.markdown('<div class="card-title">CHECK AVAILABILITY</div>', unsafe_allow_html=True)
        with st.form("avail_form"):
            sel_player = st.selectbox("Player *", all_players)
            chk_start  = st.date_input("From *", value=date.today())
            chk_end    = st.date_input("To *",   value=date.today() + timedelta(days=14))
            submitted  = st.form_submit_button("🔍  Check", use_container_width=True)

    with result_col:
        if submitted:
            if chk_start > chk_end:
                st.error("Start must be ≤ End date.")
            else:
                chk_s = pd.Timestamp(chk_start)
                chk_e = pd.Timestamp(chk_end)
                pdata = squad_df[squad_df["player_name"] == sel_player]
                blocking = pdata[
                    (pdata["start_date"] <= chk_e) & (pdata["end_date"] >= chk_s)
                ]
                cnt, level = player_workload(squad_df, sel_player)
                badge_cls  = workload_badge_class(level)

                if blocking.empty:
                    st.markdown(f"""
                    <div class="alert-box alert-success">
                        <div class="icon">✅</div>
                        <div class="body">
                            <div class="title">{sel_player} — AVAILABLE</div>
                            Free from <b>{chk_start}</b> to <b>{chk_end}</b>.<br>
                            Workload (30d): <span class="badge {badge_cls}">{level}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="alert-box alert-error">
                        <div class="icon">🚫</div>
                        <div class="body">
                            <div class="title">{sel_player} — NOT AVAILABLE</div>
                            Committed to <b>{len(blocking)}</b> event(s) in that window.
                        </div>
                    </div>""", unsafe_allow_html=True)
                    disp = blocking[["event_name","team","format","start_date","end_date"]].copy()
                    disp["start_date"] = disp["start_date"].dt.date
                    disp["end_date"]   = disp["end_date"].dt.date
                    disp.columns = ["Event","Team","Format","Start","End"]
                    st.dataframe(disp, use_container_width=True, hide_index=True)

    # ── Desktop dense: full today status table ─────────────
    st.markdown("---")
    st.markdown('<div class="card-title">ALL PLAYERS — TODAY\'S STATUS</div>',
                unsafe_allow_html=True)

    today = pd.Timestamp(date.today())

    # Filter controls in one row
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        search_p = st.text_input("Search player", placeholder="Filter by name…",
                                 key="avail_search", label_visibility="collapsed")
    with fc2:
        filter_status = st.selectbox("Status", ["All","Available","Busy"],
                                     key="avail_status", label_visibility="collapsed")
    with fc3:
        filter_wl = st.selectbox("Workload", ["All","Low","Medium","High"],
                                 key="avail_wl", label_visibility="collapsed")

    rows_out = []
    for p in all_players:
        if search_p and search_p.lower() not in p.lower():
            continue
        pdata = squad_df[squad_df["player_name"] == p]
        busy  = pdata[(pdata["start_date"] <= today) & (pdata["end_date"] >= today)]
        cnt, level = player_workload(squad_df, p)
        if busy.empty:
            rows_out.append({"Player":p,"Status":"✅ Available","Current Event":"—","Team":"—","Workload":level,"Events (30d)":cnt})
        else:
            r = busy.iloc[0]
            rows_out.append({"Player":p,"Status":"🔴 Busy","Current Event":r["event_name"],"Team":r["team"],"Workload":level,"Events (30d)":cnt})

    tbl = pd.DataFrame(rows_out)
    if filter_status != "All":
        tbl = tbl[tbl["Status"].str.contains("Available" if filter_status=="Available" else "Busy")]
    if filter_wl != "All":
        tbl = tbl[tbl["Workload"] == filter_wl]

    st.dataframe(tbl, use_container_width=True, hide_index=True, height=450)
