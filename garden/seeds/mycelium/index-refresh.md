---
type: seed
name: index-refresh
plot: mycelium
description: soil/ 配下の過去24時間の編集を検知し、soil/index.md を意味的に最新化する種(菌糸 Mode 3 / Stage 1)
status: draft                     # cron 仕込み + dry-run 検証で active へ
phase: 4                          # Phase 4 = 区画の Garden 化(菌糸基盤)
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-05-31
created_by: claude (with ガクチョ, セッション23)
last_updated: 2026-05-31
linked_workflows: []              # 業務 workflow ではなく Garden 基盤
linked_skills:
  - "garden/mycelium/SKILL.md"
linked_services: []
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 3 * * *"           # 毎日 03:00 JST(夜間バッチ枠)
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    yesterday: "$(date -d 'yesterday' +%Y-%m-%d)"
  prompt: |
    あなたは菌糸(Mycelium)Mode 3 = Index 更新の種「index-refresh」です。

    まず以下2ファイルを Read で読み込み、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/mycelium/SKILL.md(菌糸 SKILL、Mode 3 を中心に)

    その上で、SKILL の **"Mode 3: Index 更新"** の全 Step(Step 1〜5)に従って、
    {today} の index-refresh を実行します。

    今回の動的入力:
      - today: {today}
      - yesterday: {yesterday}

    操作対象:
      - 検知対象: /home/vps-harappa/garden-mirror/garden/soil/ 配下の *.md(過去 24h で mtime 変化したもの)
      - 更新対象: /home/vps-harappa/garden-mirror/garden/soil/index.md
      - 追記対象: /home/vps-harappa/garden-mirror/garden/soil/log.md
      - log 出力: /home/vps-harappa/garden-mirror/garden/log/{today}-index-refresh.log

    手順(SKILL Mode 3 Step 1〜5):

    1. **検知**: 以下コマンドで過去 24h 編集されたファイルを列挙(index.md / log.md は自己ループ防止のため除外)
       ```
       find /home/vps-harappa/garden-mirror/garden/soil -type f -name "*.md" -mtime -1 \
         -not -name "index.md" -not -name "log.md" -not -path "*/.*"
       ```
       - 0 件 → log に「no changes detected」と1行書いて exit 0(soil/log.md は触らない)
       - 1 件以上 → Step 2 へ

    2. **差分把握**: 検知された各ファイルを Read
       - 新規追加か / 既存編集か(git で確認できれば優先、なければ mtime のみ判定)
       - 何が変わったか(staff の追加・削除・role 変更 / business の追加 / 等)を要約

    3. **index.md を意味的に更新**:
       - 現状の `soil/index.md` を Read
       - 検知変更を **意味的に反映** して書き換える:
         - staff 追加/削除 → contract / role / area の集計セクション数値を更新
         - business 追加 → toC / toB / communication の表に追記
         - workflows 追加 → 4本表に追記
         - 個別 staff / business の追加・削除は要点のみ反映(全件列挙はしない)
       - LLM の解釈で「変えないほうがよい」と判断した部分は触らない(Pattern A)
       - 大規模変更(>20 ファイル)を検知した場合は、index は触らず log に「manual full scan needed」と書いて exit 0

    4. **soil/log.md に追記**(追記専用、既存内容は触らない):
       ```markdown
       ## [{today}] index-refresh | 検知 N 件
       - by: mycelium (Stage 1)
       - type: index
       - pages: index.md
       - summary: {一行要約}
       - detected: {検知ファイル一覧 or 「staff 1, business 0, workflows 0, concepts 0」のような数値要約}
       ```

    5. **完了**:
       - log({today}-index-refresh.log)末尾に `==NOTIFY==` ブロック(モック、当面通知は出さない)
       - exit 0

    べき等性:
      - 同日 2 回走らせても問題なし(2 回目は通常検知 0 件)
      - ただし同日 2 回 index.md を書き換えるのは避ける → log.md に既に「{today} index-refresh」エントリがある場合は exit 0
      - guard 実装: log.md の冒頭 30 行を grep して `[{today}] index-refresh` があれば skip

    失敗時:
      - find が失敗 → on_failure 経由でリトライ
      - index.md 書き込み失敗 → log にエラー記録 + 庭師に Discord master 通知

# === ③ 結果をどこに置くか ===
outputs:
  - kind: file_update
    path: /home/vps-harappa/garden-mirror/garden/soil/index.md
  - kind: log_append
    path: /home/vps-harappa/garden-mirror/garden/soil/log.md
  - kind: log
    path: /home/vps-harappa/garden-mirror/garden/log/{today}-index-refresh.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: none                   # 自律実行(剪定不要)
  approver: null
  notify:
    via: mock                     # 当面: log のみ
    group: null

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: none                       # 自律実行(承認なし)

