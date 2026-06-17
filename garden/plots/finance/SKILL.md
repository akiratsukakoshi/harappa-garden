---
name: finance
description: 原っぱ大学の財務区画。売上記帳(STORES/Square CSV → Freee 振替伝票)・データ整合性の地ならし(部門漏れ + 未登録明細)・財務分析(PL/CF/着地予測の対話)を月次サイクルで束ねる。HMC の finance_importer / freee_auditor / finance_analyzer の transplant 移植。master / Discord 完結。
plot: finance
topics: [財務, 売上記帳, 振替伝票, STORES, Square, 売上CSV, freee, 勘定科目, 部門, 部門漏れ, 監査, データ整合性, 未登録明細, 口座明細, wallet_txns, PL, 損益, キャッシュフロー, CF, 着地予測, 財務分析, 戦略議論, 試算表, 営業利益, 販管費, 目標, finance_importer, finance_analyzer, freee_auditor]
inherits_from:
  - garden/CHARTER.md
  - finance_importer (HMC)
  - finance_analyzer (HMC)
  - freee_auditor (HMC)
requires_soil_index: false        # Freee が正本。soil 参照は不要
created: 2026-06-17
last_updated: 2026-06-17
created_by: claude (with ガクチョ, セッション47 / plot_gardener transplant)
origin: docs/decisions/2026-06-04-plot-gardener-and-vocabulary-registers.md
linked_seeds:
  - finance/monthly-sales-import
  - finance/monthly-data-audit
  - finance/monthly-finance-review
linked_services:
  - garden/services/finance (importer.py / auditor.py / analyzer.py)
  - garden-gaku-co (Discord master 対話 = 承認・手動起動・財務議論の入口)
linked_workflows: []
linked_soil: []
status: test                      # S47: VPS デプロイ + 実API スモーク GREEN + cron3本 + bot 配線。月次サイクル初回1周見届けで active
---

# finance — 財務区画(売上記帳 / データ整合性 / 財務分析)

finance 区画は、原っぱ大学の**月次の財務オペレーション**を 1 区画に束ねたものです。HMC の 3 スキルを **transplant 移植**しました(業務知識は全部継承、変えたのは「起動」と「承認」だけ):

| モード | HMC 由来 | 役割 | Freee |
|---|---|---|---|
| **I 記帳(importer)** | finance_importer | 売上CSV(STORES/Square)→ 振替伝票候補 → 承認 → Freee 記帳 | **書込** |
| **D 監査(auditor)** | freee_auditor | 部門漏れ + 未登録明細を検出 → 部門を修正(analyzer の地ならし) | **書込(破壊的)** |
| **A 分析(analyzer)** | finance_analyzer | PL/CF/着地予測を対話。月次に Discord へ投げかけ | 読取のみ |

> 共通の業務観・呼称・トーン・Output Style 質感は [garden/CHARTER.md](../../CHARTER.md) を参照。
> 起源: HMC `.agent/skills/{finance_importer,finance_analyzer,freee_auditor}/` + `apps/同/`。

---

## scope(通行手形)

**master / Discord 完結**。財務は機微 + 外部書込なので、`core_team` / `staff` の通行手形には **一切入れません**(LINE registry にも載せない = 構造遮断)。

| scope | 使えること | 禁止 |
|---|---|---|
| master(Discord) | 記帳 / 監査 / 分析 / dry-run / Freee 書込 | — |
| core_team / staff | **何もなし** | 財務 tool を集合に入れない |

---

## 月次サイクル(この区画の季節)

ガクチョ設計(S47)。**前段が整地してから次が走る**直列フロー:

```
5日       ガクチョが STORES/Square 売上CSV を Drive にアップ   ← recurring task
6日 08:00  種 I 記帳   importer fetch→generate→Sheets→board    ← 承認で Freee 記帳
9日 08:00  種 D 監査   auditor scan(部門漏れ + 未登録明細)     ← analyzer 前の地ならし
10日 08:00 種 A 分析   analyzer summary → Discord に対話の投げかけ
```

