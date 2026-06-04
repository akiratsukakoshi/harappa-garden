"""社内 LINE 対話パイプラインの smoke test — 実 API/LINE 不要。

検証する配線(中立基盤の上の core_team 層):
  1. gate が JSON を解釈して GateResult を返す(should/dispatch)
  2. gate が should=False を返すと respond は呼ばれない(沈黙の規律)
  3. respond が capability で絞った tool だけを Provider に渡す
  4. tool-use ループ: LLM の ToolCall → registry.call → 結果を戻して最終テキスト
  5. capability 外の tool 呼び出しは respond が構造的に拒否する(情報境界)
  6. signature.verify が正しい署名のみ通す

実行:
    cd garden/services/garden-gaku-co && python3 -m line.smoke_test
"""
from __future__ import annotations

import base64
import hashlib
import hmac

import capabilities
from brain import gate, respond
from brain.provider import LLMResponse, ToolCall
from line import signature
from tools import registry


class ScriptedProvider:
    """system プロンプトの内容でゲート/応答を見分けて canned 応答を返す。"""

    name = "scripted"

    def __init__(self):
        self.respond_calls = 0

    def chat(self, *, system, messages, tools=None, model=None, max_tokens=1024):
        # ゲート呼び出し(分類 AI のプロンプト)
        if "メッセージ分類" in system:
            last = str(messages[-1].get("content", ""))
            if "黙って" in last:
                return LLMResponse(text='{"should_respond": false, "reason": "宛てでない"}')
            if "echo" in last:
                return LLMResponse(
                    text='{"should_respond": true, "reason": "ツール依頼", "dispatch": {"type": "tools"}}'
                )
            return LLMResponse(
                text='{"should_respond": true, "reason": "呼びかけ", "dispatch": {"type": "direct"}}'
            )

        # 応答呼び出し(Stage2)
        self.respond_calls += 1
        # tool 結果が戻ってきたら最終テキストを返す
        if messages and messages[-1].get("role") == "tool":
            return LLMResponse(text=f"ツール結果: {messages[-1]['content']}")
        # tool が渡されていて、1 周目なら echo を呼ぶ
        if tools and any(t.name == "echo" for t in tools):
            return LLMResponse(tool_calls=[ToolCall(id="t1", name="echo", arguments={"text": "原っぱ"})])
        return LLMResponse(text="はい、承知しました。")


def main() -> None:
    p = ScriptedProvider()

    # 1. gate: 呼びかけ → should=True / direct
    g = gate.should_respond(p, latest_message="ガクコ、ちょっといい?", history_text="(なし)")
    assert g.should and g.dispatch["type"] == "direct", g
    print("[1] gate direct .............. OK")

    # 2. gate: 宛てでない → should=False(respond は呼ばれない設計)
    g2 = gate.should_respond(p, latest_message="今日は黙ってて(他の人宛て)", history_text="(なし)")
    assert not g2.should, g2
    print("[2] gate silence ............. OK")

    # 3-4. respond: tools dispatch → echo を呼んで結果を戻し最終テキスト
    out = respond.generate_response(
        p, scope="line_core_team", system="(test persona)",
        latest_message="echo して", history_text="(なし)", sender="u1", offer_tools=True,
    )
    assert out and "原っぱ" in out, f"tool-use ループが回っていない: {out!r}"
    print(f"[3-4] respond tool-use ....... OK  -> {out!r}")

    # 5. capability 外 tool は拒否(line_staff に無い架空 tool を直接呼ばせる)
    registry.register("finance_secret", "(テスト)機微ツール", {"type": "object", "properties": {}})(
        lambda a: "TOP SECRET"
    )
    assert "finance_secret" not in capabilities.tools_for("line_core_team"), "境界設定が緩い"

    class RogueProvider(ScriptedProvider):
        def chat(self, *, system, messages, tools=None, model=None, max_tokens=1024):
            if messages and messages[-1].get("role") == "tool":
                return LLMResponse(text=f"結果: {messages[-1]['content']}")
            return LLMResponse(tool_calls=[ToolCall(id="r1", name="finance_secret", arguments={})])

    out2 = respond.generate_response(
        RogueProvider(), scope="line_core_team", system="(test)",
        latest_message="機微を出して", history_text="(なし)", sender="u1", offer_tools=True,
    )
    assert "TOP SECRET" not in (out2 or ""), f"capability 外 tool が漏れた: {out2!r}"
    assert "使えません" in (out2 or ""), f"拒否メッセージが出ていない: {out2!r}"
    print("[5] capability 越え拒否 ....... OK")

    # 6. signature
    secret = "testsecret"
    body = b'{"events":[]}'
    sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert signature.verify(body, sig, secret), "正しい署名を弾いた"
    assert not signature.verify(body, sig, "wrong"), "誤った secret を通した"
    print("[6] signature verify ......... OK")

    print("\nALL GREEN — core_team 対話パイプライン(gate / respond / tool-use / 情報境界 / 署名)健全")


if __name__ == "__main__":
    main()
