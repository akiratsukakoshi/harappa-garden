---
name: expense_processor
description: ガクチョ個人のクレジットカード明細・レシート画像から Freee 経費登録候補を抽出し、board 剪定依頼にして承認後に Freee 登録する区画。月末リマインド → 翌月2日抽出 → 承認登録の三段。master / Discord 完結。
plot: expense_processor
topics: [経費, 経費登録, 経費精算, クレカ, クレジットカード, 明細, レシート, 領収書, freee, 勘定科目, 費目, 部門, PayPay, イオン, コスモ, Gemini, OCR, 月末, 翌月2日, 個人経費]
inherits_from:
  - garden/CHARTER.md
  - expense_processor (HMC)
requires_soil_index: false      # Freee が正本。soil 参照は不要
created: 2026-06-05
last_updated: 2026-06-05
created_by: claude (with ガクチョ, セッション35 / plot_gardener 初 dogfood)
origin: docs/decisions/2026-06-04-plot-gardener-and-vocabulary-registers.md
linked_seeds:
  - expense_processor/month-end-reminder
  - expense_processor/monthly-expense-draft
linked_services:
  - garden/services/expense-processor (Python: processor.py 移植予定 = Phase 2)
  - garden-gaku-co (Discord master 対話 = 承認・手動起動の入口)
linked_workflows: []
linked_soil: []
---

# expense_processor — 個人経費の Freee 登録(候補抽出 → 承認 → 登録)

expense_processor 区画は、ガクチョ個人のクレジットカード明細(CSV)とレシート画像から **Freee 経費登録の候補** を抽出し、**Freee 登録の前にガクチョが確認・修正できる board(剪定依頼)** を用意する区画です。承認後に Freee へ実登録します。

HMC の `expense_processor`(`apps/expense_processor/processor.py`)を **移植型(transplant)** で Garden 化したもの。**業務知識(パーサ・Gemini 分類・Freee 登録)は全部継承し、変えたのは「起動」と「承認」だけ** です。

> 共通の業務観・呼称・トーン・Output Style 質感は [garden/CHARTER.md](../../CHARTER.md) を参照。本 SKILL は expense_processor 固有の手順・判断ルールに集中します。
> 起源: HMC `.agent/skills/expense_processor/SKILL.md` + `apps/expense_processor/processor.py`。

---

## scope(通行手形)

**master / Discord 完結**。Freee は財務機微なので、`core_team` / `staff` の通行手形には **一切入れません**(LINE registry にも載せない = 構造遮断)。承認も実登録も Discord master(= Claude Code が native に Freee を叩ける)で完結します。

| scope | 使えること | 禁止 |
|---|---|---|
| master(Discord) | 抽出 / 候補確認 / 修正 / dry-run / Freee 登録 | — |
| core_team / staff | **何もなし** | 財務 tool を集合に入れない |

---

## SSOT(本 plot の正本)

- **Freee = 当月経費の正本**。Garden は「抽出 → 登録」の橋渡しを担うだけで、登録済みデータの正本は Freee 側。
- **input フォルダ = 未処理の明細・レシート置き場**。Google Drive の `EXPENSE_DRIVE_FOLDER_ID/input/`(ガクチョが端末から置く)。processor が同期 → ローカル処理 → `proceeded/YYYYMMDD/` にアーカイブ。
- 費目(勘定科目)5 分類: `旅費交通費 / 原材料 / 消耗品費 / 通信費 / 会議費`。**Freee 側に同名の勘定科目が存在する前提**(完全一致でないと登録時スキップ)。

---

## ファイルと役割

