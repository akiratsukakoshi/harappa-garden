"""Freee API client (HMC modules/freee_client/client.py から移植)

Garden 化のための差分:
- import パス: `from ..utils import` → `from .utils import`
- それ以外のロジックは HMC 版と完全に同一
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
        # token_file 未指定なら同 service の secrets/freee_tokens.json を使う
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

    def get_partners(self):
        url = f"https://api.freee.co.jp/api/1/partners"
        partners = []
        offset = 0
        limit = 3000

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
