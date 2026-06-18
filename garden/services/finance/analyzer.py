#!/usr/bin/env python3
"""analyzer — freee 財務分析(PL/CF/着地予測)。read-only(HMC apps/finance_analyzer/ 移植)

Garden 化の差分:
- import パス lib.* / TARGETS・REPORTS をサービス相対の絶対パスに
- 書き込みは一切しない(read-only)。月次は種 monthly-finance-review が summary を実行し、
  その出力をもとに Claude が Discord に「対話の投げかけ」を行う(数値+論点)。
- 財務の見方・議論フレーム・指標定義は SKILL Mode A に吸い上げ(継承の核)。

使い方(SKILL Mode A):
    analyzer.py check                  # データ品質(部門未設定・未決済の月別件数)
    analyzer.py pl [--start-month N --end-month N]   # 月次 PL テーブル + CSV
    analyzer.py cf [--months N]        # 口座残高 + 月次CF推移 + 年度末予測
    analyzer.py summary                # 戦略議論用サマリー(JSON + テキスト)
    analyzer.py client-recon           # soil クライアント台帳 × Freee 部門売上の突合(S52)
    analyzer.py targets [--set-revenue ... --set-operating-profit ...]  # 目標値の表示/設定
"""
import os
import sys
import csv
import json
import argparse
from datetime import date, datetime

from dotenv import load_dotenv

from lib.freee_client import FreeeClient
from lib.utils import setup_logger

logger = setup_logger("FinanceAnalyzer")
load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(_BASE_DIR, "reports")
TARGETS_FILE = os.path.join(_BASE_DIR, "config", "targets.json")

SALES_CATEGORIES = {"売上高"}
COGS_CATEGORIES = {
    "売上原価", "期首商品棚卸", "当期商品仕入",
    "他勘定振替高(商)", "期末商品棚卸", "商品売上原価",
}
SGA_CATEGORIES = {"販売管理費"}


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
    return f"{int(n):,}"


def _fiscal_months(fiscal_year, fiscal_start_month, count=12):
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
    out = {"revenue": 0, "cogs": 0, "gross_profit": 0, "sga": 0, "operating_profit": 0}
    if not resp or "trial_pl" not in resp:
        return out
    for item in resp["trial_pl"].get("balances", []):
        cat = item.get("account_category_name", "")
        name = item.get("account_item_name", "")
        if not name:
            continue
        c = item.get("credit_amount", 0)
        d = item.get("debit_amount", 0)
        if cat in SALES_CATEGORIES:
            out["revenue"] += c - d
        elif cat in COGS_CATEGORIES:
            out["cogs"] += d - c
        elif cat in SGA_CATEGORIES:
            out["sga"] += d - c
    out["gross_profit"] = out["revenue"] - out["cogs"]
    out["operating_profit"] = out["gross_profit"] - out["sga"]
    return out


def _print_pl_table(monthly_data, fm_list, targets):
    cols = [f"{y}-{m:02d}" for y, m, _ in fm_list]
    rows = ["売上高", "売上原価", "売上総利益", "販売管理費", "営業利益"]
    key_map = {"売上高": "revenue", "売上原価": "cogs", "売上総利益": "gross_profit",
               "販売管理費": "sga", "営業利益": "operating_profit"}
    col_w = max(10, max((len(c) for c in cols), default=7) + 2)
    row_w = 12
    header = f"{'項目':<{row_w}}" + "".join(f"{c:>{col_w}}" for c in cols) + f"{'累計':>{col_w}}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    totals = {k: 0 for k in key_map.values()}
    for label in rows:
        key = key_map[label]
        values = []
        for col in cols:
            v = monthly_data.get(col, {}).get(key, 0)
            totals[key] += v
            values.append(v)
        line = f"{label:<{row_w}}" + "".join(f"{_fmt(v):>{col_w}}" for v in values)
        line += f"{_fmt(totals[key]):>{col_w}}"
        if label in ("売上総利益", "営業利益"):
            print(sep)
        print(line)
        if label in ("売上総利益", "営業利益"):
            print(sep)
    t = targets.get("annual_targets", {})
    if t.get("revenue"):
        print(f"\n目標: 売上高 {_fmt(t['revenue'])}円 / 進捗: {totals['revenue'] / t['revenue'] * 100:.1f}%")
    if t.get("operating_profit"):
        print(f"目標: 営業利益 {_fmt(t['operating_profit'])}円 / 進捗: {totals['operating_profit'] / t['operating_profit'] * 100:.1f}%")


