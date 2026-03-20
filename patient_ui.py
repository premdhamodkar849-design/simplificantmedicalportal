"""
patient_ui.py — Full patient portal.
- Map-based hospital selection (locked after choice)
- Registration form (Enter key moves forward, not back)
- Token issuance with live queue tracker
- Prescription notification when doctor prescribes
- Patient history tab
"""
 
import streamlit as st
import time
from config import (
    HOSPITALS, COMPLAINTS,
    get_queue, get_patient_by_token,
    queue_position, bed_status_color, timestamp,
    total_available_beds, total_beds, _ensure_ward_format,
)
from database import (
    register_patient, check_duplicate, get_next_token,
    fetch_patients, connection_banner,
)
 
try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False
 
 
# ─────────────────────────────────────────────────────────────
# STEP INDICATOR
# ─────────────────────────────────────────────────────────────
def _stepper(current_step):
    steps = [
        ("select_hospital", "Find Hospital"),
        ("register",        "Register"),
        ("token",           "Token"),
        ("track",           "Track"),
    ]
    idx_map = {s[0]: i for i, s in enumerate(steps)}
    cur     = idx_map.get(current_step, 0)
    cols    = st.columns(len(steps))
    for i, (key, label) in enumerate(steps):
        with cols[i]:
            if i < cur:    cls, icon = "sd-done",   "✓"
            elif i == cur: cls, icon = "sd-active",  str(i+1)
            else:          cls, icon = "sd-todo",    str(i+1)
            st.markdown(f"""
            <div style="text-align:center;">
                <div class="step-dot {cls}">{icon}</div>
                <div style="font-size:11px;color:#64748b;font-weight:500;">{label}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# STEP 1 — Hospital Selection with Map
# ─────────────────────────────────────────────────────────────
def _step_select_hospital():
    connection_banner()
    st.markdown("""
    <div class="page-header">
        <p class="page-title">🏥 Find a Hospital Near You</p>
        <p class="page-sub">Search on the map or pick from the list below</p>
    </div>""", unsafe_allow_html=True)
 
    search = st.text_input("🔍 Search hospital by name or area",
                           placeholder="e.g. Apollo, Baner, General…", key="pat_search")
 
    if HAS_FOLIUM:
        center_lat = sum(h["lat"] for h in HOSPITALS.values()) / len(HOSPITALS)
        center_lng = sum(h["lng"] for h in HOSPITALS.values()) / len(HOSPITALS)
        m = folium.Map(location=[center_lat, center_lng], zoom_start=12,
                       tiles="CartoDB positron")
 
        for name, info in HOSPITALS.items():
            avail = total_available_beds(name)
            tot   = total_beds(name)
            queue = len(get_queue(name))
            color = bed_status_color(name)
            icon_c = "green" if avail > tot * 0.3 else ("orange" if avail > 0 else "red")
 
            popup_html = f"""
            <div style="font-family:Inter,sans-serif;min-width:200px;padding:4px;">
                <div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:6px;">
                    {name}
                </div>
                <div style="font-size:12px;color:#64748b;margin-bottom:8px;">
                    📍 {info['address']}<br>🔬 {info['specialty']}
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <span style="background:{color}22;color:{color};padding:2px 8px;
                                 border-radius:999px;font-size:11px;font-weight:600;">
                        🛏 {avail}/{tot} beds
                    </span>
                    <span style="background:#6366f111;color:#6366f1;padding:2px 8px;
                                 border-radius:999px;font-size:11px;font-weight:600;">
                        👥 {queue} in queue
                    </span>
                </div>
            </div>"""
            folium.Marker(
                location=[info["lat"], info["lng"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"🏥 {name}",
                icon=folium.Icon(color=icon_c, icon="plus-sign", prefix="glyphicon"),
            ).add_to(m)
 
        st.markdown("**Interactive Map** — click a pin for details:")
        st_folium(m, height=340, use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("💡 `pip install folium streamlit-folium` for an interactive map.")
 
    st.markdown("**Select your hospital:**")
    filtered = {
        n: i for n, i in HOSPITALS.items()
        if not search.strip()
        or search.lower() in n.lower()
        or search.lower() in i["address"].lower()
    }
 
    if not filtered:
        st.warning("No hospitals match your search.")
        return
 
    for name, info in filtered.items():
        avail = total_available_beds(name)
        tot   = total_beds(name)
        queue = len(get_queue(name))
        color = bed_status_color(name)
        pct   = int(avail / tot * 100) if tot else 0
 
        col_card, col_btn = st.columns([5, 1])
        with col_card:
            st.markdown(f"""
            <div class="hosp-card">
                <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                    <div>
                        <div style="font-size:16px;font-weight:700;color:#0f172a;">{name}</div>
                        <div style="font-size:12px;color:#94a3b8;margin-top:2px;">
                            📍 {info['address']} &nbsp;·&nbsp; 🔬 {info['specialty']}
                        </div>
                    </div>
                    <div style="font-size:12px;color:#64748b;">📞 {info['phone']}</div>
                </div>
                <div style="display:flex;gap:8px;margin-top:10px;align-items:center;flex-wrap:wrap;">
                    <span style="background:{color}15;color:{color};padding:3px 10px;
                                 border-radius:999px;font-size:12px;font-weight:600;">
                        🛏 {avail}/{tot} beds
                    </span>
                    <span style="background:#6366f111;color:#6366f1;padding:3px 10px;
                                 border-radius:999px;font-size:12px;font-weight:600;">
                        👥 {queue} in queue
                    </span>
                    <div style="flex:1;min-width:80px;">
                        <div style="height:5px;background:#e2e8f0;border-radius:999px;overflow:hidden;">
                            <div style="width:{pct}%;height:5px;background:{color};
                                        border-radius:999px;"></div>
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
            if avail > 0:
                if st.button("Select →", key=f"hsel_{name}",
                             use_container_width=True, type="primary"):
                    st.session_state.pat_hospital = name
                    st.session_state.pat_step = "register"
                    st.rerun()
            else:
                st.markdown("""
                <div style="background:#fef2f2;color:#dc2626;text-align:center;
                            border-radius:8px;padding:6px 8px;font-size:12px;font-weight:600;">
                    Full 🚫
                </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# STEP 2 — Registration Form
# NOTE: Back button is OUTSIDE the form to prevent Enter-key triggering it
# ─────────────────────────────────────────────────────────────
def _step_register():
    hosp = st.session_state.pat_hospital
    st.markdown(f"""
    <div class="page-header">
        <p class="page-title">Patient Registration</p>
        <p class="page-sub">Registering at <strong>{hosp}</strong></p>
    </div>""", unsafe_allow_html=True)
 
    st.markdown(f"""
    <div style="background:#ede9fe;border:1px solid #c4b5fd;border-radius:10px;
                padding:12px 16px;margin-bottom:20px;
                display:flex;align-items:center;gap:10px;">
        <span style="font-size:18px;">🔒</span>
        <span style="color:#5b21b6;font-size:14px;font-weight:600;">
            Session locked to <strong>{hosp}</strong> for privacy.
        </span>
    </div>""", unsafe_allow_html=True)
 
    # Back button OUTSIDE the form — so Enter key never triggers it
    if st.button("← Back to Hospital Selection", key="reg_back"):
        st.session_state.pat_step = "select_hospital"
        st.rerun()
 
    # Registration form — Enter will trigger the primary submit button
    with st.form("patient_reg_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name   = st.text_input("Full Name *", placeholder="e.g. Rahul Sharma")
            mobile = st.text_input("Mobile Number *", placeholder="10-digit mobile", max_chars=10)
        with c2:
            age    = st.number_input("Age", min_value=0, max_value=120, value=30)
            gender = st.selectbox("Gender", ["Prefer not to say","Male","Female","Other"])
 
        complaint = st.selectbox("Chief Complaint *", COMPLAINTS)
        notes = st.text_area(
            "Describe your symptoms (optional)",
            placeholder="Duration, severity, any medications taken…",
            height=90,
        )
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        # Only ONE submit button — Enter key will trigger this
        submit = st.form_submit_button(
            "Get My Token →", type="primary", use_container_width=True
        )
 
    if submit:
        if not name.strip():
            st.error("Please enter your full name.")
            return
        if not mobile.strip() or not mobile.isdigit() or len(mobile) != 10:
            st.error("Please enter a valid 10-digit mobile number.")
            return
 
        existing_p = check_duplicate(mobile, hosp)
        if existing_p:
            st.warning("⚠️ Already registered here. Taking you to your tracker…")
            st.session_state.pat_token  = existing_p["token"]
            st.session_state.pat_mobile = mobile
            st.session_state.pat_name   = existing_p["name"]
            st.session_state.pat_step   = "track"
            time.sleep(0.6)
            st.rerun()
            return
 
        token = get_next_token()
        patient = {
            "id":            len(st.session_state.patients) + 1,
            "name":          name.strip(),
            "phone":         mobile,
            "age":           age,
            "gender":        gender,
            "complaint":     complaint,
            "notes":         notes.strip(),
            "token":         token,
            "status":        "waiting",
            "hospital":      hosp,
            "registered_at": timestamp(),
        }
        _, db_err = register_patient(patient)
        if db_err:
            st.warning(f"⚠️ Saved locally — DB: {db_err}")
        st.session_state.pat_token  = token
        st.session_state.pat_mobile = mobile
        st.session_state.pat_name   = name.strip()
        st.session_state.pat_step   = "token"
        st.rerun()
 
 
# ─────────────────────────────────────────────────────────────
# STEP 3 — Token Issued
# ─────────────────────────────────────────────────────────────
def _step_token():
    patient = get_patient_by_token(st.session_state.pat_token)
    if not patient:
        st.error("Session expired.")
        st.session_state.pat_step = "select_hospital"
        st.rerun()
        return
 
    pos  = queue_position(patient) or 1
    wait = pos * 5
 
    st.markdown("""
    <div class="page-header">
        <p class="page-title">🎉 Token Issued!</p>
        <p class="page-sub">Save this token — you'll need it to track your position.</p>
    </div>""", unsafe_allow_html=True)
 
    col_token, col_info = st.columns([1, 1])
    with col_token:
        st.markdown(f"""
        <div class="token-card">
            <div class="token-label">Your Token</div>
            <div class="token-num">#{patient['token']}</div>
            <div style="margin-top:14px;font-size:15px;opacity:.9;font-weight:600;">
                {patient['hospital']}
            </div>
            <div style="margin-top:6px;font-size:12px;opacity:.7;">
                Registered at {patient['registered_at']}
            </div>
        </div>""", unsafe_allow_html=True)
 
    with col_info:
        st.markdown(f"""
        <div class="card" style="height:100%;box-sizing:border-box;">
            <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;
                        letter-spacing:1.5px;margin-bottom:14px;font-weight:600;">Summary</div>
            <div style="display:flex;flex-direction:column;gap:12px;font-size:14px;">
                <div><div style="font-size:10px;color:#94a3b8;">PATIENT</div>
                     <strong>{patient['name']}</strong></div>
                <div><div style="font-size:10px;color:#94a3b8;">MOBILE</div>
                     {patient['phone']}</div>
                <div><div style="font-size:10px;color:#94a3b8;">COMPLAINT</div>
                     <span style="color:#6366f1;font-weight:600;">{patient['complaint']}</span></div>
                <div style="display:flex;gap:20px;">
                    <div><div style="font-size:10px;color:#94a3b8;">POSITION</div>
                         <div style="font-size:28px;font-weight:800;color:#6366f1;line-height:1.1;">
                             #{pos}
                         </div></div>
                    <div><div style="font-size:10px;color:#94a3b8;">EST. WAIT</div>
                         <div style="font-size:28px;font-weight:800;color:#d97706;line-height:1.1;">
                             {wait}m
                         </div></div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
 
    st.markdown("<br>", unsafe_allow_html=True)
    st.success(f"📲 **SMS Notification (Simulated):** We'll alert {patient['phone']} when you're next.")
    if st.button("📍 Track My Position Live →", use_container_width=True, type="primary"):
        st.session_state.pat_step = "track"
        st.rerun()
 
 
# ─────────────────────────────────────────────────────────────
# PRESCRIPTION NOTIFICATION CARD
# ─────────────────────────────────────────────────────────────
def _prescription_notification(token):
    notifs = st.session_state.get("notifications", {})
    if token not in notifs:
        return
    n = notifs[token]
    doctor_name = n.get("doctor","").replace("."," ").title()
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);
                border:2px solid #16a34a;border-radius:16px;padding:20px;margin-bottom:20px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <span style="font-size:24px;">💊</span>
            <div>
                <div style="font-size:15px;font-weight:800;color:#14532d;">
                    Prescription Ready!
                </div>
                <div style="font-size:12px;color:#16a34a;">
                    From {doctor_name} · {n.get('hospital','')} · {n.get('time','')}
                </div>
            </div>
        </div>
        <div style="background:white;border-radius:10px;padding:14px;
                    font-size:14px;color:#0f172a;white-space:pre-wrap;line-height:1.7;
                    border:1px solid #bbf7d0;">{n['message']}</div>
        <div style="margin-top:10px;background:#dcfce7;border-radius:8px;
                    padding:10px;font-size:12px;color:#166534;display:flex;gap:8px;">
            <span>📲</span>
            <span>SMS sent to <strong>{n['phone']}</strong> with prescription details</span>
        </div>
    </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# STEP 4 — Live Tracker + History
# ─────────────────────────────────────────────────────────────
def _step_track():
    patient = get_patient_by_token(st.session_state.pat_token)
    if not patient:
        st.error("Patient not found. Please register again.")
        st.session_state.pat_step = "select_hospital"
        return
 
    st.markdown(f"""
    <div class="page-header">
        <p class="page-title">📍 My Queue & Records</p>
        <p class="page-sub">🔒 {patient['hospital']} &nbsp;·&nbsp; Token #{patient['token']}</p>
    </div>""", unsafe_allow_html=True)
 
    tab_track, tab_history = st.tabs(["📍 Live Tracker","📋 My History"])
 
    with tab_track:
        # Prescription notification (shows when doctor prescribes)
        _prescription_notification(patient["token"])
 
        # Terminal states
        if patient["status"] == "done":
            st.success("✅ Your consultation is **complete**. Thank you for visiting!")
            if patient.get("prescription"):
                st.markdown(f"""
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;
                            padding:16px;margin-top:12px;">
                    <div style="font-size:13px;font-weight:700;color:#166534;margin-bottom:8px;">
                        📋 Your Prescription
                    </div>
                    <div style="font-size:14px;color:#0f172a;white-space:pre-wrap;line-height:1.7;">
                        {patient['prescription']}
                    </div>
                </div>""", unsafe_allow_html=True)
            st.balloons()
            if st.button("Return to Home", use_container_width=True, type="primary"):
                st.session_state.pat_step     = "select_hospital"
                st.session_state.pat_token    = None
                st.session_state.pat_hospital = None
                st.rerun()
            return
 
        if patient["status"] == "admitted":
            ward = patient.get("ward","")
            st.markdown(f"""
            <div style="background:#dbeafe;border:1px solid #93c5fd;border-radius:14px;
                        padding:28px;text-align:center;margin-bottom:20px;">
                <div style="font-size:40px;margin-bottom:10px;">🏥</div>
                <div style="font-size:20px;font-weight:700;color:#1e40af;">
                    You've been admitted
                </div>
                {f'<div style="font-size:14px;color:#3b82f6;margin-top:4px;font-weight:600;">🏥 {ward} Ward</div>' if ward else ""}
                <div style="font-size:14px;color:#3b82f6;margin-top:6px;">
                    A bed has been allocated. Please follow the ward staff.
                </div>
            </div>""", unsafe_allow_html=True)
            if patient.get("prescription"):
                st.markdown(f"""
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px;">
                    <div style="font-size:13px;font-weight:700;color:#166534;margin-bottom:8px;">
                        📋 Doctor's Notes
                    </div>
                    <div style="font-size:14px;color:#0f172a;white-space:pre-wrap;">
                        {patient['prescription']}
                    </div>
                </div>""", unsafe_allow_html=True)
            if st.button("Return to Home", use_container_width=True):
                st.session_state.pat_step     = "select_hospital"
                st.session_state.pat_token    = None
                st.session_state.pat_hospital = None
                st.rerun()
            return
 
        # Live tracking
        pos   = queue_position(patient)
        if pos is None:
            st.info("Updating your position…")
            return
 
        wait       = pos * 5
        queue      = get_queue(patient["hospital"])
        total_in_q = len(queue)
        progress   = max(0.0, min(1.0, 1 - (pos / max(total_in_q, 1))))
 
        left, right = st.columns([3, 2])
        with left:
            if pos == 1:
                st.success("🔔 **You're next!** Please proceed to the consultation room.")
            elif pos <= 3:
                st.warning(f"⚡ Almost there — **{pos-1} patient(s) before you**")
            else:
                st.info(f"👥 **{pos-1} ahead.** Estimated wait: **{wait} minutes**")
 
            st.progress(progress)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;font-size:11px;
                        color:#94a3b8;margin-top:4px;margin-bottom:16px;">
                <span>Start</span>
                <span>{int(progress*100)}% through queue</span>
                <span>Your turn</span>
            </div>""", unsafe_allow_html=True)
 
            st.markdown("**Queue Preview:**")
            for i, p in enumerate(queue[:8]):
                is_me = p["token"] == patient["token"]
                bg  = "#ede9fe" if is_me else "#f8fafc"
                bdc = "#6366f1" if is_me else "#e2e8f0"
                st.markdown(f"""
                <div style="background:{bg};border:1px solid {bdc};border-radius:8px;
                            padding:10px 14px;margin-bottom:6px;
                            display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:{'700' if is_me else '400'};
                                 color:{'#5b21b6' if is_me else '#374151'};font-size:13px;">
                        {'👉 YOU — ' if is_me else f'{i+1}.  '}Token #{p['token']} · {p['name']}
                    </span>
                    <span style="font-size:11px;color:#94a3b8;">
                        {'🟣' if is_me else p['complaint'][:18]}
                    </span>
                </div>""", unsafe_allow_html=True)
 
        with right:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:16px;
                        padding:22px;color:white;text-align:center;margin-bottom:14px;">
                <div style="font-size:11px;opacity:.75;text-transform:uppercase;
                            letter-spacing:1.5px;margin-bottom:6px;">Queue Position</div>
                <div style="font-size:72px;font-weight:900;line-height:1;">#{pos}</div>
                <div style="font-size:12px;opacity:.7;margin-top:4px;">
                    of {total_in_q} waiting
                </div>
            </div>
            <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;
                        padding:18px;text-align:center;margin-bottom:14px;">
                <div style="font-size:11px;color:#c2410c;text-transform:uppercase;
                            letter-spacing:1.5px;margin-bottom:4px;">Est. Wait</div>
                <div style="font-size:48px;font-weight:800;color:#ea580c;line-height:1;">
                    {wait}
                </div>
                <div style="font-size:12px;color:#c2410c;margin-top:2px;">minutes</div>
            </div>
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;
                        padding:14px;text-align:center;">
                <div style="font-size:12px;color:#166534;font-weight:600;margin-bottom:4px;">
                    📲 SMS Alert Active
                </div>
                <div style="font-size:12px;color:#15803d;">
                    Notifying<br><strong>{patient['phone']}</strong>
                </div>
            </div>""", unsafe_allow_html=True)
 
        col_r, col_h = st.columns(2)
        with col_r:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        with col_h:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.pat_step     = "select_hospital"
                st.session_state.pat_token    = None
                st.session_state.pat_hospital = None
                st.rerun()
 
    with tab_history:
        _patient_history(patient)
 
 
