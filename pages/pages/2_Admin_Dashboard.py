import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

st.set_page_config(page_title="P.A.C.E. Admin Help Desk", page_icon="🖥️", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        .main { background-color: #f8fafc; }
        .admin-header {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            padding: 25px; border-radius: 20px; color: white; margin-bottom: 25px;
        }
        .prescription-doc {
            background-color: #ffffff;
            border: 2px solid #312e81;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            font-family: Arial, sans-serif;
            color: #1a1a1a;
        }
        .rx-box {
            background-color: #f1f5f9;
            padding: 10px;
            border-radius: 6px;
            font-family: monospace;
            margin-top: 5px;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

SUPABASE_CONN_STRING = "postgresql://postgres.pafsrnguwnpagyytzirx:pacekiosk2027@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def get_supabase_conn():
    return psycopg2.connect(SUPABASE_CONN_STRING)

def get_all_appointments_df():
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("""
            SELECT a.appointment_date AS "Date", a.appointment_time AS "Time Slot",
                   p.name AS "Patient Name", a.doctor_name AS "Assigned Doctor", a.status AS "Status"
            FROM appointments a JOIN patients p ON a.patient_id = p.patient_id
            ORDER BY a.appointment_date ASC
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def get_prescriptions_df():
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("""
            SELECT id, patient_id, patient_name AS "Patient Name", doctor_name AS "Prescribing Doctor", 
                   diagnosis, medications AS "Medications", lab_orders AS "Lab Orders", 
                   instructions, doctor_signature, status AS "Order Status", date_issued AS "Date/Time"
            FROM prescriptions ORDER BY date_issued DESC
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# INVENTORY HELPER FUNCTIONS
def get_inventory_df():
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("""
            SELECT id, medicine_name AS "Medicine", stock_quantity AS "Stock Level", unit AS "Unit", last_updated AS "Last Updated"
            FROM pharmacy_inventory ORDER BY medicine_name ASC
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def update_medicine_stock(med_id, new_qty):
    try:
        conn = get_supabase_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE pharmacy_inventory SET stock_quantity = %s, last_updated = CURRENT_TIMESTAMP WHERE id = %s", (new_qty, med_id))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False

def add_new_medicine(name, qty, unit):
    try:
        conn = get_supabase_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pharmacy_inventory (medicine_name, stock_quantity, unit) VALUES (%s, %s, %s)", (name, qty, unit))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False

def mark_prescription_fulfilled(rx_id, med_to_deduct=None, qty_to_deduct=0):
    try:
        conn = get_supabase_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE prescriptions SET status = 'DISPATCHED' WHERE id = %s", (rx_id,))
        
        if med_to_deduct and qty_to_deduct > 0:
            cursor.execute("""
                UPDATE pharmacy_inventory 
                SET stock_quantity = GREATEST(0, stock_quantity - %s), last_updated = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (qty_to_deduct, med_to_deduct))
            
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False

def get_logs_severity_df():
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("SELECT severity_status FROM patient_logs", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def get_severe_alerts():
    try:
        conn = get_supabase_conn()
        df = pd.read_sql_query("""
            SELECT l.timestamp, p.name, l.symptoms 
            FROM patient_logs l JOIN patients p ON l.patient_id = p.patient_id 
            WHERE l.severity_status = 'SEVERE' ORDER BY l.timestamp DESC LIMIT 5
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

st.markdown("""
    <div class="admin-header">
        <h1 style='margin: 0;'>🖥️ Central Administrative & Pharmacy Command Center</h1>
        <p style='color: #c7d2fe; margin-top: 6px;'>Real-time hospital analytics, appointments & pharmacy dispatch.</p>
    </div>
""", unsafe_allow_html=True)

alerts_df = get_severe_alerts()
if not alerts_df.empty:
    for _, row in alerts_df.iterrows():
        st.markdown(f"""
            <div style='background-color: #fff1f2; border-left: 6px solid #e11d48; padding: 14px; border-radius: 10px; color: #881337; margin-bottom: 10px;'>
                🚨 <b>CRITICAL INTERVENTION NEEDED:</b> Patient <b>{row['name']}</b> flagged SEVERE. Symptoms: <i>{row['symptoms']}</i>
            </div>
        """, unsafe_allow_html=True)

# TABS FOR BETTER ORGANIZATION
tab1, tab2, tab3, tab4 = st.tabs(["📊 Analytics & Triage", "📋 Master Appointments", "💊 Pharmacy & Lab Orders", "📦 Inventory & Stock Tracker"])

with tab1:
    st.subheader("Live Hospital Analytics")
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        logs_df = get_logs_severity_df()
        if not logs_df.empty:
            sev_counts = logs_df['severity_status'].value_counts().reset_index()
            sev_counts.columns = ['Severity', 'Count']
            fig1 = px.pie(sev_counts, names='Severity', values='Count', title="Patient Triage Severity Breakdown",
                          color='Severity', color_discrete_map={'NORMAL': '#10b981', 'SEVERE': '#ef4444'}, hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
    with chart_col2:
        apps_df = get_all_appointments_df()
        if not apps_df.empty:
            doc_counts = apps_df['Assigned Doctor'].value_counts().reset_index()
            doc_counts.columns = ['Doctor', 'Appointments']
            fig2 = px.bar(doc_counts, x='Doctor', y='Appointments', title="Doctor Workload Distribution",
                          color='Appointments', color_continuous_scale='teal')
            st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader("Master Appointment Registry")
    st.dataframe(get_all_appointments_df(), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("💊 Pharmacy & Laboratory Order Desk")
    rx_df = get_prescriptions_df()
    
    if not rx_df.empty:
        st.dataframe(rx_df[['id', 'Date/Time', 'Patient Name', 'Prescribing Doctor', 'Medications', 'Lab Orders', 'Order Status']], use_container_width=True, hide_index=True)
        
        st.write("---")
        col_disp, col_print = st.columns([1, 1.2], gap="large")
        
        with col_disp:
            st.markdown("##### 📦 Dispatch Fulfillment Action")
            pending_orders = rx_df[rx_df['Order Status'] == 'PENDING']
            if not pending_orders.empty:
                rx_to_fill = st.selectbox("Select Pending Order ID to Dispatch", pending_orders['id'].tolist())
                
                inv_df = get_inventory_df()
                deduct_med_id = None
                deduct_qty = 0
                
                if not inv_df.empty:
                    st.caption("Optional: Deduct inventory stock for this order")
                    med_map = dict(zip(inv_df['Medicine'], inv_df['id']))
                    selected_med_name = st.selectbox("Select Medicine Dispatched", ["None"] + list(med_map.keys()))
                    
                    if selected_med_name != "None":
                        deduct_med_id = med_map[selected_med_name]
                        deduct_qty = st.number_input("Quantity Dispatched", min_value=1, value=1)

                if st.button("Mark Order as DISPATCHED / READY 🚚", use_container_width=True):
                    if mark_prescription_fulfilled(rx_to_fill, deduct_med_id, deduct_qty):
                        st.success(f"Order #{rx_to_fill} marked as DISPATCHED and inventory updated!")
                        st.rerun()
            else:
                st.info("All pharmacy and lab orders are fully dispatched!")

        with col_print:
            st.markdown("##### 📄 Print Official Doctor E-Prescription")
            selected_rx_id = st.selectbox("Select Order ID to Print", rx_df['id'].tolist(), key="select_rx_print")
            
            sel_rx = rx_df[rx_df['id'] == selected_rx_id].iloc[0]
            
            diag_text = sel_rx['diagnosis'] if sel_rx['diagnosis'] else "N/A"
            meds_text = str(sel_rx['Medications']).replace('\n', '<br>') if sel_rx['Medications'] else "None"
            labs_text = str(sel_rx['Lab Orders']).replace('\n', '<br>') if sel_rx['Lab Orders'] else "None"
            inst_text = sel_rx['instructions'] if sel_rx['instructions'] else "None"
            
            sig_data = str(sel_rx.get('doctor_signature', ''))
            if sig_data.startswith("data:image"):
                signature_html = f'<img src="{sig_data}" style="max-height: 50px; max-width: 180px; display: block; margin-left: auto;" alt="Doctor Signature"/>'
            elif sig_data.startswith("TEXT_SIG:"):
                sig_text = sig_data.replace("TEXT_SIG:", "")
                signature_html = f'<p style="font-family: \'Brush Script MT\', cursive; font-size: 22px; color: #1e1b4b; margin: 0; text-align: right;">{sig_text}</p>'
            else:
                signature_html = f'<p style="font-family: \'Brush Script MT\', cursive; font-size: 22px; color: #1e1b4b; margin: 0; text-align: right;">{sel_rx["Prescribing Doctor"]}</p>'

            st.markdown(f"""
            <div class="prescription-doc">
                <h2 style="text-align: center; color: #1e1b4b; margin-bottom: 0;">P.A.C.E. MEDICAL CLINIC</h2>
                <p style="text-align: center; color: #666; font-size: 0.85rem; margin-top: 2px;">Official Physician E-Prescription & Requisition</p>
                <hr style="border: 1px solid #312e81;">
                <p style="margin-bottom: 4px;"><b>Date Issued:</b> {sel_rx['Date/Time']} <span style="float:right;"><b>Rx Order No:</b> #{sel_rx['id']}</span></p>
                <p style="margin-bottom: 4px;"><b>Patient Name:</b> {sel_rx['Patient Name']} (ID: {sel_rx['patient_id']})</p>
                <p style="margin-bottom: 4px;"><b>Attending Doctor:</b> {sel_rx['Prescribing Doctor']}</p>
                <hr>
                <p style="margin-bottom: 6px;"><b>Clinical Diagnosis:</b><br>{diag_text}</p>
                <h4 style="color: #1e1b4b; margin-bottom: 2px;">💊 Prescribed Medicines:</h4>
                <div class="rx-box">{meds_text}</div>
                <h4 style="color: #1e1b4b; margin-bottom: 2px;">🧪 Diagnostic Lab Orders:</h4>
                <div class="rx-box">{labs_text}</div>
                <p style="margin-bottom: 6px;"><b>Special Instructions:</b><br>{inst_text}</p>
                <br>
                <div style="text-align: right;">
                    {signature_html}
                    <p style="margin-top: 0; margin-bottom: 0;">_______________________<br><b>{sel_rx['Prescribing Doctor']}</b><br>Licensed Physician</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write(" ")
            components.html("""
                <button onclick="window.print()" style="
                    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 8px;
                    cursor: pointer;
                    width: 100%;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">🖨️ PRINT E-PRESCRIPTION NOW</button>
            """, height=60)
    else:
        st.info("No prescription or lab requisitions found in the database.")

with tab4:
    st.subheader("📦 Pharmacy Stock & Inventory Management")
    inv_df = get_inventory_df()
    
    if not inv_df.empty:
        st.dataframe(inv_df, use_container_width=True, hide_index=True)
        
        st.write("---")
        inv_col1, inv_col2 = st.columns(2, gap="large")
        
        with inv_col1:
            st.markdown("##### 🔄 Update Existing Stock")
            med_map = dict(zip(inv_df['Medicine'], zip(inv_df['id'], inv_df['Stock Level'])))
            selected_med = st.selectbox("Select Item to Update", list(med_map.keys()))
            selected_id, current_stock = med_map[selected_med]
            
            new_stock_qty = st.number_input("New Stock Level", min_value=0, value=current_stock)
            if st.button("Save Stock Level Update 💾", use_container_width=True):
                if update_medicine_stock(selected_id, new_stock_qty):
                    st.success(f"Stock for '{selected_med}' updated to {new_stock_qty}!")
                    st.rerun()

        with inv_col2:
            st.markdown("##### ➕ Register New Item to Inventory")
            new_med_name = st.text_input("Medicine Name & Dosage", placeholder="e.g. Cetirizine 10mg")
            new_med_qty = st.number_input("Initial Quantity", min_value=0, value=50)
            new_med_unit = st.selectbox("Unit", ["tablets", "capsules", "bottles", "boxes", "vials"])
            
            if st.button("Add New Medicine to Inventory 🚀", use_container_width=True):
                if new_med_name:
                    if add_new_medicine(new_med_name, new_med_qty, new_med_unit):
                        st.success(f"Added '{new_med_name}' to inventory!")
                        st.rerun()
                else:
                    st.warning("Please enter a medicine name.")
    else:
        st.info("No inventory items found. Please execute the SQL table initialization query in Supabase first.")
