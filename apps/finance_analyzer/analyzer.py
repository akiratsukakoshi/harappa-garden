#!/usr/bin/env python3
"""
freee 財務分析ツール
PL/BS/CF の取得・品質確認・予測用データ出力
"""
import sys
import os
import csv
import json
import argparse
from datetime import date, datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from modules.freee_client import FreeeClient
from modules.utils import setup_logger

logger = setup_logger("FinanceAnalyzer")

REPORTS_DIR = "data/finance_analyzer/reports"
TARGETS_FILE = "data/finance_analyzer/targets.json"

# freee 勘定カテゴリ分類
SALES_CATEGORIES = {"売上高"}
COGS_CATEGORIES = {
    "売上原価", "期首商品棚卸", "当期商品仕入",
    "他勘定振替高(商)", "期末商品棚卸", "商品売上原価",
}
SGA_CATEGORIES = {"販売管理費"}


# ── ユーティリティ ──────────────────────────────────────────────────────────────

def _add_months(dt, n):
    """日付に n ヶ月加算する"""
    month = dt.month - 1 + n
    year = dt.year + month // 12
    month = month % 12 + 1
    return dt.replace(year=year, month=month, day=1)


def _load_targets():
    if os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "fiscal_year": date.today().year,
        "fiscal_start_month": 10,
        "annual_targets": {"revenue": 0, "gross_profit": 0, "operating_profit": 0},
        "notes": "",
    }


def _save_targets(targets):
    os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
    with open(TARGETS_FILE, "w", encoding="utf-8") as f:
        json.dump(targets, f, ensure_ascii=False, indent=2)


def _fmt(n):
    """数値を円形式でフォーマット"""
    return f"{int(n):,}"


def _fiscal_months(fiscal_year, fiscal_start_month, count=12):
    """会計年度の (calendar_year, calendar_month, fiscal_month_index) リストを返す"""
    result = []
    y, m = fiscal_year, fiscal_start_month
    for i in range(1, count + 1):
        result.append((y, m, i))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return result


def _parse_pl_response(resp):
    """get_trial_pl の応答から {revenue, cogs, gross_profit, sga, operating_profit} を返す"""
    out = {"revenue": 0, "cogs": 0, "gross_profit": 0, "sga": 0, "operating_profit": 0}
    if not resp or "trial_pl" not in resp:
        return out
    for item in resp["trial_pl"].get("balances", []):
        cat = item.get("account_category_name", "")
        name = item.get("account_item_name", "")
        if not name:
            continue  # 小計・合計行は除外
        c = item.get("credit_amount", 0)
        d = item.get("debit_amount", 0)
        if cat in SALES_CATEGORIES:
            val = c - d
        elif cat in COGS_CATEGORIES or cat in SGA_CATEGORIES:
            val = d - c
        else:
            continue
        if cat in SALES_CATEGORIES:
            out["revenue"] += val
        elif cat in COGS_CATEGORIES:
            out["cogs"] += val
        elif cat in SGA_CATEGORIES:
            out["sga"] += val
    out["gross_profit"] = out["revenue"] - out["cogs"]
    out["operating_profit"] = out["gross_profit"] - out["sga"]
    return out


