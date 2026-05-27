# HMG 庭の見取り図

> **常に最新**。セッションごとに更新する。塚越さん(庭師)が「今どこにいるか」を1ページで把握するためのファイル。

## 一行で

HARAPPA Management Garden (HMG) は AI中心の経営運用プラットフォーム。
庭師=塚越さん、エージェント群=自律的に育つ生態系。HMC(操縦席)からの進化版(庭=育てる生態系)。

## 現在地 @2026-05-27

- **設計フェーズ**: 土壌の最小実装(Phase 1)+ 種 draft 5本 + **Phase 3a A-3 完了(mirror-daemon)** + **Phase 3a A-1 完動(本番ランチャー実装 + permission mode 確立 + recurring-spawn が backlog.md への書き込みまで完走)** + **ADR 4 本まとめ**
- **直近セッション**: [2026-05-27 セッション13](../docs/sessions/2026-05-27-session13.md) — 1 セッションで 5 本立てを全走:案 E と スキーマ拡張 5 項目を正式 ADR 化 / vault 内 Garden フォルダ配置 ADR / board 構造 ADR / 既存 draft パス統一(`/opt/garden` → `/home/vps-harappa/garden-mirror/`) / 本番ランチャー実装(`garden/services/launcher/`)+ VPS deploy + recurring-spawn 実走で claude -p が種を完全実行 / mirror-daemon 運用観察項目整理
- **直近の重要決定**: 既存 `hmc_tasks/` リネームせず流用(daily-pilot 種の I/O 先確定)/ 種ファイルは vault ミラーしない(repo + scp deploy)/ `garden/board/` は `pending` / `processed` / `triage` の 3 系統 / ランチャーは Node.js + 自前 YAML パーサ(最小依存)/ 案 E と 5 項目を正式昇格

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
| 種 (seeds) | [garden/seeds/](seeds/) | 🌱 | README + **スキーマ拡張5項目 ADR 化(S13)** + draft 5本(全パス基準統一済)+ **案 E 正式 ADR(S13)** + **本番ランチャー初版 + VPS 実走 OK(S13)** |
| サービス (services) | [garden/services/](services/) | 🌱 | **garden-couchdb(S10)+ garden-mirror-daemon(S12)+ garden-launcher(S13)稼働中** |
| 平文 MD ミラー | `~/garden-mirror/`(VPS) | 🌱 | **58 ファイル同期中 + ライブ更新 OK + 連続編集追従 OK(S12-13)**。`hmc_tasks/` 既存 + `garden/` 新設方針確定(S13)。daemon = [garden/services/mirror-daemon/](services/mirror-daemon/) |
| 本番ランチャー | [garden/services/launcher/](services/launcher/) | 🌱 | **S13 初版:frontmatter パース + 並行制御 + 状態永続化 + VPS deploy + recurring-spawn 実走で claude -p が種を完全に読み解いた**(書き込みは permission mode 待ち) |
| VPS 管理 | [vps/](../vps/) | 🌱 | **本 repo で正本管理開始(S11)**。proxy-manager / ig_scheduler / cron 構成ミラー + NPM backup 取得 + dev-flow + recovery 整備 |
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
- [x] **VPS 現状把握 + Claude Code v2.1.150 動作確認 + 最小ランチャー試作の cron 検証 OK**(2026-05-25 セッション9)
- [x] **A-2: VPS CouchDB + Obsidian LiveSync 実装完了**(2026-05-25 セッション10)— PC ↔ iPhone ↔ VPS 三端末リアルタイム同期動作
- [x] **A-3: 平文 MD ミラー daemon 実装完了**(2026-05-27 セッション12)— [garden/services/mirror-daemon/](services/mirror-daemon/) 稼働中、56 ファイル初期同期 + ライブ同期動作確認
- [x] **A-1: 本番ランチャー実装(初版)+ VPS 実走検証**(2026-05-27 セッション13)— [garden/services/launcher/](services/launcher/) で frontmatter パース・並行制御・状態永続化・dry-run。recurring-spawn 実走で claude -p が種を完全実行(書き込みは permission mode 判断待ち)
- [x] **連絡板 `garden/board/` 構造設計 ADR**(セッション13)— pending / processed / triage の 3 系統、テンプレ、ライフサイクル、書き戻し経路の保留明示
- [x] **gakuchovault 内 Garden フォルダ設計 ADR**(セッション13)— `hmc_tasks/` リネームせず流用、`garden/` 新設、種ファイルは vault ミラーしない
- [x] **スキーマ拡張 5 項目 + 案 E の正式 ADR 化**(セッション13)— 暫定 → 正式へ昇格、既存 draft の改善余地表も「検討済」に更新
- [x] **既存 draft 5本のパス統一**(セッション13)— `/opt/garden/...` → `/home/vps-harappa/garden-mirror/{hmc_tasks,garden}/...`
- [x] **claude -p permission mode 確立**(セッション13 続き)— `~/.claude/settings.json` で `Write/Edit/Read` を `hmc_tasks/` `garden/` に path-scoped allow
- [x] **mirror-daemon 権限修正**(セッション13 続き)— `user: "1000:1000"` 追加 + 既存ファイル `chown -R vps-harappa:vps-harappa`、daemon が host vps-harappa として書き出すように
- [x] **vault 内 `garden/` 新設**(セッション13 続き)— `garden/{README.md, board/{pending,processed,triage}, inbox/{processed,archive}, log}/` 一式 created。`.archive` は Obsidian で作成不可だったため `archive/` に統一
- [x] **`hmc_tasks/recurring_master.md` に id 後付け**(セッション13 続き)— 15 件全部に `<!-- id:rNNN -->` 振り済
- [x] **recurring-spawn 副作用あり実走完動作確認**(セッション13 続き)— `## 定期` セクション新設 + `r001 暗号資産の相場確認` 書き込み成功 🎉
- [ ] **A-1 続き**: on_failure.retry の自動化・fallback の LINE 通知発火・audit の永続化整理
- [ ] **watcher daemon 実装**(event 種用、glob 監視)
- [ ] **gaku-co5.0 側「LINE 返信 → board MD 書き戻し」処理を実装**
- [ ] **書き戻し経路の確定**(mirror-daemon 双方向化 vs CouchDB 直書き)
- [ ] **recurring_master.md のスキーマ確定 + id 後付け + 既存 recurring の棚卸し + 移行計画**
- [ ] **vault に `garden/` フォルダを新設**(塚越さん側で実施 → LiveSync 反映)
- [ ] daily-pilot 4本の active 化

