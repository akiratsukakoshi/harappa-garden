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

logger = setup_logger("ScheduleSyncer")

# Constants
SPREADSHEET_ID = "14JuhBGiS2IUiv1F89bCBFEppXeF9paflL6Ll1gxrZGM"
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class ScheduleSyncer:
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

    def sync(self, year=2026):
        logger.info(f"Starting Sync for Year: {year}")
        
        # 1. Read UI_Annual_Planner
        ws_planner = self.sh.worksheet("UI_Annual_Planner")
        raw_data = ws_planner.get_all_values()
        
        # 2. Read DB_Schedule to preserve manual edits (Time, Note, etc.)
        ws_schedule = self.sh.worksheet("DB_Schedule")
        existing_records = ws_schedule.get_all_records()
        
        # Build existing map: Key = "YYYY-MM-DD" -> List of records (since multiple can exist)
        # However, syncing strictly from Annual Planner implies Annual Planner is master "existence" source.
        # But we want to keep details if Content/Loc match or just by index?
        # Strategy:
        # Key = "YYYY-MM-DD" + "Program_Name" (Content).
        # IF content matches, we preserve Location/Time/Note.
        # If content changed, we treat as new?
        # Let's try to preserve by "Program_Name".
        
        db_map = {} # Key: "YYYY-MM-DD__ProgramName", Value: Record Dict
        for r in existing_records:
            d_str = str(r['Date']).strip()
            p_name = str(r['Program_Name']).strip()
            key = f"{d_str}__{p_name}"
            db_map[key] = r

        new_db_rows = []
        
        # 3. Iterate Annual Planner Grid
        # Header Row: 0. Data start: 1.
        # Cols: A=Day (0), Jan=[B(1) C(2) D(3)], Feb=[E(4) F(5) G(6)]...
        # Month M Offset = 1 + (M-1)*3.
        # Jan(1) -> 1. Col 1(Wd), 2(Loc), 3(Content).
        
        for row_idx, row in enumerate(raw_data[1:], start=1):
            if row_idx > 31: break 
            
            day_str = row[0]
            if not day_str.isdigit(): continue
            day = int(day_str)
            
            for m in range(1, 13):
                # Calculate base column index
                base_col = 1 + (m - 1) * 3
                
                # Check bounds
                if base_col + 2 >= len(row): break
                
                # col_wd = row[base_col]
                col_loc = row[base_col+1].strip()     # 1月_場所
                col_content = row[base_col+2].strip() # 1月_内容 (Course/Program)
                
                if not col_content and not col_loc:
                    continue

                # Check Valid Date
                try:
                    date_obj = datetime(year, m, day)
                    date_str = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue

                # Handle Multi-line (Soft Wrap)
                # Split by newline
                locs = col_loc.split('\n')
                contents = col_content.split('\n')
                
                # Normalize length. max(len(locs), len(contents))
                count = max(len(locs), len(contents))
                
                for i in range(count):
                    # Get Loc and Content safely
                    l = locs[i].strip() if i < len(locs) else (locs[-1].strip() if locs else "")
                    c = contents[i].strip() if i < len(contents) else (contents[-1].strip() if contents else "")
                    
                    if not l and not c: continue
                    
                    # Logic:
                    # In this new design, "Content" in Annual Planner maps to 'Course_Category'? or 'Program_Name'?
                    # User request: "Annual Planner has Course Name". "Loc has Location".
                    # Let's map: Annual.Content -> DB.Course_Category AND DB.Program_Name (initially same)
                    # OR is Program_Name blank?
                    # Let's set Course_Category = c, Program_Name = c (as default).
                    
                    category = c
                    program_name = c # Default
                    location = l
                    
                    # Check if exists to preserve Time/Note
                    key = f"{date_str}__{program_name}"
                    
                    if key in db_map:
                        # Preserve details from DB
                        existing = db_map[key]
                        record = {
                            "Date": date_str,
                            "Program_ID": existing.get("Program_ID", ""),
                            "Course_Category": category, # Update from UI
                            "Program_Name": existing.get("Program_Name", ""), # User might have refined Name in DB?
                                                                             # If we overwrite P_Name with category, we lose detail.
                                                                             # If matches, keep. If not?
                                                                             # Complicated. Let's assume Annual Planner "Content" is Broad Category.
                                                                             # Start with that.
                            "Location": location if location else existing.get("Location", ""), # UI priority if present
                            "Time_Start": existing.get("Time_Start", ""),
                            "Time_End": existing.get("Time_End", ""),
                            "Headcount_Required": existing.get("Headcount_Required", ""),
                            "Status": existing.get("Status", "Planned"),
                            "Note": existing.get("Note", "")
                        }
                    else:
                        # New Record
                        record = {
                            "Date": date_str,
                            "Program_ID": "",
                            "Course_Category": category,
                            "Program_Name": category, # Initial value
                            "Location": location,
                            "Time_Start": "",
                            "Time_End": "",
                            "Headcount_Required": "",
                            "Status": "Planned",
                            "Note": ""
                        }
                    
                    new_db_rows.append(record)

        # 4. Write Back
        # Sort by Date
        new_db_rows.sort(key=lambda x: x["Date"])
        
        headers = ["Date", "Program_ID", "Course_Category", "Program_Name", "Location", "Time_Start", "Time_End", "Headcount_Required", "Status", "Note"]
        
        final_values = []
        for r in new_db_rows:
            row = [str(r.get(h, "")) for h in headers]
            final_values.append(row)
            
        ws_schedule.clear()
        ws_schedule.update(range_name='A1', values=[headers] + final_values)
        logger.info(f"Sync Complete. Total Rows: {len(final_values)}")

if __name__ == "__main__":
    syncer = ScheduleSyncer()
    
    # Check for CLI args for year
    target_year = 2026
    if len(sys.argv) > 1:
        try:
            target_year = int(sys.argv[1])
        except:
            pass
            
    syncer.sync(year=target_year)