- どのモードも **任意タイミング起動可**(「売上記帳まわして」「部門監査まわして」「財務見せて」)。
- 6日の記帳はガクチョ承認待ち。9日の監査・10日の分析は**その時点の Freee 状態**で走る(承認が遅れていれば投げかけにその旨を添える)。

---

## SSOT(本 plot の正本)

- **Freee = 財務の正本**。Garden は「CSV → 記帳」「漏れ → 修正」「Freee → 分析」の橋渡し。
- **売上CSV置き場** = Drive の `FINANCE_SALES_DRIVE_FOLDER_ID`(ガクチョが毎月5日にアップ)。register 成功後 `processed/YYYYMMDD/` へ自動退避(二重記帳防止)。
- **部門マスター = 実 Freee が正本**。importer の Sheets ドロップダウン・register の name→id、auditor の scan・dropdown・apply は**すべて実行時に `get_sections()` で実 Freee を参照**(S47 deploy 時に HMC 移植の旧 config が現行27区画とずれていた[「逗子_放課後サボール」→「放課後サボール」等]ため、config 依存をやめた)。`config/mapping_config.json` の sections は section_guesser のヒント用(現行化済・ドリフトしても登録は壊れない)。
- **目標値** = **正本は [soil/finance/targets.md](../../soil/finance/targets.md)**(経営知識)。`config/targets.json` は analyzer が目標比計算で機械読みするミラー(`analyzer.py targets` で設定)。ずれたら soil を正とする。
- **経営の議論知識** = [soil/finance/discussions/](../../soil/finance/discussions/)(継続性の正本)。財務分析は service でなく soil を読む(Mode A 参照)。
- 振替伝票の構造: **借方=前受金(対象外)/ 貸方=売上高(課税売上10%)**、起票日=取引月の月末、摘要に `[FinanceImporter]` タグ。

---

## Mode I: 売上記帳(STORES/Square → Freee 振替伝票)

**起動(2入口)**: ① 種 `finance/monthly-sales-import`(cron 毎月6日 08:00)② 手動「売上記帳まわして」。

### フロー
1. `importer.py fetch` — Drive の売上CSV を `input/` に取得(`FETCHED_FILES: N`)
2. `importer.py generate` — `input/` を **stores/square 自動判定**で解析 → 振替伝票候補の review CSV。**部門はルール推定**(完全一致 → keyword。当たらなければ空欄)。出力 `REVIEW_CSV` / `EXTRACT_ROWS` / `SECTION_MISSING`
3. **空判定(★重要)**: `EXTRACT_ROWS: 0`(= CSV 未アップ or 売上なし)→ board を作らず Discord に「今月は売上CSVが無いのでスキップ。アップしたら『売上記帳まわして』」と通知して終了
4. `importer.py to-sheet {REVIEW_CSV} --tab {YYYYMM}` — レビュー用 Sheets タブ作成。**部門列はプルダウン(16区画)、部門が空の行は黄色**(ガクチョが埋める箇所)。`REVIEW_SHEET_URL` を控える
5. board 起草(`garden/board/pending/{today}-sales-import.md`)— サマリ(件数 / 合計額 / 部門未設定 {SECTION_MISSING}件)+ frontmatter に `review_tab` / `review_sheet_url` / `target_month`
6. Discord 通知(Sheet URL 必須):「💴 {月}分の売上 {N}件 ¥{合計} を記帳候補に。部門未設定 {k}件は黄色で表示。表で部門を埋めて『承認』で振替伝票を作ります → {URL}」

### 承認(Mode I 登録)
master の Discord でガクチョが「承認」したら:
1. `importer.py from-sheet {review_tab}` → `REVIEWED_CSV`(金額空/0 の削除行はスキップ)
2. `importer.py register {REVIEWED_CSV} --dry-run` → 件数・合計を 1 行で提示(`これで {N}件・¥{合計} を振替伝票にします。いい?`)
3. OK で `importer.py register {REVIEWED_CSV}`(本登録)→ Drive 原本を `processed/` へ自動退避 → board を processed へ
- **部門が空の行も登録は通る**(部門なし = 全社共通扱い)。後で Mode D が拾うので止めない。