#### Phase 3b: HMC の VPS 移植 + secret 管理設計

- [x] **VPS 管理体制の確立(セッション11)** — `vps/` ディレクトリ + ガクコ系/その他系の2系統分離 + NPM backup 取得スクリプト
- [ ] **NPM backup の定期実行化**(週次 cron で `vps/proxy-manager/export.sh` を回す)
- [ ] **NPM backup の logs 除外**(現状 272 ファイル中の多くがログ。`export.sh` に `--exclude='data/logs/*'` 追加)
- [ ] **secret の外部 storage 二重化**(現状ローカル WSL のみ。1Password / 暗号化 zip 等)
- [ ] **VPS スナップショット自動化**(`docker ps` / `df -h` / 構成差分の cron 取得 → `vps/snapshots/`)
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
- [ ] (継続) VPS 信頼性課題(Docker 停止)対処の優先度判断 — uptime 172日からは安定気配
- [ ] (継続) Obsidian LiveSync 採用後の Dropbox 同期方式の扱い(残すか整理するか)
- [ ] (継続) スキーマ拡張 5 項目の正式 ADR 化判断
- [ ] (継続) monthly period 表現の柔軟性方針
- [ ] (継続) 既存 recurring の recurring_master.md への移行計画
- [ ] (継続) `~/codex-auth.json` の用途確認(Garden で不要なら削除)
- [ ] (継続) subscription auth の同時セッション制限が問題になった時の API key 移行判断
- [ ] **(継続)** iPhone 旧 vault(Dropbox 経由)の整理(`gakuchovault-ls` 検証後、削除可否判断)
- [x] **(済)** Phase 3a 次回着手の優先順位判断 — セッション13 で 5 本立てを全走 (A-1 / 連絡板 / vault layout / 案 E ADR / 拡張5項目 ADR + mirror-daemon 観察)
- [x] **(済)** claude -p の permission mode = B 案(settings.json で path-scoped allow)で確定
- [x] **(済)** vault 内 `garden/` フォルダ新設(Obsidian 作業完了)
- [x] **(済)** `hmc_tasks/recurring_master.md` に id 後付け(15 件)
- [ ] **(新)** **テスト残骸の整理** = LiveSync 削除イベント不帰問題として継続調査(Obsidian の "Deleted files" 設定 / LiveSync 設定の確認が必要)

