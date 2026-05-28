---
type: seed
name: morning-briefing
plot: daily-pilot
description: 毎日 06:30 に backlog → active 抽出 + calendar 取得 + Triage 質問生成 + LINE 通知する種
status: active
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-05-25
created_by: claude (with 塚越さん, セッション8)
last_updated: 2026-05-28
activated: 2026-05-28   # セッション15: cron 06:30 自動発火 → backlog→active 抽出 + Triage 生成を実証して active 化(calendar MCP 認証は後追い)
linked_workflows:
  - "[[daily-cycle]]"   # ステップ2
linked_skills:
  - "hmc_pilot (HMC)"   # 移行元(手順参照のみ)
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "30 6 * * *"           # 毎日 06:30 JST
  timezone: Asia/Tokyo
  # 議論余地: 早朝移動日のカレンダー連動シフト(daily-cycle ステップ2 改善余地❓)

# === ② 何を実行するか ===
engine: claude-code
execute:
  skill: hmc_pilot (HMC)           # 当面は手順参照のみ。実行は Garden 内 MD + MCP(Calendar)で完結
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    today_md: "$(date +%-m/%-d)"
    today_slash: "$(date +%Y/%m/%d)"
    today_jp: "$(date +%-m月%-d日)"
    # 曜日は VPS に ja_JP.UTF-8 locale 未導入のため、prompt 内で Claude が today から判定する
  prompt: |
    あなたは daily-pilot 区画の種「morning-briefing」です。
    目的: 塚越さんが iPhone 一画面で「今日(= {today_jp}、曜日は {today} から判定)やること」を把握できる
          状態を作る。曜日は (月)(火)(水)(木)(金)(土)(日) のいずれかで表記する。

    手順:
      1. 入力読み込み
         - /home/vps-harappa/garden-mirror/hmc_tasks/backlog.md(deadline = {today} or それ以前のタスクを抽出)
         - /home/vps-harappa/garden-mirror/hmc_tasks/active_tasks.md(前夜に night-review がクリアしているはず)
         - Google Calendar(MCP)から本日 {today} の予定取得
         - /home/vps-harappa/garden-mirror/garden/board/triage/{today}-morning-briefing.md(存在すれば「resume モード」、後述)

      2. **resume モード判定**
         - {today}-morning-briefing.md が存在し、`status: awaiting_triage` または塚越さんの
           回答(LINE 短文返信 or board 直接編集)が反映されている → resume モードへ
         - 存在しない → 通常の初回起動モード

      3-A. **初回モード**
         a. backlog から **deadline ≦ today** のタスクを active_tasks.md にコピー
            (backlog からは削除しない。マスタは backlog)
            - active_tasks のテンプレ構造: `# Today's Tasks - {today_slash} (曜日)` ヘッダ +
              `## スケジュール` + `## 運営・企画` + `## 管理事務` + `## 家のこと` + `## 追加` の順
              ※ 曜日は {today} から判定して (月)(火)(水)(木)(金)(土)(日) のいずれかで表記
            - 期限超過タスクは `🚨 期限超過` セクションを冒頭に挿入して分けて表示
            - 暫定締切タスク(`・暫定` 付き)は Triage 候補に格上げ(後述 c)
            - backlog の Level 2 カテゴリ(`## 運営・企画` 等)を尊重して active のセクション分けに反映
         b. カレンダー予定の埋め込み
            - **Google Calendar MCP 利用可** → 取得した本日 {today} の予定を active_tasks.md の
              `## スケジュール` セクションに `- HH:MM タイトル` 形式で埋め込み
            - **Google Calendar MCP 失敗(認証切れ等)** → `## スケジュール` セクションに
              `- ⚠️ カレンダー取得失敗(MCP 未認証 or エラー)` と 1 行だけ書いて続行
              ※ Phase 3 検証中の暫定モード。MCP 認証完了で自動的に通常モードへ
         c. Triage 候補を抽出し、board/{today}-morning-briefing.md に質問入り MD を生成:
            - 暫定締切タスク → 「Q1: 締切確認が必要なタスク」
            - 曖昧期限(「来週」「近日」「ASAP」等の自然言語のみ) → 「Q2: 締切の数値化」
            - AI 支援候補(時間がかかる・要調査・要相談 等) → 「Q3: AI 支援提案」
            - status: awaiting_triage, 質問なし(0件)なら status: confirmed で完結扱い
         d. 完了報告のログ出力(LINE 通知はモック化中、ガクコ /send は呼ばない)
            作成する報告文面を `/home/vps-harappa/garden-mirror/garden/log/{today}-morning-briefing.log` の
            末尾に **`==NOTIFY==` ブロックで append**(launcher が既存内容を書いた後の末尾に追記):
            - Triage 0件 → 「✅ {today_jp} ブリーフ。アクション X件 / 予定 Y件」
            - Triage 1件以上 → 「📋 {today_jp} ブリーフ + Triage X件。board 確認 → 返信か編集で」
            (Phase 3 で ガクコ /send 連携が組まれたら、この文面を /send に投げる)

      3-B. **resume モード**
         a. board/{today}-morning-briefing.md の塚越さん回答(LINE 受信 by gaku-co5.0 or 手動編集)
            を読み解く
         b. 回答を active_tasks.md / backlog.md(締切修正等)に反映
         c. board ファイルの status を `triage-done` に更新
         d. LINE 通知: 「✅ Triage 反映済み。最終ブリーフは active_tasks.md」

      4. ログ出力
         - 抽出件数・カレンダー件数・Triage 件数を
           `/home/vps-harappa/garden-mirror/garden/log/{today}-morning-briefing.log` の末尾に追記

    重要原則:
      - backlog は読み取り専用(本種では更新しない。night-review が反映する)
      - active_tasks は毎朝再構築(前夜にクリアされている前提)
      - カレンダー取得失敗 → 「⚠️ カレンダー取得失敗」を active 冒頭に表示するだけで処理続行

    失敗時:
      - backlog.md 読み取り失敗 → on_failure に従う(致命的)
      - calendar(MCP)失敗 → 続行(警告のみ)
      - board ファイル書き込み失敗 → on_failure に従う

