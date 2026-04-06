# pages/calendar_view.py  —  SCMA Multi-Entity Calendar
from __future__ import annotations

import calendar
import streamlit as st
import pandas as pd
from datetime import date

from db.operations import load_events, load_calendar_items
from utils.conflicts import detect_event_overlaps

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


def _extra_css() -> None:
    st.markdown("""
    <style>
    .pill-match   {background:rgba(63,185,80,.82); color:#e8ffe8; border-left:3px solid #4dff7c;}
    .pill-reg     {background:rgba(240,180,41,.82);color:#fff8e0; border-left:3px solid #f0b429;}
    .pill-auction {background:rgba(188,140,255,.82);color:#f5e8ff;border-left:3px solid #cc88ff;}
    </style>""", unsafe_allow_html=True)


def _on_day(df: pd.DataFrame, d: date) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if "start_date" not in df.columns or "end_date" not in df.columns:
        return pd.DataFrame()
    ts = pd.Timestamp(d)
    try:
        return df[(df["start_date"] <= ts) & (df["end_date"] >= ts)].copy()
    except Exception:
        return pd.DataFrame()


def _pill(row: pd.Series, conflict_ids: set) -> str:
    itype = row.get("type","event")
    cls   = TYPE_CSS.get(itype, "pill-intl")
    title = str(row.get("title",""))
    short = (title[:22]+"…") if len(title) > 24 else title
    flag  = " ⚠" if (itype=="event" and row.get("id") in conflict_ids) else ""
    return (
        f'<span class="gcal-pill {cls}" title="{title}">'
        f'<div class="gcal-pill-name">{short}{flag}</div>'
        f'</span>'
    )


def _build_grid(year: int, month: int, df: pd.DataFrame, conflict_ids: set) -> str:
    today    = date.today()
    grid     = calendar.monthcalendar(year, month)
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
            evs = _on_day(df, d)
            cls = "gcal-cell"
            if d == today:   cls += " gcal-today"
            if wi in WEEKEND: cls += " gcal-weekend"
            if not evs.empty and any(
                r.get("type")=="event" and r.get("id") in conflict_ids
                for _, r in evs.iterrows()
            ): cls += " has-conflict"

            day_html = (
                '<div class="gcal-day-num"><span class="gcal-today-circle">'
                f'{day_num}</span></div>'
                if d == today else
                f'<div class="gcal-day-num">{day_num}</div>'
            )
            pills = ""
            total = len(evs)
            for i, (_, row) in enumerate(evs.iterrows()):
                if i >= 3:
                    pills += f'<span class="gcal-more">+{total-3} more</span>'
                    break
                pills += _pill(row, conflict_ids)
            cells += f'<div class="{cls}">{day_html}{pills}</div>'

    return (
        f'<div class="gcal-wrapper">'
        f'<div class="gcal-dow-row">{dow_html}</div>'
        f'<div class="gcal-grid">{cells}</div>'
        f'</div>'
    )


def _legend() -> str:
    items = [
        ("rgba(26,111,181,.85)",  "Event"),
        ("rgba(63,185,80,.85)",   "Match"),
        ("rgba(240,180,41,.85)",  "Registration"),
        ("rgba(188,140,255,.85)", "Auction"),
    ]
    return '<div class="gcal-legend">' + "".join(
        f'<div class="gcal-legend-item">'
        f'<div class="gcal-legend-dot" style="background:{c};"></div>{l}</div>'
        for c, l in items
    ) + '</div>'


def _detail_panel(month_df: pd.DataFrame, conflict_ids: set) -> None:
    st.markdown('<div class="detail-panel-title">DETAILS</div>', unsafe_allow_html=True)
    if month_df is None or month_df.empty:
        st.markdown('<div style="font-size:.82rem;color:#8b949e;">No items this month.</div>',
                    unsafe_allow_html=True)
        return

    sel = st.selectbox("Item", month_df["title"].tolist(),
                        key="dp_sel", label_visibility="collapsed")
    row  = month_df[month_df["title"] == sel].iloc[0]
    itype = row.get("type","event")
    meta  = row.get("metadata",{}) or {}

    badge_map = {"event":"badge-intl","match":"badge-green",
                 "registration":"badge-yellow","auction":"badge-purple"}
    st.markdown(f"""
    <div style="display:flex;gap:.4rem;margin-bottom:.8rem;">
        <span class="badge {badge_map.get(itype,'badge-blue')}">{itype}</span>
        {"<span class='badge badge-red'>⚠ Conflict</span>"
         if itype=='event' and row.get('id') in conflict_ids else ""}
    </div>""", unsafe_allow_html=True)

    s = row["start_date"].date() if pd.notna(row["start_date"]) else "—"
    e = row["end_date"].date()   if pd.notna(row["end_date"])   else "—"
    for lbl, val in [("Start", str(s)), ("End", str(e))] + [
        (k.title(), str(v)) for k, v in meta.items() if v
    ]:
        st.markdown(
            f'<div class="detail-row">'
            f'<span class="detail-label">{lbl}</span>'
            f'<span class="detail-val">{val}</span></div>',
            unsafe_allow_html=True,
        )


