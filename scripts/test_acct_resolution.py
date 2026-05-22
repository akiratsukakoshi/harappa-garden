import os
from dotenv import load_dotenv
from modules.freee_client import FreeeClient
from apps.invoice_processor.rule_engine import RuleEngine

def main():
    load_dotenv()
    freee = FreeeClient()
    rule_engine = RuleEngine(freee)
    
    acct_name = "description"
    acct_id = rule_engine.resolve_account_item_id(acct_name)
    print(f"Account Item '{acct_name}' ID: {acct_id}")
    
    # Also list all account items to see if there's anything similar
    items = freee.get_account_items()
    print("\nAll Account Items:")
    for item in items:
        if "description" in item['name'].lower():
            print(f"Match: {item['name']} ({item['id']})")
            
if __name__ == "__main__":
    main()
