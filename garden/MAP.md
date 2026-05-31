# HMG 庭の見取り図

> **常に最新**。セッションごとに更新する。塚越さん(庭師)が「今どこにいるか」を1ページで把握するためのファイル。

## 一行で

HARAPPA Management Garden (HMG) は AI中心の経営運用プラットフォーム。
庭師=塚越さん、エージェント群=自律的に育つ生態系。HMC(操縦席)からの進化版(庭=育てる生態系)。

## 現在地 @2026-05-31

- **実装フェーズ**: S22 で **対話層の Garden 統合方針確定 + 記憶の三層分離 ADR + Stage A 着手 + 月初配信 dummy 化** を一気通貫。LINE 配信は garden-gaku-co 統合完了までの暫定として **dummy 経路**(Discord master に本文プレビュー → ガクチョ手動で LINE staff グループへ)に切替。Discord 対話の RAW logging が **11:38 から実稼働**(2026-06-01 月初配信は dummy で凌ぐ)
- **直近セッション**: [2026-05-31 セッション22](../docs/sessions/2026-05-31-session22.md) — **garden-gaku-co 統合方針 + 記憶三層分離 + Stage A + dummy 化**:報告(夜のレビュー / 朝のブリーフィングは Obsidian 連携含め OK)/ 方針確定(gaku-co5.0 と garden-gaku-co を **garden-gaku-co に統一されてからリリース**、入口=Discord/LINE 別・中身=Garden 単一)/ 記憶の構造軸見直し(S20 で見落とした「scope 軸 vs 意味軸の分断」)→ **三層分離 ADR**(RAW=scope/SOIL=意味/MEMORY WIKI=scope、soil は事実のみ、判断は memory に隔離)/ 3者間会話の扱い(@明示時のみ介入、主題別章立てで保持)/ 漏洩防御(物理境界 + 投影ビューは Stage D)/ **send_pending.py に dispatch_mode: dummy 実装**(`.env` SEND_PENDING_DEFAULT_MODE=dummy + board frontmatter 上書き)/ **memory_logger.py 新規 + bot.py 統合**(master/raw/{YYYY-MM-DD}.md に append、対話を捨てない最小実装)/ VPS 反映 + dummy 動作検証 OK(11:27 ダミー board → Discord master プレビュー流入 → processed/ 移動)+ RAW logging 動作検証 OK(11:38/11:39 の 2 turn 記録)
- **直近の重要決定**: **garden-gaku-co を統合後の本流名**として確定(gaku-co5.0 は撤退対象)/ **記憶の三層分離**(RAW・SOIL・MEMORY WIKI、配置軸が層で異なる)/ **soil には事実のみ**(判断・評価・意図は scope memory wiki に隔離=漏洩防御の主軸)/ **dummy 化の境界**(`status: approved` + `from_seed ∈ DISPATCH_LINE_SEND` のみ、test と shell 種は影響外)/ **bot 応答ポリシー**(発話には反応せず傍聴のみ、@ガクコ明示時のみ介入)/ **投影ビューは Stage D まで先送り**(Stage A〜C はガクチョ単独運用で漏洩リスクなし)
- **直近の宿題(最優先)**: **(5/31 22:00 本番初発火)** month-end-working-hours-prep が board 起草 → 集計実行 / **(6/1 19:00 dummy 配信)** 種2本 → Discord master に本文プレビュー流入 → ガクチョが手動で LINE staff グループへコピー / **(次セッション)** Stage A.5 着手(菌糸 Mode 1 = master RAW → soil + master memory wiki 振り分け実装)+ 菌糸 Stage 1(Mode 3 Index 更新)+ 統合 Stage 4(LINE webhook 受信を garden-gaku-co に追加)/ **(継続宿題)** NPM 認証懸念(統合 Stage 6 で同時解消予定)+ calendar token の 7 日後寿命確認(約 6/5)

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
| 種 (seeds) | [garden/seeds/](seeds/) | 🌱 | README + スキーマ拡張5項目 ADR + 案 E 正式 ADR + 本番ランチャー + **daily-pilot 3本 active 化(S15, cron 無人実証済)**。inbox-process / monthly-shift-survey は draft |
| サービス (services) | [garden/services/](services/) | 🌳 | **garden-couchdb(S10)+ mirror-daemon(S12)+ launcher(S13)+ writeback-daemon(S14/S15)+ garden-gaku-co(S16)+ calendar(S17)稼働中** |
| カレンダー calendar | [garden/services/calendar/](services/calendar/) | 🌳 | **S17: HMC の Google Calendar 認証を移植**(MCP 不要に)。token は Production 化後の再同意でクリーン発行。morning-briefing の📅欄に注入(launcher computed_inputs)。bot 対話でも利用予定 |
| 対話層 garden-gaku-co | [garden/services/garden-gaku-co/](services/garden-gaku-co/) | 🌳 | **S16 立ち上げ + S17 朝の対話 + S22 統合方針確定 + RAW logging 着手**:夜のレポート(22:40)+ 喋るガクコ(常駐)+ 朝の口火 morning_greet.py(06:40)+ 会話の書き戻し + **send_pending.py(S21)に dummy モード追加(S22、統合完了まで暫定)**+ **memory_logger.py 新規 + bot.py に RAW append 統合(S22 Stage A)**。次段 = Stage A.5 (菌糸 Mode 1 振り分け)/ Stage 4 LINE webhook 受信 / 統合最終 = gaku-co5.0 シャットオフ |
| 平文 MD ミラー | `~/garden-mirror/`(VPS) | 🌳 | **両方向同期完成(S14)**:CouchDB → MD = mirror-daemon、MD → CouchDB = writeback-daemon。LiveSync 互換 chunk ID 実装で Obsidian 完全反映 |
| 本番ランチャー | [garden/services/launcher/](services/launcher/) | 🌳 | **S13 完動 + S14 night-review 実走成功 + S15 で cron 無人実走を実証**(06:25/06:30 自動発火 → 完走 → Obsidian 反映)。cron 化済(06:25/06:30/22:30) |
| 書き戻し daemon | [garden/services/writeback-daemon/](services/writeback-daemon/) | 🌳 | **S14 完成 + S15 堅牢化**:reconcile scan backbone(`fs.watch` 取りこぼし対策)+ `_id` 小文字化(Case-Sensitive OFF)+ スコープ限定(`hmc_tasks/,garden/`)+ LiveSync E2EE 互換 chunk ID + ループ防止 |
| VPS 管理 | [vps/](../vps/) | 🌱 | **本 repo で正本管理開始(S11)**。proxy-manager / ig_scheduler / cron 構成ミラー + NPM backup 取得 + dev-flow + recovery 整備 |
| 共通規範 CHARTER | [garden/CHARTER.md](CHARTER.md) | 🌳 | **S20 新設**:全 plot SKILL 共通の業務観・呼称・トーン・Output Style 質感・Plot 間越境・soil 参照規約・創発取扱い。loader 機構なし(各 consumer が物理ロード) |
| 区画 (plots) | [garden/plots/](plots/) | 🌱 | **第1号 daily-pilot(S19)+ 第2号 shift_manager(S21)**:いずれも CHARTER 継承型 |
| 区画-daily-pilot | [garden/plots/daily-pilot/](plots/daily-pilot/) | 🌳 | **S19 立ち上げ / S20 CHARTER 継承化**:HMC hmc_pilot 起源 + Triage 3軸再設計 + active→backlog 反映 Mode 3 明示 + frontmatter `topics:` declare(越境 picker 用) |
| 区画-shift_manager ← **NEW** | [garden/plots/shift_manager/](plots/shift_manager/) | 🌱 | **S21 新設 plots 第2号**:CHARTER 継承 + Mode 1 月末準備 / Mode 2 シフト募集 / Mode 3 稼働確認 / Mode 4 シフト確定。HMC `apps/shift_manager/logic/` の2本を Garden 化(完全脱 HMC、残り 12 本は HMC 残置) |
| サービス-shift-manager ← **NEW** | [garden/services/shift-manager/](services/shift-manager/) | 🌳 | **S21 移植 + active**:generate_shift_form.py + generate_working_hours.py + import_kodomon.py + run_month_end_collect.sh + lib/freee_client(get_partners 最小版)+ utils + config(config_ids/section_mapping)+ secrets(600 perm)。VPS venv 構築 + API 疎通 OK |
| 種-shift_manager ← **NEW** | [garden/seeds/shift_manager/](seeds/shift_manager/) | 🌱 | **S21 種3本**:monthly-shift-survey v2(Garden 完結化) / month-end-working-hours-prep(新) / monthly-working-hours-confirmation(新、URL 方式)。すべて scheduled_send 19:00 + status:test テスト配信対応 |
| 配信ディスパッチャ ← **NEW** | [services/garden-gaku-co/send_pending.py](services/garden-gaku-co/send_pending.py) | 🌳 | **S21 新設(post_approval (4) C 案)**:cron 1分毎、board approved 検知 → from_seed で dispatch(LINE staff 配信 / shell 実行)、scheduled_send で時刻待機、status:test で personal LINE テスト配信 |
| 受け皿 inbox/kodomon ← **NEW** | [garden/inbox/kodomon/](inbox/kodomon/) | 🌱 | **S21 新設**:コドモン勤怠 CSV(Shift-JIS)の月次配置場所(`{YYYY-MM}.csv`)。月末 prep の集計実行で自動取込 → 放サボ列セルに反映 |
| 菌糸 (mycelium) ← **NEW** | [garden/mycelium/](mycelium/) | 🌱 | **S20 新設**(Garden 語彙追加):土壌維持エージェント。Mode 1 Ingest / Mode 2 Lint / Mode 3 Index 更新 / Mode 4 関係性編み直し。Stage 1(Mode 3)は shift_manager より先に実装予定 |
| 記憶 (memory) | [garden/memory/](memory/) | 🌱 | **S22 Stage A 着手**:三層分離 ADR 化(RAW=scope/SOIL=意味/MEMORY WIKI=scope、soil は事実のみ、判断は memory に隔離)+ master/raw/ で Discord 対話の RAW logging 稼働開始(11:38)+ .gitignore で raw 除外。次=Stage A.5 菌糸 Mode 1 振り分け / Stage B 夜間バッチ / Stage D LINE 統合 + 投影ビュー |
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
- [x] **night-review 副作用あり実走完動作**(S14)— 8件 archive、2件 backlog 追加、recur マーカー保持、既存 archive 規約準拠
- [x] **cron 化**(S14)— 06:25 recurring-spawn / 06:30 morning-briefing / 22:30 night-review、すべての daily-pilot cron 種が自動発火状態
- [x] **書き戻し経路完成 = writeback-daemon**(S14)— mirror-daemon と並列稼働、LiveSync 互換 chunk ID 実装、Obsidian 反映確認済
- [x] **cron 無人自動発火の実証 + writeback 堅牢化**(S15)— 06:25/06:30 が無人で完走 → Obsidian 反映。露見した 2 バグ(`fs.watch` 取りこぼし / Case-Sensitive OFF の `_id` 重複)を reconcile scan backbone + 小文字化 + スコープ限定で修正
- [x] **daily-pilot 3 本 正式 active 化**(S15)— recurring-spawn / morning-briefing / night-review。inbox-process は draft 据え置き(watcher daemon 待ち)
- [ ] **A-1 続き**: on_failure.retry の自動化・fallback の LINE 通知発火・audit の永続化整理
- [ ] **watcher daemon 実装**(event 種用、glob 監視 + board resume)
- [ ] **gaku-co5.0 側「LINE 返信 → board MD 書き戻し」処理を実装**
- [ ] **(今晩確認)** 22:30 night-review が 5/28 分を完全自律で実変換(完了 archive 転記 + active クリア + 翌日テンプレ)→ Obsidian 反映
- [ ] **バッドチャンク掃除**(writeback 初版の `h:` のみ orphan + S15 重複削除で参照されなくなった chunk の削除)
- [x] **Google Calendar 認証(S17)** — MCP ではなく HMC 認証を `garden/services/calendar/` に移植して解決。morning-briefing の📅欄に launcher computed_inputs で注入
- [x] **朝の対話(S17)** — 朝の口火 `morning_greet.py`(06:40)+ triage を active 最下段にミラー + bot の会話書き戻し(read-only 解除)。明朝が初のフル稼働ライブ
- [ ] **recurring_master.md のスキーマ確定 + 既存 recurring の棚卸し + 移行計画**

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

