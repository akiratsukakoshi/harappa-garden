#!/usr/bin/env python3
"""auditor — analyzer 前のデータ整合性を整える前処理(HMC apps/freee_auditor/ 移植 + 役割拡張)

ガクチョ S47 で役割を「監査」から「analyzer が走る前のデータ整合性を整える地ならし役」に
再定義。検出を2本立てにする:
  1. 部門振り分け漏れ(deals の section_id 空)— HMC 継承。Sheets レビュー → 承認 → PUT で修正。
  2. 未登録明細(口座と同期済みだが取引化されていない = PL に未反映の wallet_txns)— ★新規。
     freee「自動で経理」で拾いきれず手動確認待ちのお金の動き。MVP は **検出して報告**まで。
     自動登録アシストは初回実データを見てから境界を決める(expense と重なる分はそちらへ)。

Garden 化の差分:
- 一括修正(PUT /deals)は **board + dry-run 必須**(破壊的・ロールバック無し)
- 部門レビューは Google Sheets タブ(importer/expense/invoice と統一)
- import パス lib.* / データ dir はサービス相対の絶対パス

フロー(SKILL Mode D):
    auditor.py scan --month YYYY-MM         # 部門漏れ + 未登録明細を検出 → review CSV + 報告
    auditor.py to-sheet <csv> --tab YYYYMM  # 部門漏れをレビュー用 Sheets に(ガクチョが部門を埋める)
    auditor.py from-sheet <tab>             # レビュー後タブ → working CSV
    auditor.py apply <csv> --dry-run        # PUT 内容を確認(Freee 更新しない)
    auditor.py apply <csv>                  # 部門を Freee に反映(PUT /deals)+ アーカイブ
"""
import os
import sys
import csv
import json
import shutil
import calendar
import argparse
import datetime
from datetime import date, timedelta, datetime as dt_cls

from dotenv import load_dotenv

from lib.freee_client import FreeeClient
from lib.utils import setup_logger, ensure_directory

logger = setup_logger("FinanceAuditor")
load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCAN_DIR = os.path.join(_BASE_DIR, "scan")
APPLIED_DIR = os.path.join(_BASE_DIR, "applied")

# S47 実データ(2026-05)+ ガクチョ確認(2026-06-17)で確定:
# wallet_txns の status==1 = 未登録(取引化されていない = PL未反映。Square/STORES の振込入金・
# 手数料など)。status==2 = 登録済み。headline の「未登録明細」件数は status==1 のみで数える
# (全 status の内訳は透明性のため引き続き報告する)。
UNREGISTERED_STATUS = 1

REVIEW_COLUMNS = [
    ("deal_id", "取引ID"),
    ("detail_id", "明細ID"),
    ("date", "日付"),
    ("type", "種別"),
    ("partner", "取引先"),
    ("account_item", "勘定科目"),
    ("amount", "金額"),
    ("description", "摘要"),
    ("section_name", "部門"),
]


def _month_range(month_str):
    """'YYYY-MM' → ('YYYY-MM-01', 'YYYY-MM-<末日>')。"""
    y, m = [int(x) for x in month_str.split("-")]
    last = calendar.monthrange(y, m)[1]
    return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last:02d}"


def _default_start():
    today = date.today().replace(day=1)
    for _ in range(3):
        today = (today - timedelta(days=1)).replace(day=1)
    return today.strftime("%Y-%m-%d")


