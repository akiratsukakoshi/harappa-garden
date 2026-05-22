# App Definitioname: expense_processor_spec
description: Expense Processor 技術仕様書
---

# Expense Processor Technical Specification

## 1. 概要
経営者のクレジットカード明細（CSV）およびレシート画像を処理し、会計ソフトFreeeへの登録を支援するシステム。

## 2. コンポーネント



### A. Expense Processor (抽出・登録)
*   **Path:** `apps/expense_processor/processor.py`
*   **役割:** ローカルのファイルまたはDriveから取得したデータを解析し、Freeeへ登録する。

## 2. 実装要件

### 2.1 入力 (Input)
*   **データソース:**
    *   **CSV:** PayPayカード (UTF-8), イオン/コスモカード (Shift-JIS)
    *   **画像:** レシート, 領収書 (JPG, PNG, WEBP, HEIC)
*   **配置場所:** 
    *   **Google Drive:** `EXPENSE_DRIVE_FOLDER_ID` で指定されたフォルダの `input/` サブフォルダ。
    *   **Local:** `data/expense_processor/input/` (Drive から自動同期される)。
*   **ユーザー操作:** AI Agentへの指示、または `main_menu.py` からの実行。

### 2.2 処理 (Process)
1.  **Extract (抽出フェーズ):**
    *   **Drive 同期:** `DriveClient` を使用し、Google Drive の `input/` フォルダからローカルの `input/` ディレクトリへファイルをダウンロード。
    *   ディレクトリ内のファイルを走査。
    *   **CSV:** `CSVParser` クラスでフォーマットを自動判別し解析。
    *   **画像:** `ImageParser` クラスでGemini API (gemini-2.0-flash) を使用し、OCRと構造化データ抽出（JSON）を行う。
    *   **分類:** `ExpenseClassifier` クラスで、取引内容と金額から適切な勘定科目（旅費交通費、消耗品費など）を推論。
    *   **中間出力:** 解析結果を `data/expense_processor/working/`（中間CSV）に出力。
2.  **Upload (登録フェーズ):**
    *   中間CSVを読み込み、Freee APIへPOSTする。
    *   **日付正規化:** 発生日を元に、その月の末日を `due_date`（支払期日/登録日）として計算。
    *   **アーカイブ:** 完了後、入力ファイルと中間ファイルをローカルの `data/expense_processor/proceeded/` に移動。
    *   **Drive アーカイブ:** Google Drive 上のファイルも `processed/YYYYMMDD/` フォルダへ移動。

### 2.3 出力 (Output)
*   **Freee:** 経費取引（Expense Deal）として登録。
    *   **種別:** `expense`
    *   **ステータス:** `unpaid` (未決済)
    *   **発生日 (Issue Date):** 取引の発生日。
    *   **支払期日 (Due Date):** 取引月の末日。
    *   **勘定科目:** AI推論結果、またはCSV指定値。
    *   **備考:** `[AeonCard]` `[ReceiptImage]` などのソース情報を付与。

## 3. 技術スタック
*   **言語:** Python 3
*   **AI:** Google Gemini API (gemini-2.0-flash) - `google-generativeai` ライブラリ
*   **会計:** Freee Accounting API - `modules.freee_client`
*   **構成:**
    *   `apps/expense_processor/processor.py`: メインロジック
    *   `.agent/skills/expense_processor/SKILL.md`: Agentスキル定義
    *   `.agent/workflows/process_expenses.md`: ワークフロー定義

## 4. 制限事項・制約
*   **APIレート制限:** Gemini APIのRate Limit (429) に対してリトライロジックを実装済み。
*   **部門マッピング:** CSVの `department` 列がFreeeの部門名と完全一致する場合のみ部門IDを付与。