def cmd_check(client, args):
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
        import calendar as _cal
        last_day = _cal.monthrange(cal_y, cal_m)[1]
        end = f"{cal_y}-{cal_m:02d}-{last_day:02d}"
        deals = client.get_all_deals(start_issue_date=start, end_issue_date=end)
        total = len(deals)
        missing_sec = sum(1 for d in deals for det in d.get("details", []) if not det.get("section_id"))
        unsettled = sum(1 for d in deals if d.get("payment_status") not in ("settled", None))
        total_missing += missing_sec
        flag = " ⚠" if missing_sec > 0 else ""
        print(f"{month_str:<10} {total:>8} {missing_sec:>10}{flag} {unsettled:>8}")
    print(f"\n合計 部門未設定: {total_missing} 件")
    if total_missing > 0:
        print("→ 修正するには: auditor.py scan を実行してください")
    print(f"CHECK_MISSING: {total_missing}")


def cmd_pl(client, args):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    targets = _load_targets()
    fiscal_year = args.fiscal_year or targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)
    fm_list = _fiscal_months(fiscal_year, fiscal_start)
    fm_list = [fm for fm in fm_list if args.start_month <= fm[2] <= args.end_month]
    print(f"\n=== 損益計算書 FY{fiscal_year} (財務月{args.start_month}〜{args.end_month}) ===\n(単位: 円)\n")
    monthly_data = {}
    for cal_y, cal_m, fm_idx in fm_list:
        col = f"{cal_y}-{cal_m:02d}"
        logger.info(f"PL取得中: {col}")
        monthly_data[col] = _parse_pl_response(client.get_trial_pl(fiscal_year, start_month=cal_m, end_month=cal_m))
    _print_pl_table(monthly_data, fm_list, targets)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(REPORTS_DIR, f"pl_fy{fiscal_year}_{ts}.csv")
    key_map = {"売上高": "revenue", "売上原価": "cogs", "売上総利益": "gross_profit",
               "販売管理費": "sga", "営業利益": "operating_profit"}
    cols = [f"{y}-{m:02d}" for y, m, _ in fm_list]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["項目"] + cols + ["累計"])
        for label, key in key_map.items():
            vals = [monthly_data.get(c, {}).get(key, 0) for c in cols]
            writer.writerow([label] + vals + [sum(vals)])
    print(f"\nCSV保存: {csv_path}")
    print(f"PL_CSV: {csv_path}")


def cmd_cf(client, args):
    targets = _load_targets()
    fiscal_year = targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)
    walletables = client.get_walletables()
    bank = [w for w in walletables if w.get("type") in ("bank_account", "credit_card")]
    total_balance = sum(w.get("balance", 0) for w in bank if w.get("balance") is not None)
    print(f"\n=== キャッシュポジション ({date.today()}) ===\n")
    print(f"{'口座名':<30} {'残高':>15}")
    print("-" * 48)
    for w in bank:
        if w.get("balance") is None:
            continue
        print(f"{w.get('name', '不明'):<30} {_fmt(w['balance']):>15} 円")
    print("-" * 48)
    print(f"{'合計':<30} {_fmt(total_balance):>15} 円")
    fm_list = _fiscal_months(fiscal_year, fiscal_start)
    today = date.today()
    actual = [fm for fm in fm_list if date(fm[0], fm[1], 1) <= today][-args.months:]
    if not actual:
        return
    print(f"\n=== 月次営業利益 (CF近似値、直近{len(actual)}ヶ月) ===\n")
    print(f"{'月':<10} {'売上高':>12} {'営業利益':>12}")
    print("-" * 36)
    total_op = 0
    for cal_y, cal_m, _ in actual:
        pl = _parse_pl_response(client.get_trial_pl(fiscal_year, start_month=cal_m, end_month=cal_m))
        total_op += pl["operating_profit"]
        print(f"{cal_y}-{cal_m:02d}   {_fmt(pl['revenue']):>12} {_fmt(pl['operating_profit']):>12}")
    print("-" * 36)
    avg = total_op / len(actual)
    print(f"{'平均月次利益':<10} {_fmt(avg):>25}")
    months_remaining = 12 - len([fm for fm in fm_list if date(fm[0], fm[1], 1) <= today])
    projected = total_balance + avg * months_remaining
    print(f"\n=== CF予測 (残り{months_remaining}ヶ月、月平均 {_fmt(avg)}円) ===")
    print(f"  現在残高: {_fmt(total_balance)} 円")
    print(f"  年度末予測残高: {_fmt(projected)} 円")
    if projected < 0:
        bal, deficit = total_balance, None
        for fm in fm_list:
            if date(fm[0], fm[1], 1) > today:
                bal += avg
                if bal < 0 and deficit is None:
                    deficit = f"{fm[0]}-{fm[1]:02d}"
        if deficit:
            print(f"  ⚠️  {deficit} に資金ショートの可能性があります")