---

## Mode D: データ整合性の地ならし(analyzer の前処理)

**起動(2入口)**: ① 種 `finance/monthly-data-audit`(cron 毎月9日 08:00)② 手動「部門監査まわして」。

> ⚠️ 役割(S47 ガクチョ再定義)= 「監査して終わり」ではなく **analyzer が走る前にデータの整合性をある程度自動で整える地ならし役**。

### 検出は2本立て
`auditor.py scan --month {YYYY-MM}` が2つを出す:

1. **部門振り分け漏れ**(`section_id` 空の明細)→ `AUDIT_MISSING` / `AUDIT_CSV`。**Sheets レビュー → dry-run → PUT で修正**(下記)。
2. **未登録明細**(口座と同期済みだが取引化されていない = PL に未反映の `wallet_txns`)→ `UNREGISTERED_TXNS` + `UNREGISTERED_STATUS_BREAKDOWN` + サンプル。**MVP は検出して報告まで**(自動登録アシストは初回実データを見てから境界決め。expense と重なる分はそちらへ)。

### 部門漏れの修正(書込・破壊的なので board + dry-run 必須)
1. `auditor.py to-sheet {AUDIT_CSV} --tab audit{YYYYMM}` — 部門列プルダウン。ガクチョが各行に部門を入れる
2. board 起草 + Discord 通知(「🔧 {月}の部門未設定 {k}件。表で部門を埋めて『承認』で Freee に反映 → {URL}。未登録明細も {u}件あります(下記)」)
3. 承認 → `auditor.py from-sheet {tab}` → `auditor.py apply {csv} --dry-run`(**必ず先に dry-run**。件数と各行の部門を提示)→ OK で `auditor.py apply {csv}`(PUT。ロールバック無しなので慎重に)

### 未登録明細の判定(S47 確定済)
freee 明細(`wallet_txns`)の `status==1` = **未登録(取引化されていない = PL未反映)**、`status==2` = 登録済み。S47 実データ(2026-05、`{1:16, 2:23}`、サンプルは status=1 が Square/STORES の振込入金・手数料 = 取引化前)で確認 → ガクチョ承認済。`auditor.py` の `_scan_unregistered` は `UNREGISTERED_STATUS=1` で headline を絞り、全 status 内訳は透明性のため報告継続。<br>**TODO(active 後)**: 未登録明細の自動登録アシスト(勘定科目推定 → board → 登録)。口座/カード明細は expense_processor の領域と重なる分があるので境界を引いてから。

---

## Mode A: 財務分析(PL/CF/着地予測の対話 — read-only)

**起動(2入口)**: ① 種 `finance/monthly-finance-review`(cron 毎月10日 08:00 → Discord に投げかけ)② 手動「財務見せて」「PL見せて」「キャッシュ大丈夫?」等の対話。

### ⭐ 継続性(最初に必ず読む)
財務の議論は単発でなく**地続き**。分析・投げかけの前に [garden/soil/finance/](../../soil/finance/)(**VPS では `/home/vps-harappa/garden-mirror/garden/soil/finance/`** = soil-sync 管理)を読む:
- `soil/finance/discussions/` = 過去の経営議論ログ(議事録)。前回どこまで議論し、何を見込んだか。
- `soil/finance/targets.md` = 年間目標と達成戦略の**正本**(service の targets.json はその機械読みミラー)。
- toB 案件の見込みは [soil/projects/toB-pipeline.md](../../soil/projects/toB-pipeline.md)。
**月次の壁打ちが一段落したら、その回の議論を `soil/finance/discussions/{YYYYMMDD}_{題}.md` に追記**(継続性を切らさない)。

### コマンド(すべて read-only)
- `analyzer.py check` — データ品質(部門未設定・未決済の月別件数)。Mode D の必要性判断に使う
- `analyzer.py pl [--start-month N --end-month N]` — 月次 PL テーブル + CSV
- `analyzer.py cf [--months N]` — 口座残高 + 月次CF推移 + 年度末予測(資金ショート月検出)
- `analyzer.py summary` — 戦略議論用サマリー(JSON + テキスト)。`SUMMARY_JSON` を出力
- `analyzer.py targets --set-revenue … --set-operating-profit …` — 目標値設定(VPS 正本)

