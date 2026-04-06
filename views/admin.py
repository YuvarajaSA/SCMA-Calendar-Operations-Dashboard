# pages/admin.py  —  SCMA Admin Panel (Phase 7)
import streamlit as st
import pandas as pd
from db.auth import is_admin, current_email, get_supabase_user
from db.operations import (
    get_all_users, update_user_status, update_user_role,
    get_activity_logs, get_all_notifications,
    load_events, load_matches, load_teams,
    delete_event, delete_match, delete_team,
    log_activity,
)


def _confirm_delete(key: str, label: str) -> bool:
    """
    Two-step delete: first click shows warning, second click confirms.
    Returns True only on the confirmation click.
    """
    init_key = f"del_init_{key}"
    conf_key = f"del_conf_{key}"

    if st.session_state.get(conf_key):
        # Already in confirmation state
        st.markdown(f"""
        <div class="alert-box alert-error" style="padding:.6rem .9rem;">
            <div class="icon">⚠</div>
            <div class="body" style="font-size:.82rem;">
                <b>Confirm delete</b> — this cannot be undone.
            </div>
        </div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete", key=f"yes_{key}", use_container_width=True):
                st.session_state.pop(conf_key, None)
                return True
        with c2:
            if st.button("Cancel", key=f"no_{key}", use_container_width=True):
                st.session_state.pop(conf_key, None)
                st.rerun()
        return False

    if st.button(f"Delete {label}", key=f"del_{key}", use_container_width=True):
        st.session_state[conf_key] = True
        st.rerun()
    return False


def _tab_users() -> None:
    all_users = get_all_users()
    if not all_users:
        st.info("No users found.")
        return

    approved = sum(1 for u in all_users if u.get("status") == "approved")
    pending  = sum(1 for u in all_users if u.get("status") == "pending")
    rejected = sum(1 for u in all_users if u.get("status") == "rejected")

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-chip"><div class="val">{len(all_users)}</div><div class="lbl">Total</div></div>
        <div class="stat-chip"><div class="val" style="color:#3fb950;">{approved}</div><div class="lbl">Approved</div></div>
        <div class="stat-chip"><div class="val" style="color:#e3b341;">{pending}</div><div class="lbl">Pending</div></div>
        <div class="stat-chip"><div class="val" style="color:#f85149;">{rejected}</div><div class="lbl">Rejected</div></div>
    </div>""", unsafe_allow_html=True)

    status_f = st.selectbox("Filter status", ["All","approved","pending","rejected"], key="uf")
    filtered = all_users if status_f == "All" else [
        u for u in all_users if u.get("status") == status_f
    ]
    me = current_email()

    for u in filtered:
        status = u.get("status", "pending")
        role   = u.get("role", "viewer")
        is_me  = u.get("email", "") == me
        sc     = {"approved":"#3fb950","pending":"#e3b341","rejected":"#f85149"}.get(status, "#8b949e")
        rc     = {"admin":"role-admin","editor":"role-editor","viewer":"role-viewer"}.get(role, "role-viewer")

        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1.2, 1])
        with c1:
            you = " (you)" if is_me else ""
            st.markdown(
                f'<div style="font-size:.84rem;padding:.3rem 0;"><b>{u.get("name","—")}</b>{you}<br>'
                f'<span style="color:#8b949e;font-size:.74rem;">{u.get("email","")}</span>'
                f'<br><span style="color:#8b949e;font-size:.7rem;">'
                f'TZ: {u.get("timezone","UTC")}</span></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(f'<div style="font-size:.8rem;color:{sc};padding:.5rem 0;">{status}</div>',
                        unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="padding:.5rem 0;"><span class="role-pill {rc}">{role}</span></div>',
                        unsafe_allow_html=True)
        with c4:
            nr = st.selectbox("r", ["viewer","editor","admin"],
                               index=["viewer","editor","admin"].index(role),
                               key=f"nr_{u['id']}", label_visibility="collapsed")
            if st.button("Save", key=f"sv_{u['id']}", use_container_width=True):
                update_user_role(u["id"], nr)
                u_obj = get_supabase_user()
                log_activity(u_obj.id if u_obj else None, me, "update",
                             "profile", details={"target": u.get("email"), "role": nr})
                st.rerun()
        with c5:
            if not is_me:
                if status == "approved":
                    if st.button("Reject", key=f"rj_{u['id']}", use_container_width=True):
                        update_user_status(u["id"], "rejected")
                        st.rerun()
                elif status == "rejected":
                    if st.button("Restore", key=f"rs_{u['id']}", use_container_width=True):
                        update_user_status(u["id"], "approved")
                        st.rerun()
                else:
                    if st.button("Approve", key=f"ap_{u['id']}", use_container_width=True):
                        update_user_status(u["id"], "approved")
                        u_obj = get_supabase_user()
                        log_activity(u_obj.id if u_obj else None, me, "approve",
                                     "profile", details={"target": u.get("email")})
                        st.rerun()

        st.markdown("<hr style='border-color:#1c2128;margin:.15rem 0;'>", unsafe_allow_html=True)


