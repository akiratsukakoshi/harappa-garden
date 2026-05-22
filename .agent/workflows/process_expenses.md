---
description: 経費処理（抽出～確認～登録）を実行するワークフロー
---

1. 以下のコマンドを実行して、入力データ（CSV/画像）から経費データを抽出します。
   ```bash
   ./venv/bin/python3 apps/expense_processor/processor.py extract
   ```

2. 生成された中間CSVファイル（`data/expense_processor/working/` 内）を確認するようユーザーに促します。

3. ユーザーの確認・修正が完了したら、以下のコマンドでデータをFreeeへアップロードします。
   ※最初は `--dry-run` を推奨します。

   ```bash
   # Dry Run
   ./venv/bin/python3 apps/expense_processor/processor.py upload data/expense_processor/working/<LATEST_CSV> --dry-run
   ```

4. 問題なければ本番アップロードを実行します。

   ```bash
   # Production Upload
   ./venv/bin/python3 apps/expense_processor/processor.py upload data/expense_processor/working/<LATEST_CSV>
   ```
