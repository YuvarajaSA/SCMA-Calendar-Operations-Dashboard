# pages/conflicts.py
# ──────────────────────────────────────────────────────────────
#  Conflicts — Priority:
#    1. Event date conflicts (FIRST — do dates clash?)
#    2. Player conflicts     (is a player double-booked?)
#    3. Team conflicts       (is a team double-booked?)
# ──────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
from db.operations import load_squad, load_events
from utils.conflicts import (
    detect_event_overlaps,
    detect_player_conflicts,
    detect_team_conflicts,
)


def _ok_box(label: str) -> None:
    st.markdown(f"""
    <div class="alert-box alert-success">
        <div class="icon">✅</div>
        <div class="body"><div class="title">No {label}</div>
        All clear — no overlapping schedules detected.</div>
    </div>""", unsafe_allow_html=True)


def _err_box(count: int, label: str, detail: str) -> None:
    st.markdown(f"""
    <div class="alert-box alert-error">
        <div class="icon">🚨</div>
        <div class="body"><div class="title">{count} {label} Detected</div>{detail}</div>
    </div>""", unsafe_allow_html=True)


def _warn_box(count: int, label: str, detail: str) -> None:
    st.markdown(f"""
    <div class="alert-box alert-warn">
        <div class="icon">⚠️</div>
        <div class="body"><div class="title">{count} {label}</div>{detail}</div>
    </div>""", unsafe_allow_html=True)


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <h1>CONFLICTS</h1>
        <p>Automatic detection — Event date clashes checked first, then player & team overlaps</p>
    </div>
    """, unsafe_allow_html=True)

    squad_df  = load_squad()
    events_df = load_events()

    # ── PRIORITY 1: Event date overlaps ──────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.6rem;">
        <span style="background:#f85149;color:#fff;font-size:0.65rem;font-weight:800;
                     letter-spacing:0.1em;padding:0.15rem 0.5rem;border-radius:20px;">
            PRIORITY 1
        </span>
        <div class="card-title" style="margin-bottom:0;">📅 EVENT DATE CONFLICTS</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.82rem;color:#8b949e;margin-bottom:0.8rem;">
        Check these <b>before assigning players</b> — overlapping events will cause downstream conflicts.
    </div>
    """, unsafe_allow_html=True)

    eo = detect_event_overlaps(events_df)
    if not eo:
        _ok_box("Event Date Conflicts")
    else:
        _err_box(len(eo), "Event Date Conflict(s)",
                 "These events share overlapping dates. Resolve scheduling before assigning squads.")
        st.dataframe(pd.DataFrame(eo), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── PRIORITY 2: Player conflicts ─────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.6rem;">
        <span style="background:#e3b341;color:#0d1117;font-size:0.65rem;font-weight:800;
                     letter-spacing:0.1em;padding:0.15rem 0.5rem;border-radius:20px;">
            PRIORITY 2
        </span>
        <div class="card-title" style="margin-bottom:0;">👤 PLAYER CONFLICTS</div>
    </div>
    """, unsafe_allow_html=True)

    pc = detect_player_conflicts(squad_df)
    if not pc:
        _ok_box("Player Conflicts")
    else:
        _err_box(len(pc), "Player Conflict(s)",
                 "Players committed to two or more events at the same time.")
        st.dataframe(pd.DataFrame(pc), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── PRIORITY 3: Team conflicts ───────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.6rem;">
        <span style="background:#58a6ff;color:#0d1117;font-size:0.65rem;font-weight:800;
                     letter-spacing:0.1em;padding:0.15rem 0.5rem;border-radius:20px;">
            PRIORITY 3
        </span>
        <div class="card-title" style="margin-bottom:0;">🏟 TEAM CONFLICTS</div>
    </div>
    """, unsafe_allow_html=True)

    tc = detect_team_conflicts(squad_df)
    if not tc:
        _ok_box("Team Conflicts")
    else:
        _warn_box(len(tc), "Team Conflict(s)",
                  "Teams scheduled in overlapping events.")
        st.dataframe(pd.DataFrame(tc), use_container_width=True, hide_index=True)
