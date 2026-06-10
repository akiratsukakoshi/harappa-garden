---
name: invoice_processor
description: Gmail に届く請求書 PDF を月次で取得・解析し、スタッフリスト照合と稼働突合(請求漏れ検出)つきの Freee 登録候補をガクチョに剪定依頼、承認後に Freee 登録する区画。毎月12日 cron + 手動「請求書まわして」。master / Discord 完結。
plot: invoice_processor
topics: [請求書, インボイス, invoice, 支払, 月次支払, 業務委託, 外注費, freee, 取引先, partner, Gmail, 添付, PDF, Gemini, スタッフ照合, 稼働突合, 請求漏れ, 12日, リスト外]
inherits_from:
  - garden/CHARTER.md
  - invoice_processor (HMC)
requires_soil_index: false      # staff は SOIL_STAFF_DIR を service が直接読む
created: 2026-06-10
last_updated: 2026-06-10
created_by: claude (with ガクチョ, セッション41 / plot_gardener 2nd dogfood)
origin: garden/plots/plot_gardener/SKILL.md
linked_seeds:
  - invoice_processor/monthly-invoice-draft
linked_services:
  - garden/services/invoice-processor (Python: processor.py)
  - garden-gaku-co (Discord master 対話 = 承認・手動起動の入口)
linked_workflows: []
linked_soil:
  - garden/soil/people/staff/   # スタッフ照合の正本(contract / freee_id)
---

# invoice_processor — 請求書の Freee 登録(取得 → 照合 → 承認 → 登録)

invoice_processor 区画は、Gmail に届く請求書(業務委託スタッフの月次請求 + 取引先・ベンダーの請求)を取得・解析し、**Freee 登録の前にガクチョが確認・修正できる剪定依頼** を用意する区画です。承認後に Freee へ実登録します。

HMC の `apps/invoice_processor/`(fetch / extract / register)を **改植型(hybrid)** で Garden 化したもの。業務知識(Gemini 解析・ルール推論・Freee 登録・MISMATCH 補正)は継承しつつ、**S41 で 2 つの新機能** を足しました:

1. **スタッフ照合** — 請求元を soil スタッフマスター(`contract` / `freee_id`)と照合し、「スタッフの請求書」と「リスト外(取引先・ベンダー)」を分けて見せる
2. **稼働突合(請求漏れ検出)** — 前月の稼働時間シート(区分=業務委託)と突合し、**稼働があるのに請求書が来ていない人** を検出する

リスト外の請求書も **同じフローで Freee 登録まで進む**(レビューで薄い青に色分けされるだけ)。

> 共通の業務観・呼称・トーンは [garden/CHARTER.md](../../CHARTER.md) を参照。
> 起源: HMC `.agent/skills/invoice_processor/SKILL.md` + `apps/invoice_processor/`。

---

## scope(通行手形)

**master / Discord 完結**。Freee・支払情報は財務機微なので、`core_team` / `staff` の通行手形には **一切入れません**(LINE registry にも載せない = 構造遮断。expense_processor と同じ)。

| scope | 使えること | 禁止 |
|---|---|---|
| master(Discord) | fetch / 抽出 / 照合確認 / 修正 / dry-run / Freee 登録 | — |
| core_team / staff | **何もなし** | 財務 tool を集合に入れない |

---

## SSOT(本 plot の正本)

- **Freee = 登録済み取引の正本**。Garden は橋渡しのみ。
- **Gmail + Drive Inbox = 未処理請求書の置き場**。件名キーワード(請求書/invoice/領収書…)or `Invoice_Pending` ラベルで対象化。ラベルで状態管理(`Invoice_Fetched` → `処理済`)。
- **soil スタッフマスター(`garden/soil/people/staff/`)= スタッフ照合の正本**(contract / freee_id)。スタッフが増減したら soil を直す(この区画は読むだけ)。
- **稼働時間シート(`{YYYY-MM}_稼働時間`)= 前月稼働の正本**(shift-manager が生成、ワークブック ID は shift-manager config の `working_hours_id`)。
- 勘定科目・部門・支払先の推論ルール: `garden/services/invoice-processor/config/mapping_config.json`(HMC 継承)。

