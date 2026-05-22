import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from apps.kpi_monitor.sheet_syncer import SheetSyncer
from apps.kpi_monitor.config import DEPT_CATEGORIES, UNALLOCATED_SHEET_NAME, TARGET_FISCAL_YEAR
from modules.utils import setup_logger

logger = setup_logger("SheetInitializer")

def generate_headers(start_year, years=2):
    headers = ["項目"]
    months = []
    # Generate labels for 24 months (Current FY + Next FY)
    for y in range(start_year, start_year + years):
        for m in range(1, 13):
            months.append(f"{y}-{m:02d}")
    
    headers.extend(months)
    headers.append("合計") # Rightmost Total Column
    return headers, months

def main():
    syncer = SheetSyncer()
    
    # 1. Standard Items list (Master Index Template)
    # This acts as the visual template. Actual rows might vary if dynamic index is used,
    # but initially setting these helps.
    dashboard_items = [
        "売上高",
        "売上原価",
        "粗利益",
        "販売管理費",
        # SGA Placeholder (will be filled dynamically by logic, but good to have space)
        "  給料手当", "  法定福利費", "  外注費", "  荷造運賃", "  広告宣伝費", 
        "  交際費", "  会議費", "  旅費交通費", "  通信費", "  水道光熱費", 
        "  消耗品費", "  修繕費", "  支払手数料", "  地代家賃", "  保険料", 
        "  租税公課", "  減価償却費", "  採用教育費", "  雑費",
        "営業利益"
    ]
    
    header_row, month_labels = generate_headers(TARGET_FISCAL_YEAR, 2)
    
    # Template Data
    template_data = [header_row]
    for item in dashboard_items:
        row = [item] + [""] * (len(month_labels) + 1)
        template_data.append(row)
        
    # 2. Create Sheets
    # Main Dashboard (Total)
    syncer.create_worksheet("Dashboard", template_data, cols=len(header_row)+5)
    
    # Category Sheets
    for key, info in DEPT_CATEGORIES.items():
        sheet_name = info['sheet_name']
        logger.info(f"Initializing {sheet_name}...")
        syncer.create_worksheet(sheet_name, template_data, cols=len(header_row)+5)
        
    # Unallocated Sheet
    logger.info(f"Initializing {UNALLOCATED_SHEET_NAME}...")
    syncer.create_worksheet(UNALLOCATED_SHEET_NAME, template_data, cols=len(header_row)+5)
    
    # Add Drill-down header to Unallocated
    # (Just appending text at row 100 or so? Or logic will handle it)
    # Use Syncer to just init the PL part.
    
    logger.info("Initialization Complete.")

if __name__ == "__main__":
    main()
