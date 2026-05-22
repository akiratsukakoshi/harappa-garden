# Shift Manager System Specification

## 1. Overview
HMC Shift Manager は、原っぱ大学のシフト管理から月次稼働時間集計・支払処理連携までを担うサブシステム。Google Spreadsheet を UI として、人間が見やすいUIシートとシステム用DBシートを同期させる Seed-to-Master モデルを採用。月次の支払処理 (invoice_processor / 人事労務freee) と密に連携する。

## 2. Architecture
*   **Platform:** Google Spreadsheet + Python (gspread, pandas, requests)
*   **App Location:** `apps/shift_manager/`
*   **External APIs:**
  *   Freee 会計 API (取引先・部門マスタ)
  *   Freee 人事労務 API (従業員・勤怠登録) — `modules/freee_hr_client/`

## 3. Spreadsheet 構成

### UI レイヤー（人間用）
*   **`HMC_File_Annual`**: 年次予定 (UI_Annual_Planner_YYYY)
*   **`HMC_Monthly_UI` (プログラムカレンダー新)**: 月次運用シート
*   **`HMC_Shift_Form_Sheet`**: シフト募集Googleフォーム
*   **`HMC_Shift_Work` (シフト調整)**: フォーム回答集約 (Shift_Work_YYYY-MM)
*   **`HMC_Working_Hours` (スタッフ稼働時間)**: 月次稼働時間集計 (YYYY-MM_稼働時間)

### DB レイヤー（システム用、`HMC_Backend_DB`）
*   **`DB_Master_Events`**: プログラム定義（ID, 名称, 標準時間, 募集対象）
*   **`DB_Master_Staff`**: スタッフマスタ（Staff_ID, Name, Email, Type）
*   **`DB_Master_Categories`**: カテゴリ定義
*   **`DB_Master_Nicknames`**: ニックネーム照合 + PaymentType + HR_Employee_ID
*   **`DB_Shift_Logs`**: シフト操作ログ

### DB_Master_Nicknames カラム構成

| 列 | 名称 | 用途 |
|---|---|---|
| A | ニックネーム | カンマ区切り対応 (例: `ゆーじ, ユージ`) |
| B | 正式名称 | Freeeパートナー名と一致 |
| C | Freee_ID | 会計freee の取引先ID |
| D | 備考 | 自由記入 |
| E | PaymentType | `給与` / `業務委託` / `追加` |
| F | HR_Employee_ID | 人事労務freee の従業員ID |

## 4. Key Logic

### Annual Calendar Sync
*   **Source:** `UI_Annual_Planner_YYYY`
*   **Destination:** `DB_Master_Events`
*   **Script:** `apps/shift_manager/logic/annual_to_db.py`
*   **Trigger:** Manual (`--year YYYY`)

### Monthly Sheet Generation
*   **Source:** `DB_Master_Events` (target month)
*   **Destination:** `HMC_Monthly_UI` (新タブ `YYYY-MM`)
*   **Script:** `apps/shift_manager/logic/db_to_monthly.py`
*   **Trigger:** Manual (`--month YYYY-MM`)
*   **Note:** 既存タブは上書き

### Monthly Sheet Sync Back
*   **Source:** `HMC_Monthly_UI` (`YYYY-MM`)
*   **Destination:** `DB_Master_Events`
*   **Script:** `apps/shift_manager/logic/monthly_to_db.py`

### Staff Master Sync
*   **Source:** Freee API (Partners/Employees) + `data/manual_staff.csv`
*   **Destination:** `DB_Master_Staff`
*   **Script:** `apps/shift_manager/logic/sync_staff_master.py`

### Form Generation
*   **Source:** `HMC_Monthly_UI` (アンケート列がチェックされた行)
*   **Destination:** Google Forms (`HMC_Shift_Form_Sheet` フォームを更新)
*   **Script:** `apps/shift_manager/logic/generate_shift_form.py`

### Response Aggregation
*   **Source:** Google Forms 回答
*   **Destination:** `HMC_Shift_Work` (`Shift_Work_YYYY-MM`)
*   **Script:** `apps/shift_manager/logic/aggregate_responses.py`
*   **Logic:**
  *   イベント (`Date+Loc+Cat`) 別に列を生成
  *   スタッフ名: フォーム回答の「お名前」優先、未入力時はメール
  *   NG回答は赤色強調

### Working Hours Generation (新)
*   **Source:** `HMC_Monthly_UI` (`YYYY-MM`) + `DB_Master_Nicknames`
*   **Destination:** `HMC_Working_Hours` (`YYYY-MM_稼働時間`)
*   **Script:** `apps/shift_manager/logic/generate_working_hours.py`
*   **Trigger:** Manual (`--month YYYY-MM`)
*   **シート構成**:
  - A列: スタッフ名
  - B〜O列: 日付別稼働時間 (TIME format, `[h]:mm`)
  - P〜U列: カテゴリ別時間小計 (SUMPRODUCT formula)
  - V列: 合計時間 (SUM)
  - W〜AB列: カテゴリ別金額 (ROUND(時間 × 24 × 時給単価))
  - AC列: 合計金額 (SUM)
  - AD列: 区分 (PaymentType, `DB_Master_Nicknames.E列` から pre-fill)