### Claude
- [ ] 次回セッション開始時に本 MAP.md + 直近セッション(13)サマリ + 2026-05-27 ADR 4 本 + [garden/services/launcher/README.md](services/launcher/README.md) + [garden/services/mirror-daemon/OPERATION-LOG.md](services/mirror-daemon/OPERATION-LOG.md) を読む
- [x] 種の YAML スキーマ設計 + `monthly-shift-survey` draft(セッション7 完了)
- [x] daily-pilot 系 4種の draft 起草(セッション8 完了)
- [x] VPS 現状把握 + Claude Code 動作確認 + 最小ランチャー試作の cron 検証(セッション9 完了)
- [x] CouchDB + LiveSync 実装 + 三端末同期動作確認(セッション10 完了)
- [x] **Phase 3a A-3 平文 MD ミラー daemon 実装完了**(セッション12 完了)
- [x] **セッション13 で 5 本立て全走完了 + 続編で A-1 完動作**: A-1 ランチャー初版 + 連絡板 ADR + vault layout ADR + 案 E ADR + 拡張 5 項目 ADR + mirror-daemon 観察ログ + permission mode 確立 + mirror-daemon 権限修正 + recurring-spawn 副作用あり実走成功
- [ ] **次回本命候補(1)**: morning-briefing と night-review を **実走検証**(recurring-spawn と同じ流れで)。発火は cron 化(`crontab -e` で 06:25 / 06:30 / 22:30)
- [ ] **次回本命候補(2)**: watcher daemon 実装(inbox-process / morning-briefing resume 用)
- [ ] **次回本命候補(3)**: gaku-co5.0 側「LINE 返信 → board MD 書き戻し」連携(書き戻し経路の確定とセット)
- [ ] **次回本命候補(4)**: A-1 の後追い実装(on_failure.retry の自動化・fallback LINE 通知)
- [ ] **次回本命候補(5)**: vault に `garden/` フォルダ新設 + `hmc_tasks/recurring_master.md` に id 後付け
- [ ] **workflow 書き直し残り(A 案テンプレ適用)**:
  - [ ] `garden/soil/workflows/annual-quarterly-planning.md`
  - [ ] `garden/soil/workflows/program-execution.md`
