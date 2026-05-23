import os
import io
import json
import sys
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Try to import gspread for optional Google Sheets upload
try:
    import gspread
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Path configurations
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
MASTER_CSV_PATH = os.path.join(os.path.dirname(__file__), "attendance_master.csv")
CREDS_PATH = os.path.join(os.path.dirname(__file__), "service_account.json")

def load_config():
    """Load configuration from config.json or return defaults."""
    default_config = {
        "start_date": "2026-01-27",
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "last_scraped_at": "Never",
        "google_sheet_name": "ECE_B_Attendance"
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                # Ensure structure is complete
                for k, v in default_config.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception as e:
            print(f"[Warning] Failed to read config: {e}. Using defaults.")
    return default_config

def save_config(config):
    """Save config updates back to config.json."""
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[Warning] Failed to write config: {e}")

def run_diagnostics(html_content):
    """Fallback diagnostic engine using BeautifulSoup to print details if pandas parsing fails."""
    print("\n--- Diagnostic Engine ---")
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check for errors printed on the page
        body_text = soup.get_text()
        if "error" in body_text.lower() or "warning" in body_text.lower():
            print("Detected potential portal warnings or database errors on page:")
            for line in body_text.splitlines():
                if any(x in line.lower() for x in ["error", "warning", "mysql", "invalid", "denied"]):
                    print(f"  > {line.strip()}")
        
        tables = soup.find_all('table')
        print(f"Found {len(tables)} table(s) on the page.")
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"Table {i}: {len(rows)} rows.")
            if len(rows) > 0:
                cols = [th.get_text().strip() for th in rows[0].find_all(['th', 'td'])]
                print(f"  Headers: {cols[:8]}... (showing first 8 columns)")
    except Exception as e:
        print(f"Diagnostic engine failed: {e}")
    print("-------------------------\n")

def upload_to_google_sheet(df, sheet_name):
    """Upload DataFrame to Google Sheets using service account credentials."""
    if not GSPREAD_AVAILABLE:
        print("[Google Sheets] 'gspread' library is not installed. Skipping upload.")
        return False
    
    if not os.path.exists(CREDS_PATH) and "GSPREAD_CREDENTIALS" not in os.environ:
        print("[Google Sheets] Service account key 'service_account.json' not found and GSPREAD_CREDENTIALS env var is missing. Skipping upload.")
        return False

    try:
        print(f"[Google Sheets] Authenticating and uploading to sheet: '{sheet_name}'...")
        if os.path.exists(CREDS_PATH):
            gc = gspread.service_account(filename=CREDS_PATH)
        else:
            # Fallback to env variable mapping
            creds_info = json.loads(os.environ.get("GSPREAD_CREDENTIALS"))
            gc = gspread.service_account_from_dict(creds_info)
            
        try:
            sh = gc.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            print(f"[Google Sheets] Spreadsheet '{sheet_name}' not found. Creating a new one...")
            sh = gc.create(sheet_name)
            # Share sheet with the service account email if desired, or let user share manually
            print(f"[Google Sheets] Created sheet successfully! Share it using its URL.")
            
        worksheet = sh.get_worksheet(0)
        if worksheet is None:
            worksheet = sh.add_worksheet(title="Sheet1", rows="100", cols="20")
            
        worksheet.clear()
        
        # Format DataFrame values as strings to prevent JSON serialization errors
        # Convert columns & values to lists for gspread
        headers = df.columns.tolist()
        values = df.fillna("").astype(str).values.tolist()
        
        worksheet.update(values=[headers] + values, range_name='A1')
        print("[Google Sheets] Data successfully synced!")
        return True
    except Exception as e:
        print(f"[Google Sheets] Error syncing to Google Sheets: {e}")
        return False

def scrape_portal(start_date=None, end_date=None):
    """Logs in and scrapes attendance data from the college portal for a specific period."""
    config = load_config()
    
    fdt = start_date or config.get("start_date", "2026-01-27")
    tdt = end_date or config.get("end_date", datetime.now().strftime("%Y-%m-%d"))
    
    print(f"Starting Scraper Pipeline | Range: {fdt} to {tdt}")
    
    # Establish persistent session
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Credentials & target URLs
    login_url = "http://103.52.36.11/Attendance/Validate.php"
    report_url = "http://103.52.36.11/Attendance/Crprint.php"
    login_payload = {"uname": "848", "pass": "vits"}
    
    # Branch rule: first year is BSH, else ECE
    yr = "1"
    br = "BSH" if yr == "1" else "ECE"
    
    report_payload = {
        "br": br,
        "yr": yr,
        "sc": "ECE_B",
        "fdt": fdt,
        "tdt": tdt,
        "Submit": "Submit"
    }
    
    try:
        print("1. Authenticating session...")
        login_resp = session.post(login_url, data=login_payload, headers=headers, timeout=15)
        
        print("2. Fetching attendance matrix report...")
        report_resp = session.post(report_url, data=report_payload, headers=headers, timeout=(10, 180))
        
        if report_resp.status_code != 200:
            raise ValueError(f"HTTP Error {report_resp.status_code} received from portal report page.")
            
        html_text = report_resp.text
        
        # Check if login might have failed or session timed out
        if "uname" in html_text and "pass" in html_text:
            raise ValueError("Portal redirect detected. Session login validation failed.")
            
        print("3. Parsing HTML table structure...")
        tables = pd.read_html(io.StringIO(html_text))
        
        if not tables or len(tables) == 0:
            run_diagnostics(html_text)
            raise ValueError("No table elements were found in the HTML response.")
            
        attendance_df = tables[0]
        
        # Check if the dataframe is empty or malformed
        if len(attendance_df) < 2 or "H.T No." not in attendance_df.columns:
            run_diagnostics(html_text)
            raise ValueError(f"Scraped table schema mismatch. Columns found: {list(attendance_df.columns)}")
            
        print(f"4. Successfully extracted {len(attendance_df) - 1} student attendance records!")
        
        # Save to local master cache file
        attendance_df.to_csv(MASTER_CSV_PATH, index=False)
        print(f"5. Saved dataset locally to: {MASTER_CSV_PATH}")
        
        # Upload to Google Sheet if creds are active
        upload_to_google_sheet(attendance_df, config.get("google_sheet_name", "ECE_B_Attendance"))
        
        # Update config timestamp
        config["start_date"] = fdt
        config["end_date"] = tdt
        config["last_scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_config(config)
        
        print("SUCCESS: Scraper execution completed successfully.")
        return True, attendance_df
        
    except Exception as e:
        print(f"\nERROR: SCRAPER ERROR: {e}")
        # Run diagnostic engine to output markup parsing details
        if 'html_text' in locals():
            try:
                run_diagnostics(html_text)
            except Exception as diag_err:
                print(f"Failed to run diagnostic engine: {diag_err}")
        return False, str(e)

if __name__ == "__main__":
    # Check if dates are supplied via command-line arguments
    # Usage: python harvester.py [start_date] [end_date]
    f_date = sys.argv[1] if len(sys.argv) > 1 else None
    t_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    success, result = scrape_portal(f_date, t_date)
    sys.exit(0 if success else 1)
