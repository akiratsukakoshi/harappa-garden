---
name: plot_gardener
description: 業務フローを HMG の区画(plot)= SKILL / 種 / 通行手形 / service の束へ変換するためのメタ区画。HMC レガシーの移植型と新規業務の新植型を分けて扱い、毎回の判断を「議論」から「分類」に落とす。
plot: plot_gardener
topics: [Garden化, 区画, plot, SKILL, 種, 通行手形, capability, workflow, HMC移植, レガシー, service, 業務設計, 移植, 新植, transplant, seedling, hybrid, LegacyInventory]
inherits_from:
  - garden/CHARTER.md   # 全 plot 共通の業務観・呼称・トーン・Output Style 質感
created: 2026-06-04
last_updated: 2026-06-11   # S42: active 昇格(3 モード完走)
created_by: claude (with ガクチョ, セッション33 / codex 測量士サンプル起点)
origin: docs/surveyor/letters/2026-06-03-plot-gardener-skill-sample.md
linked_outputs:
  - garden/plots/{plot}/SKILL.md
  - garden/seeds/{plot}/{seed}.md
  - garden/services/{plot}/
  - garden/OPERATIONS.md
  - docs/decisions/{date}-{topic}.md
---

# plot_gardener — 区画を作るためのメタ区画

plot_gardener は、個別 tool を量産するための区画ではありません。

役割は、ガクチョから渡された **業務(workflow)を読み、HMG の構造に沿って一つの区画(plot)へ変換する** ことです。区画とは「ワークフロー起点の **SKILL + 種 + 通行手形 + service** の束」= 庭師が言う「業務のパック」そのもの(shift_manager / daily-pilot がその第1・2号)。

> 共通の業務観・呼称・トーン・Output Style 質感は [garden/CHARTER.md](../../CHARTER.md) を参照。本 SKILL は「業務を区画化する」手順・判断ルールに集中します。
> 語彙の正本(設計言語 vs 実装層の 2 register)は [docs/garden-vocabulary.md](../../../docs/garden-vocabulary.md)。

**この区画の価値は、作業を自動化することより、毎回の判断を「議論」から「分類」に落とすことにあります。** だから初回から全自動の生成器を目指しません。Claude Code がセッション中に読む **判断手順書** として機能すれば十分です。

---

## 用語の固定(2 register)

業務を区画化するとき使う 5 つの語は、2 つの register(言語層)に割れます。**庭師が設計するのは上 3 つだけ。tool / service は Garden(Claude)が水面下で選ぶ。**

| 用語 | register | 意味 | 例 |
|---|---|---|---|
| **種 (seed)** | 設計言語 | 発芽条件。いつ・何を起動するか | 月初 1 日 08:00 に board 起草 |
| **通行手形 (capability)** | 設計言語 | scope ごとの権限境界。誰がどの行動を使えるか | `master` / `core_team` / `staff` |
| **SKILL** | 確立語 | 業務の作法書。判断ルール・手順・トーン・例外処理 | `garden/plots/{plot}/SKILL.md` |
| **tool** | 実装層(水面下) | LLM が対話中に呼べる単一目的の手道具 | `search_staff`, `list_pending_boards` |
| **service** | 実装層(水面下) | 裏側で動く実装。Python / JS / daemon / webhook | `generate_working_hours.py`, `send_pending.py` |

補助語:

| 用語 | 意味 |
|---|---|
| **workflow** | 業務の目的・現状の流れ・承認点(`garden/soil/workflows/` が正本) |
| **plot(区画)** | 業務ドメインの区画。上記すべての束 = 「業務のパック」 |
| **board(連絡板)** | 庭師またはスタッフに判断を求める剪定依頼 |

重要な分離:

- **種 ≠ tool**。種 = 自律起動のきっかけ / tool = 起動後または対話中に使う手道具。混ぜない。
- **通行手形は code 内では `capability` と英語表記**(`capabilities.py` 等)。設計議論では「通行手形」を使う。
- **tool / service は水面下**。ガクチョの依頼に出さず、設計判断の単位にもしない。「SKILL と通行手形に定義されていれば、tool の粒度は Garden が決める」。

---

## この区画の入力(ガクチョからの依頼単位)

