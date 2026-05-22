"""人事労務freee APIクライアント

会計freeeとは別アプリ・別OAuth・別エンドポイント。
- API base: https://api.freee.co.jp/hr/api/v1
- Token endpoint: https://accounts.secure.freee.co.jp/public_api/token
"""

import os
import json
import time
import logging
import requests
from typing import Optional


class FreeeHRClient:
    API_BASE = "https://api.freee.co.jp/hr/api/v1"
    TOKEN_URL = "https://accounts.secure.freee.co.jp/public_api/token"

    def __init__(self, token_file: str = "modules/freee_hr_client/token.json"):
        self.logger = logging.getLogger("FreeeHRClient")
        self.client_id = os.getenv("FREEE_HR_CLIENT_ID")
        self.client_secret = os.getenv("FREEE_HR_CLIENT_SECRET")
        self.company_id = int(os.getenv("FREEE_HR_COMPANY_ID", "0")) or None
        self.token_file = token_file
        self.tokens = self._load_tokens()

    # ── トークン管理 ──────────────────────────────────────────

    def _load_tokens(self) -> Optional[dict]:
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                return json.load(f)
        return None

    def _save_tokens(self, tokens: dict):
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        tokens["issued_at"] = int(time.time())
        with open(self.token_file, "w") as f:
            json.dump(tokens, f, indent=2)
        self.tokens = tokens

    def _refresh(self) -> bool:
        if not self.tokens or "refresh_token" not in self.tokens:
            self.logger.error("Refresh token not found.")
            return False
        resp = requests.post(
            self.TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.tokens["refresh_token"],
            },
        )
        if resp.status_code == 200:
            self._save_tokens(resp.json())
            self.logger.info("HR Token refreshed.")
            return True
        self.logger.error(f"HR Refresh failed: {resp.text}")
        return False

    def _headers(self) -> dict:
        if not self.tokens:
            raise RuntimeError("No HR tokens. Run OAuth flow first.")
        return {"Authorization": f'Bearer {self.tokens["access_token"]}'}

    def _request(self, method: str, path: str, params: dict = None, json_body: dict = None) -> Optional[dict]:
        """共通リクエスト。401時は自動でトークンリフレッシュ→再試行。"""
        url = f"{self.API_BASE}{path}"
        for attempt in range(2):
            resp = requests.request(method, url, headers=self._headers(),
                                    params=params, json=json_body)
            if resp.status_code == 401 and attempt == 0:
                if not self._refresh():
                    return None
                continue
            if 200 <= resp.status_code < 300:
                if resp.text:
                    return resp.json()
                return {}
            self.logger.error(f"HR API {method} {path} failed [{resp.status_code}]: {resp.text}")
            return None
        return None

    # ── 高レベルAPI ───────────────────────────────────────────

    def get_companies(self) -> Optional[list]:
        """事業所リストを取得"""
        result = self._request("GET", "/companies")
        return result.get("companies", []) if result else None

    def get_employees(self, year: int, month: int, limit: int = 100) -> Optional[list]:
        """指定年月の従業員リストを取得"""
        if not self.company_id:
            raise RuntimeError("FREEE_HR_COMPANY_ID not set in .env")
        result = self._request("GET", "/employees",
                               params={"company_id": self.company_id,
                                       "year": year, "month": month, "limit": limit})
        return result.get("employees", []) if result else None

    def get_work_record(self, employee_id: int, date: str) -> Optional[dict]:
        """指定従業員・日付の勤怠を取得 (date format: YYYY-MM-DD)"""
        return self._request("GET", f"/employees/{employee_id}/work_records/{date}",
                             params={"company_id": self.company_id})

    def put_work_record(self, employee_id: int, date: str, body: dict) -> Optional[dict]:
        """勤怠の更新 (PUT)
        body例:
        {
            "company_id": <int>,
            "break_records": [{"clock_in_at": "...", "clock_out_at": "..."}],
            "clock_in_at": "2026-05-15T09:00:00+09:00",
            "clock_out_at": "2026-05-15T14:45:00+09:00",
            "day_pattern": "normal_work",
            "use_default_work_pattern": false,
            "not_auto_calc_work_time": false,
        }
        """
        if not body.get("company_id"):
            body["company_id"] = self.company_id
        return self._request("PUT", f"/employees/{employee_id}/work_records/{date}",
                             json_body=body)
