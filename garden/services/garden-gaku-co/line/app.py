"""社内(core_team)LINE Webhook サーバ — FastAPI。

ADR 2026-06-03 vendor-neutral-interaction-layer 実装順序「2」。
gaku-co5.0 app/line/webhook.py + app/main.py を、中立基盤(brain/tools/capabilities)
の上に再構成したもの。`import anthropic` はこのファイルにも無い(Provider 経由)。

配線:
  LINE webhook → 署名検証 → group が core_team か検査(エアギャップ)
    → 短期履歴 record → Stage1 gate(should?)→ should なら Stage2 respond
    → reply → RAW logging(memory_logger、scope=line_core_team)

**エアギャップ規律(ADR 決定5)**:
  このサーバは設定された CORE_TEAM グループ ID **のみ** 処理する。
  社外(デジタル原っぱ / AIBOU)や未知の source は構造的に無視 = スタッフ情報の漏洩経路を作らない。
  社外は別デプロイ(gaku-co5.0)が別 LINE 公式アカウントで受ける。

起動:
  cd garden/services/garden-gaku-co
  uvicorn line.app:app --host 127.0.0.1 --port 8011
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import FastAPI, Request, Response

import capabilities  # noqa: F401  (registry の echo 登録副作用 + scope 検証で使用)
import memory_logger
from brain import gate, respond
from brain.provider import AnthropicProvider, Provider
from line import context, sender, signature
from tools import registry  # noqa: F401  (@register 副作用で echo を登録)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("garden-gaku-co.line")

app = FastAPI(title="garden-gaku-co core_team LINE")

SCOPE = "line_core_team"

# このサーバが応答する唯一の LINE source(エアギャップ)。
# group ID は env、個人 1:1(source.type == user)は既定で無効(社内は group 運用)。
CORE_TEAM_GROUP_ID = os.environ.get("LINE_CORE_TEAM_GROUP_ID", "")

_provider: Provider | None = None


def get_provider() -> Provider:
    global _provider
    if _provider is None:
        _provider = AnthropicProvider(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _provider


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "scope": SCOPE,
        "core_team_group_configured": bool(CORE_TEAM_GROUP_ID),
        "tools": sorted(capabilities.tools_for(SCOPE)),
    }


def _source_group_id(source: dict) -> str | None:
    """webhook の source を内部 group key へ。core_team グループのみ許可、他は None。"""
    if source.get("type") == "group" and source.get("groupId") == CORE_TEAM_GROUP_ID:
        return CORE_TEAM_GROUP_ID
    return None  # 個人・未知グループ・room は無視(エアギャップ)


def _handle_text_sync(group_id: str, sender_id: str, text: str) -> str | None:
    """同期パイプライン(gate → respond)。executor で呼ぶ。"""
    provider = get_provider()
    context.record(group_id, sender_id, text)
    history = context.history_text(group_id)

    g = gate.should_respond(
        provider, latest_message=text, history_text=history, bot_name=context.BOT_NAME
    )
    logger.info("[gate] should=%s reason=%s dispatch=%s", g.should, g.reason, g.dispatch)
    if not g.should:
        return None

    reply = respond.generate_response(
        provider,
        scope=SCOPE,
        system=context.build_system(),
        latest_message=text,
        history_text=history,
        sender=sender_id,
        offer_tools=(g.dispatch.get("type") == "tools"),
    )
    if reply:
        context.record(group_id, context.BOT_NAME, reply)
        try:
            memory_logger.append_turn(
                SCOPE, user_text=f"{sender_id}: {text}", bot_reply=reply,
                user_label="staff", bot_label="ガクコ",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("memory_logger.append_turn failed: %s", e)
    return reply


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    body = await request.body()
    sig = request.headers.get("X-Line-Signature", "")
    secret = os.environ.get("LINE_CORE_TEAM_CHANNEL_SECRET", "")
    if not signature.verify(body, sig, secret):
        # Verify ボタンは署名付き空イベントを送る。secret 一致なら 200 を返したいので
        # 検証失敗のみ 403。
        return Response(status_code=403, content="invalid signature")

    payload = json.loads(body or b"{}")
    for event in payload.get("events", []):
        if event.get("type") != "message":
            continue
        msg = event.get("message", {})
        if msg.get("type") != "text":
            continue  # MVP はテキストのみ(画像/ファイルは次フェーズ)
        group_id = _source_group_id(event.get("source", {}))
        if group_id is None:
            logger.info("[skip] non core_team source: %s", event.get("source", {}))
            continue
        sender_id = event.get("source", {}).get("userId", "unknown")
        text = msg.get("text", "")
        reply_token = event.get("replyToken")

        reply = await asyncio.to_thread(_handle_text_sync, group_id, sender_id, text)
        if reply and reply_token:
            await sender.reply(reply_token, reply)

    return Response(status_code=200, content="ok")