def _print_pl_table(monthly_data, fiscal_months_list, targets):
    """月次PLをMarkdownテーブルとして標準出力に表示"""
    cols = [f"{y}-{m:02d}" for y, m, _ in fiscal_months_list]
    rows = ["売上高", "売上原価", "売上総利益", "販売管理費", "営業利益"]
    key_map = {
        "売上高": "revenue", "売上原価": "cogs",
        "売上総利益": "gross_profit", "販売管理費": "sga", "営業利益": "operating_profit",
    }

    # カラム幅を計算
    col_w = max(10, max((len(c) for c in cols), default=7) + 2)
    row_w = 12

    header = f"{'項目':<{row_w}}" + "".join(f"{c:>{col_w}}" for c in cols) + f"{'累計':>{col_w}}"
    sep = "-" * len(header)
    print(header)
    print(sep)

    totals = {k: 0 for k in key_map.values()}
    for row_label in rows:
        key = key_map[row_label]
        values = []
        for col in cols:
            v = monthly_data.get(col, {}).get(key, 0)
            totals[key] += v
            values.append(v)
        line = f"{row_label:<{row_w}}" + "".join(f"{_fmt(v):>{col_w}}" for v in values)
        line += f"{_fmt(totals[key]):>{col_w}}"
        if row_label in ("売上総利益", "営業利益"):
            print(sep)
        print(line)
        if row_label in ("売上総利益", "営業利益"):
            print(sep)

    # 目標比較
    t = targets.get("annual_targets", {})
    if t.get("revenue"):
        ratio = totals["revenue"] / t["revenue"] * 100
        print(f"\n目標: 売上高 {_fmt(t['revenue'])}円 / 進捗: {ratio:.1f}%")
    if t.get("operating_profit"):
        ratio = totals["operating_profit"] / t["operating_profit"] * 100
        print(f"目標: 営業利益 {_fmt(t['operating_profit'])}円 / 進捗: {ratio:.1f}%")


# ── コマンド ────────────────────────────────────────────────────────────────────

