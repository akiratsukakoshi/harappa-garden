# App Definition: finance_importer

## 1. アプリ概要
**finance_importer** は、HARAPPA Management Cockpitの最初のモジュール（Phase 1）です。
外部プラットフォーム（STORES予約、Squareなど）からダウンロードした売上データのCSVファイルを読み込み、ルールに基づいてFreee会計に「売上（Income）」として自動登録します。

## 2. 実装要件

### 2.1 入力 (Input)
* **データソース:** CSVファイル（STORES予約、Square等のエクスポートデータ）。
* **配置場所:**
    *   入力: `data/finance_importer/input/`
    *   出力（レビュー）: `data/finance_importer/review/`
    *   アーカイブ: `data/finance_importer/processed/`
* **ユーザー操作:** ユーザーはCSVを配置し、`main_menu.py` または `import_sales.py` を実行する。（推奨: AI Agent Skillの使用）

### 2.2 処理 (Process)
1.  **CSV読込:** 対象のCSVファイルを読み込む。
2.  **マッピング & EOM計算:**
    *   `mapping_config.json` の定義に従い、CSVの列を変換する。
    *   [NEW] 取引日の「月末日」を自動計算し、`registration_date` として保持する。
3.  **部門付与:** 取引内容に応じた「部門ID (Section ID)」を自動でセットする。
4.  **API送信:** 共通モジュール `modules.freee_client` を使用してFreee API（振替伝票）にPOSTする。
5.  **アーカイブ:** 処理完了後、ファイルを `processed/` ディレクトリに移動する。

### 2.3 出力 (Output)
* **Freee:** 振替伝票（Manual Journal）として登録される。
    *   **発生日 (Issue Date):** `registration_date`（各取引月の月末日）を使用。
    *   **借方 (Debit):** 前受金 (Advances Received) / 税区分: 対象外
    *   **貸方 (Credit):** 売上高 (Sales) / 税区分: 課税売上 10%
* **ログ:** 登録成功件数、エラー件数、エラー内容をコンソール（将来的にはログファイル）に出力する。

---

## 3. 現在の技術ステータス
* **Freee API接続:**
    * 共通モジュール `modules/freee_client.py` は実装済み（OAuth2認証・トークンリフレッシュ機能あり）。
    * ターゲット事業所: `HARAPPA株式会社` (ID: `723485`)。
* **開発ディレクトリ:** `apps/finance_importer/` 配下に実装を行う。

## 4. 実装に必要な情報 (Parameters)
* **事業所ID (Company ID):** `723485`
* **部門ID (Section IDs):** 開発時にAPI経由で取得し、マッピング定義に使用する。
* **CSVフォーマット:** 別途提示されるCSVヘッダー情報を元に解析ロジックを作成する。

## 5. 実装ステータス (Implemented)
1.  `apps/finance_importer/` ディレクトリ作成済み。
2.  `mapping_config.json` 実装済み（STORES/Square対応、借方/貸方設定追加）。
3.  `import_sales.py` 実装済み（AI推測、振替伝票発行ロジック実装完了）。