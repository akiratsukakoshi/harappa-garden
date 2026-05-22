import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from modules.freee_client import FreeeClient

client = FreeeClient()
try:
    taxes = client.get_taxes()
    print("Available Taxes:")
    if taxes:
        print(f"First item keys: {taxes[0].keys()}")
        print(f"First item sample: {taxes[0]}")
    for t in taxes:
        # projected adjustment
        code = t.get('code')
        name = t.get('name')
        print(f"Code: {code}, Name: {name}")
except Exception as e:
    print(f"Error: {e}")
