"""Stage2 応答生成 + tool-use ループ — ベンダー中立。

ADR 2026-06-03 vendor-neutral-interaction-layer 決定3・決定6 / gaku-co5.0 app/llm/agent.py 相当。

Stage1 ゲートが should=True を返した発言にだけ応答を生成する。
- 知識層(persona / CHARTER / memory)は system に load 済みのものを受け取る(context.py が用意)。
- 行動層は capabilities.tools_for(scope) で **構造的に** 絞った tool だけを Provider に渡す。
  → 財務/給与系 tool が staff の手に「存在しない」= 漏洩経路が prompt 頼みでなく構造で消える。
- `import anthropic` はしない。Provider.chat() と registry/capabilities だけを呼ぶ。

返り値: 応答テキスト or None(発言不要)。
"""
from __future__ import annotations

import logging

import capabilities
from brain.provider import Provider
from tools import registry

logger = logging.getLogger(__name__)

RESPOND_MODEL = "claude-haiku-4-5"
MAX_TOOL_ITERATIONS = 5


def _sanitize(text: str | None) -> str | None:
    """null/none/空 → None(発言しない)。Stage1 JSON の漏出も抑止。"""
    if not text:
        return None
    t = text.strip()
    if t.lower() in ("null", "none", ""):
        return None
    if t.startswith("{") and "should_respond" in t:
        logger.warning("Stage1 JSON leaked into Stage2 output, suppressing: %s", t[:80])
        return None
    return t


def generate_response(
    provider: Provider,
    *,
    scope: str,
    system: str,
    latest_message: str,
    history_text: str,
    sender: str,
    offer_tools: bool = True,
) -> str | None:
    """Stage2: 応答を生成する(同期)。

    Args:
      scope:   capability を引くための scope("line_core_team" 等)
      system:  context.py が組んだ system prompt(persona + CHARTER + memory)
      offer_tools: Stage1 dispatch が tools のときだけ True で渡すと安いが、
                   MVP は capability で絞った tool を常時渡し、使うかは LLM 判断でも可。
    """
    user_prompt = (
        f"【会話履歴】\n{history_text}\n\n"
        f"【最新メッセージ】\n送信者: {sender}\n内容: {latest_message}\n\n"
        "上記に応答してください。発言不要なら null とだけ出力してください。"
    )
    messages: list[dict] = [{"role": "user", "content": user_prompt}]

    specs = registry.specs_for(capabilities.tools_for(scope)) if offer_tools else []

    last_tool_result = ""
    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            resp = provider.chat(
                system=system,
                messages=messages,
                tools=specs or None,
                model=RESPOND_MODEL,
                max_tokens=2000,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("respond chat error: %s", e, exc_info=True)
            return f"⚠️ エラーが発生しました: {type(e).__name__}"

        if not resp.tool_calls:
            return _sanitize(resp.text)

        # tool-use: capability で再ガード(構造保証の二重化)してから実行
        allowed = capabilities.tools_for(scope)
        # assistant の tool_use ターンを「text + tool_calls」構造で積む。
        # text だけだと続く tool_result に対応する tool_use が無く Anthropic が 400 を返す。
        messages.append({
            "role": "assistant",
            "content": resp.text or "",
            "tool_calls": [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in resp.tool_calls
            ],
        })
        for tc in resp.tool_calls:
            if tc.name not in allowed:
                logger.warning("capability 外の tool 呼び出しを拒否: scope=%s tool=%s", scope, tc.name)
                result = f"(エラー: この scope では {tc.name} を使えません)"
            else:
                try:
                    result = registry.call(tc.name, tc.arguments)
                except Exception as e:  # noqa: BLE001
                    logger.error("tool %s failed: %s", tc.name, e)
                    result = f"(ツール実行エラー: {e})"
            last_tool_result = result
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    logger.warning("tool-use ループが上限 %d 回に達した", MAX_TOOL_ITERATIONS)
    detail = f" 最後の結果: {last_tool_result[:300]}" if last_tool_result else ""
    return f"⚠️ 処理が完了しませんでした。tool-use の確認回数が上限に達しました。{detail}"
