---
type: seed
name: night-review
plot: daily-pilot
description: 毎日 22:30 に active_tasks を読み、[x]/[ ]/追加 を backlog/archive に反映 + active クリア + LINE 報告する種
status: active
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-05-25
created_by: claude (with 塚越さん, セッション8)
last_updated: 2026-05-28
activated: 2026-05-28   # セッション15: cron 22:30 自動発火 → 完走(再実行で冪等性も確認)を実証して active 化。完全自律での実変換は今晩 5/28 分が初回
linked_workflows:
  - "[[daily-cycle]]"   # ステップ4
linked_skills:
  - "hmc_pilot (HMC)"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "30 22 * * *"          # 毎日 22:30 JST
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  skill: hmc_pilot (HMC)           # 手順参照のみ
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    today_md: "$(date +%-m/%-d)"
    today_slash: "$(date +%Y/%m/%d)"
    today_month: "$(date +%Y/%m)"
    tomorrow: "$(date -d '+1 day' +%Y-%m-%d)"
    tomorrow_md: "$(date -d '+1 day' +%-m/%-d)"
    tomorrow_slash: "$(date -d '+1 day' +%Y/%m/%d)"
    # 曜日は VPS に ja_JP.UTF-8 locale 未導入のため、prompt 内で Claude が today/tomorrow から判定する
  prompt: |
    あなたは daily-pilot 区画の種「night-review」です。

    まず以下2ファイルを Read で読み込み、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/plots/daily-pilot/SKILL.md(本区画の Mode 3)
    SKILL は CHARTER を継承して書かれています。両方を参照してください。

    その上で、SKILL の **"Mode 3: Night Review"** の全 Step(Step 1〜7)に従って、本日 {today} の振り返りを実行します。
    特に Step 4 の **active 編集の反映ロジック**(active 上で締切が書き換えられていたら backlog を更新)を厳守。

    今回の動的入力:
      - today: {today}, today_md: {today_md}, today_slash: {today_slash}, today_month: {today_month}
      - tomorrow: {tomorrow}, tomorrow_md: {tomorrow_md}, tomorrow_slash: {tomorrow_slash}

    操作対象ファイル(SKILL の「ファイルと役割」表を参照):
      - /home/vps-harappa/garden-mirror/hmc_tasks/active_tasks.md
      - /home/vps-harappa/garden-mirror/hmc_tasks/backlog.md
      - /home/vps-harappa/garden-mirror/hmc_tasks/archive.md

    曜日表記: today/tomorrow から判定して (月)(火)(水)(木)(金)(土)(日)。

    完了報告(LINE 通知はモック化中、ガクコ /send は呼ばない):
      `/home/vps-harappa/garden-mirror/garden/log/{today}-night-review.log` の末尾に
      **`==NOTIFY==` ブロックで append**:
      ```
      ==NOTIFY==
      🌱 夜のレビュー {today_md}
      ✅ 完了: {done_count}件 (archive へ)
      🔄 持ち越し: {keep_count}件 (backlog 残存)
      🔁 締切更新: {modified_count}件 (active 編集を backlog へ反映)
      ➕ 新規追加: {added_count}件
      🚨 期限超過(明日): {overdue_next_count}件
      ==END==
      ```

    失敗時:
      - active_tasks.md 読み取り失敗 → on_failure に従う(致命的)
      - backlog / archive 書き込み失敗 → on_failure に従う

# === ③ 結果をどこに置くか ===
outputs:
  - kind: backlog
    path: /home/vps-harappa/garden-mirror/hmc_tasks/backlog.md
  - kind: archive
    path: /home/vps-harappa/garden-mirror/hmc_tasks/archive.md
  - kind: active_tasks
    path: /home/vps-harappa/garden-mirror/hmc_tasks/active_tasks.md   # クリア後の状態を書き戻す
  - kind: log
    path: /home/vps-harappa/garden-mirror/garden/log/{today}-night-review.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: none                    # 自律完結(報告のみ、承認なし)
  approver: null
  notify: null                     # LINE 報告は post_approval ではなく直接送信

