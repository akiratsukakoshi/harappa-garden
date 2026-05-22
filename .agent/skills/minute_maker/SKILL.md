---
name: minute_maker
description: HMC 議事録メーカー機能。会議の文字起こしテキストから、人間と対話しながら高精度な議事録を作成し、PDF化・アーカイブまでを行う。
---

# HMC 議事録メーカー (Minute Maker)

## 1. 哲学: Human-in-the-Loop
AIはあくまでドラフト作成と整形を担当する。
固有名詞の確定、重要事項の判断、テンプレート選択は必ず人間に仰ぐこと。
勝手に判断して完了させない。

## 2. 実行環境
- **Project Root**: `/home/tukapontas/harappa-cockpit`
- **Input Dir**: `data/minutes_maker/input/` (会議の文字起こしテキスト .txt を配置)
- **Prompt Dir**: `.agent/skills/minute_maker/prompts/` (議事録テンプレート .md を配置)
- **Draft Dir**: `data/minutes_maker/draft/` (生成されたMDファイルを配置)
- **Output Dir**: `data/minutes_maker/meeting_files/YYYY/MM/` (最終的な成果物 .txt/ .md /.pdf を格納)
- **Python**: `.venv/bin/python3` (プロジェクトルートの仮想環境を使用)
- **Font Dir**: `data/minutes_maker/fonts/` (PDF生成用フォント)
- **Scripts**: `.agent/skills/minute_maker/scripts/md_to_pdf.py`

## 3. 実行フロー

### A. 解析フェーズ (Analysis)
1.  **最新ファイルの特定**:
    - `Docs Root` 配下の `input/` ディレクトリ内の最新の `.txt` ファイルを読み込む。
2.  **話者IDの抽出**:
    - テキスト内の行頭 `[...]` 形式（例：`[原っぱ大学]`）を正規表現で抽出する。
    - 重複を排除し、ユニークな話者IDのリストを作成する。
3.  **会議メタ情報の推測**:
    - ファイル名や冒頭の会話内容から「会議タイトル」と「開催日」の仮案を生成する。

### B. インタラクション (Human Interaction)
ドラフト生成前に、必ず以下の情報をユーザーにチャットで確認する。

1.  **話者マッピングの確認**:
    - 抽出した話者IDリストを提示する。
    - 「誰がどのIDに対応するか（実名・役割）」の入力を求める。
    - 例: `[原っぱ大学] -> 塚越 (代表), [sim rock] -> 和田 (CFO)`
2.  **テンプレート選択**:
    - `prompt/` 内にあるテンプレートファイル一覧を表示する。
    - ユーザーに適切なテンプレートを選択させる。
3.  **基本情報の確認**:
    - 推測した「会議タイトル」と「日付」を提示し、修正がないか確認する。
4.  **【重要】コンテキスト補足**:
    - 以下の情報の追加入力を促す。
        - **アジェンダ**: 会議の主な議題。
        - **重要キーワード**: プロジェクト名、固有名詞、頻出語句など。（表記ゆれ補正に使用）

### C. ドラフト生成とLLM実行 (Draft Generation & Execution)
ユーザーからの入力に基づき、プロンプトを構築し、LLMに処理させて議事録ドラフトを作成する。

1.  **プロンプト構築**:
    - 選択されたテンプレートを読み込み、以下のプレースホルダーを置換して「完成されたプロンプト」を作成する。
        - `{{title}}`: 会議タイトル
        - `{{date}}`: 開催日
        - `{{participants}}`: 参加者リスト（話者マッピング適用済み）
        - `{{context}}`: ユーザーから提供されたアジェンダ・キーワード
        - `{{transcript}}`: 表記ゆれ補正済みの全文テキスト（話者置換済み）
2.  **LLMによる生成実行**:
    - 構築したプロンプトをLLM（自分自身）に入力として与え、指示に従って議事録を生成させる。
    - **注意**: プロンプトファイルそのものを保存するのではなく、LLMが生成した出力結果（`# タイトル 議事録` で始まるテキスト）を保存すること。
3.  **ファイル保存**:
    - 生成された結果を `draft/YYYYMMDD_会議名(日本語).md` として出力する。
    - ユーザーに作成完了を通知し、内容の確認を求める。
        - **【重要】確認ポイントの提示**:
            - ユーザーにURLを渡すだけでなく、**「特にどこを確認してほしいか」**（AIが自信を持てなかった箇所、重要なニュアンス、アクションプランの具体性など）を箇条書きで3点程度提示すること。
            - 例: 「〇〇の発言の意図は▲▲という解釈で合っていますか？」「アクションプランの期限は空欄ですが追記しますか？」

### D. アーカイブ処理 (Archiving)
ユーザーから「PDF化して」「OK」「完了」等の承認トリガーを受信したら実行する。

1.  **PDF生成**:
    - 以下のコマンドを実行し、ドラフトMDをPDFに変換する。
      ```bash
      ./.venv/bin/python3 .agent/skills/minute_maker/scripts/md_to_pdf.py "{Draft File Path}"
      ```
2.  **ファイル移動と整理**:
    - `data/minutes_maker/meeting_files/YYYY/MM/` ディレクトリを作成する（存在しない場合）。
    - 以下の手順でファイルを移動・リネームする（**`_draft` という接尾辞は削除する**）。
        - **入力テキスト**: `data/minutes_maker/input/xxxx.txt` を `data/minutes_maker/meeting_files/YYYY/MM/xxxx.txt` に移動する（**move** コマンドを使用し、inputディレクトリからは削除する）。
        - **Markdown**: `data/minutes_maker/draft/xxxx_draft.md` を `data/minutes_maker/meeting_files/YYYY/MM/xxxx.md` にリネームして移動する。
        - **PDF**: `data/minutes_maker/draft/xxxx_draft.pdf` を `data/minutes_maker/meeting_files/YYYY/MM/xxxx.pdf` にリネームして移動する。
3.  **完了通知**:
    - 「議事録の作成とPDF化が完了しました。`data/minutes_maker/meeting_files/YYYY/MM/` に保存されています。」と報告する。

## 4. エラーハンドリング
- `data/minutes_maker/input/` にファイルがない場合は、ユーザーにファイルを配置するよう促す。
- ユーザーからの応答が曖昧な場合は、再度具体的な選択肢を提示して確認する。
