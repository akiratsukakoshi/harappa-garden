# App Definition: invoice_processor (Phase 2 Refined)

## 1. アプリ概要
**invoice_processor** は、受領した請求書（PDFまたは画像）をAIで解析し、Freee会計へ一括で自動登録するアプリケーションです。
電子データ（PDF）と物理データ（紙の撮影画像）の両方に対応し、Gemini 1.5/2.0 のマルチモーダル機能を用いて高精度な読み取りを行います。
Phase 2改修により、バッチ処理による一括抽出・確認機能と、複数明細行の対応が追加されました。

## 2. 業務フロー (Workflow)

プロセスは「抽出 (Extract)」と「登録 (Register)」の2段階に分離されました。

1.  **Fetch (システム):**
    *   `python apps/invoice_processor/main.py fetch` を実行。(`--after YYYY/MM/DD` で期間指定可能)
    *   Gmailを検索し、添付ファイルを Drive の `Invoices/Inbox` にアップロード。
    *   Driveファイルのメタデータに `thread_id` を記録し、メールには `Invoice_Fetched` ラベルを付与。
2.  **Extract (システム):**
    *   `python apps/invoice_processor/main.py extract` を実行。
    *   AIが「取引日」「支払先」「明細（金額・内容・部門）」「インボイス登録番号」を抽出。
    *   辞書ルールと履歴に基づき「パートナーコード」「勘定科目」「税区分」を推論。
    *   結果を CSV ファイル (`data/invoice_processor/review/`) として出力。
3.  **Review (人間):**
    *   出力された CSV をExcel等で開き、内容を確認・修正。
    *   必要に応じて行を追加・削除可能。
    *   マスタデータ (`export_masters.py` で出力可能) を参照してID等を補完。
4.  **Register (システム):**
    *   `python apps/invoice_processor/main.py register --file <csv_path>` を実行。
    *   CSVデータを読み込み、Freee API を介して「未決済の支出取引（Expense Deal）」として一括登録。
    *   **ステータス連携**: 登録成功時、Drive メタデータから `thread_id` を取得し、Gmailスレッドに「処理済」ラベルを付与＆アーカイブ。
    *   処理完了ファイルは `processed` フォルダへ移動。

## 3. 実装要件

### 3.1 ディレクトリ構造
```text
apps/invoice_processor/
 ├── main.py              # CLIエントリーポイント (fetch/extract/register)
 ├── fetcher.py           # Gmail添付ファイル取得・Driveアップロード [NEW]
 ├── pdf_analyzer.py      # Gemini API解析 (複数行対応)
 ├── rule_engine.py       # ルールベース推論ロジック
 ├── drive_client.py      # Google Drive操作
 ├── mapping_config.json  # パートナー・部門・勘定科目のマッピング定義
 └── export_masters.py    # Freeeマスタデータ出力スクリプト
```

### 3.1.1 shift_manager 連携
月次支払処理では `apps/shift_manager/logic/export_external_staff.py` が `data/invoice_processor/review/external_staff_YYYYMM.csv` を生成し、本アプリの `register` コマンドに同じフォーマットでそのまま渡せる構造になっている。外部スタッフ（請求書を発行しないスタッフ）のworktime稼働分はこの経路で一括登録される。

外部スタッフCSV由来の行は `file_id` がダミー値（例: `202605_extra_001`）のため、register実行時のDrive移動でエラーログが出るが**Freee登録は成功している**（想定挙動）。詳細は [shift_manager 技術仕様](shift_manager.md#external-staff-csv-export-新) を参照。

### 3.2 データモデル (CSV)
中間レビュー用 CSV は以下のフォーマット (BOM付き UTF-8) です。
*   `file_id`, `file_name`
*   `date`: 取引日 (YYYY-MM-DD)
*   `payee`: 支払先名 (AI抽出)
*   **[空欄]**: メモ用・手動修正用
*   `partner_code`: 取引先コード
*   `partner_id`: Freee取引先ID
*   `description`: 取引内容
*   `section_name`: 部門名
*   `section_id`: 部門ID
*   `account_item_name`: 勘定科目名
*   `invoice_number`: T番号
*   `amount`: 金額
*   `document_total`: 請求総額 (Validation用)
*   `calculated_total`: 明細合計 (Validation用)
*   `diff`: 差額 (Validation用)
*   `warning`: 警告メッセージ (例: MISMATCH)
*   `tax_code`: 税区分 (例: "189: 課対仕入（控80）10％")

### 3.3 ロジック
*   **パートナー特定:**
    1.  `mapping_config.json` の `partner_rules` (キーとの完全一致)
    2.  `partner_rules` のキーが支払先名や説明文に含まれるか (全文キーワード検索)
    3.  Freeeマスタ検索 (部分一致)
*   **勘定科目推論:**
    *   **外注費** (デフォルト)、**旅費交通費**、**消耗品費** の3つに限定。
    *   パートナーごとのデフォルト設定が優先。
*   **支払金額整合性 (Payment Integrity):**
    *   AI抽出した「請求総額 (Document Total)」と「明細合計」を比較。
    *   税抜/税込のズレや端数誤差を自動補正し、不一致時は `warning` を出力。
*   **複数行対応:** AIが明細行 (`items` 配列) を返した場合、CSV に複数行として展開する。合計金額は各行の `amount` に従う。
*   **マスタ連携:** `export_masters.py` により、最新のパートナー・部門・勘定科目・税区分リストをローカル CSV に出力可能。