"""Freee API client (HMC modules/freee_client/client.py フル版から移植)

Garden 化のための差分(shift-manager の移植方針に合わせる):
- import パス: `from ..utils import` → `from .utils import`
- token_file 未指定なら同 service の secrets/freee_tokens.json を使う
- それ以外のロジックは HMC 版と完全に同一(post_deal / get_account_items /
  get_sections / get_taxes / get_partners 等をフル移植)
"""

import requests
import json
import urllib.parse
import os
import time
from dotenv import load_dotenv
from .utils import setup_logger

load_dotenv()


class FreeeClient:
    def __init__(self, token_file=None):
        self.client_id = os.getenv("FREEE_CLIENT_ID")
        self.client_secret = os.getenv("FREEE_CLIENT_SECRET")
        self.target_company_id = int(os.getenv("FREEE_TARGET_COMPANY_ID"))
        # token_file の決定順:
        #   1. 引数 token_file
        #   2. env FREEE_TOKEN_FILE(他 Garden service と Freee token を共有するため。
        #      Freee は refresh token をローテートするので、同一 OAuth client を使う
        #      service 間では物理ファイルを 1 つに統一する必要がある)
        #   3. 同 service の secrets/freee_tokens.json
        if token_file is None:
            token_file = os.getenv("FREEE_TOKEN_FILE")
        if token_file is None:
            here = os.path.dirname(os.path.abspath(__file__))
            token_file = os.path.join(here, "..", "secrets", "freee_tokens.json")
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
