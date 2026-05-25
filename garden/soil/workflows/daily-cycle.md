---
type: workflow
status: active
dynamism: static
cycle: 日次
scope: 個人(塚越さん)の業務管理(タスク・スケジュール)
linked_workflows:
  - "[[monthly-cycle]]"
  - "[[program-execution]]"
linked_skills:
  - "hmc_pilot (HMC)"
sources:
  - "HMC hmc_pilot SKILL.md(現状の手順)"
  - "塚越さん 2026-05-25 セッション6 種化方針"
last_updated: 2026-05-25
last_updated_by: claude
---

# (D) デイリーサイクル(個人タスク管理)

> 塚越さんの日々のタスク・スケジュール管理ルーチン。HMC では `hmc_pilot` SKILL に手順が定義されていたが、塚越さんアクション起点 → **HMG では種(cron)起点** に転換する。

**注**: 各ステップは「**目的 (Purpose)**」と「**現状の方法 (Current Method)**」を分けて記述している。目的は不変、方法は改善対象。詳細は [README.md](README.md) と [ADR 2026-05-25](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md)。

## データモデル(全ステップ共通)

```
recurring_master ──┐
                   ├─→ backlog ──→ active_tasks ──→ archive
inbox/*.md  ───────┘                  ↑                ↑
                                  brief時に           night
                                  「今日」を抽出        review時
```

- **`backlog.md` = 唯一のマスタ**(永続)
- **`active_tasks.md` = 今日のビュー**(派生・毎晩クリア)
- **`archive.md` = 完了履歴**(永続・追記のみ)
- **`recurring_master.md` = 定期タスクのテンプレ**(編集は手動・運用中変更しない)
- **`inbox/*.md` = 外部からの投入**(議事録・letter・メール抽出 等)

## 全体図

```
[毎日 06:25]   🌱 recurring-spawn      recurring → backlog
[毎日 06:30]   🌱 morning-briefing     backlog → active + LINE通知 (+ Triage)
[日中]         手動                    塚越さんが active を編集(チェック・追加)
[毎日 22:30]   🌱 night-review         active → backlog/archive + LINE報告
[適宜]         🌱 inbox-process        inbox/*.md → backlog 振り分け
```

すべての種は **VPS 上で `claude -p` ヘッドレス起動**。詳細は [ADR](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md) 決定4 参照。

---

## ステップ

### 1. 朝の recurring 展開(🌱 daily-pilot/recurring-spawn)

- **時期**: 毎日 06:25(morning-briefing の 5 分前)
- **担当**: 種(自律発火)
- **目的**: 当日締切で実行されるべき定期タスクが backlog にあることを保証する
  - 必須データ: `recurring_master.md`
  - 必須アウトプット: `backlog.md` への当該期間インスタンス追加
- **現状の方法**(種化後):
  1. `recurring_master.md` を読む
  2. Daily: 今日の日付で未追加なら `(MM/DD締切・定期)` で backlog に追加
  3. Weekly: 該当曜日かつ今週分が未追加なら追加
  4. Monthly: 該当日かつ今月分が未追加なら追加
  5. Yearly: 該当日かつ今年分が未追加なら追加
- **アウトプット**: backlog に当該期間の recurring インスタンスが揃った状態
- **べき等性**: ◎(同日2回実行でも重複しない)

#### 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | recurring_master を MD で持つ | 例外日(祝日・休業日)を扱う仕組みが必要か未検証 | 未検証 |
| 💡 | べき等性は「タスク名一致」で判定する想定 | タスク名の微妙な表記揺れで重複追加するリスクあり。ID または日付付きキーで判定する設計が要 | 着手可能 |

---

### 2. 朝のブリーフィング + Triage(🌱 daily-pilot/morning-briefing)

- **時期**: 毎日 06:30
- **担当**: 種(自律発火)
- **目的**: 塚越さんが iPhone 一画面で「今日やること」を把握できる状態を作る
  - 必須データ: backlog(今日締切), calendar(今日の予定), 暫定締切タスクの抽出
  - 必須アウトプット: active_tasks(確定タスク) + board ファイル(Triage 質問) + LINE 通知