# === ③ 結果をどこに置くか ===
outputs:
  - kind: active_tasks
    path: /home/vps-harappa/garden-mirror/hmc_tasks/active_tasks.md
  - kind: board_draft
    path: /home/vps-harappa/garden-mirror/garden/board/triage/{today}-morning-briefing.md
  - kind: log
    path: /home/vps-harappa/garden-mirror/garden/log/{today}-morning-briefing.log

# === ④ 誰に剪定依頼するか ===
# 注: Phase 3a 検証中はガクコ /send 呼び出しを行わず、prompt 内で log 末尾に
#     `==NOTIFY==` ブロックとして書き出すモックモード。連携実装後に有効化する。
pruning:
  channel: line                    # Triage は軽量・即応性重視(LINE 短文返信が中心)
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # 当面: log に書き出すだけ
    # via: gaku-co                 # 将来: ガクコ /send 連携 active 化後
    group: personal
    template_no_triage: |
      ✅ {today_jp} ブリーフ
      アクション: {active_count}件 (期限超過: {overdue_count}件)
      予定: {calendar_count}件
      → /home/vps-harappa/garden-mirror/hmc_tasks/active_tasks.md
    template_with_triage: |
      📋 {today_jp} ブリーフ + Triage {triage_count}件
      → 返信(短文)or board 編集で回答
      → /home/vps-harappa/garden-mirror/garden/board/triage/{today}-morning-briefing.md

# === ⑤ 承認後の振る舞い ===
# Triage は「approve」ではなく「回答を受けて active を更新」する方式のため post_approval は使わない。
# resume モードで処理が完結する(execute.prompt 3-B 参照)。
post_approval: null

