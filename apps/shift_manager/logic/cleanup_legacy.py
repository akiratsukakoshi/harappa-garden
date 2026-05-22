import sys
import os
import json
import gspread
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from modules.utils import setup_logger

logger = setup_logger("CleanupLegacy")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class LegacyCleanup:
    def __init__(self):
        self.creds = self._authenticate()
        self.client = gspread.authorize(self.creds)
        self.config = self._load_config()
        self.annual_sh = self.client.open_by_key(self.config["annual_id"])

    def _authenticate(self):
        if not os.path.exists(CREDENTIALS_PATH):
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

    def _load_config(self):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)

    def cleanup(self):
        logger.info("Cleaning up legacy sheets from File_Annual...")
        
        # List of sheets to DELETE
        legacy_sheets = [
            "UI_Monthly_Detail", 
            "UI_Shift_Manager", 
            "DB_Master_Program", 
            "DB_Master_Staff", 
            "DB_Schedule", 
            "DB_Shift_Log"
        ]
        
        existing = [s.title for s in self.annual_sh.worksheets()]
        
        count = 0
        for name in legacy_sheets:
            if name in existing:
                try:
                    logger.info(f"Deleting {name}...")
                    ws = self.annual_sh.worksheet(name)
                    self.annual_sh.del_worksheet(ws)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {name}: {e}")
        
        logger.info(f"Cleanup complete. Deleted {count} sheets.")
        
        # Rename valid sheet for consistency?
        # User wants "UI_Annual_Planner" to be 2026.
        # "UI_Annual_Planner_2026" is the target.
        # Check if "UI_Annual_Planner" exists and rename it to "UI_Annual_Planner_2026" if not verified.
        # But wait, logic supports fallback. Let's just rename it to be nice.
        if "UI_Annual_Planner" in existing and "UI_Annual_Planner_2026" not in existing:
             logger.info("Renaming UI_Annual_Planner to UI_Annual_Planner_2026...")
             ws = self.annual_sh.worksheet("UI_Annual_Planner")
             ws.update_title("UI_Annual_Planner_2026")

if __name__ == "__main__":
    cleaner = LegacyCleanup()
    cleaner.cleanup()
