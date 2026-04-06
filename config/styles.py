# config/styles.py
import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

:root {
    --bg:#0d1117; --surface:#161b22; --surface2:#1c2128; --surface3:#21262d;
    --border:#30363d; --border2:#3d4450;
    --accent:#f0b429; --green:#3fb950; --danger:#f85149; --warn:#e3b341;
    --blue:#58a6ff; --purple:#bc8cff; --pink:#ff7eb6;
    --muted:#8b949e; --text:#e6edf3; --text-dim:#c9d1d9;
    --radius:10px; --radius-lg:14px;
    --shadow:0 4px 24px rgba(0,0,0,.4); --shadow-sm:0 2px 8px rgba(0,0,0,.3);
    --col-intl:#1a6fb5; --col-intl-txt:#a8d4ff;
    --col-dom:#1a6b3a;  --col-dom-txt:#a8ffcc;
    --col-lg:#6b3a7a;   --col-lg-txt:#e8b8ff;
}

html,body,[class*="css"] { font-family:'DM Sans',sans-serif; background:var(--bg)!important; color:var(--text)!important; font-size:14px; }
.main .block-container    { padding:1.5rem 2.5rem 3rem!important; max-width:1700px!important; }
.block-container          { padding-top:1.5rem!important; }
hr { border-color:var(--border)!important; }

/* SIDEBAR */
section[data-testid="stSidebar"] { background:var(--surface)!important; border-right:1px solid var(--border); min-width:240px!important; }
section[data-testid="stSidebar"] * { color:var(--text)!important; }
section[data-testid="stSidebar"] .stRadio>label { font-size:.63rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; color:var(--muted)!important; padding-left:.2rem; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { display:flex; align-items:center; gap:.5rem; padding:.5rem .85rem; border-radius:8px; margin-bottom:2px; font-size:.88rem; font-weight:500; transition:background .15s; cursor:pointer; }
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background:rgba(240,180,41,.08); }

/* PAGE HEADER */
.page-header { margin-bottom:1.6rem; padding-bottom:1rem; border-bottom:1px solid var(--border); display:flex; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:.5rem; }
.page-header h1 { font-family:'Bebas Neue',sans-serif; font-size:2.6rem; letter-spacing:.05em; color:var(--accent); margin:0; line-height:1; }
.page-header p { font-size:.86rem; color:var(--muted); margin:.25rem 0 0; }

/* CARDS */
.card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); padding:1.4rem; margin-bottom:1.2rem; }
.card-sm { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:1rem; margin-bottom:.8rem; }
.card-title { font-family:'Bebas Neue',sans-serif; font-size:1.15rem; letter-spacing:.07em; color:var(--accent); margin-bottom:.9rem; }
.section-label { font-size:.63rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); margin-bottom:.6rem; display:block; }

/* STAT CHIPS */
.stat-row { display:flex; gap:.8rem; flex-wrap:nowrap; margin-bottom:1.4rem; overflow-x:auto; padding-bottom:4px; }
.stat-chip { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:.9rem 1.3rem; min-width:110px; text-align:center; flex-shrink:0; transition:border-color .15s; }
.stat-chip:hover { border-color:var(--accent); }
.stat-chip .val { font-family:'Bebas Neue',sans-serif; font-size:2.1rem; color:var(--accent); line-height:1; }
.stat-chip .lbl { font-size:.62rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-top:.3rem; }

/* BADGES */
.badge { display:inline-block; padding:.17rem .58rem; border-radius:20px; font-size:.66rem; font-weight:800; letter-spacing:.07em; text-transform:uppercase; white-space:nowrap; }
.badge-red    { background:rgba(248,81,73,.15);  color:var(--danger); border:1px solid rgba(248,81,73,.3);  }
.badge-yellow { background:rgba(240,180,41,.15); color:var(--accent); border:1px solid rgba(240,180,41,.3); }
.badge-green  { background:rgba(63,185,80,.15);  color:var(--green);  border:1px solid rgba(63,185,80,.3);  }
.badge-blue   { background:rgba(88,166,255,.15); color:var(--blue);   border:1px solid rgba(88,166,255,.3); }
.badge-purple { background:rgba(188,140,255,.15);color:var(--purple); border:1px solid rgba(188,140,255,.3);}
.badge-pink   { background:rgba(255,126,182,.15);color:var(--pink);   border:1px solid rgba(255,126,182,.3);}
.badge-intl   { background:rgba(26,111,181,.25); color:var(--col-intl-txt); border:1px solid rgba(26,111,181,.4); }
.badge-dom    { background:rgba(26,107,58,.25);  color:var(--col-dom-txt);  border:1px solid rgba(26,107,58,.4);  }
.badge-league { background:rgba(107,58,122,.25); color:var(--col-lg-txt);   border:1px solid rgba(107,58,122,.4); }

