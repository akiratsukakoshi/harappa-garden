---
type: seed
name: inbox-process
plot: daily-pilot
description: inbox/*.md への新規投入を watcher 検知して、内容を読み、塚越さん宛アクションを backlog へ振り分ける種
status: draft
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-05-25
created_by: claude (with 塚越さん, セッション8)
last_updated: 2026-05-25
linked_workflows:
  - "[[daily-cycle]]"   # ステップ5
linked_skills:
  - "hmc_pilot (HMC)"   # 移行元(手順参照のみ)
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: event
  watch: /home/vps-harappa/garden-mirror/garden/inbox/*.md     # 監視対象(glob)
  exclude: /home/vps-harappa/garden-mirror/garden/inbox/processed/**   # 処理済みは無視
  debounce: 10s                     # 連続書き込み中はファイナル状態を待つ

# === ② 何を実行するか ===
engine: claude-code
execute:
  skill: hmc_pilot (HMC)            # 手順参照のみ
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    target_file: "{event.path}"     # watcher daemon が渡すマッチファイル
    today: "$(date +%Y-%m-%d)"
    today_md: "$(date +%-m/%-d)"
    tomorrow_md: "$(date -d '+1 day' +%-m/%-d)"
  prompt: |
    あなたは daily-pilot 区画の種「inbox-process」です。
    対象ファイル: {target_file}
    目的: inbox に投入された MD ファイル({target_file})を読み、塚越さん宛のアクション項目を
          抽出して backlog の適切なカテゴリへ振り分ける。

    手順:
      1. 対象ファイル読み込み
         - {target_file} を読む
         - frontmatter があれば `source:`(議事録/letter/メール等)を尊重
         - 既に processed の場合は何もせず終了(べき等)

      2. アクション項目の抽出
         - 「{塚越さんの名前} 担当」「ガクチョー宛」「→塚越」等の明示マーカーを優先
         - 文脈から塚越さんが取るべきアクションを推測(議事録の場合、ToDo・宿題・依頼)
         - 1 ファイルから 0〜N 件抽出してよい(0 件なら振り分けスキップで OK)

      3. backlog の Level 2 ヘッダ(カテゴリ)へ振り分け
         - 元ファイルの内容から推測(例: 開発系 → `## 開発`、財務系 → `## 財務`)
         - 既存ヘッダにマッチしない場合は `## その他` 配下にフォールバック
         - 各アクションのフォーマット:
           `- [ ] **{アクション}** ({MM/DD締切})  ← from inbox/{ファイル名}`

      4. 締切付与
         - 元ファイルに明示があれば尊重
         - なければ **翌日デフォルト暫定締切**({tomorrow_md}締切・暫定) を付与
           (night-review と同じ運用 = 翌朝 Triage Q1 で確認される)

      5. 処理済みファイルを移動
         - {target_file} → /home/vps-harappa/garden-mirror/garden/inbox/processed/{today}/{元ファイル名}
         - 既存の同名ファイルがあれば連番付与({元ファイル名}_2.md)

      6. ログ出力
         - 抽出件数・カテゴリ別件数・スキップ理由を {log_path} に記録

      7. 翌朝の morning-briefing に反映する旨を board に1行記録(任意・改善余地❓)

    重要原則:
      - 抽出 0 件でもファイル移動は実行(2重処理防止)
      - LINE 通知は本種では出さない(翌朝の morning-briefing が「inbox から N 件追加」と報告)
      - ❓ Improvement Hints 参照: 即時 LINE 通知すべきか後追い化要

    失敗時:
      - ファイル読み取り失敗 → on_failure に従う
      - backlog 書き込み失敗 → ファイル移動は実行しない(リトライ余地を残す)
      - カテゴリ判定が完全に失敗 → `## その他` フォールバックで処理続行

# === ③ 結果をどこに置くか ===
outputs:
  - kind: backlog
    path: /home/vps-harappa/garden-mirror/hmc_tasks/backlog.md
  - kind: archive                    # 処理済み inbox 自体は archive 扱い
    path: /home/vps-harappa/garden-mirror/garden/inbox/processed/{today}/{元ファイル名}
  - kind: log
    path: /home/vps-harappa/garden-mirror/garden/log/{today}-inbox-process.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: none                      # 自律完結。翌朝の morning-briefing が結果を見せる
  approver: null
  notify: null

# === ⑤ 承認後の振る舞い ===
post_approval: null

# === ⑥ べき等性 ===
idempotency:
  key: inbox-process-{target_file_basename}-{file_mtime}
  guard: |
    対象ファイルが既に inbox/processed/ 配下にあれば即終了。
    watcher が同じファイル変更を複数回通知しても、processed 移動後の起動は no-op。
    抽出処理は「ファイル → backlog 追記 → 移動」を atomic に行う(中断時の二重追加防止)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 3
    backoff: 5m
  fallback:
    via: gaku-co
    group: personal
    template: |
      ❌ inbox-process 失敗
      対象: {target_file}
      理由: {error_summary}
      詳細: {log_path}
      → 該当ファイルは inbox/ に残置。手動確認推奨

# === ⑧ 依存 ===
depends_on:
  workflow: daily-cycle
  state:
    - "/home/vps-harappa/garden-mirror/garden/inbox/ 配下に投入ファイルが存在"
    - "/home/vps-harappa/garden-mirror/garden/inbox/processed/ ディレクトリが存在(無ければ自動作成)"
    - "/home/vps-harappa/garden-mirror/hmc_tasks/backlog.md が存在・有効"
    - "watcher daemon が稼働(glob 監視)"
    - "LiveSync 平文 MD ミラーが最新化されている"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null           # event 駆動なので予測不可
---

# inbox-process — inbox の振り分け

## 目的(不変)

`/home/vps-harappa/garden-mirror/garden/inbox/*.md` に投入された外部情報(議事録・letter・メール抽出 等)から、塚越さん宛のアクション項目を抽出し、backlog の適切なカテゴリへ振り分ける。投入元から塚越さんの「今日やること」への流路を自動化する。

## 現状の方法

frontmatter の `execute` / `outputs` を参照。要約:

1. watcher daemon が `/home/vps-harappa/garden-mirror/garden/inbox/*.md` の新規 / 変更を検知
2. 該当ファイルを読む(`source:` frontmatter を尊重)
3. アクション項目を 0〜N 件抽出
4. backlog の Level 2 ヘッダ(カテゴリ)へ振り分け追記
5. 締切なしなら **翌日デフォルト暫定締切**(night-review と同ルール)
6. 処理済みファイルを `inbox/processed/{today}/` へ移動
7. ログ出力

## 投入元(現在想定)

| 投入元 | 形式 | 投入方法 |
|---|---|---|
| 議事録(Plaud) | MD(自動文字起こし) | Plaud → inbox/ 自動投入(Phase 3 横断課題) |
| letter スキャン | MD | `letter_opener` SKILL(HMC)から手動エクスポート |
| メール抽出 | MD | `email_organizer` SKILL(HMC)から手動エクスポート |
| 手動投入 | MD | 任意の MD ファイルを `/home/vps-harappa/garden-mirror/garden/inbox/` に置く |

`letter_opener` / `email_organizer` の自動連携は Phase 3 後フェーズ・Phase 4 課題。

## inbox ファイル frontmatter 推奨

```markdown
---
source: meeting | letter | email | manual
date: YYYY-MM-DD
title: 会議タイトル/差出人/件名
suggested_category: 開発 | 財務 | 営業 | その他    # 任意。種側ヒント
---

(本文)
```

抽出時に frontmatter があれば優先尊重。なくても本文から推測。

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | カテゴリ振り分けは Claude の判断 | backlog の Level 2 ヘッダ(`## 開発` 等)に厳密に揃えるルールが必要。マッピング失敗時の `## その他` フォールバック仕様未確定 | 未検証(daily-cycle ステップ5 と同期) |
| ❓ | 投入元の多様化 | 議事録 / letter / メール / Slack 等への拡張時、共通 frontmatter フォーマット要件が要るか未検証 | 未検証 |
| 💡 | 処理結果のレビュー | 翌朝の brief で「inbox から N 件追加」と要約表示(morning-briefing 側で実装) | 着手可能 |
| ❓ | LINE 即時通知の要否 | 現状なし(翌朝 brief で報告)。緊急性高い投入(letter / 重要メール)で即時通知が要るか未検証 | 未検証 |
| ❓ | watcher daemon の実装方式 | inotify / fsnotify / polling のどれを採用するか未確定。VPS Docker 環境での選択が要 | 未検証(Phase 3a インフラ課題) |
| ✋ | event 種の trigger.exclude フィールド | `processed/` 除外用。[seed-schema-extensions ADR](../../../docs/decisions/2026-05-27-seed-schema-extensions.md) で正式採用済 | **検討済**(S13 で ADR 化) |
| ✋ | event 種の `{event.path}` 変数 | watcher daemon が渡すマッチパス。同 ADR で正式化 | **検討済**(S13 で ADR 化) |
| ✋ | trigger.debounce フィールド | 連続書き込みファイナル待ち。同 ADR で正式採用済(実装方式は Phase 3a A-1 で確定) | **検討済**(S13 で ADR 化) |
| 💡 | atomic 処理 | ファイル → backlog → 移動 の中断時に二重追加するリスク。lockfile or 一時ファイル経由の atomic 化 | 構想中 |
| ❓ | カテゴリマッピングの保守 | 投入元 → カテゴリ のマッピング表を MD で持つか、Claude の判断に任せるか | 未検証 |

## 関連

- workflow: [[daily-cycle]] ステップ5
- 元 SKILL: `hmc_pilot`(HMC)
- 投入元 SKILL: `letter_opener`(HMC)、`email_organizer`(HMC)、`minute_maker`(HMC、議事録)
- ADR セッション6: [デイリーワークフロー種化](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md) 決定3(4本立て)
- ADR セッション7: [種スキーマ](../../../docs/decisions/2026-05-25-seed-schema-and-execution-host.md)
- 関連種:
  - `daily-pilot/morning-briefing`(翌朝、振り分け結果を要約報告)
  - `daily-pilot/night-review`(暫定締切ルールを共通化)

## TODO(本種に固有)

- [ ] watcher daemon の実装方式選定(inotify / fsnotify / polling)
- [ ] event 種スキーマ拡張の合意(trigger.exclude / trigger.debounce / {event.path} 変数命名)
- [ ] inbox ファイルの推奨 frontmatter フォーマット確定
- [ ] backlog Level 2 ヘッダ規約(カテゴリ命名)の確定
- [ ] カテゴリマッピング(投入元・本文 → ヘッダ)のロジック確定
- [ ] 即時通知要否の運用判断(緊急性高い投入は LINE で即通知)
- [ ] atomic 処理機構の実装(lockfile / 一時ファイル経由)
- [ ] morning-briefing 側との連携(「inbox から N 件追加」表示)

## active 化条件(Phase 3a の入口)

本種は **Garden 内完結種**(`hmc_dependency: none`)で Phase 3a の対象。**event 種** のため、他3本(cron 種)とは別の前提が要る。

### Phase 3a 由来の前提(全種共通)

1. 種ランチャー(VPS cron → `claude -p` 起動)→ 本種では cron ではなく watcher 駆動
2. **watcher daemon**(`/home/vps-harappa/garden-mirror/garden/inbox/*.md` 監視 → 本種起動 + on_failure)— **本種が前提とする必須インフラ**
3. **平文 MD ミラー daemon**(CouchDB `_changes` → `/home/vps-harappa/garden-mirror/garden/inbox/*.md` 同期)
4. ガクコ `/send`(personal)— on_failure 通知用

### 本種固有

5. event 種スキーマ拡張(trigger.exclude / trigger.debounce / {event.path})の正式化
6. inbox 投入元別の frontmatter フォーマット(議事録 / letter / メール)
7. backlog カテゴリヘッダ規約
8. inbox/processed/{today}/ ディレクトリ構造の合意
