#!/usr/bin/env python3
"""board_facts.py — board の承認判断に必要な「客観事実」を seed 毎に集める。

セッション27 で notify_pending が Discord に貼る情報を強化するために導入。
方針(セッション27 ガクチョ合意): 「事実提示」のみ。チェックリストの自動判定はしない。
ファイル存在やシートの状態を事実として並べ、判断はガクチョが行う。

設計:
  - 各 seed に対応する fact 関数を FACT_PROVIDERS に登録
  - 関数は frontmatter dict を受け、(label, value) のリストを返す
  - 取得失敗時も例外を上位に投げず (label, "取得失敗: ...") を返す
  - notify_pending は collect_facts(seed, fm) を呼ぶだけ

将来:
  - 月次シート Q列の TRUE 件数などは gspread 依存が必要なため初期スコープ外。
    必要になったら別モジュールで取得関数を足し、provider から呼ぶ。
"""

import datetime
import glob
import os
from pathlib import Path
from typing import Callable

INBOX_KODOMON_DIR = Path(os.environ.get(
    "INBOX_KODOMON_DIR",
    "/home/vps-harappa/garden-mirror/garden/inbox/kodomon"
))

MONTHLY_UI_SHEET_ID = os.environ.get("MONTHLY_UI_SHEET_ID", "1_RMAQuSb3eWV30WGQ_gsJI5M6Ll1WHvbM4ifkGDuNkM")


def _kodomon_csv_status(target_month: str) -> tuple[str, str]:
    """対象月のコドモン CSV の配置状況を返す(label, value)。"""
    if not target_month or len(target_month) < 7:
        return ("📂 コドモン CSV", "対象月不明")
    ym_hyphen = target_month
    ym_compact = target_month.replace("-", "")

    patterns = [
        str(INBOX_KODOMON_DIR / f"{ym_hyphen}.csv"),
        str(INBOX_KODOMON_DIR / f"{ym_compact}.csv"),
        str(INBOX_KODOMON_DIR / f"*{ym_hyphen}*.csv"),
        str(INBOX_KODOMON_DIR / f"*{ym_compact}*.csv"),
    ]
    matches: list[str] = []
    for pat in patterns:
        for m in glob.glob(pat):
            if m not in matches:
                matches.append(m)

    if not matches:
        return (
            "📂 コドモン CSV",
            f"⚠️ 未配置(`inbox/kodomon/{ym_hyphen}.csv` or `{ym_compact}.csv` 等が無い)",
        )

    p = Path(matches[0])
    try:
        st = p.stat()
        size_kb = st.st_size // 1024
        mtime_str = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
        extra = f" / 他 {len(matches) - 1} 件" if len(matches) > 1 else ""
        return ("📂 コドモン CSV", f"`{p.name}` ({size_kb}KB, {mtime_str} 配置){extra}")
    except Exception as e:
        return ("📂 コドモン CSV", f"配置済 (`{p.name}`, 詳細取得失敗: {str(e)[:80]})")


def _monthly_ui_sheet_link(tab_month: str, label_prefix: str = "📊 月次 UI Sheet") -> tuple[str, str]:
    """Monthly UI Sheet の URL を組み立て(タブ名併記)。"""
    if not MONTHLY_UI_SHEET_ID:
        return (label_prefix, "(MONTHLY_UI_SHEET_ID 未設定)")
    url = f"https://docs.google.com/spreadsheets/d/{MONTHLY_UI_SHEET_ID}/edit"
    return (label_prefix, f"{url} (タブ `{tab_month}`)")


def facts_for_month_end_prep(fm: dict) -> list[tuple[str, str]]:
    """shift_manager/month-end-working-hours-prep の客観事実。"""
    target_month = (fm.get("target_month") or "").strip()
    facts: list[tuple[str, str]] = []
    facts.append(_kodomon_csv_status(target_month))
    if target_month:
        facts.append(_monthly_ui_sheet_link(target_month, "📊 月次 UI Sheet(当月)"))
        # Mode 2 の翌々月 Q列確認用リンクも併記
        try:
            y, m = map(int, target_month.split("-"))
            m2 = m + 2
            y2 = y + (m2 - 1) // 12
            m2 = ((m2 - 1) % 12) + 1
            next_tab = f"{y2:04d}-{m2:02d}"
            facts.append(_monthly_ui_sheet_link(next_tab, "📊 月次 UI Sheet(翌々月 Q列確認)"))
        except Exception:
            pass
    return facts


def facts_for_monthly_shift_survey(fm: dict) -> list[tuple[str, str]]:
    """shift_manager/monthly-shift-survey の客観事実(URL は board frontmatter から拾えるので最小)。"""
    target_month = (fm.get("target_month") or "").strip()
    facts: list[tuple[str, str]] = []
    if target_month:
        facts.append(_monthly_ui_sheet_link(target_month, "📊 月次 UI Sheet(対象月 Q列確認)"))
    return facts


def facts_for_monthly_working_hours_confirmation(fm: dict) -> list[tuple[str, str]]:
    """shift_manager/monthly-working-hours-confirmation の客観事実。"""
    target_month = (fm.get("target_month") or "").strip()
    facts: list[tuple[str, str]] = []
    if target_month:
        facts.append(("🗂 タブ名", f"`{target_month}_稼働時間`"))
    return facts


FACT_PROVIDERS: dict[str, Callable[[dict], list[tuple[str, str]]]] = {
    "shift_manager/month-end-working-hours-prep": facts_for_month_end_prep,
    "shift_manager/monthly-shift-survey": facts_for_monthly_shift_survey,
    "shift_manager/monthly-working-hours-confirmation": facts_for_monthly_working_hours_confirmation,
}


def collect_facts(seed: str, fm: dict) -> list[tuple[str, str]]:
    """seed に対応する fact provider を呼ぶ。未登録なら []。例外は飲み込んでメッセージに変換。"""
    provider = FACT_PROVIDERS.get(seed)
    if not provider:
        return []
    try:
        return provider(fm)
    except Exception as e:
        return [("(facts 取得エラー)", str(e)[:200])]
