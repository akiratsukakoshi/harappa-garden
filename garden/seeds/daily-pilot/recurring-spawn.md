---
type: seed
name: recurring-spawn
plot: daily-pilot
description: 毎日 06:25 に recurring_master を読み、当該期間の定期タスクを backlog に展開する種
status: draft
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-05-25
created_by: claude (with 塚越さん, セッション8)
last_updated: 2026-05-25
linked_workflows:
  - "[[daily-cycle]]"   # ステップ1
linked_skills:
  - "hmc_pilot (HMC)"   # 移行元(現状は手順参照のみ、実行は claude-code が直接)
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "25 6 * * *"           # 毎日 06:25 JST(morning-briefing の 5 分前)
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  skill: hmc_pilot (HMC)           # 当面は手順参照のみ。実行は Garden 内 MD の読み書きで完結(HMC 呼び出しなし)
  working_dir: /opt/garden         # VPS 上の garden ルート(LiveSync 平文 MD ミラー先)
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    today_md: "$(date +%-m/%-d)"
    weekday: "$(date +%u)"         # 1=月 〜 7=日
    year: "$(date +%Y)"
    month: "$(date +%-m)"
    day: "$(date +%-d)"
    iso_week: "$(date +%G-W%V)"    # 2026-W22 形式
  prompt: |
    あなたは daily-pilot 区画の種「recurring-spawn」です。
    目的: 当日(今日 = {today})締切で実行されるべき定期タスクが backlog に揃っている状態を作る。
    後続の morning-briefing(06:30)が backlog を抽出する直前に必ず成立させる。

    重要原則(案 E ・セッション8 確定):
      - **完了済みの定期タスクを同期間内に再 spawn しない** ことを最優先で担保する
      - キー判定は **backlog + archive 両方** を機械可読コメントマーカーで grep する
      - recurring エントリは必ず `id:` を持つ(タスク名表記揺れの根本対策)

    手順:
      1. 入力読み込み
         - /opt/garden/tasks/recurring_master.md を読む
         - /opt/garden/tasks/backlog.md を読む
         - /opt/garden/tasks/archive.md を読む

      2. recurring_master の各エントリについて、当日対象か判定:
         - 各エントリは `id:` フィールド必須(例: `r001`)。ID 欠落エントリは警告ログのみで skip
         - Daily: 毎日対象、期間ID = {today}
         - Weekly: weekday({weekday}) が一致する週は対象、期間ID = {iso_week}
         - Monthly: 指定日(day == {day})が一致する月は対象、期間ID = {year}-{month}
         - Yearly: 月日が一致する年は対象、期間ID = {year}
         - period 表現の詳細仕様は recurring_master.md 冒頭のルール記述を参照

      3. 対象タスクが既出かを判定(backlog + archive 両方を grep)
         - キー = `recur:{id}@{period_id}`(例: `recur:r001@2026-06`)
         - backlog.md を走査: 同キーマーカーがある行 → 既に spawn 済み + 未完了 → skip
         - archive.md を走査: 同キーマーカーがある行 → 同期間内に既に完了済み → skip
         - 走査は機械可読コメント `<!-- recur:{id}@{period_id} -->` を grep する
           (タスク名や見出しの表記揺れの影響を受けない)

      4. skip されなかったエントリを backlog.md に追記:
         - フォーマット:
           `- [ ] **{タスク名}** ({today_md}締切・定期) <!-- recur:{id}@{period_id} -->`
         - 適切な Level 2 ヘッダ配下に整理(recurring_master の category を尊重)
         - ヘッダが存在しない場合は backlog の `## 定期` 配下に集約(無ければ末尾に新設)

      5. ログ出力
         - 追加件数・スキップ件数(backlog 既存 / archive 完了済 別)・対象外件数を
           {log_path} に1行サマリで記録

    failure mode を引き起こす可能性のある暗黙の前提:
      - night-review が `[x]` → archive 転記時に **元の行を完全保持**(recur マーカー含む)していること
        → night-review.md 側で明示している
      - recurring_master の各エントリに `id:` が振られていること
        → 不在エントリは spawn 対象外として警告

    失敗時:
      - recurring_master.md が読めない or 構文不正 → on_failure に従う
      - backlog.md / archive.md への読み書きに失敗 → on_failure に従う
      - 例外日(祝日・休業日)判定は本種では実装しない(❓ Improvement Hints 参照)

# === ③ 結果をどこに置くか ===
outputs:
  - kind: backlog
    path: /opt/garden/tasks/backlog.md
  - kind: log
    path: /opt/garden/seeds/.log/{today}-recurring-spawn.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: none                    # 自律完結(承認不要)。結果は morning-briefing が見せる
  approver: null
  notify: null

