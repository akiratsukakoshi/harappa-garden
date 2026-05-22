# Shift Manager (HMC Shift) - ユーザーマニュアル

**Shift Manager** は、原っぱ大学のプログラム日程・シフト管理を行うためのアプリケーションです。
Annual（年次計画）からDB（マスター）、そしてMonthly（月次運用）へとデータを流す「Seed to Master」モデルを採用しています。

## 構成概要

*   **File_Annual**: 年間の予定をざっくり組むためのシード（種）データ。
*   **HMC_Backend_DB**: 全データの正本（マスター）。ここにあるデータが正です。
*   **HMC_Monthly_UI (プログラムカレンダー新)**: 日々の運用で人間が触る画面。

---

## 利用方法

すべての操作はターミナル（コマンドライン）から Python スクリプトを実行して行います。

### 0. 環境の準備 (venv起動)

作業を始める前に、必ずプロジェクトルートに移動し、仮想環境 (venv) を有効化してください。

```bash
# プロジェクトルート (/home/tukapontas/harappa-cockpit/) で実行
cd /home/tukapontas/harappa-cockpit/
source venv/bin/activate
```
※ コマンドの左側に `(venv)` と表示されればOKです。

---

## 1. 年次作業 (Annual Initial Sync)
**頻度**: 年に1回（または年度計画の変更時）

File_Annual（スプレッドシート）に入力した大まかな年間予定を、システムに取り込みます。

### Step 1: スプレッドシートへの入力
`HMC_File_Annual` の各年度シート（例: `UI_Annual_Planner_2026`）に、日付・場所・カテゴリを入力してください。
※ ここでの「カテゴリ」列が重要です。

### Step 2: DBへの取り込み (Annual -> DB)
Annualシートの内容をデータベース (`DB_Master_Events`) に同期します。
※ すでに登録済みのイベントは重複して登録されません（スキップされます）。

```bash
# 例: 2026年度（2026年4月〜2027年3月）を取り込む場合
python apps/shift_manager/logic/annual_to_db.py --year 2026
```

---

## 2. 月次作業 (Monthly Operations)
**頻度**: 毎月〜毎日

### Step 1: 月次シートの生成 (DB -> Monthly)
DBにあるデータを元に、人間が見やすい「月次カレンダー形式」のシートを作成（または再作成）します。
新しい月になったら、まずこのコマンドでシートを作ってください。
※ **注意**: 既存のシートがある場合、内容は上書き（リセット）されます！編集中のデータがある場合は必ず先に保存してください。

```bash
# 例: 2026年4月のシートを作成
python apps/shift_manager/logic/db_to_monthly.py --month 2026-04
```

*   **機能**:
    *   日付・曜日（土日祝の色分け）を自動生成します。
    *   カテゴリ等の入力規則（プルダウン）を設定します。

### Step 2: 日々の調整・編集
作成された月次シート (`HMC_Monthly_UI` / プログラムカレンダー新) をブラウザで開き、詳細情報（時間、スタッフ、備考など）を入力・編集してください。

*   **編集ルール**: 詳しい編集ルールについては、以下のドキュメントを必ず確認してください。
    *   [📄 Monthly UI 操作マニュアル](../manual_monthly_operations.md)
    *   ※「運営スケジュール」列はDBに保存されない点などに注意してください。

### Step 3: DBへの保存 (Monthly -> DB)
月次シートで編集した内容を、データベース (`DB_Master_Events`) に書き戻します。
これを実行しないと、変更がシステム上の正本として確定しません。

```bash
# 例: 2026年4月の内容をDBに保存
python apps/shift_manager/logic/monthly_to_db.py --month 2026-04
```

---

## トラブルシューティング

### Q. Monthlyシートで作った書式（色など）が消えた
**A.** 仕様です。`db_to_monthly.py` (Generate) を実行すると、シートは標準の書式で再生成されます。永続させたい情報は「備考」欄などに文字で記載してください。

### Q. 「運営スケジュール」列がDBに入らない
**A.** それも仕様です。あの列は人間用のメモ欄であり、システム管理外です。

