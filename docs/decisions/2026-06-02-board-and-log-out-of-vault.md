---
title: board と log を Obsidian vault 外へ配置(LiveSync 巻き戻し事故対策)
status: accepted
date: 2026-06-02
session: 27
authors:
  - claude (with ガクチョ, セッション27)
supersedes:
  - "[2026-05-27 vault-folder-layout](2026-05-27-vault-folder-layout.md)(garden/board と garden/log の vault 内配置を再決定)"
  - "[2026-05-27 garden-board-structure](2026-05-27-garden-board-structure.md)(board の物理配置のみ — pending/processed/triage の内部構造は維持)"
related:
  - "[2026-05-28 garden-gaku-co-interaction-layer](2026-05-28-garden-gaku-co-interaction-layer.md)"
  - "[2026-06-01 board-lifecycle-and-notification](2026-06-01-board-lifecycle-and-notification.md)"
  - "[2026-06-02 soil-source-of-truth](2026-06-02-soil-source-of-truth.md)(soil の正本ルール)"
---

# board と log を Obsidian vault 外へ配置(LiveSync 巻き戻し事故対策)

## 文脈

2026-06-02 朝、5 月稼働サマリ(`2026-05_稼働時間` タブ)で **放サボ列が全消失** する事故が発生(セッション27 で復元済み)。原因調査により、構造的な不整合が判明した。

### 事故メカニズム

`garden-mirror/` は **Obsidian Self-hosted LiveSync**(CouchDB + mirror-daemon + writeback-daemon の 3 コンテナ構成)経由でガクチョの Obsidian 端末(モバイル/デスクトップ)と双方向同期されている。

board のライフサイクル(pending → processed)は VPS 上の `send_pending.py` が実行するが、別端末の Obsidian が古い「pending にある状態」を保持してオフラインだった場合、復帰時に CouchDB 経由で **削除済みの board を pending/ に再生させてしまう**。これにより既に approved → processed と進んだ board が再度 pending に湧き、`send_pending.py` が **同じ shell コマンド(`run_month_end_collect.sh`)を再実行** → `generate_working_hours.py` が `2026-05_稼働時間` タブを再生成 → 手動入力済の放サボ列が消える。

実際の事象タイムライン:
- 6/1 22:48:19 — 1 回目実行(approved → processed)、放サボ列はガクチョ入力で埋まる
- 6/1 夜 〜 6/2 09:04:36 の間 — 別端末から CouchDB に stale state が push される
- 6/2 09:04:36 — mirror-daemon が CouchDB → VPS fs に同期、5 ファイル(working-hours-prep / monthly-shift-survey / monthly-working-hours-confirmation / `_test-dummy.md` / `dummy-test-s22.md`)が pending/ に蘇生
- 6/2 09:05:01 — send_pending.py が再検出 → `run_month_end_collect.sh 2026-05` を再実行
- 6/2 09:05:19 — `generate_working_hours.py` がタブ再生成、**放サボ列が全消失**

### 連続失敗ガード(S25)が機能しなかった理由

S25 で導入した `fail_count` ベースの連続失敗ガード(N 回失敗で `board/failed/` に自動退避)も、**LiveSync が `fail_count` フィールドを毎ティック上書きでリセット** していたため、閾値に到達せず機能しなかった。Discord に同じ失敗通知が毎分流れ続けるスパムを生んだ原因も同じ。

## 検討した選択肢

### 案 A: LiveSync の ignore に `garden/board/**` を追加(board は vault 内のまま)

メリット: 既存配置を変えない。
デメリット: 「vault 内に存在するが同期されない」という変則状態。Obsidian で見えるが Obsidian 編集が VPS に伝播しない(逆もしかり)。意味的に混乱する。

### 案 B: board と log を vault 外(`/home/vps-harappa/garden/`)へ移動(本決定)

メリット:
- vault は「Obsidian で読み書きしたいもの(soil 等)」だけに絞れる
- board と log は VPS が **唯一の書き手 / 読み手** で、LiveSync 干渉の余地がゼロ
- ガクコ(Discord bot)が board を編集する権限を path-scoped で与えやすい(`/home/vps-harappa/garden/board/**`)
- 関心の分離: `garden-mirror/` = ガクチョの Obsidian 共有領域 / `garden/` = VPS スクリプトの作業領域

デメリット:
- ガクチョが Obsidian で board / log を見れなくなる
  → 承認運用を **Discord ガクコ経由** に切り替えることで補う(本 ADR と同時に実装、shift_manager SKILL Mode 5 / daily-pilot SKILL Mode 2 で承認応答ルール化)
  → 「board 見せて」「ログ確認」とガクコに頼めば中身を Discord に貼ってくれる

