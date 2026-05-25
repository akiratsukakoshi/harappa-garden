# HMG 庭の見取り図

> **常に最新**。セッションごとに更新する。塚越さん(庭師)が「今どこにいるか」を1ページで把握するためのファイル。

## 一行で

HARAPPA Management Garden (HMG) は AI中心の経営運用プラットフォーム。
庭師=塚越さん、エージェント群=自律的に育つ生態系。HMC(操縦席)からの進化版(庭=育てる生態系)。

## 現在地 @2026-05-25

- **設計フェーズ**: 土壌の最小実装(Phase 1)+ 種の設計方針(Phase 3 入口)+ workflow 規律の整備 + **デイリーワークフローのアーキテクチャ確定(Phase 3 実装準備)**
- **直近セッション**: [2026-05-25 セッション6](../docs/sessions/2026-05-25-session6.md) — デイリーワークフローの種化(4本立て)+ タスクマスタを Obsidian LiveSync + VPS CouchDB に + Claude Code ヘッドレスを Garden 全体の頭脳に
- **直近の重要決定**: タスクマスタ = Obsidian LiveSync(CouchDB)/ backlog がマスタ・active は派生 / 種の頭脳 = Claude Code ヘッドレス on VPS / Triage = LINE + board MD ハイブリッド / 締切なし追加 = 翌日暫定締切自動付与

## 区画別ステータス

凡例: ⬜未着手 / 🌱育成中(骨格あり) / 🌳成熟 / 🍂休耕 / 🥗収穫済

| Garden 語彙 | パス | 状態 | 一行 |
|---|---|---|---|
| 土壌 (soil) | [garden/soil/](soil/) | 🌱 | 骨格 + スタッフ28(role全員確定)+ 事業骨格21 + alumni候補48(保留) |
| 土壌-people/staff | [soil/people/staff/](soil/people/staff/) | 🌳 | 29名 active(運営4・フィールド20・写真5・調理0 + 飯田=企画会議メンバー、contract/role 未確定)、alumni候補48は保留 |
| 土壌-people/clients | [soil/people/clients/](soil/people/clients/) | ⬜ | クライアント担当者(個人) |
| 土壌-people/partners | [soil/people/partners/](soil/people/partners/) | ⬜ | パートナー窓口 |
| 土壌-business | [soil/business/](soil/business/) | 🌱 | 21ファイル骨格、各サービスの中身埋め待ち(3学部に linked_workflows 反映済) |
| 土壌-clients | [soil/clients/](soil/clients/) | ⬜ | クライアント企業本体 |
| 土壌-projects | [soil/projects/](soil/projects/) | ⬜ | 進行中プロジェクト |
| 土壌-workflows | [soil/workflows/](soil/workflows/) | 🌱 | toC原っぱ大学の3階層(年次/月次/開催毎)言語化済。monthly-cycle と daily-cycle が A 案テンプレで詳細化済。残り2本(annual / program-execution)は次セッション以降に書き直し |
| 土壌-events | [soil/events/](soil/events/) | ⬜ | 個別イベント |
| 土壌-meetings | [soil/meetings/](soil/meetings/) | ⬜ | 議事録インデックス(Plaud等) |
| 土壌-concepts | [soil/concepts/](soil/concepts/) | 🌱 | [[kodomon]] 1件(外部システム) |
| 種 (seeds) | garden/seeds/ | ⬜ | トリガー(cron/event/状態変化)定義 |
| 区画 (plots) | garden/plots/ | ⬜ | HMC SKILL の Garden 化版 |
| 番人 (watchers) | garden/watchers/ | ⬜ | 監視エージェント |
| 苗床 (nursery) | garden/nursery/ | ⬜ | 試行領域 |
| 蔵 (kura) | garden/kura/ | ⬜ | 長期アーカイブ |

## ロードマップ(Phase)

### Phase 1: 土壌の最小実装 ← **現在地**

