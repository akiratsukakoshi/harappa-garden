---
name: meeting_coordinator
description: core_team LINE を起点に、社内会議の日程調整、Zoom URL 発行、Google Calendar 登録、toC 会議履歴の入口を担う区画。
plot: meeting_coordinator
topics: [会議調整, 日程調整, Zoom, Google Calendar, 運営会議, 企画会議, 戦略会議, 企画担当会議, core_team, LINE, toC soil]
inherits_from:
  - garden/CHARTER.md
linked_workflows:
  - "[[annual-quarterly-planning]]"
  - "[[program-execution]]"
  - "[[monthly-cycle]]"
requires_soil:
  - garden/soil/people/staff/
created: 2026-06-27
last_updated: 2026-06-27
created_by: codex (with ガクチョ)
status: test
---

# meeting_coordinator — 会議調整区画

core_team LINE で社内会議を調整し、ガクチョまたは発議者の確定を受けて Zoom URL 発行と Google Calendar 登録まで進める区画。

この区画の目的は、日程調整の手間を減らすだけではありません。toC 領域でも、会議予定、Plaud 会議録、企画決定、STORES 予約、フィールド開催後の Notion レポートが後からつながるように、会議を soil の入口として扱います。

## SSOT(正本)

| データ | 正本 | 本区画の扱い |
|---|---|---|
| ガクチョの予定 | Google Calendar(primary) | read/write。候補抽出と確定予定作成 |
| 他参加者の空き | core_team LINE 返信 | 調整 state に記録 |
| Zoom URL | HARAPPA 会社 Zoom アカウント | 確定時に発行 |
| スタッフ email / 呼称 | `garden/soil/people/staff/` | 招待先と表示名の解決 |
| 調整状態 | `garden/services/meeting-coordinator/state/meetings.json` | service の内部 state |

## 判断ルール

- **確定は人間が行う**: 月次会議はガクチョの「確定」、スポット会議は発議者またはガクチョの「確定」で Calendar / Zoom へ書き込む。
- **確定返信の定型**: ガクチョは `運営会議 Aで確定` のように「会議名 + 候補 + 確定」で返す。`A` だけでは確定扱いしない。
- **候補はガクチョの Calendar を優先**: 他参加者の Calendar は見ず、LINE 返信ベースで調整する。
- **標準尺は90分**: 「今回は60分」など明示があれば上書きする。
- **午前優先、夜も可**: 候補は午前、午後、夜の順で提示する。
- **招待は LINE + email**: 確定後、core_team LINE に Zoom URL を通知し、参加者 email へ Google Calendar 招待を送る。
- **確定通知はZoom URLだけ**: CalendarリンクはLINEに出さない(email招待で届くため)。
- **Zoom 主催者と Calendar 主催者は分離**: Zoom は HARAPPA 会社アカウント、Calendar はガクチョの Google Calendar。
- **toC 会議は meeting_type を持つ**: 後続の Plaud / STORES / Notion 連携のため、会議種別と関連 workflow を state に残す。

## Mode 1: Monthly Operations Meeting

**種**: `meeting_coordinator/monthly-ops-meeting-check`(cron 毎月第3月曜 08:30)

毎月の運営会議を調整する。

- 発火: 前月第3週の月曜日 08:30
- 対象日: 翌月5日〜9日の平日
- 候補時間: ガクチョ Calendar の空き時間
- 優先順位: 午前 → 午後 → 夜
- 標準尺: 90分
- 参加者: ガクチョ、少佐、ゆーじさん
- 確定者: ガクチョ
- meeting_type: `operations_monthly`

## Mode 2: Spot Meeting Request

core_team LINE で「参加メンバー」「おおよその時期」「会議タイトル」を受け取り、スポット会議の調整を開始する。

- 発議者が確定できる
- ガクチョの Calendar は候補抽出に使う
- 参加者の空きは LINE 返信ベースで集める
- 必要情報が足りない場合は、会議タイトル / 参加者 / 時期 / 尺を聞き返す

## Mode 3: Availability Collection

参加者からの LINE 返信を調整 state に記録する。

- 例: 「AとCならOK」「6日は午前なら大丈夫」「Bは不可」
- LLM が発話を読み、tool `record_meeting_availability` に参加者・会議ID・返信内容を渡す
- state は事実ログとして残し、最終判断は確定者が行う
- 少佐・ゆーじさん等の返信は確定ではない。ガクコは可否を記録し、ガクチョ判断待ちであることだけ返す

## Mode 4: Confirm Meeting

確定者が候補を選んだら、以下を実行する。

1. Zoom URL を発行
2. Google Calendar に予定を作成
3. 参加者 email に招待通知
4. core_team LINE に確定通知
5. state を `confirmed` に更新

## 会議種別

| meeting_type | 周期 | 参加者 | 備考 |
|---|---|---|---|
| `operations_monthly` | 月1回、月初 | ガクチョ、少佐、ゆーじさん | MVP 対象 |
| `planning_quarterly` | 3カ月に1回、季節ごと | 運営4名 | 企画会議 |
| `strategy_quarterly` | 3カ月に1回 | 運営4名 | 戦略会議 |
| `program_planning` | 企画ごと | ガクチョ、企画担当、現場責任者、ゆーじさん | おやこ/こども学部のみ。自由デー、逗子海岸の海活動は除外 |
| `spot` | 都度 | 発議者指定 | 発議者またはガクチョが確定 |

## toC soil 連携の育て方

MVP では state に `meeting_type` / `related_workflows` / `participants` / `calendar_event_id` / `zoom_join_url` を残すところまでに留める。

次段階で、Plaud 会議録を scribe が取り込む時にこの state と照合し、toC 会議履歴へ接続する。将来の接続先は以下。

- 企画会議 / 運営会議の会議履歴
- STORES 予約の企画公開状態
- シフトカレンダー上の企画担当 / 現場責任者
- 開催後の Notion フィールドレポート

## 実装

| 層 | ファイル |
|---|---|
| service | `garden/services/meeting-coordinator/processor.py` |
| state | `garden/services/meeting-coordinator/state/meetings.json` |
| LINE tools | `garden/services/garden-gaku-co/tools/registry.py` |
| capabilities | `garden/services/garden-gaku-co/capabilities.py` |

## Improvement Hints

| 案 | 状態 |
|---|---|
| 企画会議 / 戦略会議の四半期種を追加 | 未着手 |
| `field_assistant` の企画MTG確認を meeting_coordinator に移管 | 未着手 |
| Plaud scribe と meeting state の照合 | 未着手 |
| toC 会議履歴の soil 配置を決める | 未着手 |
| 参加者返信の候補ID抽出をより厳密化 | 未着手 |
| スポット会議の実運用テスト(参加者・時期・タイトル → 候補 → 確定) | 未着手 |