# === ⑥ べき等性 ===
idempotency:
  key: morning-briefing-{today}
  guard: |
    初回モード: 同日2回起動時、{today}-morning-briefing.md が存在 + status: awaiting_triage なら
                 新規生成せず resume モードに切り替え。
    resume モード: status: triage-done になっていれば、本種の追加実行はスキップ。
    active_tasks.md は毎朝完全に再構築する(差分マージしない)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 5m
  fallback:
    via: gaku-co
    group: personal
    template: |
      ❌ morning-briefing 失敗 ({today})
      理由: {error_summary}
      詳細: {log_path}
      → 当日の active_tasks が空 or 古いまま。手動で hmc_pilot に切り替えるか検討

# === ⑧ 依存 ===
depends_on:
  workflow: daily-cycle
  state:
    - "/home/vps-harappa/garden-mirror/hmc_tasks/backlog.md が存在・有効"
    - "/home/vps-harappa/garden-mirror/hmc_tasks/active_tasks.md が前夜の night-review でクリア済み"
    - "Google Calendar MCP が稼働(失敗時は警告のみで続行)"
    - "ガクコ /send が利用可能(personal グループ)"
    - "board ファイルの resume を起動する watcher daemon が稼働(Phase 3a インフラ)"
  seeds:
    - "recurring-spawn (本種の 5 分前に発火、backlog 更新)"

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-05-26T06:30:00+09:00
---

# morning-briefing — 朝のブリーフィング + Triage

## 目的(不変)

毎日朝 06:30、塚越さんが iPhone 一画面で「**今日やること**」を把握できる状態を作る。曖昧期限や暫定締切は Triage で短文確認まで終わらせ、active_tasks が「迷いなく着手できる」形になっていることが必須。

## 現状の方法

frontmatter の `execute` / `outputs` / `pruning` を参照。要約:

1. cron 毎日 06:30 発火(recurring-spawn の 5 分後)
2. backlog から deadline ≦ today を active_tasks に抽出
3. Google Calendar(MCP)から本日予定取得し active 冒頭に貼る
4. Triage 候補(暫定締切 / 曖昧期限 / AI 支援候補)を board/{today}-morning-briefing.md に生成
5. LINE 通知(Triage 0 件 / 1 件以上で文面差)
6. 塚越さんが返信 or board 編集 → watcher daemon が **resume モード** で本種を再起動
7. resume が active を最終化 → 完了 LINE

## Triage の対話チャネル(ADR セッション6 決定5)

- LINE 短文返信 = 軽量回答(「a」「b」「明日」等)
- board MD 直接編集 = 構造化された複数回答 / 修正
- watcher daemon が board ファイル変化を検知 → 本種を resume モードで再起動
- Triage 0 件の日は board 生成のみ(質問なし=即 confirmed)

## board ファイルのテンプレ(後述)

`/home/vps-harappa/garden-mirror/garden/board/triage/{today}-morning-briefing.md` ([garden-board-structure ADR](../../../docs/decisions/2026-05-27-garden-board-structure.md) で triage/ 配置確定):