### 月次の投げかけ(10日の種)
`analyzer.py summary` を実行 → 出力(YTD実績 / 着地予測 / 現金残高 / 月次トレンド)を読み、**ガクチョに数値 + 論点で対話を投げかける**。数字を貼るだけでなく「ここを一緒に考えたい」を 1〜2 点。例:
> 📊 {FY} {n}ヶ月経過。売上 YTD ¥{x}(目標比 {p}%)、営業利益 ¥{y}。現ペース着地は売上 ¥{z}で目標 {gap}。現金 ¥{cash}。
> 気になる点:① {月}の営業利益が {理由}で凹んでいる ② 着地は強気/基本/保守でどう置く?
> どこから話そう?

### 財務の見方・議論フレーム(HMC finance_analyzer から継承する核)
**この区画の最重要資産**。数値を出すだけでなく、次の枠で議論する:

| 指標 | 定義 | 見方 |
|---|---|---|
| 売上高 | 試算表「売上高」credit−debit | 目標比・月次トレンド |
| 売上総利益 | 売上高 − 売上原価 | HARAPPA はサービス中心で原価ほぼ0 |
| 販売管理費(SGA) | 試算表「販売管理費」 | **許容ラインを意識**(固定費・人件費・通信費) |
| 営業利益 | 粗利 − SGA | 本業利益 ≒ CF 近似値 |
| 目標比 | 実績 / 目標 × 100 | 目標は `targets.json` |

議論フレーム:
1. **現状診断** — 実績 vs 目標の乖離(売上・営業利益別)+ 月別トレンド(ボラティリティ)。toB 単発案件は計上月に営業利益を大きく振らす → 安定 toC ベースをコア資産と位置づける
2. **CF 安全性** — 資金ショート月の有無。残高不足なら売上前倒し / 支出遅延
3. **着地シナリオ** — 強気(全案件達成)/ 基本(中程度削減)/ 保守(安全サイド)の3本を並べる。`summary` の予測は「現ペース継続」の機械試算なので、**季節変動は手で補正**
4. **アクション** — 売上施策 / コスト管理 / 資金調達(不足時のみ)

### HMC 既知の注意(継承)
- `summary`/`projected` の年度末予測は**機械的な現ペース外挿**。12月・3月の販管費スパイク等の季節変動を機械試算すると誤差大 → 議論で手当て
- `walletables` が一部銀行(かながわ信金等)で残高を返さないことがある → 手動確認で補足
- `targets.json` 未設定だと目標比表示がスキップ

---

## 判断ルール(横断)

| 状況 | ルール |
|---|---|
| 売上CSVの形式不明 | stores/square 自動判定に外れた CSV はスキップ(ログに警告)。ガクチョに形式を確認 |
| 部門がルールで当たらない | **空欄のまま**(AI 推測しない)。Sheets で黄色 → ガクチョが埋める。財務は勝手に推定しない |
| 振替伝票の勘定科目が Freee に無い | register が弾く。`売上高`/`前受金` が Freee に同名で存在する前提 |
| Freee 書込(register / apply) | **必ず dry-run を先に通し、件数・合計を 1 行で提示してから本登録** |
| 部門一括修正(apply) | PUT は**全フィールド送信・ロールバック無し**。dry-run 必須。承認なしで走らせない |
| 二重記帳 | register 成功後に Drive 原本を processed へ退避。同月 board 既存なら新規発火しない(べき等) |
| 未登録明細の自動登録 | **MVP では行わない**(検出・報告のみ)。実データで境界を決めるまで書込しない |
| 分析(Mode A) | read-only。Freee を一切書き換えない |

---

## Output Style(finance 固有)

CHARTER の質感に従いつつ、モード別の締め:
- **記帳**: `💴 記帳候補` → `🏷️ 部門未設定(要入力)` → `🧮 dry-run サマリ` → `🔖 承認ほしい`
- **監査**: `🔧 部門漏れ` → `📥 未登録明細(PL未反映)` → `🧮 dry-run` → `🔖 承認ほしい`
- **分析**: `📊 実績` → `📈 着地予測` → `💰 CF` → `🗣️ 一緒に考えたい論点`

