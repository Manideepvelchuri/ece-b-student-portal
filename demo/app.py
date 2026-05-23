import requests
import pandas as pd
import io
from datetime import datetime

# --- 1. Configurations ---
student_core_branch = "ECE"  
student_year = "1"           
student_section = "ECE_B"

# --- Dynamic Date Logic (Database-Compliant YYYY-MM-DD) ---
now = datetime.now()
# 'To Date' automatically changes to today's date in YYYY-MM-DD format
target_to_date = now.strftime("%Y-%m-%d")
# 'From Date' is set to the start of your semester in YYYY-MM-DD format
target_from_date = "2026-01-27" 

# First-year students fall under the BSH department payload
payload_branch = "BSH" if student_year == "1" else student_core_branch

# --- 2. Session Initialization & Login ---
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded"
}

print("1. Logging into the Vignan portal...")
login_url = "http://103.52.36.11/Attendance/Validate.php"
login_payload = {
    "uname": "848", 
    "pass": "vits"
}

# Establish our logged-in session state
session.post(login_url, data=login_payload, headers=headers)

# --- 3. Extracting the Report with Proper Wire Formats ---
report_url = "http://103.52.36.11/Attendance/Crprint.php"
report_payload = {
    "br": payload_branch,
    "yr": student_year,
    "sc": student_section, 
    "fdt": target_from_date,  # Sends as YYYY-MM-DD
    "tdt": target_to_date,    # Sends as YYYY-MM-DD
    "Submit": "Submit"
}

print(f"2. Requesting attendance data from {target_from_date} up to today ({target_to_date})...")

try:
    # Heavy tables can take a hot minute to compile on the college network
    response = session.post(report_url, data=report_payload, headers=headers, timeout=(10, 180))
    
    print("3. Data received! Parsing matrix into spreadsheet rows...")
    
    # Process html content directly into pandas
    tables = pd.read_html(io.StringIO(response.text))
    attendance_df = tables[0]
    
    # Clean output delivery
    file_name = f"Attendance_Report_{student_section}.csv"
    attendance_df.to_csv(file_name, index=False)
    print(f"\n🎉 SUCCESS! Saved {len(attendance_df)} active student records with full hour logs to '{file_name}'")

except Exception as e:
    print(f"\n❌ Execution stopped due to error: {e}")