依頼は、原則として次のどちらかの粒度で受け取ります。**tool / service の具体は Claude Code / Garden 側で選ぶので、ガクチョが粒度を決める必要はありません。**

```text
{業務名} を移植型で Garden 化して。HMC レガシーを活かして、まず MVP の SKILL + 種まで。
```

```text
{業務名} を新植型で Garden 化したい。workflow から整理して。
```

依頼が曖昧な場合は、最初に **Garden 化モード** だけ確認します。

---

## Garden 化モード

最初に必ず mode を判定します。

| mode | 意味 | 最初に読むもの |
|---|---|---|
| `transplant`(移植型) | HMC に既存 SKILL / script / app / config がある | HMC レガシー一式 |
| `seedling`(新植型) | HMC に対応物がない新規業務 | workflow / ガクチョの説明 |
| `hybrid`(改植型) | 既存実装はあるが、業務設計を大きく変える | HMC レガシー + 新 workflow |

判断に迷う場合は `hybrid` として扱い、レガシーを読んだうえで、何を継承し何を捨てるかを明示します。

---

## Mode 1: Intake(依頼の受け取り)

### 目的

ガクチョの依頼を、区画化に必要な最小情報へ整えます。

### Step 1: 依頼を要約

```markdown
## Garden 化対象

- 業務名:
- mode: transplant / seedling / hybrid
- MVP:
- 想定 scope: master / core_team / staff / external
- 期待する成果:
```

### Step 2: 不足情報を聞く(最大 3 つまで)

全部を質問しません。最初に聞くのは次の優先順で最大 3 つ:

1. HMC レガシーがあるか
2. 最初の MVP は何か
3. 誰が使うか(scope = どの通行手形に出すか)

### Step 3: すぐ決めないことを明示

次は Garden 側で決めるため、ガクチョに細かく聞きすぎません(水面下):

- tool を何個作るか
- Python / JS / API / shell の実装方式
- 内部ディレクトリ詳細
- 全 cron 設計
- 将来の全通行手形

---

## Mode 2: Legacy Inventory(transplant / hybrid 用)

### 目的

HMC レガシーを捨てず、業務知識・失敗知・実装資産を Garden に移します。

> **合言葉: 業務知識は継承する。起動と承認の形だけ Garden に変える。**

### Step 1: HMC 側の棚卸し

HMC 側(`/home/tukapontas/harappa-cockpit/`)を読み、次の表を作ります。

```markdown
## Legacy Inventory

### 参照元

- HMC SKILL:
- scripts:
- config:
- secrets:
- data/input:
- output:
- cron / trigger:
- external services:
- known failures:
- useful behavior:
- obsolete behavior:

### 継承分類

| 資産 | 分類 | 理由 | Garden 側の扱い |
|---|---|---|---|
|  | そのまま使う / Garden 作法に包む / SKILL に吸い上げる / 捨てる |  |  |
```

### Step 2: 4 分類する

| 分類 | 扱い |
|---|---|
| **そのまま使う** | API client、CSV parser、Google Sheets 操作、既存 config mapping など |
| **Garden 作法に包む** | board 承認、seed frontmatter、cron、OPERATIONS カード |
| **SKILL に吸い上げる** | 判断ルール、例外処理、文面トーン、既知の失敗 |
| **捨てる / 置き換える** | HMC の人間起動前提、古い path、手動メニュー前提、重複機構 |

### Step 3: レガシーを読む前に実装しない

`transplant` / `hybrid` では、HMC レガシーを読む前に新規実装へ進みません。

例外:

- HMC 側が存在しないことを確認済み
- ガクチョが明示的に「ゼロから作り直す」と判断した
- レガシーが壊れていて、読む価値がないことを短く記録した

---

## Mode 3: Workflow Spec(seedling / hybrid 用)

### 目的

新規業務または大きく設計を変える業務について、workflow を区画化できる粒度にします。

### Spec テンプレート

```markdown
## Workflow Spec

### 業務名
### 目的
### 現状の流れ
### 理想の流れ
### 起きてほしいタイミング
### ガクチョの承認が必要な点
### 自動でやってよい点
### 関係する人・scope
### 入力元
### 出力先
### 失敗時に知らせてほしいこと
### まず MVP でよい範囲
```

### 判断ルール

