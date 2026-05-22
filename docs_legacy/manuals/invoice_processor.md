# Invoice Processor - ユーザーマニュアル

**Invoice Processor** は、Google Drive にアップロードされた請求書（PDF/画像）を AI が自動解析し、CSVでの一括確認を経て、Freee 会計へ登録するアプリケーションです。
月次の支払処理では、**shift_manager と連動して外部スタッフ・アルバイトスタッフの処理も行います**。

## 主な機能
*   **一括抽出 (Batch Extract):** フォルダ内の全ファイルをAI解析し、編集可能なCSVとして出力
*   **複数行明細:** 1枚の請求書から複数の明細行を自動分割して抽出
*   **ルール辞書:** パートナーごとに勘定科目やFreee取引先IDを固定ルールで適用
*   **shift_manager連動:** worktimeシートの「追加」スタッフCSVを同じregisterコマンドで処理可能

---

## 月次支払処理の全体フロー

毎月の支払処理は以下の3パートで構成されます。AIアシスタント（Claude Code）と対話しながらステップバイステップで進めます。

```
1. 業務委託スタッフ（請求書あり）  → invoice_processor (fetch → extract → register)
2. 外部スタッフ（請求書なし）       → shift_manager (export_external_staff) → invoice_processor (register)
3. アルバイトスタッフ（給与）       → shift_manager (register_payroll) → 人事労務freee
```

### Part 1: 業務委託スタッフの請求書処理

#### Step 1: 請求書メールの取得 (Fetch)
Gmailを検索し、添付ファイルをDriveにアップロードします。

```bash
# 日付指定（推奨）: 前月の請求締日翌日以降を対象に
.venv/bin/python apps/invoice_processor/main.py fetch --after 2026/04/20
```

* 対象: 件名に「請求書」等が含まれるメール、または `Invoice_Pending` ラベル付きのメール
* 処理後、対象メールには `Invoice_Fetched` ラベルが付与されます
* 実行完了時に、アップロードされたファイル一覧（日時・送信元・件名）が表示されます

**実行後の確認**:
* Google Drive の `Invoices/Inbox` を開き、不要な領収書・重複ファイル・処理不要なメールの添付があれば**削除してください**
* 削除した状態で extract に進みます

#### Step 2: データの抽出 (Extract)
Drive上の未処理ファイルをAI解析しCSV出力します。

```bash
.venv/bin/python apps/invoice_processor/main.py extract
```

* 出力先: `data/invoice_processor/review/invoice_review_YYYYMMDD_HHMMSS.csv`
* **Gemini APIタイムアウトに注意**: 全件失敗時は10-30分待って再実行
* 1ファイルあたり5-10秒、10ファイルで約1-2分

**実行後の確認 - MISMATCH対応**:
CSVの `Warning` 列に `MISMATCH` がある行は、請求書の合計金額と明細金額の合計が一致していません:

| 差分パターン | 原因 | 対処 |
|---|---|---|
| -(1500前後) | 消費税が明細から漏れている | 該当行に消費税分を追加 or 既存行を税込に修正 |
| +(数千〜数万) | 小計行・合計行が重複計上 | 重複行を削除 |
| 大きな差分 | 明細抽出漏れ（複数人分など） | PDFを再確認して行を追加 |

#### Step 3: CSV内容の確認・修正 (Review)
生成されたCSVファイルを開き、以下を確認:

* **必須カラム**: `amount`, `date`, `account_item_name`, `tax_code` が空欄でないか
* **取引先**: `partner_id` 空欄なら Freee取引先マスタとの紐付けを確認・修正
* **部門**: `section_name` / `section_id` が正しいか
* **不要な行**: 翌月分が混入している場合は削除
* **既に処理済みのファイル**: 削除＋Drive上の該当PDFをProcessedへ手動移動

**CSVのカラム構成**:
```
file_id, file_name, date, payee, [備考欄], partner_code, partner_id, description,
section_name, section_id, account_item_name, invoice_number, amount,
document_total, calculated_total, diff, warning, tax_code
```

#### Step 4: Freeeへの登録 (Register)

```bash
# 必ず dry-run を先に実行
.venv/bin/python apps/invoice_processor/main.py register \
  --file data/invoice_processor/review/invoice_review_20260521_*.csv --dry-run

# dry-run でエラー0を確認した上で本番実行
.venv/bin/python apps/invoice_processor/main.py register \
  --file data/invoice_processor/review/invoice_review_20260521_*.csv
```

