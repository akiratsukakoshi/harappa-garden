
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.freee_client import FreeeClient

def main():
    print("--- Freee Re-Authentication Helper ---")
    client = FreeeClient()
    
    # 1. Generate Auth URL
    auth_url = client.get_auth_url()
    print(f"\n1. Please visit the following URL to authorize the app:")
    print(f"   {auth_url}")
    print("\n2. After authorizing, you will be redirected to a blank page (urn:ietf:wg:oauth:2.0:oob).")
    print("   Please copy the authorization code displayed on that page.")
    
    # 2. Input Code
    auth_code = input("\nEnter the Authorization Code here: ").strip()
    
    if not auth_code:
        print("Error: No code provided.")
        return

    # 3. Exchange Token
    print("\n3. Exchanging code for tokens...")
    if client.get_initial_token(auth_code):
        print("Success! Tokens have been saved to modules/freee_tokens.json.")
    else:
        print("Failed to exchange token. Please check the code and try again.")

if __name__ == "__main__":
    main()
