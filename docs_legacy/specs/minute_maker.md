# App Definition: minute_maker

## 1. アプリ概要
**Minute Maker** は、会議の文字起こしテキスト（Unstructured Data）を、構造化された議事録（Markdown/PDF）に変換するAIエージェントスキルです。
PythonスクリプトによるPDF生成エンジン `md_to_pdf.py` をバックエンドに持ち、AIエージェントがフロントエンドとしてユーザーとの対話（Human-in-the-Loop）を担当します。

## 2. 実装要件

### 2.1 ディレクトリ構成
データの機密性と管理容易性を考慮し、コード（プロンプト）とデータ（議事録）を分離しています。

*   **スキル・設定:** `.agent/skills/minute_maker/`
    *   `SKILL.md`: エージェントの挙動定義
    *   `prompts/`: 議事録テンプレート（Markdown）
    *   `scripts/`: ユーティリティスクリプト (`md_to_pdf.py`)
*   **データエリア:** `data/minutes_maker/` (Git除外対象)
    *   `input/`: 文字起こしテキスト投入口
    *   `draft/`: 中間生成物
    *   `meeting_files/`: 最終成果物アーカイブ（年/月フォルダ分け）
    *   `fonts/`: PDF埋め込み用フォントファイル

### 2.2 処理プロセス (Process)

1.  **Analysis (解析):**
    *   AIがテキストファイルを読み込み、話者リストとメタデータ（日付、タイトル）を抽出。
2.  **Mapping & Selection (対話):**
    *   ユーザー対話により話者名の置換ルールと使用テンプレートを決定。
3.  **Draft Generation (生成):**
    *   LLMがコンテキストと文字起こし全文を入力として、Markdown形式の議事録を作成。
4.  **PDF Conversion (変換):**
    *   `md_to_pdf.py` を呼び出し。
    *   `markdown2` でHTML化し、`weasyprint` でPDF化。
    *   **重要:** 日本語フォント（Noto Sans CJK JP）をOtFファイルからBase64エンコードし、CSSに直接埋め込むことで、実行環境（OS/FontConfig）に依存しないレンダリングを実現。
5.  **Archiving (保存):**
    *   完了後、ファイルを `meeting_files/YYYY/MM/` に移動し、`input` からは削除。

### 2.3 技術スタック
*   **Frontend:** AI Agent (Gemini)
*   **Backend Script:** Python
    *   `markdown2`: MD -> HTML変換
    *   `weasyprint`: HTML -> PDF変換
    *   `logging`: 実行ログ出力

## 3. 拡張性
*   **テンプレート追加:** `prompts/` ディレクトリにMDファイルを追加するだけで、エージェントが自動的に選択肢として認識します。
*   **フォント変更:** `data/minutes_maker/fonts/` に配置し、スクリプトパスを変更することで対応可能。