# === ⑤ 承認後の振る舞い ===
# 本種は剪定なし。完了時の LINE 報告は execute 内で直接 ガクコ /send を呼ぶ。
post_approval: null

# 完了時通知(本種固有のフィールド。スキーマ拡張候補)
# 注: Phase 3a 検証中はガクコ /send 呼び出しを行わず、prompt 内で log 末尾に
#     `==NOTIFY==` ブロックとして書き出すモックモード。連携実装後に有効化する。
on_complete:
  via: mock                          # 当面: log に書き出すだけ
  # via: gaku-co                     # 将来: ガクコ /send 連携 active 化後
  endpoint: /send
  body:
    group: personal
    require_approval: false
    template_summary: |
      🌱 夜のレビュー {today_md}
      ✅ 完了: {done_count}件 (archive へ)
      🔄 持ち越し: {keep_count}件 (backlog 残存)
      🔁 締切更新: {modified_count}件 (active → backlog 反映)
      ➕ 新規追加: {added_count}件
      🚨 期限超過(明日): {overdue_next_count}件

# === ⑥ べき等性 ===
idempotency:
  key: night-review-{today}
  guard: |
    同日2回起動時、active_tasks.md が既にクリア状態(空 or テンプレのみ)であれば
    本種は即終了(2回目の処理対象なし)。
    backlog / archive への書き戻しは2回起動時に重複しないよう、
    active のスナップショット → 差分計算 → atomic write で実装する。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 10m
  fallback:
    via: gaku-co
    group: personal
    template: |
      ❌ night-review 失敗 ({today})
      理由: {error_summary}
      詳細: {log_path}
      ⚠️ active_tasks をクリアできていない可能性あり。明日朝の morning-briefing が
         前日の active を保持したままになる。手動確認推奨

# === ⑧ 依存 ===
depends_on:
  workflow: daily-cycle
  state:
    - "/home/vps-harappa/garden-mirror/hmc_tasks/active_tasks.md が存在(空でも可)"
    - "/home/vps-harappa/garden-mirror/hmc_tasks/backlog.md が存在・有効"
    - "/home/vps-harappa/garden-mirror/hmc_tasks/archive.md が存在(無ければ新規作成)"
    - "LiveSync 平文 MD ミラーが最新化されている"
    - "ガクコ /send が利用可能(personal グループ)"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-05-25T22:30:00+09:00
---

# night-review — 夜の振り返り

## 目的(不変)

毎晩 22:30、当日の active_tasks の状態を backlog / archive に反映し、active を翌日のためにクリアする。塚越さんは編集を残すだけで、反映処理は完全自動。**未編集の日でも処理続行**(active は必ずクリア)。

## 現状の方法

frontmatter の `execute` / `outputs` を参照。要約:

1. cron 毎日 22:30 発火
2. active の `[x]` → backlog 削除 + archive 追記
3. active の `[ ]` → backlog 残存(active からは消える)
4. `## 追加` セクション → 4 分岐処理(`[x]`/`[ ]`+締切あり/`[ ]`+締切なし/空)
5. 締切なし追加タスクは **翌日デフォルト暫定締切** を自動付与
6. active クリア + LINE 報告

## 暫定締切ルール(ADR セッション6 決定7)

`## 追加` で締切なし → **翌日デフォルト**(翌営業日でなく単純に翌日)。

理由:
- 翌朝の active に必ず登場 → Triage で確認される → 埋もれない
- 翌営業日ロジックを入れると土日に浮上しない可能性 → 「埋もれ防止」を優先するため非採用

morning-briefing が翌朝 Triage Q1 として自動エスカレーション(`(b) 今週中` 等の選択肢を提示)。

## LINE 報告フォーマット

```
🌱 夜のレビュー {today_md}
✅ 完了: X件 (archive へ)
🔄 持ち越し: X件 (backlog 残存)
➕ 新規追加: X件
🚨 期限超過(明日): X件
```

