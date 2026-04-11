# views/csv_upload.py  —  SCMA CSV Upload System
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
from utils.datetime_utils import validate_time_str, TIMEZONES

# ── Shared helpers ────────────────────────────────────────────

def _read_file(file) -> pd.DataFrame:
    """Detects file extension and reads it into a pandas DataFrame."""
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    elif name.endswith(".xlsx"):
        return pd.read_excel(file)
    elif name.endswith(".json"):
        return pd.read_json(file)
    else:
        raise ValueError("Unsupported file type. Please upload a CSV, XLSX, or JSON file.")

def _validate_cols(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in df.columns]

def _schema_info(required: list[str], optional: list[str]) -> None:
    req_str = ", ".join(f"<b>{c}</b>" for c in required)
    opt_str = ", ".join(optional)
    st.markdown(f"""
    <div class="alert-box alert-info">
        <div class="icon">ℹ️</div>
        <div class="body" style="font-size:.82rem;">
            <b>Required:</b> {req_str}<br>
            <b>Optional:</b> {opt_str}
        </div>
    </div>""", unsafe_allow_html=True)

def _parse_time_flexible(val: str) -> str:
                try:
                    import pandas as pd
                    t = pd.to_datetime(val).time()
                    return f"{t.hour:02d}:{t.minute:02d}"
                except Exception:
                    return "00:00"

# ── Shared helpers ────────────────────────────────────────────


# ── Matches Tab ───────────────────────────────────────────────

# ── Matches Tab ───────────────────────────────────────────────

