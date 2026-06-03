"""中立基盤の smoke test — 実 API/LINE 不要(MockProvider 使用)。

ADR 2026-06-03 vendor-neutral-interaction-layer「薄い実スライス + smoke test」。

検証する配線:
  1. capability で scope の tool を絞れる(line_staff に echo が在る)
  2. その ToolSpec だけを Provider に渡せる
  3. Provider が ToolCall を返す(中立形)
  4. registry がその ToolCall を実行して結果を返す
  5. tool 結果を messages に戻すと Provider が次の応答を返す(tool-use ループの1周)

実行:
    cd garden/services/garden-gaku-co && python3 -m brain.smoke_test
"""
from __future__ import annotations

import capabilities
from brain.provider import MockProvider, Provider
from tools import registry


def run_round(provider: Provider, scope: str, user_text: str) -> str:
    tool_names = capabilities.tools_for(scope)
    specs = registry.specs_for(tool_names)
    messages: list[dict] = [{"role": "user", "content": user_text}]

    resp = provider.chat(system="(smoke) あなたは中立基盤のテスト対象です。", messages=messages, tools=specs)

    # tool-use ループ 1 周(最大 1 回だけ回す簡易版)
    if resp.tool_calls:
        tc = resp.tool_calls[0]
        assert tc.name in tool_names, f"capability 外の tool が呼ばれた: {tc.name}"
        result = registry.call(tc.name, tc.arguments)
        messages.append({"role": "assistant", "content": f"[tool_use {tc.name}]"})
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        resp2 = provider.chat(system="(smoke)", messages=messages, tools=specs)
        return resp2.text
    return resp.text


def main() -> None:
    provider = MockProvider()

    # 1. capability gating
    assert "echo" in capabilities.tools_for("line_core_team"), "core_team が echo を持たない"
    assert capabilities.tools_for("不明scope") == frozenset(), "未知 scope は空であるべき"
    print("[1] capability gating ........ OK")

    # 2. ToolSpec を渡せる
    specs = registry.specs_for(capabilities.tools_for("line_staff"))
    assert any(s.name == "echo" for s in specs), "echo の ToolSpec が無い"
    print("[2] specs_for ................ OK")

    # 3-5. tool-use ループ 1 周
    out = run_round(provider, "line_core_team", '@call:echo {"text": "原っぱ"}')
    assert "原っぱ" in out, f"tool 結果が戻っていない: {out!r}"
    print(f"[3-5] tool-use loop .......... OK  -> {out!r}")

    # 通常会話(tool を呼ばない経路)
    out2 = run_round(provider, "line_staff", "こんにちは")
    assert "こんにちは" in out2, f"echo 経路が壊れている: {out2!r}"
    print(f"[6] plain chat ............... OK  -> {out2!r}")

    print("\nALL GREEN — 中立基盤(provider / registry / capabilities)の配線は健全")


if __name__ == "__main__":
    main()