---

## ファイルと役割

| ファイル | 役割 | 備考 |
|---|---|---|
| `garden/services/invoice-processor/processor.py` | fetch / extract / check / to-sheet / from-sheet / register | HMC 移植 + 新機能 2 本 |
| `lib/gmail_client.py` | Gmail API(gog CLI 置き換え) | user OAuth token |
| `lib/staff_master.py` | soil スタッフ照合(★新機能 1) | freee_id → 氏名正規化の 2 段 |
| `lib/worktime.py` | 稼働時間シート読取(★新機能 2) | 区分=業務委託 を抽出 |
| `lib/sheets_client.py` | レビュー用 Sheets(`INVOICE_REVIEW_SHEET_ID` の `{YYYYMM}` タブ) | expense S38 案A と同 UX |
| `garden/services/invoice-processor/secrets/` | user_token.json / oauth_credentials.json(600 perm) | git 除外・VPS 配置。Freee token は shift-manager と物理共有 |
| `garden/board/pending/{today}-invoice-draft.md` | 抽出候補 + 突合結果の剪定依頼 | Mode 1 が生成 |
| `garden/log/{today}-invoice-draft.log` | 種の実行ログ | 種が追記 |

---

## Mode 1: Monthly Draft(毎月12日 — 取得・照合して board 起草)

**起動(2 入口)**:
1. 種 `invoice_processor/monthly-invoice-draft`(cron 毎月12日 08:00)
2. **手動**: ガクチョが Discord master で「請求書まわして」「請求書処理して」等 → Discord ガクコが本 Mode を on-demand 実行(遅れて届いた請求書の再処理もこれ。べき等なので何度でも可)

### 目的
前月分の請求書を Gmail から取得・解析し、スタッフ照合 + 稼働突合の結果つきで登録候補をガクチョに提示します。

### Step 1: fetch(Gmail → Drive Inbox)
```bash
# ⚠️ 絶対パス + cd なしで実行(Bash 権限は絶対パス `:*` 形式にのみ scoped allow)
/home/vps-harappa/garden/services/invoice-processor/.venv/bin/python \
  /home/vps-harappa/garden/services/invoice-processor/processor.py fetch
```
- 件名キーワード or `Invoice_Pending` ラベルの添付を Drive Inbox へ(ファイル名に thread_id 前置)
- 取得済みスレッドは `Invoice_Fetched` ラベルで二重取得を防ぐ(べき等)

### Step 2: extract(解析 + ★スタッフ照合)
```bash
... processor.py extract
```
- Gemini 解析 → ルール推論(支払先正規化 / 部門 / 勘定科目 / 税区分)→ `working/invoices_*.csv`
- 全行に `staff_slug / staff_contract / group(スタッフ or リスト外)` が付く
- 標準出力: `REVIEW_CSV` / `EXTRACT_ROWS` / `EXTRACT_STAFF_FILES` / `EXTRACT_OUTSIDE_FILES`

### Step 3: 空判定(★重要)
- **fetch 0 件かつ Inbox 空(EXTRACT_ROWS: 0)** → board は作らず「今月は請求書なしでスキップ。届いたら『請求書まわして』と言ってください」を通知して終了
- 1 件以上 → Step 4 へ

### Step 4: check(★稼働突合 — 請求漏れ検出)
```bash
... processor.py check --month {前月 YYYY-MM}
```
- 前月の `{YYYY-MM}_稼働時間` シートの **区分=業務委託** で稼働がある人と、Step 2 のスタッフ請求書を突合
- `CHECK_MISSING:` に **稼働があるのに請求書が無い人** が出る(稼働時間つき)
- シートがまだ無い月は `NO_WORKTIME_SHEET`(突合不可の旨を board に明記して続行)

### Step 5: レビュー用 Sheets 化
```bash
... processor.py to-sheet {REVIEW_CSV} --tab {前月YYYYMM}
```
- スタッフ請求が先頭・リスト外(薄い青)が後ろ。MISMATCH 等の警告行は黄色
- 勘定科目・部門はプルダウン。列の並べ替えは禁止(from-sheet が位置でマップ)