# === ⑤ 承認後の振る舞い ===
post_approval: null                # pruning なし → 不要

# === ⑥ べき等性 ===
idempotency:
  key: recurring-spawn-{today}
  guard: |
    各 recurring エントリは `<!-- recur:{id}@{period_id} -->` コメントマーカーをキーに
    backlog + archive 両方を grep し、既出なら spawn しない。
    同日2回実行されても、完了→archive 移動後でも、重複追加されない(案 E ・セッション8)。
    本種自体の「同日2回起動防止」は不要(べき等なので)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 5m
  fallback:
    via: gaku-co
    group: personal
    template: |
      ❌ recurring-spawn 失敗 ({today})
      理由: {error_summary}
      詳細: {log_path}
      → backlog 展開が走らず、morning-briefing が定期タスクを拾えない可能性あり

# === ⑧ 依存 ===
depends_on:
  workflow: daily-cycle
  state:
    - "/opt/garden/tasks/recurring_master.md が存在・有効 + 各エントリに `id:` 振られている"
    - "/opt/garden/tasks/backlog.md が存在(空でも可)"
    - "/opt/garden/tasks/archive.md が存在(空でも可)"
    - "LiveSync 平文 MD ミラーが最新化されている(_changes feed daemon 稼働中)"
    - "night-review が `[x]` → archive 転記時に元行を完全保持(recur マーカー含む)している"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-05-26T06:25:00+09:00
---

# recurring-spawn — 定期タスク展開

## 目的(不変)

毎日朝 06:25、**当日締切で実行されるべき定期タスクが backlog に揃っている** 状態を作る。morning-briefing(06:30)が backlog を抽出する直前に必ず成立させる。

## 現状の方法

frontmatter の `execute` / `outputs` を参照。要約:

1. cron 毎日 06:25 発火
2. `recurring_master.md` を読む(各エントリは `id:` 必須)
3. Daily / Weekly / Monthly / Yearly の判定で当日対象を抽出
4. `backlog.md` と `archive.md` の両方を `<!-- recur:{id}@{period_id} -->` でgrep し、既出ならskip
5. skipされなかったエントリを `(MM/DD締切・定期) <!-- recur:{id}@{period_id} -->` 付きでbacklogに追記
6. ログ出力(追加件数 / スキップ件数 backlog既存/archive完了済 別 / 対象外件数)

## 完了済み再 spawn 防止の仕組み(案 E ・セッション8 確定)

月次以上の recurring が「完了→archive 移動」した後に同期間内で再 spawn されないことを担保する方式:

```
recurring_master (id: r001, period: monthly, day: 15)
        │
        │ 6/15 06:25 spawn
        ▼
backlog.md
  ## 財務
  - [ ] **経費精算** (6/15締切・定期) <!-- recur:r001@2026-06 -->
        │
        │ 6/15 daytime 完了 → 6/15 22:30 night-review
        ▼
archive.md
  ## 2026/6/15
  - [x] **経費精算** (6/15締切・定期) <!-- recur:r001@2026-06 -->
        │
        │ 7/1〜7/14: recurring-spawn 走るが day != 15 → 対象外
        │ 7/15 06:25 recurring-spawn → 期間ID = 2026-07 → backlog/archive に「recur:r001@2026-07」なし → spawn ✓
        │ (同日2回起動など) → 期間ID = 2026-06 で既に archive にあり → skip ✓
```

ポイント:
- **キー = recurring ID + 期間ID**(`r001@2026-06`)— タスク名の表記揺れに耐える
- **backlog + archive 両方を機械可読コメントで grep** — 完了済みの再判定を確実に防ぐ
- **night-review が行を完全保持して archive に転記** することが前提(下記「関連」night-review.md と整合)

## recurring_master.md スキーマ要件(暫定)

```markdown
---
type: recurring_master
status: active
last_updated: YYYY-MM-DD
---

# Recurring Master

## ルール

- 各エントリは `id:` フィールド必須。一度発行した ID は変更しない(過去 archive と整合が崩れる)
- ID 命名: `r{連番}`(`r001`, `r002`, ...)
- period 表現:
  - **daily**: 毎日
  - **weekly**: `weekday` を曜日 (Mon-Sun または 1-7) で指定。配列も可
  - **monthly**: `day` を 1-31 で指定。`last`(月末)等は別途検討課題
  - **yearly**: `month_day` を `MM-DD` で指定

## エントリ

### r001 経費精算
- period: monthly
- day: 15
- category: 財務
- description: クレカ明細・領収書を整理して Freee に登録

### r002 週次レポート確認
- period: weekly
- weekday: Mon
- category: 開発

### r003 ゴミ出し
- period: weekly
- weekday: [Tue, Fri]
- category: 生活
```

