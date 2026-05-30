# ADR: 種(seed) と SKILL の責務分離 — Garden の業務観モジュール化

日付: 2026-05-30
セッション: 19
ステータス: 採用

## 文脈

HMG 立ち上げ時、種 prompt に業務手順を全て詰め込んでいた。具体的には [seeds/daily-pilot/morning-briefing.md](../../garden/seeds/daily-pilot/morning-briefing.md) や [night-review.md](../../garden/seeds/daily-pilot/night-review.md) の prompt 内に Step 1〜N の手順が長文で並び、種 1 本で 200〜300 行のサイズになっていた。

セッション 19 の朝、初フル稼働した morning-briefing の体感を庭師が「機械的読み上げ」と評価。具体的な課題4点:
1. 振り返り時に active 上で書き換えた締切が backlog に反映されない(機能漏れ)
2. タスクが横並び圧縮で読みづらい(表示)
3. Triage の Q1/Q2/Q3 が受け身で芯を食わない(構成)
4. 締めの一言が汎用文で意味をなさない(出力)

[HMC `.agent/skills/hmc_pilot/SKILL.md`](../../../harappa-cockpit/.agent/skills/hmc_pilot/SKILL.md) と比較したところ、HMG seed prompt には **Core Philosophy(業務観)+ Output Style(出力規範)** が欠落していることが根本原因と判明。HMC は SKILL.md の3層構造(Core Philosophy / Operational Modes / Output Style)で業務観をモデル独立に集約していたのに対し、HMG は Operational Modes だけを seed prompt に書き、業務観と出力規範を「どこにも」置いていなかった。

加えて庭師から提起された懸念:
- ガクコ(対話層)とコア(種・workflow)が分離していくと、毎回どちらが何を担うかで混乱しそう
- HMC の素晴らしさは「新機能を SKILL モジュールとして書き出すだけで実装できた」運用工数の低さにあった。これを Garden でも保ちたい

## 決定

種 と SKILL を **異なる責務を持つ2層** として分離する。

### 層1:種(seed) = 発火ディスパッチャ

| 責務 | 「いつ」「どんな入力で」発火するか |
|---|---|
| 構成要素 | frontmatter: trigger / execute(engine + computed_inputs + prompt)/ outputs / pruning / on_failure / depends_on / idempotency / audit |
| prompt の中身 | **SKILL を Read して該当 Mode を発火** する薄い指示。手順は書かない |
| 場所 | `garden/seeds/{plot}/{name}.md` |
| 寿命 | 種ごと(発火条件が変われば書き換え) |

### 層2:SKILL = 業務観モジュール

| 責務 | 「何者として」「どんな原則で」「どんな出力スタイルで」動くか |
|---|---|
| 構成要素 | Core Philosophy(不変の業務観)/ ファイルと役割 / Mode 別 Step 手順 / Output Style(トーン・形式・良い例・悪い例)/ 確定済みの判断ルール / 参照する種・サービス表 |
| 場所 | `garden/plots/{plot}/SKILL.md` |
| 寿命 | 業務寿命(年単位) |
| 性質 | **モデル独立**(Claude / Gemini / GPT で同じ振る舞い)・**チャネル独立**(cron / Discord / event で同じ振る舞い) |

### 領域境界(よくある分岐)

