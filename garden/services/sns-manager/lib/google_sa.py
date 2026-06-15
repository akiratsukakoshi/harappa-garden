"""Google サービスアカウント認証(sns-manager 用)。

Drive 読み書き(候補画像 DL + 使用済み画像を used/ へ move)+ Sheets 書き込み
(KPI ログ)を 1 つの SA で。expense/invoice と同じ harappa-drive-bot SA を流用
(ガクチョは Drive フォルダと SNS スプレッドシートを SA に共有するだけ。token
発行・再同意は不要)。

scope は full drive。新規ファイルを作らず既存の move/フォルダ作成のみなので
SA の storage quota 問題は起きない(invoice の upload とは異なる)。フォルダは
SA に **編集者** で共有しておくこと(閲覧者だと move/create が 403)。
"""
import os

from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_SA = os.path.join(_BASE_DIR, "secrets", "service_account.json")


def load_sa_credentials():
    path = os.getenv("GOOGLE_SA_FILE", _DEFAULT_SA)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"SA 鍵が見つかりません: {path}(GOOGLE_SA_FILE で指定 / expense・invoice の SA を流用)"
        )
    return Credentials.from_service_account_file(path, scopes=SCOPES)
