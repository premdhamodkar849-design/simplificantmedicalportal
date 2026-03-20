"""styles.py — Single source for all CSS. Call inject_css() once at app start."""
 
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
 
/* ── Reset & Base ─────────────────────────────── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header   { visibility: hidden; }
.block-container             { padding-top: 1.5rem !important; }
 
/* ── Sidebar ──────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c111d 0%, #161b2e 60%, #1a1f35 100%);
    border-right: 1px solid #1e2640;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #1e2640 !important;
    border: 1px solid #2d3a5c !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
}
section[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg,#6366f1,#8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
 
/* ── Role badge ───────────────────────────────── */
.role-badge {
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 14px; border-radius:999px;
    font-size:11px; font-weight:700;
    text-transform:uppercase; letter-spacing:1.5px;
    margin-bottom:4px;
}
.badge-patient { background:#ede9fe; color:#6d28d9; }
.badge-doctor  { background:#d1fae5; color:#065f46; }
.badge-staff   { background:#fef3c7; color:#92400e; }
 
/* ── Page header ──────────────────────────────── */
.page-header { margin-bottom:24px; }
.page-title  { font-size:26px; font-weight:800; color:#0f172a; margin:0 0 4px 0; }
.page-sub    { font-size:14px; color:#64748b; margin:0; }
 
/* ── Card base ────────────────────────────────── */
.card {
    background:#ffffff;
    border:1px solid #e8ecf0;
    border-radius:16px;
    padding:24px;
    box-shadow:0 1px 8px rgba(0,0,0,0.06);
    margin-bottom:16px;
}
 
/* ── Stat mini card ───────────────────────────── */
.stat-card {
    background:#f8fafc;
    border:1px solid #e2e8f0;
    border-radius:12px;
    padding:18px 14px;
    text-align:center;
}
.stat-num   { font-size:38px; font-weight:800; line-height:1.1; }
.stat-label { font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; margin-top:4px; }
 
/* ── Token card ───────────────────────────────── */
.token-card {
    background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a78bfa 100%);
    border-radius:20px; padding:36px; text-align:center; color:white;
    box-shadow:0 16px 50px rgba(99,102,241,0.45);
}
.token-num   { font-size:88px; font-weight:900; line-height:1; letter-spacing:-4px; }
.token-label { font-size:12px; opacity:.75; text-transform:uppercase; letter-spacing:2px; margin-bottom:6px; }
 
/* ── Current patient card ─────────────────────── */
.current-card {
    background:linear-gradient(135deg,#047857 0%,#059669 60%,#10b981 100%);
    border-radius:16px; padding:28px; color:white;
    box-shadow:0 10px 36px rgba(5,150,105,0.38);
    margin-bottom:20px;
}
 
/* ── Queue list item ──────────────────────────── */
.q-item {
    background:#f8fafc; border:1px solid #e2e8f0;
    border-left:4px solid #6366f1; border-radius:10px;
    padding:14px 16px; margin-bottom:8px;
    transition:border-color .15s;
}
.q-item:hover { border-left-color:#8b5cf6; background:#f1f5f9; }
 
/* ── Hospital card (patient) ──────────────────── */
.hosp-card {
    background:white; border:1px solid #e2e8f0;
    border-radius:14px; padding:18px 20px;
    transition:all .2s; cursor:pointer;
    box-shadow:0 1px 6px rgba(0,0,0,0.04);
}
.hosp-card:hover { border-color:#6366f1; box-shadow:0 4px 20px rgba(99,102,241,0.12); }
 
/* ── Bed grid cell ────────────────────────────── */
.bed-free     { background:#22c55e; border-radius:5px; display:inline-block; }
.bed-occupied { background:#ef4444; border-radius:5px; display:inline-block; }
 
/* ── Emergency badge ──────────────────────────── */
.em-alert {
    background:#fff1f2; border:2px solid #fecaca; border-radius:12px;
    padding:14px 18px; color:#b91c1c; font-weight:600; font-size:14px;
    margin-bottom:20px; display:flex; align-items:center; gap:10px;
}
 
/* ── Step dots ────────────────────────────────── */
.step-dot {
    width:30px; height:30px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:700; margin:0 auto 5px auto;
}
.sd-done   { background:#d1fae5; color:#065f46; }
.sd-active { background:#6366f1; color:white; box-shadow:0 0 0 4px rgba(99,102,241,.25); }
.sd-todo   { background:#f1f5f9; color:#94a3b8; }
 
/* ── Button polish ────────────────────────────── */
.stButton > button {
    border-radius:10px !important; font-weight:600 !important; transition:all .18s !important;
}
.stButton > button:hover { transform:translateY(-1px) !important; }
 
/* ── Input polish ─────────────────────────────── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stTextArea textarea,
.stNumberInput input {
    border-radius:10px !important;
}
 
/* ── Progress bar color ───────────────────────── */
.stProgress > div > div > div { background:linear-gradient(90deg,#6366f1,#8b5cf6) !important; }
 
/* ── Divider ──────────────────────────────────── */
hr { border-color:#e8ecf0 !important; margin:18px 0 !important; }
 
/* ── Tab style ────────────────────────────────── */
.stTabs [data-baseweb="tab"] {
    font-weight:600; font-size:13px; padding:10px 18px;
}
.stTabs [aria-selected="true"] { color:#6366f1 !important; }
</style>
"""
 
def inject_css():
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
 