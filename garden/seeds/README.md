---
type: index
status: active
last_updated: 2026-05-25
last_updated_by: claude (with 塚越さん, セッション8)
---

# garden/seeds/ — 種(自律トリガー)

> **種** = 「いつ・何が起きて・何を動かし・誰に剪定依頼するか」を1ファイル1ジョブで宣言した起動装置。
> 各種は HMC SKILL 群を **Claude Code ヘッドレス** で呼び出す。庭師は剪定(承認/修正/却下)だけに専念する。

## 関連 ADR(必読)

- [セッション4 ADR — 種設計の方針(3形式・ガクコ統合・剪定振り分け)](../../docs/decisions/2026-05-23-seeds-design-direction.md)
- [セッション5 ADR — workflow 正本性 + 改善余地表](../../docs/decisions/2026-05-24-workflows-as-truth-and-improvement-targets.md)
- [セッション6 ADR — デイリーワークフロー種化 + Claude Code ヘッドレス + LiveSync + Triage](../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md)

## ディレクトリ構造

```
garden/seeds/
├── README.md                    ← 本ファイル(運用ルール+スキーマ定義)
├── .log/                        ← 種実行ログ(YYYY-MM-DD-{seed}.log)
├── .scratch/                    ← 試作領域(本番ランチャー設計が固まったら削除)
└── {plot}/                      ← plot 別(HMC SKILL 名と原則一致)
    └── {seed-name}.md           ← 1種 = 1ファイル
```

`{plot}` は当面 HMC SKILL 名と一致させる(shift_manager / daily-pilot / finance_importer …)。将来 `garden/plots/` で区画を独立定義する時に同名対応を維持する。

`.scratch/` はセッション9(2026-05-25)で導入。VPS 上で cron → claude -p → ログ生成 のエンドツーエンドを検証する最小スクリプトを置く。本番ランチャー(frontmatter パース・on_failure・retry 等)の設計が固まったら削除する。

## 実行ホスト(セッション7 確定)

- **すべての cron 系の種は VPS 上で起動する**。塚越さん PC の起動状態に依存しない構造を取る。
- セッション6 ADR「種の頭脳 = Claude Code ヘッドレス起動 on VPS」の延長線上の決定。
- WSL 上の cron は **使わない**(PC 夜間ダウン → 早朝・夜間の cron が走らない問題を構造的に排除)。

### 種を「HMC 依存度」で分類

| 分類 | 例 | VPS だけで完結? |
|---|---|---|
| **Garden 内完結** | daily-pilot 全4本(backlog/active/board/ガクコ/calendar(MCP) のみ参照) | ✅ そのまま VPS で動く |
| **HMC 依存** | shift_manager 系 / finance 系(HMC のスクリプト・credentials・venv が必要) | ❌ HMC を VPS に移すまで active 化不可 |

### 実装ロードマップ(Phase 3a / 3b / 3c)

| Phase | 内容 | 状態 |
|---|---|---|
| **3a** | 種ランチャー(VPS)+ Garden 内完結種(daily-pilot 4本)の active 化 | 設計済(セッション6) → 実装待ち |
| **3b** | HMC を VPS に移植 or 必要部分切り出し + **secret 管理設計(セッション7 で議論中)** | 議論中 |
| **3c** | HMC 依存種(`monthly-shift-survey` 含む)の active 化 | 3b 完了後 |

→ **本セッション(7)で起草した `monthly-shift-survey.md` は Phase 3c 待ち**。先に動かせるのは daily-pilot 系。

## 種ファイルのスキーマ(MD frontmatter + 本文)

