---
name: letter_opener
description: Google Driveにアップロードされた郵便物の画像を解析し、タスクを抽出して管理システムに連携するスキル
---

# Letter Opener Skill

スマートフォンのGoogle Driveアプリ等から所定フォルダ (`Letters/Inbox`) にアップロードされた郵便物（封筒、ハガキなど）の写真を自動的に解析し、タスク化するAI・人間協調（Human-in-the-loop）スキルです。

## 主な機能

1. **Extract (抽出)**:
    *   DriveのInboxフォルダにある画像を読み込みます。
    *   Gemini API等によるOCRで画像内のテキストを読み取り、必要なタスク情報を構造化して抽出します。
    *   抽出項目: タスク番号, タスク種類（支払い, 手続き, 書類提出, 連絡, その他）, 具体的タスク内容, 締切日

2. **Review (人間による確認)**:
    *   抽出されたタスク候補をエージェントがチャット画面でユーザーに提示します。
    *   ユーザーは内容を確認し、チャット上で修正や承認を指示します。

3. **Register (登録)**:
    *   ユーザーが承認したタスク情報を `/home/tukapontas/harappa-cockpit/tasks/letter_tasks.md` に追記します。
    *   処理済みの画像ファイルをタスク番号にリネーム（可能であれば）し、Driveの `Processed` フォルダへ移動します。

## ディレクトリ構成

*   **Skill:** `.agent/skills/letter_opener/`
*   **App:** `apps/letter_opener/main.py`
*   **Data:** `data/letter_opener/`
    *   `temp/`: 画像ダウンロードや一時ファイル用
    *   `review/`: 解析結果・中間データ JSON 等

## セットアップ手順

### 1. Python環境

プロジェクト共通の `venv` (または `invoice_processor` と同様の環境) を使用します。

```bash
# プロジェクトルートで実行
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境変数の設定 (`.env`)

以下のDriveフォルダIDが `.env` に設定されている必要があります。
*   `LETTER_DRIVE_INBOX_ID`: 処理対象の画像が入るInboxフォルダ
*   `LETTER_DRIVE_PROCESSED_ID`: 処理完了後に移動するフォルダ

## エージェント（あなた）向けの実行ワークフロー

**ユーザートリガー例:** 「郵便物の確認をしよう」

1.  **解析の実行 (Extract)**
    *   `python apps/letter_opener/main.py extract` 等のコマンドを実行します。
    *   標準出力または `data/letter_opener/review/` 配下のJSON等から抽出結果を取得します。

2.  **結果の提示 (Review)**
    *   抽出結果をわかりやすくフォーマットしてチャット画面に表示します。
    *   「以下の内容でタスク化してよろしいでしょうか？必要に応じて修正点を教えてください。」と尋ねます（**必ずここでユーザーの入力を待ちます**）。

3.  **HMC等への連携と登録 (Register)**
    *   ユーザーから承認・修正指示を得たら、最終的なタスク内容を作成します。
    *   フォーマット例: `- [ ] LTR-001 [支払い] 固定資産税第2期納付 (締切: 2026/04/30)`
    *   作成したタスクを `tasks/letter_tasks.md` の末尾に追記します。
    *   Pythonスクリプトによる Register 処理 (`python apps/letter_opener/main.py register ...`) を呼び出し、Drive上の元画像ファイルを `Processed` フォルダに移動処理させます。

4.  **完了報告**
    *   「`letter_tasks.md` への書き出しと画像の移動が完了しました」とユーザーに報告します。
