# pages/add_team.py
# ──────────────────────────────────────────────────────────────
#  Add Team — search events instead of dropdown,
#             add multiple teams at once via text area or tags.
# ──────────────────────────────────────────────────────────────

import streamlit as st
from db.operations import load_events, load_teams, add_teams_bulk
from db.auth import can_edit


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <h1>ADD TEAM</h1>
        <p>Assign one or multiple teams to an event</p>
    </div>
    """, unsafe_allow_html=True)

    if not can_edit():
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">🔒</div>
            <div class="body"><div class="title">View-Only Access</div>
            Contact an admin to request edit access.</div>
        </div>""", unsafe_allow_html=True)
        return

    events_df = load_events()
    if events_df.empty:
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">⚠️</div>
            <div class="body">No events found. Add events first.</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Event SEARCH (not dropdown) ────────────────────────
    st.markdown('<div class="card-title">STEP 1 — FIND EVENT</div>', unsafe_allow_html=True)

    event_search = st.text_input(
        "Search for an event",
        placeholder="Type to filter events…",
        key="team_event_search",
    )

    all_names = events_df["event_name"].tolist()
    filtered  = [n for n in all_names if event_search.lower() in n.lower()] \
                if event_search else all_names

    if not filtered:
        st.warning("No events match your search.")
        return

    sel_event = st.radio(
        "Select event",
        options=filtered[:20],        # cap at 20 to avoid overwhelming UI
        key="team_sel_event",
    )

    # Show event details
    ev_row = events_df[events_df["event_name"] == sel_event].iloc[0]
    cat_badge = {"International":"badge-intl","Domestic":"badge-dom","League":"badge-league"}.get(ev_row["category"],"badge-blue")
    st.markdown(f"""
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin:0.5rem 0 1.2rem;">
        <span class="badge {cat_badge}">{ev_row['category']}</span>
        <span class="badge badge-blue">{ev_row['format']}</span>
        <span class="badge badge-yellow">{ev_row['gender']}</span>
        <span style="font-size:0.82rem;color:#8b949e;align-self:center;">
            {ev_row['start_date'].date()} → {ev_row['end_date'].date()} · {ev_row['country']}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card-title">STEP 2 — ADD TEAMS</div>', unsafe_allow_html=True)

    # ── Three input methods ────────────────────────────────
    method = st.radio(
        "How would you like to add teams?",
        ["📝  Type individually", "📋  Paste multiple (one per line)", "🏷️  Comma-separated"],
        horizontal=True,
        key="team_input_method",
    )

    team_names: list[str] = []

    if "📝" in method:
        # Tag-style individual add
        if "team_tags" not in st.session_state:
            st.session_state.team_tags = []

        col_in, col_btn = st.columns([3, 1])
        with col_in:
            new_team = st.text_input("Team name", placeholder="e.g. India, West Indies…",
                                     key="new_team_input")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add"):
                t = new_team.strip()
                if t and t not in st.session_state.team_tags:
                    st.session_state.team_tags.append(t)
                elif t in st.session_state.team_tags:
                    st.warning(f"'{t}' already in the list.")

        if st.session_state.team_tags:
            tags_html = " ".join(
                f'<span style="display:inline-flex;align-items:center;gap:0.3rem;'
                f'background:#161b22;border:1px solid #30363d;border-radius:20px;'
                f'padding:0.2rem 0.7rem;font-size:0.82rem;margin:2px;">'
                f'{t}</span>'
                for t in st.session_state.team_tags
            )
            st.markdown(f'<div style="margin:0.5rem 0;">{tags_html}</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🗑 Clear All", key="clr_tags"):
                    st.session_state.team_tags = []
                    st.rerun()
            team_names = st.session_state.team_tags.copy()

    elif "📋" in method:
        raw = st.text_area(
            "Paste team names (one per line)",
            height=140,
            placeholder="India\nWest Indies\nEngland\nAustralia",
            key="teams_textarea",
        )
        team_names = [t.strip() for t in raw.splitlines() if t.strip()]

    else:   # comma-separated
        raw = st.text_input(
            "Enter team names separated by commas",
            placeholder="India, West Indies, England, Australia",
            key="teams_comma",
        )
        team_names = [t.strip() for t in raw.split(",") if t.strip()]

    # Preview
    if team_names:
        st.markdown(f"""
        <div style="font-size:0.82rem;color:#8b949e;margin:0.6rem 0;">
            Ready to add <b style="color:#f0b429;">{len(team_names)}</b>
            team(s) to <b>{sel_event}</b>:
            {", ".join(f"<b>{t}</b>" for t in team_names[:8])}
            {"…" if len(team_names) > 8 else ""}
        </div>
        """, unsafe_allow_html=True)

        if st.button("💾  Save Teams", use_container_width=True, key="save_teams_btn"):
            ok_count, warns = add_teams_bulk(sel_event, team_names)
            for w in warns: st.warning(w)
            if ok_count:
                st.success(f"✅ {ok_count} team(s) added to **{sel_event}**.")
            if "📝" in method:
                st.session_state.team_tags = []
            st.rerun()

    # ── Existing teams for selected event ─────────────────
    teams_df = load_teams()
    if not teams_df.empty:
        ev_teams = teams_df[teams_df["event_name"] == sel_event]["team_name"].tolist()
        if ev_teams:
            st.markdown(f'<br><div class="card-title">CURRENT TEAMS — {sel_event}</div>',
                        unsafe_allow_html=True)
            cols = st.columns(4)
            for i, t in enumerate(ev_teams):
                cols[i % 4].markdown(f"• **{t}**")
