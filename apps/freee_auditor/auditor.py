#!/usr/bin/env python3
"""
freee 経理監査ツール
部門紐づけ漏れの発見・CSV出力・一括修正
"""
import sys
import os
import csv
import shutil
import argparse
from datetime import date, timedelta, datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from modules.freee_client import FreeeClient
from modules.utils import setup_logger

logger = setup_logger("FreeeAuditor")

SCAN_DIR = "data/freee_auditor/scan"
APPLIED_DIR = "data/freee_auditor/applied"

CSV_FIELDS = [
    "deal_id", "detail_id", "date", "type", "partner",
    "account_item", "amount", "description",
    "suggested_section", "section_name",
]


def _default_start():
    today = date.today()
    three_months_ago = today.replace(day=1)
    for _ in range(3):
        three_months_ago = (three_months_ago - timedelta(days=1)).replace(day=1)
    return three_months_ago.strftime("%Y-%m-%d")


def cmd_scan(client, args):
    """部門未設定の取引を検索してCSVに出力する"""
    os.makedirs(SCAN_DIR, exist_ok=True)

    sections = client.get_sections()
    if not sections:
        logger.error("部門一覧の取得に失敗しました")
        sys.exit(1)
    section_name_list = [s["name"] for s in sections]

    account_items = client.get_account_items() or []
    account_map = {a["id"]: a["name"] for a in account_items}

    logger.info(f"取引を取得中... 期間: {args.start} 〜 {args.end}")
    deals = client.get_all_deals(
        start_issue_date=args.start,
        end_issue_date=args.end,
    )
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
                    "suggested_section": "",
                    "section_name": "",
                })

    if not missing:
        logger.info("✓ 部門未設定の取引はありませんでした")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(SCAN_DIR, f"audit_{ts}.csv")

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(missing)

    print(f"\n=== スキャン結果 ===")
    print(f"部門未設定の取引: {len(missing)} 件")
    print(f"出力ファイル: {out_path}")
    print(f"\n利用可能な部門一覧:")
    for s in sections:
        print(f"  - {s['name']} (ID: {s['id']})")
    print(f"\n--- 次のステップ ---")
    print(f"1. {out_path} を開き、'section_name' 列に各行の部門名を入力してください")
    print(f"   ※ 'suggested_section' 列にAIの提案を記入してから確認してもOKです")
    print(f"2. 確認後に以下を実行:")
    print(f"   python3 apps/freee_auditor/auditor.py apply {out_path}")
    print(f"   (テスト実行: ... apply {out_path} --dry-run)")


def cmd_apply(client, args):
    """CSVの section_name をfreeeに反映する"""
    os.makedirs(APPLIED_DIR, exist_ok=True)

    if not os.path.exists(args.csv_file):
        logger.error(f"ファイルが見つかりません: {args.csv_file}")
        sys.exit(1)

    sections = client.get_sections()
    section_id_map = {s["name"]: s["id"] for s in sections}

    rows = []
    with open(args.csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    to_update = [r for r in rows if r.get("section_name", "").strip()]
    skip_count = len(rows) - len(to_update)

    print(f"更新対象: {len(to_update)} 件  スキップ(部門未入力): {skip_count} 件")

    if args.dry_run:
        print("--- DRY RUN (freeeは更新されません) ---")
        for r in to_update:
            sname = r["section_name"].strip()
            sid = section_id_map.get(sname, "未定義")
            print(f"  [{r['date']}] {r['partner'] or '取引先なし'} / {r['account_item']} "
                  f"¥{int(r['amount']):,} → 部門: {sname} (ID: {sid})")
        return

    success, errors = 0, []

    for r in to_update:
        sname = r["section_name"].strip()
        sid = section_id_map.get(sname)
        if not sid:
            msg = f"部門名が見つかりません: '{sname}' (deal_id={r['deal_id']})"
            logger.warning(msg)
            errors.append(msg)
            continue

        result = client.update_deal_section(
            int(r["deal_id"]),
            int(r["detail_id"]),
            sid,
        )
        if result:
            logger.info(f"  ✓ deal_id={r['deal_id']} [{r['date']}] → {sname}")
            success += 1
        else:
            msg = f"更新失敗: deal_id={r['deal_id']}"
            logger.error(f"  ✗ {msg}")
            errors.append(msg)

    print(f"\n=== 完了 ===")
    print(f"成功: {success} 件 / エラー: {len(errors)} 件")

    if errors:
        print("エラー一覧:")
        for e in errors:
            print(f"  - {e}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(APPLIED_DIR, f"applied_{ts}.csv")
    shutil.copy2(args.csv_file, archive_path)
    print(f"CSVをアーカイブ済み: {archive_path}")


def main():
    parser = argparse.ArgumentParser(description="freee 経理監査ツール")
    sub = parser.add_subparsers(dest="command")

    # scan
    scan_p = sub.add_parser("scan", help="部門未設定の取引を検索してCSV出力")
    scan_p.add_argument("--start", default=_default_start(), help="開始日 YYYY-MM-DD (デフォルト: 3ヶ月前)")
    scan_p.add_argument("--end", default=date.today().strftime("%Y-%m-%d"), help="終了日 YYYY-MM-DD")

    # apply
    apply_p = sub.add_parser("apply", help="CSVの部門設定をfreeeに反映")
    apply_p.add_argument("csv_file", help="適用するCSVファイルのパス")
    apply_p.add_argument("--dry-run", action="store_true", help="テスト実行（freeeは更新しない）")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = FreeeClient()
    if not client.refresh_token():
        logger.error("freee 認証に失敗しました")
        sys.exit(1)

    if args.command == "scan":
        cmd_scan(client, args)
    elif args.command == "apply":
        cmd_apply(client, args)


if __name__ == "__main__":
    main()
