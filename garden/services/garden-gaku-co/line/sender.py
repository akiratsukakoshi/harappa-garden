"""LINE 送信(reply / push)— gaku-co5.0 app/line/sender.py 相当(中立化)。

社内(core_team)専用デプロイ。access token / group ID は env から取り、
社外(gaku-co5.0)とは別建て(請求・失効を分離、ADR 2026-06-03 決定5)。

reply  : webhook の replyToken に対する 1 回限りの返信(無料・即時)。
push   : group へ能動送信(夜のレポート等。MVP では未使用だが用意しておく)。
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def _access_token() -> str:
    return os.environ.get("LINE_CORE_TEAM_ACCESS_TOKEN", "")


async def reply(reply_token: str, text: str) -> bool:
    """replyToken を使って LINE に返信する。"""
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json",
    }
    payload = {"replyToken": reply_token, "messages": [{"type": "text", "text": text}]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(LINE_REPLY_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        logger.error("LINE reply failed: %s %s", resp.status_code, resp.text)
        return False
    return True


async def push(to_line_id: str, text: str) -> bool:
    """group/user の LINE ID へ能動 push する。"""
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json",
    }
    payload = {"to": to_line_id, "messages": [{"type": "text", "text": text}]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(LINE_PUSH_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        logger.error("LINE push failed: %s %s", resp.status_code, resp.text)
        return False
    return True