# === ⑥ べき等性 ===
idempotency:
  key: index-refresh-{today}
  guard: |
    soil/log.md の冒頭 30 行に `[{today}] index-refresh` エントリがあれば exit 0(同日 2 重実行防止)。
    あるいは検知 0 件なら index.md / log.md とも触らずに exit 0。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: mock
    template: |
      ❌ mycelium/index-refresh 失敗
      日付: {today}
      理由: {error_summary}
      詳細: {log_path}
      → 手動で soil/index.md を見直すか、garden/mycelium/SKILL.md Mode 3 に従って手動 refresh

# === ⑧ 依存 ===
depends_on:
  workflow: null                  # 業務 workflow に依存しない
  state:
    - "/home/vps-harappa/garden-mirror/garden/soil/ が読み取り可能"
    - "/home/vps-harappa/garden/CHARTER.md が読み取り可能"
    - "/home/vps-harappa/garden/mycelium/SKILL.md が読み取り可能"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-06-01T03:00:00+09:00
---

# mycelium/index-refresh — 土壌の地図を日次で最新化

## 目的(不変)

soil/ の編集が起きたら **24 時間以内に soil/index.md が追従している** 状態を作る。庭師が朝、index を見れば最新の意味的サマリ(staff N 名・business N 件・workflows N 本)が読める。

## 現状の方法

frontmatter の `execute` / `idempotency` / `on_failure` を参照。要約:

1. cron 毎日 03:00 発火
2. Garden CHARTER + 菌糸 SKILL を読み込んだ Claude Code が、Mode 3 Step 1〜5 に従って:
   a. soil/ 配下の過去 24h 編集ファイルを find で検知
   b. 0 件なら skip、1 件以上なら差分把握 → index.md を意味的に更新
   c. soil/log.md に [今日] index-refresh エントリを追記
3. 異常時は on_failure(リトライ 2回 + log fallback)

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | mtime ベースの検知(過去 24h) | git diff ベースに切替(コミット粒度で追跡)| 未検証 |
| 💡 | cron 1日1回 | watcher daemon 化(編集即反映 + debounce 30分)| 構想中(Stage 2 以降) |
| ❓ | 検知 0 件で log.md 触らない | 何も起きなかった日も「skip」記録すべきか?(運用透明性 vs ノイズ) | 未検証 |
| ❓ | 大規模変更(>20ファイル)で停止 | 段階的に処理する設計(チャンク化)| 構想中 |
| ❓ | LLM 呼び出しコスト | 検知ありの日のみ claude-code 経由なので低頻度想定。Stage 2 安定後に Haiku 切替検討 | 未検証 |
| 💡 | 庭師通知 mock | 大規模変更検知時のみ Discord master 通知発火 | 構想中 |

## 関連

- 区画 SKILL: [garden/mycelium/SKILL.md](../../mycelium/SKILL.md)
- 維持対象: [garden/soil/index.md](../../soil/index.md)
- 編集ログ: [garden/soil/log.md](../../soil/log.md)
- ADR(S20): [菌糸の役割と soil 参照規約](../../../docs/decisions/2026-05-30-mycelium-and-soil-reference.md)
- 関連種(将来): `mycelium/ingest-raw`(Stage A.5)/ `mycelium/lint-weekly`(Stage 2)/ `mycelium/relations-monthly`(Stage 4)

## TODO(本種に固有)

- [ ] **VPS への配置**(`garden/seeds/mycelium/` 一式 + `garden/mycelium/` 一式 + CHARTER は配置済)
- [ ] **launcher.js に登録**(or crontab 直接 = 既存パターン要確認)
- [ ] **dry-run 検証**(手動で soil/ の 1 ファイル編集 → 種実行 → index 反映確認)
- [ ] **6/1 03:00 初稼働観察**

## active 化条件

1. [x] **菌糸 SKILL.md 起草**(本セッション)
2. [x] **soil/index.md の初回 full scan**(本セッション = ベースライン整備済)
3. [ ] **VPS 配置**(SKILL + 種 + 必要なら CHARTER 同期)
4. [ ] **cron 登録**(03:00 daily)
5. [ ] **dry-run 検証**(1 ファイル編集 → 種実行 → index 反映)
6. [ ] **初稼働観察**(6/1 03:00)
