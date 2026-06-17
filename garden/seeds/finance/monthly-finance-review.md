---
type: seed
name: monthly-finance-review
plot: finance
description: 毎月10日に、整地済みの Freee データで財務サマリー(PL/CF/着地予測)を取得し、Discord master に数値+論点で「対話の投げかけ」を行う種。board は作らない(通知=投げかけのみ)。手動「財務見せて」でも分析が回る。
status: test                     # S47 VPS デプロイ + cron 登録 + launcher dry-run GREEN
phase: 3a                         # read-only。承認境界なし(通知のみ)
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-17
created_by: claude (with ガクチョ, セッション47)
last_updated: 2026-06-17
linked_skills:
  - "garden/plots/finance/SKILL.md"   # Mode A
linked_services:
  - "garden/services/finance/analyzer.py"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 10 * *"          # 毎月10日 08:00 JST(記帳6日 + 監査9日 でデータが整った頃)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「財務見せて」「PL見せて」「キャッシュ大丈夫?」→ ガクコが Mode A を対話実行

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/finance
  timeout_minutes: 15
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    month_jp: "$(date +%-m月)"
  prompt: |
    あなたは finance 区画の種「monthly-finance-review」です。整地済みの財務データで
    ガクチョに「対話の投げかけ」を行うのが役目です(レポートを貼るだけにしない)。

    まず以下2ファイルを Read し、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/finance/SKILL.md(本区画の "Mode A: 財務分析" の議論フレーム)

    今回の動的入力:
      - today: {today}
      - month_jp: {month_jp}

    ⚠️ コマンドは絶対パス + cd なし:
      PY=/home/vps-harappa/garden/services/finance/.venv/bin/python
      ANA=/home/vps-harappa/garden/services/finance/analyzer.py

    Step 0 継続性(★最初に必ず):過去の経営議論を読んで地続きにする。
      - /home/vps-harappa/garden-mirror/garden/soil/finance/discussions/ の最新 md(前回どこまで議論したか)
      - /home/vps-harappa/garden-mirror/garden/soil/finance/targets.md(目標と着地予測の履歴)
      - /home/vps-harappa/garden-mirror/garden/soil/projects/toB-pipeline.md(案件の見込み)
      ※ soil は VPS では garden-mirror 配下(soil-sync 管理)。

    Step 1 サマリー取得(read-only):
      {PY} {ANA} summary
      → SUMMARY_JSON のパスと、テキスト出力(YTD実績 / 着地予測 / 現金残高 / 月次トレンド)を読む
      ※ 必要なら {PY} {ANA} cf や {PY} {ANA} check も併用してよい。

    Step 2 投げかけを作る(★この種の本質):
      SKILL Mode A の「財務の見方・議論フレーム」に沿って、数値を貼るだけでなく
      ガクチョと一緒に考えたい論点を 1〜2 点添える。例:
        - 目標比の乖離(売上 / 営業利益)
        - 月次のボラティリティ(toB 単発が凹ませた月など)
        - 着地シナリオ(強気/基本/保守をどう置くか)
        - CF 安全性(資金ショート月の有無)
      機械的な着地予測は「現ペース外挿」なので、季節変動は手当てが要ると添える。

    Step 3 庭師に投げかけ: log に `==NOTIFY==` で append(board は作らない):
      「📊 {month_jp}時点の財務、整いました。
        売上 YTD ¥{x}(目標比 {p}%)/ 営業利益 ¥{y} / 現金 ¥{cash} / 着地予測 売上 ¥{z}。
        一緒に考えたいのは ①{論点1} ②{論点2}。どこから話そう?」

    ※ この種は read-only。Freee を一切書き換えない。board も作らない(対話の口火だけ)。

    失敗時: summary が落ちたら on_failure に従い log + fallback 通知。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-finance-review.log

# === ④ 誰に伝えるか ===
pruning:
  channel: notify_only            # 承認境界なし(read-only)。board は作らない
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock
    group: master
    template: |
      📊 {month_jp}の財務サマリーが整いました。論点つきで投げかけます。
      → log/{today}-finance-review.log

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: discord_direct
  note: |
    承認境界なし。ガクチョが投げかけに乗ったら Discord master で対話継続(Mode A)。
    pl / cf / summary を追加で叩いたり、targets を設定したりは対話の中で。

# === ⑥ べき等性 ===
idempotency:
  key: monthly-finance-review-{today}
  guard: |
    read-only なので何度実行しても安全(Freee を書き換えない)。
    手動「財務見せて」はいつでも回せる。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ monthly-finance-review 失敗 / 詳細: {log_path}
      → 手動で analyzer.py summary を確認

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/finance/ デプロイ済 + venv 構築済"
    - "secrets(Freee 共有 token)配置済"
    - "config/targets.json に目標値設定済(無いと目標比表示がスキップ)"
  seeds:
    - "finance/monthly-sales-import(6日)"
    - "finance/monthly-data-audit(9日。整地後に走るのが理想)"

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null
---

# monthly-finance-review — 毎月10日の財務分析の投げかけ

## 目的(不変)

毎月10日(記帳6日 + 監査9日 でデータが整った頃)に、整地済みの Freee データで財務サマリー(PL/CF/着地予測)を取得し、**ガクチョに数値+論点で「対話の投げかけ」を行う**。レポートを貼るだけでなく、一緒に考えたい論点を添えて戦略議論の口火を切るのがこの種の本質。read-only で board は作らない。

## 現状の方法

frontmatter 参照。要約: cron 10日 08:00 発火 → CHARTER + finance SKILL(Mode A の議論フレーム)を読んだ Claude Code が `analyzer.py summary` を実行 → YTD実績・着地予測・現金残高・月次トレンドを読み、議論フレーム(現状診断 / CF安全性 / 着地シナリオ / アクション)に沿って論点を 1〜2 点添えて Discord に投げかけ。ガクチョが乗ったら対話継続。

## 関連

- 区画 SKILL: [garden/plots/finance/SKILL.md](../../plots/finance/SKILL.md) Mode A(財務の見方・議論フレーム)
- Python service: `garden/services/finance/analyzer.py`
- 先行例: daily-pilot(Claude 自身が判断・対話を担う型。Gemini 不要)

## active 化条件

1. [ ] VPS デプロイ + secrets + `config/targets.json` 目標値設定
2. [ ] スモーク(summary / cf / check 実 API + launcher --dry-run)
3. [ ] 10日 08:00 cron 登録 + bot「財務見せて」配線
4. [ ] 初回実走(summary → Discord 投げかけ → ガクチョと対話の1周)→ **active 昇格**
