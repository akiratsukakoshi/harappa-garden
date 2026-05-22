import requests
import json
import urllib.parse
import os
import time
from dotenv import load_dotenv
from ..utils import setup_logger

load_dotenv()

class FreeeClient:
    def __init__(self, token_file="modules/freee_tokens.json"):
        self.client_id = os.getenv("FREEE_CLIENT_ID")
        self.client_secret = os.getenv("FREEE_CLIENT_SECRET")
        self.target_company_id = int(os.getenv("FREEE_TARGET_COMPANY_ID"))
        self.token_file = token_file
        self.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        self.logger = setup_logger("FreeeClient")
        self.tokens = self.load_tokens()

    def load_tokens(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return None
        return None

    def save_tokens(self, tokens):
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f, indent=4)
        self.tokens = tokens

    def get_auth_url(self):
        auth_url = "https://accounts.secure.freee.co.jp/public_api/authorize"
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code"
        }
        return f"{auth_url}?{urllib.parse.urlencode(params)}"

    def get_initial_token(self, auth_code):
        token_url = "https://accounts.secure.freee.co.jp/public_api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "redirect_uri": self.redirect_uri
        }
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            self.save_tokens(response.json())
            return True
        else:
            self.logger.error(f"Token exchange failed: {response.text}")
            return False

    def refresh_token(self):
        if not self.tokens or 'refresh_token' not in self.tokens:
            self.logger.error("No refresh token available.")
            return False

        token_url = "https://accounts.secure.freee.co.jp/public_api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.tokens['refresh_token'],
            "redirect_uri": self.redirect_uri
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            self.save_tokens(response.json())
            self.logger.info("Token refreshed successfully.")
            return True
        else:
            self.logger.error(f"Token refresh failed: {response.text}")
            return False

    def _get_headers(self):
        if not self.tokens:
            raise Exception("No tokens found. Please authenticate first.")
        return {
            "Authorization": f"Bearer {self.tokens['access_token']}",
            "X-Api-Version": "2020-06-15"
        }

    def post_deal(self, date, amount, description, type="income", account_item_id=None, section_id=None, partner_id=None, tax_code=None, due_date=None, payments=None):
        url = "https://api.freee.co.jp/api/1/deals"
        
        # If account_item_id is not provided, try to find "売上高" or default
        if not account_item_id:
            account_item_id = self.get_account_items("売上高")
            if not account_item_id:
                self.logger.error("Could not find account item '売上高'.")
                return None

        # Build Details
        detail = {
            "tax_code": tax_code if tax_code else 1, # Default to 1 (課税売上 10%) if not provided
            "account_item_id": account_item_id,
            "amount": amount,
            "description": description
        }
        if section_id:
            detail["section_id"] = section_id
        
        payload = {
            "issue_date": date,
            "type": type,
            "company_id": self.target_company_id,
            "details": [ detail ]
        }
        
        if due_date:
            payload["due_date"] = due_date
            
        if payments is not None:
             payload["payments"] = payments # Can be empty list [] for unpaid


        if partner_id:
            payload["partner_id"] = partner_id
        
        return self.request("POST", url, json_data=payload)

    def post_manual_journal(self, issue_date, details, adjustment=False):
        """
        Create a manual journal entry (振替伝票).
        details: list of dicts, each containing:
            - entry_side: "debit" or "credit"
            - account_item_id: int
            - tax_code: int
            - amount: int
            - description: str (optional)
            - section_id: int (optional)
            - partner_id: int (optional)
        """
        url = "https://api.freee.co.jp/api/1/manual_journals"
        
        payload = {
            "company_id": self.target_company_id,
            "issue_date": issue_date,
            "adjustment": adjustment,
            "details": details
        }
        
        return self.request("POST", url, json_data=payload)
    
    def get_account_items(self, name_hook=None):
        url = f"https://api.freee.co.jp/api/1/account_items?company_id={self.target_company_id}"
        response = self.request("GET", url)
        if response:
            items = response['account_items']
            if name_hook:
                for item in items:
                    if item['name'] == name_hook:
                        return item['id']
                return None
            return items
        return None

    def get_sections(self):
        url = f"https://api.freee.co.jp/api/1/sections?company_id={self.target_company_id}"
        response = self.request("GET", url)
        if response:
            return response['sections']
        return []

    def get_partners(self):
        url = f"https://api.freee.co.jp/api/1/partners"
        partners = []
        offset = 0
        limit = 3000 # Try fetching max allowed
        
        while True:
            params = {
                "company_id": self.target_company_id,
                "limit": limit,
                "offset": offset
            }
            response = self.request("GET", url, params=params)
            if response and 'partners' in response:
                batch = response['partners']
                partners.extend(batch)
                if len(batch) < limit:
                    break
                offset += limit
            else:
                break
                
        return partners

    def get_taxes(self):
        url = f"https://api.freee.co.jp/api/1/taxes/companies/{self.target_company_id}"
        response = self.request("GET", url)
        if response:
            return response['taxes']
        return []

    def get_trial_pl(self, fiscal_year, start_month=1, end_month=12, section_id=None, **kwargs):
        """
        Fetch Monthly Profit & Loss (PL).
        fiscal_year: int (e.g., 2024)
        """
        url = f"https://api.freee.co.jp/api/1/reports/trial_pl"
        
        params = {
            "company_id": self.target_company_id,
            "fiscal_year": fiscal_year,
            "start_month": start_month,
            "end_month": end_month,
            "step_size": "month",
            "account_item_display_type": "account_item", 

        }
        if section_id:
            params["section_id"] = section_id
        
        if kwargs:
            params.update(kwargs)

        return self.request("GET", url, params=params)

    def get_trial_bs(self, fiscal_year, start_month=1, end_month=12, section_id=None):
        """
        Fetch Monthly Balance Sheet (BS).
        """
        url = f"https://api.freee.co.jp/api/1/reports/trial_bs"
        params = {
            "company_id": self.target_company_id,
            "fiscal_year": fiscal_year,
            "start_month": start_month,
            "end_month": end_month,
            "step_size": "month",
            "account_item_display_type": "account_item"
        }
        if section_id:
            params["section_id"] = section_id
            
        return self.request("GET", url, params=params)

    def get_deals(self, start_issue_date=None, end_issue_date=None, params=None):
        """
        Fetch deals (transactions).
        """
        url = "https://api.freee.co.jp/api/1/deals"
        base_params = {
            "company_id": self.target_company_id,
            "limit": 100
        }
        if start_issue_date:
            base_params["start_issue_date"] = start_issue_date
        if end_issue_date:
            base_params["end_issue_date"] = end_issue_date

        if params:
            base_params.update(params)

        return self.request("GET", url, params=base_params)

    def get_deal(self, deal_id):
        """取引を1件取得"""
        url = f"https://api.freee.co.jp/api/1/deals/{deal_id}"
        params = {"company_id": self.target_company_id}
        return self.request("GET", url, params=params)

    def get_all_deals(self, start_issue_date=None, end_issue_date=None, **kwargs):
        """全取引をページネーション付きで取得"""
        all_deals = []
        offset = 0
        limit = 100
        while True:
            params = {
                "company_id": self.target_company_id,
                "limit": limit,
                "offset": offset,
            }
            if start_issue_date:
                params["start_issue_date"] = start_issue_date
            if end_issue_date:
                params["end_issue_date"] = end_issue_date
            params.update(kwargs)
            response = self.request("GET", "https://api.freee.co.jp/api/1/deals", params=params)
            if not response or "deals" not in response:
                break
            batch = response["deals"]
            all_deals.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
        return all_deals

    def update_deal_section(self, deal_id, detail_id, section_id):
        """取引明細の部門IDを更新する"""
        deal_resp = self.get_deal(deal_id)
        if not deal_resp or "deal" not in deal_resp:
            self.logger.error(f"取引 {deal_id} の取得に失敗しました")
            return None
        deal = deal_resp["deal"]

        updated_details = []
        for d in deal.get("details", []):
            detail = {
                "id": d["id"],
                "account_item_id": d["account_item_id"],
                "amount": d["amount"],
                "tax_code": d["tax_code"],
                "description": d.get("description", ""),
                "section_id": section_id if d["id"] == detail_id else d.get("section_id"),
            }
            updated_details.append(detail)

        url = f"https://api.freee.co.jp/api/1/deals/{deal_id}"
        payload = {
            "company_id": self.target_company_id,
            "issue_date": deal["issue_date"],
            "type": deal["type"],
            "details": updated_details,
        }
        if deal.get("partner_id"):
            payload["partner_id"] = deal["partner_id"]
        if deal.get("due_date"):
            payload["due_date"] = deal["due_date"]
        return self.request("PUT", url, json_data=payload)

    def get_walletables(self):
        """口座・カード等の一覧と残高を取得"""
        url = "https://api.freee.co.jp/api/1/walletables"
        params = {"company_id": self.target_company_id}
        response = self.request("GET", url, params=params)
        if response:
            return response.get("walletables", [])
        return []

    def get_walletable_transactions(self, walletable_type, walletable_id,
                                    start_date=None, end_date=None, limit=100):
        """特定口座のトランザクション一覧を取得"""
        url = "https://api.freee.co.jp/api/1/walletable_txns"
        params = {
            "company_id": self.target_company_id,
            "walletable_type": walletable_type,
            "walletable_id": walletable_id,
            "limit": limit,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        response = self.request("GET", url, params=params)
        if response:
            return response.get("walletable_txns", [])
        return []

    def request(self, method, url, params=None, json_data=None):
        if not self.tokens:
            self.logger.error("Not authenticated.")
            return None

        def _do(hdrs):
            if method == "GET":
                return requests.get(url, headers=hdrs, params=params)
            elif method == "POST":
                return requests.post(url, headers=hdrs, json=json_data)
            elif method == "PUT":
                return requests.put(url, headers=hdrs, json=json_data)
            elif method == "PATCH":
                return requests.patch(url, headers=hdrs, json=json_data)
            elif method == "DELETE":
                return requests.delete(url, headers=hdrs)
            else:
                raise ValueError(f"Unsupported method: {method}")

        response = _do(self._get_headers())

        if response.status_code == 401:
            self.logger.info("Token expired, refreshing...")
            if self.refresh_token():
                response = _do(self._get_headers())
            else:
                return None

        if response.status_code not in [200, 201]:
            self.logger.error(f"API Error ({response.status_code}): {response.text}")
            return None

        return response.json()
