"""
config.py — Shared constants, credentials, hospital data, and session state bootstrap.
All modules import from here to keep a single source of truth.
"""
 
# ─────────────────────────────────────────────────────────────
# HOSPITAL MASTER DATA
# ─────────────────────────────────────────────────────────────
HOSPITALS = {
    "City General Hospital": {
        "address": "MG Road, Pune, Maharashtra 411001",
        "lat": 18.5204,
        "lng": 72.8567,
        "specialty": "Multi-specialty",
        "phone": "+91-20-2612-3456",
        "color": "#6366f1",
    },
    "Apollo MediCare": {
        "address": "Baner Road, Pune, Maharashtra 411045",
        "lat": 18.5590,
        "lng": 73.7868,
        "specialty": "Super-specialty",
        "phone": "+91-20-6620-0000",
        "color": "#0ea5e9",
    },
    "Sunrise Health Centre": {
        "address": "Kothrud, Pune, Maharashtra 411038",
        "lat": 18.5074,
        "lng": 73.8077,
        "specialty": "General",
        "phone": "+91-20-2544-1234",
        "color": "#f59e0b",
    },
    "St. Mary's Hospital": {
        "address": "Camp Area, Pune, Maharashtra 411001",
        "lat": 18.5167,
        "lng": 73.8706,
        "specialty": "Multi-specialty",
        "phone": "+91-20-2612-7890",
        "color": "#10b981",
    },
}
 
# ─────────────────────────────────────────────────────────────
# CREDENTIALS  (username → {password, hospital})
# ─────────────────────────────────────────────────────────────
DOCTOR_CREDS = {
    "dr.sharma": {"password": "doc123", "name": "Dr. Priya Sharma"},
    "dr.patel":  {"password": "doc456", "name": "Dr. Rohan Patel"},
    "dr.mehta":  {"password": "med789", "name": "Dr. Anita Mehta"},
    "dr.khan":   {"password": "doc321", "name": "Dr. Salman Khan"},
}
 
STAFF_CREDS = {
    "admin":      {"password": "staff123", "name": "Admin"},
    "nurse1":     {"password": "nurse456", "name": "Nurse Priya"},
    "reception":  {"password": "rec789",   "name": "Reception"},
    "manager":    {"password": "mgr123",   "name": "Manager"},
}
 
# ─────────────────────────────────────────────────────────────
# COMPLAINT OPTIONS
# ─────────────────────────────────────────────────────────────
COMPLAINTS = [
    "Fever / Cold / Cough",
    "Chest Pain",
    "Abdominal Pain",
    "Head Injury / Trauma",
    "Fracture / Orthopaedic",
    "Eye / ENT Issue",
    "Skin Problem / Rash",
    "Gynaecology",
    "Paediatric Issue",
    "Dental Pain",
    "Mental Health",
    "Neurological Issue",
    "Diabetes / BP Check",
    "Other",
]
 
 
# ─────────────────────────────────────────────────────────────
# WARD TYPES
# ─────────────────────────────────────────────────────────────
WARD_TYPES = ["General", "ICU", "Emergency", "OPD"]
 