| ファイル | 役割 | 備考 |
|---|---|---|
| `garden/services/expense-processor/processor.py` | extract / upload 本体(HMC 移植) | **Phase 2 で移植**(secret 必要) |
| `garden/services/expense-processor/lib/freee_client.py` | Freee API(post_deal / get_account_items / get_sections) | HMC `modules/freee_client/client.py` フル移植 |
| `garden/services/expense-processor/lib/drive_client.py` | Google Drive 同期・アーカイブ | HMC `apps/invoice_processor/drive_client.py` 移植 |
| `garden/services/expense-processor/lib/sheets_client.py` | レビュー用 Sheets 書き出し / 読み戻し(`to-sheet` / `from-sheet`) | **S38 案A**。gspread + 同 SA。ガクチョ所有ワークブック(`EXPENSE_REVIEW_SHEET_ID`)に `{YYYYMM}` タブ |
| `garden/services/expense-processor/secrets/` | Freee OAuth / GEMINI_API_KEY / Google Drive SA(600 perm) | git 除外・VPS 配置 |
| `garden/board/pending/{today}-expense-draft.md` | 抽出候補の剪定依頼 | Mode 2 が生成 / ガクチョが確認・承認 |
| `garden/log/{today}-expense-draft.log` | 種の実行ログ | 種が追記 |

---

## Mode 1: Month-end Reminder(月末 — フォルダ投入のリマインド)

**起動**: 種 `expense_processor/month-end-reminder`(cron 毎月最終日)。

### 目的
翌月2日の自動抽出に間に合うよう、ガクチョに「今月のカード明細・レシートを input フォルダに置いて」とリマインドします。**実処理はしません**(通知のみ)。

### 動作
- Discord master に 1 通通知。**Google Drive の input フォルダ URL を必ず含める**(その場で開けるように):
  - URL = `https://drive.google.com/drive/folders/{EXPENSE_DRIVE_FOLDER_ID}`(値は env から runtime 構成、repo に焼かない)
- 文面例:
  > 🧾 来月2日に経費処理します。今月のカード明細(PayPay / イオン)とレシート画像を経費フォルダに置いておいてください。
  > 📁 {input フォルダ URL}
  > 空なら処理はスキップします。間に合わなくても「経費まわして」で後からいつでも回せます。

---

## Mode 2: Extract & Draft(翌月2日 — 抽出して board 起草)

**起動(2 入口)**:
1. 種 `expense_processor/monthly-expense-draft`(cron 毎月2日 08:00)
2. **手動**: ガクチョが Discord master で「経費まわして」「経費やって」「経費の抽出して」等 → Discord ガクコ(Claude Code)が本 Mode を on-demand 実行(2日に間に合わなくても、任意のタイミングで同じフローが回る)

### 目的
input フォルダの明細・レシートを抽出し、Freee 登録候補の一覧を board(剪定依頼)にしてガクチョに提示します。

### Step 1: 抽出
```bash
# ⚠️ 絶対パス + cd なしで実行(Bash 権限はこの絶対パス形式にのみ scoped allow。
#    cd や相対 .venv/bin/python だと拒否される。processor.py は内部パスが絶対なので cwd 不問)
/home/vps-harappa/garden/services/expense-processor/.venv/bin/python \
  /home/vps-harappa/garden/services/expense-processor/processor.py extract
```
- Drive `input/` → ローカル同期 → CSV(PayPay UTF-8 / イオン・コスモ Shift-JIS 自動判別)+ 画像(Gemini OCR)を解析
- 費目を Gemini が 5 分類から推定 → 中間 CSV(`working/expenses_YYYYMMDD_HHMMSS.csv`)を出力

### Step 2: 空判定(★重要)
- **input が空 = 抽出 0 件** → board は作らず、Discord master に「空でスキップ」を通知して終了:
  > 🧾 {対象月}の経費、input フォルダが空でした。今月は処理なしでスキップします。明細が出たら「経費まわして」と言ってください。
- 抽出 1 件以上 → Step 3 へ

### Step 2.5: レビュー用 Sheets 化(S38 案A — 直接編集の面)
件数が多い月にチャット往復が破綻しないよう、抽出結果を **Google Sheets** に書き出して
ガクチョが直接一括編集できるようにします。

