from apps.shift_manager.sync_scheduler import ScheduleSyncer
from modules.utils import setup_logger
logger = setup_logger("TestSync")

def test_data_injection_and_sync():
    syncer = ScheduleSyncer()
    
    # Inject Test Data into UI_Annual_Planner
    # Target: 1月1日 (Row 2, Indices: Day(0), JanWd(1), JanLoc(2), JanCont(3))
    # Indices in 0-based array of row values?
    # gspread uses 1-based coordinates.
    # Jan 1st is Row 2.
    # Jan Loc is Col C (3).
    # Jan Content is Col D (4).
    
    ws = syncer.sh.worksheet("UI_Annual_Planner")
    
    # Test Case 1: Simple
    # Jan 1: Loc="神社", Content="初詣"
    ws.update(range_name='C2:D2', values=[["神社", "初詣"]])
    
    # Test Case 2: Multi-line (Double Booking)
    # Jan 15: Loc="逗子\n千葉", Content="企業\nおやこ"
    # Jan 15 is Row 16.
    ws.update(range_name='C16:D16', values=[["逗子\n千葉", "企業\nおやこ"]])
    
    logger.info("Test Data Injected.")
    
    # Run Sync
    syncer.sync(year=2026)
    
    # Check DB_Schedule
    ws_db = syncer.sh.worksheet("DB_Schedule")
    records = ws_db.get_all_records()
    
    logger.info(f"DB Records Found: {len(records)}")
    for r in records:
        logger.info(f"Record: {r['Date']} | {r['Course_Category']} | {r['Location']}")

if __name__ == "__main__":
    test_data_injection_and_sync()
