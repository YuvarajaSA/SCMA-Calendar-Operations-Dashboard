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
    "UTC",
    "Europe/London",
    "Europe/Paris",
    "Asia/Kolkata",
    "Asia/Colombo",
    "Asia/Dubai",
    "Asia/Karachi",
    "Asia/Dhaka",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Pacific/Auckland",
    "America/Guyana",
    "America/Port_of_Spain",
    "America/St_Lucia",
    "America/New_York",
    "America/Los_Angeles",
    "Africa/Johannesburg",
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
            if d == today:         css += " gcal-today"
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


# ── Inline add form (opens when a date is clicked) ────────────

def _inline_add_form(selected_day: date, ev_names: list[str]) -> None:
    st.markdown(f"""
    <div style="background:#1c2128;border:1px solid #30363d;border-radius:10px;
                padding:1rem 1.2rem;margin-bottom:1rem;">
        <div style="font-size:.72rem;font-weight:700;letter-spacing:.1em;
                    text-transform:uppercase;color:#f0b429;margin-bottom:.7rem;">
            Quick Add — {selected_day}
        </div>
    </div>""", unsafe_allow_html=True)

    add_type = st.selectbox("What to add", ["Match","Registration","Auction"],
                             key="inline_type", label_visibility="collapsed")

    if add_type == "Match":
        with st.form("inline_match_form", clear_on_submit=True):
            match_name = st.text_input("Match name", value=f"Match on {selected_day}")
            ev_sel = st.selectbox("Link to event (optional)", ["(none)"] + ev_names)
            venue  = st.text_input("Venue", placeholder="Optional")
            if st.form_submit_button("Add Match", use_container_width=True):
                from db.auth import can_edit
                if not can_edit():
                    st.error("Edit access required.")
                else:
                    ev_id = None
                    if ev_sel != "(none)":
                        ev_df = load_events()
                        row = ev_df[ev_df["event_name"] == ev_sel]
                        if not row.empty and "id" in row.columns:
                            ev_id = int(row.iloc[0]["id"])
                    ok, msg = add_match(ev_id, match_name, selected_day, venue=venue)
                    if ok:
                        st.success(msg)
                        load_matches.clear()
                        st.session_state.pop("cal_selected_day", None)
                        st.rerun()
                    else:
                        st.error(msg)

    elif add_type == "Registration":
        with st.form("inline_reg_form", clear_on_submit=True):
            ev_sel   = st.selectbox("Link to event (optional)", ["(none)"] + ev_names)
            deadline = st.date_input("Deadline", value=selected_day)
            notes    = st.text_input("Notes", placeholder="Optional")
            if st.form_submit_button("Add Registration", use_container_width=True):
                from db.auth import can_edit
                if not can_edit():
                    st.error("Edit access required.")
                else:
                    ev_id = None
                    if ev_sel != "(none)":
                        ev_df = load_events()
                        row = ev_df[ev_df["event_name"] == ev_sel]
                        if not row.empty and "id" in row.columns:
                            ev_id = int(row.iloc[0]["id"])
                    ok, msg = add_registration(ev_id, selected_day, deadline, notes)
                    if ok:
                        st.success(msg)
                        load_registrations.clear()
                        st.session_state.pop("cal_selected_day", None)
                        st.rerun()
                    else:
                        st.error(msg)

    else:  # Auction
        with st.form("inline_auction_form", clear_on_submit=True):
            franchise = st.text_input("Franchise name", placeholder="e.g. Mumbai Indians")
            ev_sel    = st.selectbox("Link to event (optional)", ["(none)"] + ev_names)
            location  = st.text_input("Location", placeholder="Optional")
            if st.form_submit_button("Add Auction", use_container_width=True):
                from db.auth import can_edit
                if not can_edit():
                    st.error("Edit access required.")
                else:
                    if not franchise.strip():
                        st.error("Franchise name required.")
                    else:
                        ev_id = None
                        if ev_sel != "(none)":
                            ev_df = load_events()
                            row = ev_df[ev_df["event_name"] == ev_sel]
                            if not row.empty and "id" in row.columns:
                                ev_id = int(row.iloc[0]["id"])
                        ok, msg = add_auction(ev_id, franchise.strip(), selected_day, location)
                        if ok:
                            st.success(msg)
                            load_auctions.clear()
                            st.session_state.pop("cal_selected_day", None)
                            st.rerun()
                        else:
                            st.error(msg)

    if st.button("Cancel", key="cancel_inline"):
        st.session_state.pop("cal_selected_day", None)
        st.rerun()


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


# ── Filters panel ─────────────────────────────────────────────