def render() -> None:
    _extra_css()

    st.markdown("""
    <div class="page-header">
        <div><h1>CALENDAR</h1>
        <p>Events · Matches · Registrations · Auctions</p></div>
    </div>""", unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        gender_f   = st.selectbox("Gender",   ["All","Male","Female","Mixed"], key="cf_g")
    with fc2:
        category_f = st.selectbox("Category", ["All","International","Domestic","League"], key="cf_c")
    with fc3:
        type_opts  = ["event","match","registration","auction"]
        type_f     = st.multiselect("Types", type_opts, default=type_opts, key="cf_t")
    with fc4:
        st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

    gender   = None if gender_f   == "All" else gender_f
    category = None if category_f == "All" else category_f

    # ── Load data ──────────────────────────────────────────────
    all_items = load_calendar_items(gender=gender, category=category)
    if not all_items.empty and type_f:
        all_items = all_items[all_items["type"].isin(type_f)].copy()

    # ── Conflict detection (events only) ───────────────────────
    ev_df        = load_events(gender=gender, category=category)
    overlaps     = detect_event_overlaps(ev_df)
    conflict_ids: set = set()
    for o in overlaps:
        for k in ("id_a","id_b","id","Event A id","Event B id"):
            if k in o:
                conflict_ids.add(o[k])

    # ── Year / month selectors ─────────────────────────────────
    today = date.today()
    year_min = today.year
    year_max = today.year + 2
    if not all_items.empty:
        year_min = min(year_min, int(all_items["start_date"].dt.year.min()))
        year_max = max(year_max, int(all_items["end_date"].dt.year.max()))
    year_list = list(range(year_min, year_max+1))

    yc, mc, ic = st.columns([1,1,5])
    with yc:
        def_yi = year_list.index(today.year) if today.year in year_list else 0
        sel_year = st.selectbox("Year", year_list, index=def_yi, key="cal_yr")
    with mc:
        sel_month = st.selectbox("Month", list(range(1,13)), index=today.month-1,
                                  format_func=lambda m: MONTHS[m], key="cal_mo")
    with ic:
        if overlaps:
            st.markdown(
                f'<div style="margin-top:1.6rem;">'
                f'<span class="badge badge-red">⚠ {len(overlaps)} event conflict(s)</span></div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="margin-top:1.6rem;">'
                '<span class="badge badge-green">No conflicts</span></div>',
                unsafe_allow_html=True)

    # ── Month slice ────────────────────────────────────────────
    last_day    = calendar.monthrange(sel_year, sel_month)[1]
    month_start = pd.Timestamp(date(sel_year, sel_month, 1))
    month_end   = pd.Timestamp(date(sel_year, sel_month, last_day))

    month_items = pd.DataFrame()
    if not all_items.empty:
        month_items = all_items[
            (all_items["start_date"] <= month_end) &
            (all_items["end_date"]   >= month_start)
        ].copy()

    # ── Layout: calendar | detail panel ───────────────────────
    cal_col, panel_col = st.columns([4, 1])

    with cal_col:
        st.markdown(f"""
        <div class="gcal-nav">
            <div class="gcal-month-label">{MONTHS[sel_month]} {sel_year}</div>
            <div style="font-size:.78rem;color:#8b949e;">
                {len(month_items)} item(s) this month</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(
            _build_grid(sel_year, sel_month, month_items, conflict_ids),
            unsafe_allow_html=True,
        )
        st.markdown(_legend(), unsafe_allow_html=True)

    with panel_col:
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        _detail_panel(month_items, conflict_ids)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Month list ─────────────────────────────────────────────
    if not month_items.empty:
        st.markdown("---")
        st.markdown(
            f'<div class="card-title">{MONTHS[sel_month]} {sel_year}</div>',
            unsafe_allow_html=True,
        )
        disp = month_items[["type","title","start_date","end_date"]].copy()
        disp["start_date"] = disp["start_date"].dt.date
        disp["end_date"]   = disp["end_date"].dt.date
        disp.columns = ["Type","Title","Start","End"]
        st.dataframe(disp, use_container_width=True, hide_index=True)
