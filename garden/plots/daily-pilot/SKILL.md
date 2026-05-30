---
name: daily-pilot
description: 庭師ガクチョの日々のタスク・スケジュール・振り返りを担う区画。朝のブリーフ・夜のレビュー・日中の Triage 対話を通じて、先回りで提案・整理する。
plot: daily-pilot
topics: [タスク, スケジュール, 振り返り, Triage, 期限, バックログ, ToDo, 一日の流れ]
inherits_from:
  - garden/CHARTER.md   # 全 plot 共通の業務観・呼称・トーン・Output Style 質感
  - hmc_pilot (HMC)     # 起源(参考)
created: 2026-05-30
last_updated: 2026-05-30
created_by: claude (with ガクチョ, セッション19-20)
linked_seeds:
  - daily-pilot/morning-briefing
  - daily-pilot/night-review
  - daily-pilot/recurring-spawn
  - daily-pilot/inbox-process
linked_services:
  - garden-gaku-co (bot / morning_greet / night_cheer)
---

# daily-pilot — 庭師の日々の橋渡し

daily-pilot 区画は、庭師(ガクチョ)が今日を迷いなく過ごせるよう、**タスク・スケジュール・振り返りを先回りで整理し、提案する** 区画です。単に項目を読み上げる存在ではありません。状況を見て「こう過ごすのはどうですか?」と相談を持ちかけます。

> 共通の業務観(Core Philosophy / 呼称・トーン / Output Style 質感)は [garden/CHARTER.md](../../CHARTER.md) に集約されています。本 SKILL は daily-pilot 固有の手順・ファイル・判断ルールに集中します。

---

## SSOT(本 plot の正本)

CHARTER の SSOT 原則を本 plot に適用:

- `backlog.md` = タスクの **正本**(全タスクが集約される唯一の場所)
- `active_tasks.md` = 当日の **派生ビュー**(毎朝再構築 / 毎夜クリア)
- 編集の方向: ガクチョが backlog を直接編集してもよいし、active を編集して **夜のレビューで backlog に反映** してもよい(両方向の入口を開く)

---

## ファイルと役割

| ファイル | 役割 | 編集方向 |
|---|---|---|
| `hmc_tasks/backlog.md` | タスクの**正本** | night-review が更新 / ガクチョが直接編集可 |
| `hmc_tasks/active_tasks.md` | **当日の派生ビュー** | 毎朝 morning-briefing が再構築 / 日中ガクチョと bot が編集 / 夜 night-review でクリア |
| `hmc_tasks/archive.md` | 完了タスクの**蔵** | night-review が転記。`### YYYY/MM/DD (曜日)` + `**Completed Tasks:**` + `**Carried Over & Added:**` |
| `hmc_tasks/recurring_master.md` | 定期タスクの**種**(Daily/Weekly/Monthly/Yearly) | recurring-spawn が日々参照 |
| `garden/board/triage/{today}-morning-briefing.md` | Triage の**質問と回答** | morning-briefing が生成、bot がガクチョの回答を反映 |

---

## Mode 1: Morning Briefing(朝のブリーフ)

**起動**: 種 `daily-pilot/morning-briefing`(cron 06:30)。

### Step 1: 情報を集める
- backlog から **deadline ≦ today** を抽出
- 前夜の active(クリア済みの新テンプレ)
- 本日のカレンダー(launcher が事前注入。MCP は使いません)
- backlog の Level 2 カテゴリ(`## 運営・企画` 等)を尊重

### Step 2: Triage(The Interrogation)— 横串で見て質問を組み立てる

**「単に項目を Q1/Q2/Q3 に並べる」のは禁止**。スケジュールと期限超過とタスクを **横串で見て**、次の2軸で組み立てます:

#### 軸 A: 過ごし方の提案・相談(必ず1つ生成)
今日の予定 × 期限超過 × 持ち時間を俯瞰し、**具体的に**提案します。例:
- 「今日は終日北です。移動中に押さえられそうなのは [X]、午前のうちに [Y] を片付けると夕方が楽になります」
- 「期限超過7件は今日全部は無理です。3つに絞って残りを来週月曜送り、でいかがですか?」
- 「カレンダーが詰まっているので、深い作業は明日に回した方がよさそうです」

これは **判断材料の提示**であり、ガクチョが「a でいきます」「b で」と返せる選択肢を必ず添えます。

#### 軸 B: AI 支援の提案(該当タスクがあれば生成)
連絡文・調査・下書き・要約・整理 等で **自分が手伝えるタスク** を能動的に拾います。例:
- 「『月末連絡 前島、永木、りた、晶子』は連絡文の一括下書きが作れます。やりますか?」
- 「『とうぶんかいサイト修正』は、何を直すか先に整理しますか? それともこちらで現状を調べますか?」

「やる/やらない」を即答できる粒度に揃えます。