- [x] **`shift_manager/monthly-shift-survey` を active 化**(S21、Garden 完結 v2)
- [x] **`shift_manager/month-end-working-hours-prep` 起草 → active**(S21、新規)
- [x] **`shift_manager/monthly-working-hours-confirmation` 起草 → active**(S21、URL 方式採用)
- [ ] `shift_manager/monthly-shift-finalize` 起草 → active(構想止まり、aggregate_responses.py の Garden 移植後)
- [ ] finance 系・invoice_processor・expense_processor 等の種化

**注**: S21 時点で HMC 依存は撤廃済(generate_shift_form.py + generate_working_hours.py を Garden に移植 + 6/1 から HMC 並行運用回避合意)。Phase 3b の secret 管理は最小版で先行(secrets/ 600 perm 配置)、ハードニングは継続宿題。

#### 横断・後フェーズ

- [ ] 緊急 push の経路設計(ガクコ進化と同期)
- [ ] MCP server 実装(土壌へのアクセス層)
- [ ] 既存ソース(Square予約・Notion・Plaud)の ingest

### Phase 4: 区画の Garden 化 ← **S19 で前倒し着手(daily-pilot 第1号)/ S20 で CHARTER + 菌糸基盤整備**

HMC SKILL を順次 HMG に移植・自律化。S20 で「共通根 CHARTER + 土壌維持役 菌糸 + 永続記憶」の周辺設計が固まる。

