# pages/admin.py  —  SCMA Admin Panel
import streamlit as st
import pandas as pd
from db.auth import is_admin, current_email
from db.operations import (
    get_all_users, update_user_status, update_user_role,
    get_activity_logs, get_all_notifications,
)


def _tab_users() -> None:
    all_users = get_all_users()
    if not all_users:
        st.info("No users found.")
        return

    approved = sum(1 for u in all_users if u.get("status")=="approved")
    pending  = sum(1 for u in all_users if u.get("status")=="pending")
    rejected = sum(1 for u in all_users if u.get("status")=="rejected")

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-chip"><div class="val">{len(all_users)}</div><div class="lbl">Total</div></div>
        <div class="stat-chip"><div class="val" style="color:#3fb950;">{approved}</div><div class="lbl">Approved</div></div>
        <div class="stat-chip"><div class="val" style="color:#e3b341;">{pending}</div><div class="lbl">Pending</div></div>
        <div class="stat-chip"><div class="val" style="color:#f85149;">{rejected}</div><div class="lbl">Rejected</div></div>
    </div>""", unsafe_allow_html=True)

    status_f = st.selectbox("Filter status",["All","approved","pending","rejected"],key="uf")
    filtered = all_users if status_f=="All" else [u for u in all_users if u.get("status")==status_f]
    me = current_email()

    for u in filtered:
        status  = u.get("status","pending")
        role    = u.get("role","viewer")
        is_me   = u.get("email","") == me
        sc      = {"approved":"#3fb950","pending":"#e3b341","rejected":"#f85149"}.get(status,"#8b949e")
        rc      = {"admin":"role-admin","editor":"role-editor","viewer":"role-viewer"}.get(role,"role-viewer")

        c1,c2,c3,c4,c5 = st.columns([2.5,1,1,1,1])
        with c1:
            you = " (you)" if is_me else ""
            st.markdown(
                f'<div style="font-size:.84rem;padding:.3rem 0;"><b>{u.get("name","—")}</b>{you}<br>'
                f'<span style="color:#8b949e;font-size:.74rem;">{u.get("email","")}</span></div>',
                unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div style="font-size:.8rem;color:{sc};padding:.5rem 0;">{status}</div>',
                        unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="padding:.5rem 0;"><span class="role-pill {rc}">{role}</span></div>',
                        unsafe_allow_html=True)
        with c4:
            nr = st.selectbox("r",["viewer","editor","admin"],
                               index=["viewer","editor","admin"].index(role),
                               key=f"nr_{u['id']}", label_visibility="collapsed")
            if st.button("Save",key=f"sv_{u['id']}",use_container_width=True):
                update_user_role(u["id"],nr); st.rerun()
        with c5:
            if not is_me:
                if status=="approved":
                    if st.button("Reject",key=f"rj_{u['id']}",use_container_width=True):
                        update_user_status(u["id"],"rejected"); st.rerun()
                elif status=="rejected":
                    if st.button("Restore",key=f"rs_{u['id']}",use_container_width=True):
                        update_user_status(u["id"],"approved"); st.rerun()
                else:
                    if st.button("Approve",key=f"ap_{u['id']}",use_container_width=True):
                        update_user_status(u["id"],"approved"); st.rerun()
        st.markdown("<hr style='border-color:#1c2128;margin:.15rem 0;'>", unsafe_allow_html=True)


def _tab_activity() -> None:
    logs = get_activity_logs(300)
    if not logs:
        st.info("No activity logged yet.")
        return
    df = pd.DataFrame(logs)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

    c1,c2 = st.columns(2)
    with c1:
        af = st.selectbox("Action",["All"]+sorted(df["action"].unique().tolist()),key="af")
    with c2:
        ef = st.text_input("Email filter",placeholder="Search…",key="ef",label_visibility="collapsed")

    disp = df.copy()
    if af!="All":  disp = disp[disp["action"]==af]
    if ef.strip(): disp = disp[disp["user_email"].str.contains(ef.strip(),case=False,na=False)]

    show = disp[["created_at","user_email","action","entity_type","entity_id"]].rename(columns={
        "created_at":"Time","user_email":"User","action":"Action",
        "entity_type":"Entity","entity_id":"ID"
    })
    st.dataframe(show,use_container_width=True,hide_index=True)
    csv = show.to_csv(index=False)
    st.download_button("Export CSV",csv,"activity_logs.csv","text/csv",key="exp_logs")


def _tab_notifications() -> None:
    notifs = get_all_notifications(300)
    if not notifs:
        st.info("No notifications yet.")
        return
    df = pd.DataFrame(notifs)
    df["scheduled_at"] = pd.to_datetime(df["scheduled_at"]).dt.strftime("%Y-%m-%d %H:%M")

    sf  = st.selectbox("Status",["All","pending","sent","failed"],key="nf")
    disp = df if sf=="All" else df[df["status"]==sf]

    p = len(df[df["status"]=="pending"])
    s = len(df[df["status"]=="sent"])
    f = len(df[df["status"]=="failed"])
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-chip"><div class="val" style="color:#e3b341;">{p}</div><div class="lbl">Pending</div></div>
        <div class="stat-chip"><div class="val" style="color:#3fb950;">{s}</div><div class="lbl">Sent</div></div>
        <div class="stat-chip"><div class="val" style="color:#f85149;">{f}</div><div class="lbl">Failed</div></div>
    </div>""", unsafe_allow_html=True)

    if not disp.empty:
        show = disp[["scheduled_at","user_email","type","entity_type","status","message"]].rename(columns={
            "scheduled_at":"Scheduled","user_email":"To","type":"Type",
            "entity_type":"Entity","status":"Status","message":"Message"
        })
        st.dataframe(show,use_container_width=True,hide_index=True)


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <div><h1>ADMIN</h1><p>Users · Activity · Notifications</p></div>
    </div>""", unsafe_allow_html=True)

    if not is_admin():
        st.markdown("""
        <div class="alert-box alert-error">
            <div class="icon">🔒</div>
            <div class="body"><div class="title">Admins Only</div></div>
        </div>""", unsafe_allow_html=True)
        return

    tab_u,tab_a,tab_n = st.tabs(["Users","Activity Logs","Notifications"])
    with tab_u: _tab_users()
    with tab_a: _tab_activity()
    with tab_n: _tab_notifications()
