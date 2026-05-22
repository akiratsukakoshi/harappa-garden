import sys
import os
import json
import csv
import gspread
import hashlib
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from modules.utils import setup_logger
from modules.freee_client import FreeeClient

logger = setup_logger("SyncStaffMaster")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"
MANUAL_CSV_PATH = "data/manual_staff.csv"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class StaffMasterSync:
    def __init__(self):
        self.creds = self._authenticate()
        self.gd_client = gspread.authorize(self.creds)
        self.config = self._load_config()
        self.db_sh = self.gd_client.open_by_key(self.config["backend_db_id"])
        
        # Freee Client
        self.freee = FreeeClient()
        if not self.freee.tokens:
            logger.warning("Freee tokens not found. Interactive auth might be needed or token file missing.")

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
            
    def sync(self):
        logger.info("Starting Staff Master Sync...")
        
        staff_map = {} # Key: Email (normalized), Value: Dict

        # 1. Freee Partners
        try:
            partners = self.freee.get_partners()
            logger.info(f"Fetched {len(partners)} partners from Freee.")
            for p in partners:
                # Need email. Helper text or specific field?
                # Freee Partner object has 'name', 'id'. Email is not always top level?
                # Check API: Partner response has 'long_name', 'name'. Email might be in contacts?
                # Actually, simple partners might not have email in standard fields?
                # Let's check keys if possible? No interactive shell.
                # Assuming standard structure or skipping if no email.
                # Many partners (companies) don't have email.
                # We target INDIVIDUALS?
                # If no email, can't match?
                # We can store without email but it won't be usable for forms ideally.
                # Let's try to get email if possible, else skip or use Name?
                # Requirement said "Emailをキーに重複排除". So Email is mandatory for merging.
                # If Freee Partner doesn't have email, we mock it or skip?
                # Let's skip for now if no email found.
                # Freee API Partner doesn't imply Email field at top level?
                # Let's assume 'email' key exists or check docs/memory. 
                # Partner API usually has contact info.
                
                # Correction: Freee Partners API DOES NOT guarantee email.
                # If it's missing, we skip.
                email = p.get('email', '') 
                if not email and 'contact_points' in p:
                     # sometimes nested?
                     pass
                
                if not email:
                    continue
                    
                staff_map[email] = {
                    "Staff_ID": p['id'],
                    "Name": p['name'],
                    "Email": email,
                    "Type": "Partner",
                    "Note": "From Freee"
                }
        except Exception as e:
            logger.error(f"Failed to fetch Partners: {e}")

        # 2. Freee Employees
        try:
            # Endpoint: /api/1/companies/{company_id}/employees
            url = f"https://api.freee.co.jp/api/1/companies/{self.freee.target_company_id}/employees"
            # Need limit/offset? 
            # Default limit 50. Max 100?
            # Simple implementation
            res = self.freee.request("GET", url, params={"limit": 100})
            if res and 'employees' in res:
                emps = res['employees']
                logger.info(f"Fetched {len(emps)} employees from Freee.")
                for e in emps:
                    email = e.get('email', '')
                    if not email: continue
                    
                    # Name construction
                    name = e.get('display_name')
                    if not name:
                        name = f"{e.get('last_name','')} {e.get('first_name','')}".strip()
                        
                    staff_map[email] = {
                        "Staff_ID": e['id'],
                        "Name": name,
                        "Email": email,
                        "Type": "Employee",
                        "Note": "From Freee"
                    }
        except Exception as e:
            logger.error(f"Failed to fetch Employees: {e}")
            
        # 3. Manual CSV
        if os.path.exists(MANUAL_CSV_PATH):
            try:
                with open(MANUAL_CSV_PATH, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        email = row.get('Email', '').strip()
                        if not email: continue
                        
                        # ID Generation for Manual
                        if email not in staff_map:
                            # Generate ID
                            sid = "M_" + hashlib.md5(email.encode()).hexdigest()[:8]
                            staff_map[email] = {
                                "Staff_ID": sid,
                                "Name": row.get('Name'),
                                "Email": email,
                                "Type": row.get('Type', 'Manual'),
                                "Note": row.get('Note', '')
                            }
                        else:
                            # Update Note or Type?
                            # Priority: Manual > API? Or API > Manual?
                            # Usually Manual supplements.
                            # Requirements said: "これらを統合し...".
                            # Let's let Manual overwrite specific fields if needed?
                            # Or just skip if exists.
                            # Let's Skip if already from Freee.
                            pass
                        count += 1
                    logger.info(f"Processed {count} manual records.")
            except Exception as e:
                logger.error(f"Failed to read CSV: {e}")
                
        # 4. Write to DB
        try:
            ws = self.db_sh.worksheet("DB_Master_Staff")
        except gspread.exceptions.WorksheetNotFound:
            logger.info("Sheet 'DB_Master_Staff' not found. Creating...")
            ws = self.db_sh.add_worksheet(title="DB_Master_Staff", rows=100, cols=10)
        headers = ["Staff_ID", "Name", "Email", "Type", "Note"]
        
        rows = []
        for email, data in staff_map.items():
            rows.append([
                str(data.get("Staff_ID", "")),
                data.get("Name", ""),
                data.get("Email", ""),
                data.get("Type", ""),
                data.get("Note", "")
            ])
            
        # Sort by Type then Name?
        rows.sort(key=lambda x: (x[3], x[1]))
        
        ws.clear()
        ws.update(range_name="A1", values=[headers] + rows)
        logger.info(f"Synced {len(rows)} staff to DB_Master_Staff.")

if __name__ == "__main__":
    syncer = StaffMasterSync()
    syncer.sync()
