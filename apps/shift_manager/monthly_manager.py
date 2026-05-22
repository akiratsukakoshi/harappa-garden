import sys
import os
import json
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from modules.utils import setup_logger

logger = setup_logger("MonthlyManager")

# Constants
SPREADSHEET_ID = "14JuhBGiS2IUiv1F89bCBFEppXeF9paflL6Ll1gxrZGM"
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class MonthlyManager:
    def __init__(self, spreadsheet_id=SPREADSHEET_ID):
        self.client = self._authenticate()
        self.sh = self.client.open_by_key(spreadsheet_id)
        
    def _authenticate(self):
        if not os.path.exists(CREDENTIALS_PATH):
            logger.error(f"Credentials file not found at {CREDENTIALS_PATH}")
            sys.exit(1)

        creds = None
        # Service Account Check
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
            # OAuth
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
        
        return gspread.authorize(creds)

    def load_monthly_data(self):
        ws_ui = self.sh.worksheet("UI_Monthly_Detail")
        ws_db = self.sh.worksheet("DB_Schedule")
        
        # 1. Get Config (Year-Month) from B1
        try:
            target_ym = ws_ui.acell('B1').value
            if not target_ym:
                logger.error("B1 (Year-Month) is empty.")
                return
            logger.info(f"Loading data for: {target_ym}")
        except Exception as e:
            logger.error(f"Failed to read B1: {e}")
            return

        # 2. Get DB Data
        records = ws_db.get_all_records()
        
        # 3. Filter
        filtered_rows = []
        w_map = ["月", "火", "水", "木", "金", "土", "日"]
        
        for r in records:
            d_str = str(r['Date']).strip()
            # Date starts with "YYYY-MM"
            if d_str.startswith(target_ym):
                # Calculate Day/Weekday
                try:
                    dt = datetime.strptime(d_str, "%Y-%m-%d")
                    day_str = f"{dt.day}({w_map[dt.weekday()]})"
                except:
                    day_str = ""
                
                # Headers: ["Date", "Day", "Course_Category", "Program_Name", "Location", "Time", "Headcount_Required", "Note", "Status"]
                # Map DB to UI
                # DB: Date, Program_ID, Course_Category, Program_Name, Location, Time_Start, Time_End, Headcount_Required, Status, Note
                
                # Time formatting
                t_start = r.get("Time_Start", "")
                t_end = r.get("Time_End", "")
                time_str = f"{t_start}-{t_end}" if t_start or t_end else ""
                
                row = [
                    d_str,
                    day_str,
                    r.get("Course_Category", ""),
                    r.get("Program_Name", ""),
                    r.get("Location", ""),
                    time_str,
                    r.get("Headcount_Required", ""),
                    r.get("Note", ""),
                    r.get("Status", "Planned")
                ]
                filtered_rows.append(row)
        
        # Sort by Date
        filtered_rows.sort(key=lambda x: x[0])
        
        # 4. Write to UI
        # Clear existing from Row 4 (Rows 1-2 are config/spacer, 3 is header)
        # We need to be careful not to delete logic? No, list is pure data.
        
        # Determine range to clear.
        # Max rows = ws_ui.row_count. 
        # Better: get_all_values then offset?
        # gspread clear range
        ws_ui.batch_clear(["A4:I1000"]) # Assume max 1000 for now.
        
        if filtered_rows:
            ws_ui.update(range_name='A4', values=filtered_rows)
            logger.info(f"Loaded {len(filtered_rows)} rows.")
        else:
            logger.info("No matching records found.")

    def save_monthly_details(self):
        ws_ui = self.sh.worksheet("UI_Monthly_Detail")
        ws_db = self.sh.worksheet("DB_Schedule")
        
        # 1. Read UI Data (Row 4 onwards)
        # Headers at Row 3.
        # Values: A4:I...
        ui_data = ws_ui.get_all_values()
        if len(ui_data) < 4:
            logger.info("No data to save.")
            return
            
        # Headers are at index 2 (Row 3).
        # Data starts index 3 (Row 4).
        headers = ui_data[2] # ["Date", "Day", "Course_Category", "Program_Name", "Location", ...]
        data_rows = ui_data[3:]
        
        logger.info(f"Saving {len(data_rows)} rows from UI...")
        
        # 2. Read DB Data
        db_records = ws_db.get_all_records()
        
        # 3. Update Map
        # Key strategy: Date + Course_Category + Program_Name
        # Note: If User changes Program_Name in UI, we might lose link. 
        # Constraint: User should NOT change Date/Course/ProgramName in Monthly View.
        # They should only change Location, Time, Headcount, Note, Status.
        # This acts as a "Detail Editor", not "Structure Editor".
        
        db_rows_updated = []
        
        # Convert DB list to Dict for easy access?
        # Since we just want to update fields, let's iterate DB records and if match found in UI map, update.
        # Or iterate UI and update DB map.
        
        # Let's verify Uniqueness.
        # Map: "YYYY-MM-DD|Course|Prog" -> DB Record Index (or Obj)
        db_map = {}
        for idx, r in enumerate(db_records):
            k = f"{r['Date']}|{r.get('Course_Category', '')}|{r['Program_Name']}"
            db_map[k] = idx
            
        updates_count = 0
        
        for row in data_rows:
            if len(row) < 9: continue
            
            # Extract UI vals
            u_date = row[0]
            u_course = row[2]
            u_prog = row[3]
            u_loc = row[4]
            u_time = row[5]
            u_head = row[6]
            u_note = row[7]
            u_stat = row[8]
            
            if not u_date: continue
            
            key = f"{u_date}|{u_course}|{u_prog}"
            
            if key in db_map:
                idx = db_map[key]
                record = db_records[idx]
                
                # Update fields
                record['Location'] = u_loc
                record['Headcount_Required'] = u_head
                record['Note'] = u_note
                record['Status'] = u_stat
                
                # Parse Time "HH:MM-HH:MM"
                # Simple logic: Split by '-' or space
                # If no separator, put all in Start?
                t_start = ""
                t_end = ""
                if "-" in u_time:
                    parts = u_time.split("-")
                    t_start = parts[0].strip()
                    t_end = parts[1].strip() if len(parts) > 1 else ""
                else:
                    t_start = u_time
                
                record['Time_Start'] = t_start
                record['Time_End'] = t_end
                
                updates_count += 1
            else:
                logger.warning(f"Record not found in DB: {key}. Skipping Save.")
                
        # 4. Write Back to DB
        if updates_count > 0:
            # Reconstruct list
            headers = ["Date", "Program_ID", "Course_Category", "Program_Name", "Location", "Time_Start", "Time_End", "Headcount_Required", "Status", "Note"]
            final_values = []
            for r in db_records:
                final_values.append([str(r.get(h, "")) for h in headers])
            
            ws_db.clear()
            ws_db.update(range_name='A1', values=[headers] + final_values)
            logger.info(f"DB Updated. {updates_count} records modified.")
        else:
            logger.info("No modifications applied to DB.")

if __name__ == "__main__":
    manager = MonthlyManager()
    
    # Arg parser
    # Usage: python monthly_manager.py [load|save]
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "load":
            manager.load_monthly_data()
        elif mode == "save":
            manager.save_monthly_details()
        else:
            print("Usage: load | save")
    else:
        print("Usage: python monthly_manager.py [load|save]")
