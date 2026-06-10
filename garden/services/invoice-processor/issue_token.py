#!/usr/bin/env python3
"""issue_token.py — user OAuth token の発行(ローカルで 1 回だけ実行)。

VPS cron はブラウザ同意ができないため、token は WSL ローカルで発行して
VPS の secrets/ に scp する(calendar service の初回移植と同手順)。

手順:
  1. secrets/oauth_credentials.json を配置(desktop 型 OAuth クライアント。
     HMC / calendar service と同じものを流用してよい)
  2. .venv/bin/python issue_token.py
  3. 表示される URL をブラウザで開いてガクチョが同意 → 自動で secrets/user_token.json 生成
  4. VPS へ: scp secrets/user_token.json harappa:/home/vps-harappa/garden/services/invoice-processor/secrets/
     (配置後 chmod 600)

scope を変えたら(lib/user_google.py SCOPES)再実行して再発行すること。
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

from lib.user_google import SCOPES, TOKEN_PATH, OAUTH_CREDENTIALS_PATH


def main():
    if not os.path.exists(OAUTH_CREDENTIALS_PATH):
        raise SystemExit(
            f"OAuth クライアントがありません: {OAUTH_CREDENTIALS_PATH}\n"
            "→ desktop 型 oauth_credentials.json を secrets/ に配置してください。"
        )
    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CREDENTIALS_PATH, SCOPES)
    # WSL ではブラウザ自動起動(xdg-open)が固まるので URL 表示のみにする
    creds = flow.run_local_server(port=0, open_browser=False)
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    os.chmod(TOKEN_PATH, 0o600)
    print(f"token saved: {TOKEN_PATH}")
    print("→ VPS の secrets/ に scp + chmod 600 してください。")


if __name__ == "__main__":
    main()
