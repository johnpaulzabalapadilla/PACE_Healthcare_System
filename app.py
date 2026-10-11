import streamlit as st
import psycopg2
import pandas as pd
import random
import base64
from datetime import datetime
import google.generativeai as genai

# Page setup
st.set_page_config(page_title="P.A.C.E. Healthcare System", page_icon="🏥", layout="wide")

# General Styling
st.markdown("""
    <style>
        .main {
            background-color: #f4fbf7;
        }
        .stButton>button {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border-radius: 12px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            border: none;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #059669 0%, #047857 100%);
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
        }
        div.stMetric {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            border-top: 4px solid #10b981;
        }
        .kiosk-header {
            background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 20px;
        }
        .prescription-doc {
            background-color: white;
            border: 2px solid #047857;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            font-family: 'Arial', sans-serif;
            color: #1a1a1a;
        }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM NAVIGATION SIDEBAR ---
# Toggle/Checkbox para sa Admin/Doctor testing habang nasa Patient Kiosk
show_sidebar_in_kiosk = st.sidebar.checkbox("🔓 Show Sidebar Menu in Patient Kiosk", value=True)

system_role = st.sidebar.radio("🌐 Select System Portal", ["🏥 Patient Kiosk", "👨‍⚕️ Doctor Portal", "📋 Helpdesk / Admin Desk"])

# 🔒 HIDDEN SIDEBAR LOGIC: Kapag Patient Kiosk ang napili AT NAKA-OFF ang toggle, itatago ang sidebar gamit ang CSS!
if system_role == "🏥 Patient Kiosk" and not show_sidebar_in_kiosk:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

# Configure Gemini API
API_KEY = st.secrets.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

if API_KEY and API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=API_KEY.strip())

SUPABASE_CONN_STRING = "postgresql://postgres.pafsrnguwnpagyytzirx:pacekiosk2027@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def get_supabase_conn():
    return psycopg2.connect(SUPABASE_CONN_STRING)

# --- DATABASE HELPERS ---
def get_patient_by_id(p_id):
    try:
        conn = get_supabase_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (p_id.strip(),))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return {"id": row[0], "name": row[1], "age": row[2], "address": row[3], "contact": row[4], "philhealth_id": row[5]}
    except Exception as e:
        st.error(f"Database Error: {e}")
    return None

def register_new_patient(p_id, name, age, address, contact, philhealth):
    conn = get_supabase_conn()
    cursor = conn.cursor()
    success = False
    try:
        cursor.execute("""
            INSERT INTO patients (patient_id, name, age, address, contact, philhealth_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (p_id.strip(), name, age, address, contact, philhealth))
        conn.commit()
        success = True
    except Exception as e:
        st.error(f"Registration Error: {e}")
    finally:
        cursor.close()
        conn.close()
    return success

def book_appointment(p_id, doc_name, app_date, app_time):
    conn = get_supabase_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments (patient_id, doctor_name, appointment_date, appointment_time)
        VALUES (%s, %s, %s, %s)
    """, (p_id, doc_name, str(app_date), str(app_time)))
    conn.commit()
    cursor.close()
    conn.close()

def log_consultation(p_id, temp, hr, bp, symptoms):
    conn = get_supabase_conn()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    severity = "SEVERE" if any(w in symptoms.lower() for w in ["chest pain", "breathing", "stroke", "bleeding", "masakit ang dibdib"]) else "NORMAL"
    cursor.execute("""
        INSERT INTO patient_logs (timestamp, patient_id, temperature, heart_rate, blood_pressure, symptoms, severity_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (now, p_id, str(temp), str(hr), str(bp), symptoms, severity))
    conn.commit()
    cursor.close()
    conn.close()
    return severity

def save_prescription(p_id, doc_name, diagnosis, meds, instructions, signature_b64):
    conn = get_supabase_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prescriptions (patient_id, doctor_name, diagnosis, medicines, instructions, doctor_signature)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (p_id, doc_name, diagnosis, meds, instructions, signature_b64))
    conn.commit()
    cursor.close()
    conn.close()