### Step 6: board に剪定依頼を起草
`garden/board/pending/{today}-invoice-draft.md` に:
- サマリ: スタッフ請求 {n}名 / リスト外 {m}件 / **請求漏れ疑い {k}名(名前 + 稼働時間)** / 警告 {w}件
- frontmatter に必ず: `target_month:` / `working_csv:` / `review_sheet_url:` / `review_tab:`

### Step 7: 庭師通知(Discord master、Sheet URL 必須)
> 🧾 {前月}分の請求書、{総件数}件を処理しました(スタッフ {n}名 / リスト外 {m}件)。
> ⚠️ 稼働があるのに請求書が無い人: {names or なし}
> 直接編集できる表 → {REVIEW_SHEET_URL}
> 確認して「承認」で Freee 登録します。漏れの人には催促を。

### べき等性
- 同月の board(pending/processed)が既存なら新規発火しない(手動の再処理は board 更新で対応)
- fetch は `Invoice_Fetched` ラベル、register 済みは `処理済` ラベル + Drive 移動で多重処理を防ぐ

---

## Mode 2: Approval → Freee Register(承認 — Discord で確認して登録)

**起動**: ガクチョが Discord master で invoice board に対し承認/修正/却下を指示した時。master = Claude Code が VPS で直接実行(send_pending 非経由)。

### 編集の正本
- ガクチョの編集は **レビュー Sheet が正本**。承認時は必ず `from-sheet {review_tab}` で読み戻し、`REVIEWED_CSV` を register の入力にする
- 行の削除 or 金額を空/0 にした行は from-sheet が自動スキップ(= 除外)

### 指示の分類と動作

| ガクチョの自然言語 | 動作 |
|---|---|
| 「承認」「OK」「登録して」 | `from-sheet {review_tab}` → **必ず `register --file {REVIEWED_CSV} --dry-run` を先に** → 件数・合計額を 1 行報告 → OK で本登録 |
| 「○○の請求書は除外」 | Sheet で行削除してもらう(or こちらで金額を 0 に)→ from-sheet → dry-run → 本登録 |
| 「却下」「来月まとめる」 | 登録せず board を pending 残置 |
| 「board 見せて」 | board 全文 + Sheet URL を Discord に貼る |

### 登録の安全規範
- **必ず dry-run を先に通し、件数・合計額をガクチョに見せてから本登録**
- 本登録成功後(service が自動で実施): Gmail スレッドに `処理済` ラベル + アーカイブ / Drive Inbox → Processed(エラー行のファイルは Error)
- board を `garden/board/processed/` へ移動 + Discord に完了報告(`✅ {N}件を Freee 登録(支出・未決済)`)

---

## 判断ルール(HMC 既知の失敗から継承 + S41 追加)

| 状況 | ルール |
|---|---|
| MISMATCH(請求総額 ≠ 明細合計)±1,500 前後 | 消費税が明細から漏れている可能性。Sheet の黄色行を確認 |
| MISMATCH ±数千〜数万 | 小計/合計行の重複計上 or 経費二重計上の可能性 |
| MISMATCH 大きな差分 | 明細抽出漏れ(複数人分の請求等)。元 PDF を確認 |
| `partner_id` 空欄 | Freee に取引先が未登録。新規登録するか既存先に紐付けてから登録(空欄のまま登録すると摘要に支払先名が前置される) |
| **スタッフなのにリスト外判定**(★S41) | 屋号で請求している可能性(niyatto design = 吉田さん等)。`config/mapping_config.json` の partner_rules に屋号を足す + soil の freee_id を確認 |
| **請求漏れ検出**(★S41) | 稼働シートに居て請求書が無い人 → ガクチョから催促。**自動催促はしない**(人間関係はガクチョの領分) |
| 勘定科目が Freee と不一致(`Invalid Account Item`) | 登録時スキップ → dry-run で検出して科目名を直す |
| Gemini timeout / 503 | service 内で 429 リトライ済。503 連発時は 10–30 分待って手動再実行 |
| 外部スタッフ CSV 由来の行(file_name 空) | Drive/Gmail 後始末を自動スキップ(HMC ではエラーが出ていた想定挙動を解消済) |
| 登録前 | **必ず dry-run を先に通す** |

