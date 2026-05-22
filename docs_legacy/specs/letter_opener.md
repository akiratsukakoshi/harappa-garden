# Letter Opener 技術仕様書

## 1. システム概要
`letter_opener` は、Google Driveをインターフェースとし、郵便物の画像から処理すべきタスク情報をGenAIを用いて抽出し、HMCのマークダウンベースのタスクシステム (`tasks/letter_tasks.md` 経由) に統合する自動化モジュールです。

## 2. アーキテクチャ構成

* **AI Agent (HMC Vice Pilot)**: 本モジュールの全体オーケストレーションと、Human-in-the-loopの対話を担う (`.agent/skills/letter_opener/SKILL.md`)。
* **Python CLI (`apps/letter_opener/main.py`)**: 具体的なデータのフェッチ、解析、ファイル移動を実行するエントリポイント。
* **Drive Client (`apps/letter_opener/drive_client.py`)**: Google Workspace API を用いたGoogle Drive上の画像ファイル取得・移動。
* **OCR Analyzer (`apps/letter_opener/ocr_analyzer.py`)**: `gemini-2.0-flash` を利用し、画像からタスク情報を構造化 (JSON) して抽出。

## 3. 処理フロー

### 3.1 Extract (抽出フェーズ)
**コマンド:** `python apps/letter_opener/main.py extract`
1. `DriveClient` を経由して `LETTER_DRIVE_INBOX_ID` フォルダをスキャンし、対象画像を `data/letter_opener/temp/` にダウンロード。
2. 各画像に対し `TaskAnalyzer.analyze()` を実行。Gemini APIへアップロードし、以下のプロンプト定義に従いJSONを抽出。
   - `task_type` (支払い, 手続き, 書類提出, 連絡, 確認, その他)
   - `task_content`
   - `deadline` (YYYY/MM/DD)
   - `summary`
3. 分析結果にユニークな `task_id` (`LTR-XXXX`) およびファイルメタデータを付与し、`data/letter_opener/review/letter_review_YYYYMMDD_HHMMSS.json` として保存。

### 3.2 Review (Human-in-the-loop フェーズ)
*(このフェーズはPythonスクリプトではなく、HMCエージェントの処理として実行される)*
1. エージェントが出力されたJSONを読み取り、チャットUI上でユーザーに対して内容の確認を促す。
2. ユーザーからの修正指示があれば、エージェント側でメモリ上のタスクデータを修正する。
3. ユーザーからの承認を得る。

### 3.3 Register (登録フェーズ)
**コマンド:** `python apps/letter_opener/main.py register --file <json_file>`
1. 承認済みのJSONファイルを指定してRegisterコマンドを実行。
2. JSON内の各タスクをMarkdownのチェックボックスリスト（例: `- [ ] LTR-ABCD [支払い] ...`）にフォーマット変換。
3. 変換した文字列を `/home/tukapontas/harappa-cockpit/tasks/letter_tasks.md` の末尾に追記。
4. `DriveClient` を経由し、処理が完了した関連画像ファイルを `LETTER_DRIVE_PROCESSED_ID` へ移動 (IDベースの親フォルダ差し替え)。

## 4. HMC本体 (`hmc_pilot`) との統合
`tasks/letter_tasks.md` は中間バッファとして機能します。
`hmc_pilot` スキルの `Inbox Processing` ロジック（`apps/hmc_pilot/scripts` またはエージェントフロー）において、`tasks/inbox/` と共に `tasks/letter_tasks.md` もスキャン対象となります。
タスクが抽出された後、`tasks/backlog.md` の適切なカテゴリ配下へマージされ、元の `letter_tasks.md` の内容はクリア（空ファイル化）されることで、処理済みの状態を管理します。

## 5. 依存関係
* Python 3.x
* `google-generativeai` (Gemini OCR用途)
* `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib` (Google Drive制御)
* 環境変数: `GEMINI_API_KEY`, `LETTER_DRIVE_INBOX_ID`, `LETTER_DRIVE_PROCESSED_ID`
