# config/styles.py
import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    /* Premium Deep Zinc/Noir Palette */
    --bg: #09090b; 
    --surface: #121214; 
    --surface2: #18181b; 
    --surface3: #27272a;
    
    /* Ultra-subtle borders */
    --border: rgba(255, 255, 255, 0.08); 
    --border2: rgba(255, 255, 255, 0.12);
    --border-hover: rgba(255, 255, 255, 0.2);
    
    /* Sophisticated Accents (Indigo/Violet base) */
    --accent: #818cf8; 
    --accent-glow: rgba(129, 140, 248, 0.15);
    --green: #34d399; --danger: #f87171; --warn: #fbbf24;
    --blue: #60a5fa; --purple: #a78bfa; --pink: #f472b6;
    
    /* Refined Text */
    --text: #f4f4f5; 
    --text-dim: #a1a1aa; 
    --muted: #71717a;
    
    /* Premium Geometry */
    --radius: 12px; 
    --radius-lg: 16px;
    --shadow: 0 4px 24px rgba(0,0,0,0.4); 
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.2);
    --shadow-premium: 0 10px 40px -10px rgba(0,0,0,0.5);
    
    /* App Specific */
    --col-intl: #3b82f6; --col-intl-txt: #bfdbfe;
    --col-dom: #10b981;  --col-dom-txt: #a7f3d0;
    --col-lg: #8b5cf6;   --col-lg-txt: #ddd6fe;
    --active: #f87171; 
    --active-bg: rgba(248, 113, 113, 0.1);
}

/* GLOBAL TYPOGRAPHY & LAYOUT */
html, body, [class*="css"] { 
    font-family: 'Inter', sans-serif; 
    background: var(--bg) !important; 
    color: var(--text) !important; 
    font-size: 14px; 
    -webkit-font-smoothing: antialiased;
}
.main .block-container { padding: 2rem 2.5rem 3rem !important; max-width: 100% !important; }
hr { border-color: var(--border) !important; }

/* STREAMLIT SIDEBAR */
section[data-testid="stSidebar"] { 
    background: var(--surface) !important; 
    border-right: 1px solid var(--border); 
}
section[data-testid="stSidebar"] .stRadio>label { 
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted) !important; 
}

/* SIDEBAR NAVIGATION BUTTONS */
section[data-testid="stSidebar"] .stButton>button {
    background: transparent !important; color: var(--text-dim) !important;
    border: none !important; border-radius: 8px !important;
    font-size: 0.88rem !important; font-weight: 500 !important;
    padding: 0.5rem 0.8rem !important; text-align: left !important; justify-content: flex-start !important;
    transition: all 0.2s ease !important;
}
section[data-testid="stSidebar"] .stButton>button:hover {
    background: var(--surface3) !important; color: var(--text) !important;
}
section[data-testid="stSidebar"] .stButton>button[kind="primary"] {
    background: var(--accent-glow) !important; color: var(--accent) !important;
    border-left: 3px solid var(--accent) !important; font-weight: 600 !important;
}

/* PAGE HEADER (Gradient Text for Premium Feel) */
.page-header { 
    margin-bottom: 2rem; padding-bottom: 1.5rem; 
    border-bottom: 1px solid var(--border); 
    display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; 
}
.page-header h1 { 
    font-family: 'Plus Jakarta Sans', sans-serif; 
    font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; 
    background: linear-gradient(135deg, #ffffff 0%, #a1a1aa 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; line-height: 1.2; 
}
.page-header p { font-size: 0.95rem; color: var(--muted); margin: 0.4rem 0 0; }

/* CARDS & CONTAINERS */
.card { 
    background: var(--surface); border: 1px solid var(--border); 
    border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;
    box-shadow: var(--shadow-sm); transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.card:hover { transform: translateY(-2px); box-shadow: var(--shadow-premium); border-color: var(--border-hover); }
.card-sm { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.2rem; margin-bottom: 1rem; }
.card-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.1rem; font-weight: 600; color: var(--text); margin-bottom: 1rem; }

/* STAT CHIPS */
.stat-row { display: flex; gap: 1rem; flex-wrap: nowrap; margin-bottom: 1.5rem; overflow-x: auto; padding-bottom: 8px; }
.stat-chip { 
    background: linear-gradient(180deg, var(--surface2) 0%, var(--surface) 100%);
    border: 1px solid var(--border); border-radius: var(--radius); 
    padding: 1.2rem 1.5rem; min-width: 140px; flex-shrink: 0; 
    transition: all 0.2s ease; box-shadow: var(--shadow-sm);
}
.stat-chip:hover { border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 8px 20px var(--accent-glow); }
.stat-chip .val { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2rem; font-weight: 700; color: var(--text); line-height: 1; }
.stat-chip .lbl { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); margin-top: 0.5rem; }

/* BADGES (Softer, sleeker) */
.badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.65rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; white-space: nowrap; }
.badge-red    { background: rgba(248,113,113,0.1); color: var(--danger); border: 1px solid rgba(248,113,113,0.2); }
.badge-yellow { background: rgba(251,191,36,0.1);  color: var(--warn);   border: 1px solid rgba(251,191,36,0.2); }
.badge-green  { background: rgba(52,211,153,0.1);  color: var(--green);  border: 1px solid rgba(52,211,153,0.2); }
.badge-blue   { background: rgba(96,165,250,0.1);  color: var(--blue);   border: 1px solid rgba(96,165,250,0.2); }

