# App Definition: Finance Analyzer

## 1. アプリ概要

**Finance Analyzer** は、freeeの財務データ（PL・BS・CF）をリアルタイムで取得・集計し、チャット上での財務状況確認・将来予測・戦略議論を支援するアプリケーションです。

kpi_monitor（Google Sheets書き出し型）の後継として設計されており、「静的なレポート生成」ではなく「AIと対話しながら財務を分析する」ことを目的としています。

**2フェーズ設計:**

| フェーズ | 目的 | 主なコマンド |
|---|---|---|
| フェーズ1（データ品質確認） | 分析前に帳票の精度を確認する | `check` |
| フェーズ2（分析・議論） | 実績把握・予測・戦略議論 | `pl`, `cf`, `summary` |

---

## 2. 業務フロー (Workflow)

```
[targets]        [check]             [pl / cf / summary]
目標値設定 → データ品質確認 → 財務データ取得・表示 → AI戦略議論
               ↑                       ↑
           異常あれば              各コマンドは
         freee_auditor で修正      独立実行可能
```

---

## 3. 実装要件

### 3.1 ディレクトリ構造

```text
apps/finance_analyzer/
 └── analyzer.py          # メイン処理（全コマンド）

data/finance_analyzer/    # Git管理外
 ├── targets.json         # 年間目標値設定ファイル
 └── reports/             # PL・CF・サマリーのCSV/JSONレポート

.agent/skills/finance_analyzer/
 └── SKILL.md             # Agentスキル定義（日本語）
```

### 3.2 設定ファイル仕様 (`targets.json`)

```json
{
  "fiscal_year": 2025,
  "fiscal_start_month": 10,
  "annual_targets": {
    "revenue": 15000000,
    "gross_profit": 9000000,
    "operating_profit": 2500000
  },
  "notes": "昨対比120%目標"
}
```

`targets` コマンドで更新。全コマンドで自動参照される。

### 3.3 コマンド仕様

#### `check [--fiscal-year YYYY]`

月別の会計データ品質を集計して表示する。

**処理フロー:**
1. `fiscal_year` と `fiscal_start_month` から会計年度の12ヶ月を算出
2. 月ごとに `get_all_deals()` を実行
3. 各月について `section_id` 未設定件数・`payment_status != settled` 件数を集計
4. テーブル形式で表示

---

#### `pl [--fiscal-year YYYY] [--start-month N] [--end-month N]`

月次損益計算書をテーブル表示 + CSV保存する。

**処理フロー:**
1. 指定範囲の財務月ごとに `get_trial_pl(fiscal_year, start_month=m, end_month=m)` を実行
2. `_parse_pl_response()` でレスポンスから主要5指標を抽出
3. Markdownテーブルとして stdout に出力（目標比・累計付き）
4. CSV保存: `data/finance_analyzer/reports/pl_fy{YYYY}_{ts}.csv`

**勘定カテゴリ分類:**

| 区分 | Freeeカテゴリ名 |
|---|---|
| 売上高 | 売上高, 売上総損益金額, 営業損益金額 |
| 売上原価 | 売上原価, 期首商品棚卸, 当期商品仕入, 他勘定振替高(商), 期末商品棚卸, 商品売上原価 |
| 販売管理費 | 販売管理費 |

売上系は `credit - debit`、費用系は `debit - credit` で計算。

---

#### `cf [--months N]`

口座残高と月次CFを表示する。

**処理フロー:**
1. `get_walletables()` で全口座・カードの残高を取得
2. 直近N ヶ月分の `get_trial_pl()` で月次営業利益を取得（CF近似値）
3. 現在残高 + 月次平均 × 残り月数 = 年度末推計残高を算出
4. 推計残高が負になる月を資金ショート候補として警告

**CF近似の前提:**
- 営業利益をキャッシュフローの近似値として使用
- 設備投資・借入返済等の資本的支出は含まない

---

#### `summary [--fiscal-year YYYY]`

戦略議論用の財務サマリーを生成する。

