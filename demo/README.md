# ECE-B Student Attendance & Performance Portal

A Pure-Python real-time dashboard and background data pipeline designed to monitor and display student attendance compliance and academic results for section ECE-B.

---

## Directory Structure

```
d:/py ip project/demo/
├── .github/
│   └── workflows/
│       └── scrape.yml            # GitHub Actions cron scheduler
├── harvester.py                  # Background web portal scraper & sheets uploader
├── dashboard.py                  # Streamlit portal interface
├── sem1_results.csv              # Student exam records & login credentials database
├── attendance_master.csv         # Local cache of scraped attendance data
├── config.json                   # Shared system configurations (scraping ranges)
└── README.md                     # This documentation file
```

---

## 🚀 Getting Started

### 1. Install Dependencies
Run the following command in your terminal to install the necessary libraries:
```bash
pip install streamlit requests pandas beautifulsoup4 lxml gspread
```

### 2. Run the Web Dashboard
Start the local Streamlit development server:
```bash
streamlit run dashboard.py
```
This will launch the dashboard in your default browser at `http://localhost:8501`.

### 3. Run the Harvester Standalone
To manually trigger the background scraper to authenticate and parse raw data from the college portal:
```bash
python harvester.py
```
This updates the local database cache `attendance_master.csv` and updates `config.json`'s log timestamp.

---

## 🔑 Login Credentials for Testing

### 🛡️ Admin Access
* **Username:** `admin`
* **Password:** `admin123`

### 🔑 Student Access (Examples)
You can login using the following generated credentials:
1. **Roll Number:** `25891A0465` | **DOB (Password):** `2007-11-04` (Student: YALANGI HARSHIT RAM)
2. **Roll Number:** `25891A0466` | **DOB (Password):** `2007-11-23` (Student: ABHI SRI R)
3. **Roll Number:** `25891A0474` | **DOB (Password):** `2007-12-18` (Student: BUDDA RAMYA - has a subject fail warning to demo the UI)

---

## 📊 SGPA & Credits Calculation Rules

The dashboard dynamically calculates the first-semester SGPA using the following parameters:

### Subjects Credits Allocation
* **Theory (NAS, DS, PYTHON, EC, ODEVC):** 3.0 credits each
* **Labs (BEE LAB, DS LAB, APP PHTH LAB, EC LAB):** 1.5 credits each
* **General (EWS, CRT):** 1.5 credits each

### Grade Point Scale
* **Marks >= 90:** Grade `O` (Outstanding) | GP: `10`
* **Marks >= 80:** Grade `A+` (Excellent) | GP: `9`
* **Marks >= 70:** Grade `A` (Very Good) | GP: `8`
* **Marks >= 60:** Grade `B+` (Good) | GP: `7`
* **Marks >= 50:** Grade `B` (Above Average) | GP: `6`
* **Marks >= 40:** Grade `C` (Pass) | GP: `5`
* **Marks < 40:** Grade `F` (Fail) | GP: `0`

---

## 📅 Google Sheets API Setup

The harvester can sync your attendance database to a Google Sheet automatically in the background. Follow these steps to activate the sync:

1. **Create Google Cloud Project:**
   * Go to the [Google Cloud Console](https://console.cloud.google.com/).
   * Create a new project.
2. **Enable APIs:**
   * Go to **API & Services > Library**.
   * Search for and enable both the **Google Drive API** and **Google Sheets API**.
3. **Create Service Account Credentials:**
   * Go to **API & Services > Credentials**.
   * Click **Create Credentials** and choose **Service Account**.
   * Fill in the service account name and click **Create and Continue**.
   * Under the service account credentials page, click the **Keys** tab, click **Add Key > Create New Key**, select **JSON**, and download the file.
4. **Link Credentials to the Dashboard:**
   * Rename the downloaded JSON file to `service_account.json`.
   * Place the `service_account.json` file directly inside your project directory (`d:/py ip project/demo/`).
5. **Share Google Sheet:**
   * Open the JSON key file and copy the `"client_email"` address (looks like: `your-service-account@your-project-id.iam.gserviceaccount.com`).
   * Create a new Google Sheet named `ECE_B_Attendance` (or customize the sheet name in `config.json`).
   * Click **Share** on the Google Sheet and paste the service account email. Give it **Editor** permissions.