```markdown
---
type: seed
name: {seed-name}                # 例: monthly-shift-survey
plot: {plot}                     # 例: shift_manager
description: {一行で何をする種か}
status: draft | active | paused | deprecated
version: 1
created: YYYY-MM-DD
last_updated: YYYY-MM-DD

# === ① いつ点火するか(trigger) ===
trigger:
  type: cron | event | state-change
  # cron の場合
  schedule: "0 8 1 * *"          # 標準 cron 式
  timezone: Asia/Tokyo
  # event の場合
  watch: garden/inbox/*.md       # 監視対象(glob)
  # state-change の場合
  source: {sheet/cell or file path}
  condition: "値が空 → 値が入った時"

# === ② 何を実行するか(execute) ===
engine: claude-code              # launcher が解決する runner。現状の実装は claude-code のみ。
                                 # codex / gemini-cli は未実装で、指定すると launcher が exit 2 で明示エラー
                                 # (S60: launcher.mjs が engine を本当に読む構造に。RUNNERS に追加で対応 engine が増える)
execute:
  skill: {SKILL名} (HMC|HMG)     # 既存 HMC SKILL or 将来 HMG plot
  prompt: |                       # Claude Code に渡す自然言語指示
    対象月 = …
    手順:
      1. …
      2. …
    詳細は {マニュアルパス} 参照。
  working_dir: {実行場所}
  computed_inputs:                # 発火時に動的計算する値
    target_month: "$(date -d '+2 months' +%Y-%m)"

# === ③ 結果をどこに置くか(outputs) ===
outputs:
  - kind: board_draft | active_tasks | backlog | archive | log
    path: {ファイルパス(テンプレ可)}

# === ④ 誰に剪定依頼するか(pruning) ===
pruning:
  channel: line | board_with_notify | board | none   # 重さで自動振り分け(ADR セッション4 決定6 + none を S8 で追加)
  approver: "[[庭師の wiki link]]" | null            # channel: none なら null
  notify:                                            # channel: none なら null。board_with_notify / board は notify 必須
    via: gaku-co
    group: personal | core_team | staff
    template: |
      📋 {何の下書きか}
      → {board ファイルパス}

# === ⑤ 承認後の振る舞い(任意) ===
post_approval:
  via: gaku-co
  endpoint: /send
  body:
    group: personal | core_team | staff
    require_approval: false                   # 既に剪定承認済み
    message_from: {board ファイルから本文を読む}

# === ⑥ べき等性 ===
idempotency:
  key: {seed-name}-{target_month}
  guard: |
    同 key で board ファイルが既に存在 → スキップ

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: gaku-co
    group: personal
    template: |
      ❌ {seed-name} 失敗
      理由: {error_summary}
      詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  workflow: {workflow-name}                   # 出自の workflow
  state: [{前提状態}]
  seeds: [{前段の他種}]

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null
---

# {seed-name}

## 目的(不変)
このステップが達成しなければならないこと(目的は変えるならそれは別の種)。

## 現状の方法
(frontmatter の execute / pruning / post_approval を参照)

## 改善余地(Improvement Hints)
workflows/ と同じ表形式。❓未検証 / 💡着手可能 / ✋検討済 / 🛠️実装中。

## 関連
出自の workflow / SKILL / ADR / 関連種。

## TODO
本種に固有の宿題。
```

## 種型ごとの注意

### cron 種

- 標準 cron 式(`分 時 日 月 曜`)。timezone は明示。
- 平日・土日祝の区別が必要な場合は `schedule` を複数記述 or 1つにまとめて prompt 内で日種判定。
- VPS の `claude -p "..."` をシェル経由で起動する想定(常駐 daemon ではない)。

### event 種

- watcher daemon が glob を監視。マッチ → `claude -p` 起動。
- daemon 実装は Phase 3 課題(`daily-pilot/inbox-process` と合わせて設計)。
- event 種は追加フィールド(セッション8 で導入、合意要):
  - `trigger.exclude` — watch 対象から除外する glob(例: `processed/**`)
  - `trigger.debounce` — 連続書き込み中のファイナル状態待ち(例: `10s`)
  - `{event.path}` — マッチファイルのパス(computed_inputs / prompt で参照可能)

### state-change 種

- 元データ(Sheet・ファイル・DB)の差分を polling or hook で検出。
- 「シフトアンケート Q列にチェック → アンケート発火」など。

## 改善余地表のルール(workflows/ と共通)

- ❓ 未検証 / 💡 着手可能 / ✋ 検討済(却下理由併記) / 🛠️ 実装中
- セッション中に思いついた改善案は **まず該当種の表に追記** してから判断を仰ぐ
- ✋ の再提案は禁止(却下理由を尊重)

詳細: [workflows/README.md](../soil/workflows/README.md) と [ADR セッション5](../../docs/decisions/2026-05-24-workflows-as-truth-and-improvement-targets.md)

## 既存 HMC SKILL との関係(相談事項)

> セッション7 で塚越さんから提起された重要論点。種ファイル設計と並行で議論する。

**現状**: HMC SKILL は機能集約型(1 SKILL = 機能群)。

| 例 | shift_manager SKILL |
|---|---|
| 含むタスク | 年次/月次/シフト管理(募集・集計)/稼働時間/支払処理(請求書・給与・追加スタッフ) |

**種化すると起きること**:

1. **1種 = 1責務** に分解されるため、1 SKILL を **複数種** が異なるタスクで参照する
2. 共通処理(ガクコ配信・稼働表読み取り・Freee 連携)が SKILL に重複・散逸する可能性
3. SKILL を直しても、参照する種を漏れなく追従させる仕組みが要る

**対応方針(暫定)**:

- 種は当面 **「該当する HMC SKILL の特定タスクだけ呼び出す」** 形で書く(execute.prompt で範囲を絞る)
- 種を増やす過程で SKILL の再編必要性が顕在化したタイミングで、SKILL 分解 ADR を立てる
- 種 frontmatter の `execute.skill` を機械可読にしておけば、「この SKILL を参照している種一覧」が grep で出る → 影響分析の足場になる

