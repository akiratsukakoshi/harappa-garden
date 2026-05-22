import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from apps.kpi_monitor.sheet_syncer import SheetSyncer
from apps.kpi_monitor.config import DEPT_CATEGORIES, UNALLOCATED_SHEET_NAME

def main():
    s = SheetSyncer()
    
    targets = ["Dashboard"]
    for info in DEPT_CATEGORIES.values():
        targets.append(info['sheet_name'])
    targets.append(UNALLOCATED_SHEET_NAME)
    
    for t in targets:
        try:
            ws = s.get_worksheet(t)
            if ws:
                print(f"Deleting {t}...")
                s.spreadsheet.del_worksheet(ws)
        except Exception as e:
            print(f"Error deleting {t}: {e}")

if __name__ == "__main__":
    main()