/* ALERT BOXES */
.alert-box { border-radius:var(--radius); padding:.85rem 1.1rem; margin-bottom:.7rem; display:flex; gap:.75rem; align-items:flex-start; }
.alert-error   { background:rgba(248,81,73,.09);  border:1px solid rgba(248,81,73,.35);  }
.alert-warn    { background:rgba(227,179,65,.09); border:1px solid rgba(227,179,65,.35); }
.alert-success { background:rgba(63,185,80,.09);  border:1px solid rgba(63,185,80,.35);  }
.alert-info    { background:rgba(88,166,255,.09); border:1px solid rgba(88,166,255,.35); }
.alert-box .icon  { font-size:1.1rem; flex-shrink:0; margin-top:1px; }
.alert-box .body  { font-size:.85rem; color:var(--text-dim); line-height:1.5; }
.alert-box .title { font-weight:700; color:var(--text); margin-bottom:.15rem; }

/* PRIORITY CHIPS */
.p-chip { display:inline-block; font-size:.58rem; font-weight:900; letter-spacing:.12em; text-transform:uppercase; padding:.15rem .5rem; border-radius:20px; margin-right:.5rem; vertical-align:middle; }
.p1 { background:var(--danger);color:#fff; }
.p2 { background:var(--warn);color:#0d1117; }
.p3 { background:var(--blue);color:#0d1117; }

/* RIGHT DETAIL PANEL */
.detail-panel { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); padding:1.2rem; position:sticky; top:1rem; }
.detail-panel-title { font-family:'Bebas Neue',sans-serif; font-size:1.1rem; letter-spacing:.06em; color:var(--accent); margin-bottom:1rem; padding-bottom:.6rem; border-bottom:1px solid var(--border); }
.detail-row { display:flex; justify-content:space-between; align-items:flex-start; padding:.4rem 0; border-bottom:1px solid rgba(48,54,61,.5); font-size:.84rem; }
.detail-row:last-child { border-bottom:none; }
.detail-label { color:var(--muted); font-size:.78rem; font-weight:600; flex-shrink:0; margin-right:.6rem; }
.detail-val   { color:var(--text); font-weight:500; text-align:right; }

/* TIMELINE */
.tl-row { display:grid; grid-template-columns:2.4fr 1.2fr .9fr 1.1fr 1.1fr 1.4fr; gap:.4rem; align-items:center; padding:.6rem 1rem; border-radius:8px; margin-bottom:3px; font-size:.83rem; border:1px solid var(--border); }
.tl-row.tl-header { background:rgba(240,180,41,.05); font-size:.64rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); border-color:transparent; }
.tl-row.tl-overlap { background:rgba(248,81,73,.08);  border-color:rgba(248,81,73,.3);  }
.tl-row.tl-tight   { background:rgba(227,179,65,.08); border-color:rgba(227,179,65,.3); }
.tl-row.tl-normal  { background:var(--surface); }
.tl-row.tl-normal:hover { background:var(--surface2); }

/* GOOGLE CALENDAR */
.gcal-wrapper { width:100%; }
.gcal-nav { display:flex; align-items:center; gap:1rem; margin-bottom:.8rem; flex-wrap:wrap; }
.gcal-month-label { font-family:'Bebas Neue',sans-serif; font-size:1.9rem; letter-spacing:.05em; color:var(--text); flex-shrink:0; }
.gcal-dow-row { display:grid; grid-template-columns:repeat(7,1fr); gap:2px; margin-bottom:2px; border-bottom:1px solid var(--border); padding-bottom:4px; }
.gcal-dow-cell { text-align:center; font-size:.62rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); padding:.3rem 0; }
.gcal-dow-cell.weekend { color:rgba(139,148,158,.5); }
.gcal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:2px; }