**未決**:

- SKILL の粒度を **種に対応する細粒度** に再編するか / 機能群のまま **接面だけ統一** するか
- 共通処理(ガクコ配信など)を **横断 SKILL** として独立させるか / 各 SKILL に持たせるか

→ 種2本目以降の draft 過程で具体問題が顕在化したら、 [garden/MAP.md](../MAP.md) の宿題に格上げして ADR 議論する。

## 既存・予定の種一覧

| 種 ID | trigger | HMC依存 | 該当Phase | 状態 | 一行 |
|---|---|---|---|---|---|
| [shift_manager/monthly-shift-survey](shift_manager/monthly-shift-survey.md) | cron 月初1日 | あり | **3c** | draft | 翌月シフトアンケートを下書き → 剪定 → staff LINE 配信 |
| [daily-pilot/recurring-spawn](daily-pilot/recurring-spawn.md) | cron 毎日 06:25 | なし | **3a** | **active** (S15) | recurring_master を見て、当該期間のインスタンスを backlog に追加 |
| [daily-pilot/morning-briefing](daily-pilot/morning-briefing.md) | cron 毎日 06:30 | なし | **3a** | **active** (S15) | backlog から今日締切を active 抽出 + calendar + Triage + LINE |
| [daily-pilot/night-review](daily-pilot/night-review.md) | cron 毎日 22:30 | なし | **3a** | **active** (S15) | active の `[x]/[ ]/追加` を backlog/archive 反映 + LINE 報告 |
| [daily-pilot/inbox-process](daily-pilot/inbox-process.md) | event | なし | **3a** | draft | inbox/*.md 投入 → 振り分け → backlog 追記 |
| shift_manager/month-end-working-hours-prep | cron 月末 | あり | **3c** | 構想 | 稼働表準備(検証チェックリスト+generate+コドモン手入力リマインド) |
| shift_manager/monthly-working-hours-confirmation | cron 月初1日 | あり | **3c**(保留) | 構想 | 稼働時間確認依頼。庭師の「見せ方」決定後に着手 |
| shift_manager/monthly-shift-finalize | cron 月初10日 | あり | **3c** | 構想 | シフト確定+稼働確認締切の集約通知 |

## スキーマ拡張(セッション13 ADR で正式化)

セッション8 で導入された 5 項目は [seed-schema-extensions ADR](../../docs/decisions/2026-05-27-seed-schema-extensions.md) で **正式採用済**。詳細は ADR 参照。要約:

| フィールド | 用途 | 導入種 |
|---|---|---|
| `pruning.channel: none` | 自律完結種(剪定なし)用。approver/notify は null | recurring-spawn / night-review / inbox-process |
| `on_complete` (frontmatter top-level) | 剪定なしで完了報告だけ送る種用 | night-review |
| `trigger.exclude` | event 種の watch 対象から除外する glob | inbox-process |
| `trigger.debounce` | event 種の連続書き込みファイナル状態待ち | inbox-process |
| `{event.path}` 変数 | event 種で watcher daemon が渡すマッチファイルパス | inbox-process |

関連 ADR:
- [recurring-respawn-prevention ADR](../../docs/decisions/2026-05-27-recurring-respawn-prevention.md) — 案 E(`<!-- recur:... -->` マーカー)
- [vault-folder-layout ADR](../../docs/decisions/2026-05-27-vault-folder-layout.md) — vault 内の `hmc_tasks/` 流用と `garden/` 新設
- [garden-board-structure ADR](../../docs/decisions/2026-05-27-garden-board-structure.md) — `garden/board/` の内部構造(pending / processed / triage)

## Phase 3a の前提インフラ(VPS 完結種を動かすための最小セット)

- VPS CouchDB セットアップ(+ LiveSync)
- 平文 MD ミラー daemon(`_changes` feed リスナ)
- 種ランチャー(VPS cron → `claude -p` 起動 + ログ + on_failure 処理)
- watcher daemon(event 種用、glob 監視)
- gaku-co5.0 側「LINE 返信 → board MD 書き戻し」

## Phase 3b の追加インフラ(HMC 依存種に進むための追加要件)

- HMC の VPS 移植 or 必要部分(`apps/shift_manager/logic/*.py` 等)切り出し
- HMC が VPS で動くための venv / config_ids.json / section_mapping.json
- **secret 管理設計(セッション7 で議論中)** — Freee / Google OAuth トークン・人事労務 freee などの保管・rotation・信頼境界
- HMC 出力の Google Sheets / Forms / Drive への書き込み権限が VPS 側でも有効であること