def _tab_data() -> None:
    """Admin: safe delete for events / matches / teams with confirmation."""
    st.markdown('<div class="card-title">DELETE EVENTS</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="alert-box alert-warn">
        <div class="icon">⚠</div>
        <div class="body" style="font-size:.82rem;">
            Deleting an event also removes all linked matches, teams and squad records
            (CASCADE). This cannot be undone.
        </div>
    </div>""", unsafe_allow_html=True)

    ev_df = load_events()
    if ev_df.empty:
        st.info("No events.")
    else:
        for _, row in ev_df.iterrows():
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(
                    f'<div style="font-size:.86rem;padding:.35rem 0;">'
                    f'<b>{row["event_name"]}</b>'
                    f'<span style="color:#8b949e;font-size:.76rem;margin-left:.5rem;">'
                    f'{str(row["start_date"].date()) if hasattr(row["start_date"],"date") else row["start_date"]}'
                    f' → {str(row["end_date"].date()) if hasattr(row["end_date"],"date") else row["end_date"]}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if _confirm_delete(f"ev_{row['id']}", ""):
                    ok, msg = delete_event(int(row["id"]))
                    u_obj = get_supabase_user()
                    log_activity(u_obj.id if u_obj else None, current_email(), "delete",
                                 "event", entity_id=int(row["id"]),
                                 details={"name": row["event_name"]})
                    if ok: st.success(f"Event '{row['event_name']}' deleted."); st.rerun()
                    else:  st.error(msg)

    st.markdown("---")
    st.markdown('<div class="card-title">DELETE MATCHES</div>', unsafe_allow_html=True)
    ma_df = load_matches()
    if ma_df.empty:
        st.info("No matches.")
    else:
        for _, row in ma_df.iterrows():
            c1, c2 = st.columns([4, 1])
            with c1:
                d = row["match_date"].date().isoformat() if hasattr(row["match_date"],"date") else str(row["match_date"])
                st.markdown(
                    f'<div style="font-size:.86rem;padding:.35rem 0;">'
                    f'<b>{row.get("match_name","Match")}</b>'
                    f'<span style="color:#8b949e;font-size:.76rem;margin-left:.5rem;">{d}</span></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if _confirm_delete(f"ma_{row['id']}", ""):
                    ok, msg = delete_match(int(row["id"]))
                    u_obj = get_supabase_user()
                    log_activity(u_obj.id if u_obj else None, current_email(), "delete",
                                 "match", entity_id=int(row["id"]))
                    if ok: st.success("Match deleted."); st.rerun()
                    else:  st.error(msg)

    st.markdown("---")
    st.markdown('<div class="card-title">DELETE TEAMS</div>', unsafe_allow_html=True)
    tm_df = load_teams()
    if tm_df.empty:
        st.info("No teams.")
    else:
        for _, row in tm_df.iterrows():
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(
                    f'<div style="font-size:.86rem;padding:.35rem 0;">'
                    f'<b>{row["team_name"]}</b>'
                    f'<span style="color:#8b949e;font-size:.76rem;margin-left:.5rem;">'
                    f'{row.get("event_name","")}</span></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                tid = row.get("id")
                if tid and _confirm_delete(f"tm_{tid}", ""):
                    ok, msg = delete_team(int(tid))
                    u_obj = get_supabase_user()
                    log_activity(u_obj.id if u_obj else None, current_email(), "delete",
                                 "team", entity_id=int(tid))
                    if ok: st.success("Team deleted."); st.rerun()
                    else:  st.error(msg)


def _tab_activity() -> None:
    logs = get_activity_logs(300)
    if not logs:
        st.info("No activity logged yet.")
        return

    df = pd.DataFrame(logs)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

    c1, c2 = st.columns(2)
    with c1:
        af = st.selectbox("Action", ["All"] + sorted(df["action"].unique().tolist()), key="af")
    with c2:
        ef = st.text_input("Search email", placeholder="user@…", key="ef", label_visibility="collapsed")

    disp = df.copy()
    if af != "All":
        disp = disp[disp["action"] == af]
    if ef.strip():
        disp = disp[disp["user_email"].str.contains(ef.strip(), case=False, na=False)]

    show = disp[["created_at","user_email","action","entity_type","entity_id"]].rename(columns={
        "created_at":"Time","user_email":"User","action":"Action",
        "entity_type":"Entity","entity_id":"ID",
    })
    st.dataframe(show, use_container_width=True, hide_index=True, height=380)
    csv = show.to_csv(index=False)
    st.download_button("Export CSV", csv, "activity_logs.csv", "text/csv", key="exp_logs")


def _tab_notifications() -> None:
    notifs = get_all_notifications(300)
    if not notifs:
        st.info("No notifications yet.")
        return

    df = pd.DataFrame(notifs)
    df["scheduled_at"] = pd.to_datetime(df["scheduled_at"]).dt.strftime("%Y-%m-%d %H:%M")

    p = len(df[df["status"] == "pending"])
    s = len(df[df["status"] == "sent"])
    f = len(df[df["status"] == "failed"])

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-chip"><div class="val" style="color:#e3b341;">{p}</div><div class="lbl">Pending</div></div>
        <div class="stat-chip"><div class="val" style="color:#3fb950;">{s}</div><div class="lbl">Sent</div></div>
        <div class="stat-chip"><div class="val" style="color:#f85149;">{f}</div><div class="lbl">Failed</div></div>
    </div>""", unsafe_allow_html=True)

    sf   = st.selectbox("Filter status", ["All","pending","sent","failed"], key="nf")
    disp = df if sf == "All" else df[df["status"] == sf]

    if not disp.empty:
        show = disp[["scheduled_at","user_email","type","entity_type","status","message"]].rename(columns={
            "scheduled_at":"Scheduled","user_email":"To","type":"Type",
            "entity_type":"Entity","status":"Status","message":"Message",
        })
        st.dataframe(show, use_container_width=True, hide_index=True, height=350)


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>ADMIN</h1>
        <p>Users · Data Management · Activity · Notifications</p></div>
    </div>""", unsafe_allow_html=True)

    if not is_admin():
        st.markdown("""
        <div class="alert-box alert-error">
            <div class="icon">🔒</div>
            <div class="body"><div class="title">Admins Only</div>
            This page is restricted to administrators.</div>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown("""
    <div class="alert-box alert-info" style="margin-bottom:1rem;">
        <div class="icon">ℹ</div>
        <div class="body" style="font-size:.82rem;">
            <b>Admin</b> — full access &nbsp; | &nbsp;
            <b>Editor</b> — add/edit data &nbsp; | &nbsp;
            <b>Viewer</b> — read-only
        </div>
    </div>""", unsafe_allow_html=True)

    tab_u, tab_d, tab_a, tab_n = st.tabs([
        "Users", "Data Management", "Activity Logs", "Notifications"
    ])
    with tab_u: _tab_users()
    with tab_d: _tab_data()
    with tab_a: _tab_activity()
    with tab_n: _tab_notifications()