土壌の主要カテゴリ(人・事業・クライアント・フロー・議事録)に **骨格** を持たせる。中身は順次埋める。

- [x] コンセプト・ネーミング(2026-05-22 セッション1)
- [x] garden/ + soil/ 骨格(README/index/log)
- [x] スタッフマスター(28名 active、role 全員確定 @2026-05-22)
- [x] スタッフスキーマ contract/role 2軸化(2026-05-22 セッション2)
- [x] 事業構造骨格(toC/toB/communication 21ファイル)
- [x] 業務フロー初期化(toC原っぱ大学 3階層、2026-05-23 セッション3)
- [ ] alumni 候補 48名の `_alumni.md` 集約(塚越さん「無視でOK」判定で保留)
- [ ] クライアント企業一覧(`soil/clients/`)
- [ ] 業務フロー拡張(toB・キャンプ等の不定期イベント・サボル/俺のヨガ)
- [ ] 議事録インデックス(`soil/meetings/`) — Plaud 連携

### Phase 2: 剪定の規律(承認境界)

土壌の輪郭が見えたら、エージェントの自律実行 vs 庭師承認の境界を設計。

- [ ] 自律実行 vs 剪定待ちの境界文書化
- [ ] 通知方法(連絡板/高札)の設計
- [ ] LINE 通知連携(まずは塚越さん個人、後にチーム)
- [ ] **VPS 信頼性 watcher の設計**(Garden 共通課題、番人候補)

### Phase 3: 種(自律トリガー)

エージェントが自律起動できる仕組み。

- [x] 設計方針合意(2026-05-23 セッション4) — 3形式・ガクコ統合・番人/剪定の振り分け
- [x] 種スキーマの位置づけ・目的合意(2026-05-24 セッション5)
- [x] 最初の種候補の絞り込み(2026-05-24 セッション5) — `shift_manager/monthly-shift-survey`(月初1日アンケート送信)
- [x] **デイリーワークフローの種化アーキテクチャ確定(2026-05-25 セッション6)** — 4本立て + Claude Code ヘッドレス + LiveSync + Triage ハイブリッド
- [ ] 種の YAML スキーマ設計 ← **次セッション本命**
- [ ] 種1本目: `shift_manager/monthly-shift-survey` の draft YAML 作成
- [ ] 種2本目以降: `daily-pilot/*` 4本(recurring-spawn / morning-briefing / night-review / inbox-process)
- [ ] 連絡板(`garden/board/`)の構造設計
- [ ] 緊急 push の経路設計(ガクコ進化と同期)
- [ ] cron / event / 状態変化 のトリガー定義(`garden/seeds/`)
- [ ] **VPS CouchDB + Obsidian LiveSync セットアップ手順策定**(daily-pilot 種の前提インフラ)
- [ ] **平文 MD ミラー daemon の実装**(`_changes` feed リスナ)
- [ ] **gaku-co5.0 側に「LINE 返信 → board MD 書き戻し」処理を実装**
- [ ] MCP server 実装(土壌へのアクセス層)
- [ ] 既存ソース(Square予約・Notion・Plaud)の ingest

### Phase 4: 区画の Garden 化

HMC SKILL を順次 HMG に移植・自律化。

- [ ] HMC SKILL の Garden 化(finance_importer → invoice_processor → ...)
- [ ] 番人エージェントの実装(`garden/watchers/`)
- [ ] チームメンバー(LINE 経由)への開放準備

## 直近の宿題