def _render_filters(all_items: pd.DataFrame) -> pd.DataFrame:
    """Apply search + type + gender + category filters. Returns filtered df."""
    with st.expander("Filters & Search", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            search_q = st.text_input("Search title", placeholder="Event / match name…", key="cal_search")
            gender_f = st.selectbox("Gender", ["All","Male","Female","Mixed"], key="cf_g")
        with fc2:
            type_f = st.multiselect(
                "Item types",
                ["event","match","registration","auction"],
                default=["event","match","registration","auction"],
                key="cf_types",
            )
            category_f = st.selectbox("Category", ["All","International","Domestic","League"], key="cf_cat")
        with fc3:
            date_from = st.date_input("From date", value=None, key="cf_from")
            date_to   = st.date_input("To date",   value=None, key="cf_to")

    df = all_items.copy() if not all_items.empty else pd.DataFrame()
    if df.empty:
        return df

    if type_f:
        df = df[df["type"].isin(type_f)]

    if search_q.strip():
        df = df[df["title"].str.contains(search_q.strip(), case=False, na=False)]

    if gender_f != "All":
        def _gender_match(meta):
            return meta.get("gender","") == gender_f if isinstance(meta, dict) else True
        df = df[df["metadata"].apply(_gender_match)]

    if category_f != "All":
        def _cat_match(meta):
            return meta.get("category","") == category_f if isinstance(meta, dict) else True
        df = df[df["metadata"].apply(_cat_match)]

    if date_from:
        df = df[df["start_date"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["end_date"] <= pd.Timestamp(date_to)]

    return df.reset_index(drop=True)


# ── Main render ───────────────────────────────────────────────

def render() -> None:
    # Extra CSS for match/reg/auction pill types
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
    ev_names = event_names()

    # ── Load & filter all items ────────────────────────────────
    try:
        all_items_raw = load_calendar_items()
    except Exception:
        all_items_raw = pd.DataFrame()

    all_items = _render_filters(all_items_raw)

    # ── Conflict detection ─────────────────────────────────────
    try:
        ev_df    = load_events()
        overlaps = detect_event_overlaps(ev_df)
    except Exception:
        overlaps = []
    conflict_ids: set = set()
    for o in overlaps:
        for k in ("id_a","id_b"):
            if k in o:
                conflict_ids.add(o[k])

    # ── Year / month nav ───────────────────────────────────────
    today    = date.today()
    year_min = today.year
    year_max = today.year + 2
    if not all_items.empty:
        try:
            year_min = min(year_min, int(all_items["start_date"].dt.year.min()))
            year_max = max(year_max, int(all_items["end_date"].dt.year.max()))
        except Exception:
            pass

    year_list = list(range(int(year_min), int(year_max) + 1))

    nav1, nav2, nav3 = st.columns([1, 1, 4])
    with nav1:
        def_yr = year_list.index(today.year) if today.year in year_list else 0
        sel_year = st.selectbox("Year", year_list, index=def_yr, key="cal_yr")
    with nav2:
        sel_month = st.selectbox(
            "Month", list(range(1, 13)),
            index=today.month - 1,
            format_func=lambda m: MONTHS[m],
            key="cal_mo",
        )
    with nav3:
        badge_html = (
            f'<span class="badge badge-red">{len(overlaps)} conflict(s)</span>'
            if overlaps else
            '<span class="badge badge-green">No conflicts</span>'
        )
        st.markdown(
            f'<div style="margin-top:1.6rem;">{badge_html}</div>',
            unsafe_allow_html=True,
        )

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
            month_items = pd.DataFrame()

    # ── Selected day (for inline add) ─────────────────────────
    selected_day: date | None = st.session_state.get("cal_selected_day")

    # ── Day picker for adding items ────────────────────────────
    from db.auth import can_edit as _can_edit
    if _can_edit():
        with st.expander("Add item on a specific date", expanded=(selected_day is not None)):
            pick_col, _ = st.columns([1, 2])
            with pick_col:
                pick_date = st.date_input(
                    "Select date",
                    value=selected_day or today,
                    key="cal_pick_date",
                )
            if st.button("Open Quick Add", key="open_inline"):
                st.session_state["cal_selected_day"] = pick_date
                st.rerun()

    # ── Two-column layout ──────────────────────────────────────
    cal_col, panel_col = st.columns([4, 1], gap="medium")

    with cal_col:
        st.markdown(f"""
        <div class="gcal-nav">
            <div class="gcal-month-label">{MONTHS[sel_month]} {sel_year}</div>
            <div style="font-size:.76rem;color:#8b949e;">
                {len(month_items)} item(s) — {user_tz}
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(
            _build_grid(sel_year, sel_month, month_items, conflict_ids, selected_day),
            unsafe_allow_html=True,
        )
        st.markdown(_legend_html(), unsafe_allow_html=True)

        # Inline add form
        if selected_day and _can_edit():
            st.markdown("---")
            _inline_add_form(selected_day, ev_names)

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
