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
| **Discord master ch** | 承認依頼 / 配信完了 / 失敗通知 / 朝の口火 / 夜のレポート | 随時 + 06:40 / 22:40 | 短文返信、または Obsidian で開く |
| **朝の口火(06:40 Discord)** | 当日 `active_tasks` のサマリ + Triage 数 + board 承認待ち件数 | 1 日 1 回 | 一日の見通しを得る・対話開始 |
| **夜のレポート(22:40 Discord)** | 完了 / 持ち越し / 翌日サマリ | 1 日 1 回 | 終わりの確認 |
| **Obsidian: `hmc_tasks/active_tasks.md`** | 今日のタスク一覧(`deadline ≦ today` のみ) | 随時 | チェック / 締切編集 / `## 追加` でタスク投入 |
| **Obsidian: `garden/board/pending/*.md`** | 承認待ちの剪定依頼(shift_manager / daily-pilot 等) | 随時 | 中身を読んで `status: approved` / `status: test` / 修正 |
| **Obsidian: `garden/board/triage/{today}-*.md`** | 朝の Triage(対話用) | 1 日 1 回 | 軸 A/B/C に返答(LINE 短文 or 直接編集) |

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

1. **月末 22:00**: `month-end-working-hours-prep` 種発火 → `garden/board/pending/{date}-working-hours-prep.md` 起草 → Discord master 通知
2. **ガクチョ**: Obsidian で開き → 当月稼働シートの状態を確認(Mode 1 のチェックリスト) → `[x] 集計実行` チェック後 `status: approved`
3. **send_pending.py** が `generate_working_hours.py` 実行 → 稼働表タブ生成 → 完了通知
4. **ガクチョ**: 放サボ列を手入力 or コドモン CSV を `garden/inbox/kodomon/` に置く(→ Card 3 へ)
5. **月初 1 日 08:00**: `monthly-shift-survey` 種発火 → 翌月アンケート board 起草 → Discord master 通知
6. **ガクチョ**: 文面確認 → `status: approved`(dummy モードでは Discord master プレビューが届くので staff LINE に手動コピー)
7. **月初 1 日 09:00**: `monthly-working-hours-confirmation` 種発火(現状 dummy モード、staff 見せ方未確定で blocked: true)
8. **月初 10 日 08:00**: `monthly-shift-finalize` 種(構想)

**失敗時に見るところ**:

- VPS: `/home/vps-harappa/garden-mirror/garden/log/{today}-{seed}.log`
- VPS: `/home/vps-harappa/garden-mirror/garden/log/send-pending.log`
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

- VPS: `/home/vps-harappa/garden-mirror/garden/log/{today}-morning-briefing.log` 等
- VPS: `/home/vps-harappa/garden-mirror/garden/log/launcher.log`
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
- VPS: `/home/vps-harappa/garden-mirror/garden/log/run_month_end_collect.log`
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

- VPS: `/home/vps-harappa/garden-mirror/garden/log/index-refresh.log`
- VPS: `garden/soil/log.md` の末尾(動作の有無を確認)

**関連ファイル**:

- SKILL: [`garden/mycelium/SKILL.md`](mycelium/SKILL.md)
- 種: [`garden/seeds/mycelium/index-refresh.md`](seeds/mycelium/index-refresh.md)
- 維持対象: [`garden/soil/index.md`](soil/index.md) / [`garden/soil/log.md`](soil/log.md)

---

## 3. HMC → HMG 移行マトリクス

業務単位で「HMC ではどう動いていたか / HMG ではどこまで移ったか / ガクチョの作業」を一覧化(2026-06-02 測量士提案 2 採用)。

凡例: ✅ HMG 完全 / 🚧 部分移行・実装中 / ⬜ 未着手・HMC のみ / 🆕 HMG ネイティブ(HMC には無い)

