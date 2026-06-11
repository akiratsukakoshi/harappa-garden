#!/usr/bin/env python3
"""garden-gaku-co — 朝の口火(声がけ)(段3.5).

morning-briefing(06:30)が組んだ active_tasks.md を読み、Discord master channel に
「今朝の口火」を対話の起点として投稿する(06:40 cron)。

設計:
- 口火文面は daily-pilot SKILL の Mode 1 Step 4 / Output Style に従って claude -p で生成。
  Python は固定文を持たない(秘書らしい先回りを SKILL に集約・モデル独立)。
- active_tasks のヘッダ日付チェックは健全性確認として残す(古い/未生成を早期に検出)。
- ペルソナは --system-prompt、業務観は SKILL 同梱で確実に効かせる。
- read-only(Edit/Write 禁止)。書き戻しは bot 側 Mode 2 が担う。
"""
import datetime
import os
import re
import subprocess

import send as sender

JST = datetime.timezone(datetime.timedelta(hours=9))
MIRROR_DIR = os.environ.get("MIRROR_DIR", "/home/vps-harappa/garden-mirror")
# S27 で board は LiveSync 隔離領域へ移動済(bot.py と同じ既定値)
BOARD_DIR = os.environ.get("BOARD_DIR", "/home/vps-harappa/garden/board")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
HERE = os.path.dirname(os.path.abspath(__file__))
CHARTER_PATH = os.environ.get(
    "GARDEN_CHARTER",
    "/home/vps-harappa/garden/CHARTER.md",
)
SKILL_PATH = os.environ.get(
    "DAILY_PILOT_SKILL",
    "/home/vps-harappa/garden/plots/daily-pilot/SKILL.md",
)

PERSONA = open(os.path.join(HERE, "persona", "g-gaku-co.md"), encoding="utf-8").read()
CHARTER = open(CHARTER_PATH, encoding="utf-8").read()
SKILL = open(SKILL_PATH, encoding="utf-8").read()


def today_jst() -> datetime.date:
    return datetime.datetime.now(JST).date()


def active_path() -> str:
    return os.path.join(MIRROR_DIR, "hmc_tasks", "active_tasks.md")


def triage_board_path(d: datetime.date) -> str:
    return os.path.join(
        BOARD_DIR, "triage",
        f"{d.isoformat()}-morning-briefing.md",
    )


def header_date(text: str):
    m = re.search(r"#\s*Today's Tasks\s*-\s*(\d{4})/(\d{1,2})/(\d{1,2})", text)
    if not m:
        return None
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def build_greet_prompt(d: datetime.date, active_text: str, board_text: str) -> str:
    return (
        "あなたはガクコ(daily-pilot 区画の声)として、今朝の口火を "
        "Discord master channel に投稿します。判断知識は CHARTER(全 plot 共通)と "
        "daily-pilot SKILL(本区画固有)の二段で集約されています。SKILL は CHARTER を継承します。\n\n"
        + "──── Garden CHARTER ────\n"
        + CHARTER
        + "\n──── CHARTER ここまで ────\n\n"
        + "──── daily-pilot SKILL ────\n"
        + SKILL
        + "\n──── SKILL ここまで ────\n\n"
        + f"[今日] {d.isoformat()}\n\n"
        + "[今朝の active_tasks.md]\n----\n"
        + active_text
        + "\n----\n\n"
        + (f"[今朝の Triage board]\n----\n{board_text}\n----\n\n" if board_text else "")
        + "上の active と Triage を **横串で読み**、SKILL の Mode 1 Step 4(口火)と "
        + "CHARTER の Output Style 質感・SKILL の Output Style(daily-pilot 固有)に従って、"
        + "Discord に投稿する口火文面を生成してください。\n"
        + "- 1タスク1行・セクション順は SKILL の Output Style を厳守。\n"
        + "- 締めは **具体的な過ごし方の提案 + AI 支援の提案を1〜2文** で。汎用文は禁止。\n"
        + "- 出力は Discord に投げる本文のみ。前置きや説明は不要。\n"
        + "- 1900文字以内(Discord 1メッセージ制限の安全側)。\n"
    )


def run_claude(prompt: str) -> str:
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--system-prompt", PERSONA,
        "--strict-mcp-config",
        # 口火は read-only。Edit/Write 等の書き戻しは bot 側 Mode 2 の責務。
        "--disallowedTools",
        "Bash Glob Grep WebFetch WebSearch NotebookEdit TodoWrite Task Edit Write",
        "--model", "sonnet",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=200, cwd=HERE)
    except subprocess.TimeoutExpired:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def main() -> None:
    d = today_jst()
    path = active_path()
    if not os.path.exists(path):
        sender.send(
            f"⚠️ {d.isoformat()} の active_tasks が見つかりません(朝のブリーフ未生成かも)。\n"
            f"予定パス: {path}"
        )
        return
    text = open(path, encoding="utf-8").read()
    hd = header_date(text)
    if hd != d:
        sender.send(
            f"⚠️ active_tasks の日付が今日({d.isoformat()})ではありません"
            f"(読めた日付: {hd})。ブリーフがまだ生成途中かも。\n"
            f"パス: {path}"
        )
        return

    board_path = triage_board_path(d)
    board_text = ""
    if os.path.exists(board_path):
        board_text = open(board_path, encoding="utf-8").read()

    msg = run_claude(build_greet_prompt(d, text, board_text))
    if not msg:
        sender.send(
            f"⚠️ 朝の口火生成に失敗。active_tasks.md は組まれています。\n"
            f"確認: {path}"
        )
        return
    sender.send(msg[:1900])
    print(f"[morning-greet] sent for {d.isoformat()}")


if __name__ == "__main__":
    main()
