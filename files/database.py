"""
database.py — Supabase via direct HTTP REST API.
No supabase Python package needed — works on ANY Python version including 3.14.
Uses only urllib from the standard library.
"""
 
import os, json, urllib.request, urllib.parse, urllib.error
import streamlit as st
from pathlib import Path
 
# ── Load .env ──────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)
except ImportError:
    pass
 
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
 
 
# ── HTTP helpers ───────────────────────────────────────────────
def _h():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
 
def _get(table, params={}):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return [], "No credentials"
    try:
        qs  = urllib.parse.urlencode({"select": "*", **params})
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{table}?{qs}", headers=_h())
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return [], f"HTTP {e.code}: {e.read().decode()}"
    except Exception as e:
        return [], str(e)
 
def _post(table, payload):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None, "No credentials"
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{table}",
            data=json.dumps(payload).encode(), headers=_h(), method="POST")
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
            return (rows[0] if rows else payload), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()}"
    except Exception as e:
        return None, str(e)
 
def _patch(table, filters, payload):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False, "No credentials"
    try:
        qs  = urllib.parse.urlencode(filters)
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{table}?{qs}",
            data=json.dumps(payload).encode(), headers=_h(), method="PATCH")
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
            return True, None
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()}"
    except Exception as e:
        return False, str(e)
 
 
# ── Connection ─────────────────────────────────────────────────
def is_connected():
    return bool(SUPABASE_URL and SUPABASE_KEY)
 
def test_connection():
    rows, err = _get("hospitals", {"limit": "1"})
    return (True, None) if not err else (False, err)
 
 
# ── Hospitals ──────────────────────────────────────────────────
def fetch_hospitals():
    rows, err = _get("hospitals")
    if not err:
        for h in rows:
            st.session_state.beds[h["name"]] = {
                "total": h["total_beds"], "available": h["available_beds"]}
    return rows, err
 
def update_beds(hospital_name, ward, total, available):
    """Update bed counts for a specific ward in a hospital."""
    if hospital_name in st.session_state.beds:
        if ward not in st.session_state.beds[hospital_name]:
            st.session_state.beds[hospital_name][ward] = {}
        st.session_state.beds[hospital_name][ward]["total"]     = total
        st.session_state.beds[hospital_name][ward]["available"] = available
    # For DB: store as ward-specific columns or JSON — simplified flat storage
    # We use a naming convention: ward_general_total, ward_icu_total etc.
    ward_key = ward.lower().replace(" ","_")
    return _patch("hospitals", {"name": f"eq.{hospital_name}"}, {
        f"{ward_key}_total":     total,
        f"{ward_key}_available": available,
    })
 
 
# ── Token ──────────────────────────────────────────────────────
def get_next_token():
    if not is_connected():
        st.session_state.token_counter += 1
        return st.session_state.token_counter
    try:
        rows, err = _get("token_sequence", {"id": "eq.1"})
        if err or not rows:
            raise Exception(err)
        new_val = rows[0]["last_token"] + 1
        _patch("token_sequence", {"id": "eq.1"}, {"last_token": new_val})
        st.session_state.token_counter = new_val
        return new_val
    except Exception:
        st.session_state.token_counter += 1
        return st.session_state.token_counter
 
 
# ── Credentials ────────────────────────────────────────────────
def _fallback_creds(username, password, role):
    from config import DOCTOR_CREDS, STAFF_CREDS
    creds = DOCTOR_CREDS if role == "doctor" else STAFF_CREDS
    if username in creds and creds[username]["password"] == password:
        return {"username": username, "full_name": creds[username]["name"], "role": role}, None
    return None, "Invalid credentials"
 
def verify_credential(username, password, role):
    if not is_connected():
        return _fallback_creds(username, password, role)
    rows, err = _get("credentials", {"username": f"eq.{username}", "role": f"eq.{role}"})
    if err or not rows:
        return _fallback_creds(username, password, role)
    row = rows[0]
    if row["password"] != password:
        return None, "Invalid credentials"
    return row, None
 
 