def cmd_check(client, args):
    """データ品質チェック：部門未設定・未決済の件数を月別に表示"""
    targets = _load_targets()
    fiscal_year = args.fiscal_year or targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)
    fm_list = _fiscal_months(fiscal_year, fiscal_start)

    today = date.today()
    print(f"\n=== データ品質チェック FY{fiscal_year} ===\n")
    header = f"{'月':<10} {'総件数':>8} {'部門未設定':>10} {'未決済':>8}"
    print(header)
    print("-" * len(header))

    total_missing = 0
    for cal_y, cal_m, _ in fm_list:
        month_str = f"{cal_y}-{cal_m:02d}"
        if date(cal_y, cal_m, 1) > today:
            print(f"{month_str:<10} {'(未来)':>8}")
            continue

        start = f"{cal_y}-{cal_m:02d}-01"
        last_day = (date(cal_y + (cal_m // 12), cal_m % 12 + 1, 1) - __import__('datetime').timedelta(days=1)).day
        end = f"{cal_y}-{cal_m:02d}-{last_day:02d}"

        deals = client.get_all_deals(start_issue_date=start, end_issue_date=end)
        total = len(deals)
        missing_sec = sum(
            1 for d in deals
            for det in d.get("details", []) if not det.get("section_id")
        )
        unsettled = sum(1 for d in deals if d.get("payment_status") not in ("settled", None))
        total_missing += missing_sec
        flag = " ⚠" if missing_sec > 0 else ""
        print(f"{month_str:<10} {total:>8} {missing_sec:>10}{flag} {unsettled:>8}")

    print(f"\n合計 部門未設定: {total_missing} 件")
    if total_missing > 0:
        print("→ 修正するには: python3 apps/freee_auditor/auditor.py scan を実行してください")


def cmd_pl(client, args):
    """PLデータを取得してテーブル表示 + CSV保存"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    targets = _load_targets()
    fiscal_year = args.fiscal_year or targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)

    start_fm = args.start_month
    end_fm = args.end_month

    fm_list = _fiscal_months(fiscal_year, fiscal_start)
    # 指定範囲にフィルタ
    fm_list = [fm for fm in fm_list if start_fm <= fm[2] <= end_fm]

    print(f"\n=== 損益計算書 FY{fiscal_year} "
          f"(財務月{start_fm}〜{end_fm} / {fm_list[0][0]}-{fm_list[0][1]:02d}〜"
          f"{fm_list[-1][0]}-{fm_list[-1][1]:02d}) ===")
    print("(単位: 円)\n")

    monthly_data = {}
    for cal_y, cal_m, fm_idx in fm_list:
        col = f"{cal_y}-{cal_m:02d}"
        logger.info(f"PL取得中: {col} (財務月{fm_idx})")
        resp = client.get_trial_pl(fiscal_year, start_month=cal_m, end_month=cal_m)
        monthly_data[col] = _parse_pl_response(resp)

    _print_pl_table(monthly_data, fm_list, targets)

    # CSV保存
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(REPORTS_DIR, f"pl_fy{fiscal_year}_{ts}.csv")
    rows_out = ["売上高", "売上原価", "売上総利益", "販売管理費", "営業利益"]
    key_map = {
        "売上高": "revenue", "売上原価": "cogs", "売上総利益": "gross_profit",
        "販売管理費": "sga", "営業利益": "operating_profit",
    }
    cols = [f"{y}-{m:02d}" for y, m, _ in fm_list]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["項目"] + cols + ["累計"])
        for label in rows_out:
            key = key_map[label]
            vals = [monthly_data.get(c, {}).get(key, 0) for c in cols]
            writer.writerow([label] + vals + [sum(vals)])
    print(f"\nCSV保存: {csv_path}")


def cmd_cf(client, args):
    """キャッシュフロー分析：口座残高と月次純CF推移を表示"""
    targets = _load_targets()
    fiscal_year = targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)

    # 口座残高
    walletables = client.get_walletables()
    bank_wallets = [w for w in walletables if w.get("type") in ("bank_account", "credit_card")]

    total_balance = sum(w.get("balance", 0) for w in bank_wallets if w.get("balance") is not None)

    print(f"\n=== キャッシュポジション ({date.today()}) ===\n")
    print(f"{'口座名':<30} {'残高':>15}")
    print("-" * 48)
    for w in bank_wallets:
        bal = w.get("balance")
        if bal is None:
            continue
        print(f"{w.get('name', '不明'):<30} {_fmt(bal):>15} 円")
    print("-" * 48)
    print(f"{'合計':<30} {_fmt(total_balance):>15} 円")

    # 月次営業利益をCFの近似値として取得
    months = args.months
    fm_list = _fiscal_months(fiscal_year, fiscal_start)
    today = date.today()
    actual_months = [fm for fm in fm_list if date(fm[0], fm[1], 1) <= today][-months:]

    if actual_months:
        print(f"\n=== 月次営業利益 (CF近似値、直近{len(actual_months)}ヶ月) ===\n")
        print(f"{'月':<10} {'売上高':>12} {'営業利益':>12}")
        print("-" * 36)
        total_op = 0
        for cal_y, cal_m, fm_idx in actual_months:
            col = f"{cal_y}-{cal_m:02d}"
            resp = client.get_trial_pl(fiscal_year, start_month=cal_m, end_month=cal_m)
            pl = _parse_pl_response(resp)
            total_op += pl["operating_profit"]
            print(f"{col:<10} {_fmt(pl['revenue']):>12} {_fmt(pl['operating_profit']):>12}")
        print("-" * 36)
        avg = total_op / len(actual_months) if actual_months else 0
        print(f"{'平均月次利益':<10} {_fmt(avg):>25}")

        # CF予測
        t = targets.get("annual_targets", {})
        months_remaining = 12 - len([fm for fm in fm_list if date(fm[0], fm[1], 1) <= today])
        projected_end_balance = total_balance + avg * months_remaining
        print(f"\n=== CF予測 (残り{months_remaining}ヶ月、月平均 {_fmt(avg)}円で推移した場合) ===")
        print(f"  現在残高: {_fmt(total_balance)} 円")
        print(f"  年度末予測残高: {_fmt(projected_end_balance)} 円")
        if projected_end_balance < 0:
            deficit_month = None
            bal = total_balance
            for fm in fm_list:
                if date(fm[0], fm[1], 1) > today:
                    bal += avg
                    if bal < 0 and deficit_month is None:
                        deficit_month = f"{fm[0]}-{fm[1]:02d}"
            if deficit_month:
                print(f"  ⚠️  {deficit_month} に資金ショートの可能性があります")


def cmd_summary(client, args):
    """予測・戦略議論用の財務サマリーを生成 (JSON + テキスト出力)"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    targets = _load_targets()
    fiscal_year = args.fiscal_year or targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)
    fm_list = _fiscal_months(fiscal_year, fiscal_start)

    today = date.today()
    actual_months = [fm for fm in fm_list if date(fm[0], fm[1], 1) <= today]

    # PL取得
    print(f"FY{fiscal_year} のPLデータを取得中...")
    monthly_pl = {}
    for cal_y, cal_m, fm_idx in actual_months:
        col = f"{cal_y}-{cal_m:02d}"
        resp = client.get_trial_pl(fiscal_year, start_month=cal_m, end_month=cal_m)
        monthly_pl[col] = _parse_pl_response(resp)

    # YTD集計
    ytd = {"revenue": 0, "cogs": 0, "gross_profit": 0, "sga": 0, "operating_profit": 0}
    for v in monthly_pl.values():
        for k in ytd:
            ytd[k] += v[k]

    # 口座残高
    walletables = client.get_walletables()
    bank_wallets = [w for w in walletables
                    if w.get("type") in ("bank_account", "credit_card") and w.get("balance") is not None]
    total_cash = sum(w.get("balance", 0) for w in bank_wallets)

    months_elapsed = len(actual_months)
    months_remaining = 12 - months_elapsed

    # 月次平均
    avg_rev = ytd["revenue"] / months_elapsed if months_elapsed else 0
    avg_op = ytd["operating_profit"] / months_elapsed if months_elapsed else 0

    # 年度末予測
    t = targets.get("annual_targets", {})
    projected_full_year = {k: ytd[k] + (ytd[k] / months_elapsed * months_remaining if months_elapsed else 0)
                           for k in ytd}

    # JSON出力
    summary_data = {
        "generated_at": str(today),
        "fiscal_year": fiscal_year,
        "fiscal_start_month": fiscal_start,
        "months_elapsed": months_elapsed,
        "months_remaining": months_remaining,
        "targets": t,
        "ytd_pl": ytd,
        "monthly_pl": monthly_pl,
        "projected_full_year_pl": projected_full_year,
        "current_cash": {
            "total": total_cash,
            "walletables": [{"name": w.get("name"), "balance": w.get("balance")} for w in bank_wallets],
        },
        "monthly_avg": {"revenue": avg_rev, "operating_profit": avg_op},
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(REPORTS_DIR, f"summary_fy{fiscal_year}_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    # テキストサマリー表示
    print(f"\n{'='*55}")
    print(f"  財務サマリー FY{fiscal_year}  ({months_elapsed}ヶ月経過 / 残り{months_remaining}ヶ月)")
    print(f"{'='*55}")

    print(f"\n【現金・預金残高】")
    for w in bank_wallets:
        print(f"  {w['name']:<25} {_fmt(w['balance']):>15} 円")
    print(f"  {'合計':<25} {_fmt(total_cash):>15} 円")

    print(f"\n【PL実績 ({months_elapsed}ヶ月累計)】")
    for label, key in [("売上高", "revenue"), ("売上原価", "cogs"),
                        ("売上総利益", "gross_profit"), ("販売管理費", "sga"), ("営業利益", "operating_profit")]:
        val = ytd[key]
        tgt = t.get({"revenue": "revenue", "operating_profit": "operating_profit"}.get(key, ""), 0)
        ratio_str = f"  目標比 {val/tgt*100:.1f}%" if tgt else ""
        print(f"  {label:<12} {_fmt(val):>15} 円{ratio_str}")

    print(f"\n【年度末予測 (現ペース継続)】")
    for label, key in [("売上高予測", "revenue"), ("営業利益予測", "operating_profit")]:
        pval = projected_full_year[key]
        tgt = t.get(key.replace("予測", ""), 0)
        gap_str = f"  目標差 {_fmt(tgt - pval)}円不足" if tgt and pval < tgt else (
                  f"  目標差 {_fmt(pval - tgt)}円超過" if tgt else "")
        print(f"  {label:<12} {_fmt(pval):>15} 円{gap_str}")

    print(f"\n【月次トレンド (直近{min(6, months_elapsed)}ヶ月)】")
    print(f"  {'月':<10} {'売上高':>12} {'営業利益':>12}")
    print(f"  {'-'*36}")
    for col, pl in list(monthly_pl.items())[-6:]:
        print(f"  {col:<10} {_fmt(pl['revenue']):>12} {_fmt(pl['operating_profit']):>12}")

    print(f"\n詳細JSON: {json_path}")
    print(f"\n--- このサマリーをもとに以下の議論ができます ---")
    print(f"  ・年度末着地予測の精度を上げる (部門別内訳、季節変動)")
    print(f"  ・目標未達の場合のシナリオ分析")
    print(f"  ・キャッシュフローの危険月の特定")
    print(f"  ・目標達成に必要な月次売上の試算")


def cmd_targets(client_unused, args):
    """目標値の表示・更新"""
    targets = _load_targets()

    if args.set_revenue is not None:
        targets["annual_targets"]["revenue"] = int(args.set_revenue)
    if args.set_gross_profit is not None:
        targets["annual_targets"]["gross_profit"] = int(args.set_gross_profit)
    if args.set_operating_profit is not None:
        targets["annual_targets"]["operating_profit"] = int(args.set_operating_profit)
    if args.fiscal_year:
        targets["fiscal_year"] = int(args.fiscal_year)
    if args.fiscal_start_month:
        targets["fiscal_start_month"] = int(args.fiscal_start_month)
    if args.notes:
        targets["notes"] = args.notes

    _save_targets(targets)

    t = targets["annual_targets"]
    print(f"\n=== 目標値 FY{targets['fiscal_year']} (期首: {targets['fiscal_start_month']}月) ===")
    print(f"  売上高:   {_fmt(t['revenue'])} 円")
    print(f"  売上総利益: {_fmt(t['gross_profit'])} 円")
    print(f"  営業利益: {_fmt(t['operating_profit'])} 円")
    if targets.get("notes"):
        print(f"  備考: {targets['notes']}")
    print(f"\n保存先: {TARGETS_FILE}")


# ── エントリーポイント ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="freee 財務分析ツール")
    sub = parser.add_subparsers(dest="command")

    # check
    cp = sub.add_parser("check", help="データ品質チェック（部門未設定・未決済件数）")
    cp.add_argument("--fiscal-year", type=int, help="会計年度 (例: 2025)")

    # pl
    pp = sub.add_parser("pl", help="損益計算書の取得・表示")
    pp.add_argument("--fiscal-year", type=int, help="会計年度")
    pp.add_argument("--start-month", type=int, default=1, help="開始財務月 1-12 (デフォルト: 1)")
    pp.add_argument("--end-month", type=int, default=12, help="終了財務月 1-12 (デフォルト: 12)")

    # cf
    cfp = sub.add_parser("cf", help="キャッシュフロー分析（口座残高 + 月次CF推移）")
    cfp.add_argument("--months", type=int, default=6, help="集計月数 (デフォルト: 6)")

    # summary
    sp = sub.add_parser("summary", help="財務サマリー生成（予測・戦略議論用）")
    sp.add_argument("--fiscal-year", type=int, help="会計年度")

    # targets
    tp = sub.add_parser("targets", help="目標値の表示・更新")
    tp.add_argument("--fiscal-year", type=int)
    tp.add_argument("--fiscal-start-month", type=int)
    tp.add_argument("--set-revenue", type=float, help="年間売上目標（円）")
    tp.add_argument("--set-gross-profit", type=float, help="年間売上総利益目標（円）")
    tp.add_argument("--set-operating-profit", type=float, help="年間営業利益目標（円）")
    tp.add_argument("--notes", help="備考テキスト")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "targets":
        cmd_targets(None, args)
        return

    client = FreeeClient()
    if not client.refresh_token():
        logger.error("freee 認証に失敗しました")
        sys.exit(1)

    dispatch = {
        "check": cmd_check,
        "pl": cmd_pl,
        "cf": cmd_cf,
        "summary": cmd_summary,
    }
    dispatch[args.command](client, args)


if __name__ == "__main__":
    main()
