from apps.shift_manager.logic.monthly_to_db import MonthlyToDB
from apps.shift_manager.logic.db_to_monthly import DBToMonthly
from modules.utils import setup_logger
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
logger = setup_logger("TestPhase2")

def test_bidirectional():
    monthly = MonthlyToDB()
    gen = DBToMonthly()
    target_ym = "2026-01"
    
    # 1. Simulate User Edit in Monthly UI
    # We know Row 2 is Jan 1 (from previous Seed).
    # Cols:
    # A=Date, B=Week, C=Loc, D=Cat, E=Cont, F=Time
    # G=Planner
    # M=ActHrs
    # O=Inv
    
    ws = monthly.monthly_sh.worksheet(target_ym)
    
    logger.info("Simulating User Edit...")
    # Update Loc(C2) to "Updated by Test"
    # Update Time(F2) to "10:00-12:00"
    # Update Planner(G2) to "Tukapontas"
    
    ws.update(range_name='C2:G2', values=[["Updated by Test", "初詣", "初詣", "10:00-12:00", "Tukapontas"]])
    
    # 2. Sync to DB
    logger.info("Syncing Monthly to DB...")
    monthly.sync_month(target_ym)
    
    # 3. Verify DB
    ws_db = monthly.db_sh.worksheet("DB_Master_Events")
    records = ws_db.get_all_records()
    
    found = False
    for r in records:
        if r['Date'] == '2026-01-01' and r['Location'] == 'Updated by Test' and r['Planner'] == 'Tukapontas':
            logger.info(f"DB Verification SUCCESS: {r}")
            found = True
            break
            
    if not found:
        logger.error("DB Verification FAILED.")
        return

    # 4. (Optional) Re-generate Monthly to ensure persistence
    logger.info("Re-generating Monthly from DB...")
    gen.generate_monthly_sheet(target_ym)
    
    # Check if data persists
    val = ws.acell('C2').value
    if val == "Updated by Test":
        logger.info("Round-trip Persistence SUCCESS.")
    else:
        logger.error(f"Round-trip failed. C2={val}")

if __name__ == "__main__":
    test_bidirectional()