- [x] **daily-pilot SKILL.md 新設**(S19) — HMC hmc_pilot 起源継承 + Garden 語彙再構築 + Triage 3軸再設計。5 経路を SKILL 参照型に
- [x] **Garden CHARTER 新設**(S20) — 全 plot SKILL 共通の業務観モジュール。daily-pilot SKILL は CHARTER 継承型に圧縮。トーン統一(ですます調)。[ADR](../docs/decisions/2026-05-30-garden-charter.md)
- [x] **菌糸(Mycelium)を Garden 語彙に追加 + ディレクトリ立ち上げ**(S20) — 土壌維持エージェント。[ADR](../docs/decisions/2026-05-30-mycelium-and-soil-reference.md)
- [x] **永続記憶の設計合意**(S20) — gaku-co5.0 memory システム(LLM Wiki 方式・スコープ分離)を移植。マスター透視権は Stage D で追加
- [x] **garden-gaku-co 統合方針 ADR**(S22) — 入口=Discord/LINE 別・中身=Garden 単一、garden-gaku-co を統合後の本流名に確定、Stage 0〜7 段階移行 [ADR](../docs/decisions/2026-05-31-garden-gaku-co-unification.md)
- [x] **記憶の三層分離 ADR**(S22) — RAW=scope/SOIL=意味/MEMORY WIKI=scope、soil は事実のみ、判断は memory に隔離、3者間会話の扱い、漏洩防御の設計 [ADR](../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md)
- [x] **永続記憶 Stage A 着手**(S22) — `garden/memory/master/raw/` で Discord 対話の RAW logging 稼働開始(memory_logger.py + bot.py 統合)
- [x] **dummy 化実装**(S22 Stage 0) — send_pending.py に dispatch_mode: dummy 追加、6/1 月初配信は Discord master プレビュー経由でガクチョ手動コピー運用
- [ ] **菌糸 Stage 1(Mode 3 Index 更新)実装** ← 次回着手(shift_manager より先 / 三層分離規約と整合する形で実装)
- [ ] **永続記憶 Stage A.5 実装**(菌糸 Mode 1 = master RAW → soil + master memory wiki 振り分け、三層分離 ADR §2 規約に従う)← 次回着手
- [ ] HMC SKILL の Garden 化(次候補: `shift_manager` SKILL 移植・Phase 3c 着手と同期 / 菌糸 Stage 1 完了が前提)
- [ ] HMC SKILL の Garden 化(finance_importer → invoice_processor → ...)
- [ ] 番人エージェントの実装(`garden/watchers/`)
- [ ] チームメンバー(LINE 経由)への開放準備(永続記憶 Stage D = マスター透視権実装と同期)

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
- [ ] **(継続)** **テスト残骸の整理** = LiveSync 削除イベント不帰問題として継続調査(Obsidian の "Deleted files" 設定 / LiveSync 設定の確認が必要)
- [x] **(済 S15)** ~~明朝 2026-05-28 の cron 自動発火結果確認~~ — 06:25/06:30 完走 → 2 バグ修正 → Obsidian 反映確認
- [x] **(済 2026-05-29・セキュリティ)** ~~COUCHDB_PASS の rotation~~ — `_config` API で変更、CouchDB/mirror/writeback/Obsidian PC・iPhone の 5 消費者へ反映、旧パス失効。記録: [incidents/2026-05-29_couchdb_pass_rotation.md](../docs/security/incidents/2026-05-29_couchdb_pass_rotation.md)
- [x] **(済 2026-05-30 S19)** ~~NPM UI から proxy host `n8n-harappa.duckdns.org` 削除~~ — 庭師作業完了
- [ ] **(改善余地)** LiveSync 用に非 admin 専用 CouchDB ユーザーを分離(現状は単一 admin 共有 = rotation 時 blast radius 大)
- [x] **(済 S17)** ~~Google Calendar MCP の VPS 認証~~ → MCP ではなく HMC 認証を `garden/services/calendar/` に移植して解決。token は Production 再同意でクリーン発行。明朝 06:30 の morning-briefing が📅欄を実際に埋めるのが初回ライブ確認
- [ ] **(継続・監視)** calendar token の寿命確認 — HMC は Production 化済だが、移植 token が Testing 由来の7日クロックを引きずっていないか(再同意済なので無期限のはず)。約7日後 6/5 も生きていれば確定
- [x] **(済 S19)** ~~reschedule(締切変更→backlog 編集)経路のライブ検証~~ — S17 sandbox 通過後、S17/S18 持ち越し3セッション分が S19 当日中の Discord 対話で自然消化。期限超過7件 + 追加3件が backlog/active に同期反映、bot 独自の `## 運営・企画(繰越)` セクション新設という先回りも観察

