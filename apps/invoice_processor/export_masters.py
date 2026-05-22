import os
import sys
import csv
import itertools
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.freee_client import FreeeClient
from modules.utils import setup_logger, ensure_directory

logger = setup_logger("MasterDataExporter")

def main():
    load_dotenv()
    
    output_dir = "data/invoice_processor"
    ensure_directory(output_dir)
    output_path = os.path.join(output_dir, "master_data.csv")
    
    client = FreeeClient()
    
    logger.info("Fetching Partners...")
    partners = client.get_partners()
    
    logger.info("Fetching Sections...")
    sections = client.get_sections()
    
    logger.info("Fetching Account Items...")
    account_items = client.get_account_items() # passing None gets all
    
    logger.info("Fetching Taxes...")
    taxes = client.get_taxes()
    
    # Sort lists for easier lookup
    partners.sort(key=lambda x: x['name'])
    sections.sort(key=lambda x: x['name'])
    if account_items:
        account_items.sort(key=lambda x: x['name'])
    else:
        account_items = []
        
    if taxes:
        # Sort taxes by code
        taxes.sort(key=lambda x: x['code'])
    else:
         taxes = []

    logger.info(f"Got {len(partners)} partners, {len(sections)} sections, {len(account_items)} account items, {len(taxes)} taxes.")

    # Prepare rows
    # We want columns: Partner, PartnerID, Section, SectionID, AccountItem, AccountItemID, TaxType
    # Since lists have different lengths, we use itertools.zip_longest
    
    headers = [
        "Partner", "PartnerID", 
        "Section", "SectionID", 
        "AccountItem", "AccountItemID", 
        "TaxType(ID:Name)"
    ]
    
    rows = []
    
    # Create iterators
    # Partners
    p_iter = ({'name': p['name'], 'id': p['id'], 'code': p.get('code')} for p in partners)
    # Sections
    s_iter = ({'name': s['name'], 'id': s['id']} for s in sections)
    # Account Items
    a_iter = ({'name': a['name'], 'id': a['id']} for a in account_items)
    # Taxes
    t_iter = ({'display': f"{t['code']}: {t['name']}"} for t in taxes)
    
    for p, s, a, t in itertools.zip_longest(p_iter, s_iter, a_iter, t_iter, fillvalue=None):
        row = {
            "Partner": p['name'] if p else "",
            "PartnerID": p['id'] if p else "", # Maybe include code? User asked for ID but often code is useful. Let's stick to ID as requested.
            "Section": s['name'] if s else "",
            "SectionID": s['id'] if s else "",
            "AccountItem": a['name'] if a else "",
            "AccountItemID": a['id'] if a else "",
            "TaxType(ID:Name)": t['display'] if t else ""
        }
        rows.append(row)
        
    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        
    logger.info(f"Exported master data to {output_path}")
    print(f"Master data exported to: {output_path}")

if __name__ == "__main__":
    main()
