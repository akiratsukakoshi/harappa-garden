---
name: invoice_processor
description: Gmail/Driveの請求書PDFを解析しFreeeへ取引登録するスキル。月次支払処理を塚越さんとステップバイステップで伴走する。
---

# Invoice Processor Skill

Gmail から請求書を取得 → Google Driveに保存 → AI解析でCSV生成 → Freee登録、までを支援するスキル。
**月次の支払処理は shift_manager の `export_external_staff.py` と連動する**。本SKILLは塚越さんとのHuman-in-the-Loopでの段階的処理を前提とする。

## 0. 月次支払処理の全体像

塚越さんが月次の支払処理を依頼してきた場合（例: 「今月の支払い処理を進めます」「請求書を処理して」）、以下の流れを案内・伴走すること。

```
1. invoice_processor で業務委託スタッフの請求書を処理
   a. fetch    — Gmail → Drive (請求書PDFをアップロード)
   b. extract  — Drive PDF → review CSV (AI解析)
   c. review   — 塚越さんがCSV内容を確認・修正
   d. register — Freeeへ登録 (dry-run → 本番)

2. shift_manager で外部スタッフ（請求書なし）のCSV生成
   a. generate_working_hours — worktimeシート生成（金額・区分自動）
   b. export_external_staff  — 「追加」スタッフ → invoice_processor 用 CSV
   c. register (再度 invoice_processor で)

3. shift_manager で給与スタッフを人事労務freeeへ登録
   a. register_payroll — 「給与」スタッフを人事労務freeeに勤怠登録
```

## 1. ステップバイステップ伴走フロー

### Step 1: 開始確認
塚越さんから月次支払処理の依頼があった場合、まず以下を確認する:

- **対象期間**: 「○月分の支払い処理ですね。請求書取得は何日以降のメールを対象にしますか？」（典型: 前月の請求締日翌日 = 月の20日前後）
- **shift_manager側の準備状況**: 「worktimeシート (`{対象月}_稼働時間`) は既に生成済みですか？」 — 未生成なら先にshift_managerフローを案内（[詳細](.agent/skills/shift_manager/SKILL.md)）

### Step 2: Fetch (Gmail → Drive)

```bash
.venv/bin/python apps/invoice_processor/main.py fetch --after YYYY/MM/DD
```

**実行後の伴走事項**:
- アップロードされたファイル一覧（日時・送信元・件名）を提示する
- **送信者ごとに集計し、過去の支払先と照合**:
  - 「先月までに○○さんからは請求が来ていたが今月は来ていない」を指摘
  - 「同じ送信者から複数月分まとめて届いている」場合は塚越さんに確認
- 「Driveの Invoices/Inbox を一度確認して、不要な領収書や重複ファイルがあれば削除してください」と案内
- 削除後の件数を塚越さんに教えてもらう（extract前にDriveが整理された状態にする）

### Step 3: Extract (Drive PDF → CSV)

```bash
.venv/bin/python apps/invoice_processor/main.py extract
```

**注意点**:
- **Gemini APIタイムアウト** が頻発する場合あり (`The read operation timed out` / `503 Service Unavailable`)。全件失敗した場合は10-30分待って再試行
- 処理時間は1ファイルあたり5-10秒、12ファイルで約1-2分
- バックグラウンド実行を推奨（`run_in_background=true`）

**実行後の伴走事項**:
1. **MISMATCH集計を提示** — Warning列に`MISMATCH`があるファイルを一覧化:
   ```
   | ファイル | 請求書合計 | 計算合計 | 差分 | 推定原因 |
   ```
   - 差分の典型パターン:
     - **-(±1500前後)**: 消費税が明細から漏れている
     - **+(±数千〜数万)**: 小計行・合計行が重複計上、または経費を二重計上
     - **大きな差分**: 明細抽出漏れ（複数人分など）
2. **その他の注意点を指摘**:
   - 取引先がFreee未登録 (`partner_id` 空欄) → 新規登録 or 既存先紐付け要
   - `date` が誤抽出（PDF作成日が入っているケース）
   - `account_item_name` に `"description"` がそのまま入っているケース

### Step 4: Review (塚越さんがCSV確認・修正)
**この段階で塚越さんに以下を依頼**:
- CSVファイル (`data/invoice_processor/review/invoice_review_YYYYMMDD_*.csv`) を開いて確認・修正
- 処理不要な行（5月分が混入している等）は削除
- 既に処理済みのファイルがあれば削除＋Drive上の該当PDFをProcessedへ手動移動

**塚越さんから修正完了の合図があったら次へ進む**。
**Drive上の処理スキップファイルがあれば** 以下のコードでProcessedへ移動:

```python
# 該当ファイルのキーワードでマッチして移動
from drive_client import DriveClient
drive = DriveClient()
files = drive.list_files_in_folder(INBOX_ID)
for f in files:
    if "<キーワード>" in f["name"]:
        drive.move_file(f["id"], INBOX_ID, PROCESSED_ID)
```

### Step 5: 外部スタッフCSV（shift_manager連携）

塚越さんに確認: 「**worktimeから追加スタッフ（請求書なしの外部スタッフ）のCSVも生成しますか？**」

YESの場合:
```bash
.venv/bin/python apps/shift_manager/logic/export_external_staff.py --month YYYY-MM
```

**実行後の伴走事項**:
- 出力ファイル: `data/invoice_processor/review/external_staff_YYYYMM.csv`
- `partner_id` 空欄の警告が出た場合 → 塚越さんに「Freeeで取引先を新規登録するか、CSVで partner_id を手入力してください」と案内
- このCSVも次のregister Stepで処理する

