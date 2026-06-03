"""行動 tool レジストリ — ベンダー中立。

ADR 2026-06-03 vendor-neutral-interaction-layer 決定3 / 決定4。

行動 tool = 「素の Python 関数(ロジック)+ 中立スキーマ(定義)」。
LLM に渡す時だけ Provider アダプタが各社形式に変換する(registry は何も知らない)。
scope による認可は capabilities.py が担い、registry は「定義と実行」だけに責務を限定する。

使い方:
    @register("echo", "渡した文字列をそのまま返す(疎通確認用)",
              {"type": "object", "properties": {"text": {"type": "string"}},
               "required": ["text"]})
    def _echo(args): return args.get("text", "")

    specs_for(["echo"])        -> [ToolSpec(...)]   # capability で絞った後の一覧を Provider へ
    call("echo", {"text": "hi"}) -> "hi"            # LLM の ToolCall を実行
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from brain.provider import ToolSpec


@dataclass
class Tool:
    spec: ToolSpec
    handler: Callable[[dict[str, Any]], str]


_REGISTRY: dict[str, Tool] = {}


def register(name: str, description: str, parameters: dict[str, Any]):
    """tool を登録するデコレータ。handler は (args: dict) -> str。"""
    def deco(fn: Callable[[dict[str, Any]], str]) -> Callable[[dict[str, Any]], str]:
        _REGISTRY[name] = Tool(ToolSpec(name=name, description=description, parameters=parameters), fn)
        return fn
    return deco


def specs_for(names) -> list[ToolSpec]:
    """指定 tool 名(=capability で絞った集合)の ToolSpec 一覧を返す。"""
    return [_REGISTRY[n].spec for n in names if n in _REGISTRY]


def call(name: str, arguments: dict[str, Any]) -> str:
    """tool を実行して文字列結果を返す。未登録なら例外。"""
    tool = _REGISTRY.get(name)
    if tool is None:
        raise KeyError(f"unknown tool: {name}")
    return tool.handler(arguments or {})


def all_names() -> set[str]:
    return set(_REGISTRY)


# ── 最初の中立 tool(疎通確認用)─────────────────────────────
@register(
    "echo",
    "渡した文字列をそのまま返す。基盤の疎通確認用。",
    {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "返す文字列"}},
        "required": ["text"],
    },
)
def _echo(args: dict[str, Any]) -> str:
    return str(args.get("text", ""))
