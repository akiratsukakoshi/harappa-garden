import sys
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from modules.freee_client import FreeeClient
from modules.utils import setup_logger
from apps.kpi_monitor.sheet_syncer import SheetSyncer
from apps.kpi_monitor.config import TARGET_FISCAL_YEAR, KPI_MAPPINGS, DEPT_CATEGORIES, UNALLOCATED_SHEET_NAME, SECTION_RENAMES, COGS_CATEGORIES

logger = setup_logger("KPIMonitor")

def get_fiscal_months(start_year, start_month):
    """
    Returns a list of (year, month) tuples for a fiscal year starting at start_year-start_month.
    E.g. 2024-10 -> [(2024,10), (2024,11)... (2025,9)]
    """
    months = []
    y = start_year
    m = start_month
    for _ in range(12):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months

def fetch_and_structure_data(client, term_start_str):
    """
    Fetches data for Previous FY and Current FY.
    term_start_str: "202510" -> Current starts Oct 2025.
    Previous starts Oct 2024.
    """
    
    # Parse Start
    start_y = int(term_start_str[:4])
    start_m = int(term_start_str[4:])
    
    prev_y = start_y - 1
    
    # Define Periods
    periods = [
        {"label": "Prev", "fy": prev_y, "months": get_fiscal_months(prev_y, start_m)},
        {"label": "Curr", "fy": start_y, "months": get_fiscal_months(start_y, start_m)}
    ]
    
    monthly_snapshots = {} # Key: "YYYY-MM"
    master_accounts = set()
    master_accounts_order = [] 
    master_item_details = {} 
    
    for period in periods:
        # Note: We use period["fy"] for API year, assuming it matches Freee Fiscal Year definition.
        # If Company starts in Oct, '2024' usually means the term starting Oct 2024.
        fy_year = period["fy"]
        logger.info(f"Fetching FY{fy_year} ({period['label']})...")
        
        # start_month=1 means First Month of Fiscal Year (Oct)
        for m_idx in range(1, 13):
            # Calculate actual Label
            cal_y, cal_m = period["months"][m_idx-1]
            month_label = f"{cal_y}-{cal_m:02d}"
            
            logger.info(f"Fetching {month_label} (FY Month {m_idx})...")
            
            try:
                # API Call
                pl_resp = client.get_trial_pl(fy_year, start_month=m_idx, end_month=m_idx, 
                                              breakdown_display_type="section")
                
                if not (pl_resp and 'trial_pl' in pl_resp and 'balances' in pl_resp['trial_pl']):
                    # Initialize empty
                    monthly_snapshots[month_label] = {"Total": {}, "Sections": {}, "SectionNames": {}}
                    continue

                balances = pl_resp['trial_pl']['balances']
                
                month_accum = {
                    "Total": {},
                    "Sections": {}, 
                    "SectionNames": {} 
                }

                def add_val(target_dict, key, val):
                    target_dict[key] = target_dict.get(key, 0) + val

                # Breakdown Parsing
                for item in balances:
                    name = item.get('account_item_name')
                    if not name: continue
                    cat = item.get('account_category_name')
                    
                    if 'sections' in item:
                        for sec in item['sections']:
                            sid = sec['id']
                            sname = sec['name']
                            month_accum["SectionNames"][sid] = sname
                            
                            sc = sec.get('credit_amount', 0)
                            sd = sec.get('debit_amount', 0)
                            sval = 0
                            
                            if cat == KPI_MAPPINGS["Sales"] or cat == KPI_MAPPINGS["GrossProfit"] or cat == KPI_MAPPINGS["OperatingProfit"]:
                                sval = sc - sd
                            elif cat in COGS_CATEGORIES or cat == KPI_MAPPINGS["SGA"]:
                                sval = sd - sc
                            else:
                                sval = sd - sc
                            
                            if sid not in month_accum["Sections"]: month_accum["Sections"][sid] = {}
                            add_val(month_accum["Sections"][sid], name, sval)

                # Total Fetch (Separate Call)
                pl_total = client.get_trial_pl(fy_year, start_month=m_idx, end_month=m_idx)
                if pl_total and 'trial_pl' in pl_total and 'balances' in pl_total['trial_pl']:
                    for item in pl_total['trial_pl']['balances']:
                        name = item.get('account_item_name')
                        if not name: continue
                        cat = item.get('account_category_name', '')
                        
                        if name not in master_accounts:
                            master_accounts.add(name)
                            master_accounts_order.append(name)
                            master_item_details[name] = cat
                            
                        c = item.get('credit_amount', 0)
                        d = item.get('debit_amount', 0)
                        val = 0
                        if cat == KPI_MAPPINGS["Sales"] or cat == KPI_MAPPINGS["GrossProfit"] or cat == KPI_MAPPINGS["OperatingProfit"]:
                            val = c - d
                        elif cat in COGS_CATEGORIES or cat == KPI_MAPPINGS["SGA"]:
                            val = d - c
                        else:
                            val = d - c
                        month_accum["Total"][name] = val
                    
                monthly_snapshots[month_label] = month_accum

            except Exception as e:
                logger.error(f"Error fetching {month_label}: {e}")
                # Use empty
                monthly_snapshots[month_label] = {"Total": {}, "Sections": {}, "SectionNames": {}}

    return master_accounts_order, monthly_snapshots, master_item_details, periods

