#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""field_assistant — フィールド運営アシスタントの実処理。

コマンド(種・対話 tool・手動のすべてがここを通る):
  weekly        週初めリマインド(当該週の準備 + 翌週の企画MTG確認)→ LINE push
  brief         活動日 D-2 ブリーフ(企画・名簿サマリ・スタッフ・天気)→ LINE push
  roster        任意日の参加者名簿(テキスト返却。--to-sheet でスプシ出力 + URL)
  furikae       当月月謝未消化チェック → LINE push(--if-last-day で月末日のみ実行)
  clear-sheets  名簿ワークブックの全タブ削除(月末掃除)

共通: --dry-run で push せず stdout に出す。--date / --month で対象指定。
正本: シフトカレンダー(発火マスター)/ STORES 予約 API(名簿)/ Open-Meteo(天気)。
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from lib import stores_lib  # noqa: E402


def _load_env():
    """service ルートの .env を読む(既存の環境変数は上書きしない)。"""
    path = os.path.join(_HERE, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_env()

JST = dt.timezone(dt.timedelta(hours=9))


def today_jst() -> dt.date:
    return dt.datetime.now(JST).date()


def _send(text: str, dry_run: bool):
    if dry_run:
        print("---- dry-run(push せず表示)----")
        print(text)
        return
    from lib import line_push
    targets = line_push.push(text)
    print(f"[field-assistant] pushed to {len(targets)} target(s)")


def _mention(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "(未記入⚠️)"
    # 「ゆーじさん」のように呼称込みのニックネームには「 さん」を重ねない
    suffix = "" if name.endswith(("さん", "ちゃん", "くん", "先生")) else " さん"
    return f"@{name}{suffix}"


def _event_line(e) -> str:
    from lib import calendar_reader as cal
    parts = [cal.date_jp(e["date"])]
    if e.get("category"):
        parts.append(e["category"])
    if e.get("activity"):
        parts.append(f"「{e['activity']}」")
    if e.get("venue"):
        parts.append(f"@{e['venue']}")
    if e.get("time"):
        parts.append(e["time"])
    return " ".join(parts)


# ── weekly ──────────────────────────────────────────────


def cmd_weekly(args) -> int:
    from lib import calendar_reader as cal
    base = dt.date.fromisoformat(args.date) if args.date else today_jst()
    monday = base - dt.timedelta(days=base.weekday())
    sunday = monday + dt.timedelta(days=6)
    next_monday, next_sunday = monday + dt.timedelta(days=7), sunday + dt.timedelta(days=7)

    this_week = cal.events_between(monday, sunday)
    next_week = [e for e in cal.events_between(next_monday, next_sunday)
                 if cal.needs_planning_mtg(e)]

    lines = [f"🌱 今週のフィールド予定({monday.month}/{monday.day}〜{sunday.month}/{sunday.day})"]
    if not this_week:
        lines.append("今週の開催予定はありません。")
    for e in this_week:
        lines.append("")
        lines.append(f"■ {_event_line(e)}")
        lines.append(f"　現場責任者: {_mention(e.get('lead'))} — 準備チェックをお願いします")
        lines.append("　□物品手配 □スタッフスレ投稿 □体験者への案内(いれば) □天気判断(前日まで)")
    if next_week:
        lines.append("")
        lines.append("─────")
        lines.append("📋 来週の企画MTG確認(おやこ・こども学部)")
        for e in next_week:
            lines.append(f"・{_event_line(e)}")
            lines.append(f"　企画: {_mention(e.get('planner'))} — 企画MTGはお済みですか?(開催2週前が目安)")
    _send("\n".join(lines), args.dry_run)
    return 0


# ── brief(D-2)───────────────────────────────────────────


def _roster_rows_for_date(date: dt.date):
    token = os.environ.get("STORES_API_TOKEN")
    client = stores_lib.StoresClient(token, verbose=False)
    start, end = stores_lib.day_bounds(date.isoformat())
    return stores_lib.build_roster(client.list_reservations(start, end), client=client)


def _rows_for_event(rows, e, n_calendar_events):
    """カレンダーのイベント e に対応する STORES 名簿行を選ぶ。対応なしは None。

    企業案件・スペシャルイベントは STORES に存在しないことがある(S43 ガクチョ指摘)。
    その場合に同日の別イベントの名簿を誤って張り付けないこと。
    照合は ①活動名の部分一致 → ②学部(category)名の一致 → ③同日イベントが
    カレンダー上 1 件だけなら表記ゆれとみなして全行、の順。
    """
    if not rows:
        return None
    act = (e.get("activity") or "").strip()
    by_name = [r for r in rows if r["イベント名"] and act and
               (r["イベント名"] in act or act in r["イベント名"])]
    if by_name:
        return by_name
    cat = (e.get("category") or "").strip()
    if cat:
        by_cat = [r for r in rows if cat in (r["イベント名"] or "")]
        if by_cat:
            return by_cat
    if n_calendar_events == 1:
        return rows
    return None


def _kids_part(row) -> str:
    """子ども名の括弧表示。記入が無い行は「空欄」と明示(S43 ガクチョ指示)。
    おとな学部はそもそも子ども欄が無いので付けない。"""
    kids = "・".join(stores_lib.kids_names(row))
    if kids:
        return f"({kids})"
    if "おとな" in (row.get("イベント名") or ""):
        return ""
    return "(子ども欄: 空欄)"


def cmd_brief(args) -> int:
    from lib import calendar_reader as cal
    from lib import weather as wx
    target = dt.date.fromisoformat(args.date) if args.date else today_jst() + dt.timedelta(days=2)
    events = cal.events_between(target, target)
    if not events:
        print(f"[field-assistant] no events on {target} — skip")
        return 0

    rows = _roster_rows_for_date(target)
    lines = [f"📋 あさって {cal.date_jp(target)} の開催情報です"]
    for e in events:
        lines.append("")
        lines.append(f"■ {_event_line(e)}")
        staff_bits = []
        if e.get("lead"):
            staff_bits.append(f"現場責任者 {_mention(e['lead'])}")
        if e.get("planner"):
            staff_bits.append(f"企画 {_mention(e['planner'])}")
        if e.get("first_aid"):
            staff_bits.append(f"応急衛生 {e['first_aid']}")
        if e.get("staff"):
            staff_bits.append(f"スタッフ {e['staff']}")
        if staff_bits:
            lines.append("　" + " / ".join(staff_bits))

        ev_rows = _rows_for_event(rows, e, len(events))
        if ev_rows is None:
            lines.append("　👨‍👩‍👧 名簿: ストアズなし(STORES に該当イベントの予約がありません)")
        else:
            total_groups = len(ev_rows)
            total_people = sum(r.get("参加人数") or 0 for r in ev_rows)
            lines.append(f"　👨‍👩‍👧 参加 {total_groups}組 {total_people}名")
            for r in ev_rows:
                lines.append(f"　・{r['苗字']}{_kids_part(r)} {r['支払方法']}")

        try:
            f = wx.forecast(e.get("venue", ""), target)
            lines.append(f"　🌤 天気({f['venue']}): {f['summary']}")
        except Exception as ex:  # 天気が落ちてもブリーフは出す
            lines.append(f"　🌤 天気: 取得失敗({type(ex).__name__})")
    lines.append("")
    lines.append("詳細名簿(アレルギー・連絡先)が必要なら「名簿出して」と話しかけてください")
    _send("\n".join(lines), args.dry_run)
    return 0


# ── roster(対話 tool / 手動)──────────────────────────────


def roster_text(date_str: str, to_sheet: bool = False) -> str:
    """tool からも呼ばれる本体。テキストサマリ(+ スプシ URL)を返す。"""
    date = dt.date.fromisoformat(date_str)
    rows = _roster_rows_for_date(date)
    if not rows:
        return f"{date_str} の参加確定の予約はありません。"
    lines = [f"📋 {date_str} の参加者名簿({len(rows)}組)"]
    by_event = {}
    for r in rows:
        by_event.setdefault(r["イベント名"], []).append(r)
    for ev, ev_rows in by_event.items():
        people = sum(r.get("参加人数") or 0 for r in ev_rows)
        lines.append(f"■ {ev}({len(ev_rows)}組 {people}名)")
        for r in ev_rows:
            mark = ""
            a = (r.get("アレルギー・留意事項") or "").strip()
            if a and a not in ("なし", "ナシ", "無し", "特になし"):
                mark = " ⚠️留意事項あり"
            lines.append(f"・{r['苗字']}{_kids_part(r)} {r['支払方法']}{mark}")
    if to_sheet:
        from lib import sheets_export
        url = sheets_export.write_roster_tab(rows, date.strftime("%m%d"))
        lines.append("")
        lines.append(f"📄 詳細一覧(保護者名・アレルギー・緊急連絡先): {url}")
        lines.append("※このシートは月末に自動クリアされます")
    return "\n".join(lines)


def cmd_roster(args) -> int:
    text = roster_text(args.date, to_sheet=args.to_sheet)
    print(text)
    return 0


# ── furikae(月末)─────────────────────────────────────────


def cmd_furikae(args) -> int:
    today = today_jst()
    if args.if_last_day:
        if (today + dt.timedelta(days=1)).day != 1:
            print("[field-assistant] not last day — skip")
            return 0
    month = args.month or today.strftime("%Y-%m")
    token = os.environ.get("STORES_API_TOKEN")
    client = stores_lib.StoresClient(token, verbose=False)
    start, end = stores_lib.month_range_jst(month)
    customers = client.list_customers()
    reservations = client.list_reservations(start, end)
    rows, targets = stores_lib.build_furikae(customers, reservations)

    lines = [f"💴 {month} 月謝未消化チェック(月謝会員 {len(rows)}名)"]
    if not targets:
        lines.append("今月の月謝未消化はゼロです 🎉")
    else:
        lines.append(f"振替対象 {len(targets)}名(当月の月謝利用 0 回):")
        for t in targets:
            note = f" ※参加{t['当月参加回数']}回あり({t['参加明細']})" if t["当月参加回数"] else ""
            lines.append(f"・{t['顧客名']}({t['契約中の月謝']}){note}")
        lines.append("")
        lines.append("振替チケットの発行は STORES 管理画面からお願いします(API は参照のみ)")

    # 一覧をスプシに書き出して URL を LINE に添付(A案・固定タブ上書き、月末掃除でも残す)
    try:
        from lib import sheets_export
        url = sheets_export.write_furikae_tab(rows, month)
        lines.append("")
        lines.append(f"📋 全会員の一覧はこちら: {url}")
    except Exception as e:  # noqa: BLE001 — シート出力失敗でも通知は止めない
        print(f"[field-assistant] sheet export skipped: {e}")

    _send("\n".join(lines), args.dry_run)

    # 監査用 CSV(VPS ローカルのみ、repo には載らない)
    out_dir = os.path.join(_HERE, "output")
    os.makedirs(out_dir, exist_ok=True)
    import csv
    path = os.path.join(out_dir, f"月謝振替チェック_{month}.csv")
    cols = ["顧客名", "契約中の月謝", "当月予約件数", "当月参加回数",
            "うち月謝利用回数", "参加明細", "振替要否"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"[field-assistant] csv: {path}")
    return 0


def weather_text(place: str, date_str: str) -> str:
    """tool からも呼ばれる本体。場所 + 日付 → 天気・気温・風のテキスト。

    calendar_reader(gspread)に依存させない: 天気は stdlib のみで動くこと
    (LINE コンテナ等どこからでも呼べること)を保つ。
    """
    from lib import weather as wx
    date = dt.date.fromisoformat(date_str)
    days_ahead = (date - today_jst()).days
    if days_ahead > 15:
        return f"{date_str} は予報範囲外です(Open-Meteo は 16 日先まで)。"
    if days_ahead < -1:
        return f"{date_str} は過去日です(予報 API のため過去の実況は出せません)。"
    f = wx.forecast(place, date)
    date_jp = f"{date.month}/{date.day}({'月火水木金土日'[date.weekday()]})"
    return f"🌤 {date_jp} {f['venue']}の天気: {f['summary']}"


def cmd_weather(args) -> int:
    print(weather_text(args.place, args.date))
    return 0


def cmd_sync_line_users(args) -> int:
    """webhook が収集した userId(line_collected.json)を soil の line_display_name と
    照合し、line_users.json(ニックネーム → userId)を更新する。

    soil 側: people/staff/*.md frontmatter の `line_display_name:` が照合キー。
    マッチしたスタッフは nicknames 全部 + 表示名を userId に紐づける(シフトカレンダーは
    どのニックネーム表記でも来るため)。マッチしない収集分は一覧表示(手動判断用)。
    """
    import json as _json
    import re as _re

    soil_dir = os.environ.get(
        "SOIL_STAFF_DIR", "/home/vps-harappa/garden-mirror/garden/soil/people/staff"
    )
    collected_path = os.path.join(_HERE, "config", "line_collected.json")
    users_path = os.path.join(_HERE, "config", "line_users.json")
    try:
        collected = _json.load(open(collected_path, encoding="utf-8"))
    except (FileNotFoundError, _json.JSONDecodeError):
        print("収集データなし(line_collected.json が空)。グループでの発話を待ってください")
        return 0
    users = {}
    try:
        users = _json.load(open(users_path, encoding="utf-8"))
    except (FileNotFoundError, _json.JSONDecodeError):
        pass

    # soil frontmatter から line_display_name / nicknames を素朴に抜く(stdlib のみ)
    staff = []  # [(display_name, [nicknames...], slug)]
    for fn in sorted(os.listdir(soil_dir)):
        if not fn.endswith(".md") or fn.startswith(("README", "index", "_")):
            continue
        head = open(os.path.join(soil_dir, fn), encoding="utf-8").read().split("---")
        if len(head) < 3:
            continue
        fm = head[1]
        m = _re.search(r"^line_display_name:\s*(.+)$", fm, _re.M)
        # 値の後ろのインラインコメント(` # …`)は捨てる
        display = _re.sub(r"\s+#.*$", "", m.group(1)).strip().strip('"') if m else ""
        if not display or display in ("null", "~"):
            continue
        # nicknames: の直後のリストだけ取る(次のキーで打ち切り)
        nick_block = _re.search(r"nicknames:\n((?:\s*-\s*.+\n)+)", fm)
        nicks = _re.findall(r"-\s*(.+)", nick_block.group(1)) if nick_block else []
        staff.append((display, [n.strip() for n in nicks], fn[:-3]))

    matched, unmatched = [], []
    for uid, display in collected.items():
        hit = next((s for s in staff if s[0] == display), None)
        if hit:
            for key in set(hit[1] + [display]):
                users[key] = uid
            matched.append(f"{display} → {hit[2]}({len(hit[1])} ニックネーム)")
        else:
            unmatched.append(f"{display}(userId 収集済・soil に line_display_name 未記録)")

    _json.dump(users, open(users_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"line_users.json 更新: {len(users)} キー")
    for m_ in matched:
        print(f"  ✅ {m_}")
    for u in unmatched:
        print(f"  ⏳ {u}")
    return 0


def cmd_clear_sheets(args) -> int:
    from lib import sheets_export
    if args.dry_run:
        print("dry-run: 名簿ワークブックの全タブ(README 以外)を削除します")
        return 0
    removed = sheets_export.clear_all()
    print(f"[field-assistant] cleared tabs: {removed or '(なし)'}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="field_assistant processor")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("weekly", help="週初めリマインド")
    w.add_argument("--date", help="基準日 YYYY-MM-DD(既定: 今日)")
    w.add_argument("--dry-run", action="store_true")
    w.set_defaults(fn=cmd_weekly)

    b = sub.add_parser("brief", help="活動日 D-2 ブリーフ")
    b.add_argument("--date", help="対象活動日 YYYY-MM-DD(既定: 今日+2)")
    b.add_argument("--dry-run", action="store_true")
    b.set_defaults(fn=cmd_brief)

    r = sub.add_parser("roster", help="任意日の参加者名簿")
    r.add_argument("--date", required=True, help="対象日 YYYY-MM-DD")
    r.add_argument("--to-sheet", action="store_true", help="スプシにも出力して URL を返す")
    r.set_defaults(fn=cmd_roster)

    f = sub.add_parser("furikae", help="月謝未消化チェック")
    f.add_argument("--month", help="対象月 YYYY-MM(既定: 当月)")
    f.add_argument("--if-last-day", action="store_true", help="月末日でなければ skip")
    f.add_argument("--dry-run", action="store_true")
    f.set_defaults(fn=cmd_furikae)

    c = sub.add_parser("clear-sheets", help="名簿ワークブックの月末掃除")
    c.add_argument("--dry-run", action="store_true")
    c.set_defaults(fn=cmd_clear_sheets)

    s = sub.add_parser("sync-line-users", help="収集済 userId を soil と照合して line_users.json 更新")
    s.set_defaults(fn=cmd_sync_line_users)

    wx = sub.add_parser("weather", help="場所 + 日付の天気・気温・風")
    wx.add_argument("--place", required=True, help="会場名・地名(venues.json で解決)")
    wx.add_argument("--date", required=True, help="対象日 YYYY-MM-DD")
    wx.set_defaults(fn=cmd_weather)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