# ── scan ──────────────────────────────────────────────────────────────────────
def cmd_scan(client, args):
    ensure_directory(SCAN_DIR)
    if args.month:
        start, end = _month_range(args.month)
    else:
        start, end = args.start, args.end

    sections = client.get_sections()
    if not sections:
        logger.error("部門一覧の取得に失敗しました")
        return 1
    account_items = client.get_account_items() or []
    account_map = {a["id"]: a["name"] for a in account_items}

    # ── 1. 部門振り分け漏れ ──
    logger.info(f"取引を取得中... 期間: {start} 〜 {end}")
    deals = client.get_all_deals(start_issue_date=start, end_issue_date=end)
    logger.info(f"取得件数: {len(deals)} 件")
    missing = []
    for deal in deals:
        for detail in deal.get("details", []):
            if not detail.get("section_id"):
                missing.append({
                    "deal_id": deal["id"],
                    "detail_id": detail["id"],
                    "date": deal.get("issue_date", ""),
                    "type": deal.get("type", ""),
                    "partner": deal.get("partner_name", ""),
                    "account_item": account_map.get(detail.get("account_item_id", 0), ""),
                    "amount": detail.get("amount", 0),
                    "description": detail.get("description", ""),
                    "section_name": "",
                })

    review_csv = ""
    if missing:
        ts = dt_cls.now().strftime("%Y%m%d_%H%M%S")
        review_csv = os.path.join(SCAN_DIR, f"audit_{ts}.csv")
        with open(review_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=[k for k, _ in REVIEW_COLUMNS])
            w.writeheader()
            w.writerows(missing)

    # ── 2. 未登録明細(口座同期済 / 取引化されていない = PL 未反映)──
    #   freee /api/1/wallet_txns。明細の「未登録」判定条件は初回実データで確定するため、
    #   status の内訳と件数を必ず報告する(ガクチョ + Claude が実物を見て境界を決める)。
    unreg_count, status_breakdown, unreg_samples = _scan_unregistered(client, start, end)

    # ── 報告(機械可読 + 人間可読)──
    print(f"AUDIT_MISSING: {len(missing)}")
    if review_csv:
        print(f"AUDIT_CSV: {review_csv}")
    print(f"UNREGISTERED_TXNS: {unreg_count}")
    if status_breakdown:
        print(f"UNREGISTERED_STATUS_BREAKDOWN: {json.dumps(status_breakdown, ensure_ascii=False)}")

    print(f"\n=== データ整合性スキャン {start} 〜 {end} ===")
    print(f"部門未設定の明細: {len(missing)} 件")
    if missing and review_csv:
        print(f"  → レビュー CSV: {review_csv}")
        print(f"  利用可能な部門: {', '.join(s['name'] for s in sections)}")
    print(f"未登録の口座明細(取引化されていない / PL 未反映、status==1): {unreg_count} 件")
    if status_breakdown:
        print(f"  status 内訳(全件): {status_breakdown}  ※1=未登録 / 2=登録済")
    if unreg_samples:
        print("  未登録明細サンプル(最大5件):")
        for s in unreg_samples[:5]:
            print(f"    {s}")
    return 0


def _scan_unregistered(client, start, end):
    """口座/カードの明細(wallet_txns)から未登録分(status==1)を拾う。

    全 wallet_txns を取得 → status 別に集計(透明性のため全内訳を報告)。headline の
    「未登録明細」件数は UNREGISTERED_STATUS(=1)のみ。サンプルも status==1 から拾う。
    戻り値: (未登録件数[status==1], 全 status 内訳, status==1 のサンプル)
    """
    walletables = client.get_walletables()
    targets = [w for w in walletables if w.get("type") in ("bank_account", "credit_card")]
    unreg = 0
    breakdown = {}
    samples = []
    for w in targets:
        try:
            txns = client.get_wallet_txns(
                walletable_type=w.get("type"), walletable_id=w.get("id"),
                start_date=start, end_date=end, limit=100,
            )
        except Exception as e:
            logger.warning(f"wallet_txns 取得失敗({w.get('name')}): {e}")
            continue
        for t in txns:
            st = t.get("status")
            breakdown[str(st)] = breakdown.get(str(st), 0) + 1
            if st == UNREGISTERED_STATUS:
                unreg += 1
                if len(samples) < 10:
                    samples.append({
                        "口座": w.get("name"), "date": t.get("date"),
                        "amount": t.get("amount"), "entry_side": t.get("entry_side"),
                        "description": (t.get("description") or "")[:30],
                    })
    return unreg, breakdown, samples