---

## このSKILLを参照する種・サービス

| 名前 | 役割 | SKILL 参照範囲 |
|---|---|---|
| `garden/seeds/finance/monthly-sales-import.md` | 毎月6日 cron 記帳 | Mode I |
| `garden/seeds/finance/monthly-data-audit.md` | 毎月9日 cron 監査 | Mode D |
| `garden/seeds/finance/monthly-finance-review.md` | 毎月10日 cron 分析投げかけ | Mode A |
| `garden/services/garden-gaku-co/bot.py`(Discord) | 承認・手動起動・財務議論の入口 | Mode I/D 承認 + Mode A 対話 |
| `garden/services/finance/{importer,auditor,analyzer}.py` | 各モード本体 | (機械処理・SKILL ロード不要) |

---

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| 💡 | 未登録明細は検出・報告のみ | 初回実データで `wallet_txns` の未登録 status を確定 → 自動登録アシスト(勘定科目推定 → board → 登録)。expense と領域が重なる分は境界を引く | 構想中(実データ待ち) |
| 💡 | 部門推定はルールのみ | 当たらない摘要のパターンを keyword_rules に追記して命中率を上げる(AI 推測は入れない方針) | 随時 |
| 💡 | 着地予測は機械的な現ペース外挿 | 季節変動(12月・3月の販管費)を織り込んだ補正モデル | 構想中 |
| 💡 | 部門別 PL 深掘り | `get_trial_pl(section_id=...)` で部門別貢献度を出す(HMC は未実装だった) | 構想中 |

---

## 関連

- 共通規範: [garden/CHARTER.md](../../CHARTER.md)
- メタ区画: [garden/plots/plot_gardener/SKILL.md](../plot_gardener/SKILL.md)(本区画は transplant 移植)
- 起源: HMC `apps/finance_importer/` `apps/finance_analyzer/` `apps/freee_auditor/`
- 関連区画: [expense_processor](../expense_processor/SKILL.md) / [invoice_processor](../invoice_processor/SKILL.md)(同じ master 系・Freee・Sheets レビュー・board 承認パターン)
- 種スキーマ: [garden/seeds/README.md](../../seeds/README.md)

---

## このSKILLの昇格状態

- 段階: **test**(S47 VPS デプロイ + 実 API スモーク GREEN。月次サイクル初回1周見届けで active)
- active 条件:
  1. [x] VPS デプロイ(rsync + venv + .env + secrets 600)(S47)
  2. [x] ⭐ secret 配置:Freee 共有 token / SA credentials / `FINANCE_SALES_DRIVE_FOLDER_ID` / `FINANCE_REVIEW_SHEET_ID`(全て配置済、S47)
  3. [x] スモーク実 API GREEN(S47): analyzer check[FY全月]・summary[売上¥15.9M/営業利益▲¥2.85M]/ auditor scan[部門漏れ23 + 未登録明細16(status==1)]/ **Sheets ラウンドトリップ(importer/auditor とも to-sheet→from-sheet GREEN)**/ importer generate + register --dry-run[月末起票・部門/勘定科目/税の解決 GREEN]
  4. [x] 種3本 cron 登録(6日/9日/10日)+ bot 配線(売上記帳/部門監査/財務見せて)+ settings.json finance venv 許可 + recurring r019(5日 CSVアップ)(S47)
  5. [ ] **月次サイクル初回1周見届け**(5日アップ → 6日記帳 → 9日監査 → 10日投げかけ)→ **active 昇格**
- 済(S47): **未登録明細の status 確定** = 実データ `{1:16, 2:23}` + サンプル(status=1 = Square/STORES振込・手数料 = 取引化前)→ ガクチョ確認 → `_scan_unregistered` を **status==1 で filter**(全内訳は透明性で報告継続)。**TODO(active 後)**: 未登録明細の自動登録アシストの境界決め(expense と被る分)
