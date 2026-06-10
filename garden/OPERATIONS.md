# garden/OPERATIONS.md — 庭師の日々の運用盤

> このファイルは **「HMG を日々どう使うか」の運用早見表**。
> 戦略地図(MAP.md)・規範(CHARTER.md)・決定(ADR)・履歴(sessions)とは別の役割を担う、ガクチョ向け実用ページ。
>
> 育てる文書。新しい業務を Garden 化したら **運用カード** を追加する。
> 初版: 2026-06-02 セッション25(測量士の手紙 [2026-06-02](../docs/surveyor/letters/2026-06-02.md) 提案 1+2+4 を統合)。

---

## 0. ファイル間の役割分担

「どこに何が書いてあるか」を 1 表で。Garden が育つほど場所が増えるので、迷ったらここに戻る。

| 場所 | 役割 | 頻度 |
|---|---|---|
| **garden/OPERATIONS.md(本ファイル)** | **日々の運用早見表**(業務カード・移行表・通知の役割分担) | 月数回 / 困った時 |
| `garden/MAP.md` | 戦略地図(現在地・区画ステータス・ロードマップ・宿題) | セッション開始時 |
| `garden/CHARTER.md` | 全 plot 共通の業務観・トーン・Output Style 規範 | plot SKILL 編集時 |
| `garden/plots/{plot}/SKILL.md` | 各業務の手順・判断ルール正本 | 業務改善時 |
| `garden/soil/workflows/*.md` | 業務プロセスの正本(目的不変・方法は改善対象) | 業務見直し時 |
| `docs/sessions/YYYY-MM-DD-sessionN.md` | セッション履歴 | 振り返り時 |
| `docs/decisions/YYYY-MM-DD-題名.md` | 設計判断 ADR | 重要決定時 |
| `docs/surveyor/letters/YYYY-MM-DD.md` | 外部視点 codex からの手紙 + Claude Code 応答 | 月 1〜2 回 |
| `docs/discussions/*.md` | 壁打ち議論ログ(任意) | 議論深掘り時 |

---

## 1. 今日見る場所(役割分担)

ガクチョが日々接する **6 つの面** と、それぞれに何が来るか・何をするか。

