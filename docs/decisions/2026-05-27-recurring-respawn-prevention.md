# 案 E: recurring 完了済み再 spawn 防止 — `<!-- recur:{id}@{period_id} -->` マーカー方式

- **日付**: 2026-05-27(ADR 起草日)
- **決定日**: 2026-05-25(セッション8)
- **記録**: セッション8 で合意 → セッション13 で正式 ADR 化
- **決定者**: 塚越さん(庭師) / Claude
- **ステータス**: 合意・実装は `daily-pilot/recurring-spawn` の draft に反映済 / Phase 3a A-1(本番ランチャー)実装時に動作検証

## 背景

セッション6・7 で「**recurring_master → backlog → active → archive**」というデイリーワークフローのデータフロー(以下 BAA フロー)を確定。`daily-pilot/recurring-spawn` 種が毎日 06:25 に recurring_master を見て、当該期間のインスタンスを backlog に追加する役割を担う。

セッション8 の draft 起草中に塚越さんから **本質的な指摘**:

> monthly のタスクは、完了して archive に入った後、同じ月の中で再 spawn されないか?

3 つのシナリオで具体問題が表面化:

| # | シナリオ | 問題 |
|---|---|---|
| 1 | 月初に spawn → 同日 active で完了 → archive 行き → 翌日再 spawn 時 | backlog から消えた状態を「未追加」と誤判定し再 spawn |
| 2 | 「月初 N 営業日」「第N週」等の複数日許容 period | 期間内の各日で再 spawn 判定が走り、重複生成 |
| 3 | recurring_master 側の表記揺れ(全角半角・改行・装飾) | name による grep マッチ失敗で「未追加」誤判定 → 重複 |

## 検討した案

| 案 | 概要 | 採否 |
|---|---|---|
| A | recurring-spawn を冪等にせず、ロックファイルで実行制御 | 却下(複数日許容 period に対応できない) |
| B | spawn 済み情報を **別ファイル**(例: `_recur_state.md`)に記録 | 却下(BAA フロー外にもう 1 ファイル増える / 同期負荷) |
| C | recurring_master の各エントリに `last_completed` 等の状態を持たせる | 却下(マスタが状態を持つと「ビューと派生」の関係が崩れる) |
| D | name のハッシュをキーに spawn 済みリストを backlog 末尾に隠す | 却下(可読性悪化 + name 表記揺れに弱い) |
| **E** | **backlog/archive の行末に `<!-- recur:{id}@{period_id} -->` マーカーを埋め、両方を grep で判定** | **採択** |

## 決定

### 案 E の中核

1. **キー** = `recur:{id}@{period_id}`
   - 例 1: `recur:r001@2026-06`(monthly)
   - 例 2: `recur:r023@2026-06-04`(daily)
   - 例 3: `recur:r045@2026-W23`(weekly、ISO週)
2. **マーカー** = `<!-- recur:{id}@{period_id} -->` を **backlog 行末** に埋め込む
3. **判定** = recurring-spawn が **backlog + archive の両方を grep**(`grep -F 'recur:r001@2026-06'`)し、ヒットすれば skip
4. **転記時の保持** = night-review が `[x]` → archive 転記時、**元行を完全保持**(マーカー含む)

### マーカーの位置

backlog の行末。例:

```markdown
- [ ] 2026-06-15 月次シフト確定通知 <!-- recur:r001@2026-06 -->
- [ ] 2026-06-04 daily-pilot 朝ブリーフ <!-- recur:r023@2026-06-04 -->
```

行末コメントは Obsidian で非表示・Markdown レンダラでも非表示(HTML コメント扱い)。LiveSync 経由で plain text として保存される。

### 前提条件(セット)

案 E が成立するためには **以下 3 条件が必須**:

| 前提 | 内容 | 反映先 |
|---|---|---|
| ① recurring_master の `id:` 必須 | 各エントリにユニーク ID(`r001` 等)。表記揺れ対策の根本 | recurring_master スキーマ要件 |
| ② night-review の **元行完全保持** | `[x]` → archive 転記時にマーカー含む全文をそのまま転記。`[x] →` への置換などで欠落させない | `daily-pilot/night-review.md` 本文 |
| ③ archive は grep 可能な単一ストレージ | 月別ファイル分割しても良いが、grep 範囲は「全期間 archive + backlog」 | archive 設計時に確認 |

### period_id の生成規約

trigger.schedule から決定論的に算出する:

| period | period_id 例 | 算出方法 |
|---|---|---|
| daily | `2026-06-04` | 発火日(JST) |
| weekly | `2026-W23` | ISO 週(JST 基準) |
| monthly | `2026-06` | 発火月(JST) |
| yearly | `2026` | 発火年(JST) |
| 月初 N 営業日 | `2026-06`(月単位) | period 内のどの日に走っても同じ月 ID |
| 第 N 週 | `2026-W23` | ISO 週 ID |

**重要**: 「複数日許容 period」(例: 月初 1-3 営業日のどこかで動く)でも **period_id は単一の月 ID** にする。これで同一 period 内の重複が構造的に防げる。

## 実装インターフェース(recurring-spawn 種の prompt 内擬似コード)

```
for each entry in recurring_master:
  id = entry.id
  period_id = compute_period_id(entry.period, now)
  marker = f"recur:{id}@{period_id}"
  if grep -F marker backlog.md OR grep -F marker archive/**/*.md:
    skip
  else:
    append to backlog: f"- [ ] {due} {entry.name} <!-- {marker} -->"
```

