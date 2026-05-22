---
name: freee_auditor
description: freeeの取引データを監査し、部門（セクション）の振り分け漏れを発見・一括修正するスキル
---

# Freee 経理監査スキル

freeeに登録されている取引の中から**部門が設定されていないもの**を検出し、AIによる部門提案を経て一括修正するスキルです。

## 発動タイミング

以下のような発言があったときにこのスキルを使う：
- 「部門の振り分け漏れを確認して」
- 「経理の精度チェックをしたい」
- 「〇月〜〇月の部門未設定を直したい」
- 「部門が空白の取引をリストアップして」

## ディレクトリ構成

- スクリプト: `apps/freee_auditor/auditor.py`
- スキャン結果CSV: `data/freee_auditor/scan/`
- 反映済みアーカイブ: `data/freee_auditor/applied/`

---

## ワークフロー

### ステップ1：スキャン実行

部門が未設定の取引を検索してCSVに出力する。

```bash
# デフォルト（直近3ヶ月）
python3 apps/freee_auditor/auditor.py scan

# 期間指定
python3 apps/freee_auditor/auditor.py scan --start 2025-10-01 --end 2026-03-31
```

**出力**: `data/freee_auditor/scan/audit_YYYYMMDD_HHMMSS.csv`

CSVの列構成：
| 列名 | 内容 |
|---|---|
| deal_id | freee取引ID |
| detail_id | 明細行ID |
| date | 取引日 |
| type | income / expense |
| partner | 取引先名 |
| account_item | 勘定科目 |
| amount | 金額（円） |
| description | 摘要 |
| suggested_section | **AIが提案する部門名（次ステップで記入）** |
| section_name | **最終的に適用する部門名（人間が確認・修正）** |

---

### ステップ2：AIによる部門提案と確認

CSVを読み込み、各行の `account_item`・`description`・`amount` をもとに、利用可能な部門リストから最適な部門を推論して `suggested_section` 列に記入する。

**AIへの指示（このステップで実行すること）**：
1. スキャン結果CSVの内容をユーザーに提示する（件数、主な取引一覧）
2. 各行について、以下の部門から最も適切なものを推論する：
   - スキャン実行時に出力される「利用可能な部門一覧」を参照すること
3. 推論結果を `suggested_section` に記入したCSVを提示し、ユーザーに確認を求める
4. ユーザーが修正・承認したら `section_name` 列に確定値を書き込む

**重要**：部門の確定はユーザーの承認が必要。スキャン結果だけで apply を実行しないこと。

---

### ステップ3：freeeへの反映

ユーザーが確認・承認した `section_name` を持つCSVを指定してfreeeを更新する。

```bash
# まずDry Runでテスト
python3 apps/freee_auditor/auditor.py apply data/freee_auditor/scan/audit_xxx.csv --dry-run

# 内容を確認したら本番実行
python3 apps/freee_auditor/auditor.py apply data/freee_auditor/scan/audit_xxx.csv
```

---

## 注意事項

- **承認フロー必須**: `apply` の実行前に必ずユーザーの確認を得ること。部門の変更は会計データを直接変更するため不可逆に近い。
- **部門名の一致**: `section_name` はfreeeの部門名と完全一致が必要。スキャン時に表示される「利用可能な部門一覧」を必ず参照すること。
- **空白行はスキップ**: `section_name` が空白の行は apply 時に自動的にスキップされる。
- **エラー時**: apply で失敗した行はログに記録され、修正後に再実行できる。

## 連携スキル

- **finance_analyzer**（財務分析スキル）: 部門振り分けが完了した後、`finance_analyzer check` でデータ品質を再確認することを推奨。
