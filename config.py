"""
Configuration for the Asset Migration Automation Tool (AMAT) - Direct API Mode.

Edit the values below, or override any of them via CLI flags on main.py
(CLI flags always win over these defaults).
"""

# --- Google Sheets ---
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"          # The long ID in the Google Sheets URL between /d/ and /edit
WORKSHEET_NAME = "Assets"                            # Tab name inside the spreadsheet

# --- Google Drive ---
DRIVE_FOLDER_ID = "YOUR_DRIVE_FOLDER_ID_HERE"         # Destination folder ID for uploaded images

# --- Google OAuth ---
CREDENTIALS_FILE = "credentials.json"   # OAuth client secret, downloaded from Google Cloud Console
TOKEN_FILE = "token.json"               # Auto-created after first successful login
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

# --- Source Excel file (the export containing embedded images) ---
SOURCE_SHEET_NAME = None     # None = use the first/active worksheet
HEADER_ROW = 1                # Row number (1-indexed) containing "Asset Code", "Asset Name", "Picture", etc.
ASSET_CODE_HEADER = "Asset Code"
ASSET_NAME_HEADER = "Asset Name"
PICTURE_HEADER = "Picture"

# --- Behaviour ---
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3

# --- Paths ---
LOG_DIR = "logs"
REPORT_DIR = "reports"
TEMP_DIR = "temp"

