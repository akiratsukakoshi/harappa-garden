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

# テスト用の 1:1 許可リスト(エアギャップの限定的な例外)。
# LINE_TEST_USER_IDS にカンマ区切りで userId を入れると、その個人の 1:1 のみ通す。
# 既定は空 = 全ての 1:1 を無視(エアギャップ維持)。本番グループ投入後は空に戻す運用。
# 1:1 は「全メッセージが bot 宛」なので gate を素通りさせる(意味的に正しい)。
TEST_USER_IDS = {u for u in os.environ.get("LINE_TEST_USER_IDS", "").split(",") if u.strip()}

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
        "test_user_ids": len(TEST_USER_IDS),
        "tools": sorted(capabilities.tools_for(SCOPE)),
    }


def _resolve_source(source: dict) -> tuple[str | None, bool]:
    """webhook の source を (context_key, is_direct) へ。

    - core_team グループ → (group_id, False)  ※ group なので gate を通す
    - テスト許可 userId の 1:1 → ("test_dm:{userId}", True)  ※ 1:1 なので gate 素通り
    - それ以外(個人・未知グループ・room) → (None, False)  = 無視(エアギャップ)
    """
    if source.get("type") == "group" and source.get("groupId") == CORE_TEAM_GROUP_ID and CORE_TEAM_GROUP_ID:
        return CORE_TEAM_GROUP_ID, False
    if source.get("type") == "user" and source.get("userId") in TEST_USER_IDS:
        return f"test_dm:{source.get('userId')}", True
    return None, False  # 個人・未知グループ・room は無視(エアギャップ)


def _handle_text_sync(group_id: str, sender_id: str, text: str, direct: bool = False) -> str | None:
    """同期パイプライン(gate → respond)。executor で呼ぶ。

    direct=True(1:1 テスト)では gate を素通り(全メッセージが bot 宛のため)。
    """
    provider = get_provider()
    context.record(group_id, sender_id, text)
    history = context.history_text(group_id)

    if direct:
        # 1:1 テストは純粋な会話を見たいので placeholder の echo は渡さない。
        # (echo は noop の配線確認用。渡すとモデルが無駄に呼んで最終テキストが空になり
        #  reply が飛ばないことがある。tool-use は smoke で検証済、実ツール実装後に再開。)
        offer_tools = False
        logger.info("[gate] bypassed (direct 1:1 test, tools off)")
    else:
        g = gate.should_respond(
            provider, latest_message=text, history_text=history, bot_name=context.BOT_NAME
        )
        logger.info("[gate] should=%s reason=%s dispatch=%s", g.should, g.reason, g.dispatch)
        if not g.should:
            return None
        offer_tools = (g.dispatch.get("type") == "tools")

    reply = respond.generate_response(
        provider,
        scope=SCOPE,
        system=context.build_system(),
        latest_message=text,
        history_text=history,
        sender=sender_id,
        offer_tools=offer_tools,
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
        group_id, direct = _resolve_source(event.get("source", {}))
        if group_id is None:
            logger.info("[skip] non core_team source: %s", event.get("source", {}))
            continue
        sender_id = event.get("source", {}).get("userId", "unknown")
        text = msg.get("text", "")
        reply_token = event.get("replyToken")

        reply = await asyncio.to_thread(_handle_text_sync, group_id, sender_id, text, direct)
        if reply and reply_token:
            await sender.reply(reply_token, reply)

    return Response(status_code=200, content="ok")