| 内容 | 配置レイヤ |
|---|---|
| 業務観・判断原則・出力規範 | **SKILL** |
| 人格・口調・呼称 | **persona**(garden-gaku-co/persona/*.md) |
| 入出力チャネル特性(Discord 文字数制限、typing 表示 等) | **Python / bot 設定** |
| 「いつ起動するか」「冪等性」「失敗時挙動」 | **種 frontmatter** |
| その回限定の動的入力(today / calendar_block) | **種 prompt 内 computed_inputs** |

判断ルール:
- 「Claude を別モデルに替えても変わらないでほしい」→ SKILL
- 「ガクコを別 AI 名に替えても変わらないでほしい」→ persona
- 「Discord を LINE に替えたら変わる」→ Python / bot 設定

## 帰結

1. **同じ SKILL を複数 trigger が共有できる** — daily-pilot SKILL を cron 種2本 + Discord event 1本 + cron スクリプト2本 = 5経路が参照
2. **SKILL 更新で全経路に一括反映** — 種は次回 cron 起動時から自動反映(prompt 内で Read)/ bot 系は SKILL を起動時ロードのため再起動が必要
3. **新トリガーを増やしても SKILL 無修正** — watcher daemon 実装 → inbox-process 種を active 化 → 既存 SKILL Mode 4 を呼ぶだけ
4. **新機能 = 新 SKILL or 新 Mode 追加** — HMC で享受していた「SKILL モジュールを書くだけで実装できる」軽さが Garden でも復活
5. **HMC SKILL の移植が直行で可能** — shift_manager / finance 系などを Phase 3c で移植する際、`garden/plots/{区画名}/SKILL.md` に Garden 語彙で書き直すだけで区画が立ち上がる

## 実装(セッション19)

### daily-pilot 区画(plots 第1号)

[garden/plots/daily-pilot/SKILL.md](../../garden/plots/daily-pilot/SKILL.md)(新設・355行)が以下を集約:
- Core Philosophy 4原則(Human-in-the-Loop / SSOT / Pattern A / **Empowerment & Proactivity**)
- 呼称・トーン(「ガクチョ」音引きなし・畳みかけない)
- ファイルと役割表
- Mode 1: Morning Briefing(横串の Triage = 軸 A 過ごし方提案 / 軸 B AI 支援提案 / 軸 C 判断ほしい)
- Mode 2: Conversation(編集権限表 / 締めの確認 / 過去ログの扱い)
- Mode 3: Night Review(**active 編集の backlog 反映ロジック** = 短期対応 1 を SKILL に集約)
- Output Style(1タスク1行・セクション順・**良い締めの例 / 悪い締めの例**を明示)
- 確定済みの判断ルール表
- 「このSKILLを参照する種・サービス」表(5経路)

### 5経路の振り替え

| 経路 | trigger | 振り替え前 → 振り替え後 |
|---|---|---|
| [seeds/daily-pilot/morning-briefing.md](../../garden/seeds/daily-pilot/morning-briefing.md) | cron 06:30 | 300行 prompt → 30行(SKILL Mode 1 発火) |
| [seeds/daily-pilot/night-review.md](../../garden/seeds/daily-pilot/night-review.md) | cron 22:30 | 270行 prompt → 30行(SKILL Mode 3 発火) |
| [services/garden-gaku-co/bot.py](../../garden/services/garden-gaku-co/bot.py) | Discord event | ハードコード方針 → 起動時 SKILL ロード + prompt 同梱(Mode 2) |
| [services/garden-gaku-co/morning_greet.py](../../garden/services/garden-gaku-co/morning_greet.py) | cron 06:40 | Python 固定文 → claude -p + SKILL + persona(Mode 1 Step 4) |
| [services/garden-gaku-co/night_cheer.py](../../garden/services/garden-gaku-co/night_cheer.py) | cron 22:40 | persona のみ → SKILL + persona の二段(Mode 3 Step 7。集計とエラー検出は決め打ち継続) |

### 起源・継承

- HMC `.agent/skills/hmc_pilot/SKILL.md`(Antigravity IDE 時代の Vice Pilot SKILL)を起源として継承
- Garden 語彙で書き直し + Triage 構造の再設計(Q1/Q2/Q3 → 軸 A/B/C)+ active→backlog 反映ロジックを Mode 3 Step 4 に明示

## 副作用と検証

- 種は SKILL を毎回 Read するためレイテンシが微増。ただし daily-pilot 種は 06:25/06:30/22:30 の3回/日でコスト無視できる
- bot は SKILL を起動時ロードのため SKILL 更新時は再起動必須。`run-bot.sh` の keepalive が手作業を最小化(`kill && rm pid && run-bot.sh`)
- セッション19 当日に Discord 対話で reschedule 経路のライブ検証成功(S17/S18 持ち越し3セッションが消化)。SKILL Mode 2 の編集権限表通りに backlog + active 両方が反映され、bot が独自工夫で `## 運営・企画(繰越)` セクションを冒頭に新設するという「先回り」も観察された

## 関連

- ADR セッション 7: [種スキーマ](2026-05-25-seed-schema-and-execution-host.md)
- ADR セッション 8: [スキーマ拡張5項目](2026-05-27-seed-schema-extensions.md)(`pruning.channel: none` / `on_complete` 等)
- ADR セッション 16: [garden-gaku-co を Garden の対話層に統合](2026-05-28-garden-gaku-co-interaction-layer.md)
- MAP.md Phase 4 「区画の Garden 化」を前倒し着手(daily-pilot が区画第1号)
- memory: [ux-first-dev-flow](../../../.claude/projects/-home-tukapontas-harappa-garden/memory/ux-first-dev-flow.md)(本 ADR の起点となった「実装前に UX 確認」の指針)

## 今後

- 次の区画候補: `garden/plots/shift_manager/SKILL.md`(HMC からの移植第1号、Phase 3c 着手時)
- watcher daemon 実装後、`inbox-process` 種が active 化されたら SKILL に Mode 4(Inbox Processing)を追記
- 「種 trigger と SKILL Mode の対応関係」を表で常に最新化(現状は SKILL 末尾の表が正本)
