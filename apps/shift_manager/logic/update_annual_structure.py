import sys
import os
import json
import gspread
import jpholiday
from datetime import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from gspread_formatting import format_cell_range, CellFormat, Color, TextFormat

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from modules.utils import setup_logger

logger = setup_logger("UpdateAnnualStructure")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class AnnualStructureUpdater:
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



    def _init_sheet(self, sheet_name, months, base_year_logic):
        """
        months: list of integers [1, 2, 3] or [4, ..., 12, 1, 2, 3]
        base_year_logic: function(month) -> year
        """
        try:
            ws = self.annual_sh.worksheet(sheet_name)
            logger.info(f"Sheet {sheet_name} exists. Re-initializing headers & weekdays...")
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Creating sheet {sheet_name}...")
            ws = self.annual_sh.add_worksheet(title=sheet_name, rows=40, cols=50)

        # Build Headers
        headers = ["Day"]
        for m in months:
            headers.extend([f"{m}月_曜", f"{m}月_会場", f"{m}月_カテゴリ"])
            
        w_map = ["月", "火", "水", "木", "金", "土", "日"]
        
        rows = []
        fmt_requests = []
        sheet_id = ws.id
        
        # Grid Data Generation
        for d in range(1, 32):
            row_vals = [str(d)]
            
            # Row Index for this Day (1-based for API).
            # Header is Row 1. Day 1 is Row 2.
            row_idx = d + 1 
            
            for i, m in enumerate(months):
                year = base_year_logic(m)
                wd_str = ""
                
                # Column Index for Weekday.
                # Col 0: Day.
                # Month i: Weekday is at 1 + (i * 3).
                col_idx = 1 + (i * 3)
                
                r_type = "NORMAL"
                
                try:
                    dt = datetime(year, m, d)
                    wd_str = w_map[dt.weekday()]
                    
                    is_holiday = jpholiday.is_holiday(dt)
                    is_sunday = (dt.weekday() == 6)
                    is_saturday = (dt.weekday() == 5)
                    
                    if is_holiday or is_sunday:
                        r_type = "RED"
                    elif is_saturday:
                        r_type = "BLUE"
                        
                except ValueError:
                    wd_str = ""
                
                row_vals.extend([wd_str, "", ""])
                
                # Add Format Request if needed
                if r_type != "NORMAL":
                    color = {"red": 1.0, "green": 0.0, "blue": 0.0} if r_type == "RED" else {"red": 0.0, "green": 0.0, "blue": 1.0}
                    req = {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": row_idx - 1, "endRowIndex": row_idx,
                                "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1
                            },
                            "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": color}}},
                            "fields": "userEnteredFormat.textFormat.foregroundColor"
                        }
                    }
                    fmt_requests.append(req)

            rows.append(row_vals)

        # Batch Update Values
        ws.update(range_name='A1', values=[headers])
        ws.update(range_name='A2', values=rows)
        
        # Batch Update Formats
        # Also clear previous formats?
        req_clear = {
            "repeatCell": {
                "range": {"sheetId": sheet_id},
                "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}}}},
                "fields": "userEnteredFormat.textFormat.foregroundColor"
            }
        }
        # Prepend clear request
        full_requests = [req_clear] + fmt_requests
        
        if full_requests:
            ws.spreadsheet.batch_update({"requests": full_requests})
        
        logger.info(f"Initialized {sheet_name} with {len(months)} months (Headers, Weekdays & Colors).")

    def run(self):
        # 1. UI_Annual_Planner_2025 (Transition: Jan-Mar 2026)
        # Months: 1, 2, 3 -> Year 2026
        def logic_2025(m):
            return 2026

        self._init_sheet("UI_Annual_Planner_2025", [1, 2, 3], logic_2025)
        
        # 2. UI_Annual_Planner_2026 (FY2026: Apr 2026 - Mar 2027)
        # Months: 4..12 -> 2026, 1..3 -> 2027
        def logic_2026(m):
            if m >= 4: return 2026
            return 2027

        self._init_sheet("UI_Annual_Planner_2026", [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3], logic_2026)
        
        logger.info("Annual Structure Updated (Refined Phase 1.8).")

if __name__ == "__main__":
    updater = AnnualStructureUpdater()
    updater.run()
