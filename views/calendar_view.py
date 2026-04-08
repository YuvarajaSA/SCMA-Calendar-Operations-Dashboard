# pages/calendar_view.py  —  SCMA Multi-Entity Calendar
# Phase 2: events + matches + registrations + auctions
# Crash-proof (no KeyError), timezone-aware, filters, inline add

from __future__ import annotations

import calendar
import streamlit as st
import pandas as pd
from datetime import date, datetime, timezone as tz

from db.operations import (
    load_events, load_calendar_items,
    load_teams, teams_for_event, event_names,
    add_match, add_registration, add_auction,
    load_matches, load_registrations, load_auctions,
)
from utils.conflicts import detect_event_overlaps

# ── Constants ─────────────────────────────────────────────────
MONTHS  = ["","January","February","March","April","May","June",
           "July","August","September","October","November","December"]
DOW     = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
WEEKEND = {5, 6}

TYPE_CSS = {
    "event":        "pill-intl",
    "match":        "pill-match",
    "registration": "pill-reg",
    "auction":      "pill-auction",
}
TYPE_BADGE = {
    "event":        "badge-intl",
    "match":        "badge-green",
    "registration": "badge-yellow",
    "auction":      "badge-purple",
}

SCMA_TIMEZONES = [
    "UTC", "Europe/London", "Europe/Paris", "Asia/Kolkata", "Asia/Colombo",
    "Asia/Dubai", "Asia/Karachi", "Asia/Dhaka", "Asia/Singapore", "Asia/Tokyo",
    "Australia/Sydney", "Pacific/Auckland", "America/Guyana",
    "America/Port_of_Spain", "America/St_Lucia", "America/New_York",
    "America/Los_Angeles", "Africa/Johannesburg",
]


# ── Timezone helper ────────────────────────────────────────────

def _to_user_tz(dt: datetime | pd.Timestamp, tz_str: str) -> datetime:
    """Convert UTC datetime to user's local timezone."""
    try:
        import pytz
        user_tz = pytz.timezone(tz_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.utc)
        return dt.astimezone(user_tz)
    except Exception:
        return dt


def _get_user_tz() -> str:
    from db.auth import get_supabase_user
    from db.operations import get_profile
    user = get_supabase_user()
    if not user:
        return "UTC"
    profile = get_profile(user.id)
    return (profile or {}).get("timezone", "UTC") or "UTC"


# ── Calendar grid helpers ──────────────────────────────────────

def _safe_on_day(df: pd.DataFrame, d: date) -> pd.DataFrame:
    """Return rows active on day d. Never raises KeyError."""
    if df is None or df.empty:
        return pd.DataFrame()
    if "start_date" not in df.columns or "end_date" not in df.columns:
        return pd.DataFrame()
    ts = pd.Timestamp(d)
    try:
        return df[
            (df["start_date"] <= ts) & (df["end_date"] >= ts)
        ].copy()
    except Exception:
        return pd.DataFrame()


def _pill_html(row: pd.Series, conflict_ids: set) -> str:
    itype  = row.get("type", "event")
    css    = TYPE_CSS.get(itype, "pill-intl")
    title  = str(row.get("title", ""))
    short  = (title[:22] + "…") if len(title) > 24 else title
    flag   = " ⚠" if (itype == "event" and row.get("id") in conflict_ids) else ""
    return (
        f'<span class="gcal-pill {css}" title="{title.replace(chr(34),chr(39))}">'
        f'<div class="gcal-pill-name">{short}{flag}</div>'
        f'</span>'
    )


