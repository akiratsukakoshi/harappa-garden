# HMG 庭の見取り図

> **常に最新**。セッションごとに更新する。塚越さん(庭師)が「今どこにいるか」を1ページで把握するためのファイル。

## 一行で

HARAPPA Management Garden (HMG) は AI中心の経営運用プラットフォーム。
庭師=塚越さん、エージェント群=自律的に育つ生態系。HMC(操縦席)からの進化版(庭=育てる生態系)。

## 現在地 @2026-05-25

- **設計フェーズ**: 土壌の最小実装(Phase 1)+ 種スキーマ草案 + 種 draft 5本(shift 1 + daily-pilot 4)+ **案 E(recurring 完了済み再 spawn 防止)合意** + スキーマ拡張 5 項目(暫定)
- **直近セッション**: [2026-05-25 セッション8](../docs/sessions/2026-05-25-session8.md) — daily-pilot 4本 draft 起草(recurring-spawn / morning-briefing / night-review / inbox-process)+ スキーマ拡張 5 項目 + 案 E(recur マーカー方式)
- **直近の重要決定**: daily-pilot 4本 draft 化 / スキーマ拡張 5 項目(channel:none, on_complete, trigger.exclude/debounce, {event.path}) / 案 E = `<!-- recur:{id}@{period_id} -->` で backlog+archive 両方 grep / recurring_master の ID 必須 / night-review が archive 転記時に元行完全保持

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
| 種 (seeds) | [garden/seeds/](seeds/) | 🌱 | README + スキーマ草案(+拡張5項目 暫定)+ draft 5本(shift 1 + daily-pilot 4)+ 案 E 合意 |
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

### Phase 3: 種(自律トリガー) — **3a / 3b / 3c に細分(セッション7)**

エージェントが自律起動できる仕組み。

#### 設計合意済

- [x] 設計方針合意(2026-05-23 セッション4) — 3形式・ガクコ統合・番人/剪定の振り分け
- [x] 種スキーマの位置づけ・目的合意(2026-05-24 セッション5)
- [x] 最初の種候補の絞り込み(2026-05-24 セッション5) — `shift_manager/monthly-shift-survey`(月初1日アンケート送信)
- [x] **デイリーワークフロー種化アーキテクチャ確定(2026-05-25 セッション6)** — 4本立て + Claude Code ヘッドレス + LiveSync + Triage ハイブリッド
- [x] **種 YAML スキーマ草案 + 1本目 draft(2026-05-25 セッション7)** — [seeds/README.md](seeds/README.md) と [shift_manager/monthly-shift-survey.md](seeds/shift_manager/monthly-shift-survey.md)
- [x] **cron 種の実行ホスト確定(2026-05-25 セッション7)** — すべて VPS で起動(PC 非依存)
- [x] **種を HMC 依存度で分類 + Phase 3 を 3a/3b/3c に細分(セッション7)**
- [x] **daily-pilot 4本 draft 起草(2026-05-25 セッション8)** — [daily-pilot/](seeds/daily-pilot/)
- [x] **スキーマ拡張 5 項目(暫定)導入(セッション8)** — `pruning.channel: none` / `on_complete` / `trigger.exclude` / `trigger.debounce` / `{event.path}` 変数
- [x] **案 E(recurring 完了済み再 spawn 防止)合意(セッション8)** — `<!-- recur:{id}@{period_id} -->` マーカーで backlog+archive 両方 grep

#### Phase 3a: 種ランチャー(VPS)+ Garden 内完結種(daily-pilot 4本)の active 化

- [x] **種2-5本目 draft 起草: `daily-pilot/*` 4本**(2026-05-25 セッション8)
- [ ] **VPS CouchDB + Obsidian LiveSync セットアップ手順策定**(全種共通の前提)
- [ ] **平文 MD ミラー daemon の実装**(`_changes` feed リスナ)
- [ ] **種ランチャー実装**(VPS cron → `claude -p` 起動 + ログ + on_failure)
- [ ] **watcher daemon 実装**(event 種用、glob 監視)
- [ ] 連絡板(`garden/board/`)の構造設計(pending / processed の切り分け、配信本文セクション規約、recur マーカー連動)
- [ ] **gaku-co5.0 側「LINE 返信 → board MD 書き戻し」処理を実装**
- [ ] **recurring_master.md のスキーマ確定 + 既存 recurring の棚卸し + 移行計画**
- [ ] **スキーマ拡張 5 項目 + 案 E の正式 ADR 化**(暫定 → 正式へ)
- [ ] daily-pilot 4本の active 化

#### Phase 3b: HMC の VPS 移植 + secret 管理設計

- [ ] **secret 管理設計の確定(セッション7 議論B 継続)** — 保管方式・rotation・信頼境界・VPS ハードニング
- [ ] `docs/security/README.md` を VPS 環境にも拡張(現状は WSL 前提)
- [ ] HMC の VPS 移植 or 必要部分切り出し(まず shift_manager の `generate_shift_form.py` から)
- [ ] HMC credentials の VPS 配置(Freee / Google OAuth・人事労務 freee)
- [ ] VPS 自体のハードニング監査・強化(SSH / firewall / fail2ban / 自動更新)