def cmd_summary(client, args):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    targets = _load_targets()
    fiscal_year = args.fiscal_year or targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)
    fm_list = _fiscal_months(fiscal_year, fiscal_start)
    today = date.today()
    actual = [fm for fm in fm_list if date(fm[0], fm[1], 1) <= today]
    print(f"FY{fiscal_year} のPLデータを取得中...")
    monthly_pl = {}
    for cal_y, cal_m, _ in actual:
        monthly_pl[f"{cal_y}-{cal_m:02d}"] = _parse_pl_response(
            client.get_trial_pl(fiscal_year, start_month=cal_m, end_month=cal_m))
    ytd = {"revenue": 0, "cogs": 0, "gross_profit": 0, "sga": 0, "operating_profit": 0}
    for v in monthly_pl.values():
        for k in ytd:
            ytd[k] += v[k]
    walletables = client.get_walletables()
    bank = [w for w in walletables if w.get("type") in ("bank_account", "credit_card") and w.get("balance") is not None]
    total_cash = sum(w.get("balance", 0) for w in bank)
    months_elapsed = len(actual)
    months_remaining = 12 - months_elapsed
    t = targets.get("annual_targets", {})
    projected = {k: ytd[k] + (ytd[k] / months_elapsed * months_remaining if months_elapsed else 0) for k in ytd}
    summary_data = {
        "generated_at": str(today), "fiscal_year": fiscal_year, "fiscal_start_month": fiscal_start,
        "months_elapsed": months_elapsed, "months_remaining": months_remaining, "targets": t,
        "ytd_pl": ytd, "monthly_pl": monthly_pl, "projected_full_year_pl": projected,
        "current_cash": {"total": total_cash,
                         "walletables": [{"name": w.get("name"), "balance": w.get("balance")} for w in bank]},
        "monthly_avg": {"revenue": ytd["revenue"] / months_elapsed if months_elapsed else 0,
                        "operating_profit": ytd["operating_profit"] / months_elapsed if months_elapsed else 0},
    }
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(REPORTS_DIR, f"summary_fy{fiscal_year}_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*55}")
    print(f"  財務サマリー FY{fiscal_year}  ({months_elapsed}ヶ月経過 / 残り{months_remaining}ヶ月)")
    print(f"{'='*55}")
    print("\n【現金・預金残高】")
    for w in bank:
        print(f"  {w['name']:<25} {_fmt(w['balance']):>15} 円")
    print(f"  {'合計':<25} {_fmt(total_cash):>15} 円")
    print(f"\n【PL実績 ({months_elapsed}ヶ月累計)】")
    for label, key in [("売上高", "revenue"), ("売上原価", "cogs"), ("売上総利益", "gross_profit"),
                       ("販売管理費", "sga"), ("営業利益", "operating_profit")]:
        tgt = t.get(key, 0) if key in ("revenue", "operating_profit") else 0
        ratio = f"  目標比 {ytd[key] / tgt * 100:.1f}%" if tgt else ""
        print(f"  {label:<12} {_fmt(ytd[key]):>15} 円{ratio}")
    print("\n【年度末予測 (現ペース継続)】")
    for label, key in [("売上高予測", "revenue"), ("営業利益予測", "operating_profit")]:
        pval = projected[key]
        tgt = t.get(key, 0)
        gap = f"  目標差 {_fmt(tgt - pval)}円不足" if tgt and pval < tgt else (f"  目標差 {_fmt(pval - tgt)}円超過" if tgt else "")
        print(f"  {label:<12} {_fmt(pval):>15} 円{gap}")
    print(f"\n詳細JSON: {json_path}")
    print(f"SUMMARY_JSON: {json_path}")


