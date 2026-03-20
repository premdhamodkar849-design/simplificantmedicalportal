"""
doctor_ui.py — Doctor dashboard.
Hospital-locked per session.
Prescription saved to patient record → visible in patient tracker + SMS simulation.
"""
 
import streamlit as st
import time
from config import (
    DOCTOR_CREDS, WARD_COLORS,
    get_queue, timestamp, bed_status_color,
    total_available_beds, total_beds, _ensure_ward_format,
)
from database import update_patient_status, fetch_patients, connection_banner
 
 
def _my_hospital():
    return st.session_state.doc_hospital
 
def _my_name():
    return DOCTOR_CREDS[st.session_state.doc_username]["name"]
 
 
# ─────────────────────────────────────────────────────────────
# CURRENT PATIENT CARD
# ─────────────────────────────────────────────────────────────
def _current_card(patient):
    ward    = patient.get("ward","")
    wc      = WARD_COLORS.get(ward,{})
    ward_tag = (
        f'<span style="background:rgba(255,255,255,.2);border-radius:999px;'
        f'padding:2px 10px;font-size:12px;font-weight:600;">🏥 {ward} Ward</span>'
        if ward else ""
    )
    st.markdown(f"""
    <div class="current-card">
        <div style="font-size:11px;opacity:.75;text-transform:uppercase;letter-spacing:1.5px;
                    margin-bottom:10px;display:flex;align-items:center;gap:8px;">
            <span style="width:8px;height:8px;background:#fff;border-radius:50%;
                         display:inline-block;opacity:.8;"></span>
            NOW CONSULTING &nbsp; {ward_tag}
        </div>
        <div style="font-size:28px;font-weight:800;margin-bottom:4px;">{patient['name']}</div>
        <div style="font-size:13px;opacity:.85;margin-bottom:16px;">
            📞 {patient['phone']} &nbsp;·&nbsp; Token #{patient['token']}
            &nbsp;·&nbsp; {patient.get('age','?')} yrs, {patient.get('gender','—')}
        </div>
        <div style="background:rgba(255,255,255,.18);border-radius:10px;padding:14px;margin-bottom:14px;">
            <div style="font-size:10px;opacity:.75;text-transform:uppercase;
                        letter-spacing:1px;margin-bottom:4px;">Chief Complaint</div>
            <div style="font-size:16px;font-weight:700;">{patient['complaint']}</div>
            {f'<div style="font-size:13px;opacity:.8;margin-top:6px;">{patient["notes"]}</div>'
             if patient.get("notes") else ""}
        </div>
        <div style="font-size:12px;opacity:.7;">⏰ Registered at {patient.get('registered_at','—')}</div>
    </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# PRESCRIPTION PANEL
# ─────────────────────────────────────────────────────────────
def _prescription_panel(current, hospital):
    beds  = _ensure_ward_format(hospital)
    avail = total_available_beds(hospital)
 
    st.markdown("""
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;
                padding:16px;margin-bottom:16px;">
        <div style="font-size:13px;font-weight:700;color:#166534;margin-bottom:10px;">
            📋 Prescription & Notes
        </div>""", unsafe_allow_html=True)
 
    presc = st.text_area(
        label="Prescription",
        placeholder=(
            "Medicines: e.g. Paracetamol 500mg × 3 times/day × 5 days\n"
            "Diagnosis: e.g. Viral fever\n"
            "Follow-up: e.g. Review after 3 days\n"
            "Advice: Rest, fluids, avoid cold food…"
        ),
        height=160,
        key=f"presc_{current['token']}",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
 
    # Action buttons
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("✅ Done + Notify", use_container_width=True,
                     type="primary", key="btn_next"):
            if not presc.strip():
                st.warning("Please add a prescription before marking as done.")
            else:
                ok, err = update_patient_status(
                    current["token"], "done",
                    prescription=presc.strip(),
                    completed_at=timestamp(),
                )
                if err:
                    st.warning(f"DB: {err}")
                # Simulate SMS
                _simulate_sms(current, presc.strip())
                st.toast(f"✅ {current['name']} consultation complete. Patient notified!", icon="✅")
                time.sleep(0.5)
                st.rerun()
 
    with b2:
        if avail > 0:
            if st.button("🏥 Admit Patient", use_container_width=True, key="btn_admit"):
                ok, err = update_patient_status(
                    current["token"], "admitted",
                    prescription=presc.strip() if presc.strip() else None,
                    admitted_at=timestamp(),
                )
                # Reduce beds (General ward default from doctor view)
                ward_beds = beds.get("General", {"total":0,"available":0})
                if ward_beds["available"] > 0:
                    from database import update_beds
                    ward_beds["available"] -= 1
                    update_beds(hospital, "General",
                                ward_beds["total"], ward_beds["available"])
                if err:
                    st.warning(f"DB: {err}")
                st.toast(f"🏥 {current['name']} admitted!", icon="🏥")
                time.sleep(0.4)
                st.rerun()
        else:
            st.markdown("""
            <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;
                        padding:8px;text-align:center;font-size:12px;color:#dc2626;
                        font-weight:600;">No beds! 🚫</div>""", unsafe_allow_html=True)
 
    with b3:
        if st.button("⏭️ Skip Patient", use_container_width=True, key="btn_skip"):
            for p in st.session_state.patients:
                if p["token"] == current["token"]:
                    st.session_state.patients.remove(p)
                    st.session_state.patients.append(p)
                    break
            st.toast("Patient moved to end of queue.")
            time.sleep(0.3)
            st.rerun()
 
 
