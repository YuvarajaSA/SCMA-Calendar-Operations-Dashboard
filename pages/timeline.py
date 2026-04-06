# pages/timeline.py
import streamlit as st
import pandas as pd
from db.operations import load_squad
from utils.analysis import gap_analysis, player_workload, workload_badge_class


def render() -> None:
    st.markdown("""
    <div class="page-header">
        <h1>PLAYER TIMELINE</h1>
        <p>Full event schedule · gap analysis · workload scoring</p>
    </div>
    """, unsafe_allow_html=True)

    squad_df = load_squad()
    if squad_df.empty:
        st.markdown("""
        <div class="alert-box alert-warn">
            <div class="icon">⚠️</div>
            <div class="body">No squad data found. Add players via <b>👥 Add Squad</b>.</div>
        </div>""", unsafe_allow_html=True)
        return

    all_players = sorted(squad_df["player_name"].unique().tolist())

    # ── Desktop: selector + badges in one row ─────────────
    sel_col, wl_col = st.columns([2, 3])
    with sel_col:
        sel_player = st.selectbox("Select Player", all_players)

    if not sel_player:
        return

    result     = gap_analysis(squad_df, sel_player)
    cnt, level = player_workload(squad_df, sel_player)
    badge_cls  = workload_badge_class(level)

    with wl_col:
        st.markdown(f"""
        <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;margin-top:1.6rem;">
            <div>
                <span style="font-size:.65rem;font-weight:800;letter-spacing:.1em;
                             text-transform:uppercase;color:#8b949e;">Workload (30d)&nbsp;</span>
                <span class="badge {badge_cls}">{level}</span>
            </div>
            <div>
                <span style="font-size:.65rem;font-weight:800;letter-spacing:.1em;
                             text-transform:uppercase;color:#8b949e;">Events in window&nbsp;</span>
                <span class="badge badge-blue">{cnt}</span>
            </div>
            <div>
                <span style="font-size:.65rem;font-weight:800;letter-spacing:.1em;
                             text-transform:uppercase;color:#8b949e;">Total events&nbsp;</span>
                <span class="badge badge-blue">{len(result)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Timeline + summary panel side by side ──────────────
    tl_col, summary_col = st.columns([3, 1])

    with tl_col:
        st.markdown("""
        <div class="tl-row tl-header">
            <span>Event</span><span>Team</span><span>Format</span>
            <span>Start</span><span>End</span><span>Gap / Status</span>
        </div>""", unsafe_allow_html=True)

        for _, row in result.iterrows():
            gs   = row.get("gap_status","—") or "—"
            gd   = row.get("gap_days", None)
            gd_s = f"{int(gd)}d" if gd is not None else "—"
            cls  = ("tl-overlap" if "Overlap" in str(gs)
                    else "tl-tight" if ("Tight" in str(gs) or "Back" in str(gs))
                    else "tl-normal")
            gap_display = f"{gs} ({gd_s})" if gd is not None else gs

            st.markdown(f"""
            <div class="tl-row {cls}">
                <span><b>{row['event_name']}</b></span>
                <span>{row['team']}</span>
                <span>{row['format']}</span>
                <span>{row['start_date'].date()}</span>
                <span>{row['end_date'].date()}</span>
                <span>{gap_display}</span>
            </div>""", unsafe_allow_html=True)

        # Legend
        st.markdown("""
        <div style="display:flex;gap:1rem;margin-top:.8rem;flex-wrap:wrap;">
            <span class="badge badge-red">🔴 Overlap</span>
            <span class="badge badge-yellow">🟠 Back-to-Back · 🟡 Tight (≤7d)</span>
            <span class="badge badge-green">🟢 OK (&gt;7d)</span>
        </div>""", unsafe_allow_html=True)

    with summary_col:
        # Summary stats panel
        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
        st.markdown('<div class="detail-panel-title">SUMMARY</div>', unsafe_allow_html=True)

        if not result.empty:
            gaps = result["gap_days"].dropna()
            overlaps   = (result["gap_status"].str.contains("Overlap", na=False)).sum()
            tight_gaps = (result["gap_status"].str.contains("Tight|Back", na=False)).sum()
            ok_gaps    = (result["gap_status"] == "🟢 OK").sum()

            for lbl, val, color in [
                ("Total Events", len(result), "var(--accent)"),
                ("Overlaps",     overlaps,    "var(--danger)" if overlaps else "var(--green)"),
                ("Tight Gaps",   tight_gaps,  "var(--warn)"   if tight_gaps else "var(--green)"),
                ("OK Gaps",      ok_gaps,     "var(--green)"),
                ("Avg Gap (days)", f"{gaps.mean():.1f}" if len(gaps) else "—", "var(--blue)"),
            ]:
                st.markdown(
                    f'<div class="detail-row"><span class="detail-label">{lbl}</span>'
                    f'<span class="detail-val" style="color:{color};font-weight:700;">'
                    f'{val}</span></div>',
                    unsafe_allow_html=True,
                )

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Full gap table ──────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="card-title">GAP ANALYSIS TABLE</div>', unsafe_allow_html=True)
    out = result[["event_name","team","format","start_date","end_date","gap_days","gap_status"]].copy()
    out["start_date"] = out["start_date"].dt.date
    out["end_date"]   = out["end_date"].dt.date
    out.columns = ["Event","Team","Format","Start","End","Gap Days","Status"]
    st.dataframe(out, use_container_width=True, hide_index=True)
