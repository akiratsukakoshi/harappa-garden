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
import base64
import importlib.util
import json
import logging
import os
import re
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse

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


# ── 承認待ち board の閲覧専用ダッシュボード(案1, S56)──────────────
# 同ドメイン(core.harappa.monster)に1経路追加。承認は Discord のまま=閲覧専用。
# Basic 認証。パスワードは env BOARD_DASH_PASSWORD か秘密ファイル(.board-dash-secret)。
BOARD_DASH_USER = os.environ.get("BOARD_DASH_USER", "gaku")
_BOARD_DASH_SECRET_FILE = Path(
    os.environ.get("BOARD_DASH_SECRET_FILE",
                   "/home/vps-harappa/garden/services/garden-gaku-co/.board-dash-secret")
)


def _board_dash_password() -> str:
    v = os.environ.get("BOARD_DASH_PASSWORD")
    if v:
        return v.strip()
    try:
        return _BOARD_DASH_SECRET_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


@app.get("/board")
async def board_dashboard(request: Request) -> Response:
    password = _board_dash_password()
    if not password:
        return Response(
            "board ダッシュボード未設定です(BOARD_DASH_PASSWORD / .board-dash-secret)。",
            status_code=503,
        )
    # (1) モバイル向け: ?key=<secret> の1タップアクセス(Basic 認証ダイアログ不要)
    key = request.query_params.get("key", "")
    if key and secrets.compare_digest(key, password):
        import board_dashboard as bd
        return HTMLResponse(bd.render_dashboard_html())

    # (2) Basic 認証(デスクトップ等)
    auth = request.headers.get("authorization", "")
    ok = False
    if auth.startswith("Basic "):
        try:
            user, _, pw = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
            ok = secrets.compare_digest(user, BOARD_DASH_USER) and secrets.compare_digest(pw, password)
        except Exception:
            ok = False
    if not ok:
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="HARAPPA Garden board"'},
        )
    import board_dashboard as bd
    return HTMLResponse(bd.render_dashboard_html())


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


# ── LINE userId 収集(S42 field_assistant メンション用)──────────────
# メンションは userId 必須 + 一括取得 API は認証済アカウント限定のため、
# 発話イベントから userId → 表示名を収集して field-assistant に渡す。
# 収集先は config/line_collected.json(userId → displayName)。
# 紐づけは field-assistant の `processor.py sync-line-users`(soil line_display_name と照合)。
COLLECT_PATH = os.environ.get(
    "FIELD_LINE_COLLECT_PATH",
    "/home/vps-harappa/garden/services/field-assistant/config/line_collected.json",
)


def _collect_line_user(source: dict, user_id: str) -> None:
    """発話者の userId + 表示名を記録(既知 userId はスキップ。失敗は無視)。"""
    if not user_id or user_id == "unknown":
        return
    try:
        try:
            with open(COLLECT_PATH, encoding="utf-8") as f:
                collected = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            collected = {}
        if user_id in collected:
            return
        import httpx

        token = os.environ.get("LINE_CORE_TEAM_ACCESS_TOKEN", "")
        if source.get("type") == "group":
            url = f"https://api.line.me/v2/bot/group/{source.get('groupId')}/member/{user_id}"
        else:
            url = f"https://api.line.me/v2/bot/profile/{user_id}"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if resp.status_code != 200:
            logger.warning("collect profile failed: %s %s", resp.status_code, resp.text)
            return
        collected[user_id] = resp.json().get("displayName", "")
        with open(COLLECT_PATH, "w", encoding="utf-8") as f:
            json.dump(collected, f, ensure_ascii=False, indent=1)
        logger.info("[collect] new LINE user: %s", collected[user_id])
    except Exception as e:  # noqa: BLE001 — 収集は本流を絶対に止めない
        logger.warning("collect_line_user failed: %s", e)


def _handle_text_sync(group_id: str, sender_id: str, text: str, direct: bool = False) -> str | None:
    """同期パイプライン(gate → respond)。executor で呼ぶ。

    direct=True(1:1 テスト)では gate を素通り(全メッセージが bot 宛のため)。
    """
    deterministic = _handle_deterministic_tool(text)
    if deterministic:
        context.record(group_id, sender_id, text)
        context.record(group_id, context.BOT_NAME, deterministic)
        return deterministic

    provider = get_provider()
    context.record(group_id, sender_id, text)
    history = context.history_text(group_id)

    if direct:
        # 1:1(ガクチョの恒久テスト環境、S42)は gate 素通り + tool あり。
        # S34 当時は echo しか無く「モデルが無駄に呼んで応答が空になる」ため切っていたが、
        # 実 tool(get_event_roster / get_weather)が入ったので解放。
        offer_tools = True
        logger.info("[gate] bypassed (direct 1:1 test, tools on)")
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


def _handle_deterministic_tool(text: str) -> str | None:
    """LLMに任せると落ちると困る短い確定コマンドを決定的に処理する。

    MVP対象: 「A案で運営会議を確定」「Bで確定、zoom発行」等。
    """
    # 確定は「会議名 + 候補 + 確定/決定」を基本形にする。
    # 「Aで確定」だけの省略形も、open meeting が1件だけなら processor 側で解決する。
    if "確定" not in text and "決定" not in text:
        return None
    has_meeting_name = "運営会議" in text
    m = re.search(r"\b([A-F])\b|([A-F])案", text, re.I)
    if not m:
        return None
    if not has_meeting_name and not re.search(r"\b[A-F]\s*で\s*(確定|決定)", text, re.I):
        return None
    candidate_id = (m.group(1) or m.group(2)).upper()
    try:
        mc = _load_meeting_coordinator()
        return mc.confirm_meeting(None, candidate_id, meeting_type="operations_monthly")
    except Exception as e:  # noqa: BLE001
        logger.error("deterministic meeting confirm failed: %s", e, exc_info=True)
        return f"会議確定に失敗しました({type(e).__name__}: {e})"


def _load_meeting_coordinator():
    mc_dir = os.environ.get(
        "MEETING_COORDINATOR_DIR", "/home/vps-harappa/garden/services/meeting-coordinator"
    )
    module_path = os.path.join(mc_dir, "processor.py")
    spec = importlib.util.spec_from_file_location("meeting_coordinator_processor_line", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load meeting coordinator from {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        # S42: メンション用 userId 収集(初見の発話者のみ。本流に影響しない)
        await asyncio.to_thread(_collect_line_user, event.get("source", {}), sender_id)

        reply = await asyncio.to_thread(_handle_text_sync, group_id, sender_id, text, direct)
        if reply and reply_token:
            await sender.reply(reply_token, reply)

    return Response(status_code=200, content="ok")