- **現状の方法**(種化後):
  1. `backlog.md` から **deadline = 今日** のタスクを active_tasks にコピー(削除しない)
  2. Google Calendar から今日の予定取得(MCP)
  3. 曖昧期限のタスク・暫定締切タスク・AI 支援候補を抽出 → `board/{date}-morning-briefing.md` に Triage 質問を生成
  4. LINE で「brief できました / Triage X 件あります」と通知(ガクコ経由)
  5. 塚越さんが返信 or board 直接編集 → event 種が resume(別ステップ)
- **アウトプット**:
  - `active_tasks.md` 当日分(Triage 確定後)
  - `board/{date}-morning-briefing.md`
  - LINE 通知
- **依存**: recurring-spawn の完了

#### 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 固定 06:30 発火 | 早朝移動日(05:30 出発等)はカレンダー連動で動的シフトする選択肢あり。実運用後に判断 | 未検証 |
| ❓ | カレンダーは Google Calendar 1 経路のみ | 他カレンダー(出張・家族)との統合が要るか未確認 | 未検証 |
| 💡 | LINE 通知文面 | 通知が long-form だと iPhone で読みにくい。要約 + URL + 短いアクション指示 を磨く余地 | 着手可能 |

---

### 3. 日中 — タスクの編集(手動)

- **時期**: 日中(塚越さんの活動時間中)
- **担当**: 塚越さん
- **目的**: 「進捗反映」と「新規発見の捕捉」を Obsidian の編集で行う
  - 必須データ: なし(自由編集)
  - 必須アウトプット: active_tasks への `[x]` チェック、`## 追加` セクションへの新規追記、`[ ]` 削除等
- **現状の方法**:
  1. PC では Obsidian デスクトップ、外出時は Obsidian iPhone で active_tasks を開く
  2. 完了したタスクに `[x]` を付ける
  3. 日中に思いついたタスクは active_tasks の末尾 `## 追加` セクションへ自由記述
  4. **不要になったタスクは active から削除**(`[ ]` を消す)
  5. 編集は LiveSync で自動的に CouchDB → VPS / 他端末に伝搬(数秒)
- **アウトプット**: 編集された active_tasks
- **重要な原則**:
  - `## 追加` に **締切なしで書いても OK**。night-review が翌日デフォルトで暫定締切を付与する
  - active から削除しても backlog には残る(マスタは backlog)。「今日やらない」判断のために削除可

#### 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 自由記述に頼る | 大量追加・カテゴリ分けが必要な日に整理しきれない可能性。種側の自動カテゴリ振り分けが要るかは運用後に判断 | 未検証 |
| 💡 | LINE から直接「追加」できる経路がない | ガクコ経由で「LINE で短文 → board/inbox に書き込み」できれば移動中の捕捉性が更に向上 | 構想中 |

---

### 4. 夜の振り返り(🌱 daily-pilot/night-review)

- **時期**: 毎日 22:30
- **担当**: 種(自律発火)
- **目的**: 当日の状態を backlog/archive に反映し、active を翌日のためにクリアする
  - 必須データ: active_tasks
  - 必須アウトプット: backlog 更新 + archive 追記 + active クリア + LINE 報告
- **現状の方法**(種化後):
  1. `active_tasks.md` を読む
  2. `[x]` 付き → backlog から削除 + `archive.md` の `## YYYY/MM/DD` 配下に追記
  3. `[ ]` → backlog にはそのまま残す(active から消すだけ。deadline は変えない)
  4. `## 追加` セクションを 4 分岐で処理:
     - `[x]` → archive 直行
     - `[ ]` + 締切あり → backlog へ追記
     - `[ ]` + **締切なし → 翌日デフォルトで暫定締切付与** → `(MM/DD締切・暫定)` 付きで backlog 追記
     - 空 → 何もしない
  5. active_tasks をクリア(空ファイルにする)
  6. LINE で当日サマリ通知:
     ```
     🌱 夜のレビュー YYYY-MM-DD
     ✅ 完了: X件 (archive へ)
     🔄 持ち越し: X件 (backlog 残存)
     ➕ 新規追加: X件
     ```