### Q. Annualの内容を変更したが反映されない
**A.** Annualはあくまで「初期データ（Seed）」です。一度DBに取り込まれた後は、**Monthlyシート側**または**DB直接編集**で修正を行ってください。Annualを直してもう一度コマンドを叩いても、既存データは（重複防止のため）更新されません。

---

## 3. シフト管理 (Phase 3: Shift Management)
**頻度**: 毎月 (募集開始〜確定時)

シフト募集から確定までの一連のフローです。

### Step 1: スタッフマスター準備 (Sync Staff)
Freeeの取引先データと手動CSVを統合し、最新のスタッフリストをDBに用意します。
```bash
python apps/shift_manager/logic/sync_staff_master.py
```
※ 手動追加したいスタッフは `data/manual_staff.csv` に追記してください。

### Step 2: 募集フォーム作成 (Generate Form)
Monthlyシートで募集対象のプログラムに「アンケート」フラグを立て、Googleフォームを生成・更新します。

1. **Monthlyシート**: 募集したい行の「アンケート」列 (Q列) にチェックを入れる。
   * **※仕様上の注意**: フォーム生成はMonthlyシートの入力内容（時間など）を**直接読み取って**作成されます。そのため「事前に `monthly_to_db.py` を実行してDBに保存しておく」という手順は**不要**です。
2. **コマンド実行**:
   ```bash
   python apps/shift_manager/logic/generate_shift_form.py --month 2026-01
   ```
3. **フォーム確認**: 出力されたURLを確認し、スタッフに配布します。
   ※ フォームのタイトルや選択肢（日程）は自動更新されます。

### Step 3: 回答の集約 (Aggregate)
フォームの回答を読み込み、専用の「シフト調整用スプレッドシート」に `Shift_Work_YYYY-MM` シートを作成（または更新）します。

```bash
# 例: 2026年1月分を集計
python apps/shift_manager/logic/aggregate_responses.py --month 2026-01
```
*   **出力先**: 別途定義されたシフト集計用スプレッドシート
*   **機能**:
    *   **イベント別集計**: 「日付＋会場＋カテゴリ」ごとに列を分けて集計表を作成します。同日開催の別イベントも区別されます。
    *   **ヘッダー表記**: 「日付(曜日) [改行] 会場 カテゴリ」のように、コンパクトに表示されます。
    *   **スタッフ名**: フォームの「お名前」欄の回答を優先して表示します（未入力の場合はメールアドレス）。
    *   **NG表示**: 「NG」回答のあるセルは赤色で強調表示されます。
    *   **手動調整**: 調整・確定作業は、この作成されたシート上で手動で行ってください（Monthlyカレンダーへの自動反映機能はありません）。

---

## 4. 稼働時間集計と支払処理連携 (Working Hours & Payment)
**頻度**: 毎月（前月の支払処理時）

シフト確定後の稼働時間集計から、Freee/人事労務freee 連携までの一連のフローです。

### Step 1: 稼働時間シート生成
月次シートの内容を集計し、スタッフ別稼働時間シートを生成します。

```bash
python apps/shift_manager/logic/generate_working_hours.py --month 2026-05
```

* **出力先**: `working_hours_id` で指定された専用スプレッドシート（`apps/shift_manager/config_ids.json` 参照）
* **シート構成** (`YYYY-MM_稼働時間` タブ):
  - **A列**: スタッフ名（正式名称）
  - **B〜O列**: 日付別稼働時間 (`h:mm` 形式)
  - **P〜U列**: カテゴリ別時間小計 (SUMPRODUCT 数式)
  - **V列**: 合計時間
  - **W〜AB列**: カテゴリ別金額 (時間 × 時給, ROUND数式) ※自動生成
  - **AC列**: 合計金額 ※自動生成
  - **AD列**: 区分 (`給与` / `業務委託` / `追加`) — `DB_Master_Nicknames` の `PaymentType` 列から自動pre-fill
* **時給単価**: `apps/shift_manager/section_mapping.json` の `hourly_rate` （既定 1250円）
* **放サボ列はオレンジ色のセルで手入力を促す**（人により稼働時間が異なるため）

### Step 2: スタッフへのシフト確認
生成されたシートを元に、スタッフへ稼働時間の確認・合意を取ります（毎月10日まで）。
業務委託スタッフからは請求書がメールで送付されます。