| 業務 | HMC | HMG | 段階 | ガクチョの作業 |
|---|---|---|---|---|
| **シフト管理(月次)** | `apps/shift_manager/` 全体 | shift_manager plot + 種 3 本 active + Python scripts 移植済 | ✅ 完了(残: Mode 3 見せ方未確定、Mode 4 構想) | 月末 board 確認 → 集計実行 / 月初 dummy 配信を staff LINE に手動コピー / 6/10 までに精算ルート確認 |
| **日次タスク管理** | `apps/hmc_pilot` SKILL + active_tasks/backlog 手動運用 | daily-pilot plot + 種 3 本 active + bot 対話 + active/backlog 自動構築 | ✅ 完了 | 朝 Discord で対話 / Obsidian で backlog 編集 / 夜の対話で返答 |
| **コドモン CSV 取込** | (HMC 期は無し、Garden で新規) | kodomon-sync(α)+ import_kodomon.py | 🆕 ✅ 完了(γ は将来) | 月末までにコドモン Web で CSV エクスポート → `garden/inbox/kodomon/` に置く |
| **土壌維持(soil index)** | (HMC 期は無し) | mycelium index-refresh active | 🆕 ✅ 完了(Stage 1) | なし(自律) |
| **永続記憶** | (HMC 期は無し) | RAW logging 稼働(Stage A)、ingest skeleton(Stage A.5 未実装) | 🆕 🚧 実装中 | なし(自律、Stage A.5 完成後に挙動観察) |
| **経費登録** | `apps/expense_processor` | 未移植 | ⬜ | HMC で従来通り |
| **売上記帳(STORES/Square)** | `apps/finance_importer` | 未移植 | ⬜ | HMC で従来通り |
| **請求書処理** | `apps/invoice_processor` | 未移植 | ⬜ | HMC で従来通り |
| **メール整理** | `apps/email_organizer` | 未移植 | ⬜ | HMC で従来通り |
| **議事録(Plaud等)** | `apps/minute_maker` | 未移植 | ⬜ | HMC で従来通り |
| **SNS 投稿** | `apps/sns_pilot` | 未移植 | ⬜ | HMC で従来通り |
| **部門振り分け監査** | `apps/freee_auditor` | 未移植 | ⬜ | HMC で従来通り |
| **財務分析(PL/CF)** | `apps/finance_analyzer` | 未移植 | ⬜ | HMC で従来通り |
| **手紙仕分け** | `apps/letter_opener` | 未移植 | ⬜ | HMC で従来通り |

**移行優先度の現在地**(S25 時点):

- 次の本命候補: **永続記憶 Stage A.5 実装**(本セッションは見通し整備で消費、S26 以降)
- 並行候補: **finance 系 / invoice_processor / expense_processor の Garden 化**(Phase 3b の secret 管理整備と同期)
- 後追い: SNS / 議事録 / メール / 監査 / 分析 / 手紙

---

## 4. 失敗時の見るところ(共通リファレンス)

困った時に見る場所を一箇所に。

### ログファイル

| 何 | パス |
|---|---|
| 種の実行ログ | VPS `/home/vps-harappa/garden-mirror/garden/log/{today}-{seed}.log` |
| send_pending(配信ディスパッチャ) | VPS `/home/vps-harappa/garden-mirror/garden/log/send-pending.log` |
| ランチャー | VPS `/home/vps-harappa/garden-mirror/garden/log/launcher.log` |
| mirror daemon | `ssh harappa "docker logs garden-mirror-daemon"` |
| writeback daemon | `ssh harappa "docker logs garden-writeback-daemon"` |
| garden-gaku-co bot | VPS `/home/vps-harappa/garden-mirror/garden/log/bot.log` |
| kodomon-sync(WSL 側) | `/tmp/kodomon-sync.log` |
| 朝の口火 / 夜の cheer | VPS `/home/vps-harappa/garden-mirror/garden/log/morning-greet.log` / `night-cheer.log` |
| send_pending cron | VPS `/home/vps-harappa/garden-mirror/garden/log/send-pending-cron.log` |

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
ssh harappa "ls /home/vps-harappa/garden-mirror/garden/board/pending/"   # 承認待ち board
ssh harappa "tail -50 /home/vps-harappa/garden-mirror/garden/log/send-pending.log"
```

---

## 5. 関連

- 戦略地図: [`garden/MAP.md`](MAP.md)
- 規範: [`garden/CHARTER.md`](CHARTER.md)
- 起源: [`docs/origin.md`](../docs/origin.md)
- コンセプト: [`docs/concept.md`](../docs/concept.md)
- Garden 語彙: [`docs/garden-vocabulary.md`](../docs/garden-vocabulary.md)
- 測量士運用: [`docs/surveyor/README.md`](../docs/surveyor/README.md)
- 初版起点 ADR: 本ファイルは ADR 起票せず、測量士の手紙 [2026-06-02](../docs/surveyor/letters/2026-06-02.md) 提案 1+2+4 への応答として起草