def _build_grid(
    year: int, month: int,
    df: pd.DataFrame,
    conflict_ids: set,
    selected_day: date | None,
) -> str:
    today = date.today()
    grid  = calendar.monthcalendar(year, month)
    dow_html = "".join(
        f'<div class="gcal-dow-cell{"  weekend" if i in WEEKEND else ""}">{d}</div>'
        for i, d in enumerate(DOW)
    )
    cells = ""
    for week in grid:
        for wi, day_num in enumerate(week):
            if day_num == 0:
                cells += '<div class="gcal-cell gcal-other"></div>'
                continue
            d   = date(year, month, day_num)
            evs = _safe_on_day(df, d)

            css = "gcal-cell"
            if d == today:          css += " gcal-today"
            if wi in WEEKEND:       css += " gcal-weekend"
            if d == selected_day:   css += " gcal-selected"
            if not evs.empty and any(
                r.get("type") == "event" and r.get("id") in conflict_ids
                for _, r in evs.iterrows()
            ):
                css += " has-conflict"

            day_num_html = (
                f'<div class="gcal-day-num">'
                f'<span class="gcal-today-circle">{day_num}</span></div>'
                if d == today else
                f'<div class="gcal-day-num">{day_num}</div>'
            )
            pills = ""
            total = len(evs)
            for i, (_, row) in enumerate(evs.iterrows()):
                if i >= 3:
                    pills += f'<span class="gcal-more">+{total - 3} more</span>'
                    break
                pills += _pill_html(row, conflict_ids)

            cells += f'<div class="{css}">{day_num_html}{pills}</div>'

    return (
        f'<div class="gcal-wrapper">'
        f'<div class="gcal-dow-row">{dow_html}</div>'
        f'<div class="gcal-grid">{cells}</div>'
        f'</div>'
    )


def _legend_html() -> str:
    items = [
        ("rgba(26,111,181,.85)",  "Event / Tournament"),
        ("rgba(63,185,80,.82)",   "Match"),
        ("rgba(240,180,41,.82)",  "Registration"),
        ("rgba(188,140,255,.82)", "Auction"),
    ]
    return '<div class="gcal-legend">' + "".join(
        f'<div class="gcal-legend-item">'
        f'<div class="gcal-legend-dot" style="background:{c};"></div>{l}</div>'
        for c, l in items
    ) + '</div>'


# ── Detail panel ──────────────────────────────────────────────

def _detail_panel(month_df: pd.DataFrame, conflict_ids: set, user_tz: str) -> None:
    st.markdown('<div class="detail-panel-title">DETAILS</div>', unsafe_allow_html=True)

    if month_df is None or month_df.empty:
        st.markdown(
            '<div style="font-size:.82rem;color:#8b949e;padding:.5rem 0;">No items this month.</div>',
            unsafe_allow_html=True,
        )
        return

    titles  = month_df["title"].tolist()
    sel_idx = st.session_state.get("cal_detail_idx", 0)
    if sel_idx >= len(titles):
        sel_idx = 0

    sel = st.selectbox(
        "Item", titles,
        index=sel_idx,
        key="dp_sel",
        label_visibility="collapsed",
    )

    row   = month_df[month_df["title"] == sel].iloc[0]
    itype = row.get("type", "event")
    meta  = row.get("metadata", {}) or {}

    badge = TYPE_BADGE.get(itype, "badge-blue")
    conflict = itype == "event" and row.get("id") in conflict_ids

    st.markdown(f"""
    <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.7rem;">
        <span class="badge {badge}">{itype}</span>
        {"<span class='badge badge-red'>Conflict</span>" if conflict else ""}
    </div>""", unsafe_allow_html=True)

    s = row["start_date"]
    e = row["end_date"]
    s_str = s.date().isoformat() if hasattr(s, "date") and pd.notna(s) else "—"
    e_str = e.date().isoformat() if hasattr(e, "date") and pd.notna(e) else "—"

    detail_rows = [("Start", s_str), ("End", e_str)]
    for k, v in meta.items():
        if v:
            detail_rows.append((k.replace("_"," ").title(), str(v)))

    for lbl, val in detail_rows:
        st.markdown(
            f'<div class="detail-row">'
            f'<span class="detail-label">{lbl}</span>'
            f'<span class="detail-val">{val}</span></div>',
            unsafe_allow_html=True,
        )

    if user_tz != "UTC":
        st.markdown(
            f'<div style="font-size:.7rem;color:#8b949e;margin-top:.5rem;">'
            f'Times shown in {user_tz}</div>',
            unsafe_allow_html=True,
        )


# ── Filter Helper (No UI rendering, just logic) ────────────────

