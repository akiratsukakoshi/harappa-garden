---
name: mycelium
description: 土壌維持エージェント(菌糸)。soil の Ingest / Lint / Index 更新 / 関係性編み直しの 4 Mode を担う。bot から呼ばれる業務 plot ではなく、種(cron)から呼ばれる基盤 SKILL。
type: mycelium
inherits_from:
  - garden/CHARTER.md
requires_soil_index: false
created: 2026-05-31
last_updated: 2026-05-31
created_by: claude (with ガクチョ, セッション23)
linked_seeds:
  - mycelium/index-refresh        # Stage 1(S23 起草、S23 active)
  - mycelium/ingest-raw           # Stage A.5(S23 skeleton、S26 active)
  - mycelium/consolidate-wiki     # Stage B(S30 起草・active)
linked_services: []
linked_soil:
  - soil/index.md                 # 維持対象
  - soil/log.md                   # 編集ログ追記先
---

# mycelium — 土壌維持エージェント

> 土の中で網目状に広がり、栄養を分解して各ページに運ぶ存在。見えないが土壌の健全性を支える基盤。

mycelium は業務 plot ではなく、Garden の **基盤 SKILL** です。庭師が直接呼ぶことはほぼなく、種(cron)や他の plot から間接的に駆動されます。

> 共通の業務観・呼称・トーン・Output Style 質感は [garden/CHARTER.md](../CHARTER.md) を参照。本 SKILL は mycelium 固有の責務・手順・判断ルールに集中します。

---

## 位置づけ

Garden 語彙 ([docs/garden-vocabulary.md](../../docs/garden-vocabulary.md)) における役割:

| 役割 | 担当 |
|---|---|
| 庭師(Gardener) | 意志・決定・最終承認・剪定 |
| 番人(Watcher) | 監視・告げる(見て報告) |
| **菌糸(Mycelium)** ← 本 SKILL | **分解・運搬・integrate・index 更新・関係性編み直し** |
| 草木 / 木の精 | 対話(ガクコ等) |

番人と菌糸の違い:番人は「見て告げる」、菌糸は「分解して運ぶ」。責務が違うため独立カテゴリ。

---

## SSOT(本 SKILL の正本)

- [garden/soil/index.md](../soil/index.md) = **土壌の地図の正本**(菌糸が常に最新化)
- [garden/soil/log.md](../soil/log.md) = **編集ログの正本**(追記専用、菌糸の動作も記録)
- 各 soil ファイル自体の正本性は各カテゴリ(`people/staff/README.md` 等)が定義。菌糸はそれらの **集約面** = index と log を維持

---

## ファイルと役割

| ファイル | 役割 | 編集方向 |
|---|---|---|
| `garden/soil/index.md` | 土壌の地図(意味的サマリ) | 菌糸 Mode 3 が更新 / 庭師が直接編集も可 |
| `garden/soil/log.md` | 編集ログ(追記専用) | 菌糸の各 Mode が動作記録 / Ingest 結果記録 |
| `garden/memory/master/wiki/index.md` | master memory wiki の主題一覧 | 菌糸 Mode 1 (Stage A.5) が更新 |
| `garden/memory/master/wiki/{topic}.md` | master memory wiki の主題別ページ | 菌糸 Mode 1 (Stage A.5) が新設・追記 |
| `garden/memory/master/raw/{YYYY-MM-DD}.md` | Discord master 対話の生ログ(機密) | bot.py / memory_logger.py が append、菌糸 Mode 1 が読む |
| `garden/services/garden-gaku-co/memory_logger.py` | RAW 書き込み層 | 菌糸の入口 = ここに溜まった RAW を Mode 1 が引き取る |

---

## Mode 3: Index 更新(Stage 1 = 現セッション稼働)

**起動**: 種 `mycelium/index-refresh`(cron 日次 03:00 想定)。将来 watcher daemon 化候補。

### 目的
soil/ 配下が編集されたら、`soil/index.md`(土壌の地図)を **意味的に** 最新化します。機械的なファイル一覧化ではなく、LLM が読んで「staff 29 名(運営4 / フィールド20 / 写真5)」のような意味的分類サマリを作るのが本責務(Karpathy LLM Wiki 哲学)。