### 庭師(塚越さん)
- [ ] **稼働時間表のスタッフへの見せ方**(セッション4 で保留 — 個別要約 / スプシ個人タブ / 現状スクショ から選ぶ or 新案)
- [ ] `business/` 各サービスページの中身埋め(or Claude が他ソースから合成)
- [ ] 飯田淳毅さんの contract 確定(業務委託で良いか)
- [ ] `余の日` プログラムの実態
- [ ] Notion 振り返りレポート構造の MCP 開放(必要タイミングで)
- [ ] 体験案内 / お礼テンプレートのコピー元提供
- [ ] シフト管理担当の確認(`monthly-cycle` の TODO)
- [ ] Square予約 / Notion / Plaud のシェア(Phase 3 で必要)
- [ ] 月次シートの Q列チェック運用(誰がいつ入れるか)
- [ ] コドモンの API/MCP 提供有無の確認可能性
- [ ] **(新)** VPS 信頼性課題(Docker 停止)対処の優先度判断
- [ ] **(新)** Obsidian LiveSync 採用に伴う現行 Obsidian 同期方式(Remotely Sync 等)の切替計画

### Claude
- [ ] 次回セッション開始時に本 MAP.md + セッション6 + 2026-05-25/24/23 の 3 ADR を読む
- [ ] **次回本命(継続)**: 種の YAML スキーマ設計 + `shift_manager/monthly-shift-survey` の draft YAML
  - スキーマには `engine:` フィールド・`depends_on:` を組み込む
- [ ] **workflow 書き直し残り(A 案テンプレ適用)**:
  - [ ] `garden/soil/workflows/annual-quarterly-planning.md`
  - [ ] `garden/soil/workflows/program-execution.md`
- [ ] **(新)** VPS CouchDB + Obsidian LiveSync セットアップ手順策定
- [ ] **(新)** 平文 MD ミラー daemon 実装方針(`_changes` feed リスナ)
- [ ] **(新)** gaku-co5.0 側「LINE 返信 → board MD 書き戻し」の連携仕様

## 主要な決定の索引

| 決定 | 日付 | 記録場所 |
|---|---|---|
| HMG ネーミング | 2026-05-22 | [decisions/2026-05-22-naming.md](../docs/decisions/2026-05-22-naming.md) |
| 土壌方式 = Karpathy LLM Wiki | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |
| スキーマ = role 1軸 + 機微情報 Wiki 外置き | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |
| 慶ちゃん追加・「運営」表記統一 | 2026-05-22 | [CLAUDE.md](../CLAUDE.md) |
| Obsidian は分離 + 読み取り参照 | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |
| 業務フロー = ハイブリッド配置 | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |
| スタッフスキーマ contract/role 2軸分離 | 2026-05-22 | [sessions/2026-05-22-session2.md](../docs/sessions/2026-05-22-session2.md) |
| 三根美紗 = 三根美沙(Freee) 表記ゆれ同定 | 2026-05-22 | [sessions/2026-05-22-session2.md](../docs/sessions/2026-05-22-session2.md) |
| スタッフ 28名 role 全員確定 | 2026-05-22 | [sessions/2026-05-22-session2.md](../docs/sessions/2026-05-22-session2.md) |
| alumni 候補48名は保留(言及不要のため) | 2026-05-22 | [sessions/2026-05-22-session2.md](../docs/sessions/2026-05-22-session2.md) |
| workflows/ = toC原っぱ大学 3階層(年次/月次/開催毎)で初期化 | 2026-05-23 | [sessions/2026-05-23-session3.md](../docs/sessions/2026-05-23-session3.md) |
| 飯田淳毅 = 企画会議メンバーとして staff 化 | 2026-05-23 | [sessions/2026-05-23-session3.md](../docs/sessions/2026-05-23-session3.md) |
| 種は 3形式(cron / event / state-change) | 2026-05-23 | [decisions/2026-05-23-seeds-design-direction.md](../docs/decisions/2026-05-23-seeds-design-direction.md) |
| ガクコ = 庭の出口(3チャネル+承認フローを再利用) | 2026-05-23 | [decisions/2026-05-23-seeds-design-direction.md](../docs/decisions/2026-05-23-seeds-design-direction.md) |
| 番人 = 定刻 cron + 緊急 push | 2026-05-23 | [decisions/2026-05-23-seeds-design-direction.md](../docs/decisions/2026-05-23-seeds-design-direction.md) |
| 剪定の置き場は重さで自動振り分け(line / board_with_notify / board) | 2026-05-23 | [decisions/2026-05-23-seeds-design-direction.md](../docs/decisions/2026-05-23-seeds-design-direction.md) |
| ガクコ core_team は当面いじらず(飯田は未参加) | 2026-05-23 | [decisions/2026-05-23-seeds-design-direction.md](../docs/decisions/2026-05-23-seeds-design-direction.md) |
| workflows/ が正本(SKILL/他データソースは追従) | 2026-05-24 | [decisions/2026-05-24-workflows-as-truth-and-improvement-targets.md](../docs/decisions/2026-05-24-workflows-as-truth-and-improvement-targets.md) |
| workflow は目的不変・方法は改善対象(各ステップに改善余地表) | 2026-05-24 | [decisions/2026-05-24-workflows-as-truth-and-improvement-targets.md](../docs/decisions/2026-05-24-workflows-as-truth-and-improvement-targets.md) |
| 種は責務で分割(同タイミングでも分ける) | 2026-05-24 | [sessions/2026-05-24-session5.md](../docs/sessions/2026-05-24-session5.md) |
| 最初の種 = `shift_manager/monthly-shift-survey`(月初1日アンケート送信) | 2026-05-24 | [sessions/2026-05-24-session5.md](../docs/sessions/2026-05-24-session5.md) |
| タスクマスタの置き場 = Obsidian LiveSync + VPS CouchDB(数秒push同期) | 2026-05-25 | [decisions/2026-05-25-daily-workflow-and-task-master-architecture.md](../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md) |
| backlog がマスタ、active_tasks は派生ビュー(全 recurring が backlog 経由) | 2026-05-25 | 同上 |
| デイリーワークフローの種は 4本立て(recurring-spawn / morning-briefing / night-review / inbox-process) | 2026-05-25 | 同上 |
| 種の頭脳 = Claude Code ヘッドレス起動 on VPS(Garden 全体に適用) | 2026-05-25 | 同上 |
| Triage 対話チャネル = LINE + board MD ハイブリッド(返信2系統) | 2026-05-25 | 同上 |
| night-review = 常に処理(差分のみ反映、active は必ずクリア) | 2026-05-25 | 同上 |
| `## 追加` 締切なしタスク = 翌日デフォルトで暫定締切自動付与 + 翌朝 Triage で確定 | 2026-05-25 | 同上 |