def get_doctor_roster_names():
    return ["Dr. Sarah Evans", "Dr. Marcus Vance", "Dr. Althea Reyes", "Dr. Jonathan Cross", "Dr. Paul"]

# ==============================================================================
# 1️⃣ PATIENT KIOSK PORTAL
# ==============================================================================
if system_role == "🏥 Patient Kiosk":
    st.markdown("""
        <div class="kiosk-header">
            <h1 style='margin: 0;'>🏥 P.A.C.E. Patient Service Station</h1>
            <p style='color: #a7f3d0; margin-top: 5px;'>Automated Health Check & Instant Triage Desk</p>
        </div>
    """, unsafe_allow_html=True)

    if "kiosk_page" not in st.session_state: st.session_state.kiosk_page = "login"
    if "active_patient" not in st.session_state: st.session_state.active_patient = None

    if st.session_state.kiosk_page == "login":
        col_a, col_b, col_c = st.columns([1, 1.5, 1])
        with col_b:
            st.subheader("🔑 Enter Patient ID")
            search_id = st.text_input("🔍 Patient ID / Student Number")
            if search_id:
                patient = get_patient_by_id(search_id)
                if patient:
                    st.success(f"Welcome back, **{patient['name']}**!")
                    if st.button("Proceed to Kiosk Station ➜", use_container_width=True):
                        st.session_state.active_patient = patient
                        st.session_state.kiosk_page = "diagnostics"
                        st.rerun()
                else:
                    st.info("⚠️ Account not registered. Please fill out details below.")
                    with st.form("reg_form"):
                        p_name = st.text_input("Full Legal Name *")
                        p_age = st.number_input("Age *", min_value=1, value=20)
                        p_contact = st.text_input("Contact Number *")
                        p_philhealth = st.text_input("PhilHealth Number")
                        p_address = st.text_area("Residential Address *")
                        if st.form_submit_button("Register & Continue", use_container_width=True):
                            if p_name and p_contact and p_address:
                                if register_new_patient(search_id, p_name, p_age, p_address, p_contact, p_philhealth):
                                    st.session_state.active_patient = get_patient_by_id(search_id)
                                    st.session_state.kiosk_page = "diagnostics"
                                    st.rerun()

    elif st.session_state.kiosk_page == "diagnostics":
        patient = st.session_state.active_patient
        col_head1, col_head2 = st.columns([3, 1])
        with col_head1: st.success(f"👤 Patient Session: **{patient['name']}** (ID: `{patient['id']}`)")
        with col_head2:
            if st.button("🚪 Logout Session", use_container_width=True):
                st.session_state.kiosk_page = "login"
                st.session_state.active_patient = None
                if "kiosk_messages" in st.session_state: del st.session_state.kiosk_messages
                st.rerun()

        col1, col2 = st.columns([1, 1.2], gap="large")
        with col1:
            st.subheader("1️⃣ Biometrics & Vitals Scan")
            if st.button("🌿 SCAN VITALS NOW", use_container_width=True):
                st.session_state["k_temp"] = round(random.uniform(36.2, 38.9), 1)
                st.session_state["k_hr"] = random.randint(65, 110)
                st.session_state["k_bp"] = f"{random.randint(110, 145)}/{random.randint(70, 95)}"
                st.toast("Vitals scanned successfully!")

            t, h, b = st.session_state.get("k_temp", "--"), st.session_state.get("k_hr", "--"), st.session_state.get("k_bp", "--")
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Temp (°C)", f"{t}")
            m_col2.metric("Heart (BPM)", f"{h}")
            m_col3.metric("BP", f"{b}")

            st.write("---")
            st.subheader("2️⃣ Appointment Booking")
            with st.form("book_form"):
                doc = st.selectbox("Select Available Doctor", options=get_doctor_roster_names())
                a_date = st.date_input("Preferred Date")
                a_time = st.selectbox("Time Slot", ["09:00 AM", "10:30 AM", "02:00 PM", "03:30 PM"])
                if st.form_submit_button("Confirm Booking Slot", use_container_width=True):
                    book_appointment(patient["id"], doc, a_date, a_time)
                    st.success(f"🎉 Slot confirmed with {doc}!")

        with col2:
            st.subheader("3️⃣ Symptom Assessment Assistant")
            if "kiosk_messages" not in st.session_state:
                st.session_state.kiosk_messages = [{"role": "assistant", "content": f"Hello {patient['name']}! What symptoms are you experiencing right now?"}]

            for m in st.session_state.kiosk_messages:
                with st.chat_message(m["role"]): st.write(m["content"])

            if prompt := st.chat_input("Type your symptoms here..."):
                with st.chat_message("user"): st.write(prompt)
                st.session_state.kiosk_messages.append({"role": "user", "content": prompt})

                vt = st.session_state.get("k_temp", "Not scanned")
                vh = st.session_state.get("k_hr", "Not scanned")
                vb = st.session_state.get("k_bp", "Not scanned")

                tag = log_consultation(patient["id"], vt, vh, vb, prompt)
                if tag == "SEVERE": st.error("🚨 Emergency Warning: Severe symptoms flagged!")

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing..."):
                        try:
                            sys_instruction = (
                                "You are an empathetic and professional clinical triage assistant for a healthcare kiosk. "
                                "Analyze the patient's vitals (temperature, heart rate, and blood pressure) alongside their reported symptoms.\n\n"

                                "1. Language Adaptation:\n"
                                "   - Detect the patient's language. If they ask in Tagalog/Filipino, respond entirely in Tagalog. "
                                "If English, respond in English. If Taglish, respond in natural Taglish.\n\n"

                                "2. Triage Assessment & Response Structure:\n"
                                "   - Urgency Check: If vitals are abnormal (e.g., Temp >= 38.0°C, BP >= 140/90) or symptoms suggest high severity, start with a bold ⚠️ URGENT CARE NOTICE.\n"
                                "   - Immediate Comfort & First Aid: Provide 3-4 actionable, clear comfort or first-aid recommendations in Markdown bullet points tailored specifically to their symptoms.\n"
                                "   - What to Expect: Briefly mention what the attending physician will evaluate during check-up to ease patient anxiety.\n\n"

                                "3. Tone & Medical Safety:\n"
                                "   - Keep a supportive, calming, and concise professional tone.\n"
                                "   - Do NOT provide formal medical diagnoses or exact medication prescriptions.\n"
                                "   - Always end with a clear reminder that a doctor consultation is strictly required for an official diagnosis and treatment plan."
                            )
                            # Inayos ang model name sa gemini-1.5-flash-latest para hindi na mag-404 error
                            model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest', system_instruction=sys_instruction)
                            response = model.generate_content(f"Vitals: Temp {vt}°C, HR {vh} BPM, BP {vb}. Symptoms: {prompt}").text
                        except Exception as e:
                            response = f"⚠️ API Error: {str(e)}\n\n🩺 Please rest and consult the attending doctor."
                        
                        st.write(response)
                st.session_state.kiosk_messages.append({"role": "assistant", "content": response})