実装本体は `daily-pilot/recurring-spawn.md` 本文の手順節を参照。

## トレードオフ

### 採用理由

- BAA フローの **3 ファイル(backlog / active / archive)** に閉じる
- マーカーは **plain text**(LiveSync の同期負荷ゼロ)
- ID で判定するので **name 表記揺れに影響されない**
- archive を消さない限り再 spawn が永久に起きない(過去 period への手動追加にも対応可)

### 妥協点 / 留意点

- **archive ファイル数が増えると grep コストが上がる**:
  - 月別ファイル分割の閾値設計が必要(Phase 3a A-1 で具体化)
  - 初期は全期間単一ファイルでも問題ないと判断(年単位で数千行程度の見込み)
- **手動で backlog から削除した recurring** は「未完了のまま再 spawn されない」状態に固定される:
  - 期待挙動(削除 = 「今期間は不要」の意思表示)と整合
  - 翌 period では新しい `period_id` で再 spawn される
- **archive 編集事故への耐性は低い**:
  - 既存マーカーを手で書き換えてしまうと再 spawn が起きる
  - 対策: archive は read-only 運用、night-review 以外は触らない規律

### 棄却した代替を再採用する条件

- **案 B**(別ファイル化)= もし将来「マーカー量が backlog/archive のノイズになる」と判断される or grep コストが問題化したら再検討
- **案 C**(master 側 state)= もし「ビューと派生」の関係を別の形で整理する設計判断が出たら再検討

## recurring_master.md スキーマ要件(本 ADR で確定する最小)

```yaml
- id: r001           # 必須(案 E の根本前提)
  name: 月次シフト確定通知
  period: monthly     # daily | weekly | monthly | yearly
  day: 10             # daily/weekly/monthly のどの日に発火
  category: shift_manager
  description: 月次のシフト確定をスタッフに通知
```

| フィールド | 必須? | 用途 |
|---|---|---|
| `id` | **必須** | 案 E のマーカーキー。一度発行したら絶対に変えない |
| `name` | 必須 | 人間が読む名前(変更可) |
| `period` | 必須 | 期間種別 |
| `day` / `weekday` / `month_day` | 任意 | period に応じた発火日 |
| `category` | 任意 | plot との対応 |
| `description` | 任意 | 補足 |

**ID 規約**:

- フォーマット = `r{連番:03}`(`r001`, `r002`, ...)
- 一度発行した ID は **絶対に再利用しない**(欠番 OK)
- ID の付与は recurring_master 編集時に塚越さん or Claude が振る

## night-review の連動改訂(必須)

night-review が `[x]` → archive 転記する際の **元行完全保持** が案 E の前提。 [daily-pilot/night-review.md](../../garden/seeds/daily-pilot/night-review.md) 本文に下記を明示済:

> archive 転記時は元行を **完全保持**。マーカー(`<!-- recur:... -->`)を含む末尾コメント・空白・装飾も書き換えず転記する。`[x] →` への置換、空白正規化、改行除去は禁止。

## 適用範囲

### 即時適用(セッション8 で実施済)

- [garden/seeds/daily-pilot/recurring-spawn.md](../../garden/seeds/daily-pilot/recurring-spawn.md) — 案 E 手順を prompt に反映
- [garden/seeds/daily-pilot/night-review.md](../../garden/seeds/daily-pilot/night-review.md) — 元行完全保持を明示
- [garden/seeds/README.md](../../garden/seeds/README.md) — 種一覧で案 E 反映済を注記
- [garden/MAP.md](../../garden/MAP.md) — 決定索引に追記

### 本 ADR 化に伴う追記(セッション13)

- ADR 起草(本ファイル) + MAP.md「主要決定の索引」に正式 ADR リンクを追記

### Phase 3a A-1 実装で検証する事項

- backlog/archive のサイズが増えても grep が現実的速度で完了するか
- archive の月別分割が必要になる閾値(行数 / ファイルサイズ)
- 手動編集事故対策(read-only 規律で十分か)

### 未決事項(別議論)

- recurring_master の既存 recurring(HMC・紙ベース・運用上のもの)からの **移行計画**(MAP.md 宿題)
- monthly の period 表現の柔軟性(「月末」「第N曜日」等をどこまで持たせるか)
- 非 recurring タスク(inbox/board からの追加)へのマーカー付与の要否

## 既存決定との関係

- **依存**:
  - セッション6 ADR — BAA フロー(backlog がマスタ・active は派生ビュー)
  - セッション7 ADR — 種スキーマ草案
- **拡張**:
  - recurring_master.md に `id` 必須を追加(本 ADR で確定)
  - night-review の挙動に「元行完全保持」制約を追加
- **影響**:
  - [seed-schema-extensions ADR](2026-05-27-seed-schema-extensions.md) と合わせて、daily-pilot 系の Phase 3a A-1 実装条件が揃う

## 関連

- [セッション8 サマリ](../sessions/2026-05-25-session8.md)
- [seed-schema-extensions ADR](2026-05-27-seed-schema-extensions.md)
- [セッション6 ADR(BAA フロー)](2026-05-25-daily-workflow-and-task-master-architecture.md)
- [セッション7 ADR(種スキーマ)](2026-05-25-seed-schema-and-execution-host.md)
- [garden/seeds/daily-pilot/recurring-spawn.md](../../garden/seeds/daily-pilot/recurring-spawn.md)
- [garden/seeds/daily-pilot/night-review.md](../../garden/seeds/daily-pilot/night-review.md)
