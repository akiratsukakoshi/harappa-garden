import sys
import os
import json
import gspread
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from modules.utils import setup_logger

logger = setup_logger("ShiftManagerInit")

# Constants
SPREADSHEET_ID = "14JuhBGiS2IUiv1F89bCBFEppXeF9paflL6Ll1gxrZGM"
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def authenticate():
    """Authenticates with Google APIs using Service Account or OAuth."""
    if not os.path.exists(CREDENTIALS_PATH):
        logger.error(f"Credentials file not found at {CREDENTIALS_PATH}")
        sys.exit(1)

    creds = None
    
    # Check if Service Account
    try:
        with open(CREDENTIALS_PATH, 'r') as f:
            data = json.load(f)
            if data.get("type") == "service_account":
                logger.info("Using Service Account.")
                creds = service_account.Credentials.from_service_account_file(
                    CREDENTIALS_PATH, scopes=SCOPES
                )
    except Exception as e:
        logger.error(f"Error reading credentials file: {e}")

    if not creds:
        # OAuth Flow (Reuse token if available)
        logger.info("Using OAuth Client.")
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                # Note: run_local_server might not work in headless env without port forwarding, 
                # but we assume credentials might be set up or this is a service account env.
                # If this hangs, we know why.
                creds = flow.run_local_server(port=0)
            
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())

    return creds

def init_sheets():
    creds = authenticate()
    client = gspread.authorize(creds)

    try:
        sh = client.open_by_key(SPREADSHEET_ID)
        logger.info(f"Connected to Spreadsheet: {sh.title}")
    except Exception as e:
        import traceback
        logger.error(f"Failed to open spreadsheet: {e}")
        logger.error(traceback.format_exc())
        return

    # Define Schema
    # 1. UI_Annual_Planner
    # Headers: Day, 1月_曜, 1月_場所, 1月_内容 ... 12月_内容
    # Total Cols: 1 (Day) + 12 * 3 = 37 columns
    
    annual_headers = ["Day"]
    for i in range(1, 13):
        annual_headers.extend([f"{i}月_曜", f"{i}月_場所", f"{i}月_内容"])

    schema = {
        "UI_Annual_Planner": {
            "headers": annual_headers,
            "description": "Grid: Day x Month(Day/Loc/Content)"
        },
        "UI_Monthly_Detail": {
            "headers": ["Date", "Day", "Course_Category", "Program_Name", "Location", "Time", "Headcount_Required", "Note", "Status"],
            "description": "Monthly Detail List"
        },
        "UI_Shift_Manager": {
            "headers": ["Date", "Program_Name", "Headcount_Required", "Candidates", "Confirmed_1", "Confirmed_2", "Confirmed_3", "Confirmed_4", "Confirmed_5"],
            "description": "Shift Adjustments"
        },
        "DB_Master_Program": {
            "headers": ["Program_ID", "Program_Name", "Course_Category", "Abbrev", "Standard_Time", "Standard_Headcount", "Default_Location"],
            "description": "Master: Programs"
        },
        "DB_Master_Staff": {
            "headers": ["Staff_ID", "Name", "Nickname", "Freee_ID", "Email", "Rank", "Status"],
            "description": "Master: Staff"
        },
        "DB_Schedule": {
            "headers": ["Date", "Program_ID", "Course_Category", "Program_Name", "Location", "Time_Start", "Time_End", "Headcount_Required", "Status", "Note"],
            "description": "Transaction: Schedule"
        },
        "DB_Shift_Log": {
            "headers": ["Date", "Program_ID", "Staff_ID", "Status", "Work_Hours"],
            "description": "Transaction: Shift Log"
        }
    }

    existing_titles = [s.title for s in sh.worksheets()]

    for sheet_name, config in schema.items():
        if sheet_name not in existing_titles:
            logger.info(f"Creating sheet: {sheet_name}")
            # Ensure enough columns for Annual Planner
            cols = 40 if sheet_name == "UI_Annual_Planner" else 20
            worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=cols)
        else:
            logger.info(f"Sheet exists: {sheet_name}. Updating headers.")
            worksheet = sh.worksheet(sheet_name)
            # Resize if needed for Annual Planner
            if sheet_name == "UI_Annual_Planner" and worksheet.col_count < 40:
                worksheet.resize(cols=40)
        
        # Update Headers
        if sheet_name == "UI_Monthly_Detail":
            # Header Row 1 -> Config
            worksheet.update(range_name='A1:B1', values=[["Year-Month:", "2026-01"]])
            # Header Row 3 -> Cols
            worksheet.update(range_name='A3', values=[config["headers"]])
        else:
            worksheet.update(range_name='A1', values=[config["headers"]])
        
        # Special setup for UI_Annual_Planner (Fill days and weekdays)
        if sheet_name == "UI_Annual_Planner":
            from datetime import datetime
            
            # Fill A2:A32 with 1..31
            # Also fill Weekdays
            # We construct a matrix: Rows=31, Cols=37
            data_grid = []
            
            # Weekday mapping
            w_map = ["月", "火", "水", "木", "金", "土", "日"]
            year = 2026
            
            for d in range(1, 32):
                row_data = [str(d)] # Col A
                for m in range(1, 13):
                    # Check if valid date
                    try:
                        dt = datetime(year, m, d)
                        wd = w_map[dt.weekday()]
                    except ValueError:
                        wd = "-" # Invalid date (e.g. Feb 30)
                    
                    # Columns: Weekday, Location(Empty), Content(Empty)
                    row_data.extend([wd, "", ""])
                data_grid.append(row_data)
                
            # Update grid
            # Range: A2 to ending col. 1 (Day) + 12*3 = 37 cols. 
            # End Col AI = 35? No, let's calc.
            # 1 + 36 = 37. Excel col 37 is AK.
            # A=1, Z=26, AA=27... AK=37.
            
            # Use unconstrained range update
            worksheet.update(range_name='A2', values=data_grid)

    logger.info("Initialization Complete.")

if __name__ == "__main__":
    init_sheets()
