from apps.shift_manager.logic.annual_to_db import AnnualToDB
from apps.shift_manager.logic.db_to_monthly import DBToMonthly
from apps.shift_manager.logic.monthly_to_db import MonthlyToDB
from apps.shift_manager.logic.update_annual_structure import AnnualStructureUpdater
from modules.utils import setup_logger
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
logger = setup_logger("TestFullFlowJP")

def test_full_flow():
    # 1. Setup Annual Structure (Clean Slate)
    logger.info("--- Step 1: Update Annual Structure ---")
    updater = AnnualStructureUpdater()
    updater.run()
    
    # 2. Inject Data into UI_Annual_Planner_2026
    # Target: 4月 (Col 2,3,4 - indices 1,2,3... wait, Annual sync reads 0-based list)
    # Headers: Day, 4月_曜, 4月_会場, 4月_カテゴリ ...
    # C2 (Loc), D2 (Cat).
    # Value: "JPTestVenue", "おやこ学部" (Valid Category)
    
    logger.info("--- Step 2: Inject Test Data (Apr 1) ---")
    syncer_a = AnnualToDB()
    ws_annual = syncer_a.annual_sh.worksheet("UI_Annual_Planner_2026")
    ws_annual.update(range_name='C2:D2', values=[["JPTestVenue", "おやこ学部"]])

    # Clear DB to prevent pollution from previous runs
    ws_db = syncer_a.db_sh.worksheet("DB_Master_Events")
    ws_db.clear()
    ws_db.update(range_name='A1', values=[["Date", "Location", "Category", "Content", "Time_Schedule", 
            "Planner", "Site_Lead", "Medic", "Staff_General", "Photographer", "Cook", 
            "Actual_Hours", "Memo", "Invoice_Status"]])
    
    # 3. Sync Annual -> DB
    logger.info("--- Step 3: Annual -> DB (2026) ---")
    syncer_a.sync(year=2026)
    
    # 4. Generate Monthly (2026-04)
    logger.info("--- Step 4: DB -> Monthly (2026-04, New Layout) ---")
    syncer_b = DBToMonthly()
    syncer_b.generate_monthly_sheet("2026-04")
    
    # 5. Verify Monthly Content & Headers
    ws_m = syncer_b.monthly_sh.worksheet("2026-04")
    
    # Read UNFORMATTED to check Date Logic if needed, or FORMATTED for Display?
    # Test script runs in python, reading via gspread.
    # Default is Formatted.
    # Date (A2) should be "4/1" if format applied? or "2026-04-01"?
    # If format is applied, value returned by API depends on RenderOption.
    # By default, FORMATTED. So we might see "4/1".
    
    headers = ws_m.row_values(1)
    # A:日付, B:曜日, C:運営スケジュール, D:会場(Old C), E:カテゴリ(Old D), F:活動内容(Old E)
    if headers[2] == "運営スケジュール":
        logger.info("Header Verification SUCCESS: Ops Schedule found.")
    else:
        logger.error(f"Header Verification FAILED: Col C = {headers[2]}")
        # return

    # Check Data
    # Row 2 (Apr 1).
    # A2: Date, B2: Week, C2: Ops, D2: Loc, E2: Cat, F2: Cont
    vals = ws_m.row_values(2)
    # [0]=Date, [1]=Wk, [2]=Ops, [3]=Loc, [4]=Cat, [5]=Cont
    
    val_date = vals[0]
    val_ops = vals[2]
    val_loc = vals[3]
    val_cat = vals[4]
    
    logger.info(f"Row 2 Date Value: {val_date}") 
    # Can be "4/1" or "2026-04-01" depending on format status.
    # Validating existence is enough.
    
    if val_ops == "":
        logger.info("Ops Schedule Empty as expected.")
    else:
        logger.error(f"Ops Schedule Not Empty: {val_ops}")

    if val_loc == "JPTestVenue" and val_cat == "おやこ学部":
         logger.info("Data Verification SUCCESS: Initial Data Loaded.")
    else:
         logger.error(f"Data Verification FAILED: Loc={val_loc}, Cat={val_cat}")

    # 6. Monthly -> DB Sync (User Edit)
    logger.info("--- Step 5: Monthly -> DB (Edit Sync) ---")
    # Edit Monthly
    # Modify Ops (C2) -> "OpsNote" (Should be ignored)
    # Modify Location (D2) -> "EditedVenue"
    # Modify Content (F2) -> "NewContent"
    
    # Update Range C2:F2
    # C:Ops, D:Loc, E:Cat, F:Cont
    ws_m.update(range_name='C2:F2', values=[["OpsNote", "EditedVenue", "おやこ学部", "NewContent"]])
    
    syncer_c = MonthlyToDB()
    syncer_c.sync_month("2026-04")
    
    # 7. Verify DB
    ws_db = syncer_c.db_sh.worksheet("DB_Master_Events")
    records = ws_db.get_all_records()
    found = False
    for r in records:
        if r['Date'] == '2026-04-01':
            logger.info(f"DB Record: {r}")
            if r['Location'] == 'EditedVenue' and r['Content'] == 'NewContent':
                 found = True
                 logger.info("DB Sync Verification SUCCESS.")
                 break
    if not found:
        logger.error("DB Sync Verification FAILED.")

if __name__ == "__main__":
    test_full_flow()