スキーマ自体は本種の draft 起草時の暫定案。Phase 3a 着手時に確定し、ADR 化する。

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| 🛠️ | キー = `recur:{id}@{period_id}` で backlog + archive 両方を grep | **案 E 採用済(セッション8)**。完了済み再 spawn 問題を構造的に解決。recurring_master の ID 付与と night-review の元行保持が前提 | 実装中(Phase 3a 着手時に具体化) |
| ❓ | recurring_master を MD で持つ | 例外日(祝日・休業日・庭師休業)の扱いが未設計。MD に `exclude_days:` フィールドを持たせる or 外部祝日 API 連携 | 未検証 |
| ❓ | `execute.skill: hmc_pilot (HMC)` 参照 | Garden 内完結なので HMC SKILL に依存しない。HMG-native の操作手順書化(`garden/plots/daily-pilot/SKILL.md` 等)が要るか未検証 | 未検証(SKILL再編相談事項) |
| ❓ | 期間ID の計算(週初・月初の定義) | Weekly = ISO週(月曜始まり)固定。Monthly = 暦月。明示しないと表記揺れる。recurring_master 側で `period_anchor` を持つ手もある | 未検証 |
| ❓ | monthly の period 表現 | 現状は `day: N` のみ。月末(`last`)・第N曜日(`first_monday`)・月初N営業日 等の柔軟性をどこまで持たせるか | 未検証(Phase 3a 着手時に確定) |
| ❓ | archive 走査の負荷 | archive 1ファイル無制限成長で grep 負荷増大。**archive を月単位ファイル分割**(`archive/2026-06.md`)に切り替える余地。本種は archive ファイル群を走査するように改訂が要 | 構想中(archive 数千行を超えたら検討) |
| ❓ | `pruning.channel: none` を新設 | スキーマ草案には `line/board_with_notify/board` の3種のみ記載。自律完結種のために `none` を追加した。妥当性を確認 → seeds/README.md にも反映済 | 未検証(セッション8 で導入、合意要) |
| ❓ | `/opt/garden` を VPS マウント先と仮定 | 実装フェーズで確定。マウント方式(LiveSync 平文ミラー先)・権限・所有ユーザの設計が必要 | 未検証(Phase 3a インフラ課題) |
| 💡 | recurring_master の例外日対応 | 祝日 API(国民の祝日) + 庭師個別休業日リストの併用で例外日スキップ | 構想中 |

## 関連

- workflow: [[daily-cycle]] ステップ1
- 元 SKILL: `hmc_pilot`(HMC)— recurring 展開の手順記述あり
- ADR セッション6: [デイリーワークフロー種化アーキテクチャ](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md) 決定3(4本立て)・決定4(Claude Code ヘッドレス)
- ADR セッション7: [種スキーマ + 実行ホスト + Phase 細分](../../../docs/decisions/2026-05-25-seed-schema-and-execution-host.md)
- 関連種: `daily-pilot/morning-briefing`(直後 06:30 に発火、本種の出力を読む)

## TODO(本種に固有)

- [ ] `recurring_master.md` のスキーマ確定(`id` 必須・`period` 表現・`period_anchor` / `exclude_days`)→ Phase 3a 着手時に ADR 化
- [ ] monthly の period 表現の柔軟性確定(指定日のみ / 月末 / 第N曜日 / 月初N営業日)
- [ ] 期間ID の計算ロジック(週初 = 月曜 / 月初 = 1日 でロックするか)
- [ ] backlog の Level 2 ヘッダ規約の確定(category マッピング)
- [ ] HMG-native の操作手順書化(`hmc_pilot` 依存を切る)
- [ ] `pruning.channel: none` のスキーマ追加合意(seeds/README.md 更新)→ 完了済
- [ ] VPS Garden マウントパス(`/opt/garden`)の確定
- [ ] 既存の recurring(HMC 側 / 紙ベース)から `recurring_master.md` への移行計画
- [ ] archive 月単位分割への切替判断基準(行数閾値)

## active 化条件(Phase 3a の入口)

本種は **Garden 内完結種**(`hmc_dependency: none`)で Phase 3a の対象。

### Phase 3a 由来の前提(全種共通)

1. 種ランチャー(VPS cron → `claude -p` 起動 + ログ + on_failure)
2. **平文 MD ミラー daemon**(CouchDB `_changes` → `/opt/garden/tasks/*.md` 同期)
3. recurring_master.md 本体の整備(現状 HMC/Obsidian 側にある場合は移行が要)
4. backlog.md の Level 2 ヘッダ規約の確定

### 本種固有

5. recurring_master の `category` マッピング → backlog ヘッダ配置のルール
6. 期間ID計算ロジックの確定(prompt 内判定 or computed_inputs で確定させるか)
