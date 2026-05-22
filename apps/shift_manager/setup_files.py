import sys
import os
import json
import gspread
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from modules.utils import setup_logger

logger = setup_logger("SetupFiles")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
TARGET_FOLDER_ID = "1S0FroRSuThEAZaqqNQDN3_RubAztcQOZ"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def authenticate():
    if not os.path.exists(CREDENTIALS_PATH):
        logger.error(f"Credentials file not found at {CREDENTIALS_PATH}")
        sys.exit(1)

    creds = None
    try:
        with open(CREDENTIALS_PATH, 'r') as f:
            data = json.load(f)
            if data.get("type") == "service_account":
                creds = service_account.Credentials.from_service_account_file(
                    CREDENTIALS_PATH, scopes=SCOPES
                )
    except Exception:
        pass

    if not creds:
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
    
    return creds

def move_file_to_folder(drive_service, file_id, folder_id):
    try:
        # Retrieve the existing parents to remove
        file = drive_service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        
        # Move the file by adding the new parent and removing the old one
        drive_service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        logger.info(f"Moved file {file_id} to folder {folder_id}")
        return True
    except Exception as e:
        logger.error(f"Error moving file {file_id}: {e}")
        return False

def setup():
    creds = authenticate()
    gc = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)

    existing_config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            existing_config = json.load(f)

    # 1. Create HMC_Monthly_UI
    if "monthly_ui_id" in existing_config:
        logger.info("HMC_Monthly_UI already exists inside config.")
        monthly_sh = gc.open_by_key(existing_config["monthly_ui_id"])
    else:
        logger.info("Creating HMC_Monthly_UI...")
        monthly_sh = gc.create("HMC_Monthly_UI")
        move_file_to_folder(drive_service, monthly_sh.id, TARGET_FOLDER_ID)
        existing_config["monthly_ui_id"] = monthly_sh.id

    # 2. Create HMC_Backend_DB
    if "backend_db_id" in existing_config:
        logger.info("HMC_Backend_DB already exists inside config.")
        db_sh = gc.open_by_key(existing_config["backend_db_id"])
    else:
        logger.info("Creating HMC_Backend_DB...")
        db_sh = gc.create("HMC_Backend_DB")
        move_file_to_folder(drive_service, db_sh.id, TARGET_FOLDER_ID)
        existing_config["backend_db_id"] = db_sh.id

    # Save Config
    with open(CONFIG_PATH, 'w') as f:
        json.dump(existing_config, f, indent=4)
        logger.info(f"Config saved to {CONFIG_PATH}")

    # 3. Initialize DB Sheets
    # Sheets: DB_Master_Events, DB_Master_Categories, DB_Shift_Logs
    db_schema = {
        "DB_Master_Events": [
            "Date", "Location", "Category", "Content", "Time_Schedule", 
            "Planner", "Site_Lead", "Medic", "Staff_General", "Photographer", "Cook", 
            "Actual_Hours", "Memo", "Invoice_Status"
        ],
        "DB_Master_Categories": ["Category_Name"],
        "DB_Shift_Logs": ["Date", "Staff_ID", "Status"]
    }

    # Helper to init sheet
    existing_titles = [s.title for s in db_sh.worksheets()]
    
    # Remove default 'Sheet1' if it exists and we are creating others
    # (Only if we have other sheets to switch to, or do it last)

    for name, headers in db_schema.items():
        if name not in existing_titles:
            ws = db_sh.add_worksheet(title=name, rows=1000, cols=20)
            ws.append_row(headers)
            logger.info(f"Created {name}")
        else:
            logger.info(f"{name} exists.")
            # Verify/Update headers? Skip for now to avoid accidental overwrite of data
            pass
            
    # Init Data for Categories
    ws_cat = db_sh.worksheet("DB_Master_Categories")
    current_cats = ws_cat.col_values(1) # Read col 1
    
    required_cats = [
        "おやこ学部", "こども学部", "おとな学部", "企業案件", 
        "イベント", "キャンプ", "その他"
    ]
    
    # Check if header present "Category_Name"
    if "Category_Name" not in current_cats:
        ws_cat.clear()
        ws_cat.append_row(["Category_Name"])
        current_cats = ["Category_Name"]

    new_cats = []
    for c in required_cats:
        if c not in current_cats:
            new_cats.append([c])
            
    if new_cats:
        ws_cat.append_rows(new_cats)
        logger.info(f"Added {len(new_cats)} categories.")

    # Cleanup Sheet1 if exists and not needed
    if "Sheet1" in [s.title for s in db_sh.worksheets()] and len(db_sh.worksheets()) > 1:
        db_sh.del_worksheet(db_sh.worksheet("Sheet1"))

    logger.info("Setup Complete.")
    print(f"Monthly UI: https://docs.google.com/spreadsheets/d/{existing_config['monthly_ui_id']}")
    print(f"Backend DB: https://docs.google.com/spreadsheets/d/{existing_config['backend_db_id']}")

if __name__ == "__main__":
    setup()