- **目的(Purpose)と現状の方法(Current Method)を混ぜない**(CLAUDE.md の workflow 原則)。
- 目的は workflow の核として守る。現状の方法は改善対象として扱う。
- 承認点が 3 つ以上ある場合は、MVP では 1 つに絞れるか検討する。
- `staff` scope に出るものは、個人情報・給与・財務・契約情報を特に分離する(通行手形で構造遮断、prompt 頼みにしない)。

---

## Mode 4: Garden Design(成果物の設計)

### 目的

Intake / Legacy Inventory / Workflow Spec をもとに、作るものを最小セットに絞ります。

### 標準出力

```markdown
## Garden Design

### plot(区画)
- name:
- purpose:
- topics:
- requires_soil:
- linked_workflows:

### SKILL
- 作成/更新:
- 主な Mode:
- SSOT:
- 判断ルール:

### seeds(種)
| seed | trigger | 何を起草/実行するか | 承認境界 |
|---|---|---|---|
|  |  |  |  |

### services / tools(水面下 = Garden が選ぶ)
| 名前 | 種別 | 役割 | 実装方針 |
|---|---|---|---|
|  | service / tool |  |  |

### capability(通行手形)
| scope | 使えること | 禁止すること |
|---|---|---|
| master |  |  |
| core_team |  |  |
| staff |  |  |

### board / notification
- board を作る条件:
- Discord / LINE 通知:
- 失敗時:

### OPERATIONS 更新
- 運用カードを追加するか:
- HMC -> HMG 移行表を更新するか:
```

### 設計原則

- **命名規約は [ADR 2026-06-10](../../../docs/decisions/2026-06-10-naming-convention.md) に従う**: plot 名(`plots/` と `seeds/` のディレクトリ)= underscore(`expense_processor`)、実行体(`services/` ディレクトリ・種ファイル・シェルスクリプト・コンテナ)= hyphen(`expense-processor` / `monthly-expense-draft.md`)。Python モジュールは PEP 8 で underscore。既存の不一致はリネームしない(絶対パス参照の破壊リスク)。
- 最初の MVP は **SKILL + 種 1 本 + 必要最小 service** を基本にする。
- read / draft 系は core_team へ出しやすい(通行手形に入れやすい)。
- **execute 系は原則 board を挟む**。
- 外部サービスへ書き込む場合は、承認境界を明示する。
- `garden/MAP.md` より先に `garden/OPERATIONS.md` の運用カードを更新する。

---

## Mode 5: Implementation Plan(Claude Code への作業分解)

### 目的

Claude Code が迷わず着手できる単位に分解します。

### 出力テンプレート

```markdown
## Implementation Plan

### Phase 0: 読む
- [ ] HMC レガシー:
- [ ] workflow:
- [ ] soil:
- [ ] related ADR:

### Phase 1: 骨格
- [ ] `garden/plots/{plot}/SKILL.md`
- [ ] `garden/seeds/{plot}/{seed}.md`
- [ ] 必要な service skeleton

### Phase 2: 実処理
- [ ] HMC logic 移植 / 新規 service 実装
- [ ] board 起草
- [ ] log / failure behavior

### Phase 3: capability / 対話(通行手形)
- [ ] tool が必要なら registry 追加(`tools/registry.py`)
- [ ] scope ごとの capability 設定(`capabilities.py`)
- [ ] core_team / master の見え方確認

### Phase 4: 運用面
- [ ] `garden/OPERATIONS.md` 運用カード
- [ ] HMC -> HMG 移行表
- [ ] 必要なら ADR

### Phase 5: 検証
- [ ] dry-run
- [ ] dummy dispatch
- [ ] 失敗時 board
- [ ] cron / webhook 初回検証ポイント
```

### 実装判断(迷ったらこの順)

1. 既存 HMG の pattern
2. HMC レガシーの有用な実装
3. workflow の目的
4. 最小 MVP
5. 将来拡張

---

## Mode 6: Review and Promotion(苗から本番へ)

### 目的

作った区画を、試作で終わらせず運用に乗せます。

### 昇格条件

| 段階 | 条件 |
|---|---|
| draft | SKILL + 種の骨格がある |
| test | dry-run または dummy dispatch が通る |
| active | 実運用の初回が通り、OPERATIONS に運用カードがある |
| mature | 失敗時の見方・承認境界・HMC 側の扱いが明確 |