### 案 C: vault 自体を廃止して全部 git で管理

却下: soil(知識ベース)や inbox/kodomon(モバイルからの CSV アップロード)等、Obsidian 利便性が必要な領域は残る。

## 決定

**案 B を採用。** `garden/board/` と `garden/log/` を `/home/vps-harappa/garden/{board,log}/` に移行し、Obsidian vault の外側で管理する。

承認運用は Discord 経由(ガクコへの自然言語指示)に切り替え。Obsidian 操作を不要にする。

## 新しい配置

```
/home/vps-harappa/
├── garden-mirror/                 ← Obsidian vault(LiveSync 対象)
│   └── garden/
│       ├── soil/                  ← ✅ vault 内のまま(ガクチョが Obsidian で読む知識ベース)
│       ├── inbox/                 ← ✅ vault 内のまま(モバイルからの CSV アップロード経路)
│       └── memory/master/raw/     ← △ 当面 vault 内(将来再検討)
│
└── garden/                        ← VPS スクリプト領域(LiveSync 対象外)
    ├── CHARTER.md
    ├── plots/, seeds/, services/, mycelium/
    ├── board/                     ← ★ 新配置(2026-06-02 移行)
    │   ├── pending/
    │   ├── processed/
    │   ├── failed/
    │   ├── triage/
    │   └── quarantine/
    └── log/                       ← ★ 新配置(2026-06-02 移行)
```

## 影響と実装(セッション27 同時実装)

### コード
- `garden/services/garden-gaku-co/send_pending.py` — env default の `BOARD_*` / `LOG_PATH` を新パスに
- `garden/services/garden-gaku-co/bot.py` — `BOARD_DIR` 環境変数を新設、`triage_board_path` で利用
- `garden/services/garden-gaku-co/run-*.sh`(4 本)— `LOG=` を新パスに
- `garden/services/launcher/launcher.mjs` — `LOG_ROOT` default を新パスに

### 種ファイル(9 ファイル)
sed 一括置換: `/home/vps-harappa/garden-mirror/garden/{board,log}/` → `/home/vps-harappa/garden/{board,log}/`

### ドキュメント
- `garden/OPERATIONS.md` — 「Obsidian で board を開く」→「Discord でガクコに承認」に書き換え
- `garden/plots/shift_manager/SKILL.md` Mode 5(Discord Approval Response)新設
- `garden/plots/daily-pilot/SKILL.md` Mode 2 編集権限表に shift_manager 承認ルート追加

### VPS 物理移行
1. ガクチョが LiveSync の ignore pattern に `garden/board/` と `garden/log/` を追加(これを **先にやる** — 旧場所削除で別端末との同期波及を防ぐため)
2. `mv /home/vps-harappa/garden-mirror/garden/board /home/vps-harappa/garden/board`
3. `mv /home/vps-harappa/garden-mirror/garden/log /home/vps-harappa/garden/log`
4. `crontab -l | sed 's|garden-mirror/garden/log|garden/log|g' | crontab -`(cron の log redirect path 更新)
5. CouchDB 側に残った board / log ドキュメントは別途削除(または ignore で放置)

## 既存 ADR との関係

- [2026-05-27 vault-folder-layout](2026-05-27-vault-folder-layout.md) — `garden/board/` と `garden/log/` を vault 内に置く決定だった部分を **本 ADR が上書き(supersede)**。`soil/` `inbox/` 等の他配置は維持
- [2026-05-27 garden-board-structure](2026-05-27-garden-board-structure.md) — board の内部構造(pending / processed / failed / triage / quarantine の 5 系統)は **維持**。物理配置だけ移動

## リスクと監視

- **CouchDB に旧データが残る**: writeback-daemon が「削除」を伝播するが、ignore 設定により mirror-daemon 側で再受信しない。万一同期波及が起きた場合は CouchDB の Fauxton UI で直接削除可能
- **承認操作の習熟度**: Discord でのガクコ承認運用に慣れるまで、ガクチョが Obsidian を開きに行く癖が残る → board は vault 外なので「開くファイルが無い」状態が習慣矯正を助ける
- **board の閲覧性**: 過去の processed/failed を遡る時、ガクコに「先月の processed リストアップして」「あの board の中身見せて」と聞けば応答する([shift_manager SKILL Mode 5](../../garden/plots/shift_manager/SKILL.md#mode-5-discord-approval-response承認応答))
