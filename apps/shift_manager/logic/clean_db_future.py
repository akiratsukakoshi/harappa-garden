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

logger = setup_logger("CleanDBFuture")

# Constants
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class CleanDBFuture:
    def __init__(self):
        self.creds = self._authenticate()
        self.client = gspread.authorize(self.creds)
        self.config = self._load_config()
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

    def clean(self, dry_run=False):
        ws_events = self.db_sh.worksheet("DB_Master_Events")
        all_records = ws_events.get_all_values()
        
        if len(all_records) < 2:
            logger.info("Database is empty or only has headers.")
            return

        headers = all_records[0]
        data_rows = all_records[1:]
        
        # Find Date column index
        try:
            date_idx = headers.index("Date")
        except ValueError:
            logger.error("'Date' column not found.")
            return

        rows_to_keep = []
        rows_to_delete_count = 0
        
        target_date = datetime(2026, 4, 1)
        
        logger.info(f"Scanning {len(data_rows)} rows for events on or after 2026-04-01...")

        for row in data_rows:
            date_str = row[date_idx]
            keep = True
            
            try:
                # Handle possible formats if inconsistent, but assuming YYYY-MM-DD
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                if dt >= target_date:
                    keep = False
            except ValueError:
                # If date parse fails, keep it to be safe (or log warning)
                pass
            
            if keep:
                rows_to_keep.append(row)
            else:
                rows_to_delete_count += 1

        logger.info(f"Found {rows_to_delete_count} rows to delete.")
        
        if dry_run:
            logger.info("[DRY-RUN] No changes made.")
            return

        if rows_to_delete_count > 0:
            # Overwrite sheet
            # 1. Clear sheet
            ws_events.clear()
            # 2. Add Headers
            # 3. Add Kept Rows
            
            # Prepare new data
            new_data = [headers] + rows_to_keep
            ws_events.update(new_data)
            logger.info(f"Deleted {rows_to_delete_count} rows. Kept {len(rows_to_keep)} rows.")
        else:
            logger.info("Nothing to delete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview deletion without executing")
    args = parser.parse_args()

    cleaner = CleanDBFuture()
    cleaner.clean(dry_run=args.dry_run)