```bash
# working_csv は Step 1 の標準出力末尾の絶対パス。標準出力に REVIEW_SHEET_URL / REVIEW_TAB が出る
/home/vps-harappa/garden/services/expense-processor/.venv/bin/python \
  /home/vps-harappa/garden/services/expense-processor/processor.py to-sheet <working_csv>
```
- ガクチョ所有のレビュー用ワークブック(`EXPENSE_REVIEW_SHEET_ID`)に `{YYYYMM}` タブを作成。
- 費目はプルダウン(5分類)、要確認行は黄色。列は working CSV と 1:1(位置固定・並べ替え禁止)。
- 出力の `REVIEW_SHEET_URL`(`#gid=` 付き)と `REVIEW_TAB` を次の Step で使う。

### Step 3: board に剪定依頼を起草
`garden/board/pending/{today}-expense-draft.md` に:
- 抽出候補の一覧(発生日 / 費目 / 内容 / 金額 / ソース)。費目別の件数サマリも付ける
- **要確認フラグ**: `[要確認:日付不明]`(画像抽出で日付取れず)/ 費目が「消耗品費」フォールバックの可能性が高い行
- frontmatter に必ず(承認時に from-sheet で読み戻すため):
  - `working_csv:` … Step 1 の中間 CSV 絶対パス
  - `review_sheet_url:` … Step 2.5 の `REVIEW_SHEET_URL`
  - `review_tab:` … Step 2.5 の `REVIEW_TAB`(= `{YYYYMM}`)

### Step 4: 庭師通知
- Discord master に 1 行通知(**Sheet URL を必ず含める**):
  > 🧾 {対象月}の経費候補、{N}件を抽出しました。直接編集できる表 → {REVIEW_SHEET_URL}
  > 費目内訳: 旅費交通費{a} / 消耗品費{b} / 会議費{c} …。要確認{r}件は黄色。
  > 件数が多ければ Sheet で一括編集、少しならチャットでも。編集したら「承認」で Freee 登録します。

### べき等性
- 同月の board(pending/processed)が既存なら **新規発火しない**
- `proceeded/` にアーカイブ済みの明細は再処理しない(upload 後に input → proceeded へ移動するため二重登録を防ぐ)

---

## Mode 3: Approval → Freee Upload(承認 — Discord で確認して登録)

**起動**: ガクチョが Discord master で expense board に対し承認/修正/却下を指示した時。**master = Claude Code が VPS で直接 Freee を叩く**(send_pending 等の配信機構は経由しない)。

### 編集の正本(S38 案A)
- Step 2.5 で **Sheets を出している**(通常運用)→ ガクチョの編集はその Sheet が正本。承認時は必ず
  **`from-sheet {review_tab}`** で読み戻し、出力の `REVIEWED_CSV` を upload の入力にする
  (board frontmatter の `review_tab` を使う)。
- 金額が空/0 の行(= Sheet で削除された行)は from-sheet が自動でスキップする。

### 指示の分類と動作

| ガクチョの自然言語 | 動作 |
|---|---|
| 「承認」「OK」「登録して」「上げて」 | **`from-sheet {review_tab}` → REVIEWED_CSV** を **必ず先に `upload --dry-run`** で確認 → 1 行報告 → 問題なければ本登録 |
| 「N件目の費目を会議費に変えて承認」(少量のチャット修正) | Sheet 未編集前提なら working CSV の該当行を Edit(費目 / 金額 / 部門 / 内容)→ dry-run → 本登録。**Sheet を出した後は Sheet 側で直してもらい from-sheet を使う**(二重編集回避) |
| 「N件目は除外」「これは経費じゃない」 | Sheet ならその行を削除してもらう(from-sheet が空/0 行をスキップ)。チャット少量なら working CSV から該当行削除 → dry-run → 本登録 |
| 「却下」「やめて」「来月でいい」 | 登録せず board を pending 残置(or processed へ手動移動) |
| 「board 見せて」「中身出して」 | board 全文を Read して Discord に貼る(Sheet URL も併記) |

