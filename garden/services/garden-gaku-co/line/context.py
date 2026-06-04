"""core_team scope のコンテキスト組み立て — 知識層の load。

ADR 2026-06-03 vendor-neutral 決定1(知識層は中立 markdown)/
ADR 2026-05-31 memory-three-layer §4(情報境界)。

system prompt の材料:
  - persona(scope 固有の「個」)
  - CHARTER(Garden 全 plot 共通の業務観・呼称・トーン)
  - 直近の自 scope RAW(line_core_team の過去数日 + 当日)

**情報境界の要**: ここで load するのは core_team **自身の** RAW だけ。
master の私的 wiki / RAW は混ぜない(core_team から見えてはいけない)。
財務・給与等の機微は capability(行動層)と memory(知識層)の両方で遮断する。

短期履歴(gate に渡す会話の流れ)は、軽量なプロセス内リングで持つ(group 単位)。
再起動で消えるが、MVP のゲート判定には十分。永続は RAW logging が担う。
"""
from __future__ import annotations

import os
import pathlib
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
HERE = pathlib.Path(__file__).resolve().parent
SVC = HERE.parent  # garden-gaku-co/

CHARTER_PATH = pathlib.Path(
    os.environ.get("GARDEN_CHARTER", "/home/vps-harappa/garden/CHARTER.md")
)
PERSONA_PATH = pathlib.Path(
    os.environ.get("CORE_TEAM_PERSONA", str(SVC / "persona" / "core-team.md"))
)

MIRROR_DIR = os.environ.get("MIRROR_DIR", "/home/vps-harappa/garden-mirror")
SCOPE = "line_core_team"
RAW_DIR = pathlib.Path(MIRROR_DIR) / "garden" / "memory" / SCOPE / "raw"
RECENT_RAW_DAYS = 3
RAW_CHARS_CAP = 20000

BOT_NAME = "ガクコ"


class _FileCache:
    """mtime ベースの動的キャッシュ。編集 → 次 turn で反映(bot 再起動不要、S30 と同方式)。"""

    def __init__(self, path: pathlib.Path):
        self._path = path
        self._mtime: float | None = None
        self._text = ""

    def get(self) -> str:
        try:
            m = self._path.stat().st_mtime
        except OSError:
            return self._text
        if m != self._mtime:
            try:
                self._text = self._path.read_text(encoding="utf-8")
                self._mtime = m
            except OSError:
                pass
        return self._text


_charter_cache = _FileCache(CHARTER_PATH)
_persona_cache = _FileCache(PERSONA_PATH)


def _read_recent_raw(today: date) -> str:
    """自 scope の過去 RECENT_RAW_DAYS 日 + 当日 RAW を結合(古い順)。"""
    parts: list[str] = []
    for delta in range(RECENT_RAW_DAYS, -1, -1):
        d = today - timedelta(days=delta)
        p = RAW_DIR / f"{d.isoformat()}.md"
        try:
            parts.append(p.read_text(encoding="utf-8"))
        except OSError:
            continue
    text = "\n\n".join(parts)
    if len(text) > RAW_CHARS_CAP:
        text = text[-RAW_CHARS_CAP:]  # 直近を残す
    return text


def build_system() -> str:
    """persona + CHARTER + 直近 RAW から core_team の system prompt を組む。"""
    persona = _persona_cache.get() or "あなたは Garden の対話エージェント「ガクコ」です。"
    charter = _charter_cache.get()
    recent = _read_recent_raw(datetime.now(JST).date())

    sections = [
        "あなたは運営スタッフ(core_team)の LINE グループで動くガクコです。",
        "判断知識は CHARTER(Garden 全 plot 共通の業務観・呼称・トーン)と persona に従ってください。",
        "",
        "──── persona ────",
        persona,
        "──── persona ここまで ────",
    ]
    if charter:
        sections += ["", "──── Garden CHARTER ────", charter, "──── CHARTER ここまで ────"]
    if recent:
        sections += [
            "",
            "[直近の記憶(この運営チャンネルの過去数日 + 当日 RAW)]",
            recent,
        ]
    sections += [
        "",
        "返答は簡潔・自然に。発言不要なら null とだけ出力してください。",
        "あなたは運営チームの一員として、判断の補助・情報整理を行います。",
    ]
    return "\n".join(sections)


# ── プロセス内 短期履歴(group 単位リング)──────────────────────
_HISTORY: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))


def record(group_id: str, sender: str, text: str) -> None:
    _HISTORY[group_id].append((datetime.now(JST).strftime("%H:%M"), sender, text))


def history_text(group_id: str) -> str:
    rows = _HISTORY.get(group_id)
    if not rows:
        return "(会話履歴なし)"
    return "\n".join(f"[{ts}] {who}: {msg}" for ts, who, msg in rows)
