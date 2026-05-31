"""memory_logger.py — Garden 記憶層の RAW logging(S22 Stage A 最小実装)

ADR: docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md

責務:
  - scope ごとの RAW を `garden/memory/{scope}/raw/{YYYY-MM-DD}.md` に append する
  - 初回(その日 1 turn 目)はファイルを frontmatter 付きで初期化する
  - 書式は人間が読める日次 MD(夜のレビューで読み返す前提)

スコープ外(後段の責務):
  - EXTRACT / CONSOLIDATE → 夜間バッチ(Stage B)
  - soil + memory wiki への振り分け → 菌糸 Mode 1 Ingest(Stage A.5)
  - 14 日経過 RAW 削除 → 夜間バッチ(Stage B)

Stage A 時点では、対話を「捨てない」仕組みだけを動かす。
"""

import datetime
import os
import pathlib
import threading


JST = datetime.timezone(datetime.timedelta(hours=9))

# garden-mirror 配下に置く = LiveSync 経由で Obsidian/PC/iPhone から読める + writeback-daemon が拾う
# 環境変数で上書き可(MIRROR_DIR 既定は bot.py と合わせる)
_DEFAULT_BASE = os.environ.get(
    "MEMORY_BASE",
    os.path.join(os.environ.get("MIRROR_DIR", "/home/vps-harappa/garden-mirror"),
                 "garden", "memory"),
)

_lock = threading.Lock()


def _raw_dir(scope: str, base: str | None = None) -> pathlib.Path:
    return pathlib.Path(base or _DEFAULT_BASE) / scope / "raw"


def _today_path(scope: str, now: datetime.datetime, base: str | None = None) -> pathlib.Path:
    return _raw_dir(scope, base) / f"{now.date().isoformat()}.md"


def _ensure_file(path: pathlib.Path, scope: str, now: datetime.datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    header = (
        "---\n"
        f"scope: {scope}\n"
        f"date: {now.date().isoformat()}\n"
        "layer: raw\n"
        "---\n\n"
        f"# {scope} RAW {now.date().isoformat()}\n\n"
    )
    path.write_text(header, encoding="utf-8")


def append_turn(
    scope: str,
    user_text: str,
    bot_reply: str,
    user_label: str = "ガクチョ",
    bot_label: str = "ガクコ",
    now: datetime.datetime | None = None,
    base: str | None = None,
) -> pathlib.Path:
    """1 turn(ユーザー発話 + bot 返答)を RAW に append する。

    戻り値: 書き込み先パス(テスト・ログ表示用)
    """
    now = now or datetime.datetime.now(JST)
    path = _today_path(scope, now, base=base)
    block = (
        f"## {now.strftime('%H:%M:%S')}\n\n"
        f"**{user_label}**:\n{user_text.rstrip()}\n\n"
        f"**{bot_label}**:\n{bot_reply.rstrip()}\n\n"
        "---\n\n"
    )
    with _lock:
        _ensure_file(path, scope, now)
        with path.open("a", encoding="utf-8") as f:
            f.write(block)
    return path


def append_note(
    scope: str,
    note: str,
    label: str = "note",
    now: datetime.datetime | None = None,
    base: str | None = None,
) -> pathlib.Path:
    """単発の note(bot 起点の発話 / 観察ログ等)を append する。

    morning_greet / night_cheer など 一方向の bot 発話を残したい場合に使う。
    Stage A 最小実装では bot.py のみが呼ぶが、将来の拡張用に用意。
    """
    now = now or datetime.datetime.now(JST)
    path = _today_path(scope, now, base=base)
    block = (
        f"## {now.strftime('%H:%M:%S')} [{label}]\n\n"
        f"{note.rstrip()}\n\n"
        "---\n\n"
    )
    with _lock:
        _ensure_file(path, scope, now)
        with path.open("a", encoding="utf-8") as f:
            f.write(block)
    return path