**処理フロー:**
1. 会計年度の実績月すべてについて `get_trial_pl()` を実行
2. YTD（年度累計）集計と月次平均を算出
3. 月次平均 × 残り月数 = 年度末着地予測を算出
4. `get_walletables()` で現在残高を取得
5. stdout にテキストサマリーを表示
6. JSON保存: `data/finance_analyzer/reports/summary_fy{YYYY}_{ts}.json`

**JSON出力スキーマ:**

```json
{
  "generated_at": "YYYY-MM-DD",
  "fiscal_year": 2025,
  "fiscal_start_month": 10,
  "months_elapsed": 6,
  "months_remaining": 6,
  "targets": { "revenue": 0, "gross_profit": 0, "operating_profit": 0 },
  "ytd_pl": { "revenue": 0, "cogs": 0, "gross_profit": 0, "sga": 0, "operating_profit": 0 },
  "monthly_pl": { "2025-10": { "revenue": 0, ... }, ... },
  "projected_full_year_pl": { "revenue": 0, ... },
  "current_cash": {
    "total": 0,
    "walletables": [ { "name": "口座名", "balance": 0 } ]
  },
  "monthly_avg": { "revenue": 0, "operating_profit": 0 }
}
```

---

#### `targets`

目標値の確認・更新を行う。

| パラメータ | 説明 |
|---|---|
| `--fiscal-year` | 会計年度 |
| `--fiscal-start-month` | 期首月（1〜12） |
| `--set-revenue` | 年間売上目標（円） |
| `--set-gross-profit` | 年間売上総利益目標（円） |
| `--set-operating-profit` | 年間営業利益目標（円） |
| `--notes` | 備考テキスト |

---

### 3.4 会計年度計算ロジック

```python
# fiscal_year=2025, fiscal_start_month=10 の場合
# 財務月1 = 2025年10月
# 財務月6 = 2026年3月
# 財務月12 = 2026年9月

def _fiscal_months(fiscal_year, fiscal_start_month, count=12):
    # (calendar_year, calendar_month, fiscal_month_index) のリストを返す
```

`get_trial_pl(fiscal_year, start_month=fm_idx, end_month=fm_idx)` の `start_month` / `end_month` は**会計年度内の財務月（1-12）**であることに注意。カレンダー月ではない。

---

### 3.5 freee API 利用エンドポイント

| メソッド | エンドポイント | 用途 |
|---|---|---|
| GET | `/api/1/deals` | データ品質チェック用取引取得 |
| GET | `/api/1/reports/trial_pl` | 月次PL取得 |
| GET | `/api/1/reports/trial_bs` | BS取得（将来拡張用） |
| GET | `/api/1/walletables` | 口座残高取得 |
| GET | `/api/1/walletable_txns` | 口座取引明細（将来拡張用） |

---

## 4. 技術スタック

- **言語:** Python 3
- **会計:** Freee Accounting API - `modules.freee_client`
- **依存ライブラリ:** `requests`, `python-dotenv`, `json`, `csv`（標準ライブラリのみ使用）

---

## 5. kpi_monitor との関係

| 項目 | kpi_monitor | finance_analyzer |
|---|---|---|
| 出力先 | Google Sheets | stdout（Markdown）+ CSV/JSON |
| 操作方式 | バッチ実行 | 対話型・コマンド単位 |
| 部門別詳細 | ◎（スプリットレイアウト） | △（全社PL中心） |
| 戦略議論 | ✗ | ◎ |
| 予測機能 | ✗ | ◎ |
| AI連携 | ✗ | ◎ |

kpi_monitor は非推奨となりましたが、部門別の詳細スプリットレイアウトが必要な場合は引き続き利用可能です。

---

## 6. 将来拡張

- **部門別PL:** `get_trial_pl()` の `breakdown_display_type="section"` パラメータを活用した部門別PL表示
- **BS分析:** `get_trial_bs()` を使った資産・負債の推移確認
- **口座トランザクション分析:** `get_walletable_transactions()` を使った実際のキャッシュフロー詳細
- **Sheets連携:** `summary` の結果をkpi_monitorのSheetSyncerで出力するオプション
