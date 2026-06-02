---
type: seed
name: ingest-raw
plot: mycelium
description: master scope の対話 RAW を読み、三層分離 ADR §2 規約に従って soil / memory wiki / 廃棄 に振り分ける種(菌糸 Mode 1 / Stage A.5)
status: active                    # S26 dry-run 4 回完走 + 冪等性確認で active 化(2026-06-02)
phase: 4                          # Phase 4 = 区画の Garden 化(菌糸基盤)
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-05-31
created_by: claude (with ガクチョ, セッション23)
last_updated: 2026-05-31
linked_workflows: []
linked_skills:
  - "garden/mycelium/SKILL.md"
linked_services: []
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "30 3 * * *"          # 毎日 03:30 JST(夜間バッチ枠、index-refresh の 30 分後)
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
# 将来 claude-haiku-4-5 直接呼び出しに切替可能性あり(コスト最適化、Stage B でも同様)
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    yesterday: "$(date -d 'yesterday' +%Y-%m-%d)"
    fourteen_days_ago: "$(date -d '14 days ago' +%Y-%m-%d)"
  prompt: |
    あなたは菌糸(Mycelium)Mode 1 = Ingest の種「ingest-raw」です。

    まず以下 3 ファイルを Read で読み込み、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/mycelium/SKILL.md(菌糸 SKILL、Mode 1 を中心に)
      3. /home/vps-harappa/garden-mirror/garden/memory/README.md(三層分離の概要)

    その上で、SKILL の **"Mode 1: Ingest"** の全 Step(処理ステップ 1〜7)に従って、
    {today} の RAW ingest を実行します。

    今回の動的入力:
      - today: {today}
      - yesterday: {yesterday}
      - fourteen_days_ago: {fourteen_days_ago}

    操作対象:
      - 読み取り対象: /home/vps-harappa/garden-mirror/garden/memory/master/raw/{YYYY-MM-DD}.md で **以下を全て満たすもののみ**:
        - ファイル日付が yesterday 〜 fourteen_days_ago の範囲内(**today は対象外** — 当日 RAW は翌日 03:30 実行で処理する)
        - frontmatter `last_ingested_at` が **未設定**(設定済み = 処理完了とみなし、turn 単位の差分処理は行わない = RAW 単位の冪等保証)
      - 書き込み対象:
        - /home/vps-harappa/garden-mirror/garden/memory/master/wiki/{topic}.md(主題別)
        - /home/vps-harappa/garden-mirror/garden/memory/master/wiki/index.md(主題一覧)
        - /home/vps-harappa/garden-mirror/garden/soil/people/staff/{slug}.md の ## メモ セクション(短文事実)
        - /home/vps-harappa/garden-mirror/garden/soil/log.md(長文・経緯型)
        - /home/vps-harappa/garden-mirror/garden/memory/master/raw/{YYYY-MM-DD}.md の frontmatter `last_ingested_at`
      - log 出力: /home/vps-harappa/garden-mirror/garden/log/{today}-ingest-raw.log

    手順(SKILL Mode 1 処理ステップ 1〜7):

    1. **対象 RAW を列挙**: 前日 + 直近 14 日(yesterday → fourteen_days_ago)の RAW ファイル一覧を取得
       - **today(当日)の RAW は対象外**(翌日 03:30 実行で処理する)
       - 各ファイル frontmatter の `last_ingested_at` を確認
       - **未設定** のもののみ「未処理」とマーク(設定済みは全部 skip = RAW 単位の冪等保証)

    2. **未処理 RAW の全 turn 抽出**: マークされた RAW の全 turn を Read
       - 該当 RAW 0 件 → skip(log に「no unprocessed raw」)

    3. **LLM 振り分け**: 各 turn を SKILL Mode 1 振り分け規約に従って分類
       - 検証可能な短文事実 → soil/people/staff/{slug}.md の ## メモ(短文)
       - 長文・経緯型の事実 → soil/log.md
       - 判断・評価・意図 → memory/master/wiki/{topic}.md
       - 決定事項 → wiki + soil 両方
       - 予定 → soil events/projects + wiki 注記
       - グレー → 捨てる(何もしない、log にも残さない)

    4. **主題判定**: wiki 行きの場合、SKILL の事前定義主題リストから選ぶ
       - 該当なし → LLM が kebab-case で新規命名(例: `summer-camp-prep`)
       - 新規主題は memory/master/wiki/index.md に登録

    5. **書き込み**:
       - staff ページの ## メモ セクションに `- {date}: {事実}` 追記(セクションなければ新設)
       - wiki 主題ファイルに章立て追記(`### {date} - {一行サマリ}` で新章 + 本文)
       - soil/log.md に ingest 記録(長文の場合のみ、既存 ingest フォーマット)
       - 新規主題なら memory/master/wiki/index.md 更新

    6. **冪等保証**:
       - 処理した各 RAW ファイルの frontmatter に `last_ingested_at: {today}T03:30:00+09:00` を追加
       - 翌日以降の実行時、この RAW は全部 skip される(turn 単位の差分処理は行わない)
       - 当日 RAW で 03:30 以降に新しい turn が追加された場合は、翌日 03:30 実行で処理される(2 日待ち最大、リアルタイム反映より冪等性を優先)

    7. **log 記録**: 処理サマリを log に出力
       ```
       summary:
         raw_files_processed: N
         turns_processed: M
         soil_facts_added: K
         wiki_entries_added: L
         topics_new: [topic1, topic2]
         turns_discarded_grey: G
       ```

    べき等性:
      - **RAW 単位の処理完了マーカー** で冪等保証(`last_ingested_at` の有無のみで判定、turn 時刻比較はしない)
      - 同日 2 回走らせても処理済み RAW は全部 skip される
      - soil/log.md の冒頭 30 行に `[{today}] ingest-raw` エントリがあれば exit 0(guard、補助)

    失敗時:
      - 個別 turn の振り分け失敗 → その turn は skip(log 記録)、他は処理続行
      - 大規模変更(>50 turn)の場合 → 半分に分割して 2 回処理 or board 剪定依頼(Mode 2 連携)

    トーン:
      - log には簡潔に件数のみ
      - 振り分けの判断理由は記録しない(プライバシー + ログ肥大化防止)

