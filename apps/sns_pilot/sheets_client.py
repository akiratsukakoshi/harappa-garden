"""
SNS KPI を Google スプレッドシートに記録する。
振り返りシート: https://docs.google.com/spreadsheets/d/1NWU7FYGsMol18aHkrvpVzEB7dxIk2YvyTlb4eUD-Ycg
"""
import json
import gspread
from google.oauth2.service_account import Credentials
from modules.utils import setup_logger

logger = setup_logger("SNSSheetsClient")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_PATH = "credentials.json"

with open("apps/sns_pilot/config.json") as f:
    _CONFIG = json.load(f)

SPREADSHEET_ID = _CONFIG["spreadsheet_id"]
SHEETS = _CONFIG["sheets"]


class SNSSheetsClient:
    def __init__(self):
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
        logger.info(f"スプレッドシート接続: {self.spreadsheet.title}")

    def _get_or_create_sheet(self, name: str) -> gspread.Worksheet:
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            logger.info(f"シート '{name}' を新規作成します")
            return self.spreadsheet.add_worksheet(title=name, rows=500, cols=20)

    # ──────────────────────────────────────────────
    # 投稿ログ（週次）
    # ──────────────────────────────────────────────

    def ensure_post_log_header(self):
        ws = self._get_or_create_sheet(SHEETS["post_log"])
        if ws.row_count < 1 or not ws.row_values(1):
            ws.update("A1", [[
                "投稿日", "曜日", "形式", "目的", "投稿時間",
                "リーチ", "保存", "シェア", "コメント", "インプレッション",
                "フォロワー外リーチ率", "3秒視聴率", "permalink"
            ]])
        return ws

    def append_post_log(self, rows: list[dict]):
        """
        rows: [
          { "date": "2026-04-22", "weekday": "火", "format": "フィード", "purpose": "B",
            "post_time": "20:00", "reach": 1200, "saved": 45, "shares": 12,
            "comments": 8, "impressions": 1500,
            "non_follower_reach_rate": 0.72, "3sec_retention": None,
            "permalink": "https://..." }
        ]
        """
        ws = self.ensure_post_log_header()
        for r in rows:
            ws.append_row([
                r.get("date", ""),
                r.get("weekday", ""),
                r.get("format", ""),
                r.get("purpose", ""),
                r.get("post_time", ""),
                r.get("reach", ""),
                r.get("saved", ""),
                r.get("shares", ""),
                r.get("comments", ""),
                r.get("impressions", ""),
                r.get("non_follower_reach_rate", ""),
                r.get("3sec_retention", ""),
                r.get("permalink", ""),
            ])
        logger.info(f"投稿ログ {len(rows)} 件を記録しました")

    # ──────────────────────────────────────────────
    # 週次サマリー
    # ──────────────────────────────────────────────

    def ensure_weekly_summary_header(self):
        ws = self._get_or_create_sheet(SHEETS["weekly_summary"])
        if ws.row_count < 1 or not ws.row_values(1):
            ws.update("A1", [[
                "週", "フォロワー数", "前週比", "総リーチ",
                "フィードB リーチ", "フィードAC リーチ", "Reels リーチ",
                "Reels フォロワー外率", "Reels 3秒率",
                "最高パフォーマンス投稿", "AIコメント"
            ]])
        return ws

    def append_weekly_summary(self, data: dict):
        """
        data: {
          "week": "2026-04-21",
          "followers": 1500, "followers_diff": 12,
          "total_reach": 3800,
          "feed_b_reach": 1200, "feed_ac_reach": 1100,
          "reels_reach": 1500,
          "reels_non_follower_rate": 0.72, "reels_3sec_rate": 0.55,
          "top_post": "04/22 フィードB (保存45件)",
          "ai_comment": "C目的の保存率が高め→来週も哲学系を入れると良さそう"
        }
        """
        ws = self.ensure_weekly_summary_header()
        ws.append_row([
            data.get("week", ""),
            data.get("followers", ""),
            data.get("followers_diff", ""),
            data.get("total_reach", ""),
            data.get("feed_b_reach", ""),
            data.get("feed_ac_reach", ""),
            data.get("reels_reach", ""),
            data.get("reels_non_follower_rate", ""),
            data.get("reels_3sec_rate", ""),
            data.get("top_post", ""),
            data.get("ai_comment", ""),
        ])
        logger.info(f"週次サマリー記録: {data.get('week')}")

    # ──────────────────────────────────────────────
    # Reels KPI トラッキング
    # ──────────────────────────────────────────────

    def ensure_reels_kpi_header(self):
        ws = self._get_or_create_sheet(SHEETS["reels_kpi"])
        if ws.row_count < 1 or not ws.row_values(1):
            ws.update("A1", [[
                "投稿日", "リーチ", "再生数", "フォロワー外リーチ率",
                "3秒視聴率", "シェア数", "DM送信数", "permalink"
            ]])
        return ws

    def append_reels_kpi(self, data: dict):
        ws = self.ensure_reels_kpi_header()
        ws.append_row([
            data.get("date", ""),
            data.get("reach", ""),
            data.get("plays", ""),
            data.get("non_follower_reach_rate", ""),
            data.get("3sec_retention", ""),
            data.get("shares", ""),
            data.get("dm_sends", ""),
            data.get("permalink", ""),
        ])
        logger.info(f"Reels KPI記録: {data.get('date')}")