### Step 3: 業務委託スタッフの請求書処理
[invoice_processor マニュアル](invoice_processor.md) の Part 1 を実施します。

### Step 4: 外部スタッフ（請求書なし）のCSV生成
稼働時間シートの **区分=「追加」** のスタッフを、invoice_processor 用のCSVに自動展開します。

```bash
python apps/shift_manager/logic/export_external_staff.py --month 2026-05
```

* **出力先**: `data/invoice_processor/review/external_staff_202605.csv`
* **挙動**:
  - 区分=「追加」のスタッフを抽出
  - カテゴリ別金額（W列以降）で金額>0の部門ごとに1行展開
  - 部門名は `section_mapping.json` で通称→Freee正式部門名に変換（例: `放サボ` → `逗子_放課後サボール`）
  - `partner_id` はFreee取引先から正式名称で照合。未登録は空欄で出力＋警告表示
  - 勘定科目: `section_mapping.json` の `default_account_item` （既定: `外注費`）
  - 日付: 対象月の末日
* このCSVは invoice_processor の register コマンドにそのまま渡せます

### Step 5: アルバイトスタッフの人事労務freee勤怠登録
稼働時間シートの **区分=「給与」** のスタッフを、人事労務freee に勤怠登録します。
人事労務freee 側で時給×時間の給与計算が自動で行われます。

```bash
# 必ず dry-run を先に実行
python apps/shift_manager/logic/register_payroll.py --month 2026-05 --dry-run

# 本登録
python apps/shift_manager/logic/register_payroll.py --month 2026-05

# 既存勤怠データを上書きする場合
python apps/shift_manager/logic/register_payroll.py --month 2026-05 --force
```

* **挙動**:
  - 区分=「給与」のスタッフを抽出
  - 各スタッフの日別稼働時間 (B〜O列) を人事労務freee の `work_records` API でPUT登録
  - HR_Employee_ID は `DB_Master_Nicknames` の F列 で解決
  - **出勤時刻は 09:00 固定**、退勤時刻は 09:00＋稼働分数で自動計算（実際の時刻は人事労務freee 側で修正可能）
* **前提**:
  - `.env` に `FREEE_HR_CLIENT_ID` / `FREEE_HR_CLIENT_SECRET` / `FREEE_HR_COMPANY_ID` が設定済み
  - `modules/freee_hr_client/token.json` に OAuth トークンが保存済み
  - 対象スタッフが `DB_Master_Nicknames` に `PaymentType=給与` と `HR_Employee_ID` が登録済み
* **既存データへの配慮**:
  - 該当日に既に勤怠データがある場合は警告表示でスキップ（`--force` で強制上書き）

---

## 5. マスターデータ管理

### DB_Master_Nicknames シート構成

| 列 | 名称 | 用途 |
|---|---|---|
| A | ニックネーム | カンマ区切りで複数表記対応（例: `ゆーじ, ユージ`） |
| B | 正式名称 | Freeeパートナー名と一致させる |
| C | Freee_ID | 会計freee の取引先ID |
| D | 備考 | 自由記入 |
| E | PaymentType | `給与` / `業務委託` / `追加` — generate_working_hours の AD列に pre-fill される |
| F | HR_Employee_ID | 人事労務freee の従業員ID — register_payroll で使用 |

### PaymentType と対応する処理フロー

| PaymentType | 処理 |
|---|---|
| `業務委託` | 請求書ベース → invoice_processor (fetch → extract → register) |
| `追加` | 請求書なし → shift_manager (export_external_staff) → invoice_processor (register) |
| `給与` | 人事労務freee → shift_manager (register_payroll) |

### section_mapping.json
`apps/shift_manager/section_mapping.json` で通称→Freee正式部門名の対応を管理:

```json
{
  "mapping": {
    "放サボ": "逗子_放課後サボール",
    "おやこ学部": "おやこ学部",
    "おとな学部": "おとな学部",
    "こども学部": "こども学部",
    "企業案件": "企業案件",
    "共創": "共創プロジェクト"
  },
  "default_account_item": "外注費",
  "hourly_rate": 1250
}
```

新カテゴリ追加時はこのファイルに追記してください（例: イベント列が将来追加された場合は `"イベント": "逗子_SSEK"` を追加）。

---
