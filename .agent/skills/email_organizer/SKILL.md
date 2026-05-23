---
name: email_organizer
description: Gmailの受信トレイを整理し、重要なタスクを抽出するためのスキル
---

# Email Organizer Skill

このスキルは、膨大な受信トレイから「メルマガ・通知」を一括アーカイブし、「重要なメール」からタスク（返信・確認）を抽出してリスト化するためのツールです。
Human-in-the-Loop（人間による確認）を前提とし、実行するたびにアーカイブのルールを学習して効率化を進めます。
> **Operational Rule**: 初めてアーカイブする送信元については、必ずユーザーに確認をとってから除外リスト（Config）に追加してください。独断で追加してはいけません。

## 主な機能
1.  **Learning Archiver（学習型アーカイブ）**:
    *   メルマガや通知を自動判定・アーカイブします。
    *   初回に「これはメルマガですか？」とユーザーに確認し、ルール（送信元・件名）を学習します。
2.  **Task Extractor（タスク抽出）**:
    *   重要なメールをAIが解析し、「要返信」「要確認」などのアクションと締め切りを提案します。
    *   ユーザーが承認すると、`tasks/mail_task.md` にToDoリストとして書き出します。

## ディレクトリ構成
*   **Skill:** `.agent/skills/email_organizer/`
*   **App:** `apps/email_organizer/organizer.py`
*   **Config:** `data/email_organizer/config.json` (学習データ)
*   **Output:** `tasks/mail_task.md` (抽出されたタスク)

## セットアップ手順

### 1. Python環境の準備
プロジェクト共通の `venv` を使用します。依存ライブラリ（`google-generativeai`, `python-dotenv` 等）が含まれています。

```bash
# プロジェクトルートで実行
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. gogcli のセットアップ
Gmailの操作には `gogcli` を使用します。

1.  **インストール確認**: `~/.local/bin/gog version` が表示されること。
2.  **認証 (Login)**: まだ認証していない場合は、以下を実行して `me` としてログインします。
    ```bash
    ~/.local/bin/gog login
    # ブラウザが開くので、Googleアカウントで認証してください。
    ```
3.  **パスワード設定**: スクリプト実行時にキーリングのパスワードが必要です。
    ```bash
    export GOG_KEYRING_PASSWORD=your_password
    ```

### 3. APIキーの設定（AI機能用）
`.env` ファイルに `GOOGLE_API_KEY` が設定されていることを確認してください。
これがない場合、タスク抽出は簡易的なキーワード判定のみとなります。

## 使用方法

以下のコマンドを実行して、インタラクティブモードを開始します。

```bash
# パスワードは環境に合わせて設定してください
export GOG_KEYRING_PASSWORD=your_password
./venv/bin/python3 apps/email_organizer/organizer.py
```

### 実行フロー
1.  **スキャン**: 未読メールを最大30件取得・分析します。
2.  **自動アーカイブ**: 既知のルールに基づき、不要なメールをアーカイブ対象にします。
3.  **提案（Plan）の表示**:
    *   `[1] Auto-Archive`: 自動アーカイブ対象
    *   `[2] Task Candidates`: AIが提案するタスク（要返信・要確認）
    *   `[3] Review / Uncertain`: 判断できなかったメール
4.  **インタラクティブ確認**:
    *   コマンド `i` を入力すると、`[3]` の不明なメールを1件ずつ確認できます。
    *   **a (Archive)**: アーカイブ・送信元を学習リストに追加。（※**初出の送信元は必ずユーザーに確認すること**）
    *   **t (Task)**: タスクとして追加（期限などの修正が可能）。
    *   **v (Invoice)**: 請求書としてマーク（`Invoice_Pending`）。Invoice Processorへの引き渡し用。
    *   **s (Skip)**: 何もしない。
5.  **実行 (Execute)**:
    *   コマンド `y` を入力すると、確定したアーカイブ処理とタスク書き出しを実行します。

## トラブルシューティング
*   **gogcliエラー**: `GOG_KEYRING_PASSWORD` が正しいか確認してください。
*   **分析が遅い**: Gemini APIの応答待ちが発生している可能性があります。
*   **誤検知**: `data/email_organizer/config.json` を直接編集して、誤ったルールを削除してください。