# ── Patients — create ──────────────────────────────────────────
def register_patient(patient):
    st.session_state.patients.append(patient)
    if not is_connected():
        return patient, None
    db_row = {
        "name": patient["name"], "phone": patient["phone"],
        "age": patient.get("age"), "gender": patient.get("gender"),
        "complaint": patient["complaint"], "notes": patient.get("notes", ""),
        "token": patient["token"], "status": patient["status"],
        "hospital_name": patient["hospital"],
        "is_emergency": patient.get("is_emergency", False),
        "registered_at": patient.get("registered_at", ""),
    }
    row, err = _post("patients", db_row)
    return row or patient, err
 
 
# ── Patients — read ────────────────────────────────────────────
def fetch_patients(hospital_name=None):
    if not is_connected():
        if hospital_name:
            return [p for p in st.session_state.patients
                    if p.get("hospital") == hospital_name], None
        return st.session_state.patients, None
    params = {"order": "created_at"}
    if hospital_name:
        params["hospital_name"] = f"eq.{hospital_name}"
    rows, err = _get("patients", params)
    if err:
        return st.session_state.patients, err
    normalised = [{**r, "hospital": r.get("hospital_name", "")} for r in rows]
    if hospital_name:
        st.session_state.patients = [
            p for p in st.session_state.patients
            if p.get("hospital") != hospital_name
        ] + normalised
    else:
        st.session_state.patients = normalised
    return normalised, None
 
def check_duplicate(phone, hospital_name):
    if not is_connected():
        matches = [p for p in st.session_state.patients
                   if p["phone"] == phone and p.get("hospital") == hospital_name
                   and p["status"] == "waiting"]
        return matches[0] if matches else None
    rows, _ = _get("patients", {"phone": f"eq.{phone}",
                                "hospital_name": f"eq.{hospital_name}",
                                "status": "eq.waiting"})
    if rows:
        return {**rows[0], "hospital": rows[0].get("hospital_name", "")}
    return None
 
 
# ── Patients — update ──────────────────────────────────────────
def update_patient_status(token, status, prescription=None, admitted_at=None, completed_at=None):
    for p in st.session_state.patients:
        if p["token"] == token:
            p["status"] = status
            if prescription is not None: p["prescription"] = prescription
            if admitted_at  is not None: p["admitted_at"]  = admitted_at
            if completed_at is not None: p["completed_at"] = completed_at
            break
    if not is_connected():
        return True, None
    payload = {"status": status}
    if prescription is not None: payload["prescription"] = prescription
    if admitted_at  is not None: payload["admitted_at"]  = admitted_at
    if completed_at is not None: payload["completed_at"] = completed_at
    return _patch("patients", {"token": f"eq.{token}"}, payload)
 
 
# ── Sync ───────────────────────────────────────────────────────
def sync_all():
    _, e1 = fetch_hospitals()
    _, e2 = fetch_patients()
    return f"hospitals: {e1} | patients: {e2}" if (e1 or e2) else None
 
 
# ── Banner ─────────────────────────────────────────────────────
def connection_banner():
    if not is_connected():
        st.markdown("""
        <div style="padding:6px 12px;background:#fefce8;border:1px solid #fde68a;
                    border-radius:8px;margin-bottom:16px;font-size:12px;color:#854d0e;">
            🟡 <strong>Offline mode</strong> — add SUPABASE_URL + SUPABASE_KEY to .env
        </div>""", unsafe_allow_html=True)
        return
    if "db_live" not in st.session_state:
        ok, err = test_connection()
        st.session_state.db_live     = ok
        st.session_state.db_live_err = err
    if st.session_state.get("db_live"):
        st.markdown("""
        <div style="padding:6px 12px;background:#f0fdf4;border:1px solid #bbf7d0;
                    border-radius:8px;margin-bottom:16px;font-size:12px;color:#166534;">
            🟢 <strong>Supabase connected</strong> — data persists to cloud
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="padding:6px 12px;background:#fff1f2;border:1px solid #fecaca;
                    border-radius:8px;margin-bottom:16px;font-size:12px;color:#b91c1c;">
            🔴 <strong>Supabase error</strong> — {st.session_state.get('db_live_err','')}
        </div>""", unsafe_allow_html=True)