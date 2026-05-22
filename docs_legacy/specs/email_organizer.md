# Email Organizer Technical Specification

## 1. 概要
Gmailの未読スレッドを取得し、AI（Gemini API）とルールベースのハイブリッドロジックで「アーカイブ推奨」と「タスク用」に分類するPythonアプリケーション。

## 2. アーキテクチャ
*   **Language:** Python 3.12+
*   **Infrastructure:** `gogcli` (Go-based Gmail CLI) via `subprocess`
*   **AI Model:** Gemini 1.5 Flash (via `google-generativeai`)
*   **Configuration:** JSON (`data/email_organizer/config.json`)
*   **Location:** `apps/email_organizer/organizer.py`

## 3. データフロー
1.  **Fetch:** `gog gmail search "label:UNREAD label:INBOX" --max 30` を実行し、未読スレッドを取得。
2.  **Auto Actions:** `config.json` の `archive_rules` に基づき、既知の不要メールを抽出。
3.  **Analyze:** 残りのメールを分析。
    *   **LLM分析:** 件名・本文・送信元から「アクション（返信/確認）」「要約」「締め切り」を抽出。
    *   **Fallback:** APIキーがない場合はキーワードベースのヒューリスティックを使用。
4.  **Interactive Review:** ユーザーにプランを提示し、不明なメールの学習・分類を行う。
5.  **Execution:**
    *   **Archive:** `gog gmail thread modify <threadId> --remove INBOX`
    *   **Task Output:** `tasks/mail_task.md` にMarkdownチェックリスト形式で追記。
    *   **Learn:** 新しいアーカイブ対象ルールを `config.json` に保存。

## 4. 依存関係
*   **Libraries:** `google-generativeai`, `python-dotenv` (see `requirements.txt`)
*   **External CLI:** `gogcli` (`~/.local/bin/gog`)
*   **Environment:**
    *   `GOG_KEYRING_PASSWORD`: `gogcli` 認証用
    *   `GOOGLE_API_KEY`: Gemini API用

## 5. 出力フォーマット (`tasks/mail_task.md`)
```markdown
- [ ] [期限: YYYY-MM-DD] [要返信] 件名... (From: 送信者)
```
このファイルは、別途 `Task Management Skill` によって朝/夕に `tasks/backlog.md` 等へ統合されることを想定している。
