# pages/add_squad.py
import streamlit as st
from db.operations import event_names, teams_for_event, bulk_add_players, load_squad
from db.auth import can_edit


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <h1>SQUAD BUILDER</h1>
        <p>Add players to team squads — queue multiple names and save at once</p>
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

    ev_list = event_names()
    if not ev_list:
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">⚠️</div>
            <div class="body">No events found. Add events and teams first.</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Two-column desktop layout: form | current squad ───
    form_col, squad_col = st.columns([2, 1])

    with form_col:
        c1, c2 = st.columns(2)
        with c1:
            sel_event = st.selectbox("Select Event", ev_list, key="sq_event")
        team_list = teams_for_event(sel_event)
        with c2:
            if team_list:
                sel_team = st.selectbox("Select Team", team_list, key="sq_team")
            else:
                st.warning("No teams for this event yet.")
                sel_team = None

        if not sel_team:
            return

        st.markdown("---")

        queue_key = f"pq_{sel_event}_{sel_team}"
        if queue_key not in st.session_state:
            st.session_state[queue_key] = []

        # Input row
        pi_col, pb_col = st.columns([4, 1])
        with pi_col:
            new_p = st.text_input("Player Name", placeholder="Type name and click ➕",
                                  key="pname_inp")
        with pb_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add"):
                name = new_p.strip()
                if not name:
                    st.error("Enter a name.")
                elif name in st.session_state[queue_key]:
                    st.warning(f"'{name}' already queued.")
                else:
                    st.session_state[queue_key].append(name)
                    st.rerun()

        # Queue
        queue = st.session_state[queue_key]
        if queue:
            st.markdown(f"""
            <div style="font-size:.78rem;font-weight:700;letter-spacing:.1em;
                        text-transform:uppercase;color:#8b949e;margin:.6rem 0 .4rem;">
                Queue — {len(queue)} player(s) for {sel_team}
            </div>""", unsafe_allow_html=True)

            # Show queue as inline tags with remove buttons
            for idx, p in enumerate(queue):
                qc1, qc2 = st.columns([6, 1])
                with qc1:
                    st.markdown(
                        f'<div style="padding:.3rem 0;font-size:.88rem;">'
                        f'<span style="color:#8b949e;">{idx+1}.</span>&nbsp; <b>{p}</b></div>',
                        unsafe_allow_html=True,
                    )
                with qc2:
                    if st.button("✕", key=f"rm_{idx}_{p}"):
                        st.session_state[queue_key].pop(idx)
                        st.rerun()

            s1, s2 = st.columns([3, 1])
            with s1:
                if st.button("💾  Save All to Squad", use_container_width=True):
                    ok_cnt, warns = bulk_add_players(queue, sel_event, sel_team)
                    for w in warns: st.warning(w)
                    if ok_cnt:
                        st.success(f"✅ {ok_cnt} player(s) added.")
                    st.session_state[queue_key] = []
                    st.rerun()
            with s2:
                if st.button("🗑 Clear", use_container_width=True):
                    st.session_state[queue_key] = []
                    st.rerun()
        else:
            st.markdown("""
            <div class="alert-box alert-info" style="margin-top:.8rem;">
                <div class="icon">💡</div>
                <div class="body">Type a player name and click <b>➕ Add</b> to build your queue.</div>
            </div>""", unsafe_allow_html=True)

    with squad_col:
        # Right panel: current squad
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        st.markdown('<div class="detail-panel-title">CURRENT SQUAD</div>', unsafe_allow_html=True)
        squad_df = load_squad()
        if not squad_df.empty and sel_team:
            cur = squad_df[
                (squad_df["event_name"] == sel_event) &
                (squad_df["team"] == sel_team)
            ]
            if not cur.empty:
                for i, p in enumerate(cur["player_name"].tolist(), 1):
                    st.markdown(
                        f'<div style="padding:.28rem 0;font-size:.86rem;'
                        f'border-bottom:1px solid rgba(48,54,61,.4);">'
                        f'<span style="color:#8b949e;">{i}.</span> {p}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div style="font-size:.82rem;color:#8b949e;">No players yet.</div>',
                            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