```markdown
---
type: pruning_request
from_seed: daily-pilot/morning-briefing
date: {today}
status: awaiting_triage | triage-done
created: {today}T06:30:00+09:00
triage_count: 3
---

# {today_jp} {weekday_jp} 朝のブリーフィング

## 本日の予定(カレンダー)

(active_tasks に同じものを貼る)

## Triage(回答ください)

### Q1: 締切確認が必要なタスク(夜種で暫定設定)

- [ ] 「{タスク}」 → 暫定: 今日({today_md})
  - [ ] (a) 今日のままで OK
  - [ ] (b) 今週中(金曜まで)
  - [ ] (c) 自由記述: ____

### Q2: 締切の数値化が必要なタスク

- [ ] 「{タスク}」 → 自然言語期限「来週」
  - [ ] (a) 月曜まで
  - [ ] (b) 金曜まで
  - [ ] (c) 自由記述: ____

### Q3: AI 支援提案

- [ ] 「{タスク}」 → 提案: claude-code で下調べを作成
  - [ ] (a) Yes(下調べ実行)
  - [ ] (b) No(自分でやる)

## 庭師アクション

- LINE 短文返信なら: 「Q1: a / Q2: b / Q3: a」のような形式
- 詳細編集なら: 本ファイルを Obsidian で編集 → 保存(LiveSync で VPS 反映)
```

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 固定 06:30 発火 | 早朝移動日(05:30 出発等)はカレンダー連動で動的シフトする選択肢あり | 未検証(daily-cycle ステップ2 と同期) |
| ❓ | カレンダーは Google Calendar 1 経路 | 他カレンダー(出張・家族)との統合が要るか未確認 | 未検証 |
| 💡 | LINE 通知文面 | iPhone で読みやすい長さ(2〜3行)に磨く余地 | 着手可能 |
| ❓ | Triage の resume 機構 = watcher daemon | board ファイル更新 → 本種 resume 再起動の仕組み未実装(Phase 3a 課題) | 未検証(Phase 3a インフラ) |
| ❓ | LINE 短文返信の構文(「Q1: a」等) | 構文ゆれ対応 + 自由記述パースは gaku-co5.0 側の責務分担と要相談 | 未検証(gaku-co5.0 INTERFACE と同期) |
| 💡 | 期限超過タスクの目立たせ方 | `🚨 期限超過` セクション + LINE 通知の overdue_count に明示 | 着手可能 |
| ❓ | Triage 0 件の日の挙動 | board 生成は要らない説も。生成して `status: confirmed` で運用ログに残す方が後追いしやすいか | 未検証 |
| ❓ | resume と初回の同一種を兼ねる構成 | 別種(`morning-briefing-resume`)に分けると依存関係が明確になるが「4本立て」に反する。要再検討 | 未検証 |

## 関連

- workflow: [[daily-cycle]] ステップ2
- 元 SKILL: `hmc_pilot`(HMC)— 旧朝ブリーフ手順
- ADR セッション6: [デイリーワークフロー種化](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md) 決定3・決定4・決定5(Triage ハイブリッド)
- ADR セッション7: [種スキーマ](../../../docs/decisions/2026-05-25-seed-schema-and-execution-host.md)
- 関連種:
  - `daily-pilot/recurring-spawn`(本種の 5 分前)
  - `daily-pilot/night-review`(前夜 22:30、active クリアの担当)
  - `daily-pilot/inbox-process`(随時、backlog 追記)
- ガクコ INTERFACE: [/home/tukapontas/gaku-co5.0/INTERFACE.md](file:///home/tukapontas/gaku-co5.0/INTERFACE.md) — `/send`、LINE 返信 webhook

## TODO(本種に固有)

- [ ] watcher daemon の設計(board ファイル変更 → 本種 resume 起動)
- [ ] LINE 短文返信 → board 書き戻し処理(gaku-co5.0 側)の連携仕様
- [ ] Triage Q の構造(Q1/Q2/Q3 + 選択肢 a/b/c)の正式テンプレ化
- [ ] active_tasks のフォーマット規約(冒頭カレンダー / 期限超過 / 暫定締切 / 通常 の並び順)
- [ ] resume と初回起動を同一種で兼ねる是非の再検討(分離した方が依存追跡が楽になる)
- [ ] LINE 通知文面(no_triage / with_triage)の磨き

## active 化条件(Phase 3a の入口)

本種は **Garden 内完結種**(`hmc_dependency: none`)で Phase 3a の対象。

### Phase 3a 由来の前提(全種共通)

1. 種ランチャー(VPS cron → `claude -p` 起動 + ログ + on_failure)
2. **平文 MD ミラー daemon**(CouchDB `_changes` → `/home/vps-harappa/garden-mirror/hmc_tasks/*.md` 同期)
3. **watcher daemon**(`/home/vps-harappa/garden-mirror/garden/board/triage/*.md` 変更検知 → 該当種 resume 起動)
4. Google Calendar MCP の VPS Claude Code への結合
5. ガクコ `/send`(personal)経由 LINE 通知の最小ループ
6. gaku-co5.0 側 「LINE 返信 → board MD 書き戻し」 処理の実装

### 本種固有

7. board ファイルの Triage テンプレ規約確定(Q 構造・選択肢構文)
8. LINE 短文返信パターン(「Q1: a」等)の合意 + パーサ実装(gaku-co5.0)
9. resume モードの動作確認(初回 → 回答 → resume → 完了 のループ)
