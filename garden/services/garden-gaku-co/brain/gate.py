"""Stage1 ゲート(should_respond)— ベンダー中立。

ADR 2026-06-03 vendor-neutral-interaction-layer 決定6 / gaku-co5.0 app/llm/switch.py 相当。

多人数チャネル(core_team / staff)では、大半のメッセージは Bot 宛てではない。
「いつ喋り、いつ黙るか」を毎メッセージ安く高速に判定するのがこの層の役割。
判定は小型モデル(Haiku 既定)で ~100token。`import anthropic` はせず、Provider.chat()
だけを呼ぶ(LLM 差し替えはアダプタ 1 枚で済む)。

返り値: GateResult(should, reason, dispatch)
  - should=False なら respond を呼ばない(コスト最適化 + 沈黙の規律)
  - dispatch.type は "direct"(通常会話)/ "tools"(ツール操作を要する)
    ※ skill dispatch は業務ツール整備フェーズ(次)で追加。MVP は direct/tools のみ。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from brain.provider import Provider

logger = logging.getLogger(__name__)

GATE_MODEL = "claude-haiku-4-5"  # ゲートは小型モデル固定(安く速く)


@dataclass
class GateResult:
    should: bool
    reason: str = ""
    dispatch: dict[str, Any] = field(default_factory=lambda: {"type": "direct"})


def _system_prompt(bot_name: str) -> str:
    return f"""あなたはメッセージ分類 AI です。
与えられた会話履歴と最新メッセージを分析し、
「最新メッセージが Bot に向けられた発言かどうか」と「どの処理経路が適切か」を判定してください。

判定基準(should_respond):
※ デフォルトは false。以下のいずれかに明確に該当する場合のみ true とする。
- 「Bot の名前」({bot_name})への直接メンション・呼びかけがある → true
- この Bot が直前に発言しており、それへの直接の返事である → true
- 会話履歴を見て Bot との対話が継続中であり、最新メッセージがその流れへの返答・続きと判断できる → true
  (例: 直前の Bot 発言への質問への回答、会話の続き、「ありがとう」「なるほど」などの反応)
  (除外: 他の参加者への発言、全員向けアナウンス、明らかに別のトピック)
- 上記以外はすべて false(他ユーザー・グループ全体・雑談・独り言を含む)

dispatch の選択基準(should_respond=true のときのみ):
- URL を読む・ウェブ検索・「調べて」「できる?」などツール操作を要する依頼 → {{"type": "tools"}}
- 上記以外の通常会話・質問・雑談 → {{"type": "direct"}}

必ず以下の JSON のみで出力してください。説明文は不要です:
- true かつ tools: {{"should_respond": true, "reason": "一言", "dispatch": {{"type": "tools"}}}}
- true かつ direct: {{"should_respond": true, "reason": "一言", "dispatch": {{"type": "direct"}}}}
- false: {{"should_respond": false, "reason": "一言"}}"""


def should_respond(
    provider: Provider,
    *,
    latest_message: str,
    history_text: str,
    bot_name: str = "ガクコ",
) -> GateResult:
    """Stage1: この発言に Bot が応答すべきか + 経路を判定する(同期)。

    例外は全て握りつぶして「黙る(should=False)」に倒す = 安全側。
    """
    user_content = (
        f"Bot の名前: {bot_name}\n\n"
        f"【会話履歴】\n{history_text}\n\n"
        f"【最新メッセージ】\n{latest_message}\n\n"
        "このメッセージは Bot への語りかけですか?"
    )
    try:
        resp = provider.chat(
            system=_system_prompt(bot_name),
            messages=[{"role": "user", "content": user_content}],
            model=GATE_MODEL,
            max_tokens=100,
        )
        raw = (resp.text or "").strip()
        start, end = raw.find("{"), raw.rfind("}") + 1
        result = json.loads(raw[start:end])
    except Exception as e:  # noqa: BLE001 — 判定失敗は黙る(安全側)
        logger.warning("gate parse/chat failed: %s", e)
        return GateResult(should=False, reason=f"error: {e}")

    should_raw = result.get("should_respond", False)
    # LLM が "false" を文字列で返す事故対策(bool("false") は True になる)
    should = should_raw.lower() == "true" if isinstance(should_raw, str) else bool(should_raw)
    dispatch = result.get("dispatch") or {"type": "direct"}
    return GateResult(should=should, reason=result.get("reason", ""), dispatch=dispatch)