### Step 1: 過去24時間の編集を検知
```bash
# 最終更新が直近 24h 以内のファイルを列挙(index.md / log.md は自己ループ防止のため除外)
find /home/vps-harappa/garden-mirror/garden/soil -type f -name "*.md" -mtime -1 \
  -not -name "index.md" -not -name "log.md" -not -path "*/.*"
```
- 0 件 → log に skip 記録して exit 0
- 1 件以上 → Step 2 へ

### Step 2: 編集差分を読む
- 検知された各ファイルを Read
- 変更内容を把握(新規追加 / 内容更新 / メタ情報の変化など)

### Step 3: index.md を意味的に更新
- 現状の `soil/index.md` を Read
- 検知した変更を **意味的に反映** して書き換える:
  - staff 増減 → カテゴリ集計(運営 N / フィールド N / 写真 N / 調理 N)を更新
  - business 配下の追加 → 該当カテゴリ表を更新
  - 新カテゴリ(events / clients 等)の中身が育ったら「未着手」マーカーを外す
  - 個別 staff / business の追加・削除は要点だけ反映(全件列挙はしない)
- LLM の解釈で「変えないほうがよい」と判断した部分は触らない(Pattern A)

### Step 4: log.md に追記
```markdown
## [YYYY-MM-DD] index-refresh | 検知 N 件
- by: mycelium (Stage 1)
- type: index
- pages: index.md
- summary: {何が変わったかの一行要約}
- detected: {検知された変更ファイル一覧}
```

### Step 5: 完了通知
- log の末尾に `==NOTIFY==` ブロック(モック)
- 当面 Discord master 通知は **しない**(夜間バッチで毎日 1 回流れると過剰)
- 庭師が朝 `index.md` を見れば最新化されている、という運用

### 判断ルール

| 状況 | ルール |
|---|---|
| 検知 0 件 | skip(log に「no changes」だけ記録) |
| 大規模変更(>20 ファイル) | 一気に書き換えず「初回 full scan が必要」と判定 → board に剪定依頼を立てて庭師に full scan 起動を依頼 |
| index.md の構造変更が必要 | 自動では実施しない。board に提案を立てて庭師承認待ち |
| LLM の解釈に迷う変更 | index は触らず log にだけ記録、次回再判定 |

### 初回 full scan(Stage 1 立ち上げの一回キリ)
**人間(Claude 対話セッション中)が手動で実施**。soil/ の全ファイルを読み、index.md を意味的に書き直す。

log.md の type は **`index-bootstrap`** とする(`index-refresh` と区別。種の guard で誤 skip されないため)。

実施記録:

- **2026-05-31 セッション23** で初回実施(staff 29名 + business 21ファイル + workflows 4本 + concepts 1件)

---

## Mode 1: Ingest(Stage A.5 = 次セッション実装)

**起動**: 種 `mycelium/ingest-raw`(cron 日次 03:30 想定、夜間バッチ枠、index-refresh の 30 分後)。

### 目的
`garden/memory/master/raw/` に蓄積された対話 RAW を読み、[記憶三層分離 ADR §2 規約](../../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md) に従って soil / memory wiki / 廃棄 に振り分けます。

### 振り分け規約(ADR §2 抜粋 + セッション23 決定事項)

| 抽出内容 | 出力先 | 形式 |
|---|---|---|
| **検証可能な短文事実**(誰・いつ・何・どう) | **soil の該当ファイル**(staff / events / business 等) | エンティティページの `## メモ` セクションに `- YYYY-MM-DD: {事実}` で1行追記 |
| **長文・経緯型の事実 / ログ的なもの** | **soil/log.md** | 既存ログ規約(`## [YYYY-MM-DD] ingest \| title` + 5 行) |
| **判断・評価・意図**(主観的) | **scope memory wiki**(該当 scope ローカル) | 主題別ファイル `wiki/{topic}.md` に追記 |
| **決定事項**(具体的に動く) | **scope memory wiki** + **soil**(該当対象あれば) | 両方に書き、相互参照 |
| **予定**(未来の事実) | **soil**(events / projects)+ scope memory(注記) | event ページ + master memory にも一言 |
| **グレーな約束 / 文脈ノイズ** | **捨てる**(ADR §2 庭師方針) | log にも残さない(雑談肥大化防止) |

### 4 論点の決定(セッション23 庭師合意)