### 登録の安全規範
- **必ず dry-run を先に通し、件数・合計額・費目をガクチョに 1 行で見せてから本登録**(`これで12件・合計¥84,300を登録します。いい?`)。
- 本登録は `processor.py upload {REVIEWED_CSV or 中間CSV}`(dry-run なし)。成功後:
  - input ファイル + 中間 CSV を `proceeded/YYYYMMDD/` にアーカイブ(Drive も `processed/YYYYMMDD/` へ移動)
  - board を `garden/board/processed/` へ移動
  - Discord に完了報告(`✅ {N}件を Freee 登録(未決済 / 支払期日=各月末)。アーカイブ済`)
- **費目が Freee の勘定科目名と完全一致しない行はスキップされる**(HMC 挙動)。dry-run でスキップが出たら、本登録前にガクチョに知らせて費目名を直す。

---

## 判断ルール(HMC 既知の失敗から継承)

| 状況 | ルール |
|---|---|
| 費目が Freee の勘定科目名と不一致 | 登録時スキップ → **未登録分に退避**(`working/FAILED_*.csv`)。dry-run で検出 → 費目名を正す(5 分類は Freee に同名科目がある前提) |
| 部門(department)が Freee の部門名と不一致 | 部門なしで登録される。必要なら CSV の department 列を正確な部門名に |
| 画像抽出で日付不明 | `details` に `[要確認:日付不明]` が付く。board でガクチョに発生日を確認してから登録 |
| **発生日が会計年度の期首日以前**(S37 で実発生) | Freee が 400 で弾く(`期首日以前の取引を登録することができません`)。**画像 OCR の年読み間違いが主因**(他が当年なのに 1 件だけ数年前等)。実日付に直して再登録、or 不要なら除外 |
| Gemini が費目に迷う | `消耗品費` にフォールバック。**必ず人間が確認** |
| Gemini 429 レート制限 | service 内で指数バックオフ・リトライ済(3 回) |
| 同月 board が既存 | 新規発火しない(べき等性) |
| 登録前 | **必ず dry-run を先に通す** |
| 二重登録 | 登録成功が 1 件以上の時のみ input → proceeded へアーカイブ。アーカイブ済みは再処理しない |
| **partial 失敗(一部だけ登録失敗)** | S37 改善:**失敗行は `working/FAILED_{ts}.csv` に退避**(成功分はアーカイブ=二重登録防止、失敗分は残す)+ **exit code 1** + ログ末尾に `==NOTIFY==` アラーム。修正して `processor.py upload working/FAILED_*.csv` で再登録 |
| **全件失敗(登録 0 件)** | アーカイブをスキップ(input / CSV を残し再試行可能に) |

---

## Output Style(expense_processor 固有)

CHARTER の Output Style 質感に従いつつ、固有のセクション順:

`🧾 抽出結果` → `⚠️ 要確認` → `💴 登録サマリ(dry-run)` → `🔖 判断ほしい`

### 良い締めの例
- 「6月分、12件を抽出しました。うち1件が日付不明([要確認])、2件は費目が消耗品費フォールバックです。dry-run の合計は ¥84,300。要確認3件だけ先に直しますか? それともこのまま登録でいいですか?」

---

## このSKILLを参照する種・サービス

| 名前 | 役割 | SKILL の参照範囲 |
|---|---|---|
| `garden/seeds/expense_processor/month-end-reminder.md` | 月末 cron リマインド | Mode 1 |
| `garden/seeds/expense_processor/monthly-expense-draft.md` | 毎月2日 08:00 cron 抽出 | Mode 2 全体 + Output Style |
| `garden/services/garden-gaku-co/bot.py`(Discord) | 承認・手動起動の入口 | Mode 2(手動)+ Mode 3 全体 |
| `garden/services/expense-processor/processor.py` | extract / upload 本体 | (SKILL ロード不要・機械処理) |