# ==============================================================================
# 2️⃣ DOCTOR PORTAL
# ==============================================================================
elif system_role == "👨‍⚕️ Doctor Portal":
    st.title("👨‍⚕️ Doctor Consultation Dashboard")
    
    col_doc_header, col_refresh = st.columns([3, 1])
    with col_doc_header:
        selected_doc = st.selectbox("🔑 Select / Login as Doctor:", get_doctor_roster_names())
    with col_refresh:
        st.write(" ")
        st.write(" ")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    conn = get_supabase_conn()
    df_all_patients = pd.read_sql_query("""
        SELECT DISTINCT p.patient_id, p.name, p.age, p.contact
        FROM patients p
        LEFT JOIN appointments a ON p.patient_id = a.patient_id
        LEFT JOIN patient_logs l ON p.patient_id = l.patient_id
        WHERE a.doctor_name = %s OR l.patient_id IS NOT NULL
    """, conn, params=(selected_doc,))
    conn.close()

    st.subheader(f"📅 Active Patients assigned or with Vitals Scanned ({selected_doc})")
    
    if df_all_patients.empty:
        st.info("No active patient logs or appointments found yet.")
    else:
        st.dataframe(df_all_patients, use_container_width=True)
        selected_p_id = st.selectbox("🔍 Select Patient ID to Examine Record & Chat Log:", df_all_patients["patient_id"].unique())

        if selected_p_id:
            conn = get_supabase_conn()
            logs = pd.read_sql_query("SELECT timestamp, temperature, heart_rate, blood_pressure, symptoms, severity_status FROM patient_logs WHERE patient_id = %s ORDER BY timestamp DESC", conn, params=(selected_p_id,))
            conn.close()

            st.write("---")
            st.markdown(f"### 📊 Scanned Vitals & Chatbot History (Patient: `{selected_p_id}`)")
            if not logs.empty:
                st.dataframe(logs, use_container_width=True)
                st.write("💬 **Patient Chat & Symptoms Log:**")
                for index, row in logs.iterrows():
                    st.chat_message("user").write(
                        f"**[{row['timestamp']}] Scanned Vitals:** Temp: {row['temperature']}°C | BP: {row['blood_pressure']} | HR: {row['heart_rate']}\n\n"
                        f"**Reported Symptom/Convo:** {row['symptoms']}"
                    )
            else:
                st.warning("No vitals/chat logs found for this patient.")

            st.write("---")
            st.subheader("✍️ Issue Signed Digital Prescription")
            with st.form("prescription_form"):
                diag = st.text_area("Clinical Diagnosis *")
                meds = st.text_area("Prescribed Medicines (Name, Dosage, Frequency) *", placeholder="e.g. Paracetamol 500mg - 1 tablet every 6 hours for 3 days")
                inst = st.text_area("Special Instructions / Advice", placeholder="e.g. Drink plenty of fluids and get adequate rest.")
                
                st.write("✍️ **Doctor's E-Signature:**")
                sig_type = st.radio("Signature Format:", ["Upload Signature Image (PNG/JPG)", "Type Full Digital Signature Name"], horizontal=True)
                
                sig_b64 = ""
                uploaded_sig = None
                typed_sig = ""
                
                if sig_type == "Upload Signature Image (PNG/JPG)":
                    uploaded_sig = st.file_uploader("Upload signature PNG/JPG image", type=["png", "jpg", "jpeg"])
                else:
                    typed_sig = st.text_input("Type Digital Signature Verification", value=f"{selected_doc}, M.D.")

                if st.form_submit_button("💾 Save & Sign Prescription", use_container_width=True):
                    if diag and meds:
                        if uploaded_sig is not None:
                            sig_bytes = uploaded_sig.read()
                            sig_b64 = "data:image/png;base64," + base64.b64encode(sig_bytes).decode("utf-8")
                        else:
                            sig_b64 = f"TEXT_SIG:{typed_sig if typed_sig else selected_doc}"

                        save_prescription(selected_p_id, selected_doc, diag, meds, inst, sig_b64)
                        st.success("✅ Signed Prescription saved successfully! Admin/Helpdesk can now view and print it.")