#### 論点 1: 抽出粒度 = ハイブリッド(短文事実 → staff ページ / ログ的 → log.md)
- staff ページの `## メモ` セクションに **検証可能な短文事実** を時系列追記(date 付き)
- 経緯型・複文 → soil/log.md(既存 ingest 規約に従う)
- staff ページが肥大化したら Mode 2 (Lint, Stage 2) で「古いメモを archive 化しますか?」と剪定提案

#### 論点 2: 主題判定 = ハイブリッド(事前定義 + 該当なしで新規 LLM 命名)
- 事前定義主題リスト(本 SKILL の末尾「主題候補」表で管理):
  - `staff_assignment` — スタッフの役割・配置・契約
  - `event_planning` — イベント企画・調整
  - `business_strategy` — 事業方針・サービス改廃
  - `client_relations` — クライアント・パートナー関係
  - `tech_infra` — Garden / VPS / インフラ
  - `personal_reflection` — 庭師個人の振り返り・気持ち
  - `daily_operation` — 日々の運営調整
- 上記に該当しない時のみ LLM が新規命名(kebab-case、`memory/master/wiki/index.md` で主題一覧管理)
- 新規命名は菌糸 Mode 2 (Lint) で類似主題のマージ提案を将来追加

#### 論点 3: 冪等 = RAW 単位 `last_ingested_at` + wiki append-only
- 各 RAW ファイル(`memory/master/raw/{YYYY-MM-DD}.md`)の frontmatter に `last_ingested_at: <ISO8601>` を追加
- 種実行時は `last_ingested_at` 以降に追加された turn のみ処理
- wiki 側の重複(同じ事実の再追記)は **許容**(append-only、履歴として価値)
- 重複の整理は菌糸 Mode 2 (Lint) で後処理

#### 論点 4: 失敗時 = ADR §2 「グレーは捨てる」を厳格適用
- LLM が振り分け判断つかない発話 → **何もしない**(log にも残さない)
- 雑談・あいさつ・「あー」「えーと」などのフィラーは無視
- 「保留 box」「_pending/」は作らない(肥大化リスク回避)
- 将来 Lint(Stage 2)で「捨て率が高すぎる」傾向検出時に再検討

### モデルと環境
- LLM: `claude-haiku-4-5`(コスト優先、gaku-co5.0 と同じ判断)
- 入力: 前日分の `memory/master/raw/{YYYY-MM-DD}.md` の `last_ingested_at` 以降
- 出力先: 上記振り分け表通り

### 出力先(Stage A.5 で稼働)
- `garden/memory/master/wiki/{topic}.md`(主題別 wiki ページ)
- `garden/memory/master/wiki/index.md`(主題一覧、菌糸 Mode 1 が更新)
- `garden/soil/people/staff/{slug}.md` の `## メモ` セクション(短文事実)
- `garden/soil/log.md`(長文・経緯型)
- `garden/memory/master/raw/{YYYY-MM-DD}.md` の frontmatter `last_ingested_at` 更新

### 処理ステップ(skeleton)

1. **対象 RAW を列挙**: 前日 + 直近 14 日の `memory/master/raw/*.md` で `last_ingested_at` が未設定 or turn の最終時刻より古いもの
2. **未処理 turn 抽出**: 各 RAW ファイルから `last_ingested_at` 以降の turn を Read
3. **LLM 振り分け**(haiku-4-5): 各 turn を読み、振り分け規約に従って分類(soil 該当 / wiki 該当 / 両方 / 捨てる)
4. **主題判定**: wiki 行きの場合、事前定義リストまたは新規命名
5. **書き込み**:
   - staff ページの `## メモ` セクションに `- YYYY-MM-DD: {事実}` 追記
   - wiki 主題ファイルに章立て追記
   - soil/log.md に ingest 記録(長文の場合)
   - 新規主題なら `memory/master/wiki/index.md` 更新
6. **冪等保証**: RAW frontmatter の `last_ingested_at` を処理時刻に更新
7. **log 記録**: 処理サマリ + `==NOTIFY==` ブロックを **stdout に出力**(launcher が stdout を `garden/log/{today}-ingest-raw.log` に capture する。**Write ツールで log を直接書かない** — cwd サンドボックス外なので弾かれる)

### 主題候補(事前定義リスト)

