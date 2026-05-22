# HMC KPI Monitor Configuration

# Fiscal Year Settings
TARGET_FISCAL_YEAR = 2024

# Account Item Mappings (Freee Category Name -> Internal Key)
KPI_MAPPINGS = {
    "Sales": "売上高",
    "COGS": "売上原価",
    "GrossProfit": "売上総損益金額",
    "SGA": "販売管理費",
    "OperatingProfit": "営業損益金額",
}

# COGS Categories (Freee often splits COGS into these)
COGS_CATEGORIES = [
    "売上原価", "期首商品棚卸", "当期商品仕入", 
    "他勘定振替高(商)", "期末商品棚卸", "商品売上原価"
]

# Department Category Definitions
# Format: "CategoryName": { "SheetName": "...", "Ids": [123, 456] }

# ID References based on previous scans:
# おとな学部: 2985715
# おやこ学部: 2985717
# こども学部: 2985716
# 逗子_共通: 1052579
# 逗子_放課後サボール: 1052577
# 俺のヨガ: 2501870
# 大阪_コース: 246400
# 大阪_SSEK: 1424131 (Assumed relevant to Osaka group)
# ナーフ学園: 3381924
# 逗子_イベントその他: 153360 (Assumed "Individual Event")
# 共創プロジェクト: 3114498
# 企業案件: 153355
# 全社共通: 1052584

DEPT_CATEGORIES = {
    "Dept_Individual_Harappa": {
        "name": "個人向け_原っぱ大学",
        "sheet_name": "Dept_Individual_Harappa",
        "ids": [2985715, 2985717, 2985716, 1052579]
    },
    "Dept_Individual_Other": {
        "name": "個人向け_その他定期",
        "sheet_name": "Dept_Individual_Other",
        "ids": [1052577, 2501870, 246400, 1424131] 
    },
    "Dept_Event": {
        "name": "個人向けイベント",
        "sheet_name": "Dept_Event",
        "ids": [153360, 3381924]
    },
    "Dept_Corporate": {
        "name": "企業案件",
        "sheet_name": "Dept_Corporate",
        "ids": [3114498, 153355]
    },
    "Dept_Common": {
        "name": "全社共通",
        "sheet_name": "Dept_Common",
        "ids": [1052584]
    }
}

# Unallocated/Other departments fall into "Dept_Unallocated" sheet automatically.
UNALLOCATED_SHEET_NAME = "Dept_Unallocated"

SECTION_RENAMES = {
    1424131: "大阪_イベント" # Request: "大阪 イベント"
}
