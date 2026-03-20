"""
staff_ui.py — Staff / Admin dashboard.
Ward-based bed management (General / ICU / Emergency / OPD).
Hospital locked per session.
"""
 
import streamlit as st
from config import (
    STAFF_CREDS, HOSPITALS, COMPLAINTS, WARD_TYPES, WARD_COLORS,
    get_queue, timestamp, bed_status_color, total_available_beds, total_beds,
    _ensure_ward_format,
)
from database import (
    update_beds, update_patient_status, register_patient,
    get_next_token, fetch_patients, connection_banner,
)
 
 
def _my_hospital():
    return st.session_state.staff_hospital
 
def _my_name():
    return STAFF_CREDS[st.session_state.staff_username]["name"]
 
 
# ─────────────────────────────────────────────────────────────
# WARD BED GRID
# ─────────────────────────────────────────────────────────────
def _ward_bed_grid(hospital):
    wards     = _ensure_ward_format(hospital)
    tot_all   = sum(w["total"]     for w in wards.values())
    avail_all = sum(w["available"] for w in wards.values())
    occ_all   = tot_all - avail_all
    pct_occ   = int(occ_all / tot_all * 100) if tot_all else 0
    occ_color = bed_status_color(hospital)
 
    st.markdown("""
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:18px;">
        <div style="display:flex;align-items:center;gap:6px;">
            <div style="width:13px;height:13px;background:#22c55e;border-radius:3px;"></div>
            <span style="font-size:12px;color:#64748b;">Available</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
            <div style="width:13px;height:13px;background:#94a3b8;border-radius:3px;"></div>
            <span style="font-size:12px;color:#64748b;">Occupied</span>
        </div>
    </div>""", unsafe_allow_html=True)
 
    for ward in WARD_TYPES:
        if ward not in wards:
            continue
        info  = wards[ward]
        total = info["total"]
        avail = info["available"]
        occ   = total - avail
        wc    = WARD_COLORS[ward]
 
        blocks = ""
        for i in range(1, total + 1):
            is_occ = i <= occ
            bg  = "#94a3b8" if is_occ else wc["bg"]
            brd = "#64748b" if is_occ else wc["border"]
            blocks += (
                f'<div title="{ward} Bed {i} — {"Occupied" if is_occ else "Available"}" '
                f'style="width:34px;height:34px;background:{bg};border:2px solid {brd};'
                f'border-radius:6px;display:inline-flex;align-items:center;justify-content:center;'
                f'font-size:10px;font-weight:700;color:white;box-shadow:0 1px 3px rgba(0,0,0,.15);">'
                f'{i}</div>'
            )
 
        st.markdown(f"""
        <div style="background:{wc['badge']};border:1px solid {wc['border']}33;
                    border-radius:12px;padding:16px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <div style="font-size:14px;font-weight:700;color:{wc['text']};">{ward} Ward</div>
                <div style="display:flex;gap:10px;font-size:12px;">
                    <span style="background:{wc['bg']}33;color:{wc['text']};padding:2px 10px;
                                 border-radius:999px;font-weight:600;">{avail} free</span>
                    <span style="background:#94a3b822;color:#475569;padding:2px 10px;
                                 border-radius:999px;font-weight:600;">{occ} occupied</span>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:5px;">{blocks}</div>
        </div>""", unsafe_allow_html=True)
 
    st.markdown(f"""
    <div style="margin-top:4px;">
        <div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:5px;">
            <span>Overall Occupancy</span>
            <span style="font-weight:600;color:{occ_color};">{pct_occ}% · {occ_all}/{tot_all} beds used</span>
        </div>
        <div style="height:8px;background:#e2e8f0;border-radius:999px;overflow:hidden;">
            <div style="width:{pct_occ}%;height:8px;background:{occ_color};border-radius:999px;"></div>
        </div>
    </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# TAB 1 — BED MANAGEMENT
# ─────────────────────────────────────────────────────────────
def _tab_beds(hospital):
    wards     = _ensure_ward_format(hospital)
    avail_all = total_available_beds(hospital)
    tot_all   = total_beds(hospital)
    occ_all   = tot_all - avail_all
    queue_cnt = len(get_queue(hospital))
 
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Total Beds", tot_all,    "#6366f1"),
        (c2, "Available",  avail_all,  bed_status_color(hospital)),
        (c3, "Occupied",   occ_all,    "#ef4444"),
        (c4, "In Queue",   queue_cnt,  "#d97706"),
    ]:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-num" style="color:{color};">{val}</div>
                <div class="stat-label">{label}</div>
            </div>""", unsafe_allow_html=True)
 
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if avail_all == 0:
        st.error("🚨 No beds available across all wards!")
    elif avail_all <= 3:
        st.warning(f"⚠️ Critical: Only {avail_all} beds remaining!")
 
    st.markdown("---")
    st.markdown("#### 🛏️ Bed Map by Ward")
    _ward_bed_grid(hospital)
 
    st.markdown("---")
    st.markdown("#### ⚙️ Bed Controls")
    ward_sel = st.selectbox("Select Ward", WARD_TYPES, key="bed_ctrl_ward")
    winfo    = wards.get(ward_sel, {"total": 0, "available": 0})
    wc       = WARD_COLORS[ward_sel]
 
    st.markdown(f"""
    <div style="background:{wc['badge']};border:1px solid {wc['border']}44;border-radius:10px;
                padding:12px 16px;margin-bottom:12px;">
        <span style="font-size:13px;color:{wc['text']};font-weight:600;">
            {ward_sel} Ward: {winfo['available']} free / {winfo['total']} total
        </span>
    </div>""", unsafe_allow_html=True)
 
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button(f"➕ Add {ward_sel} Bed", use_container_width=True, key="add_bed"):
            wards[ward_sel]["total"]     += 1
            wards[ward_sel]["available"] += 1
            update_beds(hospital, ward_sel, wards[ward_sel]["total"], wards[ward_sel]["available"])
            st.toast(f"✅ {ward_sel} bed added!")
            st.rerun()
    with bc2:
        if winfo["available"] > 0:
            if st.button(f"➖ Remove {ward_sel} Bed", use_container_width=True, key="rem_bed"):
                wards[ward_sel]["total"]     -= 1
                wards[ward_sel]["available"] -= 1
                update_beds(hospital, ward_sel, wards[ward_sel]["total"], wards[ward_sel]["available"])
                st.toast(f"Removed a {ward_sel} bed.")
                st.rerun()
        else:
            st.button(f"➖ Remove {ward_sel} Bed", disabled=True,
                      use_container_width=True, key="rem_bed_dis")
 
    # ── Discharge ──
    st.markdown("---")
    st.markdown("#### 🏠 Discharge Patient")
    admitted_here = [p for p in st.session_state.patients
                     if p.get("hospital") == hospital and p["status"] == "admitted"]
    if not admitted_here:
        st.info("No admitted patients to discharge.")
    else:
        dis_opts = {
            f"#{p['token']} — {p['name']} · {p.get('ward','General')} Ward · Admitted {p.get('admitted_at','—')}": p
            for p in admitted_here
        }
        dis_sel = st.selectbox("Select patient to discharge", list(dis_opts.keys()),
                               key="dis_sel")
        if st.button("✅ Confirm Discharge", type="primary",
                     use_container_width=True, key="dis_confirm"):
            chosen   = dis_opts[dis_sel]
            dis_ward = chosen.get("ward", "General")
            update_patient_status(chosen["token"], "done", completed_at=timestamp())
            if dis_ward in wards:
                wards[dis_ward]["available"] = min(
                    wards[dis_ward]["available"] + 1, wards[dis_ward]["total"])
                update_beds(hospital, dis_ward,
                            wards[dis_ward]["total"], wards[dis_ward]["available"])
            st.success(f"✅ {chosen['name']} discharged from {dis_ward} Ward. Bed freed.")
            st.rerun()
 
    # ── Admit from queue ──
    st.markdown("---")
    st.markdown("#### 🧾 Admit from Queue")
    queue = get_queue(hospital)
    if not queue:
        st.info("No patients waiting in queue.")
    elif avail_all == 0:
        st.error("No beds available.")
    else:
        opts     = {f"#{p['token']} · {p['name']} ({p['complaint']})": p for p in queue}
        sel      = st.selectbox("Patient", list(opts.keys()), key="adm_from_q")
        adm_ward = st.selectbox("Admit to Ward", WARD_TYPES, key="adm_ward")
        winfo2   = wards.get(adm_ward, {"total":0,"available":0})
        if winfo2["available"] == 0:
            st.warning(f"⚠️ No beds in {adm_ward} Ward. Choose another.")
        else:
            if st.button("✅ Admit to Ward", type="primary",
                         use_container_width=True, key="adm_q_btn"):
                chosen = opts[sel]
                update_patient_status(chosen["token"], "admitted", admitted_at=timestamp())
                for p in st.session_state.patients:
                    if p["token"] == chosen["token"]:
                        p["ward"] = adm_ward
                        break
                wards[adm_ward]["available"] -= 1
                update_beds(hospital, adm_ward,
                            wards[adm_ward]["total"], wards[adm_ward]["available"])
                st.success(f"✅ {chosen['name']} admitted to {adm_ward} Ward!")
                st.rerun()
 
 
