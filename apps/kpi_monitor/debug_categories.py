import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from modules.freee_client import FreeeClient
from apps.kpi_monitor.config import TARGET_FISCAL_YEAR

def main():
    client = FreeeClient()
    resp = client.get_trial_pl(TARGET_FISCAL_YEAR, start_month=4, end_month=6) # Check a few months
    if not resp or 'trial_pl' not in resp:
        print("No data")
        return

    balances = resp['trial_pl']['balances']
    seen_cats = set()
    print("--- Categories Found ---")
    for item in balances:
        c = item.get('account_category_name')
        n = item.get('account_item_name')
        if c not in seen_cats:
            print(f"Category: '{c}' (Example Item: {n})")
            seen_cats.add(c)
            
if __name__ == "__main__":
    main()