### Claude
- [ ] 次回セッション開始時に本 MAP.md + [S22 サマリ](../docs/sessions/2026-05-31-session22.md) + [統合方針 ADR](../docs/decisions/2026-05-31-garden-gaku-co-unification.md) + [記憶三層分離 ADR](../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md) + 6/1 19:00 dummy 配信の結果(Discord master プレビュー到達 + ガクチョ手動コピー実施)+ master/raw/ の蓄積状況を読む
- [x] 種の YAML スキーマ設計 + `monthly-shift-survey` draft(セッション7 完了)
- [x] daily-pilot 系 4種の draft 起草(セッション8 完了)
- [x] VPS 現状把握 + Claude Code 動作確認 + 最小ランチャー試作の cron 検証(セッション9 完了)
- [x] CouchDB + LiveSync 実装 + 三端末同期動作確認(セッション10 完了)
- [x] **Phase 3a A-3 平文 MD ミラー daemon 実装完了**(セッション12 完了)
- [x] **セッション13 で 5 本立て全走完了 + 続編で A-1 完動作**: A-1 ランチャー初版 + 連絡板 ADR + vault layout ADR + 案 E ADR + 拡張 5 項目 ADR + mirror-daemon 観察ログ + permission mode 確立 + mirror-daemon 権限修正 + recurring-spawn 副作用あり実走成功
- [x] **セッション14 で Phase 3a 最後のピース完成**: night-review 副作用あり実走 + cron 化 + writeback-daemon 実装 + LiveSync 互換 chunk ID 解析 + Obsidian 反映成功
- [x] **セッション15 で cron 無人実証 + writeback 堅牢化 + daily-pilot 3本 active 化宣言**
- [x] **セッション19 で plots 第1号 = daily-pilot SKILL.md 新設(355行) + 5経路振り替え + reschedule ライブ検証成功 + ADR 化**
- [x] **セッション22 で対話層統合方針確定 + 記憶三層分離 ADR + Stage A 着手 + 6/1 dummy 化**(send_pending.py + memory_logger.py + bot.py 統合 + VPS 反映 + 動作検証 OK)
- [ ] **次回本命候補(1)**: **菌糸 Stage 1 実装**(Mode 3 = soil/ 配下 watcher + index.md 自動追従。staff 29 名分の最新化 = shift_manager 着手の前提)
- [ ] **次回本命候補(2)**: **永続記憶 Stage A.5 実装**(菌糸 Mode 1 = master RAW → soil + master memory wiki 振り分け、三層分離 ADR §2 規約に従う)
- [ ] **次回本命候補(3)**: 統合 Stage 1〜3(memory 移植 → 夜間バッチ → bot context ロード、A.5 と並行 / 連動)
- [ ] **次回本命候補(4)**: SKILL+CHARTER 二段ロード稼働の継続観察(S20 〜 S22 で複数回稼働、トーン磨き込み判断)
- [ ] **次回本命候補(5)**: 次の区画 = HMC 移植第2号(finance / invoice_processor 等、菌糸 Stage 1 完了が前提)
- [ ] **次回本命候補(6)**: bot.py に plot ディスパッチャ実装(案 D の picker)— shift_manager + daily-pilot の topics 集約
- [ ] **次回本命候補(7)**: 統合 Stage 4(LINE webhook 受信を garden-gaku-co に追加、送信は当面 gaku-co5.0 経由のまま)
- [ ] **次回本命候補(8)**: watcher daemon 実装(event 種・inbox-process / board resume の入口)
- [ ] **次回本命候補(9)**: A-1 後追い(on_failure.retry の自動化・fallback LINE 通知発火)
- [ ] **次回本命候補(10)**: バッドチャンク掃除(`h:` で `+` がない orphan chunks の削除スクリプト)
- [ ] **workflow 書き直し残り(A 案テンプレ適用)**:
  - [ ] `garden/soil/workflows/annual-quarterly-planning.md`
  - [ ] `garden/soil/workflows/program-execution.md`
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
| archive 既存規約継続(`### YYYY/MM/DD (曜日)` + `**Completed Tasks:**` + `**Carried Over & Added:**`) | 2026-05-27 (S14) | [sessions/2026-05-27-session14.md](../docs/sessions/2026-05-27-session14.md) |
| LINE 通知は当面モック化(prompt で `==NOTIFY==` ブロックを log 末尾に書く)| 2026-05-27 (S14) | 同上 |
| 曜日表記は Claude が today から判定(VPS に ja_JP locale 不要) | 2026-05-27 (S14) | 同上 |
| 書き戻し経路 = 別 daemon (writeback-daemon)、mirror-daemon は触らない | 2026-05-27 (S14) | [decisions/2026-05-27-writeback-daemon-implementation.md](../docs/decisions/2026-05-27-writeback-daemon-implementation.md) |
| 単一 chunk 戦略(LiveSync は連結読みするので互換)+ フィードバック防止 = 内容比較 + chunk format 検証 | 2026-05-27 (S14) | 同上 |
| LiveSync 暗号化 chunk ID = `"h:+" + xxhash.h64(`piece-hashedPassphrase-length`).toString(36)` | 2026-05-27 (S14) | 同上 |
| Phase 3a daily-pilot cron 化(06:25 recurring-spawn / 06:30 morning-briefing / 22:30 night-review) | 2026-05-27 (S14) | [sessions/2026-05-27-session14.md](../docs/sessions/2026-05-27-session14.md) |
| writeback 検知 backbone = reconcile scan(`fs.watch` は経年取りこぼし、mtime scan 15s が source of truth) | 2026-05-28 (S15) | [decisions/2026-05-27-writeback-daemon-implementation.md](../docs/decisions/2026-05-27-writeback-daemon-implementation.md) |
| writeback `_id = path.toLowerCase()`(Case-Sensitive OFF 対応)+ スコープ `hmc_tasks/,garden/` 限定 | 2026-05-28 (S15) | 同上 |
| cron 無人実証完了をもって daily-pilot 3本 active 化(inbox-process は据え置き) | 2026-05-28 (S15) | [sessions/2026-05-28-session15.md](../docs/sessions/2026-05-28-session15.md) |
| gaku-co = Garden の対話層(接客)/ Garden = 奥座敷。真実は MD 一箇所、橋は mirror/writeback | 2026-05-28 (S16) | [decisions/2026-05-28-garden-gaku-co-interaction-layer.md](../docs/decisions/2026-05-28-garden-gaku-co-interaction-layer.md) |
| 頭脳はチャネル単位(ガクチョ=Discord+claude -p / チーム=gaku-co API / 社外=隔離)+ 内側/外側をデプロイ分離 | 2026-05-28 (S16) | 同上 |
| master チャネル = Discord(proactive push 無料無制限・表示・スレッド)/ garden-gaku-co は本 repo・最小ネイティブから育てる | 2026-05-28 (S16) | 同上 |
| ガクチョ呼称(音引きなし)を全プロジェクト共通で `~/.claude/CLAUDE.md` に記憶 | 2026-05-28 (S16) | [sessions/2026-05-28-session16.md](../docs/sessions/2026-05-28-session16.md) |
| 朝は対話型(夜レポートの朝版=一方向は作らない)/ 口火は gaku-co から声がけ 06:40 | 2026-05-29 (S17) | [sessions/2026-05-29-session17.md](../docs/sessions/2026-05-29-session17.md) |
| カレンダーは MCP でなく HMC 認証(`manage_calendar.py`)を `garden/services/calendar/` に移植 / launcher computed_inputs で prompt 注入 | 2026-05-29 (S17) | 同上 |
| calendar token は Production 再同意でクリーン発行(access=約1h・refresh=Production無期限)/ HMC とクライアント共有 | 2026-05-29 (S17) | [services/calendar/README.md](services/calendar/README.md) |
| bot 書き戻し = settings.json path-scoped(hmc_tasks/garden)・即書き＋軽い報告・Triage 全消化で確認・自動確定しない | 2026-05-29 (S17) | 同上 |
| 開発フロー = UX 先行(実装前に想定 UX を確認、当初計画＋高解像度 UX で方向確定)| 2026-05-29 (S17) | memory `ux-first-dev-flow` |
| 種(seed) と SKILL の責務分離(種 = 発火ディスパッチャ / SKILL = 業務観モジュール、モデル独立・チャネル独立) | 2026-05-30 (S19) | [decisions/2026-05-30-skill-and-seed-separation.md](../docs/decisions/2026-05-30-skill-and-seed-separation.md) |
| daily-pilot 区画 SKILL 新設 = plots 第1号(Phase 4 前倒し)+ HMC hmc_pilot を起源継承 + Triage 3軸(過ごし方提案 / AI 支援提案 / 判断ほしい)再設計 | 2026-05-30 (S19) | [plots/daily-pilot/SKILL.md](plots/daily-pilot/SKILL.md) |
| 5 経路(種2本 + bot + morning_greet + night_cheer)を SKILL 参照型に振り替え + active→backlog 反映ロジックを Mode 3 に明示 | 2026-05-30 (S19) | [sessions/2026-05-30-session19.md](../docs/sessions/2026-05-30-session19.md) |
| reschedule 経路(Discord 対話 → backlog/active 同期反映)のライブ検証成功 | 2026-05-30 (S19) | 同上 |
| **Garden CHARTER 新設** = 全 plot SKILL 共通の業務観モジュール(loader 機構なし・各 consumer が物理ロード) | 2026-05-30 (S20) | [decisions/2026-05-30-garden-charter.md](../docs/decisions/2026-05-30-garden-charter.md) |
| **ガクコ位置づけ再定義** = 「補佐」ではなく「Garden の中の存在 / 草木 / 木の精 / 庭師との橋渡し役」。役割名は固定しない | 2026-05-30 (S20) | 同上 |
| **トーン統一** = ですます調基本、過剰敬語 / Vice Pilot 表現は撤廃(HMC 由来語彙)、揺らぎ許容 | 2026-05-30 (S20) | 同上 |
| **plot 間越境ルール = 案 D**(独自 picker+loader、各 plot SKILL の frontmatter `topics:` を bot 起動時集約、越境発話は確認を挟む) | 2026-05-30 (S20) | [CHARTER.md](CHARTER.md) + memory `vendor-neutrality-skills` |
| **Claude Code 標準 Skills 機構は不採用**(ベンダー中立方針) | 2026-05-30 (S20) | memory `vendor-neutrality-skills` |
| **菌糸(Mycelium)を Garden 語彙に追加**(土壌維持エージェント、番人と兄弟ではない独立カテゴリ) | 2026-05-30 (S20) | [decisions/2026-05-30-mycelium-and-soil-reference.md](../docs/decisions/2026-05-30-mycelium-and-soil-reference.md) + [garden-vocabulary.md](../docs/garden-vocabulary.md) |
| **soil 参照規約** = 各 plot SKILL frontmatter で `requires_soil_index:` declare + index.md on-demand Read + soil 全体は同梱しない | 2026-05-30 (S20) | [CHARTER.md](CHARTER.md) |
| **既存 soil/index.md を菌糸の維持対象として位置づけ**(新 INDEX を作らず統合) | 2026-05-30 (S20) | [decisions/2026-05-30-mycelium-and-soil-reference.md](../docs/decisions/2026-05-30-mycelium-and-soil-reference.md) |
| **創発(SKILL 外の動き)の扱い** = 一過性で許容、庭師評価で SKILL 書き戻し、繰り返しは菌糸 Lint が拾う | 2026-05-30 (S20) | [CHARTER.md](CHARTER.md) |
| **永続記憶 = gaku-co5.0 memory システム移植**(LLM Wiki 方式・スコープ分離・RAW→WIKI 2 段・夜間バッチ・SQLite 不要) | 2026-05-30 (S20) | [sessions/2026-05-30-session20.md](../docs/sessions/2026-05-30-session20.md) |
| **マスター透視権** = bot.py(マスター)が下位スコープ index を読める、下位はマスターを読めない。Stage D で実装(チーム開放と同期) | 2026-05-30 (S20) | 同上 |
| **shift_manager Garden 完結化** = HMC `apps/shift_manager/logic/` の2本(generate_shift_form + generate_working_hours)+ freee_client(最小版)+ utils を Garden に移植。残り12本は HMC 残置で段階判断 | 2026-05-30 (S21) | [decisions/2026-05-30-shift-manager-garden-and-post-approval.md](../docs/decisions/2026-05-30-shift-manager-garden-and-post-approval.md) |
| **plots 第2号 = shift_manager SKILL.md** CHARTER 継承 + Mode 1〜4 + topics declare + requires_soil_index | 2026-05-30 (S21) | [plots/shift_manager/SKILL.md](plots/shift_manager/SKILL.md) |
| **post_approval 経路 = send_pending.py(C 案)** cron 1分毎 + status:test → personal LINE + scheduled_send で時刻待機 + from_seed dispatch | 2026-05-30 (S21) | 同上 |
| **Mode 3 稼働確認 = URL 方式**(LINE Bot API は PDF/file 直送不可、スクショ自動化はフォント崩れで品質保証困難 → スプシ URL 共有が現実解、過去月比較もできる) | 2026-05-30 (S21) | 同上 |
| **配信タイミング = 19:00 統一**(scheduled_send で時刻待機、シフト+稼働同時別メッセージ、スタッフ認知負荷低減) | 2026-05-30 (S21) | 同上 |
| **テスト配信 = status:test → personal LINE → status:pending に自動戻し**(本配信前の文面検証、何度でも繰り返し可) | 2026-05-30 (S21) | 同上 |
| **コドモン CSV 自動取込** = `garden-mirror/garden/inbox/kodomon/{YYYY-MM}.csv` (Shift-JIS) を月末 prep 集計実行で自動反映 → 放サボ列セルに業務時間 | 2026-05-30 (S21) | 同上 |
| **HMC 並行運用回避** = 5/31 以降は HMC 側 shift_manager 実行停止(OAuth race 防止、Garden に統一) | 2026-05-30 (S21) | 同上 |
| **garden-gaku-co 統合方針** = 入口=Discord/LINE 別・中身=Garden 単一、garden-gaku-co を統合後の本流名に確定(gaku-co5.0 は撤退対象)、Stage 0〜7 段階移行 | 2026-05-31 (S22) | [decisions/2026-05-31-garden-gaku-co-unification.md](../docs/decisions/2026-05-31-garden-gaku-co-unification.md) |
| **記憶の三層分離** = RAW(scope 軸)・SOIL(意味軸、事実のみ)・MEMORY WIKI(scope 軸、判断ログ)、配置軸が層で異なる | 2026-05-31 (S22) | [decisions/2026-05-31-memory-three-layer-and-soil-routing.md](../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md) |
| **soil には事実のみ書く**、判断・評価・意図は scope memory wiki に隔離(漏洩防御の主軸) | 2026-05-31 (S22) | 同上 |
| **3者間会話の扱い** = bot 宛/非宛問わず RAW、主題別章立てで memory wiki に整理、bot 応答は @明示時のみ(雑談に過剰反応しない) | 2026-05-31 (S22) | 同上 |
| **投影ビューは Stage D まで先送り**(Stage A〜C はガクチョ単独運用で漏洩リスクなし、Stage D = LINE 統合直前で実装) | 2026-05-31 (S22) | 同上 |
| **dummy 化(Stage 0)** = 6/1 月初配信は LINE に出さず Discord master プレビュー → ガクチョが手動で LINE staff グループへコピー(garden-gaku-co 統合完了までの暫定) | 2026-05-31 (S22) | [decisions/2026-05-31-garden-gaku-co-unification.md](../docs/decisions/2026-05-31-garden-gaku-co-unification.md) |
| **永続記憶 Stage A 着手** = `garden/memory/master/raw/` で Discord 対話の RAW logging 開始、memory_logger.py 経由で bot.py から append | 2026-05-31 (S22) | [memory/README.md](memory/README.md) |

