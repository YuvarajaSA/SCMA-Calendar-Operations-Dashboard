# pages/dashboard.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import date

from db.operations import load_events, load_squad, load_teams
from utils.conflicts import detect_player_conflicts, detect_team_conflicts, detect_event_overlaps
from utils.analysis import player_workload


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>DASHBOARD</h1><p>Live overview — events, conflicts, workload</p></div>
    </div>
    """, unsafe_allow_html=True)

    squad_df  = load_squad()
    events_df = load_events()
    teams_df  = load_teams()

    total_events  = len(events_df)
    total_teams   = teams_df["team_name"].nunique() if not teams_df.empty else 0
    total_players = squad_df["player_name"].nunique() if not squad_df.empty else 0

    eo = detect_event_overlaps(events_df)
    pc = detect_player_conflicts(squad_df)
    tc = detect_team_conflicts(squad_df)

    # ── Stat chips ─────────────────────────────────────────
    ec  = "#f85149" if eo else "#3fb950"
    pcc = "#f85149" if pc else "#3fb950"
    tcc = "#f85149" if tc else "#3fb950"

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-chip"><div class="val">{total_events}</div><div class="lbl">Events</div></div>
        <div class="stat-chip"><div class="val">{total_teams}</div><div class="lbl">Teams</div></div>
        <div class="stat-chip"><div class="val">{total_players}</div><div class="lbl">Players</div></div>
        <div class="stat-chip"><div class="val" style="color:{ec};">{len(eo)}</div><div class="lbl">Date Conflicts</div></div>
        <div class="stat-chip"><div class="val" style="color:{pcc};">{len(pc)}</div><div class="lbl">Player Conflicts</div></div>
        <div class="stat-chip"><div class="val" style="color:{tcc};">{len(tc)}</div><div class="lbl">Team Conflicts</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Desktop 3-col layout: events | conflicts | workload ─
    left, mid, right = st.columns([3, 2, 2])

    with left:
        st.markdown('<div class="card-title">📋 UPCOMING EVENTS</div>', unsafe_allow_html=True)
        if not events_df.empty:
            today = pd.Timestamp(date.today())
            upcoming = events_df[events_df["end_date"] >= today].head(15)
            disp = upcoming[["event_name","category","format","start_date","end_date","country","gender"]].copy()
            disp["start_date"] = disp["start_date"].dt.date
            disp["end_date"]   = disp["end_date"].dt.date
            disp.columns = ["Event","Category","Format","Start","End","Country","Gender"]
            st.dataframe(disp, use_container_width=True, hide_index=True, height=420)
        else:
            st.markdown("""
            <div class="alert-box alert-warn">
                <div class="icon">⚠️</div>
                <div class="body">No events yet. Use <b>Add Event</b> to get started.</div>
            </div>""", unsafe_allow_html=True)

    with mid:
        st.markdown('<div class="card-title">⚠️ ACTIVE CONFLICTS</div>', unsafe_allow_html=True)

        if not eo and not pc and not tc:
            st.markdown("""
            <div class="alert-box alert-success">
                <div class="icon">✅</div>
                <div class="body"><div class="title">All Clear</div>
                No scheduling conflicts detected.</div>
            </div>""", unsafe_allow_html=True)
        else:
            if eo:
                st.markdown(f'<span class="p-chip p1">P1</span>'
                            f'<b style="font-size:.88rem;">Event Date Conflicts</b>',
                            unsafe_allow_html=True)
                for c in eo[:5]:
                    st.markdown(f"""
                    <div class="alert-box alert-error" style="padding:.6rem .9rem;margin-bottom:.4rem;">
                        <div class="icon">📅</div>
                        <div class="body" style="font-size:.78rem;">
                            <b>{c['Event A']}</b><br>overlaps <b>{c['Event B']}</b><br>
                            <span style="color:#8b949e;">{c['Start A']} – {c['End A']}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                if len(eo) > 5:
                    st.markdown(f'<div class="gcal-more">+{len(eo)-5} more</div>', unsafe_allow_html=True)

            if pc:
                st.markdown(f'<div style="margin-top:.8rem;"></div>'
                            f'<span class="p-chip p2">P2</span>'
                            f'<b style="font-size:.88rem;">Player Conflicts</b>',
                            unsafe_allow_html=True)
                for c in pc[:4]:
                    st.markdown(f"""
                    <div class="alert-box alert-warn" style="padding:.6rem .9rem;margin-bottom:.4rem;">
                        <div class="icon">👤</div>
                        <div class="body" style="font-size:.78rem;">
                            <b>{c['Player']}</b><br>{c['Event A']} ↔ {c['Event B']}
                        </div>
                    </div>""", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card-title">💪 PLAYER WORKLOAD</div>', unsafe_allow_html=True)
        if not squad_df.empty:
            players = sorted(squad_df["player_name"].unique())
            rows = []
            for p in players[:20]:
                cnt, level = player_workload(squad_df, p)
                rows.append({"Player": p, "Events (30d)": cnt, "Workload": level})
            wl_df = pd.DataFrame(rows)
            st.dataframe(wl_df, use_container_width=True, hide_index=True, height=420)
        else:
            st.markdown("""
            <div class="alert-box alert-info">
                <div class="icon">💡</div>
                <div class="body">No squad data yet.</div>
            </div>""", unsafe_allow_html=True)

    # ── Bottom: category breakdown ─────────────────────────
    if not events_df.empty:
        st.markdown("---")
        b1, b2, b3 = st.columns(3)
        for col, cat, badge in [
            (b1, "International", "badge-intl"),
            (b2, "Domestic",      "badge-dom"),
            (b3, "League",        "badge-league"),
        ]:
            with col:
                subset = events_df[events_df["category"] == cat]
                st.markdown(f'<span class="badge {badge}">{cat}</span>'
                            f'<span style="font-size:.82rem;color:#8b949e;margin-left:.5rem;">'
                            f'{len(subset)} event(s)</span>', unsafe_allow_html=True)
                if not subset.empty:
                    d2 = subset[["event_name","format","start_date","gender"]].copy()
                    d2["start_date"] = d2["start_date"].dt.date
                    d2.columns = ["Event","Format","Start","Gender"]
                    st.dataframe(d2.head(8), use_container_width=True, hide_index=True)
