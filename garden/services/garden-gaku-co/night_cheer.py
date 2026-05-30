#!/usr/bin/env python3
"""garden-gaku-co — 夜のレビュー完了レポート + ひとこと(段2).

night-review(22:30)の実行結果を読み、Discord master に「振り返り処理の完了レポート」
として送る。単独で見てもタスク管理の報告と分かり、正常/異常の確認も兼ねる(ヘルスチェック)。

構成:
1. night-review ログ(garden/log/{today}-night-review.log)から exit_code と
   ==NOTIFY== .. ==END== ブロック(件数集計)を読む。
2. 正常: 「振り返り処理を実行しました + 件数 + ひとことコメント」
   異常: 「⚠️ 問題があったかも(exit / NOTIFY) + ログパス」 → エラーがここで分かる。
3. 件数とエラー検出は決め打ち(claude に頼らない=確実)。
   コメントだけ archive の今日の完了タスク名を踏まえて claude(ペルソナ)が1文生成。
"""
import datetime
import os
import re
import subprocess

import send as sender

JST = datetime.timezone(datetime.timedelta(hours=9))
WEEKDAY_JA = "月火水木金土日"
HERE = os.path.dirname(os.path.abspath(__file__))
MIRROR_DIR = os.environ.get("MIRROR_DIR", "/home/vps-harappa/garden-mirror")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
NO_TOOLS = "Bash Edit Read Write Glob Grep WebFetch WebSearch NotebookEdit TodoWrite Task"
CHARTER_PATH = os.environ.get(
    "GARDEN_CHARTER",
    "/home/vps-harappa/garden/CHARTER.md",
)
SKILL_PATH = os.environ.get(
    "DAILY_PILOT_SKILL",
    "/home/vps-harappa/garden/plots/daily-pilot/SKILL.md",
)
# 集計とエラー検出は決め打ち(確実性優先)。トーンとひとことだけ CHARTER + SKILL + persona に従う。
CHARTER = open(CHARTER_PATH, encoding="utf-8").read()
SKILL = open(SKILL_PATH, encoding="utf-8").read()
PERSONA = open(os.path.join(HERE, "persona", "g-gaku-co.md"), encoding="utf-8").read()


def today_jst() -> datetime.date:
    return datetime.datetime.now(JST).date()


def fmt_date(d: datetime.date) -> str:
    return f"{d.year}/{d.month:02d}/{d.day:02d} ({WEEKDAY_JA[d.weekday()]})"


def read_review_log(d: datetime.date):
    path = os.path.join(MIRROR_DIR, "garden", "log", f"{d.isoformat()}-night-review.log")
    if not os.path.exists(path):
        return None, path
    return open(path, encoding="utf-8").read(), path


def parse_review(log_text: str):
    m_exit = re.search(r"^exit_code:\s*(\d+)", log_text, re.M)
    exit_code = int(m_exit.group(1)) if m_exit else None
    # ログには prompt 内の NOTIFY テンプレ({done_count}等)と claude 出力の実 NOTIFY
    # (数字入り)が両方含まれる。数字が入っている最後のブロックを採用する。
    blocks = re.findall(r"==NOTIFY==(.*?)==END==", log_text, re.S)
    notify = None
    for block in reversed(blocks):
        if re.search(r"完了[^0-9]*?\d+\s*件", block):
            notify = block.strip()
            break
    counts = {}
    if notify:
        for key, label in [("done", "完了"), ("keep", "持ち越し"),
                           ("added", "新規追加"), ("overdue", "期限超過")]:
            mm = re.search(label + r"[^0-9]*?(\d+)\s*件", notify)
            counts[key] = int(mm.group(1)) if mm else None
    return exit_code, notify, counts


def todays_completed(d: datetime.date) -> str:
    path = os.path.join(MIRROR_DIR, "hmc_tasks", "archive.md")
    if not os.path.exists(path):
        return ""
    text = open(path, encoding="utf-8").read()
    ymd = f"{d.year}/{d.month:02d}/{d.day:02d}"
    m = re.search(rf"^###\s+{re.escape(ymd)}\b.*?(?=^###\s|\Z)", text, re.M | re.S)
    return m.group(0).strip() if m else ""


def compose_comment(completed_block: str, d: datetime.date) -> str:
    ctx = completed_block or "今日は archive に完了記録がありませんでした。"
    prompt = (
        "あなたはガクコ(daily-pilot 区画の声)として、夜のレビュー後の"
        "「ねぎらいのひとこと」を Discord に投稿します。判断知識は CHARTER と "
        "daily-pilot SKILL の二段で集約されています。SKILL は CHARTER を継承します。\n\n"
        + "──── Garden CHARTER ────\n"
        + CHARTER
        + "\n──── CHARTER ここまで ────\n\n"
        + "──── daily-pilot SKILL ────\n"
        + SKILL
        + "\n──── SKILL ここまで ────\n\n"
        + f"【夜のレビューのひとこと】\n今日({fmt_date(d)})の完了記録:\n\n{ctx}\n\n"
        + "CHARTER の Core Philosophy(Empowerment & Proactivity)と Output Style 質感、"
        + "そしてあなたの persona(中性的・理知的・偏りなく)を踏まえ、"
        + "ガクチョへの“ねぎらいの一言”を **1文だけ** 書いてください。\n"
        + "ですます調基本。誇張しない。完了が無くても責めず淡々と。\n"
        + "出力は本文のみ(前置き・記号囲みなし)。"
    )
    try:
        proc = subprocess.run(
            [CLAUDE_BIN, "-p", prompt,
             "--system-prompt", PERSONA,
             "--strict-mcp-config",
             "--disallowedTools", NO_TOOLS, "--model", "sonnet"],
            capture_output=True, text=True, timeout=150,
        )
    except subprocess.TimeoutExpired:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def main() -> None:
    d = today_jst()
    log_text, path = read_review_log(d)

    if log_text is None:
        sender.send(
            f"⚠️ {fmt_date(d)} の夜のレビュー・ログが見つかりません（未実行の可能性）。\n"
            f"ログ予定: {path}"
        )
        return

    exit_code, notify, counts = parse_review(log_text)
    if exit_code != 0 or notify is None:
        sender.send(
            "⚠️ 夜のレビューに問題があったかもしれません。\n"
            f"exit_code={exit_code} / NOTIFY={'あり' if notify else 'なし'}\n"
            f"ログを確認してください: {path}"
        )
        return

    # --- 正常: レポート組み立て ---
    parts = []
    if counts.get("done") is not None:
        parts.append(f"完了 {counts['done']}件")
    if counts.get("keep") is not None:
        parts.append(f"持ち越し {counts['keep']}件")
    if counts.get("added") is not None:
        parts.append(f"追加 {counts['added']}件")
    if counts.get("overdue"):
        parts.append(f"期限超過(明日) {counts['overdue']}件")
    count_line = " / ".join(parts) if parts else "(件数の取得に失敗 — ログ確認推奨)"

    comment = compose_comment(todays_completed(d), d)
    msg = f"タスクの振り返り処理を実行しました（{fmt_date(d)}）\n{count_line}"
    if comment:
        msg += f"\n\n{comment}"

    sender.send(msg)
    print(f"[night-cheer] sent for {d.isoformat()} (exit={exit_code})")


if __name__ == "__main__":
    main()