# ==============================================================================
# 3️⃣ HELPDESK / ADMIN DESK PORTAL
# ==============================================================================
elif system_role == "📋 Helpdesk / Admin Desk":
    st.title("📋 Helpdesk & General Patient Registry")
    
    col_hd_title, col_hd_ref = st.columns([3, 1])
    with col_hd_ref:
        if st.button("🔄 Refresh Admin Data", use_container_width=True):
            st.rerun()

    conn = get_supabase_conn()
    all_patients = pd.read_sql_query("SELECT * FROM patients ORDER BY patient_id DESC", conn)
    all_appointments = pd.read_sql_query("SELECT * FROM appointments", conn)
    conn.close()

    st.subheader("👥 All Registered Patients")
    if not all_patients.empty:
        booked_ids = all_appointments["patient_id"].tolist() if not all_appointments.empty else []
        all_patients["Status"] = all_patients["patient_id"].apply(lambda x: "Booked" if x in booked_ids else "Walk-in / Kiosk Logged")
        st.dataframe(all_patients, use_container_width=True)

        selected_pid_hd = st.selectbox("🔍 Select Patient ID to View Full Docs & Print Prescription:", all_patients["patient_id"].unique())

        if selected_pid_hd:
            conn = get_supabase_conn()
            p_info = get_patient_by_id(selected_pid_hd)
            p_logs = pd.read_sql_query("SELECT timestamp, temperature, heart_rate, blood_pressure, symptoms FROM patient_logs WHERE patient_id = %s ORDER BY timestamp DESC", conn, params=(selected_pid_hd,))
            p_presc = pd.read_sql_query("SELECT * FROM prescriptions WHERE patient_id = %s ORDER BY created_at DESC", conn, params=(selected_pid_hd,))
            conn.close()

            col_left, col_right = st.columns([1, 1.2])

            with col_left:
                st.markdown("### 📜 Full Vitals & Chat History")
                st.json(p_info)
                if not p_logs.empty:
                    st.dataframe(p_logs, use_container_width=True)
                else:
                    st.info("No vitals logged yet.")

            with col_right:
                st.markdown("### 📄 Signed Digital Prescription (Printable Docs View)")
                if not p_presc.empty:
                    latest_p = p_presc.iloc[0]
                    
                    formatted_meds = str(latest_p['medicines']).replace('\n', '<br>')
                    sig_data = str(latest_p.get('doctor_signature', ''))

                    if sig_data.startswith("data:image"):
                        signature_html = f'<img src="{sig_data}" style="max-height: 60px; max-width: 200px; display: block; margin-left: auto;" alt="Doctor Signature"/>'
                    elif sig_data.startswith("TEXT_SIG:"):
                        sig_text = sig_data.replace("TEXT_SIG:", "")
                        signature_html = f'<p style="font-family: \'Brush Script MT\', cursive, cursive; font-size: 24px; color: #064e3b; margin: 0; text-align: right;">{sig_text}</p>'
                    else:
                        signature_html = f'<p style="font-family: \'Brush Script MT\', cursive, cursive; font-size: 22px; color: #064e3b; margin: 0; text-align: right;">{latest_p["doctor_name"]}</p>'

                    prescription_html = f"""
                    <div class="prescription-doc">
                        <h2 style="text-align: center; color: #064e3b; margin-bottom: 0;">P.A.C.E. MEDICAL CLINIC</h2>
                        <p style="text-align: center; color: #666; font-size: 0.85rem; margin-top: 2px;">Official Signed Prescription Document</p>
                        <hr style="border: 1px solid #10b981;">
                        <p><b>Date:</b> {latest_p['created_at']} <span style="float:right;"><b>Rx No:</b> #{latest_p['id']}</span></p>
                        <p><b>Patient Name:</b> {p_info['name']} (Age: {p_info['age']})</p>
                        <p><b>Attending Physician:</b> {latest_p['doctor_name']}</p>
                        <hr>
                        <p><b>Diagnosis:</b><br>{latest_p['diagnosis']}</p>
                        <h3 style="color: #047857; margin-bottom: 5px;">Rx - Prescribed Medicines:</h3>
                        <p style="background-color: #f4fbf7; padding: 10px; border-radius: 5px; font-family: monospace;">{formatted_meds}</p>
                        <p><b>Special Instructions:</b><br>{latest_p['instructions']}</p>
                        <br>
                        <div style="text-align: right;">
                            {signature_html}
                            <p style="margin-top: 0; margin-bottom: 0;">_______________________<br><b>{latest_p['doctor_name']}</b><br>Licensed Physician</p>
                        </div>
                    </div>
                    """
                    st.markdown(prescription_html, unsafe_allow_html=True)
                    st.caption("💡 *Tip: Press `Ctrl + P` (or `Cmd + P`) in your browser to print this prescription or save it as PDF.*")
                else:
                    st.warning("⚠️ No Doctor Prescription found for this patient yet.")
    else:
        st.info("No registered patients found in Supabase.")