/* Calendar cells — desktop-first height */
.gcal-cell { background:var(--surface); border:1px solid var(--border); border-radius:6px; min-height:125px; padding:.35rem .42rem; overflow:hidden; transition:border-color .12s,background .12s; cursor:pointer; }
.gcal-cell:hover { border-color:var(--border2); background:var(--surface2); }
.gcal-cell.gcal-today   { border-color:var(--accent)!important; background:rgba(240,180,41,.04); }
.gcal-cell.gcal-other   { background:var(--bg); opacity:.52; }
.gcal-cell.gcal-weekend { background:rgba(13,17,23,.45); }
.gcal-cell.has-conflict { border-color:rgba(248,81,73,.5)!important; }

.gcal-day-num { font-size:.76rem; font-weight:700; color:var(--muted); display:flex; justify-content:flex-end; margin-bottom:.22rem; }
.gcal-today-circle { background:var(--accent); color:#0d1117; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:.7rem; font-weight:900; }

/* Event pills — show rich info on desktop */
.gcal-pill { font-size:.67rem; font-weight:600; line-height:1.25; padding:.22rem .45rem; border-radius:4px; margin-bottom:2px; overflow:hidden; cursor:pointer; display:block; transition:opacity .12s,transform .1s; border-left-width:3px; border-left-style:solid; }
.gcal-pill:hover { opacity:.85; transform:translateX(1px); }
.gcal-pill-name  { font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.gcal-pill-meta  { font-size:.59rem; opacity:.82; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-top:1px; }
.gcal-pill-teams { font-size:.57rem; opacity:.7; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

.pill-intl   { background:rgba(26,111,181,.85);  color:var(--col-intl-txt); border-left-color:#4da6ff; }
.pill-dom    { background:rgba(26,107,58,.85);   color:var(--col-dom-txt);  border-left-color:#4dff7c; }
.pill-league { background:rgba(107,58,122,.85);  color:var(--col-lg-txt);   border-left-color:#cc88ff; }
.pill-female { border-left-color:var(--pink)!important; }
.pill-conflict { outline:1px solid var(--danger); outline-offset:1px; }

.gcal-more { font-size:.62rem; color:var(--muted); cursor:pointer; padding:1px 3px; border-radius:3px; display:block; line-height:1.5; }
.gcal-more:hover { color:var(--accent); background:rgba(240,180,41,.1); }

.gcal-legend { display:flex; gap:1.2rem; flex-wrap:wrap; margin-top:.8rem; padding-top:.6rem; border-top:1px solid var(--border); }
.gcal-legend-item { display:flex; align-items:center; gap:.35rem; font-size:.72rem; color:var(--muted); white-space:nowrap; }
.gcal-legend-dot  { width:10px; height:10px; border-radius:2px; flex-shrink:0; }

/* MINI CALENDAR (search) */
.mini-cal { display:grid; grid-template-columns:repeat(7,1fr); gap:1px; background:var(--border); border-radius:6px; overflow:hidden; font-family:'DM Mono',monospace; }
.mini-cal-dow { background:var(--surface2); font-size:.55rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); text-align:center; padding:3px 0; }
.mini-cal-day { background:var(--surface); font-size:.68rem; text-align:center; padding:4px 2px; color:var(--muted); }
.mini-cal-day.in-event  { background:rgba(240,180,41,.18); color:var(--accent); font-weight:700; }
.mini-cal-day.today-day { outline:1px solid var(--accent); outline-offset:-1px; border-radius:3px; }
.mini-cal-day.empty     { background:var(--bg); }

/* STREAMLIT OVERRIDES */
.stTextInput input,.stSelectbox select,.stDateInput input,.stTextArea textarea,.stNumberInput input {
    background:var(--surface2)!important; border:1px solid var(--border)!important;
    border-radius:8px!important; color:var(--text)!important;
    font-family:'DM Sans',sans-serif!important; font-size:.88rem!important;
}
.stTextInput input:focus { border-color:var(--accent)!important; box-shadow:0 0 0 2px rgba(240,180,41,.15)!important; }
.stButton>button { background:var(--accent)!important; color:#0d1117!important; border:none!important; border-radius:8px!important; font-weight:700!important; font-family:'DM Sans',sans-serif!important; font-size:.88rem!important; padding:.5rem 1.3rem!important; transition:opacity .15s,transform .1s!important; letter-spacing:.03em!important; }
.stButton>button:hover { opacity:.85!important; transform:translateY(-1px)!important; }
.stButton>button[kind="secondary"] { background:var(--surface2)!important; color:var(--text)!important; border:1px solid var(--border)!important; }
.stButton>button[kind="secondary"]:hover { border-color:var(--accent)!important; color:var(--accent)!important; }
div[data-testid="stExpander"] { background:var(--surface)!important; border:1px solid var(--border)!important; border-radius:var(--radius)!important; }
div[data-testid="stExpander"]:hover { border-color:var(--border2)!important; }
div[data-testid="stExpander"] summary { font-weight:600!important; }
.stDataFrame { border-radius:var(--radius)!important; overflow:hidden; }
.stDataFrame thead tr th { background:rgba(240,180,41,.07)!important; color:var(--muted)!important; font-size:.64rem!important; letter-spacing:.09em!important; text-transform:uppercase!important; padding:.6rem .8rem!important; }
.stDataFrame tbody tr:hover td { background:rgba(255,255,255,.03)!important; }
.stTabs [data-baseweb="tab-list"] { gap:.3rem; border-bottom:1px solid var(--border)!important; }
.stTabs [data-baseweb="tab"] { background:transparent!important; border:none!important; color:var(--muted)!important; font-weight:700!important; font-size:.86rem!important; border-radius:6px 6px 0 0!important; padding:.5rem 1.1rem!important; }
.stTabs [aria-selected="true"] { color:var(--accent)!important; background:rgba(240,180,41,.07)!important; border-bottom:2px solid var(--accent)!important; }
label { color:var(--text-dim)!important; font-size:.84rem!important; font-weight:500!important; }
div[data-testid="stForm"] { background:var(--surface2)!important; border:1px solid var(--border)!important; border-radius:var(--radius-lg)!important; padding:1.4rem!important; }

/* LOGIN */
.login-box { width:420px; background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:2.5rem; box-shadow:var(--shadow); }
.login-logo { font-family:'Bebas Neue',sans-serif; font-size:2.8rem; color:var(--accent); letter-spacing:.06em; text-align:center; line-height:1; margin-bottom:.2rem; }
.login-sub  { font-size:.82rem; color:var(--muted); text-align:center; margin-bottom:2rem; line-height:1.5; }

/* ROLE PILLS */
.role-pill { display:inline-flex; align-items:center; gap:.35rem; padding:.22rem .7rem; border-radius:20px; font-size:.68rem; font-weight:800; letter-spacing:.07em; text-transform:uppercase; }
.role-admin  { background:rgba(248,81,73,.15); color:var(--danger); border:1px solid rgba(248,81,73,.3);  }
.role-editor { background:rgba(240,180,41,.15);color:var(--accent); border:1px solid rgba(240,180,41,.3); }
.role-viewer { background:rgba(88,166,255,.15);color:var(--blue);   border:1px solid rgba(88,166,255,.3); }

/* RESPONSIVE */
@media(max-width:1279px) {
    .main .block-container { padding:1.2rem 1.4rem 2rem!important; }
    .gcal-cell { min-height:90px; }
    .gcal-pill-meta,.gcal-pill-teams { display:none; }
    .stat-row { flex-wrap:wrap; }
}
@media(max-width:767px) {
    .main .block-container { padding:.8rem .8rem 2rem!important; }
    .page-header h1 { font-size:1.9rem; }
    .gcal-cell { min-height:55px; padding:.18rem; }
    .gcal-pill-meta,.gcal-pill-teams { display:none; }
    .gcal-pill-name { font-size:.58rem; }
    .gcal-pill { padding:.12rem .28rem; border-left-width:2px; }
    .stat-chip { min-width:80px; padding:.7rem .8rem; }
    .stat-chip .val { font-size:1.5rem; }
    .tl-row { grid-template-columns:2fr 1fr 1fr; font-size:.76rem; }
    .tl-row>span:nth-child(3),.tl-row>span:nth-child(5) { display:none; }
    .detail-panel { position:static; }
}
@media(min-width:1600px) {
    .gcal-cell { min-height:148px; }
    .gcal-pill { font-size:.72rem; padding:.27rem .52rem; }
}
"""


def inject() -> None:
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