# ============================================================
# client-recon — soil クライアント台帳 × Freee 部門売上の突合(S52)
#   Freee の売上は取引先タグなし → 部門「企業案件 / 共創プロジェクト」で toB を識別。
#   soil の案件 frontmatter(計上月/amount/payment_status/freee_partner_role/freee反映)を
#   月別に合算し、Freee 実績と並べて「確認すべき差」を投げかけ用に出す。read-only。
# ============================================================
import glob
import re as _re

TOB_SECTION_NAMES = {"企業案件", "共創プロジェクト"}


def _soil_clients_dir():
    d = os.getenv("SOIL_CLIENTS_DIR")
    if d:
        return d
    # ローカル repo レイアウトのフォールバック(VPS は .env で SOIL_CLIENTS_DIR を指定)
    return os.path.normpath(os.path.join(_BASE_DIR, "..", "..", "soil", "clients"))


def _parse_frontmatter(path):
    """README.md の YAML frontmatter を最小パース(日本語キー対応・コメント除去)。"""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return {}
    m = _re.match(r"^---\n(.*?)\n---", text, _re.S)
    if not m:
        return {}
    d = {}
    for line in m.group(1).splitlines():
        mm = _re.match(r"^([^\s:#][^:]*):\s*(.*?)\s*$", line)
        if mm:
            v = _re.sub(r"\s+#.*$", "", mm.group(2)).strip().strip('"')
            d[mm.group(1).strip()] = v
    return d


def _read_client_projects(soil_dir):
    rows = []
    for p in sorted(glob.glob(os.path.join(soil_dir, "*", "projects", "*", "README.md"))):
        fm = _parse_frontmatter(p)
        if fm.get("type") != "soil_project":
            continue
        rows.append({
            "client": fm.get("client", ""),
            "project": os.path.basename(os.path.dirname(p)),
            "amount": fm.get("amount", ""),
            "month": fm.get("計上月", ""),
            "確度": fm.get("確度", ""),
            "payment_status": fm.get("payment_status", ""),
            "role": fm.get("freee_partner_role", "請求先"),
            "freee反映": fm.get("freee反映", ""),
            "path": p,
        })
    return rows


def _amount_int(s):
    s = (s or "").replace(",", "")
    m = _re.search(r"\d+", s)
    return int(m.group()) if m else None


def _freee_tob_income_by_month(client, fiscal_year, fiscal_start):
    """企業案件・共創プロジェクト 部門の income を月別に合算。"""
    secs = client.get_sections() or []
    tob_ids = {s["id"]: s["name"] for s in secs if s.get("name") in TOB_SECTION_NAMES}
    fm_list = _fiscal_months(fiscal_year, fiscal_start)
    start = f"{fm_list[0][0]}-{fm_list[0][1]:02d}-01"
    import calendar as _cal
    ly, lm = fm_list[-1][0], fm_list[-1][1]
    end = f"{ly}-{lm:02d}-{_cal.monthrange(ly, lm)[1]:02d}"
    deals = client.get_all_deals(start_issue_date=start, end_issue_date=end)
    by_month = {}
    for d in deals:
        if d.get("type") != "income":
            continue
        mon = (d.get("issue_date") or "")[:7]
        for det in d.get("details", []):
            sid = det.get("section_id")
            if sid in tob_ids:
                slot = by_month.setdefault(mon, {"企業案件": 0, "共創プロジェクト": 0})
                slot[tob_ids[sid]] += det.get("amount", 0)
    return by_month, tob_ids


