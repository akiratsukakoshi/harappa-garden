import requests
import json
import urllib.parse
import os

# ==========================================
# ↓.envから取得します
from dotenv import load_dotenv
load_dotenv()

CLIENT_ID = os.getenv("FREEE_CLIENT_ID")
CLIENT_SECRET = os.getenv("FREEE_CLIENT_SECRET")
# ==========================================

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: FREEE_CLIENT_ID or FREEE_CLIENT_SECRET not found in .env")
    exit(1)

# ↓ターゲットとする事業所ID (HARAPPA株式会社)
TARGET_COMPANY_ID = 723485
# ==========================================

REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
TOKEN_FILE = "modules/freee_tokens.json"

def get_access_token():
    # 認証URL生成
    auth_url = "https://accounts.secure.freee.co.jp/public_api/authorize"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code"
    }
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    
    print("\n=== 再認証ステップ ===")
    print("1. ブラウザでFreeeからログアウトしているか確認してください。")
    print("2. 以下のURLを開き、「HARAPPA株式会社」のアカウントでログイン・許可してください。")
    print("-" * 20)
    print(url)
    print("-" * 20)
    
    auth_code = input("認証コードを入力: ").strip()

    # トークン取得
    token_url = "https://accounts.secure.freee.co.jp/public_api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code != 200:
        print("エラー:", response.text)
        return None
    
    # トークン保存（modulesフォルダがない場合はエラーになるので注意）
    if not os.path.exists("modules"):
        os.makedirs("modules")
        
    with open(TOKEN_FILE, 'w') as f:
        json.dump(response.json(), f, indent=4)
        
    return response.json()

def check_target_company(access_token):
    api_url = "https://api.freee.co.jp/api/1/companies"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Api-Version": "2020-06-15"
    }
    
    print("\n=== 事業所スキャン中 ===")
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        companies = response.json()['companies']
        target_found = False
        
        for company in companies:
            print(f"- 検出: {company['display_name']} (ID: {company['id']})")
            if company['id'] == TARGET_COMPANY_ID:
                target_found = True
                print("\n" + "="*40)
                print(f"★ターゲット捕捉成功！: {company['display_name']}")
                print(f"ID: {company['id']} への接続を確認しました。")
                print("="*40 + "\n")
        
        if not target_found:
            print(f"\n警告: ID {TARGET_COMPANY_ID} が見つかりませんでした。")
            print("ログインしているアカウントが、HARAPPA株式会社に招待されていない可能性があります。")
    else:
        print("データ取得失敗:", response.text)

if __name__ == "__main__":
    tokens = get_access_token()
    if tokens:
        check_target_company(tokens['access_token'])