---

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ✋ | post_deal の tax_code 既定が `1`(課税売上10%) | **経費は本来 課税仕入**。S37 で構造対処済 + 値確定:`EXPENSE_TAX_CODE=136`(課対仕入10%)を設定し post_deal に明示指定 | **対処済(136 設定済)** |
| ✋ | 費目分類が 1 行 1 Gemini 呼び出し | **S37 実運用で 77 件(画像16+CSV61行)が 5 分タイムアウトに当たった**。S38 で対処:**CSV 明細の費目分類をバッチ化**(複数行を 1 プロンプト → JSON 配列で受けて入力順に復元、`EXPENSE_CLASSIFY_BATCH_SIZE` 既定40)+ **画像 OCR を並列化**(`EXPENSE_IMAGE_OCR_WORKERS` 既定4)+ ファイル毎 `time.sleep(2)` 撤去。バッチ失敗/行数不一致/JSON 不正時はその範囲だけ 1 行ずつフォールバック | **対処済(S38)** |
| 💡 | 費目は固定 5 分類 | ガクチョの実費目分布に合わせて追加/調整(config 化) | 構想中 |
| ✋ | Discord「経費まわして」→ ガクコが実行 | **S38 配線済(Route A)**。bot.py に expense SKILL を話題検知ロード + processor.py を Bash で直接実行(settings.json で当該 venv python の絶対パスのみ `:*` scoped allow・他は default-deny)+ run_claude timeout 300s + working/ Edit/Write 許可。「経費まわして」→ Mode 2 extract→board / 「承認」→ Mode 3 dry-run→本登録。⚠️ Bash 権限は**絶対パス形式のみ**マッチ(`cd &&`・相対パスは拒否) | **対処済(S38)** |
| ❓ | input は Google Drive 手置き | Discord 添付 → 自動配置経路(kodomon-sync γ 構想と同型) | 構想中 |
| 💡 | リマインドは月末固定 | 前月の登録漏れ(proceeded に無い月)を検知して催促を強める | 構想中 |

---

## 関連

- 共通規範: [garden/CHARTER.md](../../CHARTER.md)
- メタ区画: [garden/plots/plot_gardener/SKILL.md](../plot_gardener/SKILL.md)(本区画は plot_gardener 初 dogfood)
- 起源: HMC `.agent/skills/expense_processor/SKILL.md` / `apps/expense_processor/processor.py` / `docs/specs/expense_processor.md`
- 種スキーマ: [garden/seeds/README.md](../../seeds/README.md)
- 関連区画: [shift_manager](../shift_manager/SKILL.md)(同じく master 系・board 承認パターン)

---

## このSKILLの昇格状態

- 段階: **active**(S37 で初回リアル実走完了。**cron + 手動[Claude Code 実行]は運用可能**。Discord ガクコ経由の「経費まわして」だけ未配線=改善余地参照)
- active 条件:
  1. [x] Phase 2: `garden/services/expense-processor/` 移植(processor.py + lib/freee_client フル + lib/drive_client + lib/utils、S37)
  2. [x] secret(Freee 共有 token / GEMINI_API_KEY / Drive service account)VPS 配置 + .env + venv(S37)
  3. [x] tax_code 確定(`EXPENSE_TAX_CODE=136` 課対仕入10%)
  4. [x] dry-run 検証(S37)
  5. [x] 種 2 本の cron 登録(S37)
  6. [x] **初回リアル実走(S37): ガクチョの実明細を extract → 本人が CSV 直接レビュー・除外/部門付与 → Freee 登録 59 件(¥397,373)**。うち 2 件は会計年度期首日以前(OCR 年誤読)で弾かれ → 2026 年に修正して再登録。partial 失敗ハンドリング(FAILED 退避 + exit1 + ==NOTIFY==)も実装
- 残(active 後の改善): ~~Discord ガクコ経由「経費まわして」の配線~~(S38 Route A 済)/ ~~費目分類のバッチ化(タイムアウト対策)~~(S38 済)/ OPERATIONS 運用カード / **初回 Discord 実走の見届け**(「経費まわして」→ board → 承認 → Freee 登録を bot 経由で 1 周)
