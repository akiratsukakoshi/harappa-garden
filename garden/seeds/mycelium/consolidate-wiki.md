---
type: seed
name: consolidate-wiki
plot: mycelium
description: master memory wiki の index 再生成 + 重複/矛盾検出 + 14日経過 RAW を archive に移動する種(菌糸 Mode 5 / Stage B)
status: active                    # S30 起草・直 active(本文 append-only 厳格 + index 再生成 + archive 移動の組み合わせは破壊リスク低)
phase: 4                          # Phase 4 = 区画の Garden 化(菌糸基盤)
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-03
created_by: claude (with ガクチョ, セッション30)
last_updated: 2026-06-03
linked_workflows: []
linked_skills:
  - "garden/mycelium/SKILL.md"
linked_services: []
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "50 3 * * *"          # 毎日 03:50 JST(ingest-raw 03:30 の 20 分後)
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  model: claude-haiku-4-5         # コスト最適化(haiku 直接、launcher 1.0.1 で --model 対応)
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    fourteen_days_ago: "$(date -d '14 days ago' +%Y-%m-%d)"
    archive_month_dir: "$(date -d '14 days ago' +%Y-%m)"
  prompt: |
    あなたは菌糸(Mycelium)Mode 5 = Consolidate の種「consolidate-wiki」です。

    まず以下 3 ファイルを Read で読み込み、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/mycelium/SKILL.md(菌糸 SKILL、Mode 5 を中心に)
      3. /home/vps-harappa/garden-mirror/garden/memory/README.md(三層分離の概要)

    その上で、SKILL の **"Mode 5: Consolidate"** の全 Step(処理ステップ 1〜5)に従って、
    {today} の Consolidate を実行します。

    今回の動的入力:
      - today: {today}
      - fourteen_days_ago: {fourteen_days_ago}
      - archive_month_dir: {archive_month_dir}

    操作対象:
      - 読み取り対象:
        - /home/vps-harappa/garden-mirror/garden/memory/master/wiki/*.md(index.md と .gitkeep 以外)
        - /home/vps-harappa/garden-mirror/garden/memory/master/raw/ のファイル名一覧(YYYY-MM-DD.md)
      - 書き込み対象:
        - /home/vps-harappa/garden-mirror/garden/memory/master/wiki/index.md(再生成)
        - **本文の wiki/{topic}.md は触らない**(append-only 厳格)
      - 移動対象:
        - /home/vps-harappa/garden-mirror/garden/memory/master/raw/{YYYY-MM-DD}.md(date < fourteen_days_ago)
        - → /home/vps-harappa/garden-mirror/garden/memory/master/raw/archive/{YYYY-MM}/{YYYY-MM-DD}.md
      - log 出力: /home/vps-harappa/garden/log/{today}-consolidate-wiki.log

    手順(SKILL Mode 5 処理ステップ 1〜5):

    1. **wiki 走査**: memory/master/wiki/*.md を Glob で列挙(index.md と .gitkeep 除外)
       - 0 件 → skip(log に「no wiki pages」)
       - 各ページを Read し、frontmatter の `last_updated` と `### YYYY-MM-DD - {サマリ}` 章の数・最終章の一行サマリを抽出

    2. **index.md 再生成**:
       - 既存 index.md の構造(事前定義 7 主題 + 新規追加セクション)を保つ
       - 事前定義 7 主題テーブルの「ページ」列を最新化:
         - 該当ページが存在 → `[topic.md](topic.md)` + 「最終更新」「章数」を別カラムに
         - 該当ページが未生成 → `(未生成)`
       - 新規追加セクションを最新化:
         - wiki/ 内に存在するが事前定義 7 主題に該当しない主題ページを列挙
       - **frontmatter の last_updated を {today} に、last_updated_by を 'mycelium (Mode 5 consolidate-wiki, {today})' に更新**

    3. **append-only 厳格チェック**(本文編集なし、検出のみ):
       - 各 wiki ページ内で、同じ事実が複数章に出現していないかを LLM 判断で確認
       - 古い章と新章で事実が衝突していないかを確認(例: 「Aさんは運営」→ 後の章で「Aさんはフィールド」)
       - **本文は一切触らない**(履歴保全 = 庭師の判断ログとして使う)
       - 検出した重複・矛盾は log に書き出すだけ

    4. **14 日経過 RAW を archive**:
       - Bash で `ls /home/vps-harappa/garden-mirror/garden/memory/master/raw/*.md 2>/dev/null` で raw 直下を列挙(archive/ サブディレクトリは対象外、`raw/archive/` の中身は再帰しない)
       - 各ファイル名 `YYYY-MM-DD.md` から日付を抽出
       - **date < {fourteen_days_ago}** のものを抽出(<= ではなく <、=境界は今日の対象内に残す)
       - 対象 0 件 → skip(log に「no raw to archive」)
       - 1 件以上 → 以下を Bash で実行:
         ```
         mkdir -p /home/vps-harappa/garden-mirror/garden/memory/master/raw/archive/{YYYY-MM}/
         mv /home/vps-harappa/garden-mirror/garden/memory/master/raw/{date}.md /home/vps-harappa/garden-mirror/garden/memory/master/raw/archive/{YYYY-MM}/{date}.md
         ```
       - {YYYY-MM} は対象ファイルの date の年月(例: 2026-05-15.md → archive/2026-05/)

    5. **log 記録**: 処理サマリを log に出力
       ```
       summary:
         wiki_pages: N
         index_regenerated: true/false
         duplicates_detected: D
         contradictions_detected: C
         raw_archived: K
         archive_dirs: [archive/2026-05/, ...]
       ==NOTIFY==
       菌糸 Mode 5 Consolidate 完了 ({today}):
       - wiki: N ページ、index 再生成 {true/false}
       - 重複検出: D、矛盾検出: C(Mode 2 Lint 候補なら明示)
       - RAW archive: K 件 → {archive_dirs}
       ```

    べき等性:
      - index.md 再生成は wiki 内容に対して冪等(同じ入力 → 同じ出力)
      - 14 日経過 RAW archive は move 済みファイルが対象外で自然冪等
      - log 末尾(直近 20 行)に `[{today}] consolidate-wiki` がすでにあれば exit 0(guard)

    失敗時:
      - wiki 読み取り失敗 → log 記録、archive は skip(順序保証)
      - index.md 書き込み失敗 → log 記録、archive は skip
      - archive 移動失敗(個別ファイル) → log 記録、他のファイルは続行
      - 全体失敗 → ==NOTIFY== ブロックに ❌ で記録

    トーン:
      - log は簡潔に件数のみ
      - 重複・矛盾の内容詳細は Mode 2 Lint で扱うため、ここでは件数だけ
      - index.md の表は意味的サマリ(機械的列挙でなく、主題スラグ・概要・page link・最終更新・章数を意味のある単位で示す)

    重要:
      - **本文の wiki/{topic}.md は絶対に編集しない**(append-only 厳格、Garden の memory wiki は判断履歴)
      - index.md だけ書き換える + raw archive 移動するだけ

# === ③ 結果をどこに置くか ===
outputs:
  - kind: file_update
    path: /home/vps-harappa/garden-mirror/garden/memory/master/wiki/index.md
  - kind: file_move
    from: /home/vps-harappa/garden-mirror/garden/memory/master/raw/*.md
    to: /home/vps-harappa/garden-mirror/garden/memory/master/raw/archive/{YYYY-MM}/*.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-consolidate-wiki.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: none                   # 自律実行(剪定不要)
  approver: null
  notify:
    via: mock                     # log 末尾の ==NOTIFY== ブロック
    group: null

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: none                       # 自律実行(承認なし)

# === ⑥ べき等性 ===
idempotency:
  key: consolidate-wiki-{today}
  guard: |
    log 末尾(直近 20 行)に `[{today}] consolidate-wiki` があれば exit 0。
    index 再生成は冪等。14 日経過 archive は move 済みで自然冪等。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 1h
  fallback:
    via: mock
    template: |
      ❌ mycelium/consolidate-wiki 失敗
      日付: {today}
      理由: {error_summary}
      詳細: {log_path}
      → 手動で memory/master/wiki/index.md を確認、必要なら SKILL Mode 5 を Read して手動再生成

# === ⑧ 依存 ===
depends_on:
  workflow: null
  state:
    - "/home/vps-harappa/garden-mirror/garden/memory/master/wiki/ が読み書き可能"
    - "/home/vps-harappa/garden-mirror/garden/memory/master/raw/ が読み書き可能(archive サブディレクトリ作成含む)"
    - "/home/vps-harappa/garden/CHARTER.md / mycelium/SKILL.md / memory/README.md が読み取り可能"
    - "launcher 1.0.1 以上(execute.model サポート)"
  seeds:
    - "mycelium/ingest-raw(03:30、本種は ingest 完了後に index と archive を更新)"

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null        # active 化時に設定
---

# mycelium/consolidate-wiki — wiki index 再生成 + 重複/矛盾検出 + 14日 RAW archive(Stage B)

## 目的(不変)

Mode 1 Ingest が **append-only** で動く結果、wiki ページが時系列ノートの山になる。Mode 5 Consolidate は (1) index.md を意味的サマリで再生成、(2) 重複・矛盾を検出ログ化(本文編集なし)、(3) 14 日経過 RAW を archive に退避 — の 3 つを 1 リクエストでこなす。本文は触らないので、ガクチョの判断履歴が壊れない。

## 現状の方法

frontmatter の `execute` を参照。要約:

1. cron 毎日 03:50 発火(ingest-raw 03:30 の 20 分後)
2. Garden CHARTER + 菌糸 SKILL Mode 5 + memory README を読み込んだ Claude Code(haiku-4-5)が:
   a. wiki/*.md を全 Read(index.md / .gitkeep 除外)
   b. index.md を意味的サマリで再生成(本文 wiki ページは触らない)
   c. 重複・矛盾を LLM 判断で検出 → log 記録のみ
   d. 14 日経過 RAW を `raw/archive/{YYYY-MM}/` に move
3. 異常時は on_failure(リトライ 1 回 + log fallback)

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 全 wiki ページを毎晩全 Read | 直近 N 日に追記があった wiki だけ対象にする差分方式 | 構想中(初週運用後判断) |
| ❓ | 重複・矛盾検出は log 記録のみ | Mode 2 Lint で本文整理 / board 剪定依頼に昇格 | Stage 2 で本格化 |
| ❓ | archive は月ディレクトリで集約 | 量が増えたら年ディレクトリで再集約 / kura に移送 | 長期運用後 |
| 💡 | index.md の構造が硬直 | 主題のカテゴリ分け(staff 系 / event 系 / infra 系)を意味的グルーピング | 着手可能 |
| ❓ | 振る舞いは LLM 判断に依存 | 重複検出を機械的(diff ベース)に切り替えるとコスト ↓ | 構想中 |

## 関連

- 区画 SKILL: [garden/mycelium/SKILL.md](../../mycelium/SKILL.md) Mode 5
- 入力: [garden/memory/master/wiki/](../../memory/master/) — ingest-raw が書き込み
- 出力: [garden/memory/master/wiki/index.md](../../memory/) / [garden/memory/master/raw/archive/](../../memory/master/)
- ADR(S22): [記憶の三層分離 + soil 振り分け規約](../../../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md)
- ADR(S29): [memory 正本ルール](../../../docs/decisions/2026-06-03-memory-source-of-truth.md)
- 関連種: `mycelium/ingest-raw`(03:30、本種は ingest 完了後に index と archive を更新)
- 並行: `mycelium/index-refresh`(03:00、soil/index.md の方を扱う別 index)

## active 化条件(Stage B 完了条件)

1. [x] **SKILL Mode 5 詳細化**(本セッション、S30)
2. [x] **launcher.mjs に model パラメータ対応**(S30 = 1.0.0 → 1.0.1)
3. [x] **種起草**(本セッション、S30)
4. [ ] **VPS 配置**(`/home/vps-harappa/garden/seeds/mycelium/consolidate-wiki.md` + launcher 反映)
5. [ ] **dry-run 検証**(launcher --dry-run で prompt 確認 + 実走で index 再生成と archive 動作確認)
6. [ ] **crontab 仕込み**(50 3 * * * daily)
7. [ ] **初週運用観察**(初週は重複・矛盾検出 + archive 件数を毎朝チェック)