### Step 6: Register (dry-run)

**必ず dry-run を先に実行**:
```bash
.venv/bin/python apps/invoice_processor/main.py register \
  --file data/invoice_processor/review/invoice_review_YYYYMMDD_*.csv --dry-run
```

外部スタッフCSVも処理する場合は別途同じコマンドで実行。

**実行後の伴走事項**:
- `Total / Success / Error` を読み上げる
- `Error: 0` でなければ、塚越さんに具体的なエラー内容（`Invalid Account Item` 等）を提示し、CSV修正を依頼

### Step 7: Register (本番)
塚越さんから本番実行の承認を得てから:

```bash
.venv/bin/python apps/invoice_processor/main.py register \
  --file data/invoice_processor/review/invoice_review_YYYYMMDD_*.csv
```

**注意**: 62件登録など件数が多い場合は1-3分かかる。`run_in_background=true` 推奨。

**実行後の伴走事項**:
1. `Registration Summary` の `Error` 件数を確認
2. **Drive移動エラーの解釈**:
   - 外部スタッフCSV分の行（`file_id` が `YYYYMM_extra_NNN` のようなダミー値）はDrive移動でエラーが出るが、**Freee登録は成功している**ので問題なし
   - 「ダミーfile_idのDrive移動エラーは想定通りの挙動です」と説明
3. 自動連携の動作確認:
   - 元のGmailスレッドに「処理済」ラベル付与＋アーカイブ済み
   - Drive上のPDFは Processed フォルダへ移動済み
4. `partner_id` 空欄で登録されたスタッフを名指しで報告: 「○○さんは取引先紐付けなしで登録されています。Freeeで取引先マスタを登録すると今後の処理がスムーズです」

### Step 8: 給与スタッフ（人事労務freee）登録

塚越さんに確認: 「**アルバイトスタッフの勤怠を人事労務freeeに登録しますか？**」

YESの場合（必ず dry-run 先行）:
```bash
.venv/bin/python apps/shift_manager/logic/register_payroll.py --month YYYY-MM --dry-run
.venv/bin/python apps/shift_manager/logic/register_payroll.py --month YYYY-MM
```

詳細は [shift_manager SKILL](../shift_manager/SKILL.md) 参照。

### Step 9: 月次処理完了
塚越さんに完了報告:
- 業務委託 N件、外部スタッフ N件、給与スタッフ N件を登録しました
- 未処理の請求書（来月処理予定）が Inbox に M件残っています
- 取引先未登録のスタッフ: ○○さん、××さん（次回までに登録推奨）

## 2. コマンドリファレンス

### Fetch (Email取得)
Gmailから請求書メールを検索し、添付ファイルをDriveへアップロード。

```bash
.venv/bin/python apps/invoice_processor/main.py fetch
.venv/bin/python apps/invoice_processor/main.py fetch --after 2026/05/18  # 日付指定
```
- 件名キーワード（「請求書」「invoice」「ご請求」など）または `Invoice_Pending` ラベル付きメールが対象
- 処理済みメールには `Invoice_Fetched` ラベル付与

### Extract (データ抽出)
Drive上の未処理ファイルを解析しCSV出力。

```bash
.venv/bin/python apps/invoice_processor/main.py extract
```
- 出力先: `data/invoice_processor/review/invoice_review_YYYYMMDD_HHMMSS.csv`
- AI整合性チェック: 請求書合計と明細合計の差分を `Warning` 列に記録

### Register (Freee登録)
CSV内容をFreeeへ取引（未決済）として登録。

```bash
.venv/bin/python apps/invoice_processor/main.py register --file <CSVパス> --dry-run
.venv/bin/python apps/invoice_processor/main.py register --file <CSVパス>
```
- 登録成功 → Gmailスレッドに「処理済」ラベル + アーカイブ
- 登録成功 → Drive上のPDFを Processed フォルダへ移動
- ダミー file_id（外部スタッフCSV由来）はDrive移動でエラーになるが想定挙動

## 3. ディレクトリ構成

- **Skill**: `.agent/skills/invoice_processor/SKILL.md` (本ファイル)
- **App**: `apps/invoice_processor/main.py`
  - `pdf_analyzer.py` — Gemini APIによるPDF解析
  - `rule_engine.py` — 勘定科目・取引先の推論ルール
  - `drive_client.py` — Google Drive操作
  - `mapping_config.json` — 取引先別の固定ルール辞書
- **Data**: `data/invoice_processor/`
  - `review/` — レビュー用CSV出力先（外部スタッフCSV含む）
  - `temp/` — 一時ファイル（処理後に自動削除）

## 4. トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| Extract全件失敗 (`timeout` / `503`) | Gemini API側の問題 | 10-30分待って再実行 |
| MISMATCHの差分が消費税相当 | 明細から税抜→税込変換漏れ | CSVで金額を税込に修正 |
| `partner_id` 空欄で登録 | Freee取引先未登録 | Freeeで取引先マスタ追加 |
| Drive移動エラー(dummy file_id) | 外部スタッフCSV由来の想定挙動 | 無視してOK |
| `Invalid Account Item` | 勘定科目名がFreeeマスタと不一致 | `account_item_name` 列を修正 |

## 5. 関連スキル
- **shift_manager** — 外部スタッフCSV出力 (`export_external_staff.py`) と給与スタッフ人事登録 (`register_payroll.py`) を提供
- **freee_auditor** — 登録後の部門振り分け漏れチェック
- **expense_processor** — クレカ明細・レシートからの経費登録（請求書とは別フロー）
