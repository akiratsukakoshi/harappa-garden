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


# ── field_assistant: イベント参加者名簿(read-only)──────────────
@register(
    "get_event_roster",
    "指定日の原っぱ大学イベント参加者名簿を返す(苗字・子どもの名前・利用チケット)。"
    "ユーザーが「詳しく」「一覧で」「アレルギーも」等フル名簿を求めた時だけ to_sheet=true にすると、"
    "スプレッドシートに詳細(保護者名・電話・アレルギー・緊急連絡先)を出力して URL も返す。",
    {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "対象日 YYYY-MM-DD"},
            "to_sheet": {"type": "boolean", "description": "フル名簿をスプシに出力するか(既定 false)"},
        },
        "required": ["date"],
    },
)
def _get_event_roster(args: dict[str, Any]) -> str:
    try:
        return _field_assistant().roster_text(
            str(args["date"]), to_sheet=bool(args.get("to_sheet"))
        )
    except Exception as e:
        return f"名簿の取得に失敗しました({type(e).__name__}: {e})"


def _field_assistant():
    """field-assistant の processor を import して返す(パスは env で差し替え可)。"""
    import os
    import sys
    fa_dir = os.environ.get(
        "FIELD_ASSISTANT_DIR", "/home/vps-harappa/garden/services/field-assistant"
    )
    if fa_dir not in sys.path:
        sys.path.insert(0, fa_dir)
    import processor as fa_processor
    return fa_processor


# ── field_assistant: 任意地点・任意日の天気(read-only)─────────────
@register(
    "get_weather",
    "指定した場所と日付の天気予報(天気・気温・降水確率・風/突風)を返す。"
    "場所は会場名(逗子/森戸海岸/千葉)でも任意の地名でもよい(地名検索で解決)。"
    "16 日先まで。日付は YYYY-MM-DD で渡す(「あさって」等は変換してから)。",
    {
        "type": "object",
        "properties": {
            "place": {"type": "string", "description": "会場名または地名"},
            "date": {"type": "string", "description": "対象日 YYYY-MM-DD"},
        },
        "required": ["place", "date"],
    },
)
def _get_weather(args: dict[str, Any]) -> str:
    try:
        return _field_assistant().weather_text(str(args["place"]), str(args["date"]))
    except Exception as e:
        return f"天気の取得に失敗しました({type(e).__name__}: {e})"