未編集の日(=完了 0 / 持ち越し前日分そのまま / 追加 0)も同様に 0件 表示で送信。

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 暫定締切 = 翌日固定 | 「金曜の追加 → 月曜暫定」等の営業日ロジックが要るか未検証。最初は単純運用で開始 | 未検証(daily-cycle ステップ4 と同期) |
| 💡 | 期限超過タスク表示 | LINE 報告で「🚨 期限超過(明日): X件」を別表示(本種で集計可能) | 着手可能 |
| ❓ | 22:30 固定 | 夜の追加が間に合わない日が出るか未検証。可変化は運用後に判断 | 未検証 |
| ✋ | `on_complete` フィールド | 剪定なしで完了報告だけ送る種(本種)のために導入。[seed-schema-extensions ADR](../../../docs/decisions/2026-05-27-seed-schema-extensions.md) で正式採用済 | **検討済**(S13 で ADR 化) |
| 🛠️ | backlog 削除のマッチキー = recur マーカー優先 + タスク名フォールバック | recurring 由来タスクは `<!-- recur:{id}@{period_id} -->` で一意マッチ可能。非 recurring(inbox 由来・手動追加)はタスク名+deadline フォールバック | 実装中(案 E ・セッション8) |
| ❓ | 非 recurring タスクのマッチキー | recur マーカーがない手動タスクは表記揺れに弱いまま。inbox-process が `<!-- src:inbox/{file} -->` 等を付与する設計余地 | 未検証 |
| ❓ | active クリア後のテンプレ | `# 今日のタスク` ヘッダのみ残す? 完全空? | 未検証 |
| 💡 | 部分書き込み失敗時の整合性 | active 読み → backlog/archive 書き → active クリア の途中で失敗すると不整合。atomic write + ロールバック設計 | 構想中 |
| ❓ | archive のヘッダ規約 | `## YYYY/MM/DD` で揃える前提だが、月単位サブヘッダ等の整理は必要か未検証 | 未検証 |
| ❓ | `## 追加` のマーカー | active 内で `## 追加` セクションを必ず期待する。塚越さんが書き忘れた追加(本文中追記)は拾えない | 未検証 |

## 関連

- workflow: [[daily-cycle]] ステップ4
- 元 SKILL: `hmc_pilot`(HMC)— 旧夜レビュー手順
- ADR セッション6: [デイリーワークフロー種化](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md) 決定2(backlog マスタ)・決定6(常に処理)・決定7(暫定締切)
- 関連種:
  - `daily-pilot/morning-briefing`(翌朝、本種でクリアした active を再構築)
  - `daily-pilot/recurring-spawn`(翌朝、本種より早く起動)

## TODO(本種に固有)

- [ ] `on_complete` フィールドのスキーマ追加合意(seeds/README.md 更新)
- [ ] backlog からの削除マッチキー設計(recur マーカー優先・非 recurring のフォールバック策)
- [ ] 非 recurring タスクへのマーカー付与方針(inbox-process / 手動追加で `<!-- src:... -->` 付与するか)
- [ ] active クリア後のテンプレ確定(ヘッダのみ / 完全空 / プレースホルダ)
- [ ] archive のヘッダ規約確定(`## YYYY/MM/DD`)
- [ ] atomic write + ロールバック設計(整合性担保)
- [ ] 期限超過カウントの算出ロジック(明日時点で deadline ≦ tomorrow かつ未完了)
- [ ] `## 追加` 必須化(塚越さんへの運用周知 + 種側のフォールバック「マーカーなし新規行は追加扱い」の是非)

## active 化条件(Phase 3a の入口)

本種は **Garden 内完結種**(`hmc_dependency: none`)で Phase 3a の対象。

### Phase 3a 由来の前提(全種共通)

1. 種ランチャー(VPS cron → `claude -p` 起動 + ログ + on_failure)
2. **平文 MD ミラー daemon**(CouchDB `_changes` → `/home/vps-harappa/garden-mirror/hmc_tasks/*.md` 同期)— **セッション12 で稼働開始**(`garden-mirror-daemon`)
3. ガクコ `/send`(personal)経由 LINE 通知の最小ループ

### 本種固有

4. backlog 削除マッチキーの設計合意
5. archive ヘッダ規約の確定
6. 暫定締切付与ロジックの実装(`(MM/DD締切・暫定)` フォーマットの統一)
7. atomic write 機構(中断耐性)
