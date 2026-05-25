# 種スキーマ草案 + cron 実行ホスト = VPS + Phase 3 細分

- **日付**: 2026-05-25
- **記録**: セッション7
- **決定者**: 塚越さん (庭師) / Claude (壁打ち相手)
- **ステータス**: 合意・1本目 draft 起草済(`monthly-shift-survey`)。実装は Phase 3a/3b で順次

## 背景

セッション5・6 で種の設計方針は固まったが、 **種ファイルの具体構造(スキーマ・配置・実行記述)** は draft 化に至っていなかった。本セッションで:

1. 種ファイルの **スキーマ草案** を確定し、1本目を起草する
2. その過程で、塚越さんから **「cron 系の発火タイミング = ローカル PC が落ちていたら走らないのでは?」** という指摘が出る
3. → cron 実行ホストの確定と、Phase 3 の実装順整理が連鎖して論点化

塚越さんのペイン:
- PC は夜落とすので、ローカル cron だと深夜・早朝が走らない
- 「PC 起動を確認するフロー」を排除したい(セッション6 から続く主題)

## 決定 1: 種ファイルのスキーマ草案(MD frontmatter + 本文)

セッション5 ADR の workflow テンプレ(目的・現状の方法・改善余地)と同じ形式で、frontmatter にスキーマ、本文に「目的・現状の方法・改善余地」を持つ。

### frontmatter 9要素

| # | フィールド | 用途 |
|---|---|---|
| ① | `trigger` | いつ点火(cron/event/state-change) |
| ② | `execute` | engine + skill + prompt + computed_inputs |
| ③ | `outputs` | board_draft / log / active_tasks / backlog / archive |
| ④ | `pruning` | channel(セッション4 ADR の line/board_with_notify/board)+ approver + notify |
| ⑤ | `post_approval` | ガクコ /send 経由配信、send 成功/失敗時の挙動 |
| ⑥ | `idempotency` | key + guard(重複発火防止) |
| ⑦ | `on_failure` | retry + fallback 通知 |
| ⑧ | `depends_on` | workflow / state / seeds |
| ⑨ | `audit` | last_fired / last_outcome / next_fire_estimate |

詳細は [garden/seeds/README.md](../../garden/seeds/README.md) を参照。

### 配置

```
garden/seeds/
├── README.md
├── .log/
└── {plot}/{seed-name}.md
```

`{plot}` は当面 HMC SKILL 名と一致(`shift_manager` / `daily-pilot` / `finance_importer` …)。

### 実行記述

`execute.prompt` に **SKILL 参照 + 自然言語指示** を書く(セッション6 の Claude Code ヘッドレス決定と整合)。シェルコマンド直書きではなく、Claude Code が SKILL を読み解いて判断する余地を残す。

## 決定 2: cron 系の種実行ホスト = すべて VPS(PC 非依存)

- セッション6 ADR「種の頭脳 = Claude Code ヘッドレス on VPS」の **延長線上の再確認**
- WSL 上の cron は使わない(夜間・早朝の cron 不走行を構造的に排除)
- 種ランチャー実装は VPS 上で行う(cron → `claude -p "Run seed X"` → ログ + on_failure)

## 決定 3: 種を「HMC 依存度」で分類 + Phase 3 を 3a / 3b / 3c に細分

| 分類 | 例 | VPS だけで完結? |
|---|---|---|
| **Garden 内完結種** | daily-pilot 全4本(backlog/active/board/ガクコ/calendar のみ参照) | ✅ |
| **HMC 依存種** | shift_manager / finance 系(HMC スクリプト・credentials・venv が必要) | ❌(HMC を VPS に移すまで active 化不可) |

### 実装順

| Phase | 内容 |
|---|---|
| **3a** | 種ランチャー(VPS) + Garden 内完結種(daily-pilot 4本)の active 化 |
| **3b** | HMC の VPS 移植 + secret 管理設計(別 ADR: [VPS secret 管理方針](2026-05-25-vps-secret-management-direction.md)) |
| **3c** | HMC 依存種(`monthly-shift-survey` 含む)の active 化 |

→ 本セッションで draft 起草した `monthly-shift-survey` は **Phase 3c 待ち**。先に動くのは daily-pilot 系。