# ── to-sheet / from-sheet ─────────────────────────────────────────────────────
def cmd_to_sheet(args):
    from lib import sheets_client
    # 部門ドロップダウンは実 Freee を正本(mapping_config でなく live get_sections())
    client = FreeeClient()
    sections = [s["name"] for s in client.get_sections()]
    with open(args.file, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("EMPTY: no rows")
        return 0
    tab = args.tab or ("audit" + dt_cls.now().strftime("%Y%m"))
    url, gid = sheets_client.write_tab(
        rows, tab, REVIEW_COLUMNS,
        dropdown_key="section_name", dropdown_values=sections,
        highlight_keys=["section_name"],
    )
    logger.info(f"Wrote {len(rows)} rows to audit tab {tab}: {url}")
    print(f"REVIEW_SHEET_URL: {url}")
    print(f"REVIEW_TAB: {tab}")
    print(f"REVIEW_ROWS: {len(rows)}")
    return 0


def cmd_from_sheet(args):
    from lib import sheets_client
    rows = sheets_client.read_tab(args.tab, REVIEW_COLUMNS)
    if not rows:
        print("EMPTY: no rows after review")
        return 1
    ensure_directory(SCAN_DIR)
    ts = dt_cls.now().strftime("%Y%m%d_%H%M%S")
    out = args.out or os.path.join(SCAN_DIR, f"audit_{args.tab}_reviewed_{ts}.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[k for k, _ in REVIEW_COLUMNS])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in [c for c, _ in REVIEW_COLUMNS]})
    logger.info(f"Read {len(rows)} reviewed rows from tab {args.tab} → {out}")
    print(f"REVIEWED_CSV: {out}")
    print(f"REVIEWED_ROWS: {len(rows)}")
    return 0


# ── apply(部門を Freee に反映)─────────────────────────────────────────────────
def cmd_apply(client, args):
    ensure_directory(APPLIED_DIR)
    if not os.path.exists(args.csv_file):
        logger.error(f"ファイルが見つかりません: {args.csv_file}")
        return 1

    sections = client.get_sections()
    section_id_map = {s["name"]: s["id"] for s in sections}

    with open(args.csv_file, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    to_update = [r for r in rows if r.get("section_name", "").strip()]
    skip = len(rows) - len(to_update)
    print(f"更新対象: {len(to_update)} 件  スキップ(部門未入力): {skip} 件")

    if args.dry_run:
        print("--- DRY RUN (freee は更新されません) ---")
        for r in to_update:
            sname = r["section_name"].strip()
            sid = section_id_map.get(sname, "未定義")
            try:
                amt = int(float(str(r.get("amount", "0")).replace(",", "")))
            except ValueError:
                amt = 0
            print(f"  [{r['date']}] {r.get('partner') or '取引先なし'} / {r.get('account_item')} "
                  f"¥{amt:,} → 部門: {sname} (ID: {sid})")
        print(f"DRY_RUN_ROWS: {len(to_update)}")
        return 0

    success, errors = 0, []
    for r in to_update:
        sname = r["section_name"].strip()
        sid = section_id_map.get(sname)
        if not sid:
            errors.append(f"部門名が見つかりません: '{sname}' (deal_id={r['deal_id']})")
            continue
        result = client.update_deal_section(int(r["deal_id"]), int(r["detail_id"]), sid)
        if result:
            logger.info(f"  ✓ deal_id={r['deal_id']} [{r['date']}] → {sname}")
            success += 1
        else:
            errors.append(f"更新失敗: deal_id={r['deal_id']}")

    print(f"APPLIED: {success}")
    print(f"APPLY_ERRORS: {len(errors)}")
    for e in errors:
        logger.error(f"  - {e}")

    ts = dt_cls.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(args.csv_file, os.path.join(APPLIED_DIR, f"applied_{ts}.csv"))
    return len(errors)


def main():
    parser = argparse.ArgumentParser(description="finance auditor — データ整合性の地ならし")
    sub = parser.add_subparsers(dest="command", required=True)
    sp = sub.add_parser("scan")
    sp.add_argument("--month", default=None, help="対象月 YYYY-MM(指定すると当月のみ)")
    sp.add_argument("--start", default=_default_start(), help="開始日 YYYY-MM-DD(既定: 3ヶ月前)")
    sp.add_argument("--end", default=date.today().strftime("%Y-%m-%d"), help="終了日 YYYY-MM-DD")
    p_ts = sub.add_parser("to-sheet")
    p_ts.add_argument("file")
    p_ts.add_argument("--tab", default=None)
    p_fs = sub.add_parser("from-sheet")
    p_fs.add_argument("tab")
    p_fs.add_argument("--out", default=None)
    ap = sub.add_parser("apply")
    ap.add_argument("csv_file")
    ap.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    needs_client = args.command in ("scan", "apply")
    client = None
    if needs_client:
        client = FreeeClient()
        if not client.refresh_token():
            logger.error("freee 認証に失敗しました")
            sys.exit(1)

    rc = 0
    if args.command == "scan":
        rc = cmd_scan(client, args)
    elif args.command == "to-sheet":
        rc = cmd_to_sheet(args)
    elif args.command == "from-sheet":
        rc = cmd_from_sheet(args)
    elif args.command == "apply":
        rc = cmd_apply(client, args)
    if rc:
        sys.exit(rc)


if __name__ == "__main__":
    main()