- **アウトプット**: backlog / archive 反映済み、active クリア済み、LINE 報告済み
- **未編集時の挙動**: 何もせず通常通り処理(差分なし = ファイル変更なし)。LINE は `✅ 0件` で出る

#### 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 暫定締切を翌日デフォルトに固定 | 「金曜の追加 → 月曜暫定」とか営業日ロジックが要るか未検証。最初は単純運用で開始 | 未検証 |
| 💡 | 期限超過タスクは目立たない | 期限超過(deadline < 今日)タスクを LINE 報告で別表示 → 「🚨 期限超過: X件」 | 構想中 |
| ❓ | 22:30 固定 | 夜の追加が間に合わない日が出るか未検証 | 未検証 |

---

### 5. inbox の振り分け(🌱 daily-pilot/inbox-process)

- **時期**: `inbox/*.md` への新規ファイル投入時(event 起点)
- **担当**: 種(自律発火)
- **目的**: 外部から投入された情報(議事録・letter・メール)から、塚越さん宛タスクを抽出して backlog に振り分ける
  - 必須データ: `inbox/{filename}.md`
  - 必須アウトプット: backlog 追記、ファイルを `inbox/processed/` へ移動
- **現状の方法**(種化後):
  1. file watcher が `inbox/` への新規 md 検知
  2. `claude -p "Process inbox file: {path}"` 起動
  3. Claude が内容を読み、塚越さん宛のアクション項目を抽出
  4. backlog の適切なカテゴリ(`## 開発` 等)へ振り分けて追記
  5. 締切が不明なら暫定締切(翌日)を付与
  6. 処理済みファイルを `inbox/processed/` へ移動
- **アウトプット**: backlog 追記済み、ファイル移動済み
- **投入元(現在想定)**:
  - 議事録(Plaud → 自動投入)
  - letter スキャン(letter_opener SKILL から)
  - メール抽出(email_organizer SKILL から)
  - 手動投入(任意の MD ファイルを inbox に置く)

#### 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | カテゴリ振り分けは Claude の判断 | backlog の Level 2 ヘッダ(`## 開発` 等)に厳密に揃えるルールが必要。マッピング失敗時の `## その他` フォールバック設計 | 未検証 |
| ❓ | 投入元の多様化対応 | 議事録だけでなく letter / メール / Slack 等への拡張時、共通フォーマット要件が要るか未検証 | 未検証 |
| 💡 | 処理結果のレビュー | 振り分け結果を朝の brief に「inbox から N 件追加しました」と要約表示 | 着手可能 |

---

## 不変条件(invariants)

- **backlog がマスタ**: active / archive は backlog から派生する
- **active は毎晩クリア**: 翌朝 brief で再構築される
- **締切なしタスクは backlog に存在しない**: night-review / inbox-process が暫定締切を必ず付与
- **すべての出自は backlog に合流**: recurring / inbox / 手動追加の出自分岐は backlog 到達後に消える
- **塚越さんアクションは「剪定」のみ**: 種起点で発火、塚越さんは判断・修正・承認だけを行う

## 種(自律トリガー)— 本ワークフロー由来

| 種 ID | タイミング | 性質 | 着手順 |
|---|---|---|---|
| `daily-pilot/recurring-spawn` | 毎日 06:25 | recurring → backlog 展開 | 順次 |
| `daily-pilot/morning-briefing` | 毎日 06:30 | backlog → active 抽出 + Triage + LINE | 順次 |
| `daily-pilot/night-review` | 毎日 22:30 | active → backlog/archive 反映 + LINE | 順次 |
| `daily-pilot/inbox-process` | event(inbox 投入) | inbox → backlog 振り分け | 順次 |

着手順は **`shift_manager/monthly-shift-survey` の次** に位置づける(同 ADR 適用範囲参照)。

## 関連

- [ADR 2026-05-25 デイリーワークフローの種化とタスクマスタアーキテクチャ](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md)
- [HMC hmc_pilot SKILL](../../../../harappa-cockpit/.agent/skills/hmc_pilot/SKILL.md) — 移行元の処理定義
- [[monthly-cycle]] — 月次サイクル(本サイクルから参照される定期タスクが含まれる)
- [[program-execution]] — プログラム実施フロー(本サイクルのタスクに登場する)