# ─────────────────────────────────────────────────────────────
# TAB 2 — EMERGENCY ADMIT
# ─────────────────────────────────────────────────────────────
def _tab_emergency(hospital):
    wards     = _ensure_ward_format(hospital)
    avail_all = total_available_beds(hospital)
 
    st.markdown(f"""
    <div class="em-alert">
        🚨 EMERGENCY ADMISSION — Bypasses queue entirely.
        Use only for life-threatening / critical situations at <strong>{hospital}</strong>.
    </div>""", unsafe_allow_html=True)
 
    if avail_all == 0:
        st.error("🚨 No beds available at this hospital.")
 
    with st.form("em_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            em_name  = st.text_input("Patient Name *", placeholder="Full name or 'Unknown'")
            em_phone = st.text_input("Mobile (if available)", placeholder="10-digit", max_chars=10)
        with c2:
            em_age    = st.number_input("Age (approx)", 0, 120, 35)
            em_gender = st.selectbox("Gender", ["Unknown","Male","Female","Other"])
 
        c3, c4 = st.columns(2)
        with c3:
            em_ward = st.selectbox("Admit to Ward *", WARD_TYPES)
        with c4:
            em_severity = st.select_slider(
                "Severity",
                options=["Moderate","Serious","Critical","Life-threatening"],
                value="Critical",
            )
        em_complaint = st.text_area(
            "Emergency Description *",
            placeholder="e.g. Cardiac arrest, severe trauma, unconscious…",
            height=80,
        )
        submit = st.form_submit_button(
            "🚨 Admit Immediately", type="primary",
            use_container_width=True, disabled=(avail_all == 0),
        )
 
    if submit:
        if not em_name.strip():
            st.error("Patient name is required.")
        elif not em_complaint.strip():
            st.error("Emergency description is required.")
        else:
            winfo = wards.get(em_ward, {"total":0,"available":0})
            if winfo["available"] == 0:
                st.error(f"🚨 No beds in {em_ward} Ward! Choose a different ward.")
            else:
                token = get_next_token()
                patient = {
                    "id":            len(st.session_state.patients) + 1,
                    "name":          em_name.strip(),
                    "phone":         em_phone or "N/A",
                    "age":           em_age,
                    "gender":        em_gender,
                    "complaint":     f"[EMERGENCY] {em_complaint.strip()}",
                    "notes":         f"Severity: {em_severity}",
                    "token":         token,
                    "status":        "admitted",
                    "hospital":      hospital,
                    "ward":          em_ward,
                    "is_emergency":  True,
                    "registered_at": timestamp(),
                }
                _, db_err = register_patient(patient)
                if db_err:
                    st.warning(f"DB warning: {db_err}")
                wards[em_ward]["available"] -= 1
                update_beds(hospital, em_ward,
                            wards[em_ward]["total"], wards[em_ward]["available"])
                st.success(
                    f"🚨 Emergency admission complete — Token #{token} · "
                    f"**{em_ward} Ward** at {hospital}"
                )
                st.rerun()
 
    emergencies = [p for p in st.session_state.patients
                   if p.get("is_emergency") and p.get("hospital") == hospital
                   and p["status"] == "admitted"]
    if emergencies:
        st.markdown("<br>**Active Emergency Patients:**")
        for p in emergencies:
            ward = p.get("ward","—")
            wc   = WARD_COLORS.get(ward, WARD_COLORS["Emergency"])
            st.markdown(f"""
            <div style="background:#fff1f2;border:1px solid #fecaca;border-radius:10px;
                        padding:14px 18px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">
                    <div>
                        <span style="font-weight:700;color:#dc2626;">🚨 {p['name']}</span>
                        <span style="font-size:12px;color:#94a3b8;margin-left:8px;">
                            Token #{p['token']}
                        </span>
                    </div>
                    <span style="background:{wc['badge']};color:{wc['text']};
                                 padding:2px 10px;border-radius:999px;font-size:12px;
                                 font-weight:600;">🏥 {ward} Ward</span>
                </div>
                <div style="font-size:13px;color:#7f1d1d;margin-top:6px;">
                    {p['complaint'].replace('[EMERGENCY] ','')}
                </div>
            </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# TAB 3 — PATIENT RECORDS
# ─────────────────────────────────────────────────────────────
def _tab_patients(hospital):
    st.markdown(f"Patient records for **{hospital}**")
    fc1, fc2 = st.columns(2)
    with fc1:
        status_filter = st.multiselect(
            "Status", ["waiting","admitted","done"],
            default=["waiting","admitted","done"],
        )
    with fc2:
        search = st.text_input("🔍 Search name / token")
 
    all_here = [
        p for p in st.session_state.patients
        if p.get("hospital") == hospital
        and p["status"] in status_filter
        and (not search.strip()
             or search.lower() in p["name"].lower()
             or search in str(p["token"]))
    ]
    if not all_here:
        st.info("No records match filters.")
        return
 
    st.markdown(f"**{len(all_here)} record(s)**")
    status_meta = {
        "waiting":  ("#fef3c7","#d97706","⏳"),
        "admitted": ("#dbeafe","#1d4ed8","🏥"),
        "done":     ("#dcfce7","#16a34a","✅"),
    }
    for p in all_here:
        bg, fc, icon = status_meta.get(p["status"],("#f8fafc","#64748b","•"))
        ward = p.get("ward","")
        wc   = WARD_COLORS.get(ward, {})
        presc_html = (
            f'<div style="margin-top:8px;background:white;border-radius:8px;padding:10px;'
            f'font-size:13px;color:#374151;border:1px solid #e2e8f0;">'
            f'<strong>📋 Prescription:</strong> {p["prescription"]}</div>'
            if p.get("prescription") else ""
        )
        ward_badge = (
            f'<span style="background:{wc.get("badge","#f1f5f9")};'
            f'color:{wc.get("text","#475569")};padding:2px 8px;border-radius:999px;'
            f'font-size:11px;font-weight:600;">{ward} Ward</span>'
            if ward else ""
        )
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {fc}33;border-radius:12px;
                    padding:14px 18px;margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">
                <div>
                    <span style="font-weight:700;color:#0f172a;">
                        {icon} {'🚨 ' if p.get('is_emergency') else ''}{p['name']}
                    </span>
                    <span style="font-size:12px;color:#94a3b8;margin-left:8px;">
                        #{p['token']}
                    </span>
                    <span style="font-size:12px;color:#94a3b8;margin-left:8px;">
                        📞 {p['phone']}
                    </span>
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                    {ward_badge}
                    <span style="background:{fc}22;color:{fc};padding:2px 8px;
                                 border-radius:999px;font-size:11px;font-weight:700;
                                 text-transform:uppercase;">{p['status']}</span>
                </div>
            </div>
            <div style="font-size:13px;color:#64748b;margin-top:8px;display:flex;gap:14px;flex-wrap:wrap;">
                <span>🩺 {p['complaint']}</span>
                <span>👤 {p.get('age','?')}y · {p.get('gender','—')}</span>
                <span>⏰ {p.get('registered_at','—')}</span>
            </div>
            {presc_html}
        </div>""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────
def render():
    if not st.session_state.staff_logged_in:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;">
            <div style="font-size:60px;margin-bottom:16px;">🔐</div>
            <div style="font-size:22px;font-weight:700;color:#0f172a;margin-bottom:8px;">
                Staff Login Required
            </div>
            <div style="margin-top:16px;background:#f8fafc;border:1px solid #e2e8f0;
                        border-radius:10px;padding:14px;display:inline-block;font-size:13px;color:#64748b;">
                <code>admin / staff123</code> &nbsp;·&nbsp;
                <code>nurse1 / nurse456</code><br>
                <code>reception / rec789</code> &nbsp;·&nbsp;
                <code>manager / mgr123</code>
            </div>
        </div>""", unsafe_allow_html=True)
        return
 
    hospital   = _my_hospital()
    staff_name = _my_name()
    hosp_info  = HOSPITALS.get(hospital, {})
    avail_all  = total_available_beds(hospital)
    tot_all    = total_beds(hospital)
    color      = bed_status_color(hospital)
 
    st.markdown('<span class="role-badge badge-staff">🧑‍💼 Staff Dashboard</span>',
                unsafe_allow_html=True)
    connection_banner()
 
    st.markdown(f"""
    <div class="page-header">
        <p class="page-title">Operations — {hospital}</p>
        <p class="page-sub">🔒 <strong>{staff_name}</strong> &nbsp;·&nbsp;
            {hosp_info.get('specialty','')} &nbsp;·&nbsp;
            📍 {hosp_info.get('address','')}</p>
    </div>""", unsafe_allow_html=True)
 
    st.markdown(f"""
    <div style="background:{color}12;border:1px solid {color}44;border-radius:12px;
                padding:14px 20px;margin-bottom:24px;
                display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:12px;height:12px;background:{color};border-radius:50%;"></div>
            <span style="font-weight:700;color:{color};font-size:16px;">{avail_all} beds available</span>
            <span style="color:#64748b;font-size:13px;">out of {tot_all} total</span>
        </div>
        <span style="color:#64748b;font-size:13px;">📞 {hosp_info.get('phone','')}</span>
    </div>""", unsafe_allow_html=True)
 
    tab1, tab2, tab3 = st.tabs(["🛏️  Bed Management","🚨  Emergency Admit","📋  Patient Records"])
    with tab1: _tab_beds(hospital)
    with tab2: _tab_emergency(hospital)
    with tab3: _tab_patients(hospital)
 