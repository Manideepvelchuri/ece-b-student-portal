import os
import json
import time
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime

# Import scraper from harvester
import harvester

# Page Configuration
st.set_page_config(
    page_title="VITS ECE-B Student Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Premium Aesthetics
st.markdown("""
<style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Main layout font override */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Custom Card CSS */
    .kpi-card {
        background-color: #0f172a;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
        text-align: center;
        border: 1px solid #1e293b;
        margin-bottom: 20px;
        transition: transform 0.2s ease-in-out;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
    }
    .kpi-card-red {
        background-color: #450a0a;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
        text-align: center;
        border: 1px solid #dc2626;
        color: #fca5a5;
        margin-bottom: 20px;
    }
    .kpi-card-green {
        background-color: #064e3b;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
        text-align: center;
        border: 1px solid #10b981;
        color: #a7f3d0;
        margin-bottom: 20px;
    }
    .kpi-title {
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
        color: #94a3b8;
    }
    .kpi-value {
        font-size: 36px;
        font-weight: 700;
        margin: 0;
    }
    
    /* Quick alignment tweaks */
    div.stButton > button:first-child {
        background-color: #2563eb;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
        transition: all 0.2s;
    }
    div.stButton > button:first-child:hover {
        background-color: #1d4ed8;
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# Path Configurations
CSV_ATTENDANCE_PATH = os.path.join(os.path.dirname(__file__), "attendance_master.csv")
CSV_ATTENDANCE_FALLBACK = os.path.join(os.path.dirname(__file__), "Attendance_Report_ECE_B.csv")
CSV_RESULTS_PATH = os.path.join(os.path.dirname(__file__), "sem1_results.csv")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Helper function to load attendance records safely
def load_attendance_data():
    path = CSV_ATTENDANCE_PATH if os.path.exists(CSV_ATTENDANCE_PATH) else CSV_ATTENDANCE_FALLBACK
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        st.error(f"Error loading attendance: {e}")
        return None

# Helper function to load results dataset safely
def load_results_data():
    if not os.path.exists(CSV_RESULTS_PATH):
        return None
    try:
        return pd.read_csv(CSV_RESULTS_PATH)
    except Exception as e:
        st.error(f"Error loading results: {e}")
        return None

# Save results dataset safely
def save_results_data(df):
    try:
        df.to_csv(CSV_RESULTS_PATH, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving results: {e}")
        return False

# Subject credits configurations for SGPA calculation
SUBJECT_CREDITS = {
    "NAS": 3.0,
    "DS": 3.0,
    "PYTHON": 3.0,
    "EC": 3.0,
    "ODEVC": 3.0,
    "BEE LAB": 1.5,
    "EWS": 1.5,
    "DS LAB": 1.5,
    "APP PHTH LAB": 1.5,
    "EC LAB": 1.5,
    "CRT": 1.5
}

def calculate_gpa(marks_dict):
    """Calculates SGPA based on standard grade points."""
    total_points = 0.0
    total_credits = 0.0
    
    for sub, score in marks_dict.items():
        if sub not in SUBJECT_CREDITS:
            continue
        
        # Determine Grade Point (GP)
        try:
            if pd.isna(score):
                gp = 0.0
            else:
                val = float(score)
                if val >= 90:
                    gp = 10.0  # O
                elif val >= 80:
                    gp = 9.0   # A+
                elif val >= 70:
                    gp = 8.0   # A
                elif val >= 60:
                    gp = 7.0   # B+
                elif val >= 50:
                    gp = 6.0   # B
                elif val >= 40:
                    gp = 5.0   # C (Pass)
                else:
                    gp = 0.0   # F (Fail)
            
            credits = SUBJECT_CREDITS[sub]
            total_points += gp * credits
            total_credits += credits
        except (ValueError, TypeError):
            continue
            
    if total_credits == 0:
        return 0.0
    return round(total_points / total_credits, 2)

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

# --- LOGOUT HANDLER ---
def logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.rerun()

# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🎓 VITS Student & Portal Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Section ECE-B Academic Management Portal</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.8, 1])
    
    with col2:
        tab_student, tab_admin = st.tabs(["🔑 Student Access", "🛡️ Admin Console"])
        
        # Student login logic
        with tab_student:
            with st.form("student_login_form"):
                st.subheader("Student Login")
                roll_input = st.text_input("Roll Number", placeholder="e.g., 25891A0465").strip().upper()
                dob_input = st.text_input("Password (DOB: YYYY-MM-DD)", type="password", placeholder="YYYY-MM-DD").strip()
                
                submitted = st.form_submit_button("Sign In")
                if submitted:
                    if not roll_input or not dob_input:
                        st.error("Please fill in both fields.")
                    else:
                        results_df = load_results_data()
                        if results_df is not None:
                            # Match roll and dob
                            matched = results_df[
                                (results_df["H.T No."].astype(str).str.strip().str.upper() == roll_input) &
                                (results_df["DOB"].astype(str).str.strip() == dob_input)
                            ]
                            if not matched.empty:
                                st.session_state.logged_in = True
                                st.session_state.role = "student"
                                st.session_state.user_id = roll_input
                                st.session_state.user_name = matched.iloc[0]["Student Name"]
                                st.success(f"Welcome, {st.session_state.user_name}!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Authentication failed. Invalid Roll Number or DOB.")
                        else:
                            # Fallback if results CSV isn't present - check attendance master for Roll Number
                            attendance_df = load_attendance_data()
                            if attendance_df is not None:
                                matched_stud = attendance_df[attendance_df["H.T No."].astype(str).str.strip() == roll_input]
                                if not matched_stud.empty and dob_input == "2007-01-01":
                                    st.session_state.logged_in = True
                                    st.session_state.role = "student"
                                    st.session_state.user_id = roll_input
                                    st.session_state.user_name = matched_stud.iloc[0]["Student Name"]
                                    st.success(f"Welcome, {st.session_state.user_name}! (Fallback Auth)")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Invalid credentials or databases are offline.")
                            else:
                                st.error("Database connection failed. Contact Admin.")
                                
        # Admin login logic
        with tab_admin:
            with st.form("admin_login_form"):
                st.subheader("Portal Administrator")
                admin_user = st.text_input("Username", placeholder="e.g., admin").strip()
                admin_pass = st.text_input("Password", type="password", placeholder="••••••••").strip()
                
                admin_submitted = st.form_submit_button("Authenticate")
                if admin_submitted:
                    # Simple admin authorization credentials
                    if admin_user == "admin" and admin_pass == "admin123":
                        st.session_state.logged_in = True
                        st.session_state.role = "admin"
                        st.session_state.user_id = "admin"
                        st.session_state.user_name = "Portal Administrator"
                        st.success("Admin Session Initialized.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid administrator credentials.")

# --- APPLICATION INTERFACE (LOGGED IN) ---
else:
    # Load configuration
    config = harvester.load_config()
    
    # Custom Sidebar Navigation & Info
    st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
    st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
    if st.session_state.role == "student":
        st.sidebar.markdown(f"**HT No:** `{st.session_state.user_id}`")
        
    st.sidebar.markdown("---")
    
    # Role-based Navigation Options
    if st.session_state.role == "student":
        menu = st.sidebar.radio("Navigation Menu", ["📊 Attendance Tracker", "🏆 Academic Performance"])
    else:
        menu = st.sidebar.radio("Navigation Menu", ["⚙️ Admin Settings", "📋 View Class Database"])
        
    st.sidebar.markdown("---")
    
    # Metadata info
    st.sidebar.caption(f"📅 Scraper block: {config.get('start_date')} to {config.get('end_date')}")
    st.sidebar.caption(f"🔄 Last sync: {config.get('last_scraped_at')}")
    
    if st.sidebar.button("🚪 Log Out", use_container_width=True):
        logout()
        
    # ------------------ STUDENT PANELS ------------------
    if st.session_state.role == "student":
        
        attendance_df = load_attendance_data()
        results_df = load_results_data()
        
        # 1. ATTENDANCE TRACKER VIEW
        if menu == "📊 Attendance Tracker":
            st.title("📊 Class Attendance Dashboard")
            st.write("Monitor your subject-wise presence logs and overall academic compliance.")
            
            if attendance_df is None:
                st.warning("⚠️ Attendance records are currently offline. Please try again later.")
            else:
                # Row 0: Conducted hours
                conducted_row = attendance_df.iloc[0]
                
                # Retrieve student's record
                stud_row = attendance_df[attendance_df["H.T No."].astype(str).str.strip() == st.session_state.user_id]
                
                if stud_row.empty:
                    st.error("Roll number record not found in the current attendance sheet.")
                else:
                    student_data = stud_row.iloc[0]
                    
                    # Manual "Up to Date" Selector block
                    st.markdown("### 🗓️ Query Portal Attendance")
                    col_d1, col_d2, col_d3 = st.columns([1.5, 1, 2])
                    with col_d1:
                        target_upto_date = st.date_input(
                            "Select custom 'Up to Date' to fetch live data:",
                            value=datetime.now().date(),
                            max_value=datetime.now().date()
                        )
                    with col_d2:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        trigger_live_student_fetch = st.button("Fetch Live", use_container_width=True)
                    
                    if trigger_live_student_fetch:
                        f_date = config.get("start_date", "2026-01-27")
                        t_date = target_upto_date.strftime("%Y-%m-%d")
                        
                        # Date Validation
                        start_date_obj = datetime.strptime(f_date, "%Y-%m-%d").date()
                        if target_upto_date < start_date_obj:
                            st.error(f"❌ Selected 'Up to Date' ({t_date}) cannot be before the Semester Start Date ({f_date}).")
                        else:
                            with st.spinner(f"Scraping college portal for ECE-B up to {t_date}... Please wait."):
                                success, msg = harvester.scrape_portal(start_date=f_date, end_date=t_date)
                                if success:
                                    st.success(f"Successfully retrieved updated data up to {t_date}!")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.warning(f"⚠️ Live portal sync failed: {msg}. Displaying cached master attendance data.")
                    
                    # Subject columns extractor
                    subjects = [
                        col for col in attendance_df.columns 
                        if col not in ["S.No.", "H.T No.", "Student Name", "Total", "Percentage(%)"]
                    ]
                    
                    # Totals calculation
                    total_conducted = pd.to_numeric(conducted_row["Total"], errors="coerce")
                    total_attended = pd.to_numeric(student_data["Total"], errors="coerce")
                    
                    # Dynamic formatting parsing for attendance percentage
                    pct_val = student_data["Percentage(%)"]
                    if isinstance(pct_val, str):
                        pct_val = pct_val.replace('%', '')
                    overall_pct = pd.to_numeric(pct_val, errors="coerce")
                    
                    # Conditional Formatting Metric Display
                    m_col1, m_col2, m_col3 = st.columns(3)
                    with m_col1:
                        st.markdown(f"""
                        <div class="kpi-card">
                            <div class="kpi-title">Total Hours Conducted</div>
                            <div class="kpi-value">{int(total_conducted) if not pd.isna(total_conducted) else "N/A"}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with m_col2:
                        st.markdown(f"""
                        <div class="kpi-card">
                            <div class="kpi-title">Total Hours Attended</div>
                            <div class="kpi-value">{int(total_attended) if not pd.isna(total_attended) else "N/A"}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with m_col3:
                        card_class = "kpi-card-green" if overall_pct >= 75.0 else "kpi-card-red"
                        st.markdown(f"""
                        <div class="{card_class}">
                            <div class="kpi-title">Overall Percentage</div>
                            <div class="kpi-value">{overall_pct:.2f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Status messages
                    if overall_pct < 75.0:
                        st.error(f"⚠️ **ATTENDANCE SHORTAGE WARNING:** Your attendance is **{overall_pct:.2f}%**, which is below the university-mandated 75.0%. Please contact your section head immediately.")
                    else:
                        st.success(f"✅ **GOOD STANDING:** Your attendance is **{overall_pct:.2f}%**. You are in compliance with the academic requirements.")
                    
                    # Subject-wise attendance DataFrame compilation
                    sub_logs = []
                    for sub in subjects:
                        cond = pd.to_numeric(conducted_row[sub], errors="coerce")
                        att = pd.to_numeric(student_data[sub], errors="coerce")
                        pct = (att / cond * 100) if cond > 0 else 0
                        sub_logs.append({
                            "Subject": sub,
                            "Conducted": int(cond) if not pd.isna(cond) else 0,
                            "Attended": int(att) if not pd.isna(att) else 0,
                            "Percentage (%)": round(pct, 2)
                        })
                    
                    sub_df = pd.DataFrame(sub_logs)
                    
                    # Charts display
                    st.markdown("### 📊 Subject-by-Subject Attendance Log")
                    
                    # Prepare data for Altair (melted format)
                    chart_data = sub_df.melt(id_vars=["Subject", "Percentage (%)"], value_vars=["Conducted", "Attended"], var_name="Type", value_name="Hours")
                    
                    # Side-by-side bar chart
                    attendance_chart = alt.Chart(chart_data).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                        x=alt.X('Type:N', title=None),
                        y=alt.Y('Hours:Q', title="Number of Hours"),
                        color=alt.Color('Type:N', scale=alt.Scale(domain=['Conducted', 'Attended'], range=['#3b82f6', '#10b981'])),
                        column=alt.Column('Subject:N', title=None, header=alt.Header(labelAngle=-45, labelAlign='right')),
                        tooltip=['Subject', 'Type', 'Hours']
                    ).properties(
                        width=80,
                        height=300
                    ).configure_view(
                        stroke='transparent'
                    )
                    
                    st.altair_chart(attendance_chart)
                    
                    # Detailed Data Table
                    with st.expander("📝 View Detailed Attendance Log Sheet"):
                        st.dataframe(sub_df, hide_index=True, use_container_width=True)
                        
        # 2. ACADEMIC PERFORMANCE VIEW
        elif menu == "🏆 Academic Performance":
            st.title("🏆 Academic Performance Dashboard")
            st.write("Review Semester 1 results, SGPA score metrics, and comparisons against class metrics.")
            
            if results_df is None:
                st.warning("⚠️ Academic records database is currently offline.")
            else:
                stud_res = results_df[results_df["H.T No."].str.strip() == st.session_state.user_id]
                
                if stud_res.empty:
                    st.error("No result details found for your Roll Number in the results database.")
                else:
                    student_marks = stud_res.iloc[0]
                    
                    # Dynamic GPA computation
                    subject_list = [col for col in results_df.columns if col not in ["H.T No.", "Student Name", "DOB"]]
                    
                    student_scores = {}
                    for sub in subject_list:
                        student_scores[sub] = student_marks[sub]
                        
                    sgpa = calculate_gpa(student_scores)
                    
                    # Metrics Row
                    res_col1, res_col2 = st.columns([1, 2])
                    
                    with res_col1:
                        st.markdown(f"""
                        <div class="kpi-card" style="margin-top: 25px;">
                            <div class="kpi-title">Calculated Sem-1 SGPA</div>
                            <div class="kpi-value" style="color: #60a5fa;">{sgpa:.2f}</div>
                            <p style='color: #64748b; font-size: 12px; margin-top:10px;'>Based on credits allocation matrix</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with res_col2:
                        # Clean grid display
                        st.markdown("### 📝 Exam Marks Breakdown")
                        scores_grid = []
                        for sub in subject_list:
                            raw_score = student_marks[sub]
                            if pd.isna(raw_score) or str(raw_score).strip() == "" or str(raw_score).lower() == "nan":
                                grade, gp = "Ab (Absent)", 0.0
                                display_score = "Absent"
                            else:
                                try:
                                    score = float(raw_score)
                                    display_score = int(score)
                                    if score >= 90:
                                        grade, gp = "O", 10.0
                                    elif score >= 80:
                                        grade, gp = "A+", 9.0
                                    elif score >= 70:
                                        grade, gp = "A", 8.0
                                    elif score >= 60:
                                        grade, gp = "B+", 7.0
                                    elif score >= 50:
                                        grade, gp = "B", 6.0
                                    elif score >= 40:
                                        grade, gp = "C", 5.0
                                    else:
                                        grade, gp = "F (Fail)", 0.0
                                except (ValueError, TypeError):
                                    grade, gp = "Invalid", 0.0
                                    display_score = "N/A"
                                
                            scores_grid.append({
                                "Subject Name": sub,
                                "Marks Obtained": display_score,
                                "Grade Point": gp,
                                "Grade Assigned": grade,
                                "Credits Alloc": SUBJECT_CREDITS.get(sub, 0.0)
                            })
                        
                        st.dataframe(pd.DataFrame(scores_grid), hide_index=True, use_container_width=True)
                        
                        # Add academic fail warning / good standing message
                        failed_subs = [item["Subject Name"] for item in scores_grid if "F (Fail)" in str(item["Grade Assigned"]) or "Absent" in str(item["Marks Obtained"])]
                        if failed_subs:
                            st.error(f"⚠️ **ACADEMIC ALERT:** You have not secured passing marks in the following subject(s): {', '.join(failed_subs)}. Please contact your counselor or department head.")
                        else:
                            st.success("✅ **GOOD ACADEMIC STANDING:** You have passed all subjects in the first semester.")
                        
                    st.markdown("---")
                    st.markdown("### 📊 Performance Comparison: You vs Class High / Class Average")
                    
                    # Calculate class metrics
                    comparison_records = []
                    for sub in subject_list:
                        raw_val = student_marks[sub]
                        try:
                            student_score = float(raw_val)
                            if pd.isna(student_score):
                                student_score = 0.0
                        except (ValueError, TypeError):
                            student_score = 0.0
                        
                        # Convert column to numeric, ignoring errors
                        all_marks = pd.to_numeric(results_df[sub], errors='coerce').dropna()
                        class_avg = all_marks.mean() if not all_marks.empty else 0.0
                        class_max = all_marks.max() if not all_marks.empty else 0.0
                        
                        comparison_records.append({
                            "Subject": sub,
                            "ScoreType": "Your Score",
                            "Marks": student_score
                        })
                        comparison_records.append({
                            "Subject": sub,
                            "ScoreType": "Class Average",
                            "Marks": round(class_avg, 2)
                        })
                        comparison_records.append({
                            "Subject": sub,
                            "ScoreType": "Class Highest",
                            "Marks": class_max
                        })
                        
                    comp_df = pd.DataFrame(comparison_records)
                    
                    # Render side-by-side comparison bar chart
                    comp_chart = alt.Chart(comp_df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X('ScoreType:N', title=None, axis=alt.Axis(labels=False)),
                        y=alt.Y('Marks:Q', title="Marks (out of 100)"),
                        color=alt.Color('ScoreType:N', scale=alt.Scale(domain=['Your Score', 'Class Average', 'Class Highest'], range=['#3b82f6', '#94a3b8', '#10b981'])),
                        column=alt.Column('Subject:N', title=None, header=alt.Header(labelAngle=-45, labelAlign='right')),
                        tooltip=['Subject', 'ScoreType', 'Marks']
                    ).properties(
                        width=70,
                        height=320
                    ).configure_view(
                        stroke='transparent'
                    )
                    
                    st.altair_chart(comp_chart)
                    
    # ------------------ ADMIN PANELS ------------------
    else:
        # 1. ADMIN SETTINGS
        if menu == "⚙️ Admin Settings":
            st.title("⚙️ Portal Scraper & Block Period Management")
            st.write("Adjust portal harvesting ranges, trigger manual database runs, and update class configurations.")
            
            # Scraper control dates
            st.markdown("### 📅 Change Scraping Date Blocks")
            c_col1, c_col2 = st.columns(2)
            
            with c_col1:
                admin_start_date = st.date_input(
                    "Semester Start Date (fdt):",
                    value=datetime.strptime(config.get("start_date", "2026-01-27"), "%Y-%m-%d").date()
                )
            with c_col2:
                admin_end_date = st.date_input(
                    "Report Target End Date (tdt):",
                    value=datetime.strptime(config.get("end_date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d").date()
                )
                
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 Save Settings", use_container_width=True):
                    if admin_end_date < admin_start_date:
                        st.error("❌ End Date cannot be before Start Date.")
                    else:
                        config["start_date"] = admin_start_date.strftime("%Y-%m-%d")
                        config["end_date"] = admin_end_date.strftime("%Y-%m-%d")
                        harvester.save_config(config)
                        st.success("Configuration settings updated successfully!")
                        st.rerun()
            with col_b2:
                if st.button("⚡ Trigger Manual Portal Scrape", use_container_width=True):
                    if admin_end_date < admin_start_date:
                        st.error("❌ End Date cannot be before Start Date.")
                    else:
                        f_date = admin_start_date.strftime("%Y-%m-%d")
                        t_date = admin_end_date.strftime("%Y-%m-%d")
                        
                        with st.spinner("Executing scraper on college portal... please stand by."):
                            # Force scrape with parameters
                            success, result = harvester.scrape_portal(start_date=f_date, end_date=t_date)
                            if success:
                                st.success("✅ Scrape process finished successfully. Database synced.")
                                st.rerun()
                            else:
                                st.error(f"❌ Scraper pipeline execution failed: {result}")
            
            st.markdown("---")
            st.markdown("### 🏆 Upload / Edit Academic Performance Records")
            
            # Exam Marks File Upload
            st.subheader("Bulk Marks File Import")
            uploaded_results_file = st.file_uploader("Upload new 'sem1_results.csv' spreadsheet:", type="csv")
            
            if uploaded_results_file is not None:
                try:
                    new_results_df = pd.read_csv(uploaded_results_file)
                    required_cols = ["H.T No.", "Student Name", "DOB"]
                    missing_cols = [col for col in required_cols if col not in new_results_df.columns]
                    
                    if missing_cols:
                        st.error(f"Upload failed: The CSV is missing mandatory columns: {missing_cols}")
                    else:
                        new_results_df.to_csv(CSV_RESULTS_PATH, index=False)
                        st.success(f"Successfully processed and updated {len(new_results_df)} student marks sheets!")
                        time.sleep(0.8)
                        st.rerun()
                except Exception as ex:
                    st.error(f"Error parsing uploaded CSV: {ex}")
                    
            st.markdown("---")
            st.subheader("Manual Record Editor")
            results_df = load_results_data()
            
            if results_df is None:
                st.warning("Cannot edit records: Academic performance database is offline.")
            else:
                roll_list = sorted(results_df["H.T No."].str.strip().tolist())
                selected_roll = st.selectbox("Search Student Roll Number to Edit:", roll_list)
                
                if selected_roll:
                    student_record = results_df[results_df["H.T No."].str.strip() == selected_roll].iloc[0]
                    
                    with st.form("edit_student_record_form"):
                        st.write(f"Editing Details for: **{student_record['Student Name']}**")
                        
                        new_dob = st.text_input("Date of Birth (DOB / Password):", value=str(student_record["DOB"]).strip())
                        
                        st.write("**Subject Marks (out of 100):**")
                        subject_columns = [c for c in results_df.columns if c not in ["H.T No.", "Student Name", "DOB"]]
                        
                        updated_marks = {}
                        
                        # Display input fields for marks in columns
                        marks_cols = st.columns(3)
                        for idx, sub in enumerate(subject_columns):
                            with marks_cols[idx % 3]:
                                raw_val = student_record[sub]
                                default_val = 0
                                if pd.notna(raw_val):
                                    try:
                                        default_val = int(float(raw_val))
                                        if default_val < 0:
                                            default_val = 0
                                        elif default_val > 100:
                                            default_val = 100
                                    except (ValueError, TypeError):
                                        default_val = 0
                                updated_marks[sub] = st.number_input(
                                    f"{sub}:", 
                                    min_value=0, 
                                    max_value=100, 
                                    value=default_val
                                )
                                
                        save_submitted = st.form_submit_button("Save Student Record Changes")
                        if save_submitted:
                            # Update DataFrame row
                            idx_to_update = results_df[results_df["H.T No."].str.strip() == selected_roll].index[0]
                            results_df.at[idx_to_update, "DOB"] = new_dob
                            for sub, mark in updated_marks.items():
                                results_df.at[idx_to_update, sub] = mark
                                
                            if save_results_data(results_df):
                                st.success("Student details updated successfully in database!")
                                time.sleep(0.5)
                                st.rerun()
                                
        # 2. VIEW CLASS DATABASE
        elif menu == "📋 View Class Database":
            st.title("📋 Section ECE-B Master Database Records")
            
            tab_db_att, tab_db_perf = st.tabs(["📊 Class Attendance Matrix", "🏆 Semester 1 Academic Results"])
            
            with tab_db_att:
                st.subheader("Attendance Master Records")
                df_att = load_attendance_data()
                if df_att is not None:
                    st.write(f"Showing {len(df_att) - 1} records from cached attendance database.")
                    st.dataframe(df_att, use_container_width=True)
                else:
                    st.warning("Attendance master CSV database is currently empty/offline.")
                    
            with tab_db_perf:
                st.subheader("Academic Results Database")
                df_perf = load_results_data()
                if df_perf is not None:
                    st.write(f"Showing {len(df_perf)} records from results database.")
                    st.dataframe(df_perf, use_container_width=True)
                else:
                    st.warning("Academic results CSV database is currently empty/offline.")
