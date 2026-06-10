# HMG 庭の見取り図

> **常に最新**。セッションごとに更新する。塚越さん(庭師)が「今どこにいるか」を1ページで把握するためのファイル。
>
> **日々の運用早見表(業務カード・移行表・通知役割)は [`garden/OPERATIONS.md`](OPERATIONS.md) に分離(2026-06-02 セッション25)**。MAP は戦略地図、OPERATIONS は運用盤、という役割分担。

## 一行で

HARAPPA Management Garden (HMG) は AI中心の経営運用プラットフォーム。
庭師=塚越さん、エージェント群=自律的に育つ生態系。HMC(操縦席)からの進化版(庭=育てる生態系)。

## 現在地 @2026-06-10

- **プロジェクトレビュー → 改善バッチ(S39)**: 4観点レビュー(効率/構造/運用/セキュリティ)→ 同セッションで改善実施。(1) **番人(Watcher)新設・active** = `garden/services/watcher/`、cron `*/10` でログのエラー検知 + ハートビート(`.heartbeat-*` マーカー)で cron 沈黙(S36型)を Discord 通知。Phase 2「VPS 信頼性 watcher」前倒し消化(2) **secret 防御** = 実体 6 ファイル chmod 600 + pre-commit フック(secret スキャン/実行ビット検査/ドリフト検査、`core.hooksPath` 設定済)。**git 漏洩はゼロを検証済み**(履歴含む。キーローテ不要)(3) **shell injection 対策** = send_pending.py `execute_command` を allowlist + `shell=False` 化(4) **freee client 統一** = 正本 `garden/lib/freee_client.py` + コピー同期方式。429リトライ/token共有reload(潜在バグ修正)/マスターキャッシュ。VPS 実証 GREEN(5) 実行ビット地雷 3 本修正(`run-line-container.sh` 等が 644 のままだった)+ crontab.snapshot 全面更新(9→17本の陳腐化解消)(6) ADR 2本 = [命名規約](../docs/decisions/2026-06-10-naming-convention.md)(既存リネームせず)/ [PII 案A](../docs/decisions/2026-06-10-pii-in-private-repo.md)。詳細 = [session39](../docs/sessions/2026-06-10-session39.md)
- **expense_processor active 後の改善3本(S38)**: S37 で active 化した区画の実運用改善。(1) **費目分類のバッチ化**(CSV を複数行1プロンプト→JSON配列で順序復元 / 画像 OCR を `ThreadPoolExecutor` 並列 / `time.sleep(2)` 撤去。S37 の 77 件タイムアウト対策。失敗時はその範囲だけ1行フォールバック)(2) **「経費まわして」配線 = Route A**(bot に scoped Bash。`--disallowedTools` から Bash 解放 + `settings.json` で expense venv python を **絶対パス `:*` 形式**で scoped allow + timeout 300s。⚠️ **gotcha: Claude Code の Bash 権限は絶対パス `:*` のみマッチ、`cd &&`・相対・末尾` *` は拒否** → bot/SKILL/種/execute_command を全部絶対パス化。read-only `taxes` で実地検証 → **ガクチョ Discord 実テストで完璧に機能**)(3) **件数多い月の直接編集 = Google Sheets(案A)**:`lib/sheets_client.py`(gspread + 同 SA、ガクチョ所有ワークブックに `{YYYYMM}` タブ・費目プルダウン・要確認黄色)+ `to-sheet`/`from-sheet`。extract→to-sheet→board→Sheet URL通知 / 承認→from-sheet→dry-run→登録。`EXPENSE_REVIEW_SHEET_ID`(ガクチョ作成 → SA に Editor 共有)。**合成6行でラウンドトリップ GREEN**(要確認保持・amount=0 行スキップ)。**残 = 本番1周(件数多めの月)をガクチョが見届け**(今回はガクチョ都合で次回)。詳細 = [session38](../docs/sessions/2026-06-08-session38.md)
- **expense_processor Phase 2 → cron まで(S37・本命)**: S35 で draft 起草した区画を **service 移植 → VPS デプロイ → secret 配置 → エンドツーエンド dry-run → 種2本 active → cron 登録**まで一気通貫。`garden/services/expense-processor/`(processor.py + lib/freee_client フル + drive_client + utils)。⭐secret = Drive **service account**(`harappa-drive-bot@…`、HMC creds 流用)/ Freee は **shift-manager と物理ファイル共有**(`FREEE_TOKEN_FILE`、refresh ローテ対策)/ Gemini key・Drive folder ID。**tax_code = `136`(課対仕入10%)** を `processor.py taxes` で確定(HMC 既定 1=課税 の誤り是正)。dry-run で `Tax=136`・5費目マッチ・skip 0 を確認。**移植バグ3件修正**:① `gemini-2.0-flash` 退役(404)→ 全件 `消耗品費` フォールバックを `gemini-2.5-flash` で修正(**HMC 側も壊れているはず**)② launcher の `$(...)` 限定展開で `target_month_jp`/`drive_folder_id` 未展開 → 修正。**残 = 初回リアル実走**(ガクチョの実明細待ち)で draft→active。VPS python3-venv 無 → `--without-pip`+get-pip。詳細 = [session37](../docs/sessions/2026-06-08-session37.md)
- **shift 集計スクリプト移植(S37)**: ガクコ打診「7月シフト集計のスクリプトが Garden に無い」→ `aggregate_responses.py` を `garden/services/shift-manager/` に移植 + **7月分を実集計(12件/11名 → `Shift_Work_2026-07`)**。認証は既存 SA がそのまま(Forms scope 追加)、config は HMC 一致で既に揃い。バグ2件(死スタブ / `datetime.timezone`)修正。SKILL Mode 4 を「移植済」に更新。**Mode 4 全体(種 finalize)は未だ構想、集計単体は手動利用可**。
- **障害対応(S36)**: 6/5 夜から Discord の**夜の振り返り(night-cheer 22:40)/ 朝のブリーフィング(morning-greet 06:40)が停止**。原因は **S34 の LINE デプロイ `rsync -a` が repo の実行ビット無し(`100644`)を VPS に伝播し、`run-{bot,morning-greet,night-cheer}.sh` を Permission denied で沈黙させた**こと(ガクチョの「LINE テストが引き金では」が的中)。VPS 即時 `chmod +x` + 手動 morning-greet で今朝分投稿 + **repo を `100755` に修正(根本原因)** + DEPLOY.md に注意書き。`bot.py` 本体は生存していたが keepalive も死んでおり危うい状態だった。commit `7902988`。詳細 = [session36](../docs/sessions/2026-06-06-session36.md)
- **plot_gardener 初 dogfood フェーズ(S35)**: メタ区画 `plot_gardener`(S33)を初めて実業務に当てた。**shift_manager** は「master/Discord 完結・既に完成・触らない」と**即分類して早期撤退**(= 作らないと決めるのも plot_gardener の正しい使い方)。**expense_processor** は transplant をフル一周 → **SKILL + 種2本(Phase 1)を起草**(月末リマインド[Drive URL つき]→ 翌月2日抽出[空ならスキップ]→ Discord 承認で Freee 登録、手動「経費まわして」でも回る)。**scope 固定点を memory 化**:LINE 1:1 = core_staff パイロット / **master = Discord 一本、LINE に master 回路を開かない**(→ master 業務の read tool は LINE registry に作らない)。別件で recurring_master `r005` を新フローに整合(VPS ライブ正本を三段+backup で直編集)。**残 = Phase 2(service 移植 + ⭐secret 配置[ガクチョ console]+ cron + dry-run → active 昇格)**。SKILL = [expense_processor](plots/expense_processor/SKILL.md)
- **デプロイ + 疎通フェーズ(S34)**: S32 でローカル GREEN 化した**社内 LINE サーバ(core_team)を本番 VPS にデプロイ完了 + ガクチョと 1:1 会話 GREEN**。途中、VPS の **iptables が docker→ホストを DROP** していてホストプロセス方式が塞がれていると判明 →**コンテナ化(`garden-gaku-core` を `proxy-manager_default` に載せ NPM からコンテナ名で到達)に方針転換**([ADR](../docs/decisions/2026-06-05-line-server-containerization.md))。NPM ログイン不能を **bcrypt 安全リセット**(SSH トンネルで UI 開通)、DNS は **Xserver**(Vercel でなく、`core.harappa.monster → 162.43.40.86`)+ Let's Encrypt、**tool-use の 400 バグ**(assistant の tool_use ブロック欠落)を provider/respond で修正。**テスト用エアギャップ例外 `LINE_TEST_USER_IDS`**(既定空)でガクチョ個人 1:1 のみ通す。**本番グループ投入(groupId 確定)はあえてテスト先行で残**:この後テスト環境で区画(plot)の read tool を実装→確認してから本番昇格する流れ。Runbook = [DEPLOY.md](services/garden-gaku-co/DEPLOY.md)
- **設計フェーズ(S33)**: 測量士の手紙を起点に**「業務を Garden 化する型」を確立**。語彙を **2 register**(設計言語=区画/種/通行手形 vs 実装層=tool/service、水面下)に整理 → **capability を Garden 語彙「通行手形」に昇格** → **メタ区画 `plot_gardener` をフル本番化**(Mode 1〜6、transplant/seedling/hybrid、移植型は Legacy Inventory から)。測量士の 5 提案すべて採用 → [ADR 化](../docs/decisions/2026-06-04-plot-gardener-and-vocabulary-registers.md) + 手紙に応答記入。**ガクチョが渡すのは「業務名 / mode / MVP」の 3 つだけ、tool 粒度は水面下で Garden が選ぶ**。出先のため repo 内ドキュメントのみで完結(VPS 反映なし)。**dogfood 第 1 号(shift_manager / expense_processor / core_team read tool 群)は次セッションで選定 → plot_gardener test→active**。
- **実装フェーズ(S32)**: 社内 LINE サーバ(core_team)を実装・ローカル検証 GREEN。中立基盤(S31)の **上に** gate(Stage1 Haiku)→ respond(Stage2 + tool-use)→ LINE webhook(FastAPI)を gaku-co5.0 から「**アダプタ集約しながら**」移植(`import anthropic` は provider.py だけ)。**エアギャップ = core_team group のみ通す許可リスト**、**情報境界 = capability(行動)+ context(知識)の両輪**。smoke 2 本 + FastAPI TestClient で HTTP 経路まるごと検証 GREEN(正規→応答 / 社外→無視 / 個人→無視 / 署名不正→403 / RAW 記録)。**デプロイ(VPS + NPM + secret 記入 + Verify + グループ追加)はガクチョのコンソール操作待ちで宿題化**(出先のためセッションを閉じた)。Runbook = [DEPLOY.md](services/garden-gaku-co/DEPLOY.md)
- **今朝の cron 検証**: consolidate-wiki 03:51 cron 初稼働 ✅GREEN / night-cheer 22:40(S28 修正後)✅GREEN / ingest-raw `==NOTIFY==` は未処理 RAW 0 件で⏳保留(材料待ち)
- **直近セッション**: [2026-06-10 セッション39](../docs/sessions/2026-06-10-session39.md) — **プロジェクトレビュー(4観点)→ 改善バッチ**:番人(Watcher)新設 active / pre-commit secret 防御 / execute_command allowlist 化 / freee client 統一(429リトライ + token 共有 reload + キャッシュ、VPS 実証 GREEN)/ 実行ビット地雷 3 本修正 / crontab.snapshot 更新 / ADR 2本(命名規約・PII 案A)。git 漏洩ゼロ検証済み
- [2026-06-08 セッション38](../docs/sessions/2026-06-08-session38.md) — **expense_processor active 後の改善3本**:(1) 費目分類バッチ化(CSV 複数行1プロンプト + 画像 OCR 並列、S37 タイムアウト対策)(2) 「経費まわして」配線 = Route A(bot に scoped Bash、絶対パス `:*` 形式が肝、Discord 実テスト完璧)(3) 件数多い月の直接編集 = Google Sheets 案A(`sheets_client.py` + to-sheet/from-sheet、ラウンドトリップ GREEN)。残 = 本番1周をガクチョが次回見届け
- [2026-06-08 セッション37](../docs/sessions/2026-06-08-session37.md) — **expense_processor Phase 2 → cron まで + shift 集計移植**:(1) expense service 移植 → VPS デプロイ(`--without-pip`+get-pip)→ secret(Drive SA / Freee 共有 token / Gemini)→ tax_code 136 確定 → 合成データで dry-run GREEN → 種2本 active + cron2行。移植バグ3件(gemini-2.0-flash 退役 / launcher `$()` 限定展開 ×2)修正(2) `aggregate_responses.py` を shift-manager に移植 + 7月分実集計(12件/11名 → `Shift_Work_2026-07`)+ バグ2件修正。残 = expense 初回リアル実走で draft→active
- [2026-06-06 セッション36](../docs/sessions/2026-06-06-session36.md) — **Discord 夜/朝の停止を修復**:S34 の LINE デプロイ `rsync -a` が repo の `100644` を VPS に伝播 → `run-{bot,morning-greet,night-cheer}.sh` が Permission denied で沈黙。VPS chmod +x + 手動 morning-greet 投稿 + repo を `100755` に修正(根本原因)+ DEPLOY.md 注意書き。bot.py は生存も keepalive 死で危うい状態だった。commit `7902988`
- [2026-06-05 セッション35](../docs/sessions/2026-06-05-session35.md) — **plot_gardener 初 dogfood**:(1) shift_manager を「master/Discord 完結・完成済・触らない」と即分類 → 早期撤退(2) **expense_processor を transplant フル一周** = Legacy Inventory → Garden Design(①種+手動 / ②Discord 直 upload / scope=master 構造遮断)→ **Phase 1 実装(SKILL + 種2本、全 draft)**(3) memory 固定点(LINE 1:1=core_staff パイロット / master=Discord 一本)(4) recurring_master r005 を新フローに整合(VPS ライブ正本を三段+backup で直編集)。残=Phase 2(service 移植 + secret + cron + dry-run → active)
- [2026-06-05 セッション34](../docs/sessions/2026-06-05-session34.md) — **社内 LINE サーバを本番 VPS にデプロイ + 1:1 疎通 GREEN**:(1) rsync + コンテナ化(firewall で host-process が塞がれ → `garden-gaku-core` を `proxy-manager_default` に。`Dockerfile.line` + `run-line-container.sh`、compose v1 は `ContainerConfig` バグで不可)(2) ⭐secret 記入(nano swap で一度失敗 → 再保存)(3) ⭐DNS(Xserver)+ ⭐NPM Proxy Host + Let's Encrypt(ログイン不能 → SSH トンネル + bcrypt 安全リセット)(4) ⭐Webhook Verify 200(5) tool-use 400 バグ修正(provider/respond)(6) `LINE_TEST_USER_IDS` でガクチョ 1:1 のみ通す → 会話 GREEN。本番グループは次フェーズ
- [2026-06-04 セッション33](../docs/sessions/2026-06-04-session33.md) — **業務 Garden 化の型(plot_gardener)+ 語彙 2 register**:測量士の手紙 5 提案を全採用。(1) 語彙合意=「業務のパック=区画」「tool は水面下の実装層、語彙表に載せない」「capability→通行手形に昇格」(2) `garden-vocabulary.md` に 2 register 節 + 通行手形(3) `plot_gardener/SKILL.md` フル本番化(4) `OPERATIONS.md` Card 5(5) `CLAUDE.md` に節追加(6) 手紙応答記入 + ADR。出先のため repo 内のみ。dogfood 第 1 号は次回選定
- [2026-06-04 セッション32](../docs/sessions/2026-06-04-session32.md) — **社内 LINE サーバ実装 + ローカル検証 GREEN**:(0) cron 3 件検証(2 GREEN / 1 材料待ち)(1) 測量士の手紙 2 通確認 → ガクチョ「A が先、plot_gardener は A 後」判断(2) **道 A 実装** = brain/gate.py + brain/respond.py + line/{signature,sender,context,app}.py + persona/core-team.md + requirements-line + run-line-server.sh + .env.example 更新(3) smoke 2 本 + TestClient で HTTP 経路検証 GREEN(4) デプロイ Runbook DEPLOY.md 作成 → ガクチョ宿題化
- [2026-06-03 セッション31](../docs/sessions/2026-06-03-session31.md) — **ガクコ社内 LINE 参加の方針確定 + ベンダー中立 ADR + 中立基盤(smoke GREEN)+ LINE チャネル開設**:gaku-co5.0 が社外も担うと判明 → 社外/社内エアギャップへ。頭脳=チーム b(API Haiku)。「ベンダー中立=アダプタ 1 枚で隔離」を ADR 化。中立基盤 brain/provider + tools/registry + capabilities を実装
- [2026-06-03 セッション30](../docs/sessions/2026-06-03-session30.md) — **永続記憶 3 ステージ active + SKILL 動的再読み込み**:launcher 1.0.1(`--model`)+ 菌糸 Mode 5 Consolidate + 種 consolidate-wiki(03:50・haiku)+ Stage C(bot.py に memory wiki+過去3日 RAW+当日 RAW を context ロード)+ mtime 動的キャッシュ 3 クラスで CHARTER/SKILL/PERSONA/memory を bot 再起動なしで反映。永続記憶が「対」+「縦」で揃った
- [2026-06-03 セッション30](../docs/sessions/2026-06-03-session30.md) — **永続記憶 3 ステージ active + SKILL 動的再読み込み**:launcher 1.0.1(`--model`)+ 菌糸 Mode 5 Consolidate + 種 consolidate-wiki(03:50・haiku)+ Stage C(bot.py に memory wiki+過去3日 RAW+当日 RAW を context ロード)+ mtime 動的キャッシュ 3 クラスで CHARTER/SKILL/PERSONA/memory を bot 再起動なしで反映。永続記憶が「対」+「縦」で揃った
- [2026-06-03 セッション29](../docs/sessions/2026-06-03-session29.md) — **memory 正本ルール ADR + path 大移動チェックリスト + board 掃除**:コールドスタートから 3 案件を A→B→C で完遂。**A**: ADR 新規 + memory-sync 2 本(pull/push)+ README + memory README に正本ルール表追記 + CLAUDE.md セッションプロトコル更新 + dry-run / 実走検証 OK。**B**: OPERATIONS.md §5 新章(コード/設定/種/ドキュメント/daemon/完了検証 の 6 層 + 5 分後ふりかえり、既存 §5 は §6 へ繰り下げ)。**C**: failed の `2026-06-01-monthly-shift-survey.FAILED.md` に resolution フィールド追加(S24 で再キック本配信成功済を明示)+ quarantine 2 件削除(`_test-dummy.md` / `2026-06-02-dummy-test-s27.md`)
- **直近の重要決定**: S34 ADR [2026-06-05 line-server-containerization](../docs/decisions/2026-06-05-line-server-containerization.md)(firewall 制約で LINE サーバはコンテナ化 + `docker run` 運用 + テスト用エアギャップ例外 `LINE_TEST_USER_IDS` + tool-use 400 修正)。土台は S31 ADR [2026-06-03 vendor-neutral-interaction-layer](../docs/decisions/2026-06-03-vendor-neutral-interaction-layer.md)(実装順序「2」を S32→S34 で消化)。正本は [2026-05-28 決定4](../docs/decisions/2026-05-28-garden-gaku-co-interaction-layer.md)
- **直近の宿題(最優先)**: **(expense)** ✅① Discord「経費まわして」配線(S38 Route A 済)/ ✅② 費目分類バッチ化(S38 済)/ ✅ 件数多い月の直接編集 = Sheets 案A(S38 済、ラウンドトリップ GREEN)→ **残 = 本番1周(件数多めの月)をガクチョが見届け**(extract → Sheet 編集 → 承認 → Freee 登録)/ **(plot_gardener)** expense 初回実走完了 → test→active 昇格判断 / **(shift Mode 4)** `aggregate_responses.py` 移植済(S37)。種 `monthly-shift-finalize` draft 起草が残(集計単体は手動利用可) / **(LINE 本番昇格)** core_team 本来の read tool を選定してから ⭐本番グループ投入 → groupId 確定 → `.env`(`LINE_CORE_TEAM_GROUP_ID` + `LINE_TEST_USER_IDS` 空)→ `run-line-container.sh`(手順 = [DEPLOY.md](services/garden-gaku-co/DEPLOY.md) §8) / **(掃除)** 廃止 `run-line-server.sh` / `venv-line` 物理削除判断 / **(継続)** calendar token 寿命 / 測量士の次回手紙 / ingest-raw `==NOTIFY==` 初検証 / kura 整備 / **(S39 レビュー残)** `google.generativeai`→`google.genai` 移行(deprecated 警告)/ plot_gardener SKILL に[命名 ADR](../docs/decisions/2026-06-10-naming-convention.md)参照追記 / root 残置物(`main_menu.py`・`clean.py`・`docs_legacy/`・`development/`)の `_archive/` 整理 / launcher unit test / 番人の朝ブリーフィング統合

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
| 種 (seeds) | [garden/seeds/](seeds/) | 🌱 | README + スキーマ拡張5項目 ADR + 案 E 正式 ADR + 本番ランチャー + **daily-pilot 3本 active(S15)+ shift_manager 種3本 active(S21)+ mycelium/index-refresh active(S23)+ mycelium/ingest-raw active(S26、03:30)+ mycelium/consolidate-wiki active(S30、03:50、haiku-4-5)**。inbox-process は draft |
| サービス (services) | [garden/services/](services/) | 🌳 | **garden-couchdb(S10)+ mirror-daemon(S12)+ launcher(S13)+ writeback-daemon(S14/S15)+ garden-gaku-co(S16)+ calendar(S17)稼働中** |
| カレンダー calendar | [garden/services/calendar/](services/calendar/) | 🌳 | **S17: HMC の Google Calendar 認証を移植**(MCP 不要に)。token は Production 化後の再同意でクリーン発行。morning-briefing の📅欄に注入(launcher computed_inputs)。bot 対話でも利用予定 |
| 対話層 garden-gaku-co | [garden/services/garden-gaku-co/](services/garden-gaku-co/) | 🌳 | **S16 立ち上げ + S17 朝の対話 + S22 統合方針確定 + RAW logging 着手 + S27 Discord 承認運用化 + S30 永続記憶 + 動的キャッシュ + S31 中立基盤(brain/tools/capabilities)+ 社内 LINE 方針確定**:夜のレポート(22:40)+ 喋るガクコ(常駐)+ 朝の口火 morning_greet.py(06:40)+ 会話の書き戻し + dummy モード + memory_logger + S27: list_pending_boards + board_facts.py + notify_pending 強化 + **S30: bot.py に永続記憶ロード(memory wiki + 過去3日 RAW + 当日 RAW、30000 chars cap)+ `_FileCache` / `_DirCache` / `_MemoryPastRawCache` で CHARTER/SKILL/PERSONA/memory 全部 mtime 動的キャッシュ化(編集 → 次 turn で反映、bot 再起動不要)**。**S32: 社内 LINE サーバ実装(brain/gate + brain/respond + line/{signature,sender,context,app} + persona/core-team)= 中立基盤の上に gate→respond→webhook、エアギャップ(core_team group のみ)+ 情報境界(capability + context 両輪)、ローカル検証 GREEN。**S34: 本番 VPS にデプロイ完了 + ガクチョ 1:1 疎通 GREEN**(firewall で host-process 不可 → コンテナ `garden-gaku-core` 化、`core.harappa.monster` + Let's Encrypt、tool-use 400 修正、`LINE_TEST_USER_IDS` でテスト先行)。Runbook = [DEPLOY.md](services/garden-gaku-co/DEPLOY.md)、[S34 ADR](../docs/decisions/2026-06-05-line-server-containerization.md)。本番グループ投入は残** / **gaku-co5.0 は撤退でなく「社外専用デプロイ」へ分離継続**(デジタル原っぱ大学 / AIBOU LAB・Garden とエアギャップ、[S31 ADR](../docs/decisions/2026-06-03-vendor-neutral-interaction-layer.md)) |
| 平文 MD ミラー | `~/garden-mirror/`(VPS) | 🌳 | **両方向同期 + S27 board/log 隔離**:CouchDB → MD = mirror-daemon、MD → CouchDB = writeback-daemon。LiveSync 互換 chunk ID。**S27: EXCLUDE_PREFIXES 機構**(`garden/board/`, `garden/log/` を mirror-daemon の fs 書き出し / writeback-daemon の CouchDB push 両方から完全隔離)→ vault は知識ベース(soil/inbox/memory)のみに |
| board/log VPS 領域 ← **NEW** | `/home/vps-harappa/garden/{board,log}/`(VPS) | 🌳 | **S27 新設**:LiveSync 完全隔離。`board/` = pending/processed/failed/triage/quarantine(承認運用は Discord ガクコ経由)/ `log/` = launcher / cron / send-pending / morning-greet 等の集約。**唯一の書き手 / 読み手は VPS スクリプト**、別端末からの巻き戻しは構造的にゼロ |
| 本番ランチャー | [garden/services/launcher/](services/launcher/) | 🌳 | **S13 完動 + S14 night-review 実走成功 + S15 で cron 無人実走を実証 + S30 で 1.0.1 拡張**(`execute.model` frontmatter → `claude -p --model {model}` で渡す、claude-haiku-4-5 等を種別に指定可能)。cron 化済(06:25/06:30/22:30/03:00/03:30/03:50) |
| 書き戻し daemon | [garden/services/writeback-daemon/](services/writeback-daemon/) | 🌳 | **S14 完成 + S15 堅牢化**:reconcile scan backbone(`fs.watch` 取りこぼし対策)+ `_id` 小文字化(Case-Sensitive OFF)+ スコープ限定(`hmc_tasks/,garden/`)+ LiveSync E2EE 互換 chunk ID + ループ防止 |
| VPS 管理 | [vps/](../vps/) | 🌱 | **本 repo で正本管理開始(S11)**。proxy-manager / ig_scheduler / cron 構成ミラー + NPM backup 取得 + dev-flow + recovery 整備 |
| 共通規範 CHARTER | [garden/CHARTER.md](CHARTER.md) | 🌳 | **S20 新設**:全 plot SKILL 共通の業務観・呼称・トーン・Output Style 質感・Plot 間越境・soil 参照規約・創発取扱い。loader 機構なし(各 consumer が物理ロード) |
| 区画 (plots) | [garden/plots/](plots/) | 🌱 | **第1号 daily-pilot(S19)+ 第2号 shift_manager(S21)+ メタ区画 plot_gardener(S33)+ 第3号 expense_processor(S35)**:いずれも CHARTER 継承型 |
| 区画-plot_gardener | [garden/plots/plot_gardener/](plots/plot_gardener/) | 🌱 | **S33 新設(メタ区画)**:業務を区画化する型。Mode 1〜6(Intake/Legacy Inventory/Workflow Spec/Garden Design/Implementation Plan/Review&Promotion)+ transplant/seedling/hybrid。測量士サンプル起点。状態 **test**(**S35 で初 dogfood = shift_manager 早期分類 + expense_processor フル一周。Phase 2 初回実走を見届けて active 判断**)。[ADR](../docs/decisions/2026-06-04-plot-gardener-and-vocabulary-registers.md) |
| 区画-expense_processor | [garden/plots/expense_processor/](plots/expense_processor/) | 🌳 | **S35 新設 → S37 active → S38 実運用配線**:Mode 1 月末リマインド / Mode 2 抽出→Sheets→board / Mode 3 承認→from-sheet→dry-run→Freee 登録。**scope=master 構造遮断**。状態 **active**(S37 初回実走 59件 ¥397,373)。**S38: Discord「経費まわして」配線(Route A = bot scoped Bash・絶対パス `:*` 形式)+ 件数多い月の Sheets 直接編集(案A)**。残=本番1周(Sheets 経由)をガクチョが見届け |
| サービス-expense-processor | [garden/services/expense-processor/](services/expense-processor/) | 🌳 | **S37 移植 → S38 改善**:processor.py(extract/upload/taxes/**to-sheet/from-sheet**)+ lib/freee_client + drive_client + **sheets_client(S38、gspread)** + utils。Drive=SA / Freee token=shift 共有 / Gemini=`gemini-2.5-flash` / tax_code 136。**S38: 費目分類バッチ化 + 画像 OCR 並列化 + Sheets レビュー(`EXPENSE_REVIEW_SHEET_ID`)**。data/secret は VPS のみ |
| 種-expense_processor | [garden/seeds/expense_processor/](seeds/expense_processor/) | 🌱 | **S35 種2本 → S37 active + cron 登録**:month-end-reminder(28-31日19:00)/ monthly-expense-draft(2日08:00)。computed_inputs の `$()` 限定展開バグ修正済(`*_jp` / `drive_folder_id`) |
| 区画-daily-pilot | [garden/plots/daily-pilot/](plots/daily-pilot/) | 🌳 | **S19 立ち上げ / S20 CHARTER 継承化 / S25 今日フィルタ明示化 / S27 承認応答ルート追加**:HMC hmc_pilot 起源 + Triage 3軸再設計 + active→backlog 反映 + frontmatter `topics:` declare + S25 「deadline ≦ today」明示 / **S27: Mode 2 編集権限表に shift_manager 系 board 承認/テスト/却下/編集ルートを追加**(詳細は shift_manager Mode 5 を Read)+ 任意 board の「board 見せて」ルート |
| 区画-shift_manager | [garden/plots/shift_manager/](plots/shift_manager/) | 🌱 | **S21 新設 plots 第2号 + S27 Mode 5 新設**:CHARTER 継承 + Mode 1 月末準備 / Mode 2 シフト募集 / Mode 3 稼働確認 / Mode 4 シフト確定 / **Mode 5 Discord Approval Response**(Discord 自然言語の承認指示 → board frontmatter Edit、対象 board 特定ロジック + 編集の安全規範 + 失敗時挙動)。HMC `apps/shift_manager/logic/` の2本を Garden 化 + S27 で既存タブガード(`--force-regenerate` + `_has_saboru_data`)+ CSV パス検出強化 |
| サービス-shift-manager | [garden/services/shift-manager/](services/shift-manager/) | 🌳 | **S21 移植 + active / S37 aggregate 追加**:generate_shift_form.py + generate_working_hours.py + import_kodomon.py + **aggregate_responses.py(S37、Forms 回答集計、Mode 4 Step 1)** + run_month_end_collect.sh + lib/freee_client + utils + config + secrets(600)。VPS venv + API 疎通 OK。**S37 で 7 月シフト実集計(12件/11名 → `Shift_Work_2026-07`)** |
| 種-shift_manager ← **NEW** | [garden/seeds/shift_manager/](seeds/shift_manager/) | 🌱 | **S21 種3本**:monthly-shift-survey v2(Garden 完結化) / month-end-working-hours-prep(新) / monthly-working-hours-confirmation(新、URL 方式)。すべて scheduled_send 19:00 + status:test テスト配信対応 |
| 配信ディスパッチャ | [services/garden-gaku-co/send_pending.py](services/garden-gaku-co/send_pending.py) | 🌳 | **S21 新設 + S24 大幅拡張 + S25 連続失敗ガード + S27 通知強化 + path 切替**:cron 1分毎、status: approved 検知 → dispatch、status: pending → 承認依頼通知、shell 種成功時 → 連鎖 confirmation の unblock、scheduled_send 待機、status:test テスト配信、fail_count + auto-quarantine。**S27: notify_pending 強化(配信本文プレビュー + 関連 URL + 客観事実 + Discord 操作ガイド、build_pending_notice / extract_known_urls / extract_checklist 追加)+ env default を新パス `/home/vps-harappa/garden/{board,log}/`** |
| 受け皿 inbox/kodomon | [garden/inbox/kodomon/](inbox/kodomon/) | 🌳 | **S21 新設 + S24 運搬路確立**:コドモン勤怠 CSV(Shift-JIS)の月次配置場所。ファイル名柔軟化(`{YM}.csv` / `{YYYYMM}.csv` / glob)。WSL cron で repo → VPS rsync(α)、γ(Discord アップロード)将来構想 |
| CSV 運搬サービス ← **NEW** | [services/kodomon-sync/](services/kodomon-sync/) | 🌳 | **S24 新設(経路 α)**:WSL crontab `*/5 * * * *` で repo/garden/inbox/kodomon/ → VPS の inbox/kodomon/ に rsync。コドモンの自然なファイル名のまま運搬 |
| board failed/ ← **NEW** | [garden/board/failed/](board/failed/) | 🌱 | **S24 新設(4 系統体制)**:種 on_failure 経路 board の隔離先。べき等性ガードのグロブから外して再キック可能に。`{name}.FAILED.md` 命名 |
| 菌糸 (mycelium) | [garden/mycelium/](mycelium/) | 🌳 | **S23 Stage 1 + S26 A.5 + S30 Stage B が全 active**:SKILL.md(Mode 1〜5、**Mode 5 Consolidate を S30 新設**)+ 種 index-refresh(03:00、Stage 1 = soil index 維持)+ ingest-raw(03:30、Stage A.5 = RAW → soil + wiki 振り分け)+ **consolidate-wiki(03:50、Stage B = wiki index 再生成 + 重複/矛盾検出 + 14 日 RAW archive、本文 append-only 厳格、haiku-4-5)**。残: Mode 2 Lint(Stage 2、shift_manager 安定後)/ Mode 4 関係性編み直し(Stage 4) |
| 土壌-soil 全体配置 | vault + garden-mirror + repo | 🌳 | **S23 vault 化 → S26 正本ルール明文化**:S23 で 3 箇所配置(cp/scp 初期配置)→ S26 で正本ルール ADR + `garden/services/soil-sync/` pull/push スクリプト 2 本 + セッションプロトコル化。**repo = 構造ファイル正本 / VPS = 菌糸ログ正本 / vault = 読み取り専用ビュー** |
| 同期スクリプト soil-sync ← **NEW** | [garden/services/soil-sync/](services/soil-sync/) | 🌳 | **S26 新設**:`pull-from-vps.sh`(VPS → repo、セッション開始時)+ `push-to-vps.sh`(repo → VPS、セッション終了時)+ README。LiveSync ↔ rsync を組み合わせた 3 箇所同期(vault は LiveSync 自動)。ADR [2026-06-02](../docs/decisions/2026-06-02-soil-source-of-truth.md) |
| 同期スクリプト memory-sync ← **NEW** | [garden/services/memory-sync/](services/memory-sync/) | 🌳 | **S29 新設(soil-sync の対称設計)**:`pull-from-vps.sh` + `push-to-vps.sh` + README。差分は `--exclude='*/raw/*.md'` のみ(raw は VPS 専属 + .gitignore 除外、構造的に repo に流れない)。ADR [2026-06-03](../docs/decisions/2026-06-03-memory-source-of-truth.md) |
| 記憶 (memory) | [garden/memory/](memory/) | 🌳 | **S22 Stage A → S26 A.5 → S29 正本ルール → S30 Stage B + Stage C で 4 段全部 active**:三層分離 ADR + master/raw/ RAW logging + .gitignore で raw 除外 + S23 4 論点 + S26 ingest-raw active(VPS cron 03:30、RAW 単位冪等)+ S29 正本ルール ADR(構造ファイル=repo / wiki=VPS 主・repo 従 / raw=VPS 専属)+ memory-sync 2 本 + **S30: consolidate-wiki active(03:50、wiki index 再生成 + archive)+ Stage C 永続記憶(bot 起動時に wiki + 過去 3 日 RAW を context ロード、mtime 動的キャッシュで 03:30 / 03:50 の結果が次 turn 反映)+ 03:34 ingest-raw 初収穫実績 + 13:42 consolidate-wiki 初回実走実績(index 再生成、重複/矛盾 0、archive 0)**。次=Stage D(LINE 統合 + 下位 scope RAW + 投影ビュー + マスター透視権、チーム公開時) |
| 番人 (watchers) | [garden/services/watcher/](services/watcher/) | 🌱 | **S39 新設 + active**:cron `*/10` でログのエラー検知(オフセット差分)+ ハートビート(`.heartbeat-*`)で cron 沈黙(S36型)検出 → Discord master 通知。セルフテスト GREEN。残: 朝ブリーフィング統合・相互監視 |
| 苗床 (nursery) | garden/nursery/ | ⬜ | 試行領域 |
| 蔵 (kura) | garden/kura/ | ⬜ | 長期アーカイブ |
| 測量士(外部視点)← **NEW** | [docs/surveyor/](../docs/surveyor/) | 🌱 | **S25 新設**:codex を外部視点 AI として導入。庭の縁から定期俯瞰 → `letters/YYYY-MM-DD.md` で手紙 → Claude Code が同ファイルに応答セクション追記。実装はしない。ADR [2026-06-02](../docs/decisions/2026-06-02-surveyor-role.md) |

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
- [x] **VPS 信頼性 watcher の設計**(Garden 共通課題、番人候補)→ **S39 で番人(log-watcher)として実装・active**([garden/services/watcher/](../garden/services/watcher/))

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
- [x] **菌糸 Stage 1(Mode 3 Index 更新)実装**(S23 active、6/1 03:00 初稼働確認済)
- [x] **board ライフサイクル完成 + 承認依頼通知 + 連鎖解除 + 朝のリマインド統合**(S24) — settings.json Bash 許可、send_pending.py に notify_pending + unblock_confirmation、board/failed/ 新設、morning-briefing Step 1.5、ADR [2026-06-01](../docs/decisions/2026-06-01-board-lifecycle-and-notification.md)
- [x] **放サボ自動取込のフルパス開通**(S24) — generate_working_hours.py の致命バグ修正、import_kodomon.py ファイル名柔軟化、kodomon-sync(α)経路新設
- [x] **永続記憶 Stage A.5 active 化**(S26) — wiki ディレクトリ + index 雛形 + ingest-raw 種 active + RAW 単位の冪等性確立 + crontab 03:30 仕込み + dry-run 4 回完走
- [x] **board/log を Obsidian vault 外へ + Discord ガクコ承認運用 + daemon EXCLUDE_PREFIXES**(S27) — 放サボ上書き事故対応から構造改革:`garden-mirror/garden/{board,log}/` → `garden/{board,log}/`、shift_manager SKILL Mode 5 新設、bot.py に list_pending_boards 注入、send_pending notify_pending 強化、generate_working_hours 既存タブガード、CSV パス検出強化、ADR 新規、ダミー board テスト成功
- [x] **memory 正本ルール ADR + memory-sync スクリプト 2 本**(S29) — soil-sync の対称設計(差分は raw 除外のみ)、構造ファイル=repo / wiki=VPS 主・repo 従 / raw=VPS 専属を明文化、CLAUDE.md セッションプロトコルに追加、Stage A.5 が想定通り動いている(03:34 wiki 初追記実績)タイミングで設計と現実が同期
- [x] **永続記憶 Stage B + Stage C + SKILL 動的再読み込み(S30)** — launcher 1.0.1(`execute.model` → `--model` 渡し)+ 菌糸 SKILL Mode 5 Consolidate(index 再生成 + 重複/矛盾検出 + 14 日 RAW archive、本文 append-only 厳格)+ 種 consolidate-wiki active(03:50、haiku-4-5)+ 初回実走 OK + Stage C(bot.py に memory wiki + 過去 3 日 RAW + 当日 RAW を context ロード、30000 chars cap)+ mtime 動的キャッシュ(`_FileCache`/`_DirCache`/`_MemoryPastRawCache`)で CHARTER/SKILL/PERSONA/memory 全部を再起動なしで再ロード(S27 持ち越し消化)。永続記憶の構造が「対」+「縦」で揃った
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
- [ ] **(継続/将来) CSV 運搬路 γ(Discord アップロード経路)**: 現状は α(WSL cron + rsync)。ガクチョが Discord に CSV をドラッグ&ドロップ → bot.py が受け取って VPS の `garden-mirror/garden/inbox/kodomon/` に保存する経路を将来実装(WSL 起動依存を脱却)。S24 ADR の決定 7 参照
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
- [ ] 次回セッション開始時に本 MAP.md + [S23 サマリ](../docs/sessions/2026-05-31-session23.md) + 6/1 03:00 菌糸 index-refresh 初稼働の結果(soil/log.md の追加エントリ)+ 6/1 19:00 dummy 配信の結果 + master/raw/ の蓄積状況を読む
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
- [x] **セッション23 で菌糸 Stage 1 active + Stage A.5 設計合意 + soil vault 化**(Mycelium SKILL + index-refresh active + crontab 仕込み + 4 論点合意 + ingest-raw skeleton + soil の 3 箇所配置 + monthly-shift-survey 月ずれ修正)
- [x] **セッション24 で board ライフサイクル完成 + 承認依頼通知 + 朝のリマインド統合 + 放サボ自動取込のフルパス開通 + コドモン CSV 運搬路 α 確立**(ADR 決定 7 つ + 種 3 本テンプレ統一 + generate_working_hours バグ修正 + kodomon-sync 新設 + 5 月稼働確認/7 月シフトアンケート同夜完走)
- [x] **セッション25 で連続失敗ガード + 朝ブリーフィング今日フィルタ明示化 + 測量士(codex)導入 + OPERATIONS.md 新設**(`send_pending.py` に S25 連続失敗ガード = fail_count + auto-quarantine、daily-pilot SKILL Step 3 + seed prompt 明示化、`docs/surveyor/` 新設 + ADR + 周知 4 箇所、測量士初回手紙応答として `garden/OPERATIONS.md` 660 行新設 = 役割分担表 + 業務カード 4 枚 + HMC→HMG 移行マトリクス + 失敗時リファレンス)
- [x] **セッション26 で soil 正本ルール明文化 + Stage A.5 active 化**(ADR `2026-06-02-soil-source-of-truth.md` + `garden/services/soil-sync/{pull-from-vps.sh, push-to-vps.sh, README.md}` + soil/README + CLAUDE.md セッションプロトコル + auto memory、Stage A.5: memory/master/wiki/ + index 雛形 + ingest-raw 種 active + RAW 単位の冪等性確立(turn 時刻比較を撤回)+ crontab 03:30 仕込み + dry-run 4 回完走 / 副次発見:memory 正本ルール未整理 = S27 宿題)
- [x] **セッション27 で放サボ上書き事故 → 構造改革(board/log を vault 外へ + Discord ガクコ承認運用 + daemon EXCLUDE_PREFIXES)**(import_kodomon 12 セル復元 + ADR 1 本 + 5 系統コード修正 + daemon EXCLUDE_PREFIXES 機構 + shift_manager Mode 5 新設 + bot.py list_pending_boards 注入 + send_pending notify_pending 強化 + 既存タブガード + CSV パス検出強化 + CouchDB 27 件 bulk delete + ダミー board 総合テスト成功)
- [x] **セッション28 で S27 path 移動取りこぼし 2 箇所修正**(night_cheer.py に `GARDEN_LOG_DIR` env 追加 + read_review_log 切替 + scp 反映 / settings.json に `Write/Edit(/home/vps-harappa/garden/log/**)` 2 行追加 + backup 取得 + haiku 軽量 write テスト + 副作用ファイル削除 / 副次発見:ingest-raw も同じ permission 問題で同時解決 + 03:30 ingest-raw が wiki に S27 ダミーテスト承認 1 件追記実績 = Stage A.5 初の収穫確認)
- [x] **セッション29 で memory 正本ルール ADR + path 大移動チェックリスト + board 掃除**(A: ADR `2026-06-03-memory-source-of-truth.md` + `garden/services/memory-sync/{pull/push}.sh + README.md` + memory/README に正本ルール表追記 + CLAUDE.md セッションプロトコル更新 + pull/push 検証 OK / B: OPERATIONS.md §5 path 大移動チェックリスト新章 6 層 + 完了検証 + 5 分後ふりかえり / C: failed 1 件は resolution note 追加で残置 + quarantine 2 件削除)
- [x] **セッション30 で永続記憶 Stage B + Stage C + SKILL 動的再読み込み**(1: launcher 1.0.1 で `execute.model` → `--model` 渡し + 菌糸 SKILL Mode 5 Consolidate 新設 + 種 `consolidate-wiki.md` 起草(03:50、haiku-4-5)+ 初回実走 OK + crontab 仕込み / 2: bot.py に `MEMORY_BASE` 系定数 + 起動時 memory wiki + 過去 3 日 RAW + 当日 RAW を context ロード + `build_dialogue_prompt` に `[直近の記憶]` セクション挿入(30000 chars cap)/ 3: `_FileCache` / `_DirCache` / `_MemoryPastRawCache` の 3 つの mtime ベースキャッシュクラス実装 + persona/charter/skill/wiki/past_raw 全部キャッシュ経由 + 起動時ウォームアップ + 検証 OK。永続記憶の構造が「対」(soil + memory 正本ルール)+「縦」(Stage A → A.5 → B → C)で揃った)
- [x] **(S30 達成)** 統合 Stage B(consolidate-wiki active、03:50、haiku-4-5、index 再生成 + 重複/矛盾検出 + 14 日 RAW archive)
- [x] **(S30 達成)** 統合 Stage C(bot.py 永続記憶 = memory wiki + 過去 3 日 RAW + 当日 RAW を context ロード、30000 chars cap)
- [x] **(S30 達成)** bot.py SKILL 動的再読み込み機構(mtime ベースの 3 種類キャッシュクラス、CHARTER/SKILL/PERSONA/memory 全部対象、編集 → 次 turn 反映)
- [ ] **次回本命候補(1)**: 統合 Stage B / C の初週運用観察 + 永続記憶の体感品質改善(Discord 対話で記憶想起がうまく行くか観察、prompt に置く順序の最適化)
- [ ] **次回本命候補(2)**: SKILL+CHARTER 二段ロード稼働の継続観察(S20 〜 S30 で複数回稼働、トーン磨き込み判断)
- [ ] **次回本命候補(3)**: 次の区画 = HMC 移植第3号(finance / invoice_processor 等)
- [ ] **次回本命候補(4)**: bot.py に plot ディスパッチャ実装(案 D の picker)— shift_manager + daily-pilot の topics 集約
- [ ] **次回本命候補(5)**: 統合 Stage 4(LINE webhook 受信を garden-gaku-co に追加)
- [ ] **次回本命候補(6)**: 菌糸 Mode 2 Lint(Stage 2、shift_manager 安定後 + ingest-raw 初週運用観察後、S30 で Mode 5 が「重複/矛盾検出のみログ」として実装済 → Mode 2 が本文整理 / board 剪定依頼に昇格)
- [ ] **次回本命候補(7)**: watcher daemon 実装(event 種・inbox-process / board resume の入口)
- [ ] **次回本命候補(8)**: A-1 後追い(on_failure.retry の自動化・fallback LINE 通知発火)+ バッドチャンク掃除
- [ ] **次回本命候補(9)**: kura 区画整備(S29 で failed の resolution 済 board 1 件目が退避候補確定、月次移行ポリシー設計)
- [ ] **次回本命候補(10)**: Stage D(LINE 統合 + 下位 scope RAW + 投影ビュー + マスター透視権、チーム公開時)
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
| **菌糸 Stage 1 active** = Mycelium SKILL.md(Mode 1〜4)+ 種 index-refresh.md(毎日 03:00 cron、自律実行)+ dry-run フェーズ 1 完走 + crontab 仕込み完了。明朝 6/1 03:00 から本稼働 | 2026-05-31 (S23) | [garden/mycelium/SKILL.md](mycelium/SKILL.md) + [seeds/mycelium/index-refresh.md](seeds/mycelium/index-refresh.md) |
| **soil の vault 化** = S13 vault layout 設計穴を発見、soil/ を vault + garden-mirror + repo の 3 箇所配置に昇格(memory と同パターン)。正本関係明文化は次セッション宿題 | 2026-05-31 (S23) | [sessions/2026-05-31-session23.md](../docs/sessions/2026-05-31-session23.md) |
| **Stage A.5 4 論点合意** = 抽出粒度=D(短文事実→staff ページ・長文→log.md)/ 主題判定=C(事前定義 7+LLM 新規命名)/ 冪等=C(RAW last_ingested_at + wiki append-only)/ 失敗時=A(グレー捨てる、`_pending/` なし) | 2026-05-31 (S23) | [garden/mycelium/SKILL.md](mycelium/SKILL.md) Mode 1 + [seeds/mycelium/ingest-raw.md](seeds/mycelium/ingest-raw.md) |
| **monthly-shift-survey 対象月 = +1 月** = 6/1 発火で 7 月分を出す(従来 +2 月=8 月分は誤り)。「翌々月」呼称は Mode 2 関連すべて「翌月」に統一、Mode 1 月末は「翌日 Mode 2 の対象月」と相対参照 | 2026-05-31 (S23) | [seeds/shift_manager/monthly-shift-survey.md](seeds/shift_manager/monthly-shift-survey.md) + [plots/shift_manager/SKILL.md](plots/shift_manager/SKILL.md) |
| **recurring_master 月末項目を分割** = r010 を「シフトアンケート回答チェック」にリネーム + r016 新規「コドモンCSVを設置」追加(ID 規約準拠) | 2026-05-31 (S23) | vault `hmc_tasks/recurring_master.md` |
| **soil の層別正本** = repo = 構造ファイル(staff/business/workflows/clients/events/projects/meetings/concepts)/ VPS = 菌糸産ログ(log.md + index.md)/ vault = Obsidian 読み取り専用ビュー(ガクチョ直接編集なし) | 2026-06-02 (S26) | [decisions/2026-06-02-soil-source-of-truth.md](../docs/decisions/2026-06-02-soil-source-of-truth.md) |
| **soil-sync 同期スクリプト 2 本**(pull-from-vps / push-to-vps、`--delete` なしで初版開始)+ セッション開始時 pull / 終了時 push をプロトコル化 | 2026-06-02 (S26) | [garden/services/soil-sync/](services/soil-sync/) + [CLAUDE.md](../CLAUDE.md) |
| **Stage A.5 冪等性は RAW 単位の処理完了マーカー**(turn 時刻比較を撤回、S26 dry-run で発見した turn 比較脆弱を回避)+ today RAW は対象外で翌日 03:30 処理 | 2026-06-02 (S26) | [seeds/mycelium/ingest-raw.md](seeds/mycelium/ingest-raw.md) + [sessions/2026-05-31-session23.md](../docs/sessions/2026-05-31-session23.md) §論点 3 補注 |
| **board と log を Obsidian vault 外へ移行**(`garden-mirror/garden/{board,log}/` → `/home/vps-harappa/garden/{board,log}/`)= LiveSync 起因の事故を構造的に封じ込め、vault は知識ベース(soil/inbox/memory)のみ、VPS は唯一の書き手・読み手 | 2026-06-02 (S27) | [decisions/2026-06-02-board-and-log-out-of-vault.md](../docs/decisions/2026-06-02-board-and-log-out-of-vault.md) |
| **承認運用 = Discord ガクコ経由**(Obsidian 編集 UI を経由しない、ガクコが SKILL Mode 5 通り自然言語を解釈して board frontmatter を Edit)= shift_manager SKILL Mode 5 + daily-pilot Mode 2 拡張 | 2026-06-02 (S27) | [plots/shift_manager/SKILL.md](plots/shift_manager/SKILL.md) Mode 5 + [plots/daily-pilot/SKILL.md](plots/daily-pilot/SKILL.md) Mode 2 |
| **daemon EXCLUDE_PREFIXES 機構**(mirror-daemon は除外プレフィックスを fs 書き出しから skip、writeback-daemon は CouchDB push から skip)= LiveSync ignore より頑健、VPS 側の単一真実、別端末増加にも自動対応 | 2026-06-02 (S27) | [garden/services/mirror-daemon/mirror.mjs](services/mirror-daemon/mirror.mjs) + [garden/services/writeback-daemon/writeback.mjs](services/writeback-daemon/writeback.mjs) |
| **generate_working_hours.py 既存タブガード**(`--force-regenerate` フラグ + `_has_saboru_data` チェック、既存タブに放サボ列データあり + force なし → exit 1)= 同じ事故の構造再発ゼロ | 2026-06-02 (S27) | [garden/services/shift-manager/generate_working_hours.py](services/shift-manager/generate_working_hours.py) |
| **bot.py に list_pending_boards 注入**(prompt に pending ファイル一覧を事前注入、Bash/Glob 禁止下でも承認候補を認識可能)= ガクコの自然言語承認の実用性確保 | 2026-06-02 (S27) | [garden/services/garden-gaku-co/bot.py](services/garden-gaku-co/bot.py) |
| **memory の層別正本** = repo = 構造ファイル(README/.gitkeep)/ VPS = wiki 主・raw 専属(ingest-raw + bot 書き込み)/ vault = LiveSync 経由読み取り | 2026-06-03 (S29) | [decisions/2026-06-03-memory-source-of-truth.md](../docs/decisions/2026-06-03-memory-source-of-truth.md) |
| **memory-sync 同期スクリプト 2 本**(soil-sync 対称、差分は `--exclude='*/raw/*.md'` のみ、raw が repo に流れない構造保証) | 2026-06-03 (S29) | [garden/services/memory-sync/](services/memory-sync/) + [CLAUDE.md](../CLAUDE.md) |
| **OPERATIONS.md §5 path 大移動チェックリスト**(コード/設定/種/ドキュメント/daemon/完了検証 の 6 層 + 5 分後ふりかえり + 24h 後検証ポイント宿題化、S28 学び由来) | 2026-06-03 (S29) | [garden/OPERATIONS.md §5](OPERATIONS.md#5-path-大移動チェックリスト計画時--完了検証用) |

## 直近のセッション

- [2026-06-03 セッション30](../docs/sessions/2026-06-03-session30.md) — **永続記憶 Stage B + Stage C + SKILL 動的再読み込み**:S29 終了直後「1→2→3 で行こう」指示で 3 案件 1 セッション中に完遂。**1 = Stage B Consolidate**:launcher.mjs に `execute.model` → `--model` 渡し最小拡張(1.0.0 → 1.0.1)+ [菌糸 SKILL.md](mycelium/SKILL.md) に Mode 5 = Consolidate 新設(index 再生成 + 重複/矛盾検出 + 14 日 RAW archive、本文 append-only 厳格、Karpathy LLM Wiki との差分明文化)+ 種 [`consolidate-wiki.md`](seeds/mycelium/consolidate-wiki.md) 起草(cron 03:50、engine claude-code、model claude-haiku-4-5)+ VPS 配置(scp 3 ファイル)+ haiku 単発確認 OK + launcher dry-run OK + 初回実走 OK(wiki 2 ページ + index 再生成、重複/矛盾 0、archive 0、log NOTIFY 残せた)+ crontab `50 3 * * *` 仕込み。**2 = Stage C 永続記憶**:[bot.py](services/garden-gaku-co/bot.py) に `MEMORY_BASE` 系定数 + 起動時 memory wiki + 過去 3 日 RAW を context ロード + `build_dialogue_prompt` に `[直近の記憶]` セクション挿入(30000 chars cap)+ 当日 RAW は毎 turn 再読み込み(ハイブリッド)+ bot 再起動 + 初回起動成功 + サイズ確認 OK(計 ~22KB)。**3 = SKILL 動的再読み込み(S27 持ち越し消化)**:`_FileCache`(単一ファイル mtime check)+ `_DirCache`(ディレクトリ最大 mtime check、index_first 対応)+ `_MemoryPastRawCache`(対象日 + mtime check、日またぎ自動対応)の 3 クラスを bot.py に実装 + persona/charter/skill/wiki/past_raw 全部キャッシュ経由に書き換え + 起動時ウォームアップ + bot 再起動 → 全キャッシュ正常ロード(persona 826/charter 3839/skill 9817/wiki 3826/past_raw 4039)。Stage B/C の結果が **bot 再起動を待たず次 turn で反映**(対称性確保)。学び = 永続記憶の「対(soil + memory 正本ルール)」と「縦(Stage A → A.5 → B → C)」が揃った節目、UX 先行プロセスは設計判断 5 つを箇条書きで提示するパターンが安定
- [2026-06-03 セッション29](../docs/sessions/2026-06-03-session29.md) — **memory 正本ルール ADR + path 大移動チェックリスト + board 掃除**:コールドスタート「全体概況をみて」から、宿題棚卸し → ABC 3 案件を 1 セッション中に完遂。**A** = S26-S28 持ち越し本命を消化:[ADR 2026-06-03 memory-source-of-truth](../docs/decisions/2026-06-03-memory-source-of-truth.md) 起票 + [memory-sync](../garden/services/memory-sync/) 2 本(pull/push、`--exclude='*/raw/*.md'` で raw は VPS 専属を構造保証)+ README + memory README に正本ルール表追記 + CLAUDE.md セッションプロトコル追加 + dry-run/実走検証 OK(tech_infra.md の 03:34 ingest-raw 追記分が repo に取り込み済)。soil-sync の対称設計で並列に配置(1 本統合せず責務分離)、採用しなかった案 3 つも ADR に記録。**B** = S28 学びの言語化:OPERATIONS.md §5 path 大移動チェックリスト新章(6 層 + 完了検証 + 5 分後ふりかえり)、既存 §5 関連は §6 に繰り下げ、罠 2 つを明文化(cron 想定スクリプト手動実行 / permission 不足の "沈黙")、env default は「default を新パスに + env 上書き優先」+「24h 後検証ポイント宿題化」を鉄則化。**C** = board 掃除:`failed/2026-06-01-monthly-shift-survey.FAILED.md` は frontmatter に resolution/resolution_at/resolution_session 追加で残置(README ポリシー通り、kura 候補 1 件目確定)+ quarantine 2 件削除。学び = 持ち越し本命+学び+掃除の 3 セット構成は重→軽で快適に回る + soil と memory の正本ルールが「対」として揃った + OPERATIONS.md が「育つ運用書」として機能している
- [2026-06-03 セッション28](../docs/sessions/2026-06-03-session28.md) — **S27 path 移動取りこぼし 2 箇所修正(night_cheer + claude 権限)**:昨夜 22:40 の Discord 警告通知から、S27 の `garden/log/` 移動で取りこぼされた 2 箇所を特定 →(1) `night_cheer.py:51` の `read_review_log` 旧パス →(2) settings.json に新 log path の Write/Edit 権限なし。修正 = `night_cheer.py` に `GARDEN_LOG_DIR` env 追加 + settings.json に 2 行 allow 追加 + haiku 軽量 write テスト。副次発見 = ingest-raw も同じ問題で同時解決 + 03:30 ingest-raw のコア処理成功で wiki に S27 ダミーテスト承認 1 件追記実績(Stage A.5 初収穫)
- [2026-06-02 セッション27](../docs/sessions/2026-06-02-session27.md) — **放サボ上書き事故 → 構造改革(board/log を vault 外へ + Discord ガクコ承認運用 + daemon EXCLUDE_PREFIXES)**:S26 終了の数時間後に 5 月稼働サマリの放サボ列消失を発見 → 原因は LiveSync 経由の board 巻き戻しによる send_pending 重複実行 → import_kodomon 手動実行で 12 セル復元 → 構造改革に着手:**board/log を `garden-mirror/garden/{board,log}/` → `garden/{board,log}/`** に移行(vault 外配置)+ **mirror/writeback daemon に EXCLUDE_PREFIXES** 機構(LiveSync ignore の代替、VPS 側で完全制御)+ **shift_manager SKILL Mode 5 新設**(Discord 自然言語の承認応答ルール)+ **bot.py に list_pending_boards 注入**(Bash/Glob 禁止下で pending 認識)+ **send_pending.py notify_pending 強化**(配信本文プレビュー + 関連 URL + 客観事実 + ガクコ操作ガイド)+ **board_facts.py 新規**(seed 別事実プロバイダ)+ **既存タブガード**(`generate_working_hours.py --force-regenerate` + `_has_saboru_data`、同じ事故を構造再発ゼロに)+ **CSV パス検出を import_kodomon.resolve_csv_path に一本化** + ADR 新規(supersede 注記 2 箇所)+ CouchDB 27 件 bulk delete + ダミー board でガクコ承認動線テスト成功
- [2026-06-02 セッション26](../docs/sessions/2026-06-02-session26.md) — **soil 正本ルール明文化 + Stage A.5 active 化**:S23 持ち越し宿題と本来別セッション級の Stage A.5 を 1 日で両方完走。soil 正本ルール = 案 A(vault 起点)棄却 → 層別正本案採用(ガクチョ「直接触らない運用ですっきり」)→ ADR + `garden/services/soil-sync/{pull/push}` 2 本 + soil/README + CLAUDE.md セッションプロトコル + auto memory。Stage A.5 = wiki ディレクトリ + index 雛形 + ingest-raw VPS 配置 + **dry-run 4 回**(1 回目実走成功 / 2-3 回目で turn 時刻比較の冪等性脆弱を発見 → RAW 単位の処理完了マーカーに prompt 修正 / 4 回目で完全 skip 確認)+ crontab 03:30 仕込み + status active 昇格。副次発見 = memory も 3 箇所配置問題(S27 宿題に追加)
- [2026-05-31 セッション23](../docs/sessions/2026-05-31-session23.md) — **菌糸 Stage 1 active + Stage A.5 設計合意 + soil vault 化 + monthly-shift-survey 月ずれ修正**:事前確認(対象月 +2→+1 月修正 + 関連 5 ファイルの「翌々月」呼称統一)+ recurring_master 月末項目分割 / Mycelium SKILL.md 起草(Mode 1〜4)/ soil/index.md 初回 full scan(staff 29 / business 18 / workflows 4 / concepts 1)/ vault layout 設計穴発見 → soil を vault に追加(65 ファイル)/ 種 index-refresh 起草 + dry-run フェーズ 1 完走(launcher exit 0、62 件検知、LLM 柔軟判断 OK)+ crontab 03:00 仕込み / Stage A.5 4 論点合意(D/C/C/A)→ SKILL Mode 1 詳細化 + ingest-raw skeleton 起草。明朝 6/1 03:00 から菌糸初稼働
- [2026-05-31 セッション22](../docs/sessions/2026-05-31-session22.md) — **garden-gaku-co 統合方針 + 記憶三層分離 + Stage A 着手 + 6/1 dummy 化**:報告(夜のレビュー / 朝のブリーフィングは Obsidian 連携含め OK)→ 方針確定(gaku-co5.0 と garden-gaku-co を **garden-gaku-co に統一されてからリリース**、入口=Discord/LINE 別・中身=Garden 単一)→ 記憶の構造軸見直し(S20 で見落とした「scope 軸 vs 意味軸の分断」)→ **三層分離 ADR**(RAW=scope/SOIL=意味/MEMORY WIKI=scope、soil は事実のみ、判断は memory に隔離、3者間会話の扱い、漏洩防御=投影ビューは Stage D)→ **send_pending.py に dispatch_mode: dummy 実装**(`.env` SEND_PENDING_DEFAULT_MODE=dummy + board frontmatter 上書き)→ **memory_logger.py 新規 + bot.py に append_turn 統合**(master/raw/{YYYY-MM-DD}.md、対話を捨てない最小実装)→ VPS 反映 + dummy 動作検証 OK(11:27 ダミー board → Discord master プレビュー → processed/ 移動)+ RAW logging 動作検証 OK(11:38/11:39 の 2 turn 記録)
- [2026-06-01 セッション24](../docs/sessions/2026-06-01-session24.md) — **board ライフサイクル完成 + 承認依頼通知 + 朝のリマインド統合 + 放サボ自動取込のフルパス開通**:dummy 配信不在発覚から、S21 から潜伏していた構造穴 3 つ(Bash 未許可・通知モック放置・連鎖未自動化)+ 放サボ取込の 3 重バグ(時間空スキップ・運搬路欠落・ファイル名固定)を一気通貫で塞いだ。送付ロジックを `status:` 一本化(チェックボックスは備忘録)+ board/failed/ 新設(4 系統)+ 種 3 本に庭師アクション統一テンプレ強制 + generate_working_hours バグ修正 + import_kodomon ファイル名柔軟化 + kodomon-sync(α)新設。 **5 月稼働確認 + 7 月シフトアンケート同夜完走、放サボ列 12 セル反映成功**。ADR 決定 7 つ
- [2026-05-31 セッション23](../docs/sessions/2026-05-31-session23.md) — **菌糸 Stage 1 active + Stage A.5 設計合意 + soil vault 化**
- [2026-05-31 セッション22](../docs/sessions/2026-05-31-session22.md) — **garden-gaku-co 統合方針 + 記憶三層分離 + Stage A 着手 + 6/1 dummy 化**
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
