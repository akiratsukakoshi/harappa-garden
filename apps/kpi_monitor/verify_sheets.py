import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from apps.kpi_monitor.sheet_syncer import SheetSyncer

try:
    s = SheetSyncer()
    print(f"Success! Connected to: {s.spreadsheet.title}")
    print("Available Worksheets:")
    for w in s.spreadsheet.worksheets():
        print(f" - {w.title}")
    
    ws = s.get_worksheet("Dashboard")
    if ws:
        print("Found 'Dashboard' worksheet.")
    else:
        print("Could not find 'Dashboard' worksheet.")
except Exception as e:
    print(f"Connection failed: {e}")