| 主題スラグ | 概要 |
|---|---|
| `staff_assignment` | スタッフの役割・配置・契約 |
| `event_planning` | イベント企画・調整 |
| `business_strategy` | 事業方針・サービス改廃 |
| `client_relations` | クライアント・パートナー関係 |
| `tech_infra` | Garden / VPS / インフラ |
| `personal_reflection` | 庭師個人の振り返り・気持ち |
| `daily_operation` | 日々の運営調整 |

新規追加は LLM 自動命名 → menyrium が `memory/master/wiki/index.md` に登録 → SKILL の本表にも将来追記(Mode 2 Lint で類似マージ提案)。

---

## Mode 5: Consolidate(Stage B = 本セッション S30 で active)

**起動**: 種 `mycelium/consolidate-wiki`(cron 日次 03:50 想定、ingest-raw の 20 分後)。

### 目的

Mode 1 Ingest は **append-only** で動く(同じ事実の再追記を許容)。その代償として wiki ページが時系列ノートの山になりやすい。Mode 5 は以下 3 つを 1 リクエストでこなす:

1. **index.md の再生成**:wiki ディレクトリ内の `*.md` を走査し、各ページの **最終 last_updated** + **総章数** + **直近1章の一行サマリ** を index 表に反映
2. **append-only 厳格チェック**:本文の章は **触らない**(履歴保全 = ガクチョの判断ログとして使う)。重複・矛盾は検出だけして log に記録、本文編集はしない
3. **14 日経過 RAW を archive**:`memory/master/raw/{date}.md` のうち、`date < today - 14日` のものを `memory/master/raw/archive/{YYYY-MM}/{date}.md` に move(純削除しない、復旧経路を残す)

> **Karpathy LLM Wiki との違い**:Karpathy の原案は LLM が本文を直接編集 / 上書きする。Garden の memory wiki は **庭師の判断履歴** なので本文 append-only を厳格化し、整理は index と log だけで行う(2026-06-03 S30 庭師合意)。

### モデルと環境

- LLM: `claude-haiku-4-5`(launcher の `execute.model` で指定)
- engine: `claude-code`(他の種と同じ、subscription auth 流用)
- 入力: `memory/master/wiki/*.md`(全主題ページ)+ `memory/master/raw/` のファイル名一覧
- 出力: `memory/master/wiki/index.md` の再生成 + log 記録 + 14 日経過 RAW の archive

### 処理ステップ

1. **wiki 走査**: `memory/master/wiki/*.md`(index.md と .gitkeep 以外)を全 Read
2. **index.md 再生成**:
   - 各ページの frontmatter `last_updated` と `## ###` 章数を集計
   - 直近章の `### YYYY-MM-DD - {サマリ}` の一行を抜く
   - 事前定義 7 主題 + 新規主題(運用追加)を表で並べる(該当ページがあれば `[topic.md](topic.md)`、なければ「(未生成)」)
   - 既存 index.md の構造を保ち、表の本文だけ最新化
3. **append-only 厳格チェック**(本文編集なし、検出のみ):
   - 重複(同じ事実が複数章にある)→ log に記録
   - 矛盾(古い章と新章で事実が衝突)→ log に記録
   - 本文は **触らない**
4. **14 日経過 RAW を archive**:
   - `raw/` 直下の `YYYY-MM-DD.md` を列挙
   - `date < today - 14日` のものを `raw/archive/{YYYY-MM}/{date}.md` に move(`mkdir -p` で月ディレクトリ作成)
   - move 後の log 記録(件数のみ)
5. **log 記録**: `garden/log/{today}-consolidate-wiki.log` に処理サマリ
   ```
   summary:
     wiki_pages: N
     index_regenerated: true/false
     duplicates_detected: D
     contradictions_detected: C
     raw_archived: K
     archive_dir: memory/master/raw/archive/{YYYY-MM}/
   ```

### べき等性

- index.md 再生成は冪等(同じ wiki 内容なら同じ出力)
- 14 日経過 RAW archive は移動済みファイルが対象外なので自然冪等
- log 末尾に `[{today}] consolidate-wiki` の guard チェック → 既存なら exit 0

### 失敗時

- index.md 生成失敗 → log 記録、archive は skip(順序保証)
- archive 移動失敗 → log 記録、次回再試行(冪等)

### 判断ルール