def cmd_client_recon(client, args):
    targets = _load_targets()
    fiscal_year = args.fiscal_year or targets["fiscal_year"]
    fiscal_start = targets.get("fiscal_start_month", 10)
    soil_dir = _soil_clients_dir()
    projects = _read_client_projects(soil_dir)
    by_month, tob_ids = _freee_tob_income_by_month(client, fiscal_year, fiscal_start)

    print(f"\n{'='*60}")
    print(f"  クライアント突合 FY{fiscal_year}  (soil × Freee 部門売上)")
    print(f"{'='*60}")
    print(f"soil: {soil_dir}  案件 {len(projects)} 件")
    print(f"Freee toB 部門: {', '.join(tob_ids.values()) or '(該当部門なし)'}")

    # --- Freee 実績(部門別・月次)---
    print("\n【Freee 売上(toB 部門・月別)】")
    tot_e = tot_k = 0
    for mon in sorted(by_month):
        e = by_month[mon].get("企業案件", 0)
        k = by_month[mon].get("共創プロジェクト", 0)
        tot_e += e
        tot_k += k
        print(f"  {mon}  企業案件 {_fmt(e):>12}  共創 {_fmt(k):>10}")
    print(f"  {'計':<7} 企業案件 {_fmt(tot_e):>12}  共創 {_fmt(tot_k):>10}  (合計 {_fmt(tot_e + tot_k)})")

    # --- soil 期待(売上のみ。支払先=外注費は除外)---
    print("\n【soil 案件ステータス(売上案件)】")
    flags = []
    soil_total = 0
    fy_start = f"{fiscal_year}-{fiscal_start:02d}"  # 例 2025-10。これより前の計上月は期外
    for r in projects:
        if r["role"] == "支払先":
            continue  # 京急外注費=コスト、売上でない
        amt = _amount_int(r["amount"])
        rohan = r["freee反映"]
        ps = r["payment_status"]
        # confirmed: 反映=true / 確認済 / 計上済 / 前受金(三井=入金済で月次取り崩し)
        confirmed = (rohan.startswith("true") or "確認済" in rohan or "計上済" in rohan
                     or "前受金" in rohan or "前受金" in ps)
        billed = ("請求済" in ps) or ("入金" in ps)
        waiting = ("未入金" in ps) or ("入金予定" in ps) or ("支払い手配" in ps)
        # 計上月が当期(fy_start)より前 = 期外 → FY 投げかけの対象外
        mon_match = _re.search(r"\d{4}-\d{2}", r["month"] or "")
        out_of_period = bool(mon_match) and mon_match.group() < fy_start
        if amt:
            soil_total += amt
        if out_of_period:
            continue
        if waiting:
            flags.append(f"  ⏳ {r['client']}/{r['project']}: 入金待ち({ps})")
        elif billed and not confirmed:
            flags.append(f"  ⚠️ {r['client']}/{r['project']}: 請求済だが freee反映 未確定 → 入金/記帳を確認")
    # 案件一覧(簡潔)
    for r in sorted(projects, key=lambda x: (x["client"], x["project"])):
        if r["role"] == "支払先":
            print(f"  · {r['client']}/{r['project']}  [支払先=外注費・売上対象外]")
            continue
        print(f"  · {r['client']}/{r['project']}  計上月={r['month'] or '—'} 反映={r['freee反映'] or '—'}")

    print("\n【投げかけ候補(要確認の差)】")
    if flags:
        for f in flags:
            print(f)
    else:
        print("  (なし)")

    print("\n【ヒント】")
    print("  ・Freee 売上は取引先タグなし=部門で識別。soil 額は税抜・Freee は税込(×1.1 で概算比較)。")
    print("  ・前受金(三井)は入金済でも月次計上 / 利益なし(ゴンチャ茶畑)は売上ゼロ扱い。")
    print(f"CLIENT_RECON_DONE: soil={len(projects)} freee_企業案件={_fmt(tot_e)} freee_共創={_fmt(tot_k)}")


def cmd_targets(args):
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


def main():
    parser = argparse.ArgumentParser(description="finance analyzer — freee 財務分析(read-only)")
    sub = parser.add_subparsers(dest="command", required=True)
    cp = sub.add_parser("check")
    cp.add_argument("--fiscal-year", type=int)
    pp = sub.add_parser("pl")
    pp.add_argument("--fiscal-year", type=int)
    pp.add_argument("--start-month", type=int, default=1)
    pp.add_argument("--end-month", type=int, default=12)
    cfp = sub.add_parser("cf")
    cfp.add_argument("--months", type=int, default=6)
    spp = sub.add_parser("summary")
    spp.add_argument("--fiscal-year", type=int)
    crp = sub.add_parser("client-recon")
    crp.add_argument("--fiscal-year", type=int)
    tp = sub.add_parser("targets")
    tp.add_argument("--fiscal-year", type=int)
    tp.add_argument("--fiscal-start-month", type=int)
    tp.add_argument("--set-revenue", type=float)
    tp.add_argument("--set-gross-profit", type=float)
    tp.add_argument("--set-operating-profit", type=float)
    tp.add_argument("--notes")

    args = parser.parse_args()
    if args.command == "targets":
        cmd_targets(args)
        return
    client = FreeeClient()
    if not client.refresh_token():
        logger.error("freee 認証に失敗しました")
        sys.exit(1)
    {"check": cmd_check, "pl": cmd_pl, "cf": cmd_cf, "summary": cmd_summary,
     "client-recon": cmd_client_recon}[args.command](client, args)


if __name__ == "__main__":
    main()