WARD_COLORS = {
    "General":   {"bg": "#22c55e", "border": "#16a34a", "badge": "#dcfce7", "text": "#166534"},
    "ICU":       {"bg": "#6366f1", "border": "#4f46e5", "badge": "#ede9fe", "text": "#4c1d95"},
    "Emergency": {"bg": "#ef4444", "border": "#dc2626", "badge": "#fee2e2", "text": "#7f1d1d"},
    "OPD":       {"bg": "#f59e0b", "border": "#d97706", "badge": "#fef3c7", "text": "#78350f"},
}
# ─────────────────────────────────────────────────────────────
# SESSION STATE BOOTSTRAP
# ─────────────────────────────────────────────────────────────
def init_state():
    import streamlit as st
    defaults = {
        # patients list[dict] — local cache, synced from DB
        "patients": [],
        "token_counter": 1000,
 
        # beds — ward-based structure {hospital: {ward: {total, available}}}
        "beds": {
            "City General Hospital": {
                "General":   {"total": 15, "available": 10},
                "ICU":       {"total": 3,  "available": 2},
                "Emergency": {"total": 2,  "available": 1},
                "OPD":       {"total": 5,  "available": 5},
            },
            "Apollo MediCare": {
                "General":   {"total": 20, "available": 2},
                "ICU":       {"total": 5,  "available": 1},
                "Emergency": {"total": 3,  "available": 1},
                "OPD":       {"total": 8,  "available": 0},
            },
            "Sunrise Health Centre": {
                "General":   {"total": 10, "available": 10},
                "ICU":       {"total": 2,  "available": 2},
                "Emergency": {"total": 2,  "available": 2},
                "OPD":       {"total": 6,  "available": 6},
            },
            "St. Mary's Hospital": {
                "General":   {"total": 15, "available": 6},
                "ICU":       {"total": 4,  "available": 2},
                "Emergency": {"total": 3,  "available": 1},
                "OPD":       {"total": 8,  "available": 3},
            },
        },
 
        # role navigation
        "role": "Patient",
 
        # patient session
        "pat_step":     "select_hospital",
        "pat_hospital": None,
        "pat_token":    None,
        "pat_mobile":   None,
        "pat_name":     None,
 
        # auth
        "doc_logged_in":   False,
        "doc_username":    None,
        "doc_hospital":    None,
        "staff_logged_in": False,
        "staff_username":  None,
        "staff_hospital":  None,
 
        # DB state
        "db_synced":   False,
        "sb_client":   None,
        "sb_error":    None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
 
    # ── Sync from Supabase on first load ──────────────────────
    if not st.session_state.db_synced:
        try:
            from database import sync_all
            err = sync_all()
            st.session_state.db_synced = True
            if err:
                st.session_state.sb_error = err
        except Exception as e:
            st.session_state.db_synced = True   # don't retry every render
            st.session_state.sb_error  = str(e)
 
 
# ─────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────
def next_token():
    import streamlit as st
    st.session_state.token_counter += 1
    return st.session_state.token_counter
 
def get_queue(hospital):
    import streamlit as st
    return [p for p in st.session_state.patients
            if p["hospital"] == hospital and p["status"] == "waiting"]
 
def get_patient_by_token(token):
    import streamlit as st
    for p in st.session_state.patients:
        if p["token"] == token:
            return p
    return None
 
def queue_position(patient):
    q = get_queue(patient["hospital"])
    for i, p in enumerate(q):
        if p["token"] == patient["token"]:
            return i + 1
    return None
 
def _ensure_ward_format(hospital):
    """
    Guarantee beds[hospital] is always ward-based dict.
    If Supabase sync loaded the old flat format {total, available},
    spread it across the 4 wards evenly so the UI never crashes.
    """
    import streamlit as st
    data = st.session_state.beds.get(hospital, {})
    if not data:
        return {}
    # Detect old flat format: values are ints, not dicts
    first_val = next(iter(data.values()))
    if isinstance(first_val, int):
        # Old format — migrate on the fly
        total = data.get("total", 20)
        avail = data.get("available", 10)
        per_ward_t = max(1, total  // 4)
        per_ward_a = max(0, avail  // 4)
        ward_data = {
            "General":   {"total": per_ward_t,   "available": per_ward_a},
            "ICU":       {"total": max(1, total//8), "available": max(0, avail//8)},
            "Emergency": {"total": max(1, total//10),"available": max(0, avail//10)},
            "OPD":       {"total": per_ward_t,   "available": per_ward_a},
        }
        st.session_state.beds[hospital] = ward_data
        return ward_data
    return data
 
def bed_status_color(hospital):
    import streamlit as st
    wards = _ensure_ward_format(hospital)
    total = sum(w["total"] for w in wards.values())
    avail = sum(w["available"] for w in wards.values())
    pct = avail / total if total else 0
    if pct > 0.3:  return "#16a34a"
    if pct > 0.1:  return "#d97706"
    return "#ef4444"
 
def total_available_beds(hospital):
    import streamlit as st
    wards = _ensure_ward_format(hospital)
    return sum(w["available"] for w in wards.values())
 
def total_beds(hospital):
    import streamlit as st
    wards = _ensure_ward_format(hospital)
    return sum(w["total"] for w in wards.values())
 
def timestamp():
    from datetime import datetime
    return datetime.now().strftime("%H:%M")
 