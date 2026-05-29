#!/usr/bin/env python3
"""garden-gaku-co — 朝の口火(声がけ)(段3.5).

morning-briefing(06:30)が組んだ active_tasks.md を読み、Discord master に
「今日のブリーフ + 判断ほしいこと」を**対話の口火**として投稿する(06:40 cron)。

設計:
- active_tasks.md を **そのまま要約転記**(別ロジックで作り直さない=二重管理を避ける)。
  カレンダー(## スケジュール)も Triage(## 🔖 Triage)も active に入っている前提(#1/#3)。
- 挨拶・締めは固定文(claude 呼び出し不要=高速・確実)。会話は bot が受け持つ。
- active_tasks のヘッダ日付が今日でなければ「ブリーフ未生成かも」と警告(朝のヘルスチェック兼用)。

これは一方向 push ではなく**対話の口火**: 締めでガクチョに返答を促す。
"""
import datetime
import os
import re

import send as sender

JST = datetime.timezone(datetime.timedelta(hours=9))
WEEKDAY_JA = "月火水木金土日"
MIRROR_DIR = os.environ.get("MIRROR_DIR", "/home/vps-harappa/garden-mirror")
CIRCLED = "①②③④⑤⑥⑦⑧⑨"


def today_jst() -> datetime.date:
    return datetime.datetime.now(JST).date()


def active_path() -> str:
    return os.path.join(MIRROR_DIR, "hmc_tasks", "active_tasks.md")


def parse_sections(text: str):
    """`## ヘッダ` 区切りで {header: [item, ...]} を返す(item は `- ` を剥いた本文)。"""
    sections = {}
    cur = None
    for line in text.splitlines():
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            cur = h.group(1).strip()
            sections[cur] = []
            continue
        it = re.match(r"^[-*]\s+(.*)$", line.strip())
        if cur is not None and it:
            sections[cur].append(it.group(1).strip())
    return sections


def header_date(text: str):
    m = re.search(r"#\s*Today's Tasks\s*-\s*(\d{4})/(\d{2})/(\d{2})", text)
    if not m:
        return None
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def strip_paren(name: str) -> str:
    return re.sub(r"\s*[（(][^（）()]*[)）]\s*$", "", name).strip()


def classify(sections: dict):
    schedule, overdue, tasks, triage = [], [], [], []
    for header, items in sections.items():
        if "スケジュール" in header:
            schedule = items
        elif "期限超過" in header:
            overdue = items
        elif "Triage" in header or "triage" in header:
            triage = items
        else:
            tasks.extend(items)
    return schedule, overdue, tasks, triage


def compose(d: datetime.date, sections: dict) -> str:
    schedule, overdue, tasks, triage = classify(sections)
    lines = [f"おはよう、ガクチョ。今日のブリーフ整理できたよ。"]

    lines.append("")
    lines.append("📅 今日の予定")
    if schedule:
        lines += [f" {s}" for s in schedule]
    else:
        lines.append(" (予定なし)")

    if overdue:
        names = " / ".join(strip_paren(o) for o in overdue)
        lines += ["", f"🚨 期限超過: {names}"]

    if tasks:
        names = " / ".join(strip_paren(t) for t in tasks)
        lines += ["", f"📋 今日: {names}"]

    real_triage = [t for t in triage if strip_paren(t) not in ("なし", "")]
    if real_triage:
        lines += ["", f"🔖 判断ほしいの{len(real_triage)}件"]
        for i, t in enumerate(real_triage):
            mark = CIRCLED[i] if i < len(CIRCLED) else "・"
            lines.append(f" {mark} {t}")

    lines += ["", "予定と手持ち、どう組む? 気になるとこから返して。"]
    return "\n".join(lines)


def main() -> None:
    d = today_jst()
    path = active_path()
    if not os.path.exists(path):
        sender.send(
            f"⚠️ {d.isoformat()} の active_tasks が見つかりません（朝のブリーフ未生成かも）。\n"
            f"予定パス: {path}"
        )
        return
    text = open(path, encoding="utf-8").read()
    hd = header_date(text)
    if hd != d:
        sender.send(
            f"⚠️ active_tasks の日付が今日({d.isoformat()})ではありません"
            f"（読めた日付: {hd}）。ブリーフがまだ生成途中かもしれません。\n"
            f"パス: {path}"
        )
        return

    msg = compose(d, parse_sections(text))
    sender.send(msg)
    print(f"[morning-greet] sent for {d.isoformat()}")


if __name__ == "__main__":
    main()
