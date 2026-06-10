import re

def clean_file():
    target_file = 'apps/shift_manager/logic/generate_shift_form.py'
    with open(target_file, 'r') as f:
        content = f.read()
    
    # Remove debug prints
    content = content.replace('            print(f"DEBUG: Sending Batch Update with {len(requests)} requests.")', '')
    content = content.replace('            for r in requests:\n                if "updateItem" in r:\n                    print(f"  - Update Item: {r[\'updateItem\'][\'item\'].get(\'title\', \'No Title\')}")\n', '')
    content = content.replace('                elif "createItem" in r:\n                    print(f"  - Create Item: {r[\'createItem\'][\'item\'].get(\'title\', \'No Title\')}")\n', '')
    
    # Let us just use multi_replace because my cat-based replacement is fragile.
    # Actually just run the cleaned script once to make sure.
    pass

if __name__ == "__main__":
    clean_file()