## 直近のセッション

- [2026-05-25 セッション6](../docs/sessions/2026-05-25-session6.md) — デイリーワークフローの種化アーキテクチャ確定(4本立て + Claude Code ヘッドレス + LiveSync + Triage ハイブリッド)
- [2026-05-24 セッション5](../docs/sessions/2026-05-24-session5.md) — workflow を正本かつ改善対象として整備、monthly-cycle 詳細化、コドモン登録、種候補3本に整理
- [2026-05-23 セッション4](../docs/sessions/2026-05-23-session4.md) — 種(seeds) 設計の基本方針(時計のメタファ・ガクコ統合・剪定振り分け)
- [2026-05-23 セッション3](../docs/sessions/2026-05-23-session3.md) — workflows/ toC原っぱ大学 3階層初期化・飯田淳毅 staff 追加
- [2026-05-22 セッション2](../docs/sessions/2026-05-22-session2.md) — スタッフスキーマ contract/role 2軸化・28名 role 全員確定
- [2026-05-22 セッション1](../docs/sessions/2026-05-22-session1.md) — HMG 立ち上げ・土壌+業務骨格構築

## 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md) — プロジェクト規約
- [docs/concept.md](../docs/concept.md) — HMG コンセプト(育てる文書)
- [docs/garden-vocabulary.md](../docs/garden-vocabulary.md) — Garden 語彙
- [docs/origin.md](../docs/origin.md) — HMC からの由来
- [garden/README.md](README.md) — garden/ 配下の構造
- [garden/soil/README.md](soil/README.md) — 土壌の運用ルール