/* RIGHT DETAIL PANEL */
.detail-panel { background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem; position: sticky; top: 1.5rem; }
.detail-panel-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 1.2rem; padding-bottom: 0.8rem; border-bottom: 1px solid var(--border); }
.detail-row { display: flex; justify-content: space-between; padding: 0.6rem 0; border-bottom: 1px dashed var(--border); font-size: 0.85rem; }
.detail-row:last-child { border-bottom: none; }
.detail-label { color: var(--muted); font-weight: 500; }
.detail-val   { color: var(--text); font-weight: 600; }

/* TIMELINE */
.tl-row { display: grid; grid-template-columns: 2.4fr 1.2fr 0.9fr 1.1fr 1.1fr 1.4fr; gap: 0.5rem; align-items: center; padding: 0.8rem 1rem; border-radius: 8px; margin-bottom: 4px; font-size: 0.85rem; border: 1px solid transparent; transition: background 0.2s; }
.tl-row.tl-header { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--border); border-radius: 0; padding-bottom: 0.5rem; margin-bottom: 0.8rem; }
.tl-row.tl-normal { background: var(--surface); border: 1px solid var(--border); }
.tl-row.tl-normal:hover { background: var(--surface2); border-color: var(--border-hover); }

/* GOOGLE CALENDAR OVERHAUL */
.gcal-wrapper { width: 100%; }
.gcal-month-label { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.5rem; font-weight: 700; color: var(--text); margin-bottom: 1rem; }
.gcal-dow-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 8px; }
.gcal-dow-cell { text-align: center; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; color: var(--muted); padding: 0.5rem 0; }
.gcal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }

.gcal-cell { 
    background: var(--surface); border: 1px solid var(--border); 
    border-radius: 8px; min-height: 120px; padding: 0.5rem; 
    transition: all 0.2s ease; cursor: pointer; 
}
.gcal-cell:hover { border-color: var(--accent); background: var(--surface2); box-shadow: var(--shadow-sm); }
.gcal-cell.gcal-today { border-color: var(--accent) !important; background: var(--accent-glow); }
.gcal-day-num { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.8rem; font-weight: 600; color: var(--text-dim); display: flex; justify-content: flex-end; margin-bottom: 0.5rem; }
.gcal-today-circle { background: var(--accent); color: #fff; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; box-shadow: 0 0 10px var(--accent-glow); }

.gcal-pill { 
    font-size: 0.7rem; font-weight: 500; padding: 0.3rem 0.5rem; 
    border-radius: 4px; margin-bottom: 4px; cursor: pointer; 
    border-left: 2px solid transparent; background: var(--surface3); color: var(--text);
    transition: transform 0.15s ease, opacity 0.15s; 
}
.gcal-pill:hover { transform: translateX(2px); opacity: 0.9; }

/* STREAMLIT NATIVE ELEMENT OVERRIDES */
.stTextInput input, .stSelectbox select, .stDateInput input, .stTextArea textarea, .stNumberInput input {
    background: var(--surface) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important;
    font-size: 0.9rem !important; transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.stTextInput input:focus, .stSelectbox select:focus { 
    border-color: var(--accent) !important; 
    box-shadow: 0 0 0 3px var(--accent-glow) !important; 
}
.stButton>button { 
    background: var(--accent) !important; color: #fff !important; 
    border: none !important; border-radius: 8px !important; 
    font-weight: 600 !important; font-size: 0.9rem !important; 
    padding: 0.5rem 1.5rem !important; transition: all 0.2s ease !important; 
}
.stButton>button:hover { 
    background: #6366f1 !important; /* Slightly darker indigo */
    transform: translateY(-1px) !important; box-shadow: 0 4px 12px var(--accent-glow) !important; 
}
.stButton>button[kind="secondary"] { 
    background: var(--surface2) !important; color: var(--text) !important; border: 1px solid var(--border) !important; 
}
.stButton>button[kind="secondary"]:hover { 
    border-color: var(--border-hover) !important; background: var(--surface3) !important; box-shadow: none !important;
}

div[data-testid="stForm"] { 
    background: var(--surface) !important; border: 1px solid var(--border) !important; 
    border-radius: var(--radius-lg) !important; padding: 2rem !important; 
    box-shadow: var(--shadow-sm) !important;
}

/* LOGIN BOX */
.login-box { 
    width: 100%; max-width: 400px; margin: 0 auto;
    background: var(--surface); border: 1px solid var(--border); 
    border-radius: var(--radius-lg); padding: 3rem 2.5rem; 
    box-shadow: var(--shadow-premium); backdrop-filter: blur(10px);
}
.login-logo { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2rem; font-weight: 800; color: var(--text); text-align: center; margin-bottom: 0.5rem; letter-spacing: -0.02em; }
.login-sub  { font-size: 0.9rem; color: var(--muted); text-align: center; margin-bottom: 2.5rem; }

"""

def inject() -> None:
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)