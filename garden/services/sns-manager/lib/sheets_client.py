"""SNS KPI を Google スプレッドシートに記録(sns-manager 用、SA + gspread)。
HMC apps/sns_pilot/sheets_client.py 移植。spreadsheet_id は env(SNS_SHEET_ID)。
"""
import os

import gspread

from .utils import setup_logger
from .google_sa import load_sa_credentials

SHEETS = {
    "weekly_summary": "週次サマリー",
    "post_log": "投稿ログ",
    "reels_kpi": "Reels KPI",
}


class SNSSheetsClient:
    def __init__(self):
        self.logger = setup_logger("SNSSheetsClient")
        sid = os.getenv("SNS_SHEET_ID")
        if not sid:
            raise EnvironmentError("SNS_SHEET_ID が未設定です。")
        self.client = gspread.authorize(load_sa_credentials())
        self.spreadsheet = self.client.open_by_key(sid)
        self.logger.info(f"スプレッドシート接続: {self.spreadsheet.title}")

    def _get_or_create_sheet(self, name):
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            self.logger.info(f"シート '{name}' を新規作成します")
            return self.spreadsheet.add_worksheet(title=name, rows=500, cols=20)

    # ── 投稿ログ(週次) ──
    def ensure_post_log_header(self):
        ws = self._get_or_create_sheet(SHEETS["post_log"])
        if ws.row_count < 1 or not ws.row_values(1):
            ws.update("A1", [[
                "投稿日", "曜日", "形式", "目的", "投稿時間",
                "リーチ", "保存", "シェア", "コメント", "インプレッション",
                "フォロワー外リーチ率", "3秒視聴率", "permalink",
            ]])
        return ws

    def append_post_log(self, rows):
        ws = self.ensure_post_log_header()
        for r in rows:
            ws.append_row([
                r.get("date", ""), r.get("weekday", ""), r.get("format", ""),
                r.get("purpose", ""), r.get("post_time", ""), r.get("reach", ""),
                r.get("saved", ""), r.get("shares", ""), r.get("comments", ""),
                r.get("impressions", ""), r.get("non_follower_reach_rate", ""),
                r.get("3sec_retention", ""), r.get("permalink", ""),
            ])
        self.logger.info(f"投稿ログ {len(rows)} 件を記録しました")

    # ── 週次サマリー ──
    def ensure_weekly_summary_header(self):
        ws = self._get_or_create_sheet(SHEETS["weekly_summary"])
        if ws.row_count < 1 or not ws.row_values(1):
            ws.update("A1", [[
                "週", "フォロワー数", "前週比", "総リーチ",
                "フィードB リーチ", "フィードAC リーチ", "Reels リーチ",
                "Reels フォロワー外率", "Reels 3秒率",
                "最高パフォーマンス投稿", "AIコメント",
            ]])
        return ws

    def append_weekly_summary(self, data):
        ws = self.ensure_weekly_summary_header()
        ws.append_row([
            data.get("week", ""), data.get("followers", ""), data.get("followers_diff", ""),
            data.get("total_reach", ""), data.get("feed_b_reach", ""),
            data.get("feed_ac_reach", ""), data.get("reels_reach", ""),
            data.get("reels_non_follower_rate", ""), data.get("reels_3sec_rate", ""),
            data.get("top_post", ""), data.get("ai_comment", ""),
        ])
        self.logger.info(f"週次サマリー記録: {data.get('week')}")

    # ── Reels KPI ──
    def ensure_reels_kpi_header(self):
        ws = self._get_or_create_sheet(SHEETS["reels_kpi"])
        if ws.row_count < 1 or not ws.row_values(1):
            ws.update("A1", [[
                "投稿日", "リーチ", "再生数", "フォロワー外リーチ率",
                "3秒視聴率", "シェア数", "DM送信数", "permalink",
            ]])
        return ws

    def append_reels_kpi(self, data):
        ws = self.ensure_reels_kpi_header()
        ws.append_row([
            data.get("date", ""), data.get("reach", ""), data.get("plays", ""),
            data.get("non_follower_reach_rate", ""), data.get("3sec_retention", ""),
            data.get("shares", ""), data.get("dm_sends", ""), data.get("permalink", ""),
        ])
        self.logger.info(f"Reels KPI記録: {data.get('date')}")
