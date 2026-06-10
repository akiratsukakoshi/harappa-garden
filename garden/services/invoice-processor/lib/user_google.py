"""user_google — ガクチョ user OAuth の共通ローダー(invoice-processor 用)。

invoice_processor は Gmail(請求書メール取得 + ラベル操作)・Drive(請求書 PDF の
アップロード = ガクチョ所有にする)・Sheets(レビュータブ + 稼働時間シート読取)を
**user OAuth token 1 本**で賄う。

- SA(service account)を使わない理由: SA が My Drive 共有フォルダにアップロードした
  ファイルは SA 所有になり storage quota で失敗する(HMC でも fetch は gog = user 認証
  だった)。Gmail はそもそも SA 不可(gmail.com は domain-wide delegation 無し)。
- token は calendar service と同方式(JSON token + refresh_token、headless 安全)。
  InstalledAppFlow はここでは回さない(VPS cron で発火するため)。token 発行は
  issue_token.py(ローカルで 1 回、ガクチョのブラウザ同意)で行う。

ファイル配置(SCRIPT_DIR/secrets/、chmod 600・git 除外):
  - oauth_credentials.json … desktop 型 OAuth クライアント(HMC / calendar と共有可)
  - user_token.json        … 本 service の token(scope は SCOPES の 3 本)
"""
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from .utils import setup_logger

logger = setup_logger("UserGoogle")

# scope を変えたら user_token.json を再発行すること(issue_token.py)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

_SECRETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "secrets")
TOKEN_PATH = os.environ.get(
    "INVOICE_USER_TOKEN", os.path.join(_SECRETS_DIR, "user_token.json")
)
OAUTH_CREDENTIALS_PATH = os.environ.get(
    "INVOICE_OAUTH_CREDENTIALS", os.path.join(_SECRETS_DIR, "oauth_credentials.json")
)


def load_credentials():
    """user OAuth credentials を返す。token 不在/失効なら RuntimeError(cron で静かに死なない)。"""
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(
            f"user token が見つかりません: {TOKEN_PATH}\n"
            "→ ローカルで issue_token.py を実行して発行し、VPS の secrets/ に配置してください。"
        )
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # refresh で access_token が更新されるので書き戻す(次回起動を速く)。
            # 書き戻し失敗は致命ではない(次回も refresh すればよい)
            try:
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            except OSError as e:
                logger.warning(f"token の書き戻しに失敗(続行): {e}")
        else:
            raise RuntimeError(
                "user token が失効しています(refresh_token 無効)。"
                "issue_token.py で再発行 → secrets/ に再配置してください。"
            )
    return creds