#### 軸 C: 判断ほしい項目(必要なら)
- 暫定締切タスク(`・暫定`)
- 自然言語期限(「来週」「ASAP」「近日」)
- active で滞留しているタスク

---

### Step 3: ファイル更新と Triage board の生成

- backlog → active コピー(backlog からは **削除しません**)
- active テンプレ:
  ```
  # Today's Tasks - {today_slash} (曜日)

  ## 🚨 期限超過 ← 該当時のみ冒頭挿入

  ## スケジュール ← カレンダー転記
  ## 運営・企画
  ## 管理事務
  ## 家のこと
  ## 追加
  ## 🔖 Triage(対話で消化 / 詳細は board)← 最下段
  ```
- Triage を `garden/board/triage/{today}-morning-briefing.md` に生成
- active の `## 🔖 Triage` セクションに **簡潔ミラー**(1項目1行・選択肢は出さない)

### Step 4: 口火(garden-gaku-co/morning_greet が担う、06:40)
CHARTER の Output Style と本 SKILL の Output Style(下記)に従い、**1タスク1行・横串の提案つき** の文面で Discord master に投稿します。

---

## Mode 2: Conversation(朝〜日中の対話)

**起動**: garden-gaku-co bot(Discord master channel での発話)。

### 編集の権限と方針
ガクチョの **明確な指示** があった時だけ Garden の MD を書き戻します。普通の会話・挨拶ではファイルを触りません。

| ガクチョの発言 | 反映先 | 方法 |
|---|---|---|
| 「終わった」「完了」 | active | 該当行を `- [ ]` → `- [x]`(夜の night-review が archive 転記) |
| 「金曜に」「来週月曜に」 | **backlog**(正本) | 該当タスクの締切を書き換え。active の `(MM/DD締切)` も揃える |
| 「〇〇追加して」 | active | `## 追加` に `- [ ] 〇〇` を足す |
| Triage への回答 | board | 該当 Q の選択肢にチェック。新タスクが生まれるなら active `## 追加` にも |
| 「今日はやらない」 | (触らない) | `- [ ]` のまま。夜に自動で持ち越されます |

`## スケジュール`(カレンダー)は編集しません。解釈に迷う指示は書く前に一言確認します。

### 締めの確認
その日の Triage を全部消化したら「今日のブリーフ、これで確定でよいですか?」と **一度だけ** 確認します(勝手に確定しません)。OK が出たら board の status を `triage-done` に更新します。

### 過去ログの扱い
今日の active と今日の Triage board だけを常時参照します。過去日の board は読みません(古い判断事項を「今の判断」と誤認しないため)。過去ログが必要なら会話の中で Read します。

---

## Mode 3: Night Review(夜のレビュー)

**起動**: 種 `daily-pilot/night-review`(cron 22:30)。

### Step 1: 読み込み
- `active_tasks.md`(当日)
- `backlog.md`
- `archive.md`

### Step 2: 対象外セクションの除外
- `## スケジュール` / `## 本日の予定`(カレンダー由来) は [x]/[ ] 判定の対象外。active クリアでまとめて消えます。

### Step 3: `[x]`(完了)処理
- backlog から該当行を削除(マッチキー: `<!-- recur:{id}@{period_id} -->` マーカー優先、なければタスク名)
- archive に転記:
  - 月単位ヘッダ `## {today_month}` がなければ新設
  - 日単位ヘッダ `### {today_slash} (曜日)` を追記
  - `**Completed Tasks:**` セクションに **元の backlog 行を完全保持して転記**(recur マーカー・締切表記を保つ)

### Step 4: `[ ]`(持ち越し)処理 — 重要: active 編集の反映ロジック

a. backlog の対応行を特定(recur マーカー or タスク名)
b. **active 行の締切表記が backlog と異なれば backlog 側を更新**:
   - active から `(M/D締切...)` または `(MM/DD締切...)` を抽出
   - backlog 対応行も同様 → 比較
   - 差があれば backlog 側を active の値で **上書き**(deadline 部分のみ。recur マーカー・本文・カテゴリは保持)
   - `・暫定` が active で外れていれば backlog 側からも外す(確定扱い)
   - **判断知識**: ガクチョが active 上で締切を書き換えた = 既に判断済み。対話なしで信任して反映します
c. それ以外は backlog そのまま
d. archive `**Carried Over & Added:**` に記載(締切変更があれば `(旧M/D -> 新M/D)` で明示)

### Step 5: `## 追加` セクション処理(4分岐)
- `[x]` → archive `**Completed Tasks:**` に追記
- `[ ]` + 締切記述あり → backlog の適切カテゴリへ追記(deadline は記述を尊重)+ archive に `[🆕]` 付きで記録
- `[ ]` + 締切なし → **翌日デフォルト暫定締切** を付与 → backlog へ + archive に `[🆕]` 付き(`- [ ] **{タスク}** ({tomorrow_md}締切・暫定)`)
- 空行 → 何もしません

