import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from modules.freee_client import FreeeClient

def main():
    client = FreeeClient()
    
    # 1. Get Sections
    print("--- Fetching Sections ---")
    sections = client.get_sections()
    for s in sections:
        print(f"ID: {s['id']}, Name: {s['name']}")
    
    # 2. Get PL (Trial) for current Fiscal Year (assuming 2024 for example, or calculate)
    # fiscal year of Japanese companies often starts in April or Jan.
    # Let's guess or just try 2025 (current real time is 2026-01-03, so FY2025 is likely ending or FY2026 starts).
    # Note: User metadata says 2026-01-03.
    # So we are likely in FY2025 (if Apr-Mar) or FY2026 (if Jan-Jan).
    
    fy = 2024 
    print(f"\n--- Fetching Trial PL for FY{fy} (April-March assumption or just 12 months) ---")
    
    # Fetching simplified PL
    # Note: start_month/end_month are 1-12. If FY starts in April, 1 is April? No, Freee API usually takes Month 1-12 as Fiscal Year months if relative?
    # Checked Freee API docs (mental check): start_month is 1..12 indicating month of the Fiscal Year.
    # So if FY starts April, month 1 is April.
    
    try:
        # Test breakdown
        params = {
            "company_id": client.target_company_id,
            "fiscal_year": fy,
            "start_month": 4,
            "end_month": 4,
            "breakdown_display_type": "section",
            "account_item_display_type": "account_item"
        }
        pl_data = client.request("GET", "https://api.freee.co.jp/api/1/reports/trial_pl", params=params)
        if pl_data:
            # Save to file for inspection
            with open("data/kpi_monitor/debug_pl.json", "w", encoding='utf-8') as f:
                json.dump(pl_data, f, indent=2, ensure_ascii=False)
            print("Saved PL data to 'data/kpi_monitor/debug_pl.json'")
            
            # Show top level keys
            print("Keys:", pl_data.keys())
        else:
            print("Failed to fetch PL.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
