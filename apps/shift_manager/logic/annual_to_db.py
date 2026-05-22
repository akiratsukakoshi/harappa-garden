import sys
import os
import json
import gspread
from datetime import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from modules.utils import setup_logger

logger = setup_logger("AnnualToDB")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class AnnualToDB:
    def __init__(self):
        self.creds = self._authenticate()
        self.client = gspread.authorize(self.creds)
        self.config = self._load_config()
        self.annual_sh = self.client.open_by_key(self.config["annual_id"])
        self.db_sh = self.client.open_by_key(self.config["backend_db_id"])
        # No longer need to load categories for guessing

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

    def sync(self, year=2026):
        target_sheet_name = f"UI_Annual_Planner_{year}"
        logger.info(f"Syncing Annual Planner (Year {year}) to DB from {target_sheet_name}...")
        
        try:
            ws_annual = self.annual_sh.worksheet(target_sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"{target_sheet_name} not found.")
            return

        raw_data = ws_annual.get_all_values()
        if len(raw_data) < 2: return
        
        # Read Headers to detect Month Order
        headers = raw_data[0] # Row 1
        # E.g. "Day", "4月_曜", "4月_会場", "4月_カテゴリ", ...
        
        month_map = [] # [(col_index, month_int), ...]
        
        # Parse headers to find months
        # Expectation: 3 cols per month.
        # Check "月_曜" (Weekday) which is Col 1 of the block.
        for idx in range(1, len(headers)):
            h = headers[idx]
            if "月_曜" in h:
                try:
                    m_str = h.split("月_")[0]
                    m = int(m_str)
                    month_map.append((idx, m))
                except:
                    pass
                    
        # 2. Iterate and Parse
        new_events = []
        
        for row_idx, row in enumerate(raw_data[1:], start=1): 
            if row_idx > 31: break 
            
            day_str = row[0]
            if not day_str.isdigit(): continue
            day = int(day_str)
            
            for col_idx, m in month_map:
                # col_idx is "Month_Weekday".
                # col_idx + 1 is "Month_Location"
                # col_idx + 2 is "Month_Category" (Renamed from Content)
                
                if col_idx + 2 >= len(row): break
                
                col_loc = row[col_idx+1].strip()
                col_cat = row[col_idx+2].strip()
                
                if not col_cat and not col_loc:
                    continue

                actual_year = year
                if m <= 3:
                     actual_year = year + 1
                elif m >= 4:
                     actual_year = year
                
                try:
                    date_obj = datetime(actual_year, m, day)
                    date_str = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue

                locs = col_loc.split('\n')
                cats = col_cat.split('\n')
                count = max(len(locs), len(cats))
                
                for i in range(count):
                    l = locs[i].strip() if i < len(locs) else (locs[-1].strip() if locs else "")
                    cat = cats[i].strip() if i < len(cats) else (cats[-1].strip() if cats else "")
                    
                    if not l and not cat: continue
                    
                    # Direct Map
                    entry = {
                        "Date": date_str,
                        "Location": l,
                        "Category": cat,
                        "Content": "", # Content is empty, details to be filled in Monthly
                        "Time_Schedule": "", 
                        "Planner": "",
                        "Site_Lead": "",
                        "Medic": "",
                        "Staff_General": "",
                        "Photographer": "",
                        "Cook": "",
                        "Actual_Hours": "",
                        "Memo": "",
                        "Invoice_Status": ""
                    }
                    new_events.append(entry)
        
        # 3. Write to DB_Master_Events
        ws_events = self.db_sh.worksheet("DB_Master_Events")
        
        existing_records = ws_events.get_all_records()
        existing_keys = set()
        
        # Key strategy: Date + Category + Location
        for r in existing_records:
            k = f"{r['Date']}_{r['Category']}_{r['Location']}"
            existing_keys.add(k)
            
        rows_to_add = []
        headers = [
            "Date", "Location", "Category", "Content", "Time_Schedule", 
            "Planner", "Site_Lead", "Medic", "Staff_General", "Photographer", "Cook", 
            "Actual_Hours", "Memo", "Invoice_Status"
        ]
        
        added_count = 0
        for e in new_events:
            k = f"{e['Date']}_{e['Category']}_{e['Location']}"
            if k not in existing_keys:
                row_vals = [e[h] for h in headers]
                rows_to_add.append(row_vals)
                added_count += 1
        
        if rows_to_add:
            ws_events.append_rows(rows_to_add)
            logger.info(f"Added {added_count} new events from Annual {year}.")
        else:
            logger.info("No new events found (Skipped duplicates).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026, help="Target FY Year")
    args = parser.parse_args()

    syncer = AnnualToDB()
    syncer.sync(year=args.year)
