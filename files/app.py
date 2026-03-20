"""
app.py — Entry point for MediQueue Hospital Management System.
 
Responsibilities:
  1. Page config
  2. CSS injection
  3. Session state bootstrap
  4. Sidebar (role switcher + auth)
  5. Route to patient_ui / doctor_ui / staff_ui
"""
 
import streamlit as st
from config import init_state, DOCTOR_CREDS, STAFF_CREDS, HOSPITALS, get_queue, total_available_beds, _ensure_ward_format
from database import verify_credential
from styles import inject_css
 
# ── Must be first Streamlit call ──────────────────────────────
st.set_page_config(
    page_title="MediQueue | Hospital System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
inject_css()
init_state()
 
# ── Lazy imports (avoid circular at top) ────────────────────
import patient_ui
import doctor_ui
import staff_ui
 
 
# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        # Brand
        st.markdown("""
        <div style="text-align:center;padding:22px 0 14px 0;">
            <div style="font-size:42px;">🏥</div>
            <div style="font-size:19px;font-weight:800;color:#f1f5f9;letter-spacing:-0.5px;">MediQueue</div>
            <div style="font-size:10px;color:#475569;letter-spacing:2px;text-transform:uppercase;margin-top:2px;">
                Hospital Management System
            </div>
        </div>
        <hr style="border-color:#1e2640;margin:8px 0 18px 0;">
        """, unsafe_allow_html=True)
 
        # Role switcher
        st.markdown('<div style="font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Switch Role (Demo)</div>', unsafe_allow_html=True)
        role = st.radio(
            label="role",
            options=["Patient", "Doctor", "Staff / Admin"],
            index=["Patient", "Doctor", "Staff / Admin"].index(st.session_state.role),
            label_visibility="collapsed",
        )
        if role != st.session_state.role:
            st.session_state.role = role
            st.rerun()
 
        st.markdown('<hr style="border-color:#1e2640;margin:16px 0;">', unsafe_allow_html=True)
 
        # ── Doctor auth ──────────────────────────────
        if st.session_state.role == "Doctor":
            if not st.session_state.doc_logged_in:
                st.markdown('<div style="font-size:13px;font-weight:600;color:#94a3b8;margin-bottom:10px;">🔐 Doctor Login</div>', unsafe_allow_html=True)
                u = st.text_input("Username", key="doc_u", placeholder="dr.sharma")
                p = st.text_input("Password", type="password", key="doc_p", placeholder="••••••")
                hosp_choices = list(HOSPITALS.keys())
                doc_hosp_sel = st.selectbox(
                    "Select Your Hospital",
                    hosp_choices,
                    key="doc_hosp_login",
                    help="You will be locked to this hospital after login"
                )
                if st.button("Login & Lock Hospital", key="doc_login_btn", use_container_width=True):
                    cred, err = verify_credential(u, p, "doctor")
                    if cred:
                        st.session_state.doc_logged_in = True
                        st.session_state.doc_username  = u
                        st.session_state.doc_hospital  = doc_hosp_sel
                        st.rerun()
                    else:
                        st.error(err or "Invalid credentials.")
                st.caption("Try: dr.sharma / doc123")
            else:
                info    = DOCTOR_CREDS[st.session_state.doc_username]
                hosp    = st.session_state.doc_hospital
                st.markdown(f"""
                <div style="background:#0d2d1a;border:1px solid #14532d;border-radius:10px;padding:12px 14px;margin-bottom:4px;">
                    <div style="font-size:13px;font-weight:700;color:#4ade80;">✅ {info['name']}</div>
                    <div style="font-size:11px;color:#16a34a;margin-top:3px;">🔒 {hosp}</div>
                </div>
                <div style="font-size:10px;color:#4ade8066;text-align:center;margin-bottom:10px;letter-spacing:.5px;">
                    Hospital locked for this session
                </div>""", unsafe_allow_html=True)
                if st.button("Logout", key="doc_logout", use_container_width=True):
                    st.session_state.doc_logged_in = False
                    st.session_state.doc_username  = None
                    st.session_state.doc_hospital  = None
                    st.rerun()
 
        # ── Staff auth ───────────────────────────────
        elif st.session_state.role == "Staff / Admin":
            if not st.session_state.staff_logged_in:
                st.markdown('<div style="font-size:13px;font-weight:600;color:#94a3b8;margin-bottom:10px;">🔐 Staff Login</div>', unsafe_allow_html=True)
                u = st.text_input("Username", key="staff_u", placeholder="admin")
                p = st.text_input("Password", type="password", key="staff_p", placeholder="••••••")
                staff_hosp_sel = st.selectbox(
                    "Select Your Hospital",
                    list(HOSPITALS.keys()),
                    key="staff_hosp_login",
                    help="You will be locked to this hospital after login"
                )
                if st.button("Login & Lock Hospital", key="staff_login_btn", use_container_width=True):
                    cred, err = verify_credential(u, p, "staff")
                    if cred:
                        st.session_state.staff_logged_in = True
                        st.session_state.staff_username  = u
                        st.session_state.staff_hospital  = staff_hosp_sel
                        st.rerun()
                    else:
                        st.error(err or "Invalid credentials.")
                st.caption("Try: admin / staff123")
            else:
                info = STAFF_CREDS[st.session_state.staff_username]
                hosp = st.session_state.staff_hospital
                st.markdown(f"""
                <div style="background:#1c1508;border:1px solid #78350f;border-radius:10px;padding:12px 14px;margin-bottom:4px;">
                    <div style="font-size:13px;font-weight:700;color:#fbbf24;">✅ {info['name']}</div>
                    <div style="font-size:11px;color:#d97706;margin-top:3px;">🔒 {hosp}</div>
                </div>
                <div style="font-size:10px;color:#fbbf2466;text-align:center;margin-bottom:10px;letter-spacing:.5px;">
                    Hospital locked for this session
                </div>""", unsafe_allow_html=True)
                if st.button("Logout", key="staff_logout", use_container_width=True):
                    st.session_state.staff_logged_in = False
                    st.session_state.staff_username  = None
                    st.session_state.staff_hospital  = None
                    st.rerun()
 
        # ── Live system stats ────────────────────────
        st.markdown('<hr style="border-color:#1e2640;margin:16px 0;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">System Stats</div>', unsafe_allow_html=True)
 
        total_waiting  = sum(1 for p in st.session_state.patients if p["status"] == "waiting")
        total_admitted = sum(1 for p in st.session_state.patients if p["status"] == "admitted")
        total_done     = sum(1 for p in st.session_state.patients if p["status"] == "done")
        total_beds     = sum(total_available_beds(h) for h in st.session_state.beds.keys())
 
        rows = [
            ("⏳ Waiting",      total_waiting,  "#f59e0b"),
            ("🏥 Admitted",     total_admitted, "#0ea5e9"),
            ("✅ Completed",    total_done,     "#22c55e"),
            ("🛏 Beds Free",    total_beds,     "#8b5cf6"),
        ]
        for label, val, color in rows:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:6px 0;border-bottom:1px solid #1e2640;">
                <span style="font-size:12px;color:#94a3b8;">{label}</span>
                <span style="font-size:14px;font-weight:700;color:{color};">{val}</span>
            </div>""", unsafe_allow_html=True)
 
        st.markdown("""
        <div style="margin-top:24px;text-align:center;font-size:10px;color:#334155;line-height:1.6;">
            MediQueue v2.0 · Hackathon Demo<br>All data is in-memory only
        </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────
render_sidebar()
 
role = st.session_state.role
if role == "Patient":
    patient_ui.render()
elif role == "Doctor":
    doctor_ui.render()
elif role == "Staff / Admin":
    staff_ui.render()