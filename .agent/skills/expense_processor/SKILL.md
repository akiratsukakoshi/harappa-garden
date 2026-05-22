---
name: expense_processor
description: 経営者のクレジットカード明細や領収書画像の経費登録を支援するスキル
---

# Expense Processor Skill

経営者（ガクチョー）個人のクレジットカード利用明細（CSV）および領収書（画像）から、会計ソフト「freee」へインポートするためのデータを生成・登録します。
AIによる自動抽出と、人間による最終確認（Human-in-the-Loop）を組み合わせたプロセスです。

## 主な機能
1. **抽出 (Extract)**: 
   - クレジットカード明細CSV（PayPayカード、イオン/コスモカード）を解析します。
   - 費目をAIが5つのカテゴリー（旅費交通費、原材料、消耗品費、通信費、会議費）から自動推論します。
   - 中間確認用のCSVを出力します。
2. **登録 (Upload)**:
   - 人間が確認・修正した中間CSVをfreeeに登録します。
   - 登録完了後、入力ファイルをアーカイブします。

## ディレクトリ構成
- 入力: `data/expense_processor/input/` (ここにCSVや画像を置く)
- 作業中: `data/expense_processor/working/` (生成された中間CSVが出力される)
- 完了: `data/expense_processor/proceeded/` (処理済みのファイルが移動される)

## 使用方法

### 1. データの準備
Google Driveの親フォルダ（`EXPENSE_DRIVE_FOLDER_ID` で設定されたフォルダ）内の `input` フォルダにクレジットカードの明細CSV、またはレシート画像（JPG, PNG, WEBP, HEIC）を直接配置してください。
（ローカルの `data/expense_processor/input/` に直接配置しても動作しますが、Google Driveを推奨します）

### 2. データの抽出
以下のコマンドを実行して、中間CSVを生成します。

```bash
./venv/bin/python3 apps/expense_processor/processor.py extract
```

実行後、`data/expense_processor/working/` に `expenses_YYYYMMDD_HHMMSS.csv` が生成されます。

### 3. 人間による確認・修正
生成されたCSVを開き、以下の項目を確認・修正してください。
- `account_item`: AIの推論が正しいか確認。
- `department`: 必要に応じて部門名を入力（`apps/expense_processor/processor.py` 内でFreeeの部門IDとマッピングされます）。
- `details`: 必要に応じて修正。
- `amount`: 金額が正しいか確認。

### 4. Freeeへのアップロード
修正したCSVを指定して、以下のコマンドを実行します。まずは `--dry-run` でテストすることを推奨します。

```bash
# テスト実行（登録はされません）
./venv/bin/python3 apps/expense_processor/processor.py upload data/expense_processor/working/expenses_2026xxxx.csv --dry-run

# 本番実行
./venv/bin/python3 apps/expense_processor/processor.py upload data/expense_processor/working/expenses_2026xxxx.csv
```

### 5. 完了
登録が成功すると、入力ファイルと中間CSVは `data/expense_processor/proceeded/YYYYMMDD/` にアーカイブされます。

## 注意事項
- **APIキー**: `.env` に `GOOGLE_API_KEY` と Freee APIのトークン設定が必要です。
- **費目**: AIは事前に定義された5つの費目から選択しようとしますが、迷った場合は「消耗品費」等を設定することがあります。必ず人間が確認してください。
- **部門**: CSVの `department` 列に入力された文字列は、Freee上の部門名と完全一致する必要があります。一致しない場合は部門なしで登録されます。
