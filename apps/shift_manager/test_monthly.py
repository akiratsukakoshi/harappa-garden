from apps.shift_manager.monthly_manager import MonthlyManager
from modules.utils import setup_logger
import sys

# Setting path again just in case standalone run
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

logger = setup_logger("TestMonthly")

def test_monthly_flow():
    manager = MonthlyManager()
    
    # 1. Test Load
    # Pre-condition: Date 2026-01-01 "初詣" exists from Update Task 1.
    # UI B1 needs to be '2026-01' (Should be set by init_sheets)
    
    logger.info("--- Testing Load ---")
    manager.load_monthly_data()
    
    # Verify UI content by reading back
    ws_ui = manager.sh.worksheet("UI_Monthly_Detail")
    ui_vals = ws_ui.get_all_values()
    # Expect data at Row 4
    if len(ui_vals) >= 4:
        logger.info(f"UI Row 4: {ui_vals[3]}")
    else:
        logger.error("UI Load failed, no data row.")
        return

    # 2. Test Save
    # Modify Row 4 in UI
    # Indices: Date(0), Day(1), Course(2), Prog(3), Loc(4), Time(5), Head(6), Note(7), Status(8)
    # Let's change Time and Note
    logger.info("--- Testing Save ---")
    
    # We simulate user edit by updating the sheet directly
    # Row 4 is Index 4 in 1-based gspread? Yes.
    # Update Time(F), Note(H)
    ws_ui.update(range_name='F4:H4', values=[["10:00-12:00", "", "Modified by Test"]])
    
    # Execute Save
    manager.save_monthly_details()
    
    # Verify DB
    ws_db = manager.sh.worksheet("DB_Schedule")
    db_records = ws_db.get_all_records()
    
    # Find records for 2026-01-01
    found = False
    for r in db_records:
        if r['Date'] == "2026-01-01" and r['Note'] == "Modified by Test":
            logger.info(f"DB Verification SUCCESS: {r}")
            found = True
            break
            
    if not found:
        logger.error("DB Verification FAILED.")

if __name__ == "__main__":
    test_monthly_flow()