---

## Output Style(invoice_processor 固有)

CHARTER の Output Style 質感に従いつつ、固有のセクション順:

`🧾 取得・抽出結果` → `👥 スタッフ照合(請求漏れ)` → `⚠️ 要確認(MISMATCH/取引先未登録)` → `💴 登録サマリ(dry-run)` → `🔖 判断ほしい`

### 良い締めの例
- 「5月分の請求書、9件を処理しました(スタッフ7名 / リスト外2件)。稼働があるのに請求書が無いのは守田さん(32h)だけです。MISMATCH が1件(黄色)。表を確認して『承認』で登録します。守田さんには催促お願いします。」

---

## このSKILLを参照する種・サービス

| 名前 | 役割 | SKILL の参照範囲 |
|---|---|---|
| `garden/seeds/invoice_processor/monthly-invoice-draft.md` | 毎月12日 08:00 cron | Mode 1 全体 + Output Style |
| `garden/services/garden-gaku-co/bot.py`(Discord) | 承認・手動「請求書まわして」の入口 | Mode 1(手動)+ Mode 2 全体 |
| `garden/services/invoice-processor/processor.py` | 機械処理本体 | (SKILL ロード不要) |

---

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| 💡 | 請求漏れはガクチョが手動で催促 | 該当スタッフへの自動リマインド(LINE/メール)。ただし人間関係の機微があるため当面ガクチョ経由 | 構想中 |
| 💡 | 稼働突合は「請求の有無」のみ | 請求金額 vs 稼働時間×単価の金額突合(過大/過小請求の検出) | 構想中 |
| 💡 | 外部スタッフ(区分=追加)の稼働払い CSV は HMC `export_external_staff.py` のまま | Garden に移植して register に直結(月次支払の完全 Garden 化) | 構想中 |
| 💡 | 給与スタッフの人事労務 freee 登録は手動 | HMC SKILL の Step 8 相当。別区画 or 本区画 Mode 追加 | 構想中 |
| 💡 | fetch は cron 月1回 | 週次 fetch + 12日に extract だけ回す(月末駆け込み請求の取りこぼし対策) | 構想中 |

---

## 関連

- 共通規範: [garden/CHARTER.md](../../CHARTER.md)
- メタ区画: [garden/plots/plot_gardener/SKILL.md](../plot_gardener/SKILL.md)(本区画は 2 回目の dogfood)
- 類似区画: [expense_processor](../expense_processor/SKILL.md)(同じ master 系・Sheets レビュー・承認登録パターン)
- 起源: HMC `.agent/skills/invoice_processor/SKILL.md` / `apps/invoice_processor/`
- soil: [garden/soil/people/staff/](../../soil/people/staff/README.md)(照合の正本)

---

## このSKILLの昇格状態

- 段階: **draft → test**(S41 で起草 + VPS デプロイ + スモーク検証 GREEN まで完了。初回実走待ち)
- active 条件:
  1. [x] VPS デプロイ(rsync + venv + .env + secrets 600)(S41)
  2. [x] ⭐ user OAuth token 発行(ローカル issue_token.py → ガクチョ同意 → VPS scp)(S41)
  3. [x] ⭐ レビュー用ワークブック作成(`INVOICE_REVIEW_SHEET_ID`)(S41)
  4. [x] スモーク検証(Gmail 検索 10 スレッド / Drive Inbox / check 実シートで請求漏れ 7 名検出[0h 除外] / Sheets ラウンドトリップ / launcher --dry-run)(S41)
  5. [x] 種 cron 登録(毎月12日 08:00)+ Discord「請求書まわして」配線(bot.py 話題検知、S41)
  6. [ ] 初回実走(7/12 or 手動)で board → 承認 → Freee 登録を 1 周 → **active 昇格**