| 状況 | ルール |
|---|---|
| wiki ファイル 0 件 | skip(log に「no wiki pages」) |
| index.md が存在しない | テンプレから新規生成 |
| 重複検出 0 件・矛盾 0 件 | log に「clean」とだけ記録 |
| 重複・矛盾が **大量**(> 20 件) | log に列挙 + 「Lint(Mode 2)候補」とマーク(本文整理は Mode 2 Lint で別途) |
| archive 対象 0 件 | skip(初週・運用初期は正常) |

### Output Style(Mode 5 固有)

- index.md の表は **意味的サマリ**(機械的列挙でなく、主題スラグ・概要・page link・最終更新・章数を意味のある単位で示す)
- log は簡潔に件数のみ。重複の内容詳細は Mode 2 Lint で扱う

---

## Mode 2: Lint(Stage 2 = shift_manager 安定後)

**起動**: 種 `mycelium/lint-weekly`(cron 週次、月曜 03:00 想定)。

### 概要
- 矛盾検出(soil 内の事実の衝突)
- 古い記述検出(`last_updated` 古いページ)
- 孤立ページ検出(`[[link]]` 被リンク 0)
- 欠損リンク検出(`[[link]]` 先がない)
- 創発ログ review(`garden/board/emergence/` の繰り返しパターン → SKILL 書き戻し候補として庭師に剪定依頼)

詳細は Stage 2 着手時に書き起こします。

---

## Mode 4: 関係性編み直し(Stage 4 = 運用成熟後)

**起動**: 種 `mycelium/relations-monthly`(cron 月次 1日 03:00 想定)。

### 概要
- 各 soil ファイルの `linked_*` frontmatter を実体に合わせて再構築
- 本文中の `[[link]]` 漏れを検出して追記提案
- Mode 1 / Mode 3 から呼ばれる場合もある

詳細は Stage 4 着手時に書き起こします。

---

## Output Style(mycelium 固有部分)

mycelium はガクチョと直接対話する SKILL ではない(seed 経由・log 経由が主)ため、Output Style の優先度は低いです。ただし以下を守ります:

- log.md への追記は **追記専用フォーマット**(soil/README.md の規約に従う)
- 庭師通知(将来 Discord master)が必要な場合のみ、CHARTER の Output Style に従う
- index.md の更新は **意味的サマリ重視**(機械的列挙ではなく、カテゴリと数を意味のある単位で示す)

---

## SKILL 内で確定済みの判断ルール

| 状況 | ルール |
|---|---|
| soil ファイル変更検知 0 件 | skip(log に 1 行だけ) |
| 大規模変更(>20 ファイル) | 自動更新せず board に剪定依頼 |
| index.md の構造変更が必要 | 自動では実施しない、庭師承認待ち |
| Stage A.5 で LLM が判断つかない発話 | 廃棄せず保留(具体仕様は設計議論で確定) |
| 同じ RAW の再処理 | `last_ingested_at` で冪等保証(Stage A.5 仕様) |
| index.md と log.md の更新は **同一トランザクション** | log だけ更新して index が古いまま、を作らない |

---

## このSKILLを参照する種・サービス

| 名前 | 役割 | SKILL の参照範囲 |
|---|---|---|
| `garden/seeds/mycelium/index-refresh.md` | 日次 03:00 cron(Stage 1) | Mode 3 全体 |
| `garden/seeds/mycelium/ingest-raw.md` | 日次 03:30 cron(Stage A.5、S26 active) | Mode 1 全体 |
| `garden/seeds/mycelium/consolidate-wiki.md` | 日次 03:50 cron(Stage B、S30 active) | Mode 5 全体 |
| `garden/seeds/mycelium/lint-weekly.md` | 週次 cron(Stage 2、未起草) | Mode 2 全体 |
| `garden/seeds/mycelium/relations-monthly.md` | 月次 cron(Stage 4、未起草) | Mode 4 全体 |

---

## 関連

- 共通規範: [garden/CHARTER.md](../CHARTER.md)
- 土壌: [garden/soil/](../soil/) — 被維持対象
- 土壌 README: [garden/soil/README.md](../soil/README.md) — 3責務(Ingest / Query / Lint)の元定義
- 記憶: [garden/memory/](../memory/) — Mode 1 の出力先(scope memory wiki)
- ADR(S20): [菌糸(Mycelium) の役割と soil 参照規約](../../docs/decisions/2026-05-30-mycelium-and-soil-reference.md)
- ADR(S22): [記憶の三層分離 + soil 振り分け規約](../../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md)
- 哲学: Karpathy の LLM Wiki — https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