*   **時給単価**: `apps/shift_manager/section_mapping.json` の `hourly_rate` (既定 1250円)
*   **ニックネーム照合**: `DB_Master_Nicknames` から `nick → official_name` マッピング
*   **放サボ列**: オレンジ色のセルで手入力を促す（人により稼働時間が異なるため自動入力しない）

### External Staff CSV Export (新)
*   **Source:** `HMC_Working_Hours` (`YYYY-MM_稼働時間`, AD列=`追加`)
*   **Destination:** `data/invoice_processor/review/external_staff_YYYYMM.csv`
*   **Script:** `apps/shift_manager/logic/export_external_staff.py`
*   **Trigger:** Manual (`--month YYYY-MM`)
*   **挙動**:
  - AD列=`追加` のスタッフを抽出
  - カテゴリ別金額 (W列以降) で金額>0 の部門ごとに1行展開
  - 部門名は `section_mapping.json` で通称→Freee正式部門名に変換
  - `partner_id` は Freee 取引先から正式名称で照合
  - 出力形式は invoice_processor の register コマンドが期待する形式
*   **旧フォーマット互換**: 4月以前の手動編集シートでも、行3のラベルから列構造を推測

### Payroll Registration (新)
*   **Source:** `HMC_Working_Hours` (`YYYY-MM_稼働時間`, AD列=`給与`) + `DB_Master_Nicknames.F列` (HR_Employee_ID)
*   **Destination:** Freee 人事労務 API (`PUT /api/v1/employees/{emp_id}/work_records/{date}`)
*   **Script:** `apps/shift_manager/logic/register_payroll.py`
*   **Trigger:** Manual (`--month YYYY-MM [--dry-run] [--force]`)
*   **挙動**:
  - AD列=`給与` のスタッフの日別稼働分を抽出
  - HR_Employee_ID で `DB_Master_Nicknames` と照合
  - 各日 9:00 開始の `clock_in_at` / `clock_out_at` (= 9:00 + 稼働分数) を PUT
  - `day_pattern: "normal_work"`, `use_default_work_pattern: false`
*   **既存データ保護**: 該当日に既に `clock_in_at` が記録されている場合はスキップ（`--force` で強制上書き）
*   **時給×時間の給与計算**: 人事労務freee 側で自動実行（給与登録は不要）

## 5. 設定ファイル

### `apps/shift_manager/config_ids.json`
スプレッドシートID群:
```json
{
  "annual_id": "...",        # HMC_File_Annual
  "monthly_ui_id": "...",    # HMC_Monthly_UI
  "backend_db_id": "...",    # HMC_Backend_DB
  "shift_form_id": "...",    # HMC_Shift_Form_Sheet
  "shift_work_id": "...",    # HMC_Shift_Work
  "working_hours_id": "..."  # HMC_Working_Hours (新)
}
```

### `apps/shift_manager/section_mapping.json`
部門マッピング + 時給:
```json
{
  "mapping": {
    "放サボ": "逗子_放課後サボール",
    "おやこ学部": "おやこ学部",
    "おとな学部": "おとな学部",
    "こども学部": "こども学部",
    "企業案件": "企業案件",
    "共創": "共創プロジェクト"
  },
  "default_account_item": "外注費",
  "hourly_rate": 1250
}
```

### `.env` (人事労務freee連携)
```
FREEE_HR_CLIENT_ID=...
FREEE_HR_CLIENT_SECRET=...
FREEE_HR_COMPANY_ID=...
FREEE_HR_BUSINESS_NO=...
```

### `modules/freee_hr_client/token.json`
OAuth tokenの保存先（自動更新）。

## 6. 関連モジュール

### `modules/freee_hr_client/`
*   `client.py`: FreeeHRClient — 人事労務freee API クライアント
*   `token.json`: OAuth トークン保存先
*   **API base**: `https://api.freee.co.jp/hr/api/v1`
*   **対応エンドポイント**:
  *   `GET /companies` — 事業所リスト
  *   `GET /employees` — 従業員リスト
  *   `GET /employees/{emp_id}/work_records/{date}` — 勤怠取得
  *   `PUT /employees/{emp_id}/work_records/{date}` — 勤怠登録
*   **トークンリフレッシュ**: 401時に自動リフレッシュ→再試行

## 7. Security & Compliance
*   **個人情報**: スタッフ実名 (`DB_Master_Staff`, `DB_Master_Nicknames`) はアクセス制限
*   **HR API**: 給与情報を扱うため、OAuth トークンの管理に注意
*   **Code**: `rules.md` のディレクトリ構成ルールに従う
