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


# ── meeting_coordinator: 会議調整 ────────────────────────
@register(
    "request_meeting_coordination",
    "core_team LINEで会議調整を開始する。参加者・対象月・会議タイトルを受け取り、"
    "ガクチョのGoogle Calendar空き時間から候補を作ってLINEに提示する。"
    "運営会議の定例種以外のスポット会議で使う。",
    {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "会議タイトル"},
            "participants": {"type": "string", "description": "参加者名。例: 少佐,ゆーじさん,慶ちゃん"},
            "month": {"type": "string", "description": "対象月。YYYY-MM / 今月 / 来月"},
            "duration": {"type": "integer", "description": "会議時間(分)。未指定なら90"},
            "proposer": {"type": "string", "description": "発議者 slug。通常は akira-tsukakoshi"},
        },
        "required": ["title", "participants", "month"],
    },
)
def _request_meeting_coordination(args: dict[str, Any]) -> str:
    try:
        mc = _meeting_coordinator()
        argv = [
            "spot",
            "--title", str(args["title"]),
            "--participants", str(args["participants"]),
            "--month", str(args.get("month") or "今月"),
            "--duration", str(args.get("duration") or 90),
            "--proposer", str(args.get("proposer") or "akira-tsukakoshi"),
        ]
        return _capture_cli(mc.main, argv)
    except Exception as e:
        return f"会議調整の開始に失敗しました({type(e).__name__}: {e})"


@register(
    "record_meeting_availability",
    "会議調整中の参加者返信を記録する。例: AとCならOK、6日午前は不可。",
    {
        "type": "object",
        "properties": {
            "meeting_id": {"type": "string", "description": "調整メッセージに含まれる meeting_id"},
            "participant": {"type": "string", "description": "返信した参加者名。例: 少佐"},
            "text": {"type": "string", "description": "返信内容を原文に近い形で記録"},
        },
        "required": ["meeting_id", "participant", "text"],
    },
)
def _record_meeting_availability(args: dict[str, Any]) -> str:
    try:
        mc = _meeting_coordinator()
        entry = mc.add_availability(
            str(args["meeting_id"]),
            str(args["participant"]),
            str(args["text"]),
        )
        return f"可否を記録しました: {entry['participant']} / {entry['text']}\nガクチョの確定判断を待ちます。"
    except Exception as e:
        return f"参加可否の記録に失敗しました({type(e).__name__}: {e})"


@register(
    "confirm_meeting_coordination",
    "会議候補を確定し、Zoom URL発行、Google Calendar登録、LINE確定通知を行う。"
    "ガクチョまたは発議者が確定した時だけ使う。",
    {
        "type": "object",
        "properties": {
            "meeting_id": {"type": "string", "description": "調整メッセージに含まれる meeting_id。省略時は最新のopen meetingを使う"},
            "candidate_id": {"type": "string", "description": "確定する候補ID。例: A"},
            "meeting_type": {"type": "string", "description": "meeting_id省略時の絞り込み。運営会議なら operations_monthly"},
        },
        "required": ["candidate_id"],
    },
)
def _confirm_meeting_coordination(args: dict[str, Any]) -> str:
    try:
        mc = _meeting_coordinator()
        meeting_id = args.get("meeting_id")
        return mc.confirm_meeting(
            str(meeting_id) if meeting_id else None,
            str(args["candidate_id"]).strip().upper(),
            meeting_type=str(args.get("meeting_type") or "operations_monthly"),
        )
    except Exception as e:
        return f"会議確定に失敗しました({type(e).__name__}: {e})"


def _meeting_coordinator():
    """meeting-coordinator の processor を import して返す(パスは env で差し替え可)。"""
    import importlib.util
    import os
    import sys
    mc_dir = os.environ.get(
        "MEETING_COORDINATOR_DIR", "/home/vps-harappa/garden/services/meeting-coordinator"
    )
    module_path = os.path.join(mc_dir, "processor.py")
    spec = importlib.util.spec_from_file_location("meeting_coordinator_processor", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load meeting coordinator from {module_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["meeting_coordinator_processor"] = mod
    spec.loader.exec_module(mod)
    return mod


def _capture_cli(fn, argv: list[str]) -> str:
    """processor.main(argv) の stdout を tool 結果として返す。"""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(argv)
    out = buf.getvalue().strip()
    if code:
        return out or f"コマンドが終了コード {code} で失敗しました"
    return out
