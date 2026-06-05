"""LLM プロバイダ・アダプタ — ベンダー中立の対話層の最下層。

ADR 2026-06-03 vendor-neutral-interaction-layer 決定2。

頭脳(gate / respond / tool-use ループ)は、この `Provider.chat()` インターフェース
**だけ** を呼ぶ。`import anthropic` 等のベンダー固有コードはこのファイル内のアダプタ実装に
閉じ込める。LLM を別ベンダーに替える時は、新しい Provider 実装を 1 つ足してアダプタを
差し替えるだけで、tool 定義・capability・知識層(SKILL.md)はそのまま残る。

中立な受け渡し形:
  - ToolSpec: name / description / parameters(JSON Schema)— function-calling の共通最大公約数
  - messages: [{"role": "user"|"assistant"|"tool", "content": str, ["tool_call_id": str]}]
  - LLMResponse: text + tool_calls(構造化)+ raw(デバッグ用にプロバイダ生応答)
各 Provider 実装が、この中立形 ↔ 自社 SDK 形 の変換を担う。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ToolSpec:
    """LLM に渡すツール定義(ベンダー非依存)。"""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class ToolCall:
    """LLM が「このツールをこの引数で呼びたい」と返してきたもの。"""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # プロバイダ生応答(ログ/デバッグ専用、ロジックで参照しない)


@runtime_checkable
class Provider(Protocol):
    """全 LLM バックエンドが満たすインターフェース。"""

    name: str

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        ...


class AnthropicProvider:
    """Anthropic Messages API 実装(チーム channel の頭脳 b)。

    `anthropic` は遅延 import(未インストール環境でもモジュール自体は読める)。
    """

    name = "anthropic"

    def __init__(self, api_key: str | None = None, default_model: str = "claude-haiku-4-5"):
        self._api_key = api_key
        self._default_model = default_model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from anthropic import Anthropic  # 遅延 import(ベンダー固有はここだけ)
            self._client = Anthropic(api_key=self._api_key) if self._api_key else Anthropic()
        return self._client

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        client = self._ensure_client()
        kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [self._to_anthropic_message(m) for m in messages],
        }
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters}
                for t in tools
            ]
        resp = client.messages.create(**kwargs)
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
        return LLMResponse(text="".join(text_parts), tool_calls=tool_calls, raw=resp)

    @staticmethod
    def _to_anthropic_message(m: dict[str, Any]) -> dict[str, Any]:
        role = m["role"]
        if role == "tool":
            # 中立な tool 結果 → Anthropic の tool_result 形(user ロールに入れる)
            return {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }],
            }
        if role == "assistant" and m.get("tool_calls"):
            # assistant が tool を呼んだターン → text(任意)+ tool_use ブロック列で再構成。
            # これが無いと、続く tool_result が「対応する tool_use なし」で 400 になる。
            content: list[dict[str, Any]] = []
            text = m.get("content")
            if text:
                content.append({"type": "text", "text": text})
            for tc in m["tool_calls"]:
                content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc.get("arguments", {}),
                })
            return {"role": "assistant", "content": content}
        return {"role": role, "content": m["content"]}


class MockProvider:
    """テスト用の決定的プロバイダ(ネットワーク・API key 不要)。

    smoke test と将来の単体テストで、tool-use 配線を実 API なしに検証するためのもの。
    ルール:
      - tools があり、最新 user メッセージに "@call:<tool> <json>" が含まれれば ToolCall を返す
      - tool 結果メッセージ("role": "tool")を受け取ったら、その内容を要約テキストで返す
      - それ以外は最新 user メッセージを echo
    """

    name = "mock"

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        last = messages[-1] if messages else {"role": "user", "content": ""}
        if last.get("role") == "tool":
            return LLMResponse(text=f"(mock) ツール結果を受領: {last.get('content', '')}")
        content = str(last.get("content", ""))
        if tools and "@call:" in content:
            import json
            try:
                after = content.split("@call:", 1)[1].strip()
                name, _, rest = after.partition(" ")
                args = json.loads(rest) if rest.strip() else {}
            except Exception:
                name, args = "", {}
            allowed = {t.name for t in tools}
            if name in allowed:
                return LLMResponse(tool_calls=[ToolCall(id="mock-1", name=name, arguments=args)])
        return LLMResponse(text=f"(mock echo) {content}")