#### Phase 3c: HMC 依存種の active 化(Phase 3b 完了後)

- [ ] `shift_manager/monthly-shift-survey` を active 化
- [ ] `shift_manager/month-end-working-hours-prep` 起草 → active
- [ ] `shift_manager/monthly-working-hours-confirmation` 起草(庭師「見せ方」決定後)
- [ ] `shift_manager/monthly-shift-finalize` 起草 → active
- [ ] finance 系・invoice_processor・expense_processor 等の種化

#### 横断・後フェーズ

- [ ] 緊急 push の経路設計(ガクコ進化と同期)
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
- [ ] **(新)** スキーマ拡張 5 項目の正式 ADR 化判断(早期 ADR 化 / Phase 3a 実装で揉んでから)
- [ ] **(新)** monthly period 表現の柔軟性方針(指定日のみで開始 / 月末 / N営業日 まで含むか)
- [ ] **(新)** 既存 recurring の recurring_master.md への移行計画(HMC・紙ベース・運用上のもの)

### Claude
- [ ] 次回セッション開始時に本 MAP.md + 直近セッション(8)サマリ + 2026-05-25 ADR 2本(セッション6・7)+ 2026-05-24/23 の 2 ADR を読む
- [x] 種の YAML スキーマ設計 + `monthly-shift-survey` draft(セッション7 完了)
- [x] daily-pilot 系 4種の draft 起草(セッション8 完了)
- [ ] **次回本命候補(1)**: Phase 3a インフラ — 種ランチャー + VPS CouchDB セットアップ手順策定
- [ ] **次回本命候補(2)**: 案 E + スキーマ拡張 5 項目の ADR 化
- [ ] **次回本命候補(3)**: 連絡板(`garden/board/`)の構造設計
- [ ] **workflow 書き直し残り(A 案テンプレ適用)**:
  - [ ] `garden/soil/workflows/annual-quarterly-planning.md`
  - [ ] `garden/soil/workflows/program-execution.md`
- [ ] VPS CouchDB + Obsidian LiveSync セットアップ手順策定(Phase 3a)
- [ ] 平文 MD ミラー daemon 実装方針(`_changes` feed リスナ、Phase 3a)
- [ ] gaku-co5.0 側「LINE 返信 → board MD 書き戻し」の連携仕様(Phase 3a)
- [ ] (継続) `docs/security/README.md` の VPS 環境向け拡張(Phase 3b)

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
| 種スキーマ草案(MD frontmatter 9要素)+ plot別配置 + SKILL参照+自然言語指示 | 2026-05-25 (S7) | [decisions/2026-05-25-seed-schema-and-execution-host.md](../docs/decisions/2026-05-25-seed-schema-and-execution-host.md) |
| cron 種の実行ホスト = すべて VPS(PC 非依存) | 2026-05-25 (S7) | 同上 |
| Phase 3 を 3a/3b/3c に細分(VPS完結種先行 / HMC移植 / HMC依存種active化) | 2026-05-25 (S7) | 同上 |
| VPS secret 保管 = 平文env+600開始(age 暗号化への余地残す) | 2026-05-25 (S7) | [decisions/2026-05-25-vps-secret-management-direction.md](../docs/decisions/2026-05-25-vps-secret-management-direction.md) |
| サービス単位 Docker 分離 + コンテナ内 root 不使用 + secret は必要コンテナのみマウント | 2026-05-25 (S7) | 同上 |
| OAuth scope 最小化(大枠) + 人事労務 freee 独立 client + 読取/書込分離 | 2026-05-25 (S7) | 同上 |
| rotation = 発覚時 + 年1強制 + docs/security/incidents/ 記録 | 2026-05-25 (S7) | 同上 |
| daily-pilot 4本 draft 起草(recurring-spawn / morning-briefing / night-review / inbox-process) | 2026-05-25 (S8) | [sessions/2026-05-25-session8.md](../docs/sessions/2026-05-25-session8.md) |
| スキーマ拡張 5 項目(暫定)= `pruning.channel: none` / `on_complete` / `trigger.exclude` / `trigger.debounce` / `{event.path}` | 2026-05-25 (S8) | 同上 |
| 案 E: recurring 完了済み再 spawn 防止 = `<!-- recur:{id}@{period_id} -->` で backlog+archive 両方 grep | 2026-05-25 (S8) | 同上 |
| recurring_master の各エントリは `id:` 必須(タスク名表記揺れの根本対策) | 2026-05-25 (S8) | 同上 |
| night-review は `[x]` → archive 転記時に元行を完全保持(recur マーカー含む) | 2026-05-25 (S8) | 同上 |

## 直近のセッション

- [2026-05-25 セッション8](../docs/sessions/2026-05-25-session8.md) — daily-pilot 4本 draft 起草 + スキーマ拡張 5 項目 + 案 E(recur マーカー方式)
- [2026-05-25 セッション7](../docs/sessions/2026-05-25-session7.md) — 種スキーマ起草 + `monthly-shift-survey` draft + cron 実行ホスト=VPS確定 + Phase 3a/3b/3c 細分 + VPS secret 管理方針
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
