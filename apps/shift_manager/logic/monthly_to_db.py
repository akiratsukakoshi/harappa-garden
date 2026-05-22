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

logger = setup_logger("MonthlyToDB")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class MonthlyToDB:
    def __init__(self):
        self.creds = self._authenticate()
        self.client = gspread.authorize(self.creds)
        self.config = self._load_config()
        self.monthly_sh = self.client.open_by_key(self.config["monthly_ui_id"])
        self.db_sh = self.client.open_by_key(self.config["backend_db_id"])

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

    def sync_month(self, target_ym):
        """
        target_ym: "YYYY-MM" (e.g. "2026-01")
        Reads the Monthly Sheet for YYYY-MM (New Layout) and updates DB_Master_Events.
        """
        logger.info(f"Syncing Monthly Sheet ({target_ym}) to DB...")
        
        try:
            ws_ui = self.monthly_sh.worksheet(target_ym)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Sheet {target_ym} not found.")
            return

        ui_data = ws_ui.get_all_values()
        
        # New Layout Headers in Row 1.
        # 0:日付, 1:曜日, 2:運営スケジュール(IGNORE), 
        # 3:会場, 4:カテゴリ, 5:活動内容, 6:時間...
        
        if len(ui_data) < 2:
            logger.info("No data in Monthly Sheet.")
            return
            
        ui_records = []
        for row in ui_data[1:]:
            if len(row) < 1: continue
            
            def val(idx):
                return row[idx].strip() if idx < len(row) else ""
            
            r_date = val(0)
            
            # r_date might be "YYYY-MM-DD" if we use raw value, which get_all_values() returns?
            # get_all_values() returns "Formatted Value" (displayed value) by default.
            # If we set NumberFormat "M/d", then "2026-01-26" displays as "1/26".
            # get_all_values() might return "1/26"! This breaks Logic.
            # We MUST use value_render_option='UNFORMATTED_VALUE' or 'FORMULA' to get proper string?
            # Or use get_all_records? records assume header.
            # But header "運営スケジュール" is not in DB scheme.
            
            # Solution: Use gspread's get_all_values(value_render_option='UNFORMATTED_VALUE')?
            # Actually standard gspread `get_all_values()` usually gets formatted values.
            # But we need DATE string "2026-01-01".
            # Let's check `ws_ui.get_all_values(value_render_option='UNFORMATTED_VALUE')`.
            # Date in Sheets unformatted is Serial Number (float) e.g. 45000.
            # That's hard to parse.
            
            # Alternative: Assume user didn't break column A.
            # If "M/d" is returned, we need to infer Year.
            # `target_ym` gives us Year ("2026").
            # But user might have typed wrong date.
            
            # Let's use `get('A:Z', value_render_option='FORMATTED_VALUE')`?
            # Wait, if format is `M/d`, formatted value IS `1/26`.
            # If we want `2026-01-26`, checking if gspread allows getting underlying value easily.
            # `worksheet.get(..., value_render_option='UNFORMATTED_VALUE')` -> Serial Number.
            
            # Best way: MonthlyToDB should rely on the fact that A-col is locked/system.
            # If row 2 corresponds to day 1, row 3 to day 2...
            # But user might have added rows.
            
            # Let's use `value_render_option='FORMULA'`?
            # If it's pure value, formula returns string/number.
            # If user entered `2026-01-01`, formula might vary.
            
            # Let's rely on gspread `get_all_values` fetching displayed values and Parse it? 
            # "1/26".
            # But what if locale differs?
            
            # Actually, `db_to_monthly` writes `YYYY-MM-DD` string.
            # Google Sheets Auto-detects Date.
            # If we apply `M/d` format, it displays `1/26`.
            # We need to retrieve `2026-01-26`.
            
            # Let's try `ws_ui.get(..., value_render_option='UNFORMATTED_VALUE')` 
            # and converting serial date in Python.
            # Serial 1 = 1899-12-30.
            pass

        # To handle Serial Dates safely:
        raw_vals = ws_ui.get(value_render_option='UNFORMATTED_VALUE')
        # raw_vals[0] header.
        
        for row in raw_vals[1:]:
            if len(row) < 1: continue
            
            r_date_raw = row[0] 
            # Could be float (Serial) or String (if text).
            
            r_date_str = ""
            if isinstance(r_date_raw, (int, float)):
                # Convert Serial
                dt = datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(r_date_raw))
                r_date_str = dt.strftime("%Y-%m-%d")
            else:
                # String logic
                r_date_str = str(r_date_raw).strip()
            
            if not r_date_str.startswith(target_ym): continue 
            
            def val(idx):
                if idx < len(row):
                    return str(row[idx]).strip()
                return ""
            
            # Map New Layout Index to DB Field
            # 0:Date, 1:Week, 2:Ops(Ignore), 3:Loc, 4:Cat, 5:Content, 6:Time...
            
            rec = {
                "Date": r_date_str,
                "Location": val(3),          # 会場 (New Index)
                "Category": val(4),          # カテゴリ
                "Content": val(5),           # 活動内容
                "Time_Schedule": val(6),     # 時間
                "Planner": val(7),           # 企画者
                "Site_Lead": val(8),         # 現場責任者
                "Medic": val(9),             # 応急衛生
                "Staff_General": val(10),    # スタッフ
                "Photographer": val(11),     # フォトグラファー
                "Cook": val(12),             # 調理
                "Actual_Hours": val(13),     # 実働時間
                "Memo": val(14),             # 備考
                "Invoice_Status": val(15),   # 請求
                "Recruitment_Target": val(16)# アンケート
            }
            ui_records.append(rec)
            
        logger.info(f"Read {len(ui_records)} records from UI (New Layout).")
        
        # Update DB (Overwrite for Month)
        ws_db = self.db_sh.worksheet("DB_Master_Events")
        db_data = ws_db.get_all_records()
        
        non_target_records = [r for r in db_data if not str(r['Date']).startswith(target_ym)]
        
        headers = [
            "Date", "Location", "Category", "Content", "Time_Schedule", 
            "Planner", "Site_Lead", "Medic", "Staff_General", "Photographer", "Cook", 
            "Actual_Hours", "Memo", "Invoice_Status", "Recruitment_Target"
        ]
        
        final_rows = []
        for r in non_target_records:
            final_rows.append([str(r.get(h, "")) for h in headers])
            
        for r in ui_records:
            final_rows.append([str(r.get(h, "")) for h in headers])
            
        ws_db.clear()
        ws_db.update(range_name='A1', values=[headers] + final_rows)
        
        logger.info(f"DB Updated. Total Records: {len(final_rows)}")
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=str, default="2026-01", help="Target Month YYYY-MM")
    args = parser.parse_args()

    syncer = MonthlyToDB()
    syncer.sync_month(target_ym=args.month)