# ─────────────────────────────────────────────────────────────
# PATIENT HISTORY
# ─────────────────────────────────────────────────────────────
def _patient_history(current_patient):
    st.markdown("#### 📋 My Visit History")
    st.markdown(f"Records for mobile **{current_patient['phone']}**")
 
    my_history = [
        p for p in st.session_state.patients
        if p["phone"] == current_patient["phone"]
    ]
 
    if not my_history:
        st.info("No visit history found.")
        return
 
    for p in my_history:
        status_color = {
            "waiting":  "#d97706",
            "admitted": "#1d4ed8",
            "done":     "#16a34a",
        }.get(p["status"], "#64748b")
        status_icon = {"waiting":"⏳","admitted":"🏥","done":"✅"}.get(p["status"],"•")
 
        with st.expander(
            f"{status_icon} Token #{p['token']} — {p['hospital']} · {p.get('registered_at','')}"
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div style="font-size:13px;display:flex;flex-direction:column;gap:8px;">
                    <div><span style="color:#94a3b8;font-size:11px;">HOSPITAL</span><br>
                         <strong>{p['hospital']}</strong></div>
                    <div><span style="color:#94a3b8;font-size:11px;">COMPLAINT</span><br>
                         <span style="color:#6366f1;font-weight:600;">{p['complaint']}</span></div>
                    <div><span style="color:#94a3b8;font-size:11px;">REGISTERED</span><br>
                         {p.get('registered_at','—')}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="font-size:13px;display:flex;flex-direction:column;gap:8px;">
                    <div><span style="color:#94a3b8;font-size:11px;">STATUS</span><br>
                         <span style="color:{status_color};font-weight:700;
                                      text-transform:uppercase;">{p['status']}</span></div>
                    {f'<div><span style="color:#94a3b8;font-size:11px;">WARD</span><br>{p.get("ward","—")}</div>' if p.get("ward") else ""}
                    {f'<div><span style="color:#94a3b8;font-size:11px;">COMPLETED</span><br>{p.get("completed_at","—")}</div>' if p.get("completed_at") else ""}
                </div>""", unsafe_allow_html=True)
 
            if p.get("prescription"):
                st.markdown(f"""
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
                            padding:14px;margin-top:10px;">
                    <div style="font-size:11px;color:#166534;text-transform:uppercase;
                                letter-spacing:1px;margin-bottom:6px;font-weight:600;">
                        💊 Prescription
                    </div>
                    <div style="font-size:14px;color:#0f172a;white-space:pre-wrap;line-height:1.7;">
                        {p['prescription']}
                    </div>
                </div>""", unsafe_allow_html=True)
            elif p["status"] == "done":
                st.caption("No prescription recorded for this visit.")
 
 
# ─────────────────────────────────────────────────────────────
# MAIN ENTRY
# ─────────────────────────────────────────────────────────────
def render():
    st.markdown('<span class="role-badge badge-patient">👤 Patient Portal</span>',
                unsafe_allow_html=True)
    _stepper(st.session_state.pat_step)
 
    step = st.session_state.pat_step
    if step == "select_hospital": _step_select_hospital()
    elif step == "register":      _step_register()
    elif step == "token":         _step_token()
    elif step == "track":         _step_track()