def _apply_filters(df: pd.DataFrame, search_q: str, type_f: list, gender_f: str, category_f: str, date_from, date_to) -> pd.DataFrame:
    if df.empty:
        return df
    if type_f:
        df = df[df["type"].isin(type_f)]
    if search_q.strip():
        df = df[df["title"].str.contains(search_q.strip(), case=False, na=False)]
    if gender_f != "All":
        df = df[df["metadata"].apply(lambda m: m.get("gender","") == gender_f if isinstance(m, dict) else True)]
    if category_f != "All":
        df = df[df["metadata"].apply(lambda m: m.get("category","") == category_f if isinstance(m, dict) else True)]
    if date_from:
        df = df[df["start_date"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["end_date"] <= pd.Timestamp(date_to)]
    return df.reset_index(drop=True)


# ── Main render ───────────────────────────────────────────────

def render() -> None:
    st.markdown("""
    <style>
    .pill-match   {background:rgba(63,185,80,.82); color:#e8ffe8;border-left:3px solid #4dff7c;}
    .pill-reg     {background:rgba(240,180,41,.82);color:#fff8e0;border-left:3px solid #f0b429;}
    .pill-auction {background:rgba(188,140,255,.82);color:#f5e8ff;border-left:3px solid #cc88ff;}
    .gcal-cell.gcal-selected {border-color:var(--accent)!important;background:rgba(240,180,41,.08);}
    </style>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header">
        <div><h1>CALENDAR</h1>
        <p>Events · Matches · Registrations · Auctions</p></div>
    </div>""", unsafe_allow_html=True)

    user_tz  = _get_user_tz()

    # ── Load raw data & conflicts ───────
    try:
        all_items_raw = load_calendar_items()
    except Exception:
        all_items_raw = pd.DataFrame()

    try:
        ev_df = load_events()
        overlaps = detect_event_overlaps(ev_df)
    except Exception:
        overlaps = []
    
    conflict_ids: set = set()
    for o in overlaps:
        for k in ("id_a","id_b"):
            if k in o: conflict_ids.add(o[k])

    # ── Year bounds ───────
    today    = date.today()
    year_min, year_max = today.year, today.year + 2
    if not all_items_raw.empty:
        try:
            year_min = min(year_min, int(all_items_raw["start_date"].dt.year.min()))
            year_max = max(year_max, int(all_items_raw["end_date"].dt.year.max()))
        except Exception:
            pass
    year_list = list(range(int(year_min), int(year_max) + 1))
    
    # ── UNIFIED CONTROL BAR (Search | Year | Month | Filters | Quick Add) ──
    st.markdown('<div style="margin-top:1rem; margin-bottom: 0.5rem;"></div>', unsafe_allow_html=True)
    c_search, c_y, c_m, c_filt, c_qa = st.columns([3, 1, 1, 1, 1], gap="small")
    
    with c_search:
        search_q = st.text_input("Search", placeholder="Search event / match...", label_visibility="collapsed", key="cal_search")
        
    with c_y:
        def_yr = year_list.index(today.year) if today.year in year_list else 0
        sel_year = st.selectbox("Year", year_list, index=def_yr, key="cal_yr", label_visibility="collapsed")
        
    with c_m:
        sel_month = st.selectbox("Month", list(range(1, 13)), index=today.month - 1, format_func=lambda m: MONTHS[m], key="cal_mo", label_visibility="collapsed")

    with c_filt:
        with st.popover("Filters", use_container_width=True):
            type_f = st.multiselect("Item types", ["event","match","registration","auction"], default=["event","match","registration","auction"])
            category_f = st.selectbox("Category", ["All","International","Domestic","League"])
            gender_f = st.selectbox("Gender", ["All","Male","Female","Mixed"])
            date_from = st.date_input("From date", value=None)
            date_to = st.date_input("To date", value=None)

    with c_qa:
        from db.auth import can_edit as _can_edit
        if _can_edit():
            # Quick Add as a Popover Menu
            with st.popover("Quick Add", use_container_width=True):
                st.markdown("**Quick Add**")
                
                # Default date from clicked calendar cell, or today
                sel_day = st.session_state.get("cal_selected_day", today)
                add_type = st.selectbox("Type", ["Match","Registration","Auction"], key="qa_pop_type")
                
                # Build smart dropdown options mapping {"Event Name": id, "(None)": None}
                event_options = {"(None)": None}
                if not ev_df.empty and "event_name" in ev_df.columns and "id" in ev_df.columns:
                    for _, r in ev_df.iterrows():
                        event_options[r["event_name"]] = int(r["id"])

                # Event linking
                link_event = st.checkbox("Link to an event", value=False, key="qa_pop_link")
                ev_id_m = None
                if link_event:
                    ev_sel = st.selectbox("Select Event", list(event_options.keys()), key=f"qa_pop_ev_{add_type}")
                    ev_id_m = event_options[ev_sel]

                # Forms based on type
                if add_type == "Match":
                    with st.form("qa_match_form", clear_on_submit=True):
                        pick_date   = st.date_input("Date", value=sel_day)
                        match_name  = st.text_input("Match name", value=f"Match on {pick_date}")
                        venue       = st.text_input("Venue", placeholder="Optional")
                        if st.form_submit_button("Add Match", use_container_width=True):
                            ok, msg = add_match(ev_id_m, match_name, pick_date, venue=venue)
                            if ok:
                                st.success(msg)
                                load_matches.clear()
                                st.session_state.pop("cal_selected_day", None)
                                st.rerun()
                            else:
                                st.error(msg)
                                
                elif add_type == "Registration":
                    with st.form("qa_reg_form", clear_on_submit=True):
                        deadline   = st.date_input("Deadline", value=sel_day)
                        notes      = st.text_input("Notes", placeholder="Optional")
                        if st.form_submit_button("Add Registration", use_container_width=True):
                            ok, msg = add_registration(ev_id_m, sel_day, deadline, notes)
                            if ok:
                                st.success(msg)
                                load_registrations.clear()
                                st.session_state.pop("cal_selected_day", None)
                                st.rerun()
                            else:
                                st.error(msg)
                                
                else:  # Auction
                    with st.form("qa_auc_form", clear_on_submit=True):
                        pick_date  = st.date_input("Auction Date", value=sel_day)
                        franchise  = st.text_input("Franchise name", placeholder="e.g. Mumbai Indians")
                        location   = st.text_input("Location", placeholder="Optional")
                        if st.form_submit_button("Add Auction", use_container_width=True):
                            if not franchise.strip():
                                st.error("Franchise name required.")
                            else:
                                ok, msg = add_auction(ev_id_m, franchise.strip(), pick_date, location)
                                if ok:
                                    st.success(msg)
                                    load_auctions.clear()
                                    st.session_state.pop("cal_selected_day", None)
                                    st.rerun()
                                else:
                                    st.error(msg)

    # Apply Filters
    all_items = _apply_filters(all_items_raw, search_q, type_f, gender_f, category_f, date_from, date_to)

    # ── Month slice ────────────────────────────────────────────
    last_day    = calendar.monthrange(sel_year, sel_month)[1]
    month_start = pd.Timestamp(date(sel_year, sel_month, 1))
    month_end   = pd.Timestamp(date(sel_year, sel_month, last_day))

    month_items = pd.DataFrame()
    if not all_items.empty:
        try:
            month_items = all_items[
                (all_items["start_date"] <= month_end) &
                (all_items["end_date"]   >= month_start)
            ].copy().reset_index(drop=True)
        except Exception:
            pass

    selected_day: date | None = st.session_state.get("cal_selected_day")

    # ── Two-column layout ──────────────────────────────────────
    st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
    cal_col, panel_col = st.columns([4, 1.2], gap="large")

    badge_html = (
        f'<span class="badge badge-red">{len(overlaps)} conflict(s)</span>' if overlaps else '<span class="badge badge-green">No conflicts</span>'
    )

    with cal_col:
        st.markdown(f"""
        <div class="gcal-nav">
            <div class="gcal-month-label">{MONTHS[sel_month]} {sel_year}</div>
            <div style="font-size:.76rem;color:#8b949e;display:flex;align-items:center;gap:1rem;">
                <span>{len(month_items)} item(s) — {user_tz}</span>
                {badge_html}
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(
            _build_grid(sel_year, sel_month, month_items, conflict_ids, selected_day),
            unsafe_allow_html=True,
        )
        st.markdown(_legend_html(), unsafe_allow_html=True)

    with panel_col:
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        _detail_panel(month_items, conflict_ids, user_tz)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Month item list ────────────────────────────────────────
    if not month_items.empty:
        st.markdown("---")
        st.markdown(
            f'<div class="card-title">{MONTHS[sel_month]} {sel_year} — All Items</div>',
            unsafe_allow_html=True,
        )
        disp = month_items[["type","title","start_date","end_date"]].copy()
        disp["start_date"] = disp["start_date"].dt.date
        disp["end_date"]   = disp["end_date"].dt.date
        disp.columns       = ["Type","Title","Start","End"]
        st.dataframe(disp, use_container_width=True, hide_index=True)