## 直近のセッション

- [2026-05-31 セッション22](../docs/sessions/2026-05-31-session22.md) — **garden-gaku-co 統合方針 + 記憶三層分離 + Stage A 着手 + 6/1 dummy 化**:報告(夜のレビュー / 朝のブリーフィングは Obsidian 連携含め OK)→ 方針確定(gaku-co5.0 と garden-gaku-co を **garden-gaku-co に統一されてからリリース**、入口=Discord/LINE 別・中身=Garden 単一)→ 記憶の構造軸見直し(S20 で見落とした「scope 軸 vs 意味軸の分断」)→ **三層分離 ADR**(RAW=scope/SOIL=意味/MEMORY WIKI=scope、soil は事実のみ、判断は memory に隔離、3者間会話の扱い、漏洩防御=投影ビューは Stage D)→ **send_pending.py に dispatch_mode: dummy 実装**(`.env` SEND_PENDING_DEFAULT_MODE=dummy + board frontmatter 上書き)→ **memory_logger.py 新規 + bot.py に append_turn 統合**(master/raw/{YYYY-MM-DD}.md、対話を捨てない最小実装)→ VPS 反映 + dummy 動作検証 OK(11:27 ダミー board → Discord master プレビュー → processed/ 移動)+ RAW logging 動作検証 OK(11:38/11:39 の 2 turn 記録)
- [2026-05-30 セッション21](../docs/sessions/2026-05-30-session21.md) — **shift_manager Garden 化 + 月末月初 active 化**:S20 周辺設計が固まった直後、5/31 月末日 → 6/1 月初を Garden で動かすために一気通貫実装。plots 第2号 SKILL.md(CHARTER 継承)+ HMC `apps/shift_manager/logic/` の2本(generate_shift_form + generate_working_hours)+ freee_client(最小版)+ utils を Garden に移植 + 種3本(monthly-shift-survey v2 + month-end-working-hours-prep + monthly-working-hours-confirmation)+ **post_approval 経路 = send_pending.py(cron 1分毎、(4) C 案、scheduled_send + status:test テスト配信対応)**+ **コドモン CSV 自動取込(import_kodomon.py + run_month_end_collect.sh)**+ VPS 配置・credentials・API 疎通検証・cron 4本仕込み完了。Mode 3 = URL 方式(LINE Bot API は PDF 直送不可、スクショ自動化はフォント崩れリスク)/ 配信時刻 = 6/1 19:00 統一(シフト+稼働同時、ガクチョの作業時間確保)/ HMC 並行運用回避合意 / NPM 認証懸念は継続宿題
- [2026-05-30 セッション20](../docs/sessions/2026-05-30-session20.md) — **CHARTER 化 + 菌糸新設 + 創発取扱い + 永続記憶設計**:S19 で daily-pilot SKILL を立てた直後、shift_manager 着手前の周辺設計 5 論点(SKILL 共通パーツ / plot 間越境 / soil 参照規約 / 創発取扱い / 永続記憶)を一気に整理。CHARTER 新設(全 plot 継承)+ ガクコ位置づけ再定義(橋渡し役・木の精)+ トーン統一(ですます調)+ 案 D(独自 picker+loader、Claude Code 標準 Skills 不採用=ベンダー中立)+ **菌糸(Mycelium)を Garden 語彙に追加**(土壌維持エージェント、Stage 1 から段階着手)+ 創発の評価駆動書き戻し + **永続記憶 = gaku-co5.0 移植**(LLM Wiki 方式・スコープ分離・SQLite 不要、マスター透視権は Stage D で追加)。実装は次回以降に段階着手
- [2026-05-30 セッション19](../docs/sessions/2026-05-30-session19.md) — **朝の体感改善 + SKILLベース化(plots 第1号) + reschedule ライブ検証成功**:朝チェーン初フル稼働の体感4課題(振り返り漏れ / 表示 / Triage 構成 / 締めの一言)を、(1)短期対応3つ +(2)**SKILL ベース化**(daily-pilot SKILL.md 355行新設 + 5経路を SKILL 参照型に振り替え)+(3)古い triage board 退避 +(4)ADR 化(種 = 発火ディスパッチャ / SKILL = 業務観モジュール)で根本治療。当日中に **reschedule ライブ検証成功**(S17/S18 持ち越し3セッション消化)
- [2026-05-29 セッション18](../docs/sessions/2026-05-29-session18.md) — **COUCHDB_PASS rotation + 旧 n8n 撤去 + 明朝チェーン事前点検**:3セッション持ち越しの最優先セキュリティ債を返済(`_config` API・5消費者全反映・host local.ini 永続・旧失効)。派生で旧 n8n を完全撤去(~320M shred 後削除 + 履歴 scrub、残=NPM proxy host 削除)。明朝5/30 初ライブに向け朝チェーンを点検し改善2点を発見(bot の古 Triage 誤認 / morning_greet ヘッダ厳格)→ 実装は明朝観察後に繰り越し
- [2026-05-29 セッション17](../docs/sessions/2026-05-29-session17.md) — **朝の対話を立ち上げ**:「朝のガクコ連絡が届かない」=未実装の発見 → 朝は対話型に決定。カレンダー認証を HMC から移植(MCP 不要化)、triage を active 最下段にミラー(#1)、朝の口火 morning_greet.py 06:40(#2)、bot の会話書き戻し=read-only 解除(#3/#4・sandbox 検証→本番)。開発フロー UX 先行を memory 記録
- [2026-05-28 セッション16](../docs/sessions/2026-05-28-session16.md) — **gaku-co を Garden の対話層に統合(ADR)+ garden-gaku-co 立ち上げ**:夜のレポート(振り返り完了 + 件数 + 正常/異常確認 + ひとこと、cron 22:40)+ 喋るガクコ(Discord 常駐・オンライン・claude -p 脳・read-only)を一晩で稼働。ペルソナ G-gaku-co(中性的・理知的)
- [2026-05-28 セッション15](../docs/sessions/2026-05-28-session15.md) — **cron 無人実証 + writeback 堅牢化 + active 化宣言**:06:25/06:30 が無人で完走 → Obsidian 反映を実証 / 露見した 2 バグ(`fs.watch` 取りこぼし / Case-Sensitive OFF の `_id` 重複)を reconcile scan + 小文字化 + スコープ限定で修正 / **daily-pilot 3本を draft → active 化**
- [2026-05-27 セッション14](../docs/sessions/2026-05-27-session14.md) — **Phase 3a 最後のピース完成**:night-review 副作用あり実走完動作 / morning-briefing dry-run / cron 設定 / **書き戻し経路実装(writeback-daemon)** / LiveSync 互換 chunk ID 仕様解析 + 実装 / **Obsidian 反映成功** → 種 → VPS → CouchDB → LiveSync → Obsidian の循環完成
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