def build_dataframes(master_index, monthly_snapshots, master_item_details, periods):
    """
    Builds DF with cols: [PrevFY Months] [PrevTotal] [CurrFY Months] [CurrTotal]
    """
    # Create Column List
    # Requested Order: [PrevMonths] [CurrMonths] [PrevTotals] [CurrTotals]
    
    month_cols_ordered = []
    total_cols_ordered = []
    period_cols_map = {} 
    
    for p in periods:
        p_label = p["label"]
        p_fy = p["fy"]
        p_cols = []
        for y, m in p["months"]:
            col_label = f"{y}-{m:02d}"
            month_cols_ordered.append(col_label)
            p_cols.append(col_label)
        
        total_col = f"{p_fy}年度合計"
        total_cols_ordered.append(total_col)
        period_cols_map[total_col] = p_cols
        
    cols = month_cols_ordered + total_cols_ordered

    # Prepare Master Index Order
    g_sales = []
    g_cogs = []
    g_sga = []
    g_other = []
    def get_cat(item): return master_item_details.get(item, "")

    for item in master_index:
        c = get_cat(item)
        if c == KPI_MAPPINGS["Sales"]: g_sales.append(item)
        elif c in COGS_CATEGORIES: g_cogs.append(item)
        elif c == KPI_MAPPINGS["SGA"]: g_sga.append(item)
        else: g_other.append(item)

    display_rows_full = []
    display_rows_full.extend(g_sales)
    display_rows_full.extend(g_cogs)
    display_rows_full.append("売上総利益")
    display_rows_full.extend(g_sga)
    display_rows_full.append("営業利益")
    display_rows_full.extend(g_other)
    
    display_rows_bottom = []
    display_rows_bottom.extend(g_sales)
    display_rows_bottom.extend(g_cogs)
    display_rows_bottom.append("売上総利益")
    display_rows_bottom.extend(g_sga)
    display_rows_bottom.append("営業利益")
    
    def get_val(data_dict, item_name): return data_dict.get(item_name, 0)

    def calc_profits(d_dict):
        s = sum(get_val(d_dict, i) for i in g_sales)
        c = sum(get_val(d_dict, i) for i in g_cogs)
        ga = sum(get_val(d_dict, i) for i in g_sga)
        gp = s - c
        op = gp - ga
        return s, c, gp, ga, op

    dfs = {}
    
    # 1. Total / Unallocated
    for t_name in ["Total", "Unallocated"]:
        df = pd.DataFrame(index=display_rows_full, columns=cols).fillna(0)
        
        for col in cols:
            if "合計" in col: continue
            
            snap = monthly_snapshots.get(col, {"Total": {}, "Sections": {}})
            
            if t_name == "Total":
                 for item in display_rows_full:
                    if item in ["売上総利益", "営業利益"]: continue
                    val = snap["Total"].get(item, 0)
                    df.at[item, col] = val
                    
                 s, c, gp, ga, op = calc_profits(snap["Total"])
                 df.at["売上総利益", col] = gp
                 df.at["営業利益", col] = op
                 
            else: # Unallocated
                sec_sum = {}
                # Only subtract mapped sections
                for info in DEPT_CATEGORIES.values():
                    for sid in info['ids']:
                         sdata = snap["Sections"].get(sid, {})
                         for k, v in sdata.items():
                             sec_sum[k] = sec_sum.get(k, 0) + v
                
                for item in display_rows_full:
                    if item in ["売上総利益", "営業利益"]: continue
                    tot = snap["Total"].get(item, 0)
                    sec = sec_sum.get(item, 0)
                    df.at[item, col] = tot - sec
                
                # Recalc Profits
                # Construct temp dict for calc
                un_dict = {}
                for item in display_rows_full:
                    if item in ["売上総利益", "営業利益"]: continue
                    un_dict[item] = df.at[item, col]
                s, c, gp, ga, op = calc_profits(un_dict)
                df.at["売上総利益", col] = gp
                df.at["営業利益", col] = op

        dfs[t_name] = df
        
    # 2. Departments
    for cat_key, info in DEPT_CATEGORIES.items():
        sheet_rows = []
        
        # Header Construction
        for sec_id in info['ids']:
            sec_name_found = f"Section_{sec_id}"
            if sec_id in SECTION_RENAMES:
                sec_name_found = SECTION_RENAMES[sec_id]
            else:
                 # Lookup
                 for snap in monthly_snapshots.values():
                     if sec_id in snap.get("SectionNames", {}):
                         sec_name_found = snap["SectionNames"][sec_id]
                         break
            
            sheet_rows.append(f"【{sec_name_found}】")
            sheet_rows.extend([
                f"{sec_name_found}::売上高",
                f"{sec_name_found}::売上原価",
                f"{sec_name_found}::売上総利益",
                f"{sec_name_found}::販売管理費",
                f"{sec_name_found}::営業利益",
                ""
            ])
        sheet_rows.append("【部門合計・詳細】")
        sheet_rows.extend(display_rows_bottom)
        
        df = pd.DataFrame(index=sheet_rows, columns=cols).fillna(0)
        
        # Fill Data
        for col in cols:
            if "合計" in col: continue
            
            snap = monthly_snapshots.get(col, {"Sections": {}, "SectionNames": {}})
            cat_accum = {}
            
            # Sections
            for sec_id in info['ids']:
                sec_data = snap["Sections"].get(sec_id, {})
                s, c, gp, ga, op = calc_profits(sec_data)
                
                sec_name_found = f"Section_{sec_id}"
                if sec_id in SECTION_RENAMES: sec_name_found = SECTION_RENAMES[sec_id]
                else: 
                     sec_name_found = snap["SectionNames"].get(sec_id, f"Section_{sec_id}")
                     if sec_name_found == f"Section_{sec_id}":
                         for snap_s in monthly_snapshots.values():
                             if sec_id in snap_s.get("SectionNames", {}):
                                 sec_name_found = snap_s["SectionNames"][sec_id]
                                 break
                
                df.at[f"{sec_name_found}::売上高", col] = s
                df.at[f"{sec_name_found}::売上原価", col] = c
                df.at[f"{sec_name_found}::売上総利益", col] = gp
                df.at[f"{sec_name_found}::販売管理費", col] = ga
                df.at[f"{sec_name_found}::営業利益", col] = op
                
                for k, v in sec_data.items():
                    cat_accum[k] = cat_accum.get(k, 0) + v
                    
            # Category Bottom
            for item in display_rows_bottom:
                if item in ["売上総利益", "営業利益"]: continue
                df.at[item, col] = cat_accum.get(item, 0)
                
            s, c, gp, ga, op = calc_profits(cat_accum)
            df.at["売上総利益", col] = gp
            df.at["営業利益", col] = op
            
        dfs[cat_key] = df
        
    # --- Annual Totals ---
    for df in dfs.values():
        for tot_col, sub_cols in period_cols_map.items():
            df[tot_col] = df[sub_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1)

    return dfs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("term_start", help="Start of current term YYYYMM (e.g. 202510)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    logger.info(f"Starting Multi-Year PL logic. Term Start: {args.term_start}")
    
    client = FreeeClient()
    if not client.refresh_token():
        logger.error("Auth failed")
        return

    logger.info("Step 1: Fetching and Structuring Data...")
    master_index, monthly_snapshots, master_item_details, periods = fetch_and_structure_data(client, args.term_start)
    
    logger.info("Step 2: Building DataFrames (Split Layout)...")
    dfs = build_dataframes(master_index, monthly_snapshots, master_item_details, periods)
    
    # Validation
    logger.info("Step 3: Validation...")
    
    all_months = sorted(monthly_snapshots.keys())
    valid_all = True
    for month in all_months:
        if month not in dfs["Total"].columns: continue 
        
        total_op = dfs["Total"].at["営業利益", month]
        
        cats_op_sum = 0
        for cat_key in DEPT_CATEGORIES.keys():
            cats_op_sum += dfs[cat_key].at["営業利益", month]
        
        unallocated_op = dfs["Unallocated"].at["営業利益", month]
        
        checksum = cats_op_sum + unallocated_op
        diff = abs(total_op - checksum)
        
        if diff > 1:
            logger.error(f"Validation FAILED for {month}: TotalOP {total_op:.2f} != Sum {checksum:.2f} (Diff: {diff:.2f})")
            valid_all = False
            
    if valid_all:
        logger.info(">>> VALIDATION SUCCESS.")
    else:
        logger.error(">>> VALIDATION FAILED.")
        
    if args.dry_run: return

    # Sync
    logger.info("Step 4: Syncing...")
    syncer = SheetSyncer()
    
    # Map SheetName -> DF
    sync_targets = [("Dashboard", dfs["Total"]), (UNALLOCATED_SHEET_NAME, dfs["Unallocated"])]
    for k, info in DEPT_CATEGORIES.items():
        sync_targets.append((info['sheet_name'], dfs[k]))
        
    for sheet_name, df in sync_targets:
        try:
            # 1. Prepare Row Headers (Column A)
            display_headers = []
            for idx_val in df.index:
                s = str(idx_val)
                if "::" in s:
                    display_headers.append(s.split("::")[-1])
                else:
                    display_headers.append(s)
            
            syncer.sync_row_headers(sheet_name, display_headers)
            
            # 2. Prepare Value Matrix
            data_matrix = []
            for r_idx in range(len(df.index)):
                row_vals = []
                for col_idx in range(len(df.columns)):
                    val = df.iat[r_idx, col_idx]
                    if pd.isna(val) or val == float('inf') or val == float('-inf'): val = 0
                    else: val = float(val)
                    row_vals.append(val)
                data_matrix.append(row_vals)
                
            syncer.update_data_block(sheet_name, data_matrix, start_row=2, start_col=2)
            
            # 3. Header Sync (Column Titles to Row 1)
            # Row 1 Headers: ["項目", Col1, Col2...]
            header_vals = ["項目"] + list(df.columns)
            syncer.update_data_block(sheet_name, [header_vals], start_row=1, start_col=1)
            
        except Exception as e:
            logger.error(f"Failed to sync {sheet_name}: {e}")
            raise e
            
    logger.info("Sync Complete.")

if __name__ == "__main__":
    main()
