# Finance Importer - ユーザーマニュアル

**Finance Importer** は、外部決済サービスの売上CSVデータを読み込み、Freee会計に「振替伝票」として自動記帳するアプリケーションです。
AIによる部門推測機能と、登録前のレビューフローを備えています。

## 主な機能
*   **マルチフォーマット:** STORES予約、SquareのCSVに対応。
*   **AI推測:** 取引内容から部門を自動判別。
*   **振替伝票発行:** (借)前受金 / (貸)売上高 の形式で計上。
*   **レビュー:** Freee登録前に中間ファイルで確認・修正が可能。

## 利用方法（AIエージェント / Skill）
本システムは、AIエージェントのスキル `finance_importer` を使用して対話的に操作することを推奨します。

1.  入力CSVを `data/finance_importer/input/` に置く。
2.  エージェントに「csvを処理して」と依頼する。
3.  エージェントがファイルの確認、アップロード、アーカイブまでをガイドします。

## 利用方法（手動実行）

`main_menu.py` を実行し、画面の指示に従ってください。

```bash
# プロジェクトルートで実行
source venv/bin/activate
python main_menu.py
```

### Step 1: Generate Review File (確認用ファイルの作成)
1.  メニューから `1` を選択します。
2.  取り込むCSVの種別（STORES / Square）を選択します。
3.  元のCSVファイルのパスを入力します（例: `data/finance_importer/input/202510_stores.csv`）。
4.  処理が完了すると、`data/finance_importer/review/` フォルダに確認用CSVが生成されます。
    *   **新機能:** `registration_date` 列に、その月の末日が自動計算されて出力されます。
5.  **このCSVをExcel等で開き、内容（部門名や金額、計上日）を確認・修正してください。**

### Step 2: Upload from Review File (Freeeへの送信)
1.  メニューから `2` を選択します。
2.  一覧からアップロードするファイルを選択します。
3.  **"Upload? (Dry run? y/n)"** で `y` を選ぶとテスト実行、`n` で本番登録されます。
4.  登録完了後、Freeeの「振替伝票」一覧にて **(借) 前受金 / (貸) 売上高** として計上されていることを確認してください。

### Step 3: Archive (完了ファイルの移動)
登録が完了したら、処理済みのファイルをアーカイブディレクトリに移動して整理します。

*   AIエージェントを使用している場合は、スキル `finance_importer` により自動で実施されます。
*   手動で行う場合は、以下のディレクトリに移動してください:
    *   元CSV: `data/finance_importer/processed/input/`
    *   確認CSV: `data/finance_importer/processed/review/`

## 設定・カスタマイズ
`apps/finance_importer/mapping_config.json` にて、部門IDのマッピングやCSV列の定義を変更できます。

## 注意事項
*   Freee APIトークンは `modules/freee_tokens.json` に保存され、自動更新されます。
*   AI推測は100%ではありません。必ず確認フローでチェックを行ってください。
