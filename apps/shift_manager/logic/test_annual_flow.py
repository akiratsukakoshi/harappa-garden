from apps.shift_manager.logic.annual_to_db import AnnualToDB
from modules.utils import setup_logger
logger = setup_logger("TestAnnualInject")

def inject_and_sync():
    syncer = AnnualToDB()
    ws = syncer.annual_sh.worksheet("UI_Annual_Planner")
    
    # 1. Inject Data (Jan 1, Jan 15)
    # Row 2 (Jan 1)
    # Cols C, D (Loc, Content)
    # Note: AnnualToDB reads 0-based index from get_all_values.
    # ws.update uses A1 notation.
    # C2, D2
    
    logger.info("Injecting test data...")
    ws.update(range_name='C2:D2', values=[["神社", "初詣"]])
    
    # Row 16 (Jan 15)
    ws.update(range_name='C16:D16', values=[["逗子\n千葉", "企業\nおやこ"]])
    
    # 2. Run Sync
    syncer.sync(year=2026)
    
if __name__ == "__main__":
    inject_and_sync()