## 決定 4: SKILL 再編問題は「相談事項」として記録、種2本目以降で具体化

塚越さんから提起:

> 種スキーマ設定後はスキルの再編集も必要だと考えています。複数の種にまたがってスキルが記載されていたりいなかったり、1つのスキルを異なる種から参照するなどが置きそうです。

現状の HMC SKILL は機能集約型(1 SKILL = 機能群)。種化(1種 = 1責務)すると、 **1 SKILL を複数種が異なるタスクで参照** する構造になる。SKILL 再編は不可避。

### 暫定対応方針

- 種は当面 **「該当する HMC SKILL の特定タスクだけ呼び出す」** 形で書く(`execute.prompt` で範囲を絞る)
- 種 frontmatter の `execute.skill` を機械可読にして、「この SKILL を参照している種一覧」が grep で出る → 影響分析の足場
- 種を増やす過程で再編必要性が顕在化したら、SKILL 分解 ADR を立てる

### 未決

- SKILL の粒度を **種に対応する細粒度** に再編するか / **機能群のまま接面だけ統一** するか
- 共通処理(ガクコ配信など)を **横断 SKILL** として独立させるか / 各 SKILL に持たせるか

→ MAP.md の宿題と seeds/README.md の「相談事項」として両側面で記録。

## 適用範囲

### 即時適用(本セッション)

- [garden/seeds/README.md](../../garden/seeds/README.md) — 種運用ルール + スキーマ定義 + 実行ホスト確定 + Phase 3a/3b/3c 細分 + 相談事項記録
- [garden/seeds/shift_manager/monthly-shift-survey.md](../../garden/seeds/shift_manager/monthly-shift-survey.md) — 1本目 draft(Phase 3c 待ち)
- [garden/MAP.md](../../garden/MAP.md) — Phase 3 細分、宿題、決定索引、現在地、直近セッション
- [docs/sessions/2026-05-25-session7.md](../sessions/2026-05-25-session7.md) — 本セッション サマリ

### Phase 3a 実装課題(次セッション以降)

- VPS CouchDB + LiveSync セットアップ手順策定
- 種ランチャー実装(VPS cron → `claude -p` + ログ + on_failure)
- 平文 MD ミラー daemon 実装(`_changes` feed リスナ)
- watcher daemon 実装(event 種用、glob 監視)
- 連絡板(`garden/board/`)の構造設計
- gaku-co5.0 側「LINE 返信 → board MD 書き戻し」
- daily-pilot 4本の draft 起草 → active 化

### Phase 3b 実装課題

- [VPS secret 管理方針 ADR](2026-05-25-vps-secret-management-direction.md) の実装
- HMC の VPS 移植 or 必要部分切り出し
- VPS ハードニング監査・強化(別セッション)

### Phase 3c 実装課題

- HMC 依存種(`monthly-shift-survey` から開始)の active 化

## 既存決定との関係

- **継承**:
  - セッション4 ADR(種設計の方針 — 3形式・ガクコ統合・剪定振り分け)
  - セッション5 ADR(workflow 正本性 + A 案テンプレ + 責務分割)
  - セッション6 ADR(デイリーワークフロー種化 + Claude Code ヘッドレス + Triage)
- **拡張**:
  - 種ファイルの具体スキーマ化
  - 実行ホストの統一化(VPS 確定)
  - Phase 3 の段階分割
- **影響**:
  - すべての種 frontmatter に `execution_host`・`phase`・`hmc_dependency` を持たせる
  - daily-pilot 系の起草・実装が優先(`monthly-shift-survey` は Phase 3c 待ち)

## 関連

- [セッション7 サマリ](../sessions/2026-05-25-session7.md)
- [VPS secret 管理方針 ADR](2026-05-25-vps-secret-management-direction.md)
- [セッション6 ADR(デイリーワークフロー)](2026-05-25-daily-workflow-and-task-master-architecture.md)
- [セッション5 ADR(workflow 正本性)](2026-05-24-workflows-as-truth-and-improvement-targets.md)
- [セッション4 ADR(種設計方針)](2026-05-23-seeds-design-direction.md)
- [garden/seeds/README.md](../../garden/seeds/README.md)
- [garden/seeds/shift_manager/monthly-shift-survey.md](../../garden/seeds/shift_manager/monthly-shift-survey.md)