# === ③ 結果をどこに置くか ===
outputs:
  - kind: file_update
    path: /home/vps-harappa/garden-mirror/garden/memory/master/wiki/*.md
  - kind: file_update
    path: /home/vps-harappa/garden-mirror/garden/memory/master/wiki/index.md
  - kind: file_update
    path: /home/vps-harappa/garden-mirror/garden/soil/people/staff/*.md
  - kind: log_append
    path: /home/vps-harappa/garden-mirror/garden/soil/log.md
  - kind: file_update
    path: /home/vps-harappa/garden-mirror/garden/memory/master/raw/*.md
  - kind: log
    path: /home/vps-harappa/garden-mirror/garden/log/{today}-ingest-raw.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: none                   # 自律実行(剪定不要)
  approver: null
  notify:
    via: mock
    group: null

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: none                       # 自律実行(承認なし)

# === ⑥ べき等性 ===
idempotency:
  key: ingest-raw-{today}
  guard: |
    各 RAW の frontmatter `last_ingested_at` で turn 単位の冪等保証。
    soil/log.md 冒頭 30 行に `[{today}] ingest-raw` あれば exit 0(同日 2 重実行防止)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: mock
    template: |
      ❌ mycelium/ingest-raw 失敗
      日付: {today}
      理由: {error_summary}
      詳細: {log_path}
      → 手動で memory/master/raw/{yesterday}.md を確認、必要なら SKILL Mode 1 を Read して手動振り分け

# === ⑧ 依存 ===
depends_on:
  workflow: null
  state:
    - "/home/vps-harappa/garden-mirror/garden/memory/master/raw/ が読み取り可能(bot.py + memory_logger.py で書き込み中)"
    - "/home/vps-harappa/garden-mirror/garden/memory/master/wiki/ が書き込み可能"
    - "/home/vps-harappa/garden-mirror/garden/soil/ が書き込み可能"
    - "/home/vps-harappa/garden/CHARTER.md / mycelium/SKILL.md が読み取り可能"
  seeds:
    - "mycelium/index-refresh(03:00、index は新規 wiki 主題追加を翌日反映)"

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null        # active 化時に設定
---

# mycelium/ingest-raw — 対話 RAW を意味的に振り分ける(Stage A.5)

## 目的(不変)

`memory/master/raw/` に蓄積された Discord 対話を **捨てずに整理して** Garden の知識に流入させる。事実は soil へ、判断は scope memory wiki へ、グレーは捨てる。庭師の暗黙知が漏れずに育つ。

## 現状の方法

frontmatter の `execute` を参照。要約:

1. cron 毎日 03:30 発火(index-refresh の 30 分後)
2. Garden CHARTER + 菌糸 SKILL Mode 1 + memory README を読み込んだ Claude Code が:
   a. 前日 + 直近 14 日の RAW から未処理 turn を抽出
   b. 各 turn を ADR §2 規約 + SKILL Mode 1 振り分け表に従って分類
   c. soil / memory wiki に書き込み + log 記録
   d. RAW frontmatter の last_ingested_at を更新
3. 異常時は on_failure(リトライ 2回 + log fallback)

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | claude-code engine 経由 | claude-haiku-4-5 直接呼び出しでコスト 1/10(gaku-co5.0 と同パターン)| 構想中 |
| ❓ | last_ingested_at が ISO8601 文字列(LLM 解釈) | turn 単位の UUID で確定的に追跡 | 構想中 |
| ❓ | 主題が事前定義 7 つ + 新規命名 | 運用 1〜2ヶ月後、命名揺れと類似マージの実態を見て見直し | Stage 2 Lint と連動 |
| 💡 | グレー判定で捨てたものは見えない | 「捨て率」が log に集計されれば傾向把握できる | 着手可能 |
| ❓ | RAW 14 日保持 → 削除は Stage B バッチ | 14 日経過した RAW を archive にするか純削除するか | Stage B 着手時 |
| ❓ | 振り分けプロンプトの安定性 | LLM の出力ばらつきは Stage A.5 dry-run で実観察してから調整 | 未検証 |

## 関連

- 区画 SKILL: [garden/mycelium/SKILL.md](../../mycelium/SKILL.md) Mode 1
- 入力: [garden/memory/master/raw/](../../memory/master/) — bot.py / memory_logger.py が書き込み
- 出力: [garden/memory/master/wiki/](../../memory/) / [garden/soil/](../../soil/)
- ADR(S20): [菌糸の役割と soil 参照規約](../../../docs/decisions/2026-05-30-mycelium-and-soil-reference.md)
- ADR(S22): [記憶の三層分離 + soil 振り分け規約](../../../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md)
- 関連種: `mycelium/index-refresh`(03:00、本種で新規 wiki 主題追加を翌日反映)
- 並行: `garden-gaku-co/memory_logger.py`(Stage A、RAW 書き込み層)

## TODO(本種に固有 = Stage A.5 実装作業)

- [ ] **VPS への配置**(`garden/seeds/mycelium/ingest-raw.md` を scp)
- [ ] **memory/master/wiki/ ディレクトリ作成 + index.md 雛形**
- [ ] **RAW frontmatter スキーマ更新**(`last_ingested_at` 追加、memory_logger.py 側で初期化)
- [ ] **dry-run 検証**(手動 RAW 編集 → 種実行 → wiki 反映確認)
- [ ] **cron 仕込み**(03:30 daily)
- [ ] **初稼働観察**(初週は捨て率・主題揺れを毎朝チェック)
- [ ] **改善余地: claude-haiku-4-5 直接呼び出し検討**(コスト最適化、Stage B で本格化)

## active 化条件(Stage A.5 完了条件)

1. [x] **SKILL Mode 1 詳細化**(本セッション、4 論点決定済)
2. [x] **種 skeleton 起草**(本セッション)
3. [ ] **memory_logger.py を `last_ingested_at` 対応に拡張**(次セッション、bot.py の RAW 書き込み層)
4. [ ] **memory/master/wiki/ ディレクトリ + index.md 雛形作成**
5. [ ] **dry-run 検証**(1 turn 手動編集 → 種実行 → 振り分け結果確認)
6. [ ] **cron 仕込み + 初週運用観察**