**登録成功時の自動連携**:
* 元の Gmail スレッドに「処理済」ラベル付与＋アーカイブ
* Drive 上のPDFを `Processed` フォルダへ移動

**実行後の確認**:
1. `--- Registration Summary ---` の `Error: 0` を確認
2. エラーがある場合は `Invalid Account Item` や `FAILED` の行を特定し、CSV修正後に再実行

---

### Part 2: 外部スタッフ（請求書なし）の処理

請求書を発行しないスタッフ（大野さん等）の稼働分を、worktimeシートから自動でCSV生成し、invoice_processor で登録します。

#### Step 1: 外部スタッフCSV生成
shift_manager の `export_external_staff.py` を実行:

```bash
.venv/bin/python apps/shift_manager/logic/export_external_staff.py --month 2026-05
```

* 出力先: `data/invoice_processor/review/external_staff_202605.csv`
* worktimeシートの **区分列=「追加」** スタッフの稼働金額を、**部門別に行展開**
* 部門マッピングは `apps/shift_manager/section_mapping.json` で定義（例: `放サボ` → `逗子_放課後サボール`）
* 時給は `section_mapping.json` の `hourly_rate` （既定 1250円）

**警告対応**:
* `partner_id` 空欄のスタッフが表示された場合 → Freeeで取引先新規登録 or CSVで partner_id を手入力

#### Step 2: invoice_processor で登録
上記CSVを通常のregisterコマンドで処理:

```bash
.venv/bin/python apps/invoice_processor/main.py register \
  --file data/invoice_processor/review/external_staff_202605.csv --dry-run

.venv/bin/python apps/invoice_processor/main.py register \
  --file data/invoice_processor/review/external_staff_202605.csv
```

**注意**: 外部スタッフ行は `file_id` がダミー値（`202605_extra_001` 等）のため、Drive移動でエラーが出ますが、**Freee登録自体は成功**しています。想定挙動なので無視してOKです。

---

### Part 3: アルバイトスタッフの人事労務freee登録

worktimeシートの「給与」スタッフを人事労務freeeに勤怠登録し、給与計算を自動化します。

```bash
# 必ず dry-run を先に実行
.venv/bin/python apps/shift_manager/logic/register_payroll.py --month 2026-05 --dry-run

# 本登録
.venv/bin/python apps/shift_manager/logic/register_payroll.py --month 2026-05

# 既存勤怠を上書きする場合
.venv/bin/python apps/shift_manager/logic/register_payroll.py --month 2026-05 --force
```

* 出勤時刻は **09:00 固定**、退勤時刻は 09:00＋稼働分数で自動計算
* 人事労務freee 側で 時給×時間 で給与が自動計算されます（時給は人事労務freee 側で管理）
* 詳細は [shift_manager マニュアル](shift_manager.md) を参照

---

## 4. 便利な機能

### マスタデータの取得
パートナーIDや部門IDなどの最新リストを取得:

```bash
.venv/bin/python apps/invoice_processor/export_masters.py
```
出力: `data/invoice_processor/master_data.csv`

### ルール（辞書）の設定
よく使う支払先の勘定科目を固定化: `apps/invoice_processor/mapping_config.json` を編集

```json
{
  "partner_rules": {
    "Amazon": {
      "name": "Amazon Japan G.K.",
      "account": "消耗品費"
    }
  }
}
```

---

## 5. トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| Extract全件失敗 (`timeout` / `503`) | Gemini API側の一時障害 | 10-30分待って再実行 |
| MISMATCH多発 | PDF品質や明細フォーマット由来 | CSVで個別修正 |
| `Invalid Account Item` | 勘定科目名がFreeeマスタと不一致 | CSV `account_item_name` を Freee の正式名称に |
| Drive移動エラー(dummy file_id) | 外部スタッフCSV由来 | 想定挙動。無視してOK |
| 取引先未登録警告 | スタッフがFreee未登録 | Freeeで新規取引先登録 |

---

## 6. 関連ドキュメント
* [shift_manager マニュアル](shift_manager.md) - worktime生成・外部スタッフCSV・人事給与登録
* [invoice_processor 技術仕様](../specs/invoice_processor.md)
* [shift_manager 技術仕様](../specs/shift_manager.md)