### 確認項目

- ガクチョが日々どこを見ればよいか説明できる
- board / LINE / Discord / Obsidian の役割が混線していない
- 種が何を起こすか 1 行で説明できる
- execute 系は承認なしに強い外部書き込みをしない
- HMC レガシーが残る場合、並行運用の境界が明記されている

---

## サンプル 1: HMC レガシー移植型

依頼:

```text
expense_processor を移植型で Garden 化して。HMC レガシーを活かして、まず MVP の SKILL + 種まで。
```

想定出力(抜粋):

```markdown
## Garden 化対象
- 業務名: expense_processor
- mode: transplant
- MVP: クレカ明細とレシート候補を読み、Freee 登録候補 board を起草する
- 想定 scope: master
- 期待する成果: ガクチョが承認すれば Freee 登録へ進める

## Legacy Inventory
- HMC SKILL: `.agent/skills/expense_processor/SKILL.md`
- scripts: HMC 側の Freee / Gemini / receipt parser
- config: 勘定科目・部門 mapping
- secrets: Freee OAuth / Gemini API
- known failures: PDF 読み取り失敗、部門推定漏れ、二重登録

## Garden Design
### plot
- name: expense_processor
- purpose: 経費候補を整理し、Freee 登録前の剪定依頼を作る
### seeds
| seed | trigger | 何を起草/実行するか | 承認境界 |
|---|---|---|---|
| expense_processor/monthly-expense-draft | 月初 or 手動 | 経費候補 board 起草 | Freee 登録前に承認 |
### services / tools(水面下)
| 名前 | 種別 | 役割 | 実装方針 |
|---|---|---|---|
| scan_expense_candidates.py | service | 明細・レシート候補抽出 | HMC logic 移植 |
| create_freee_expense.py | service | 承認後 Freee 登録 | HMC client を Garden 作法で包む |
```

---

## サンプル 2: 新規業務の新植型

依頼:

```text
助成金管理を新植型で Garden 化したい。workflow から整理して。
```

想定出力(抜粋):

```markdown
## Garden 化対象
- 業務名: grant_manager
- mode: seedling
- MVP: 申請期限と必要書類を board / active_tasks に出す
- 想定 scope: master / core_team
- 期待する成果: 締切前に必要判断が漏れない

## Workflow Spec
### 目的
助成金の申請・報告・証憑準備を期限前に進める。
### 起きてほしいタイミング
- 締切 30 日前 / 14 日前 / 3 日前
### ガクチョの承認が必要な点
- 申請する/しない / 提出文面 / 添付資料の最終確認

## Garden Design
### seeds
| seed | trigger | 何を起草/実行するか | 承認境界 |
|---|---|---|---|
| grant_manager/deadline-watch | 毎朝 | 近い締切を board 化 | 申請判断 |
### services / tools(水面下)
| 名前 | 種別 | 役割 | 実装方針 |
|---|---|---|---|
| list_grants | tool | 登録済み助成金の期限を見る | read_tool |
| draft_grant_board.py | service | board 起草 | 新規 |
```

---

## 禁止事項

- tool から先に設計しない(SKILL → 種 → 通行手形 が先、tool は水面下)
- HMC レガシーがあるのに読まずに作り直さない(transplant / hybrid)
- execute 系を承認境界なしで core_team / staff に渡さない
- MAP にだけ進捗を書いて OPERATIONS を更新し忘れない
- 種を tool と呼ばない / tool を種と呼ばない
- SKILL に secret 値を書かない

---

## このメタ区画自体の昇格状態

- 段階: **active**(2026-06-11 S42、ガクチョ判断)
- 実績: 3 モードすべてで実業務を完走 — **transplant** = expense_processor(S35-37)/ **hybrid** = invoice_processor(S41)/ **seedling** = field_assistant(S42、未整理の依頼 → Workflow Spec → 1 セッションで test まで)
- 「作らない」判断の実績もあり(shift_manager 早期撤退、S35)
- 学び: seedling では Mode 3 Workflow Spec が議論の核になる(Intake 3 問 + UX モック先行が効く)。Legacy Inventory は HMC 外の既存資産(storesyoyaku 等)にもそのまま使えた