- [ ] gaku-co5.0 側「LINE 返信 → board MD 書き戻し」の連携仕様(Phase 3a)
- [ ] (継続) `docs/security/README.md` の VPS 環境向け拡張(Phase 3b)
- [ ] (継続) docker-compose v2 plugin 化(Phase 3b で sudo と一緒に)

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
| VPS Claude Code v2.1.150 + subscription auth + cron→claude -p→ログ のエンドツーエンド成立 | 2026-05-25 (S9) | [sessions/2026-05-25-session9.md](../docs/sessions/2026-05-25-session9.md) |
| ランチャーは `~/.npm-global/bin/claude` フルパス必須(ssh 非対話 / cron で .bashrc 非読込み) | 2026-05-25 (S9) | 同上 |
| 試作領域 `garden/seeds/.scratch/` 導入(本番ランチャー設計が固まったら削除) | 2026-05-25 (S9) | 同上 |
| VPS 現状の正本 = [docs/vps/current-state.md](../docs/vps/current-state.md)(新設) | 2026-05-25 (S9) | 同上 |
| 既存 vault `gakuchovault` をそのまま LiveSync 化(Remotely Sync 無効化、Dropbox 放置) | 2026-05-25 (S10) | [decisions/2026-05-25-couchdb-livesync-implementation.md](../docs/decisions/2026-05-25-couchdb-livesync-implementation.md) |
| CouchDB を NPM の external network に参加させる 2NIC 方式(Garden サービス追加の標準パターン) | 2026-05-25 (S10) | 同上 |
| E2EE オン + Path/Properties Obfuscation OFF(VPS daemon が平文 MD を扱う前提) | 2026-05-25 (S10) | 同上 |
| Chunk size = 60 / Case-Sensitive = OFF / Per-file Customisation Sync = ON(診断ツール推奨) | 2026-05-25 (S10) | 同上 |
| 端末追加は必ず Setup URI 方式(passphrase 入力ミス防止 + 方向選択ミス回避) | 2026-05-25 (S10) | 同上 |
| docker-compose v1.29 互換のため `version: '3.8'` + `-p garden-couchdb` | 2026-05-25 (S10) | 同上 |
| NPM パスワードリセットは `bcrypt`(`bcryptjs` ではない)+ ハッシュ長 assertion 必須 | 2026-05-25 (S10) | 同上 |
| iPhone は新規 vault `gakuchovault-ls` で Fetch(既存 vault は触らず、ダメージ 0 戦略) | 2026-05-25 (S10) | 同上 |
| VPS 管理は本 repo `vps/` で集約(ハラッパ直結 + ig_scheduler) | 2026-05-26 (S11) | [decisions/2026-05-26-vps-management-policy.md](../docs/decisions/2026-05-26-vps-management-policy.md) |
| ガクコは別 repo 継続、本 repo からは参照リンクのみ(submodule 不採用) | 2026-05-26 (S11) | 同上 |
| NPM 内部 DB は定期 export(`vps/proxy-manager/export.sh`)→ 本 repo `backups/` に保管(git 除外) | 2026-05-26 (S11) | 同上 |
| VPS ↔ ローカル の root 所有ファイル取得は alpine コンテナ経由(sudo 不要パターン化) | 2026-05-26 (S11) | 同上 |
| 開発フロー2系統: (a) ガクコ系=GitHub 経由 / (b) その他=本 repo + scp/rsync | 2026-05-26 (S11) | [vps/dev-flow.md](../vps/dev-flow.md) |
| mirror-daemon は単方向(CouchDB → MD)から始める | 2026-05-27 (S12) | [decisions/2026-05-27-mirror-daemon-implementation.md](../docs/decisions/2026-05-27-mirror-daemon-implementation.md) |
| 実装は Node.js + octagonal-wheels 直接利用(自前実装しない) | 2026-05-27 (S12) | 同上 |
| LiveSync の `%=` プレフィックスは HKDF + AES-GCM。PBKDF2 salt は `_local/obsidian_livesync_sync_parameters` doc に格納 | 2026-05-27 (S12) | 同上 |
| mirror 配置 = VPS `/home/vps-harappa/garden-mirror/` / MD のみスコープ | 2026-05-27 (S12) | 同上 |
| Garden サービス追加パターンの 2 例目: `garden-couchdb_default` external network 参加 | 2026-05-27 (S12) | 同上 |
| 案 E(recur マーカー)を正式 ADR 化 + recurring_master の `id:` 必須化 | 2026-05-27 (S13) | [decisions/2026-05-27-recurring-respawn-prevention.md](../docs/decisions/2026-05-27-recurring-respawn-prevention.md) |
| 種スキーマ拡張 5 項目を正式 ADR 化(暫定 → 正式) | 2026-05-27 (S13) | [decisions/2026-05-27-seed-schema-extensions.md](../docs/decisions/2026-05-27-seed-schema-extensions.md) |
| vault 内 `hmc_tasks/` リネームせず流用 + `garden/` 新設 + 種ファイルは vault ミラーしない | 2026-05-27 (S13) | [decisions/2026-05-27-vault-folder-layout.md](../docs/decisions/2026-05-27-vault-folder-layout.md) |
| `garden/board/` は `pending` / `processed` / `triage` の 3 系統 + 配信本文セクション切り出し規約 | 2026-05-27 (S13) | [decisions/2026-05-27-garden-board-structure.md](../docs/decisions/2026-05-27-garden-board-structure.md) |
| 本番ランチャー(`garden/services/launcher/`)初版 = Node.js + 自前 YAML パーサ + flock + state.json | 2026-05-27 (S13) | [sessions/2026-05-27-session13.md](../docs/sessions/2026-05-27-session13.md) |
| 種ファイル基準パス = `/home/vps-harappa/garden-mirror/`(`/opt/garden` 系を一掃) | 2026-05-27 (S13) | [decisions/2026-05-27-vault-folder-layout.md](../docs/decisions/2026-05-27-vault-folder-layout.md) |

## 直近のセッション

- [2026-05-27 セッション13](../docs/sessions/2026-05-27-session13.md) — **5本立て全走**:案 E + 拡張5項目 を正式 ADR 化 / vault layout ADR / board structure ADR / 既存 draft パス統一 / **本番ランチャー初版 + VPS 実走で claude -p が種を完全実行** / mirror-daemon 運用観察ログ
- [2026-05-27 セッション12](../docs/sessions/2026-05-27-session12.md) — **Phase 3a A-3 完了: 平文 MD ミラー daemon 実装**(`garden-mirror-daemon` 稼働、56 ファイル初期同期 + ライブ更新動作確認)
- [2026-05-26 セッション11](../docs/sessions/2026-05-26-session11.md) — **VPS 管理体制確立**(`vps/` ディレクトリ + ガクコ系/その他系の2系統分離 + NPM backup 初回取得)
- [2026-05-25 セッション10](../docs/sessions/2026-05-25-session10.md) — Phase 3a A-2 完了: CouchDB + Obsidian LiveSync 三端末同期動作開始
- [2026-05-25 セッション9](../docs/sessions/2026-05-25-session9.md) — VPS 現状把握 + Claude Code v2.1.150 動作確認 + 最小ランチャー試作(cron→claude -p→ログ)エンドツーエンド成立
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