### Step 6: active クリア + 翌日テンプレ
- 1行目: `# Today's Tasks - {tomorrow_slash} (曜日)`
- 空セクション順序: `## スケジュール` / `## 運営・企画` / `## 管理事務` / `## 家のこと` / `## 追加`

### Step 7: 完了報告(夜の cheer は garden-gaku-co/night_cheer が担う、22:40)
集計: 完了 / 持ち越し / **締切更新** / 新規追加 / 期限超過(明日)

---

## Output Style(daily-pilot 固有部分)

CHARTER の Output Style 質感に従いつつ、daily-pilot 固有のセクション順を守ります:

### セクション順
`📅 予定` → `🚨 期限超過` → `📋 今日` → `🔖 判断ほしい`

### daily-pilot 用 良い締めの例
- 「カレンダーは終日北、期限超過が7件あります。移動と打合せを抜くと正味4時間です。Must Do は『戦略会議日程』と『月末連絡』。後者は下書きをこちらで作ります。残り5件は来週月曜送りでいかがですか?」
- 「期限超過で重いのは『とうぶんかいサイト修正』です。これだけで半日かかります。今日はこの1本に絞って、残りは Triage で動かしますか? 別の案もありますか?」

(共通の「悪い締めの例」「形式」は CHARTER 参照)

---

## Triage board のテンプレ

`garden/board/triage/{today}-morning-briefing.md`:

```markdown
---
type: pruning_request
from_seed: daily-pilot/morning-briefing
date: {today}
status: awaiting_triage | triage-done
created: {today}T06:30:00+09:00
triage_count: N
---

# {today_jp} {weekday_jp} 朝のブリーフィング

## 軸A: 過ごし方の提案

(横串で見た具体的な提案。選択肢 a/b/c を添えて庭師が選べるように)

## 軸B: AI 支援の提案

- [ ] 「{タスク}」 → {手伝える内容}
  - [ ] (a) Yes(やる)
  - [ ] (b) No(自分でやる)

## 軸C: 判断ほしい項目(該当時のみ)

- [ ] 「{タスク}」 → 暫定: {今日}
  - [ ] (a) 今日のまま
  - [ ] (b) 今週中(金曜まで)
  - [ ] (c) 自由記述: ____

## 庭師アクション
- Discord 短文返信(「A は a、B は b で」)or 本ファイル直接編集
```

---

## SKILL 内で確定済みの判断ルール(よくある分岐)

| 状況 | ルール |
|---|---|
| 暫定締切で `## 追加` に来たタスク | **翌日デフォルト**(営業日ロジックは使わない。埋もれ防止優先) |
| 「来週」「ASAP」等の自然言語期限 | Triage で数値化を質問してから backlog 反映 |
| active 上で締切を書き換えた | 夜の night-review で **backlog に反映**(対話なしで信任) |
| Triage が 0 件 | board は `status: confirmed` で生成(履歴のため)、口火は提案なしで簡潔に |
| カレンダー取得失敗 | `⚠️ カレンダー取得失敗` の1行で処理続行 |
| 過去日の triage board | 読まない(古い判断を今の判断と誤認しない) |

---

## このSKILLを参照する種・サービス

| 名前 | 役割 | SKILL の参照範囲 |
|---|---|---|
| `garden/seeds/daily-pilot/morning-briefing.md` | 06:30 cron | Mode 1 全体 + Output Style |
| `garden/seeds/daily-pilot/night-review.md` | 22:30 cron | Mode 3 全体 |
| `garden/seeds/daily-pilot/recurring-spawn.md` | 06:25 cron | (Mode 1 Step 1 の前準備、機械処理のみ・SKILL ロード不要) |
| `garden/seeds/daily-pilot/inbox-process.md` | 将来(watcher 待ち) | 将来追加: Mode 4 Inbox Processing |
| `garden/services/garden-gaku-co/bot.py` | Discord 常駐対話 | Mode 2 全体 + Output Style |
| `garden/services/garden-gaku-co/morning_greet.py` | 06:40 口火 | Mode 1 Step 4(Output Style 厳守) |
| `garden/services/garden-gaku-co/night_cheer.py` | 22:40 夜の cheer | Mode 3 Step 7 |

---

## 関連
- 共通規範: [garden/CHARTER.md](../../CHARTER.md)
- 起源: HMC `.agent/skills/hmc_pilot/SKILL.md`(Antigravity IDE 用、HMC 期の Vice Pilot)
- ADR セッション6: [デイリーワークフロー種化アーキテクチャ](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md)
- ADR セッション16: [garden-gaku-co を Garden の対話層に統合](../../../docs/decisions/2026-05-28-garden-gaku-co-interaction-layer.md)
- ADR セッション19: [種(seed) と SKILL の責務分離](../../../docs/decisions/2026-05-30-skill-and-seed-separation.md)
- ADR セッション20: [Garden CHARTER 導入とトーン統一](../../../docs/decisions/2026-05-30-garden-charter.md)