def _tab_matches() -> None:
    """
    File schema
    ──────────
    Required : event_name, match_date, team1, team2
    Optional : match_name, venue, match_time (HH:MM), timezone (IANA)

    Behaviour
    ─────────
    - match_time missing / empty  → "00:00"
    - timezone  missing / empty   → "UTC"
    - Invalid match_time format   → warning + row skipped
    - match_datetime is derived via datetime_utils.to_utc()
      inside bulk_add_matches(); time is never silently discarded.
    """
    _schema_info(
        required=["event_name", "match_date", "team1", "team2"],
        optional=["match_name", "venue", "match_time (HH:MM)", "timezone (IANA)"],
    )

    # Default timezone selector applied to all rows missing a timezone column
    default_tz = st.selectbox(
        "Default timezone (used when 'timezone' column is absent or blank)",
        TIMEZONES,
        index=0,
        key="csv_match_tz",
    )

    file = st.file_uploader("Upload Matches file", type=["csv", "xlsx", "json"], key="file_matches")
    if file is None:
        return

    try:
        df = _read_file(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    missing = _validate_cols(df, ["event_name", "match_date", "team1", "team2"])
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

        ev_map: dict[str, int] = {}
        if not ev_df.empty and "event_name" in ev_df.columns and "id" in ev_df.columns:
            ev_map = {r["event_name"]: int(r["id"]) for _, r in ev_df.iterrows()}

        team_map: dict[str, dict[str, int]] = {}
        if not teams_df.empty and "event_name" in teams_df.columns:
            for _, r in teams_df.iterrows():
                team_map.setdefault(r["event_name"], {})[r["team_name"].strip().lower()] = int(r.get("id", 0))

        rows:  list[dict] = []
        warns: list[str]  = []

        for i, r in df.iterrows():
            row_num  = int(i) + 1
            ev_name  = str(r.get("event_name", "")).strip()
            ev_id    = ev_map.get(ev_name)
            if not ev_id:
                warns.append(f"Row {row_num}: event '{ev_name}' not found — skipped.")
                continue

            # Parse date — keep as date object, never strip time yet
            parsed_date = pd.to_datetime(r["match_date"], errors="coerce")

            if pd.isna(parsed_date):
                warns.append(f"Row {row_num}: invalid match_date '{r['match_date']}' — skipped.")
                continue

            m_date = parsed_date.date()

            # Time resolution — strict validation, no silent fallback
            raw_time = _parse_time_flexible(r.get("match_time", ""))
            
            if not raw_time:
                raw_time = "00:00"

            # Timezone resolution
            raw_tz = str(r.get("timezone", "")).strip() if "timezone" in df.columns else ""
            if raw_tz and raw_tz not in TIMEZONES:
                warns.append(
                    f"Row {row_num}: unrecognised timezone '{raw_tz}' — "
                    f"using default '{default_tz}'."
                )
                raw_tz = default_tz
            if not raw_tz:
                raw_tz = default_tz

            # Team resolution — warn explicitly when name doesn't match
            t1n   = str(r.get("team1", "")).strip().lower()
            t2n   = str(r.get("team2", "")).strip().lower()
            t1_id = team_map.get(ev_name, {}).get(t1n)
            t2_id = team_map.get(ev_name, {}).get(t2n)
            if t1n and not t1_id:
                warns.append(
                    f"Row {row_num}: team '{t1n}' not found in '{ev_name}' — "
                    f"team1_id will be NULL."
                )
            if t2n and not t2_id:
                warns.append(
                    f"Row {row_num}: team '{t2n}' not found in '{ev_name}' — "
                    f"team2_id will be NULL."
                )

            rows.append({
                "event_id":   ev_id,
                "match_name": str(r.get("match_name", "")).strip() or f"{t1n} vs {t2n}",
                "match_date": m_date,
                "match_time": raw_time,
                "timezone":   raw_tz,
                "team1_id":   t1_id,
                "team2_id":   t2_id,
                "venue":      str(r.get("venue", "")).strip(),
            })

        if rows:
            ok_count, errs = bulk_add_matches(rows)
            for w in warns: st.warning(w)
            for e in errs:  st.warning(e)
            st.success(f"Imported {ok_count} match(es).")
        else:
            for w in warns: st.warning(w)
            st.error("No valid rows to import.")


# ── Teams Tab ─────────────────────────────────────────────────

def _tab_teams() -> None:
    _schema_info(
        required=["event_name", "team_name"],
        optional=[],
    )

    file = st.file_uploader("Upload Teams file", type=["csv", "xlsx", "json"], key="file_teams")
    if file is None:
        return
        
    try:
        df = _read_file(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    missing = _validate_cols(df, ["event_name", "team_name"])
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    if st.button("Import Teams", use_container_width=True, key="imp_teams"):
        ok_count, warns = 0, []
        for i, r in df.iterrows():
            ev_name   = str(r.get("event_name", "")).strip()
            team_name = str(r.get("team_name", "")).strip()
            if not ev_name or not team_name:
                warns.append(f"Row {int(i)+1}: empty value — skipped.")
                continue
            ok, msg = add_team(ev_name, team_name)
            if ok:
                ok_count += 1
            else:
                warns.append(f"Row {int(i)+1}: {msg}")
        for w in warns: st.warning(w)
        st.success(f"Imported {ok_count} team(s).")

# ── Squad Tab ─────────────────────────────────────────────────

# ── Squad Tab ─────────────────────────────────────────────────

def _tab_squad() -> None:
    _schema_info(
        required=["event_name", "team_name", "player_name"],
        optional=[],
    )

    file = st.file_uploader("Upload Squad file", type=["csv", "xlsx", "json"], key="file_squad")
    if file is None:
        return

    try:
        df = _read_file(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    missing = _validate_cols(df, ["event_name", "team_name", "player_name"])
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    if st.button("Import Squad", use_container_width=True, key="imp_squad"):
        ok_count, warns = 0, []
        for i, r in df.iterrows():
            ev_name   = str(r.get("event_name", "")).strip()
            team_name = str(r.get("team_name", "")).strip()
            player    = str(r.get("player_name", "")).strip()
            if not ev_name or not team_name or not player:
                warns.append(f"Row {int(i)+1}: empty value — skipped.")
                continue
            ok, msg = add_player_to_squad(player, ev_name, team_name)
            if ok:
                ok_count += 1
            else:
                warns.append(f"Row {int(i)+1}: {msg}")
        for w in warns: st.warning(w)
        st.success(f"Imported {ok_count} squad record(s).")
# ── Render ────────────────────────────────────────────────────

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