| 場所 | 何が来る | 頻度 | ガクチョのアクション |
|---|---|---|---|
| **Discord master ch** | 承認依頼(強化版) / 配信完了 / 失敗通知 / 朝の口火 / 夜のレポート | 随時 + 06:40 / 22:40 | ガクコに自然言語で返信(承認/テスト/却下/編集/`board 見せて`) |
| **朝の口火(06:40 Discord)** | 当日 `active_tasks` のサマリ + Triage 数 + board 承認待ち件数 | 1 日 1 回 | 一日の見通しを得る・対話開始 |
| **夜のレポート(22:40 Discord)** | 完了 / 持ち越し / 翌日サマリ | 1 日 1 回 | 終わりの確認 |
| **Obsidian: `hmc_tasks/active_tasks.md`** | 今日のタスク一覧(`deadline ≦ today` のみ) | 随時 | チェック / 締切編集 / `## 追加` でタスク投入 |
| **Discord 経由 board 承認応答** | 承認依頼の中身(配信本文プレビュー + 関連リンク + 客観事実)が Discord に届く | 随時 | ガクコに「承認」「テスト送って」「却下」「本文を XX に変えて承認」「board 見せて」と自然言語で伝える([shift_manager Mode 5](plots/shift_manager/SKILL.md#mode-5-discord-approval-response承認応答)) |
| **Discord(朝の Triage 返信)** | 朝の Triage(軸 A/B/C への質問) | 1 日 1 回 | Discord 短文で「A は a、B は b で」 |

> **2026-06-02(S27)以降**: `garden/board/` と `garden/log/` は **Obsidian vault の外**(`/home/vps-harappa/garden/{board,log}/`)に配置。LiveSync 起因の巻き戻し事故([ADR 2026-06-02 board-and-log-out-of-vault](../docs/decisions/2026-06-02-board-and-log-out-of-vault.md))を構造的に封じ込めるため、board と log は **VPS が唯一の書き手 / 読み手**。承認操作は Discord でガクコに伝える運用に移行。

### 役割の分離原則(2026-06-02 測量士提案 4 採用)

- **board**: ガクチョが判断すべきもの(=剪定依頼)を集める場所。「承認/却下/修正」の単位
- **morning-briefing**: 上記 board を朝に再提示する役割(Step 1.5 で `## 📋 承認待ち board` セクションを active 末尾に追加)
- **Discord**: 通知のチャネル(剪定依頼の到着・配信完了・失敗)
- **MAP**: 戦略地図(全体の現在地と進捗)
- **session**: 履歴(時系列の作業記録)
- **ADR**: 決定の記録(なぜそうしたか)
- **OPERATIONS(本ファイル)**: 日々どう使うかの早見表

→ ガクチョが「今日何を判断すべきか」を知りたければ board と朝の口火を見る。「全体としてどこにいるか」を知りたければ MAP を見る。「なぜこうなっているか」を知りたければ ADR と session を見る。

---

## 2. 業務プロセス別 運用カード

「この業務、今 HMG ではどう動くのか?」を業務単位で一覧化。

### Card 1: shift_manager(月次シフトと稼働精算)

| 項目 | 内容 |
|---|---|
| **自動度** | 半自動(cron 自動起動、配信は承認必須) |
| **トリガー** | 月末最終日 22:00 / 月初 1 日 08:00 / 月初 1 日 09:00(構想)/ 月初 10 日 08:00(構想) |
| **承認境界** | (1) 稼働表チェック完了+集計実行ボタン (2) アンケート配信文承認 (3) 稼働確認配信承認 |
| **通知先** | Discord master(board pending 起草・集計完了・配信完了・失敗)/ staff LINE グループ(本配信、現在 dummy モードで Discord 経由手動コピー) |

**月次フロー**:

1. **月末 22:00**: `month-end-working-hours-prep` 種発火 → `/home/vps-harappa/garden/board/pending/{date}-working-hours-prep.md` 起草 → Discord master に強化版承認依頼通知(関連リンク + 客観事実 + チェックリスト)
2. **ガクチョ**: Discord 通知の中身を確認(コドモン CSV 配置済 / シート URL 等が事実として並ぶ)→ ガクコに「5月稼働 集計実行」「承認」等で承認 → ガクコが board の status を approved に書き換え
3. **send_pending.py** が `generate_working_hours.py` 実行 → 稼働表タブ生成(既存タブガード付き、S27 で導入)→ コドモン CSV を自動検出して `import_kodomon.py` で放サボ列に反映 → 完了通知
4. **ガクチョ**: 月内に `garden/inbox/kodomon/{YYYY-MM,YYYYMM}*.csv` を Obsidian で配置済なら 3 で自動取込済。未配置で集計完了したら、後追いで CSV 配置 + ガクコに「コドモン取込みやって」と伝える
5. **月初 1 日 08:00**: `monthly-shift-survey` 種発火 → 翌月アンケート board 起草 → Discord master に強化版承認依頼通知(配信本文プレビュー付き)
6. **ガクチョ**: Discord 通知で本文プレビュー確認 → ガクコに「シフト募集 承認」 → ガクコが status を approved に(dummy モードでは配信時刻に Discord master へプレビュー配信)
7. **月初 1 日 09:00**: `monthly-working-hours-confirmation` 種発火(現状 dummy モード、staff 見せ方未確定で blocked: true)
8. **月初 10 日 08:00**: `monthly-shift-finalize` 種(構想)

**失敗時に見るところ**:

- VPS: `/home/vps-harappa/garden/log/{today}-{seed}.log`
- VPS: `/home/vps-harappa/garden/log/send-pending.log`
- `garden/board/failed/*.FAILED.md`(連続失敗で auto-quarantine された board、S25 で導入)
- board frontmatter の `fail_count` / `last_fail_reason`(S25 で導入)

**関連ファイル**:

- SKILL: [`garden/plots/shift_manager/SKILL.md`](plots/shift_manager/SKILL.md)
- 種: [`garden/seeds/shift_manager/`](seeds/shift_manager/)
- スクリプト: [`garden/services/shift-manager/`](services/shift-manager/)
- 配信: [`garden/services/garden-gaku-co/send_pending.py`](services/garden-gaku-co/send_pending.py)
- workflow 正本: [`garden/soil/workflows/monthly-cycle.md`](soil/workflows/monthly-cycle.md)

---

### Card 2: daily-pilot(日次タスクとブリーフィング)

| 項目 | 内容 |
|---|---|
| **自動度** | 半自動(cron 自動起動、Triage 対話と承認は ガクチョ) |
| **トリガー** | 06:25 / 06:30 / 06:40 / 22:30 / 22:40(VPS cron) |
| **承認境界** | (1) Triage 軸 A/B/C への返信 (2) backlog 直接編集(締切変更等) (3) active の `[x]` 操作 |
| **通知先** | Discord master(朝の口火・夜のレポート・Triage リマインド・board pending リマインド) |

**日次フロー**:

1. **06:25**: `recurring-spawn` 種 → 定期タスクを backlog に追加(`<!-- recur:{id}@{period_id} -->` で冪等)
2. **06:30**: `morning-briefing` 種 → backlog から `deadline ≦ today` を抽出して active 構築 + Triage 生成 + 承認待ち board リマインド追加
3. **06:40**: `morning_greet.py` → Discord master に active サマリ投稿
4. **日中**: ガクチョと bot が Discord で対話 → 必要なら active / backlog / board を編集
5. **22:30**: `night-review` 種 → active → archive 反映 / `[x]` 削除 / `[ ]` 持ち越し / 翌日テンプレ生成
6. **22:40**: `night_cheer.py` → Discord master に夜のレポート投稿

**失敗時に見るところ**:

- VPS: `/home/vps-harappa/garden/log/{today}-morning-briefing.log` 等
- VPS: `/home/vps-harappa/garden/log/launcher.log`
- VPS: `docker logs garden-mirror-daemon` / `docker logs garden-writeback-daemon`
- Obsidian LiveSync の同期状態(端末側で確認)

**関連ファイル**:

- SKILL: [`garden/plots/daily-pilot/SKILL.md`](plots/daily-pilot/SKILL.md)
- 種: [`garden/seeds/daily-pilot/`](seeds/daily-pilot/)
- bot: [`garden/services/garden-gaku-co/bot.py`](services/garden-gaku-co/bot.py)
- 朝の口火: [`garden/services/garden-gaku-co/morning_greet.py`](services/garden-gaku-co/morning_greet.py)
- 夜の cheer: [`garden/services/garden-gaku-co/night_cheer.py`](services/garden-gaku-co/night_cheer.py)
- ランチャー: [`garden/services/launcher/`](services/launcher/)

---

### Card 3: kodomon CSV 取込(放サボ稼働の反映)

| 項目 | 内容 |
|---|---|
| **自動度** | 半自動(CSV エクスポートは ガクチョ手動、WSL → VPS rsync と取込は自動) |
| **トリガー** | (1) ガクチョ: コドモン Web で CSV エクスポート → `garden/inbox/kodomon/` に保存 (2) WSL */5 cron: rsync → VPS (3) 月末 22:00 cron: `run_month_end_collect.sh` → `import_kodomon.py` |
| **承認境界** | なし(機械処理)。反映結果は Working Hours Sheet で ガクチョが目視確認 |
| **通知先** | Discord master(import 完了時の反映セル数) |

**取込フロー**:

```
[ガクチョ] コドモン Web → CSV エクスポート
   ↓
[WSL] /home/tukapontas/harappa-garden/garden/inbox/kodomon/{任意名}.csv に保存
   ↓ WSL */5 cron(sync_to_vps.sh)が rsync
[VPS] /home/vps-harappa/garden-mirror/garden/inbox/kodomon/{同名}.csv
   ↓ run_month_end_collect.sh が import_kodomon.py を呼ぶ
[Google Sheets] Working Hours の YYYY-MM_稼働時間 タブの 放サボ列(オレンジ)に反映
```

**制約(α 経路の限界)**:

- **WSL が起動中でなければ rsync が動かない**。月初 8:00 まで反映させたければ前日中に WSL を起動
- 同名ファイルは上書きしない(`--ignore-existing`)。上書きしたい時は VPS 側で先に削除
- 将来 γ 経路(Discord アップロード → bot.py で受信)に移行予定

**ファイル名規約**(`import_kodomon.py` 側で柔軟化済):

- `2026-05.csv` / `202605.csv` / `*2026-05*.csv` / `*202605*.csv`
- フォルダ内 CSV が 1 件だけならファイル名問わず採用
- コドモンのデフォルト名 `職員入退室エクスポート.csv` のままでも、月名を含めば OK

**失敗時に見るところ**:

- WSL: `/tmp/kodomon-sync.log`(rsync ログ)
- VPS: `/home/vps-harappa/garden/log/run_month_end_collect.log`
- VPS inbox: `ssh harappa "ls /home/vps-harappa/garden-mirror/garden/inbox/kodomon/"` で CSV 到着確認

**関連ファイル**:

- 運搬サービス: [`garden/services/kodomon-sync/`](services/kodomon-sync/)(README に詳細)
- 取込スクリプト: [`garden/services/shift-manager/import_kodomon.py`](services/shift-manager/import_kodomon.py)
- 受け皿: [`garden/inbox/kodomon/`](inbox/kodomon/)

---

### Card 4: mycelium index-refresh(土壌維持)

| 項目 | 内容 |
|---|---|
| **自動度** | 自律(cron 日次、LLM が意味的に index 更新を判断) |
| **トリガー** | 03:00 cron(VPS) |
| **承認境界** | なし(土壌維持は自律、ガクチョの認知に出さない) |
| **通知先** | なし(silent 運用、log のみ) |

**フロー**:

1. 過去 24h で `garden/soil/` 配下に編集があったか検知
2. 0 件なら exit 0 + log に skip 記録
3. 1 件以上 → 各ファイルを Read → `garden/soil/index.md` を意味的に更新(LLM 判断、機械的な一覧化ではない)
4. `garden/soil/log.md` に動作ログを追記

**設計哲学**: Karpathy LLM Wiki 方式。staff 増減 → カテゴリ集計を更新、business 配下追加 → 該当表を更新、など **意味で書き換える**。

**失敗時に見るところ**:

- VPS: `/home/vps-harappa/garden/log/index-refresh.log`
- VPS: `garden/soil/log.md` の末尾(動作の有無を確認)

**関連ファイル**:

- SKILL: [`garden/mycelium/SKILL.md`](mycelium/SKILL.md)
- 種: [`garden/seeds/mycelium/index-refresh.md`](seeds/mycelium/index-refresh.md)
- 維持対象: [`garden/soil/index.md`](soil/index.md) / [`garden/soil/log.md`](soil/log.md)

---

### Card 5: plot_gardener(業務を区画化する)

| 項目 | 内容 |
|---|---|
| **自動度** | 庭師起点(ガクチョが「この業務を Garden 化して」と依頼 → Claude Code が伴走) |
| **トリガー** | ガクチョの依頼。粒度は「`{業務名}` を移植型/新植型で Garden 化して」 |
| **承認境界** | 設計レビューは対話で。成果物(区画)の active 昇格はガクチョ確認 |
| **通知先** | なし(セッション内対話) |

**これは業務カードではなく「業務カードを増やすためのメタカード」**。新しい業務を HMG に載せたいとき、毎回ゼロから設計せず、この型に通す。

**ガクチョが渡すもの(3 つだけ)**: ① 業務名 ② mode(移植型 transplant / 新植型 seedling / 改植型 hybrid、迷えば Claude が判定) ③ MVP の範囲。tool / service の粒度は渡さない(水面下 = Garden が選ぶ)。

**フロー**(SKILL の Mode 1〜6):

1. **Intake** — 依頼を要約、不足は最大 3 つだけ聞く(HMC レガシー有無 / MVP / scope)
2. **Legacy Inventory**(移植型のみ) — HMC 側を棚卸し、「そのまま使う/包む/SKILL に吸い上げる/捨てる」に 4 分類。合言葉「業務知識は継承、起動と承認だけ Garden に変える」
3. **Workflow Spec**(新植型のみ) — 目的と現状の方法を分けて言語化
4. **Garden Design** — 区画 = SKILL + 種 + 通行手形 + service を最小セットで設計
5. **Implementation Plan** — Phase 0(読む)〜 Phase 5(検証)に分解
6. **Review & Promotion** — draft → test → active → mature で昇格

**判断の原則**:

- 設計するのは **区画・種・通行手形** の 3 つ。**tool / service は水面下**(Garden が選ぶ)
- read / draft 系は core_team の通行手形に出しやすい。**execute 系は原則 board を挟む**
- 移植型は **レガシーを読む前に実装しない**
- MAP より先に **この OPERATIONS の運用カード**(=新業務の Card N)を更新する

**関連ファイル**:

- SKILL: [`garden/plots/plot_gardener/SKILL.md`](plots/plot_gardener/SKILL.md)
- 語彙の正本(設計言語 vs 実装層): [`docs/garden-vocabulary.md`](../docs/garden-vocabulary.md)
- 起点(測量士サンプル): [`docs/surveyor/letters/2026-06-03-plot-gardener-skill-sample.md`](../docs/surveyor/letters/2026-06-03-plot-gardener-skill-sample.md)

---

### Card 6: invoice_processor(月次請求書処理)

| 項目 | 内容 |
|---|---|
| **自動度** | 半自動(cron 自動起動で board 起草まで、Freee 登録は承認必須) |
| **トリガー** | 毎月 12 日 08:00(VPS cron、前月分)/ 手動「請求書まわして」(Discord master) |
| **承認境界** | Freee 登録前(レビュー Sheet 確認 → 「承認」→ dry-run 提示 → 本登録) |
| **通知先** | Discord master(候補起草 + Sheet URL + **請求漏れ疑いリスト** / 完了 / 失敗) |

**月次フロー**:

1. **12 日 08:00**: `monthly-invoice-draft` 種発火 → fetch(Gmail → Drive)→ extract(Gemini 解析 + **soil スタッフ照合**)→ check(**前月稼働と突合 → 請求漏れ検出**)→ レビュー Sheets タブ作成 → board 起草 → Discord 通知
2. **ガクチョ**: Discord 通知の Sheet URL を開いて確認・編集(スタッフ請求が先頭 / リスト外 = 薄い青 / MISMATCH = 黄色。行削除 = 除外)。**請求漏れの人には催促**(自動催促はしない)
3. **ガクチョ**: ガクコに「承認」→ ガクコが from-sheet → `register --dry-run` で件数・合計額を提示 → OK で本登録
4. **service が自動後始末**: Gmail スレッド「処理済」ラベル + アーカイブ / Drive Inbox → Processed
5. 遅れて届いた請求書: 「請求書まわして」でいつでも再実行(ラベル・Drive 移動でべき等。再集計はマージ安全)

**失敗時に見るところ**:

- VPS: `/home/vps-harappa/garden/log/{date}-invoice-draft.log`
- Drive の Error フォルダ(登録失敗ファイルの隔離先)
- `working/invoices_*.csv`(抽出結果。register 失敗行の確認)

**関連ファイル**:

- SKILL: [`garden/plots/invoice_processor/SKILL.md`](plots/invoice_processor/SKILL.md)
- 種: [`garden/seeds/invoice_processor/monthly-invoice-draft.md`](seeds/invoice_processor/monthly-invoice-draft.md)
- スクリプト: [`garden/services/invoice-processor/`](services/invoice-processor/)
- スタッフ照合の正本: [`garden/soil/people/staff/`](soil/people/staff/)

---

## 3. HMC → HMG 移行マトリクス

業務単位で「HMC ではどう動いていたか / HMG ではどこまで移ったか / ガクチョの作業」を一覧化(2026-06-02 測量士提案 2 採用)。

凡例: ✅ HMG 完全 / 🚧 部分移行・実装中 / ⬜ 未着手・HMC のみ / 🆕 HMG ネイティブ(HMC には無い)

| 業務 | HMC | HMG | 段階 | ガクチョの作業 |
|---|---|---|---|---|
| **シフト管理(月次)** | `apps/shift_manager/` 全体 | shift_manager plot + 種 3 本 active + Python scripts 移植済 + aggregate_responses 移植(S37) | ✅ 完了(残: Mode 3 見せ方未確定、Mode 4 は集計単体のみ手動利用可) | 月末 board 確認 → 集計実行 / 月初 dummy 配信を staff LINE に手動コピー |
| **日次タスク管理** | `apps/hmc_pilot` SKILL + active_tasks/backlog 手動運用 | daily-pilot plot + 種 3 本 active + bot 対話 + active/backlog 自動構築 | ✅ 完了 | 朝 Discord で対話 / Obsidian で backlog 編集 / 夜の対話で返答 |
| **コドモン CSV 取込** | (HMC 期は無し、Garden で新規) | kodomon-sync(α)+ import_kodomon.py | 🆕 ✅ 完了(γ は将来) | 月末までにコドモン Web で CSV エクスポート → `garden/inbox/kodomon/` に置く |
| **土壌維持(soil index)** | (HMC 期は無し) | mycelium index-refresh active | 🆕 ✅ 完了(Stage 1) | なし(自律) |
| **永続記憶** | (HMC 期は無し) | Stage A〜C すべて active(S30。RAW logging + ingest-raw + consolidate-wiki + bot 永続記憶ロード) | 🆕 ✅ 完了(Stage D はチーム公開時) | なし(自律) |
| **経費登録** | `apps/expense_processor` | expense_processor plot + service + 種 2 本 active + cron(S35〜S38) | ✅ 完了(残: 件数多い月の本番 1 周見届け) | 月末に明細・レシートを Drive へ / Discord「経費まわして」or 承認 / Sheets レビュー |
| **売上記帳(STORES/Square)** | `apps/finance_importer` | 未移植 | ⬜ | HMC で従来通り |
| **請求書処理** | `apps/invoice_processor` | invoice_processor plot + service + 種 1 本(S41、hybrid: スタッフ照合 + 稼働突合を新設) | 🚧 draft(VPS デプロイ + ⭐token/Sheet + 初回実走待ち) | 12 日通知の Sheet 確認 → 「承認」/ 請求漏れの人へ催促 |
| **メール整理** | `apps/email_organizer` | 未移植 | ⬜ | HMC で従来通り |
| **議事録(Plaud等)** | `apps/minute_maker` | 未移植 | ⬜ | HMC で従来通り |
| **SNS 投稿** | `apps/sns_pilot` | 未移植 | ⬜ | HMC で従来通り |
| **部門振り分け監査** | `apps/freee_auditor` | 未移植 | ⬜ | HMC で従来通り |
| **財務分析(PL/CF)** | `apps/finance_analyzer` | 未移植 | ⬜ | HMC で従来通り |
| **手紙仕分け** | `apps/letter_opener` | 未移植 | ⬜ | HMC で従来通り |

**移行優先度の現在地**(S41 時点):

- 完了: 永続記憶(S30)/ expense_processor(S37-S38)
- 実装中: **invoice_processor**(S41 で plot + service + 種を起草。デプロイ + 初回実走待ち)
- 次の候補: **finance_importer / freee_auditor の Garden 化**(plot_gardener 移植型で。expense/invoice の型を流用)
- 後追い: SNS / 議事録 / メール / 監査 / 分析 / 手紙

### 3.1 SKILL 正本表(どちらを読むべきか)— S39 新設

同名業務の SKILL が `.agent/skills/`(HMC 継承)と `garden/plots/`(Garden 正本)の両方に存在するものがある。
**Garden 化済みの業務は garden/plots/ が常に正本**。HMC 側は業務知識の参照用として残置(削除しない。合言葉「業務知識は継承、起動と承認だけ Garden に変える」)。

| 業務 | 正本 | HMC 側の扱い |
|---|---|---|
| シフト管理 | [garden/plots/shift_manager/SKILL.md](plots/shift_manager/SKILL.md) | `.agent/skills/shift_manager/` = 参照のみ(冒頭バナー有) |
| 経費登録 | [garden/plots/expense_processor/SKILL.md](plots/expense_processor/SKILL.md) | `.agent/skills/expense_processor/` = 参照のみ(冒頭バナー有) |
| 日次タスク管理 | [garden/plots/daily-pilot/SKILL.md](plots/daily-pilot/SKILL.md) | `.agent/skills/hmc_pilot/` = 参照のみ(冒頭バナー有) |
| 請求書処理 | [garden/plots/invoice_processor/SKILL.md](plots/invoice_processor/SKILL.md) | `.agent/skills/invoice_processor/` = 参照のみ(冒頭バナー有、S41) |
| 上記以外の 7 業務 | `.agent/skills/{name}/SKILL.md`(HMC 運用継続中) | Garden 化時に plot_gardener を通す |

業務手順(workflow)の正本は従来通り [`garden/soil/workflows/`](soil/workflows/)(CLAUDE.md 参照)。本表は SKILL(実行手順書)レイヤーの正本を定める。

---

## 4. 失敗時の見るところ(共通リファレンス)

困った時に見る場所を一箇所に。

### ログファイル

| 何 | パス |
|---|---|
| 種の実行ログ | VPS `/home/vps-harappa/garden/log/{today}-{seed}.log` |
| send_pending(配信ディスパッチャ) | VPS `/home/vps-harappa/garden/log/send-pending.log` |
| ランチャー | VPS `/home/vps-harappa/garden/log/launcher.log` |
| mirror daemon | `ssh harappa "docker logs garden-mirror-daemon"` |
| writeback daemon | `ssh harappa "docker logs garden-writeback-daemon"` |
| garden-gaku-co bot | VPS `/home/vps-harappa/garden/log/bot.log` |
| kodomon-sync(WSL 側) | `/tmp/kodomon-sync.log` |
| 朝の口火 / 夜の cheer | VPS `/home/vps-harappa/garden/log/morning-greet.log` / `night-cheer.log` |
| send_pending cron | VPS `/home/vps-harappa/garden/log/send-pending-cron.log` |

### board の状態

| ディレクトリ | 中身 |
|---|---|
| `garden/board/pending/` | 承認待ち(`status: pending` で初回承認依頼通知 → `approved`/`test` でディスパッチ) |
| `garden/board/processed/` | 承認 → 配信完了済み |
| `garden/board/failed/*.FAILED.md` | 種が `on_failure` で起草した失敗 board / S25 連続失敗で auto-quarantine された board |
| `garden/board/triage/{today}-*.md` | 朝の Triage(daily-pilot Mode 1) |
| `garden/board/quarantine/` | 手動退避用(S25 2026-06-02 で `_test-dummy.md` を退避済) |

### S25 で導入された連続失敗ガード

- 種ディスパッチが連続 N 回(default 3)失敗すると `garden/board/failed/{name}.FAILED.md` に自動退避
- 通知は **1 通目 ❌ + N 回目 ⚠️** の 2 通で打ち止め(spam しない)
- board frontmatter に `fail_count` / `last_fail_at` / `last_fail_reason` が記録される
- env: `SEND_PENDING_FAIL_THRESHOLD`(default 3)で閾値変更可

### VPS 接続

```bash
ssh harappa                                # SSH 接続
ssh harappa "crontab -l"                   # cron 一覧
ssh harappa "ls /home/vps-harappa/garden/board/pending/"   # 承認待ち board
ssh harappa "tail -50 /home/vps-harappa/garden/log/send-pending.log"
```

---

## 5. path 大移動チェックリスト(計画時 + 完了検証用)

board / log / soil / memory など **複数レイヤーで参照される path を移動する時に必ず通す確認表**。S27(board/log を vault 外へ)で多数のレイヤーを更新したが、S28 朝に **`night_cheer.py` と `~/.claude/settings.json` の 2 箇所が漏れていた** ことが判明。同じ取りこぼしを構造的に防ぐためのチェックリスト。

> 使い方: path 移動の Pull Request / セッションで、下記の各層を上から順に点検。該当しないレイヤーはチェック不要だが、**「該当しない」と判断したこと自体は記録** する。

### 5.1 コード層(env default + path 解決ロジック)

| 対象 | 確認ポイント | S27 例 |
|---|---|---|
| `services/garden-gaku-co/send_pending.py` | `BOARD_DIR` / `LOG_DIR` 等 env default | S27 で更新済 |
| `services/garden-gaku-co/bot.py` | board / log 参照 | S27 で確認 |
| `services/garden-gaku-co/morning_greet.py` | log 参照 + 関連ファイル参照 | S27 で更新 |
| **`services/garden-gaku-co/night_cheer.py`** | **`LOG_DIR` 等 env / log path 計算** | **S28 で漏れ発覚 → 修正** |
| `services/garden-gaku-co/memory_logger.py` | RAW 出力先 | path 移動時は要確認 |
| `services/launcher/launcher.mjs` | log 出力先 / board 参照 | S27 で更新済 |
| 各 seed の `run-*.sh` ラッパー | 環境変数 / 引数の path | S27 で更新済 |

**鉄則**: env default は「**新パスへの切り替え**」ではなく「**env 上書き優先 + default を新パスに**」のパターンに。VPS 側 cron で env 設定を忘れても動く設計に。

### 5.2 設定層(permission + cron)

| 対象 | 確認ポイント | S27 例 |
|---|---|---|
| **VPS `~/.claude/settings.json`** | **`permissions.allow` の `Write(...)` / `Edit(...)` / `Read(...)` 行が新パスをカバーするか** | **S28 で漏れ発覚 → 修正** |
| VPS `crontab -l` | cron entry の log 出力リダイレクト先 | S27 で更新済 |
| VPS `~/.claude/CLAUDE.md` | path 言及があるか | path 移動時は要確認 |

**罠**: `settings.json` で path-scoped allow が無いと、Claude が「権限お待ちしてます」と止まる(失敗ではなく沈黙)。dry-run の `claude -p ... --model haiku` で実際に Write を試して通るか確認。

### 5.3 種ファイル層(frontmatter + prompt)

| 対象 | 確認ポイント |
|---|---|
| `garden/seeds/**/*.md` frontmatter の `board.path` | board 移動の影響範囲 |
| 種 prompt 内の log パス参照 | `==NOTIFY== ... ==END==` 等の出力指示 |
| 種 prompt 内のディレクトリ glob | `garden/board/pending/*.md` 等 |

### 5.4 ドキュメント層

| 対象 | 確認ポイント |
|---|---|
| `garden/OPERATIONS.md` | path 参照箇所 |
| `garden/MAP.md` | 区画表 + ロードマップの path 言及 |
| `garden/CHARTER.md` | 言及があれば |
| `garden/plots/**/SKILL.md` | board 参照箇所 |
| ADR を新規起票 | path 移動の経緯と新ルール |
| `CLAUDE.md`(repo / VPS) | セッションプロトコルの path 言及 |

### 5.5 daemon 層

| 対象 | 確認ポイント | S27 例 |
|---|---|---|
| `services/mirror-daemon/` | `EXCLUDE_PREFIXES` / 監視 root | S27 で `EXCLUDE_PREFIXES=garden/board/,garden/log/` 新設 |
| `services/writeback-daemon/` | `EXCLUDE_PREFIXES` / 監視 root | 同上 |
| 各種 sync スクリプト | rsync の `--exclude` / source / dest | path 移動範囲に応じて |

### 5.6 完了検証(副作用ゼロのスモークテスト)

path 移動完了時に **必ず通す検証**:

```bash
# 1. settings.json で path が allow されているか(軽量 write テスト)
ssh harappa "claude -p 'Use the Write tool to create the file /home/vps-harappa/{NEW_PATH}/_perm-test.log with the single line content: perm-check-ok' --model haiku"
ssh harappa "ls /home/vps-harappa/{NEW_PATH}/_perm-test.log && rm /home/vps-harappa/{NEW_PATH}/_perm-test.log"

# 2. cron 起動を想定したスクリプトを「副作用ゼロ」で叩く
#    NG: ./run-night-cheer.sh を朝に実行 → 内部 today_jst() が今日依存で動作変わる + Discord 警告ノイズ
#    OK: Python 関数を直接呼び、特定日付で path 解決のみ確認
ssh harappa "cd /home/vps-harappa/garden/services/garden-gaku-co && python3 -c '
import datetime, night_cheer
d = datetime.date(2026, 6, 2)
log_text, path = night_cheer.read_review_log(d)
print(\"path:\", path, \"size:\", len(log_text) if log_text else 0)
'"
```

**罠の言語化**(S28 の学び):

- **cron 想定スクリプトの手動実行は罠**:`today_jst()` のような「今日依存ロジック」は、cron 時刻と手動実行時刻で振る舞いが変わる。手動デバッグの前に内部ロジックを確認、または関数を直接呼ぶ副作用ゼロの検証に切り替える
- **失敗ではなく "沈黙" が起きる**:permission 不足は exit 0 のままログが残らないだけ = 監視で見つけにくい。完了検証で明示的に Write を試す

### 5.7 path 移動の "5 分後ふりかえり"

PR をマージ / セッションを閉じる前に **チェックリストを上から眺め直す**:

- [ ] コード層: env default 切り替え完了
- [ ] 設定層: settings.json + cron 完了
- [ ] 種ファイル層: frontmatter + prompt 完了
- [ ] ドキュメント層: OPERATIONS / MAP / ADR / CLAUDE 完了
- [ ] daemon 層: EXCLUDE_PREFIXES + sync スクリプト完了
- [ ] 完了検証: 軽量 write テスト + 副作用ゼロ関数呼び出し
- [ ] **24h 後の検証ポイントを宿題化**(夜の cron / 朝の cron / 別 cron 種が初回稼働するタイミングを明記)

最後の 24h 後検証ポイント明記が重要。S27 → S28 の取りこぼし発覚は「夜の Discord 警告通知」がきっかけだったが、これを **事前に「次の cron 種起動時に NOTIFY が log に残るか確認」** と宿題化していれば、警告が来る前に気づけた。

### 5.8 関連

- 起点 ADR: [2026-06-02 board-and-log-out-of-vault](../docs/decisions/2026-06-02-board-and-log-out-of-vault.md)
- 取りこぼしセッション: [2026-06-02 セッション27](../docs/sessions/2026-06-02-session27.md)
- 学びセッション: [2026-06-03 セッション28](../docs/sessions/2026-06-03-session28.md)
- 本章の起点セッション: [2026-06-03 セッション29](../docs/sessions/2026-06-03-session29.md)

---

## 6. 関連

- 戦略地図: [`garden/MAP.md`](MAP.md)
- 規範: [`garden/CHARTER.md`](CHARTER.md)
- 起源: [`docs/origin.md`](../docs/origin.md)
- コンセプト: [`docs/concept.md`](../docs/concept.md)
- Garden 語彙: [`docs/garden-vocabulary.md`](../docs/garden-vocabulary.md)
- 測量士運用: [`docs/surveyor/README.md`](../docs/surveyor/README.md)
- 初版起点 ADR: 本ファイルは ADR 起票せず、測量士の手紙 [2026-06-02](../docs/surveyor/letters/2026-06-02.md) 提案 1+2+4 への応答として起草
- §5 path 大移動チェックリスト追記: [2026-06-03 セッション29](../docs/sessions/2026-06-03-session29.md) で追加(S28 学び由来、ADR なし)
