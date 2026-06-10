# HMC Task Management System 技術仕様書

## 1. システム構成概要
本システムは、LLMエージェント（Antigravity）を「オーケストレーター」として配置し、ローカルのMarkdownファイルと外部API（Google Calendar）を接続するアーキテクチャを採用している。

### コンポーネント
*   **Agent (Vice Pilot)**: ユーザーの自然言語入力を解釈し、適切なツールを実行する。行動指針は `.agent/skills/hmc_pilot/SKILL.md` に定義。
*   **Database (Markdown)**: タスクの永続化層。`tasks/` ディレクトリ配下に配置。
*   **Calendar Tool**: `.agent/skills/hmc_pilot/scripts/manage_calendar.py`。Google Calendar APIのラッパー。

## 2. ファイル・ディレクトリ構造

```text
harappa-cockpit/
├── .agent/skills/
│   └── hmc_pilot/
│       ├── SKILL.md         # エージェントのシステムプロンプト/行動ルール定義
│       └── scripts/
│           └── manage_calendar.py   # カレンダー操作スクリプト
├── tasks/                   # タスクデータベース
│   ├── active_tasks.md      # 今日のタスクリスト
│   ├── backlog.md           # バックログ（定期タスク含む）
│   ├── archive.md           # 完了タスクログ
│   └── inbox/               # インボックス
└── oauth_credentials.json   # Google OAuth クライアントID（Desktop App）
```

## 3. 機能詳細

### 3.1 Pilot Rules (`SKILL.md`)
エージェントの振る舞いを規定するファイル。
*   **Morning Briefing**: カレンダー取得、タスク結合、Deadline Check（期限確認ロジック）、カテゴリ別出力フォーマット。
*   **Task Management**: 自然言語によるMarkdown編集操作。
*   **Daily Review**: タスクのArchiving処理。

### 3.2 Calendar Manager (`manage_calendar.py`)
Google Calendar API v3 を使用した Python スクリプト。
*   **認証**: `oauth_credentials.json` を使用した OAuth 2.0 User Flow。初回はブラウザ（または手動URLコピー）による承認が必要。トークンは `token.json` にキャッシュされる。
*   **機能**:
    *   `get_events`: 今日の予定取得（終日/時間指定）。
    *   `add_event`: イベント追加。
    *   `delete_event`: タイトル完全一致によるイベント削除（当日以降）。

## 4. データ構造 (Markdown)

### backlog.md
*   **Recurring Tasks**: 定期実行タスクをセクション管理。
    *   Weekly / Monthly で区分。
    *   各行に関連アプリ名（`[アプリ: Shift Manager]` 等）を記載し、エージェントが実行ツールを推測しやすくする。
*   **Categories**: ユーザー定義のカテゴリ（【開発】【事務】等）で見出し分けを行う。

## 5. 依存関係
*   `google-api-python-client`
*   `google-auth-oauthlib`
*   `google-auth-httplib2`
