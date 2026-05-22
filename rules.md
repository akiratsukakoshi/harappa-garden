# Project Directory Structure Rules

HARAPPA Management Cockpit プロジェクトにおけるディレクトリ運用のルールを定義します。
新しいアプリケーションを追加する際は、本ルールに従ってください。

## 1. 基本方針
*   **Root is Clean:** ルートディレクトリには、プロジェクト全体に関わる必要最低限のファイルのみを配置する。
*   **App Isolation:** 各アプリケーションは `apps/{app_name}/` 内で完結させるよう努める。
*   **Data Separation:** データファイルは `data/{app_name}/` に配置し、Git管理から除外して安全性を確保する。

## 2. ディレクトリ構成

### Root (`/`)
*   プロジェクト全体の定義ファイル (`project_harappa-cockpit.md`, `README.md`, `rules.md`)
*   全体設定 (`.env`, `.gitignore`)
*   共通エントリーポイント (`main_menu.py`, `requirements.txt`)

### Applications (`apps/{app_name}/`)
*   各アプリケーションのソースコード置き場。
*   個別の `config.json` 等もここに配置する。

### Data (`data/{app_name}/`)
*   CSV、画像、ログなど、アプリが入出力するデータ置き場。
*   **重要:** このディレクトリは `.gitignore` によりGit管理から除外される。
*   構造例:
    *   `data/finance_importer/input/`: 入力用CSV
    *   `data/finance_importer/audit/`: 監査ログ

### Documentation (`docs/`)
*   `docs/specs/`: 仕様書、設計書。
*   `docs/sample/`: テスト用のサンプルデータ。
*   `docs/manuals/`: ユーザーマニュアル等。

### Modules (`modules/`)
*   複数アプリで共有される汎用ライブラリ（APIクライアント、ロガー等）。

## 3. ファイル命名規則
*   **Python:** スネークケース (`import_sales.py`, `section_guesser.py`)
*   **Class:** パスカルケース (`FreeeClient`, `SectionGuesser`)

## 4. ツール・CLIの使用
*   **gogcli:** Google Workspace操作に使用。
    *   コマンドパス: `~/.local/bin/gog`
    *   アカウントエイリアス: `me` (通常使用)
    *   認証情報: `~/.config/gogcli/` (非公開情報含むためGit管理外)
    *   **重要:** 非対話モードでの実行時は、環境変数 `GOG_KEYRING_PASSWORD` にパスワードを設定すること（例: `export GOG_KEYRING_PASSWORD=your_password`）。スクリプト内でのハードコードは禁止。

