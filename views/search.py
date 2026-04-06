# pages/search.py
# ──────────────────────────────────────────────────────────────
#  Search & Event Finder
#  • Search by event name / country / format + optional year
#  • Results shown as a mini calendar + conflict summary
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

import calendar as cal_lib
import streamlit as st
import pandas as pd
from datetime import date

from db.operations import load_events, load_squad
from utils.conflicts import conflicts_for_event

MONTH_NAMES = ["","Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
DOW         = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

CAT_CLASS = {
    "International": "ev-intl",
    "Domestic":      "ev-dom",
    "League":        "ev-league",
}


def _mini_calendar(year: int, month: int, highlight_start: date, highlight_end: date) -> str:
    """Small month grid highlighting the event's date range."""
    today  = date.today()
    c      = cal_lib.monthcalendar(year, month)
    dow    = "".join(f'<div style="font-size:0.6rem;font-weight:700;color:#8b949e;'
                     f'text-align:center;padding:2px;">{d}</div>' for d in DOW)
    cells  = ""
    for week in c:
        for day_num in week:
            if day_num == 0:
                cells += '<div style="min-height:28px;"></div>'
                continue
            d      = date(year, month, day_num)
            in_ev  = highlight_start <= d <= highlight_end
            is_tod = d == today
            bg     = "rgba(240,180,41,0.25)" if in_ev else "transparent"
            border = "1px solid #f0b429" if is_tod else "1px solid transparent"
            color  = "#f0b429" if is_tod else ("#e6edf3" if in_ev else "#8b949e")
            cells += (
                f'<div style="font-size:0.72rem;text-align:center;padding:3px 0;'
                f'border-radius:4px;background:{bg};border:{border};color:{color};'
                f'font-weight:{"700" if in_ev else "400"};">{day_num}</div>'
            )
    return f"""
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:1px;
                background:#30363d;border-radius:6px;padding:4px;
                font-family:'DM Sans',sans-serif;">
        {dow}{cells}
    </div>
    """


def _conflict_summary(event_name: str, events_df: pd.DataFrame, squad_df: pd.DataFrame) -> None:
    cfls = conflicts_for_event(event_name, events_df, squad_df)
    total = len(cfls["event"]) + len(cfls["player"]) + len(cfls["team"])

    if total == 0:
        st.markdown("""
        <div class="alert-box alert-success" style="margin-top:0.6rem;">
            <div class="icon">✅</div>
            <div class="body"><div class="title">No conflicts found</div>
            This event has no date overlaps, player double-bookings or team conflicts.</div>
        </div>""", unsafe_allow_html=True)
        return

    # Event conflicts (highest priority)
    if cfls["event"]:
        with st.expander(f"📅 Date Conflicts ({len(cfls['event'])})", expanded=True):
            for c in cfls["event"]:
                other = c["Event B"] if c["Event A"] == event_name else c["Event A"]
                other_start = c["Start B"] if c["Event A"] == event_name else c["Start A"]
                other_end   = c["End B"]   if c["Event A"] == event_name else c["End A"]
                st.markdown(f"""
                <div class="alert-box alert-error">
                    <div class="icon">🚨</div>
                    <div class="body">
                        Overlaps with <b>{other}</b><br>
                        <span style="color:#8b949e;font-size:0.82rem;">
                        {other_start} → {other_end}</span>
                    </div>
                </div>""", unsafe_allow_html=True)

    # Player conflicts
    if cfls["player"]:
        with st.expander(f"👤 Player Conflicts ({len(cfls['player'])})"):
            df = pd.DataFrame(cfls["player"])
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Team conflicts
    if cfls["team"]:
        with st.expander(f"🏟 Team Conflicts ({len(cfls['team'])})"):
            df = pd.DataFrame(cfls["team"])
            st.dataframe(df, use_container_width=True, hide_index=True)


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <h1>SEARCH & FIND</h1>
        <p>Search by event name, country or format · filter by year</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Search bar ─────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        query = st.text_input(
            "🔍  Search",
            placeholder="Event name, country, format…",
            key="search_query",
            label_visibility="collapsed",
        )
    with col2:
        years = list(range(2024, date.today().year + 3))
        year_opt = ["All years"] + [str(y) for y in years]
        sel_year = st.selectbox("Year", year_opt, key="search_year",
                                label_visibility="collapsed")
    with col3:
        gender_f = st.selectbox("Gender", ["All","Male","Female"],
                                key="search_gender", label_visibility="collapsed")

    if not query.strip():
        st.markdown("""
        <div class="alert-box alert-info" style="margin-top:1rem;">
            <div class="icon">💡</div>
            <div class="body">Type a search term above to find events.
            You can search by event name, country, or format.</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Load & filter ──────────────────────────────────────
    all_events = load_events()
    squad_df   = load_squad()

    if all_events.empty:
        st.warning("No events in the database yet.")
        return

    mask = (
        all_events["event_name"].str.contains(query, case=False, na=False) |
        all_events["country"].str.contains(query, case=False, na=False)    |
        all_events["format"].str.contains(query, case=False, na=False)
    )
    results = all_events[mask].copy()

    if sel_year != "All years":
        y = int(sel_year)
        results = results[
            (results["start_date"].dt.year == y) |
            (results["end_date"].dt.year   == y)
        ]

    if gender_f != "All":
        results = results[results["gender"] == gender_f]

    if results.empty:
        st.markdown(f"""
        <div class="alert-box alert-warn">
            <div class="icon">🔍</div>
            <div class="body">No events found for <b>"{query}"</b>.</div>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown(f"""
    <div style="font-size:0.82rem;color:#8b949e;margin-bottom:1rem;">
        {len(results)} event(s) found
    </div>
    """, unsafe_allow_html=True)

    # ── Result cards ───────────────────────────────────────
    for _, ev in results.iterrows():
        cat       = ev.get("category","International")
        cat_cls   = CAT_CLASS.get(cat,"ev-intl")
        cat_badge = {"International":"badge-intl","Domestic":"badge-dom","League":"badge-league"}.get(cat,"badge-blue")
        gen_badge = "badge-blue" if ev["gender"] == "Male" else "badge-purple"
        s_date    = ev["start_date"].date()
        e_date    = ev["end_date"].date()
        duration  = (ev["end_date"] - ev["start_date"]).days + 1

        with st.expander(
            f"📍 {ev['event_name']}  —  {s_date}  →  {e_date}",
            expanded=(len(results) == 1),
        ):
            left, right = st.columns([3, 2])

            with left:
                # Badges row
                st.markdown(f"""
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;">
                    <span class="badge {cat_badge}">{cat}</span>
                    <span class="badge {gen_badge}">{ev['gender']}</span>
                    <span class="badge badge-blue">{ev['format']}</span>
                    <span class="badge badge-yellow">{ev['event_type']}</span>
                </div>
                <div style="font-size:0.86rem;color:#c9d1d9;display:grid;
                            grid-template-columns:1fr 1fr;gap:0.5rem 1.5rem;
                            margin-bottom:1rem;">
                    <div><span style="color:#8b949e;">Country</span><br><b>{ev['country']}</b></div>
                    <div><span style="color:#8b949e;">Duration</span><br><b>{duration} day(s)</b></div>
                    <div><span style="color:#8b949e;">Start</span><br><b>{s_date}</b></div>
                    <div><span style="color:#8b949e;">End</span><br><b>{e_date}</b></div>
                </div>
                """, unsafe_allow_html=True)
                if ev.get("notes"):
                    st.markdown(f"""
                    <div style="font-size:0.82rem;color:#8b949e;border-left:2px solid #30363d;
                                padding-left:0.8rem;">{ev['notes']}</div>
                    """, unsafe_allow_html=True)

                st.markdown("**Conflict Check:**")
                _conflict_summary(ev["event_name"], all_events, squad_df)

            with right:
                # Mini calendars for start month (and end month if different)
                st.markdown(f"""
                <div style="font-size:0.75rem;font-weight:700;letter-spacing:0.1em;
                            text-transform:uppercase;color:#8b949e;margin-bottom:0.5rem;">
                    {MONTH_NAMES[s_date.month]} {s_date.year}
                </div>
                """, unsafe_allow_html=True)
                st.markdown(
                    _mini_calendar(s_date.year, s_date.month, s_date, e_date),
                    unsafe_allow_html=True,
                )

                if e_date.month != s_date.month or e_date.year != s_date.year:
                    st.markdown(f"""
                    <div style="font-size:0.75rem;font-weight:700;letter-spacing:0.1em;
                                text-transform:uppercase;color:#8b949e;margin:0.8rem 0 0.5rem;">
                        {MONTH_NAMES[e_date.month]} {e_date.year}
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(
                        _mini_calendar(e_date.year, e_date.month, s_date, e_date),
                        unsafe_allow_html=True,
                    )
