import sys
import os
import json
import gspread
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from gspread_formatting import *

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from modules.utils import setup_logger

logger = setup_logger("AggregateResponses")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/forms.responses.readonly"
]

class ShiftAggregator:
    def __init__(self):
        self.creds = self._authenticate()
        self.gd_client = gspread.authorize(self.creds)
        self.form_service = build('forms', 'v1', credentials=self.creds)
        self.config = self._load_config()
        self.monthly_sh = self.gd_client.open_by_key(self.config["monthly_ui_id"])
        self.db_sh = self.gd_client.open_by_key(self.config["backend_db_id"])
        # Separate Sheet for Aggregation
        self.shift_work_sh = self.gd_client.open_by_key(self.config["shift_work_id"])
        
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

    # ...

    def aggregate(self, target_ym, cutoff_date=None):
        # ... (Previous Logic) ...
                    
        # 6. Generate/Update Sheet in Separate Spreadsheet
        sheet_name = f"Shift_Work_{target_ym}"
        try:
            ws = self.shift_work_sh.worksheet(sheet_name)
            logger.info(f"Updating existing sheet in Shift Spreadsheet: {sheet_name}")
            existing_vals = ws.get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            ws = self.shift_work_sh.add_worksheet(title=sheet_name, rows=100, cols=20)
            logger.info(f"Created new sheet in Shift Spreadsheet: {sheet_name}")
            existing_vals = []

    def _load_config(self):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
            
    def get_candidates(self, target_ym):
        """
        Reads Monthly sheet to get Recruitment Candidates.
        Returns:
            label_map: dict[FormLabel] -> ColumnHeader
            ordered_cols: list[ColumnHeader]
        """
        try:
            ws = self.monthly_sh.worksheet(target_ym)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Sheet {target_ym} not found.")
            return {}, []
            
        raw_vals = ws.get_all_values()
        if len(raw_vals) < 2: return {}, []
        
        label_map = {} 
        ordered_cols = [] 
        
        for row in raw_vals[1:]:
            if len(row) <= 16: continue
            chk = row[16].strip().upper()
            if chk == 'TRUE':
                date = row[0]
                wd = row[1]
                loc = row[3]
                cat = row[4]
                cont = row[5]
                time_sch = row[6]
                
                # Form Label (Full)
                label = f"{date} ({wd}) 【{loc}】{cat}: {cont} {time_sch}"
                
                # Column Header (Display)
                # User Request: Date + Wd + Loc + Cat (with Line Break)
                header = f"{date} ({wd})\n{loc} {cat}"
                
                # Map Label -> Header
                label_map[label] = header
                
                if header not in ordered_cols:
                    ordered_cols.append(header)
                # If duplicate header exists (e.g. 2 events same cat/loc),
                # they will merge into one column.
                # User example showed diff loc/cat, so valid.
                # If collision happens for distinct contents, current spec merges them.
                # Assuming this is acceptable based on request.
                    
        return label_map, ordered_cols

    def get_staff_map(self):
        """
        Returns dict[Email] -> Name
        """
        try:
            ws = self.db_sh.worksheet("DB_Master_Staff")
            recs = ws.get_all_records()
            s_map = {}
            for r in recs:
                email = str(r.get("Email", "")).strip()
                if email:
                    s_map[email] = r.get("Name", "")
            return s_map
        except Exception as e:
            logger.error(f"Failed to read Staff Master: {e}")
            return {}

    def fetch_responses(self, form_id, cutoff_dt):
        """
        Fetch responses from Form API, created after cutoff_dt.
        cutoff_dt: datetime object (timezone aware usually, but Form API returns UTC ISO string).
        """
        try:
            res = self.form_service.forms().responses().list(formId=form_id).execute()
        except Exception as e:
            logger.error(f"Form API Error: {e}")
            return []
            
        if 'responses' not in res:
            return []
            
        valid_responses = []
        for r in res['responses']:
            ts_str = r['lastSubmittedTime'] # '2026-01-02T09:00:00.000Z'
            ts = date_parser.isoparse(ts_str)
            
            # Make cutoff offset aware if needed or compare carefully
            if ts.tzinfo is None:
                # Should be UTC, so assume UTC
                pass
            
            # Simple compare: if cutoff_dt has tz, fine.
            if ts >= cutoff_dt:
                valid_responses.append(r)
                
        return valid_responses

    def get_form_schema(self, form_id):
        try:
            return self.form_service.forms().get(formId=form_id).execute()
        except Exception as e:
            logger.error(f"Failed to get form schema: {e}")
            return {}

    def aggregate(self, target_ym, cutoff_date=None, output_suffix=""):
        logger.info(f"Aggregating responses for {target_ym} (suffix: {output_suffix})...")
        
        # 1. Config & Dates
        form_id = self.config.get("shift_form_id")
        if not form_id:
            logger.error("Form ID not found in config.")
            return

        # ... (Date logic handled below/preserved) ...
        if not cutoff_date:
            ym = datetime.strptime(target_ym, "%Y-%m")
            prev_m = ym.replace(day=1) - timedelta(days=1)
            cutoff_date = prev_m.replace(day=1)
            from datetime import timezone
            cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
            
        logger.info(f"Cutoff Date (UTC): {cutoff_date}")

        # 2. Get Candidates
        label_map, ordered_cols = self.get_candidates(target_ym)
        if not label_map:
            logger.info("No candidates found in Monthly sheet.")
            return

        # 2.5 Get Form Schema to find Question IDs
        schema = self.get_form_schema(form_id)
        name_q_id = None
        freq_q_id = None
        interview_q_id = None
        contact_q_id = None
        for item in schema.get('items', []):
            title = item.get('title', '')
            q_item = item.get('questionItem', {}).get('question', {})
            qid = q_item.get('questionId')
            if not qid:
                continue
            if "名前" in title or "Name" in title:
                name_q_id = qid
                logger.info(f"Found Name Question: {title} (ID: {name_q_id})")
            elif "シフトに入れますか" in title or "どれくらい" in title:
                freq_q_id = qid
                logger.info(f"Found Frequency Question: {title} (ID: {freq_q_id})")
            elif "面談" in title:
                interview_q_id = qid
                logger.info(f"Found Interview Question: {title} (ID: {interview_q_id})")
            elif "連絡" in title or "相談" in title:
                contact_q_id = qid
                logger.info(f"Found Contact Question: {title} (ID: {contact_q_id})")
            
        # 3. Get Staff Master (Optional Fallback)
        staff_map = self.get_staff_map() # Email -> Name
        
        # 4. Fetch Responses
        responses = self.fetch_responses(form_id, cutoff_date)
        logger.info(f"Fetched {len(responses)} valid responses.")
        
        # 5. Process
        matrix_data = {} # StaffName -> {Header: 'NG'/'OK'}
        
        for r in responses:
            email = r.get('respondentEmail', '')
            answers = r.get('answers', {})

            # Try to get Name from Answer
            staff_name = ""
            if name_q_id and name_q_id in answers:
                ans_obj = answers[name_q_id]
                staff_name = ans_obj.get('textAnswers', {}).get('answers', [{}])[0].get('value', '')

            if not staff_name:
                staff_name = staff_map.get(email, email)

            if not staff_name:
                staff_name = f"Unknown_{r['responseId'][:5]}"

            if staff_name not in matrix_data:
                matrix_data[staff_name] = {}

            # Extract frequency answer
            if freq_q_id and freq_q_id in answers:
                vals = answers[freq_q_id].get('textAnswers', {}).get('answers', [])
                matrix_data[staff_name]['_freq'] = ", ".join(v.get('value', '') for v in vals)

            # Extract interview preference
            if interview_q_id and interview_q_id in answers:
                vals = answers[interview_q_id].get('textAnswers', {}).get('answers', [])
                matrix_data[staff_name]['_interview'] = ", ".join(v.get('value', '') for v in vals)

            # Extract contact/consultation (free text)
            if contact_q_id and contact_q_id in answers:
                vals = answers[contact_q_id].get('textAnswers', {}).get('answers', [])
                matrix_data[staff_name]['_contact'] = vals[0].get('value', '') if vals else ""

            # Parse NG Dates
            all_ng = False
            all_ok = False
            ng_headers = []

            skip_qids = {q for q in (name_q_id, freq_q_id, interview_q_id, contact_q_id) if q}
            for qid, ans in answers.items():
                if qid in skip_qids:
                    continue
                vals = ans.get('textAnswers', {}).get('answers', [])
                for v in vals:
                    txt = v.get('value', '')
                    if txt == "全部NG":
                        all_ng = True
                    elif txt == "むしろ全部OK":
                        all_ok = True
                    elif txt in label_map:
                        ng_headers.append(label_map[txt])

            if all_ng:
                for h in ordered_cols:
                    matrix_data[staff_name][h] = "NG"
            elif all_ok:
                pass
            else:
                for h in ng_headers:
                    matrix_data[staff_name][h] = "NG"
                    
        # 6. Generate/Update Sheet
        sheet_name = f"Shift_Work_{target_ym}{output_suffix}"
        try:
            try:
                ws = self.shift_work_sh.worksheet(sheet_name)
                logger.info(f"Updating existing sheet in Shift Spreadsheet: {sheet_name}")
                # Read Existing
                existing_vals = ws.get_all_values()
                # Parse existing?
                # Complex if Staff list changed.
                # Let's rely on HEADER matching.
            except gspread.exceptions.WorksheetNotFound:
                ws = self.shift_work_sh.add_worksheet(title=sheet_name, rows=100, cols=20)
                logger.info(f"Created new sheet in Shift Spreadsheet: {sheet_name}")
                existing_vals = []
                
            # Headers
            # [Staff, Freq, Comment, Col1, Col2 ...]
            
            # Map Date -> Col Index
            # If dates in Monthly are duplicate? (e.g. same day different prog).
            # Then Candidates `ordered_cols` might have duplicates if I stored Date only?
            # `get_candidates`: `label_map[label] = date`. `ordered_cols.append(date)`.
            # If multiple events on same day, `ordered_cols` has duplicates?
            # `if date not in ordered_cols:` checks uniqueness.
            # So columns are aggregated by DATE.
            # Wait, if user marks NG for "Event A on Day 1", is it NG for "Event B on Day 1"?
            # Usually Shift is by DAY or Event?
            # "参加不可(NG)の日程" implies DATE.
            # So "NG on Day 1" means NG for all events on Day 1.
            # My logic aggregates by Date string. This is correct.
            
            headers = ["Staff", "希望頻度", "面談希望"] + ordered_cols + ["連絡・相談"]
            
            # Staff list: Merge existing users and new respondents.
            staff_list = list(matrix_data.keys())
            
            # If existing sheet, preserve manual rows?
            existing_staff = []
            if existing_vals and len(existing_vals) > 0:
                # Assuming Row 1 is headers.
                old_headers = existing_vals[0]
                # Find Staff col index (0)
                for row in existing_vals[1:]:
                    if row:
                        s = row[0]
                        if s and s not in staff_list:
                            existing_staff.append(s)
            
            full_staff = sorted(list(set(staff_list + existing_staff)))
            
            # Construct Rows
            final_rows = []
            
            # Map Old Header Index for preserving data
            # old_col_map = { date: index }
            old_idx_map = {}
            if existing_vals:
                for i, h in enumerate(existing_vals[0]):
                    old_idx_map[h] = i
                    
            # Map Old Staff Row Index
            old_staff_row_map = {}
            if existing_vals:
                for r_i, row in enumerate(existing_vals):
                    if r_i == 0: continue
                    if row:
                        old_staff_row_map[row[0]] = row
            
            for s in full_staff:
                row = [""] * len(headers)
                row[0] = s
                
                # Retrieve Old Data
                old_row = old_staff_row_map.get(s, [])
                
                # Fill Default from Old
                for c_i, h in enumerate(headers):
                    if h in old_idx_map and old_idx_map[h] < len(old_row):
                        row[c_i] = old_row[old_idx_map[h]]
                        
                # Overwrite with New Response data if present
                if s in matrix_data:
                    data = matrix_data[s]
                    if '_freq' in data:
                        row[1] = data['_freq']
                    if '_interview' in data:
                        row[2] = data['_interview']
                    if '_contact' in data:
                        row[len(headers) - 1] = data['_contact']
                    for d, status in data.items():
                        if d.startswith('_'):
                            continue
                        if status == "NG":
                            try:
                                idx = headers.index(d)
                                row[idx] = "NG"
                            except ValueError:
                                pass
                                
                final_rows.append(row)
                
            # Write
            ws.clear()
            ws.update(range_name='A1', values=[headers] + final_rows)
            
            # Formatting
            # NG = Red, Confirmed (◎) = Blue?
            # Using gspread_formatting
            
            rule_ng = ConditionalFormatRule(
                ranges=[GridRange.from_a1_range('D2:Z100', ws)],
                booleanRule=BooleanRule(
                    condition=BooleanCondition('TEXT_EQ', ['NG']),
                    format=CellFormat(backgroundColor=Color(1, 0.8, 0.8)) # Reddish
                )
            )
            rule_confirmed = ConditionalFormatRule(
                ranges=[GridRange.from_a1_range('D2:Z100', ws)],
                booleanRule=BooleanRule(
                    condition=BooleanCondition('TEXT_EQ', ['◎']), # Confirmed
                    format=CellFormat(backgroundColor=Color(0.8, 0.8, 1)) # Blueish
                )
            )
            
            rules = get_conditional_format_rules(ws)
            # Remove old rules? Or append?
            # To avoid dupe, clear logic is complex.
            # But we cleared sheet, rules might persist?
            # gspread `clear()` clears data, not rules usually.
            # Let's overwrite rules.
            rules.clear()
            rules.append(rule_ng)
            rules.append(rule_confirmed)
            rules.save()
            
            # Freeze Panes
            ws.freeze(rows=1, cols=3)
            
            # Wrap Text for Header Row
            format_cell_range(ws, '1:1', CellFormat(wrapStrategy='WRAP'))
            
            logger.info("Sheet Generated and Formatted.")
            
        except Exception as e:
            logger.error(f"Failed to generate Matrix: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=str, default="2026-04", help="Target Month YYYY-MM")
    # Date limit
    parser.add_argument("--cutoff", type=str, help="Cutoff Date YYYY-MM-DD (UTC)")
    parser.add_argument("--output_suffix", type=str, default="", help="Suffix for output sheet name")
    
    args = parser.parse_args()

    agg = ShiftAggregator()
    
    cutoff = None
    if args.cutoff:
        cutoff = date_parser.parse(args.cutoff).replace(tzinfo=datetime.timezone.utc)
        
    agg.aggregate(target_ym=args.month, cutoff_date=cutoff, output_suffix=args.output_suffix)
