import sys
import os
import json
import gspread
import calendar
import jpholiday
from datetime import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from gspread_formatting import set_column_width

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from modules.utils import setup_logger

logger = setup_logger("DBToMonthly")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class DBToMonthly:
    def __init__(self):
        self.creds = self._authenticate()
        self.client = gspread.authorize(self.creds)
        self.config = self._load_config()
        self.monthly_sh = self.client.open_by_key(self.config["monthly_ui_id"])
        self.db_sh = self.client.open_by_key(self.config["backend_db_id"])
        self.categories = self._load_categories()

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

    def _load_categories(self):
        ws = self.db_sh.worksheet("DB_Master_Categories")
        vals = ws.col_values(1)
        if vals:
             return vals[1:]
        return []

    def generate_monthly_sheet(self, target_ym):
        logger.info(f"Generating Monthly Sheet for: {target_ym}")
        
        ws_events = self.db_sh.worksheet("DB_Master_Events")
        records = ws_events.get_all_records()
        
        month_events = [r for r in records if str(r['Date']).startswith(target_ym)]
        
        try:
            ws = self.monthly_sh.worksheet(target_ym)
            logger.info(f"Sheet {target_ym} exists. Clearing...")
            ws.clear()
            # Clear formats is implied by clear usually? No, clear kills content/format.
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Creating sheet {target_ym}...")
            ws = self.monthly_sh.add_worksheet(title=target_ym, rows=100, cols=20)

        # Headers
        headers = [
            "日付", "曜日", "運営スケジュール", 
            "会場", "カテゴリ", "活動内容", "時間", 
            "企画者", "現場責任者", "応急衛生", "スタッフ", "フォトグラファー", "調理", 
            "実働時間", "備考", "請求", "アンケート"
        ]
        
        w_map = ["月", "火", "水", "木", "金", "土", "日"]
        data_rows = []
        row_types = [] 

        try:
            parts = target_ym.split("-")
            year = int(parts[0])
            month = int(parts[1])
            last_day = calendar.monthrange(year, month)[1]
        except:
            logger.error(f"Invalid Month Format: {target_ym}")
            return
            
        for d in range(1, last_day + 1):
            dt = datetime(year, month, d)
            d_str = dt.strftime("%Y-%m-%d")
            wd = w_map[dt.weekday()]
            
            is_holiday = jpholiday.is_holiday(dt)
            is_sunday = (dt.weekday() == 6)
            is_saturday = (dt.weekday() == 5)
            
            r_type = "NORMAL"
            if is_holiday or is_sunday:
                r_type = "RED"
            elif is_saturday:
                r_type = "BLUE"
            
            day_recs = [r for r in month_events if r['Date'] == d_str]
            
            if day_recs:
                for r in day_recs:
                    # Parse Recruitment_Target for Checkbox (True/False)
                    rec_flag = r.get('Recruitment_Target')
                    if str(rec_flag).upper() == 'TRUE':
                        rec_val = True
                    else:
                        rec_val = False

                    row = [
                        d_str, wd, "", 
                        r.get('Location', ''), r.get('Category', ''), r.get('Content', ''), r.get('Time_Schedule', ''),
                        r.get('Planner', ''), r.get('Site_Lead', ''), r.get('Medic', ''), r.get('Staff_General', ''), 
                        r.get('Photographer', ''), r.get('Cook', ''),
                        r.get('Actual_Hours', ''), r.get('Memo', ''), r.get('Invoice_Status', ''),
                        rec_val
                    ]
                    data_rows.append(row)
                    row_types.append(r_type)
            else:
                row = [
                    d_str, wd, "",
                    "", "", "", "",
                    "", "", "", "", "", "",
                    "", "", "", False
                ]
                data_rows.append(row)
                row_types.append(r_type)
            
        ws.update(range_name='A1', values=[headers] + data_rows)
        
        # --- Manual Batch Update ---
        requests = []
        sheet_id = ws.id
        
        # 1. Date Format (A2:A)
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id, 
                    "startRowIndex": 1, "endRowIndex": 1 + len(data_rows), 
                    "startColumnIndex": 0, "endColumnIndex": 1
                },
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "M/d"}}},
                "fields": "userEnteredFormat.numberFormat"
            }
        })
        
        # 2. Text Colors (Sat/Sun)
        # We iterate row types.
        for i, r_type in enumerate(row_types):
            if r_type == "NORMAL": continue
            
            color = {"red": 1.0, "green": 0.0, "blue": 0.0} if r_type == "RED" else {"red": 0.0, "green": 0.0, "blue": 1.0}
            
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": i + 1, "endRowIndex": i + 2,
                        "startColumnIndex": 0, "endColumnIndex": 2 # A and B
                    },
                    "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": color}}},
                    "fields": "userEnteredFormat.textFormat.foregroundColor"
                }
            })
            
        # 3. Background Colors (Gray)
        gray = {"red": 0.9, "green": 0.9, "blue": 0.9}
        # A2:B
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1 + len(data_rows), "startColumnIndex": 0, "endColumnIndex": 2},
                "cell": {"userEnteredFormat": {"backgroundColor": gray, "horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment)"
            }
        })
        # E2:E (Category) -> Index 4
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1 + len(data_rows), "startColumnIndex": 4, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {"backgroundColor": gray, "horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment)"
            }
        })
        # H2:P (Planner..Inv) -> Index 7 to 16
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1 + len(data_rows), "startColumnIndex": 7, "endColumnIndex": 16},
                "cell": {"userEnteredFormat": {"backgroundColor": gray}},
                "fields": "userEnteredFormat.backgroundColor"
            }
        })
        
        # 4. Center Alignment for Time (G, Index 6)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1 + len(data_rows), "startColumnIndex": 6, "endColumnIndex": 7},
                "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        })
        
        # 5. Header Style
        header_color = {"red": 0.8, "green": 0.8, "blue": 1.0}
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 17},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_color, 
                        "horizontalAlignment": "CENTER", 
                        "textFormat": {"bold": True}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)"
            }
        })
        
        # 6. Validation
        if self.categories:
            requests.append({
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": 1 + len(data_rows),
                        "startColumnIndex": 4,
                        "endColumnIndex": 5
                    },
                    "rule": {
                        'condition': {
                            'type': 'ONE_OF_LIST',
                            'values': [{"userEnteredValue": c} for c in self.categories]
                        },
                        'showCustomUi': True,
                        'strict': True
                    }
                }
            })

        # 7. Checkbox for Recruitment (Q, Index 16)
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 1 + len(data_rows),
                    "startColumnIndex": 16,
                    "endColumnIndex": 17
                },
                "rule": {
                    'condition': {'type': 'BOOLEAN'},
                    'showCustomUi': True
                }
            }
        })

        # Execute Batch
        if requests:
            ws.spreadsheet.batch_update({"requests": requests})
            
        # Column Widths (Simpler via gspread_formatting wrapper or manual)
        # Using wrapper for convenience as it generates simple requests usually.
        # But separate call.
        set_column_width(ws, 'A', 50)
        set_column_width(ws, 'B', 30)
        set_column_width(ws, 'C', 200)
        set_column_width(ws, 'D', 150)
        set_column_width(ws, 'E', 120)
        set_column_width(ws, 'F', 300)
        set_column_width(ws, 'G', 120)
        set_column_width(ws, 'Q', 60) # Questionnaire
            
        logger.info(f"Generated {target_ym} with {len(data_rows)} rows (New Layout & Manual Styling).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=str, default="2026-01", help="Target Month YYYY-MM")
    args = parser.parse_args()

    gen = DBToMonthly()
    gen.generate_monthly_sheet(target_ym=args.month)
