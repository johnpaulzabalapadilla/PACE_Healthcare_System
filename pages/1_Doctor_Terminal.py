import streamlit as st
import psycopg2
import pandas as pd
import base64

st.set_page_config(page_title="P.A.C.E. Doctor Terminal", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        .main { background-color: #fafaf9; }
        .doc-header {
            background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
            padding: 25px; border-radius: 20px; color: white; margin-bottom: 25px;
        }
        .stButton>button {
            background: #0f766e; color: white; border-radius: 10px; font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

SUPABASE_CONN_STRING = "postgresql://postgres.pafsrnguwnpagyytzirx:pacekiosk2027@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def get_supabase_conn():
    return psycopg2.connect(SUPABASE_CONN_STRING)

def init_prescription_table():
    try:
        conn = get_supabase_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                id SERIAL PRIMARY KEY,
                patient_id VARCHAR(50),
                patient_name VARCHAR(100),
                doctor_name VARCHAR(100),
                diagnosis TEXT,
                medications TEXT,
                lab_orders TEXT,
                instructions TEXT,
                doctor_signature TEXT,
                status VARCHAR(20) DEFAULT 'PENDING',
                date_issued TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Table Init Error: {e}")

init_prescription_table()

def get_doctor_appointments_df(doc_name):
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("""
            SELECT a.appointment_date AS "Date", a.appointment_time AS "Time Slot",
                   p.name AS "Patient Name", p.patient_id AS "ID", p.age AS "Age", p.contact AS "Contact"
            FROM appointments a JOIN patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_name = %s ORDER BY a.appointment_date ASC
        """, conn, params=(doc_name,))
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def get_all_patients():
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("SELECT patient_id, name, age, contact FROM patients ORDER BY name ASC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def save_prescription(p_id, p_name, doc_name, diag, rx, labs, inst, sig_b64):
    try:
        conn = get_supabase_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prescriptions (patient_id, patient_name, doctor_name, diagnosis, medications, lab_orders, instructions, doctor_signature)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (p_id, p_name, doc_name, diag, rx, labs, inst, sig_b64))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

def get_doctor_prescription_history(doc_name):
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("""
            SELECT id AS "Rx ID", patient_name AS "Patient", diagnosis AS "Diagnosis", 
                   medications AS "Medications", status AS "Dispatch Status", date_issued AS "Date Issued"
            FROM prescriptions 
            WHERE doctor_name = %s 
            ORDER BY date_issued DESC
        """, conn, params=(doc_name,))
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def get_patient_timeline(patient_id):
    try:
        conn = get_supabase_conn()
        vitals_df = pd.read_sql_query("""
            SELECT timestamp AS "Date/Time", temperature AS "Temp (°C)", heart_rate AS "HR (BPM)", 
                   blood_pressure AS "BP", symptoms AS "Symptoms / Query"
            FROM patient_logs 
            WHERE patient_id = %s 
            ORDER BY timestamp DESC
        """, conn, params=(patient_id,))
        
        rx_df = pd.read_sql_query("""
            SELECT date_issued AS "Date", doctor_name AS "Doctor", diagnosis AS "Diagnosis", 
                   medications AS "Medications", lab_orders AS "Lab Orders" 
            FROM prescriptions 
            WHERE patient_id = %s 
            ORDER BY date_issued DESC
        """, conn, params=(patient_id,))
        
        conn.close()
        return vitals_df, rx_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

if "logged_doc" not in st.session_state: st.session_state.logged_doc = None

st.markdown("""
    <div class="doc-header">
        <h1 style='margin: 0;'>🩺 Practitioner Workspace & E-Prescription Portal</h1>
        <p style='color: #ccfbf1; margin-top: 6px;'>Encode digital prescriptions and diagnostic lab requisitions with E-Signatures.</p>
    </div>
""", unsafe_allow_html=True)

if not st.session_state.logged_doc:
    col_a, col_b, col_c = st.columns([1, 1.5, 1])
    with col_b:
        roster_names = ["Dr. Paul", "Dr. Generine", "Dr. Sean", "Dr. Nilda"]
        selected_doc = st.selectbox("⚕️ Select Your Name", options=roster_names)
        pin = st.text_input("🔑 Enter Security PIN", type="password")
        
        if st.button("Unlock Physician Ledger 🔓", use_container_width=True):
            doctor_pins = {"Dr. Paul": "1111", "Dr. Generine": "2222", "Dr. Sean": "3333", "Dr. Nilda": "4444"}
            if pin == doctor_pins.get(selected_doc):
                st.session_state.logged_doc = selected_doc
                st.rerun()
            else:
                st.error("Invalid Security PIN Code.")
else:
    doc = st.session_state.logged_doc
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1: st.markdown(f"### Practitioner: **{doc}**")
    with col_h2:
        if st.button("🚪 Logout Account", use_container_width=True):
            st.session_state.logged_doc = None
            st.rerun()
            
    st.write("---")
    
    tab_workspace, tab_dispatch = st.tabs(["🩺 Active Clinical Workspace", "📦 Direct Order Dispatch Status"])
    
    with tab_workspace:
        col1, col2 = st.columns([1.1, 1.3], gap="large")
        
        with col1:
            st.subheader("📋 Scheduled Appointments")
            apps_df = get_doctor_appointments_df(doc)
            if not apps_df.empty:
                st.dataframe(apps_df, use_container_width=True, hide_index=True)
            else:
                st.info("No scheduled appointments found for you today.")

            st.write("---")
            st.subheader("📊 Patient History & Timeline Viewer")
            
            all_patients_df = get_all_patients()
            if not all_patients_df.empty:
                p_map = dict(zip(all_patients_df['name'] + " (ID: " + all_patients_df['patient_id'] + ")", all_patients_df['patient_id']))
                selected_p_label = st.selectbox("🔍 Select Patient Records:", list(p_map.keys()))
                target_p_id = p_map[selected_p_label]

                past_vitals, past_rx = get_patient_timeline(target_p_id)
                hist_tab1, hist_tab2 = st.tabs(["📉 Vitals History", "💊 Past Prescriptions"])
                
                with hist_tab1:
                    if not past_vitals.empty:
                        st.dataframe(past_vitals, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No historical vitals records found for this patient.")
                        
                with hist_tab2:
                    if not past_rx.empty:
                        for idx, row in past_rx.iterrows():
                            with st.expander(f"🗓️ Visit on {row['Date']} — Dr. {row['Doctor']}"):
                                st.write(f"**Diagnosis:** {row['Diagnosis']}")
                                st.write(f"**Rx Medications:** {row['Medications']}")
                                st.write(f"**Lab Orders:** {row['Lab Orders']}")
                    else:
                        st.caption("No prior prescriptions found for this patient.")
            else:
                st.info("No registered patients in the database.")
                
        with col2:
            st.subheader("💊 Issue Signed E-Prescription & Lab Orders")
            all_patients_df = get_all_patients()
            
            if not all_patients_df.empty:
                patient_options = dict(zip(all_patients_df['name'] + " (ID: " + all_patients_df['patient_id'] + ")", zip(all_patients_df['patient_id'], all_patients_df['name'])))
                selected_rx_p_label = st.selectbox("Select Active Patient for Consultation", list(patient_options.keys()), key="rx_patient_select")
                selected_rx_id, selected_rx_name = patient_options[selected_rx_p_label]
                
                with st.form("rx_form"):
                    st.markdown(f"**Target Patient:** `{selected_rx_name}` (ID: `{selected_rx_id}`)")
                    
                    diag_input = st.text_area("🩺 Clinical Diagnosis", placeholder="e.g. Acute Upper Respiratory Tract Infection (URTI)")
                    rx_input = st.text_area("💊 Prescribed Medicines & Dosage *", placeholder="e.g. Paracetamol 500mg - 1 tab every 6 hours for 3 days\nAmoxicillin 500mg - 1 capsule 3x daily for 7 days")
                    lab_input = st.text_area("🧪 Lab Tests / Imaging Requisition", placeholder="e.g. Complete Blood Count (CBC), Chest X-Ray PA View")
                    inst_input = st.text_area("📝 Special Instructions / Advice", placeholder="e.g. Take medicines after meals. Drink plenty of water and rest.")
                    
                    st.write("✍️ **Physician Digital E-Signature:**")
                    sig_option = st.radio("Signature Style:", ["Upload Signature Image (PNG/JPG)", "Type Full Digital Signature Name"], horizontal=True)
                    
                    uploaded_sig = st.file_uploader("Upload signature image", type=["png", "jpg", "jpeg"]) if sig_option == "Upload Signature Image (PNG/JPG)" else None
                    typed_sig = st.text_input("Type Verification Signature", value=f"{doc}, M.D.") if sig_option != "Upload Signature Image (PNG/JPG)" else ""
                    
                    if st.form_submit_button("🚀 Submit & Send E-Prescription to Helpdesk", use_container_width=True):
                        if rx_input or lab_input or diag_input:
                            if uploaded_sig is not None:
                                sig_b64 = "data:image/png;base64," + base64.b64encode(uploaded_sig.read()).decode("utf-8")
                            else:
                                sig_b64 = f"TEXT_SIG:{typed_sig if typed_sig else doc}"

                            if save_prescription(selected_rx_id, selected_rx_name, doc, diag_input, rx_input, lab_input, inst_input, sig_b64):
                                st.success(f"🎉 Signed E-Prescription & Lab Order transmitted to Help Desk for **{selected_rx_name}**!")
                        else:
                            st.warning("Please enter at least a diagnosis, prescribed medicine, or lab order.")
            else:
                st.info("No registered patients found in database.")

    with tab_dispatch:
        st.subheader("📦 Live Pharmacy Dispatch Status Tracker")
        st.caption("Track in real-time whether the Help Desk / Pharmacy has fulfilled your issued prescriptions.")
        
        doc_history_df = get_doctor_prescription_history(doc)
        if not doc_history_df.empty:
            st.dataframe(
                doc_history_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No prescriptions recorded for your account yet.")
