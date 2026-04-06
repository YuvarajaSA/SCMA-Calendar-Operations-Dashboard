# pages/csv_upload.py  —  SCMA CSV Upload System
from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import date

from db.auth import can_edit
from db.operations import (
    load_events, load_teams, load_players,
    add_match, add_team, add_player_to_squad,
    bulk_add_matches,
)


def _validate_cols(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in df.columns]


def _tab_matches() -> None:
    st.markdown("""
    <div class="alert-box alert-info">
        <div class="icon">ℹ️</div>
        <div class="body">
            <b>Required columns:</b> event_name, match_date, team1, team2<br>
            <b>Optional:</b> match_name, venue
        </div>
    </div>""", unsafe_allow_html=True)

    file = st.file_uploader("Upload matches CSV", type=["csv"], key="csv_matches")
    if file is None:
        return

    try:
        df = pd.read_csv(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    missing = _validate_cols(df, ["event_name","match_date","team1","team2"])
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    st.markdown(f"**Preview** — {len(df)} rows")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    if st.button("Import Matches", use_container_width=True, key="imp_matches"):
        ev_df    = load_events()
        teams_df = load_teams()

        if ev_df.empty:
            st.error("No events in database. Add events first.")
            return

        ev_map = {}
        if not ev_df.empty and "event_name" in ev_df.columns and "id" in ev_df.columns:
            ev_map = {r["event_name"]: int(r["id"]) for _, r in ev_df.iterrows()}

        team_map: dict[str, dict[str, int]] = {}
        if not teams_df.empty and "event_name" in teams_df.columns:
            for _, r in teams_df.iterrows():
                team_map.setdefault(r["event_name"],{})[r["team_name"]] = int(r.get("id",0))

        rows, warns = [], []
        for i, r in df.iterrows():
            ev_name = str(r.get("event_name","")).strip()
            ev_id   = ev_map.get(ev_name)
            if not ev_id:
                warns.append(f"Row {i+1}: event '{ev_name}' not found — skipped.")
                continue

            try:
                m_date = pd.to_datetime(r["match_date"]).date()
            except Exception:
                warns.append(f"Row {i+1}: invalid match_date '{r['match_date']}' — skipped.")
                continue

            t1n = str(r.get("team1","")).strip()
            t2n = str(r.get("team2","")).strip()
            t1_id = team_map.get(ev_name,{}).get(t1n)
            t2_id = team_map.get(ev_name,{}).get(t2n)

            rows.append({
                "event_id":   ev_id,
                "match_name": str(r.get("match_name","")).strip() or f"{t1n} vs {t2n}",
                "match_date": m_date,
                "team1_id":   t1_id,
                "team2_id":   t2_id,
                "venue":      str(r.get("venue","")).strip(),
            })

        if rows:
            ok_count, errs = bulk_add_matches(rows)
            for w in warns: st.warning(w)
            for e in errs:  st.warning(e)
            st.success(f"Imported {ok_count} match(es).")
        else:
            for w in warns: st.warning(w)
            st.error("No valid rows to import.")


def _tab_teams() -> None:
    st.markdown("""
    <div class="alert-box alert-info">
        <div class="icon">ℹ️</div>
        <div class="body"><b>Required columns:</b> event_name, team_name</div>
    </div>""", unsafe_allow_html=True)

    file = st.file_uploader("Upload teams CSV", type=["csv"], key="csv_teams")
    if file is None:
        return

    try:
        df = pd.read_csv(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    missing = _validate_cols(df, ["event_name","team_name"])
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    if st.button("Import Teams", use_container_width=True, key="imp_teams"):
        ok_count, warns = 0, []
        for i, r in df.iterrows():
            ev_name   = str(r.get("event_name","")).strip()
            team_name = str(r.get("team_name","")).strip()
            if not ev_name or not team_name:
                warns.append(f"Row {i+1}: empty value — skipped.")
                continue
            ok, msg = add_team(ev_name, team_name)
            if ok:
                ok_count += 1
            else:
                warns.append(f"Row {i+1}: {msg}")
        for w in warns: st.warning(w)
        st.success(f"Imported {ok_count} team(s).")


def _tab_squad() -> None:
    st.markdown("""
    <div class="alert-box alert-info">
        <div class="icon">ℹ️</div>
        <div class="body"><b>Required columns:</b> event_name, team_name, player_name</div>
    </div>""", unsafe_allow_html=True)

    file = st.file_uploader("Upload squad CSV", type=["csv"], key="csv_squad")
    if file is None:
        return

    try:
        df = pd.read_csv(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    missing = _validate_cols(df, ["event_name","team_name","player_name"])
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    if st.button("Import Squad", use_container_width=True, key="imp_squad"):
        ok_count, warns = 0, []
        for i, r in df.iterrows():
            ev_name   = str(r.get("event_name","")).strip()
            team_name = str(r.get("team_name","")).strip()
            player    = str(r.get("player_name","")).strip()
            if not ev_name or not team_name or not player:
                warns.append(f"Row {i+1}: empty value — skipped.")
                continue
            ok, msg = add_player_to_squad(player, ev_name, team_name)
            if ok:
                ok_count += 1
            else:
                warns.append(f"Row {i+1}: {msg}")
        for w in warns: st.warning(w)
        st.success(f"Imported {ok_count} squad record(s).")


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>CSV UPLOAD</h1>
        <p>Bulk import matches, teams and squad records</p></div>
    </div>""", unsafe_allow_html=True)

    if not can_edit():
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">🔒</div>
            <div class="body">Edit access required.</div>
        </div>""", unsafe_allow_html=True)
        return

    tab1, tab2, tab3 = st.tabs(["Matches", "Teams", "Squad"])
    with tab1: _tab_matches()
    with tab2: _tab_teams()
    with tab3: _tab_squad()