def _simulate_sms(patient, prescription):
    """Store SMS notification in session state — visible in patient tracker."""
    if "notifications" not in st.session_state:
        st.session_state.notifications = {}
    st.session_state.notifications[patient["token"]] = {
        "type":         "prescription",
        "message":      prescription,
        "doctor":       st.session_state.doc_username,
        "hospital":     patient["hospital"],
        "time":         timestamp(),
        "phone":        patient["phone"],
    }
 
 
# ─────────────────────────────────────────────────────────────
# QUEUE LIST
# ─────────────────────────────────────────────────────────────
def _queue_list(queue, current_token):
    for i, p in enumerate(queue):
        if p["token"] == current_token:
            continue
        wait = i * 5
        st.markdown(f"""
        <div class="q-item">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
                <div style="flex:1;">
                    <div style="font-size:11px;color:#94a3b8;font-weight:600;margin-bottom:2px;">
                        #{i+1} &nbsp;·&nbsp; Token {p['token']}
                    </div>
                    <div style="font-size:16px;font-weight:700;color:#0f172a;">{p['name']}</div>
                    <div style="font-size:13px;color:#6366f1;margin-top:2px;">{p['complaint']}</div>
                    {f'<div style="font-size:12px;color:#94a3b8;margin-top:3px;">{p["notes"][:60]}…</div>'
                     if p.get("notes") else ""}
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <div style="font-size:11px;color:#94a3b8;">Est. wait</div>
                    <div style="font-size:18px;font-weight:700;color:#d97706;">~{wait}m</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:2px;">
                        📞 {p['phone']}<br>
                        {p.get('age','?')}y · {p.get('gender','—')}
                    </div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# PATIENT HISTORY TAB
# ─────────────────────────────────────────────────────────────
def _history_tab(hospital):
    st.markdown("#### 📂 Patient History — Completed Today")
 
    search = st.text_input("🔍 Search by name, token or phone", key="hist_search")
    done_list = [
        p for p in st.session_state.patients
        if p.get("hospital") == hospital
        and p["status"] in ("done","admitted")
        and (not search.strip()
             or search.lower() in p["name"].lower()
             or search in str(p["token"])
             or search in str(p.get("phone","")))
    ]
 
    if not done_list:
        st.info("No completed consultations yet.")
        return
 
    st.markdown(f"**{len(done_list)} patient(s)**")
    for p in done_list:
        icon  = "✅" if p["status"] == "done" else "🏥"
        color = "#16a34a" if p["status"] == "done" else "#1d4ed8"
        bg    = "#f0fdf4" if p["status"] == "done" else "#eff6ff"
 
        with st.expander(
            f"{icon} Token #{p['token']} — {p['name']} · {p['complaint'][:40]}"
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div style="font-size:13px;display:flex;flex-direction:column;gap:8px;">
                    <div><span style="color:#94a3b8;font-size:11px;">PATIENT</span><br>
                         <strong>{p['name']}</strong></div>
                    <div><span style="color:#94a3b8;font-size:11px;">MOBILE</span><br>
                         {p['phone']}</div>
                    <div><span style="color:#94a3b8;font-size:11px;">AGE / GENDER</span><br>
                         {p.get('age','?')} yrs · {p.get('gender','—')}</div>
                    <div><span style="color:#94a3b8;font-size:11px;">REGISTERED</span><br>
                         {p.get('registered_at','—')}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="font-size:13px;display:flex;flex-direction:column;gap:8px;">
                    <div><span style="color:#94a3b8;font-size:11px;">COMPLAINT</span><br>
                         <strong style="color:#6366f1;">{p['complaint']}</strong></div>
                    <div><span style="color:#94a3b8;font-size:11px;">STATUS</span><br>
                         <span style="color:{color};font-weight:700;text-transform:uppercase;">
                             {p['status']}
                         </span></div>
                    {f'<div><span style="color:#94a3b8;font-size:11px;">COMPLETED</span><br>{p.get("completed_at","—")}</div>'
                     if p.get("completed_at") else ""}
                    {f'<div><span style="color:#94a3b8;font-size:11px;">WARD</span><br>{p.get("ward","—")}</div>'
                     if p.get("ward") else ""}
                </div>""", unsafe_allow_html=True)
 
            if p.get("prescription"):
                st.markdown(f"""
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
                            padding:14px;margin-top:12px;">
                    <div style="font-size:11px;color:#166534;text-transform:uppercase;
                                letter-spacing:1px;margin-bottom:8px;font-weight:600;">
                        📋 Prescription
                    </div>
                    <div style="font-size:14px;color:#0f172a;white-space:pre-wrap;
                                line-height:1.6;">{p['prescription']}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#fef9c3;border:1px solid #fde68a;border-radius:8px;
                            padding:10px;font-size:13px;color:#854d0e;">
                    ⚠️ No prescription recorded for this patient.
                </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────
def render():
    if not st.session_state.doc_logged_in:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;">
            <div style="font-size:60px;margin-bottom:16px;">🔐</div>
            <div style="font-size:22px;font-weight:700;color:#0f172a;margin-bottom:8px;">
                Doctor Login Required
            </div>
            <div style="margin-top:16px;background:#f8fafc;border:1px solid #e2e8f0;
                        border-radius:10px;padding:14px;display:inline-block;
                        font-size:13px;color:#64748b;">
                <code>dr.sharma / doc123</code> &nbsp;·&nbsp;
                <code>dr.patel / doc456</code><br>
                <code>dr.mehta / med789</code> &nbsp;·&nbsp;
                <code>dr.khan / doc321</code>
            </div>
        </div>""", unsafe_allow_html=True)
        return
 
    hospital = _my_hospital()
    doc_name = _my_name()
    queue    = get_queue(hospital)
    avail    = total_available_beds(hospital)
 
    st.markdown('<span class="role-badge badge-doctor">👨‍⚕️ Doctor Dashboard</span>',
                unsafe_allow_html=True)
    connection_banner()
 
    st.markdown(f"""
    <div class="page-header">
        <p class="page-title">Welcome, {doc_name}</p>
        <p class="page-sub">🔒 {hospital}</p>
    </div>""", unsafe_allow_html=True)
 
    # Stats row
    done_today   = sum(1 for p in st.session_state.patients
                       if p.get("hospital") == hospital
                       and p["status"] in ("done","admitted"))
    admitted_now = sum(1 for p in st.session_state.patients
                       if p.get("hospital") == hospital and p["status"] == "admitted")
 
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "In Queue",       len(queue),    "#6366f1"),
        (c2, "Seen Today",     done_today,    "#16a34a"),
        (c3, "Admitted",       admitted_now,  "#0ea5e9"),
        (c4, "Beds Available", avail,         bed_status_color(hospital)),
    ]:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-num" style="color:{color};">{val}</div>
                <div class="stat-label">{label}</div>
            </div>""", unsafe_allow_html=True)
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    # Tabs
    tab_queue, tab_history = st.tabs(["🟢 Active Queue", "📂 Patient History"])
 
    with tab_queue:
        if not queue:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;background:#f8fafc;
                        border-radius:16px;border:1px dashed #e2e8f0;">
                <div style="font-size:48px;margin-bottom:12px;">🎉</div>
                <div style="font-size:18px;font-weight:600;color:#374151;">Queue is empty!</div>
                <div style="font-size:14px;color:#94a3b8;margin-top:6px;">All patients seen.</div>
            </div>""", unsafe_allow_html=True)
        else:
            current  = queue[0]
            left_col, right_col = st.columns([2, 3])
 
            with left_col:
                st.markdown("#### 🟢 Current Patient")
                _current_card(current)
                _prescription_panel(current, hospital)
 
            with right_col:
                st.markdown(f"#### 📋 Queue — {len(queue)} waiting")
                _queue_list(queue, current["token"])
 
    with tab_history:
        _history_tab(hospital)
  