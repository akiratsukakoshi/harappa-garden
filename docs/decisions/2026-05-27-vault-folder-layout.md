# gakuchovault 内の Garden フォルダ配置

- **日付**: 2026-05-27
- **記録**: セッション13
- **決定者**: 塚越さん(庭師) / Claude
- **ステータス**: ⚠️ **部分的に supersede**(2026-06-02 セッション27 で `garden/board/` と `garden/log/` を vault 外へ移動。`soil/` `inbox/` 等の他配置は維持。詳細: [ADR 2026-06-02 board-and-log-out-of-vault](2026-06-02-board-and-log-out-of-vault.md))

## 背景

セッション12 で **mirror-daemon が稼働開始**。vault(`gakuchovault`)が VPS の `/home/vps-harappa/garden-mirror/` に **平文 MD として展開** されるようになり、daily-pilot 4 本の種が「素朴に MD を読める」状態が成立。

ここで配置設計の論点が立つ:

| 論点 | 内容 |
|---|---|
| 既存 `hmc_tasks/` の扱い | HMC 時代から運用中の BAA フロー実体(backlog/active_tasks/archive/recurring_master)。daily-pilot 種の I/O 先になる |
| `garden/` フォルダの新設粒度 | 連絡板(`board/`)・inbox・ログ等をどこに置くか |
| 種ファイル本体の所在 | `garden/seeds/*.md` を vault にも置くか、HMG repo に閉じるか |

## 現状調査(2026-05-27 時点)

VPS mirror トップレベル:

```
/home/vps-harappa/garden-mirror/
├── 00_MOC/                    (主索引)
├── AGENTS.md                  (LiveSync テスト由来 / 整理対象)
├── archive/
├── development/
├── digihara/
├── garden-livesync-test.md.md (テスト残骸 / 整理対象)
├── gardenテスト.md            (テスト残骸 / 整理対象)
├── hmc_tasks/                 ← 既存の BAA フロー実体
│   ├── active_tasks.md (23行)
│   ├── archive.md (526行)
│   ├── backlog.md (28行)
│   ├── recurring_master.md (24行、daily/weekly/monthly/yearly 言語化済・id なし)
│   ├── letter_tasks.md, mail_task.md, 追加タスク.md
├── newsletter/
├── personal/
├── 経営/
├── 軽量なtts.md               (テスト残骸 / 整理対象)
└── 野比買い出し.md            (テスト残骸 / 整理対象)
```

## 決定

### 決定 1: `hmc_tasks/` はそのまま流用 — daily-pilot 種の I/O 先として確定

- フォルダ名 `hmc_tasks/` は **変更しない**(リネームは LiveSync 上で全 doc ID 再生成 → 再同期コスト発生のため回避)
- 中の 3 ファイル(`backlog.md` / `active_tasks.md` / `archive.md`)+ `recurring_master.md` は **そのまま daily-pilot 種の I/O 先**
- HMG/HMC の語彙議論とフォルダ名の整合は **無視**(実態の継続性を優先)
- recurring_master.md には **後付けで `id:` を付与**(案 E の前提条件、別タイミングで実施)

「H**MC** タスク」という名前が残るが、これは "塚越さんのデイリータスク管理" の歴史的呼称として固定。HMG 側で別名運用したい場合は `00_MOC/` の主索引で別名表示を用意する程度で対応可。

### 決定 2: vault 直下に `garden/` フォルダを新設(連絡板・inbox 等の置き場)

```
gakuchovault/
├── 00_MOC/                    (既存)
├── hmc_tasks/                 (既存・daily-pilot 種の I/O 先)
├── garden/                    ← 新設
│   ├── README.md              (本 vault 内 garden の説明)
│   ├── board/                 (連絡板。剪定依頼の置き場)
│   │   ├── pending/           (剪定待ち)
│   │   └── processed/         (剪定済み)
│   ├── inbox/                 (event 種の入口。inbox-process が振り分け)
│   │   ├── processed/         (振り分け済み)
│   │   └── archive/           (履歴保管・watcher exclude)
│   └── log/                   (種実行ログ。`YYYY-MM-DD-{seed}.log`)
├── ... (既存フォルダはそのまま)
```

**論拠**:

- `garden/` 配下は **HMG が能動的に書き込む領域**。既存フォルダ(`personal/` `経営/` `archive/` 等)と切り分けて衝突回避
- `hmc_tasks/` と `garden/` の二段運用:
  - `hmc_tasks/` = 既存 BAA フローの実体(タスク本体)
  - `garden/` = 種が動かす **入出力レイヤ**(連絡板・inbox・ログ)
- 内部構造の詳細(`board/pending` の中身構造、ファイル命名規約等)は **別 ADR**: [garden-board-structure ADR](2026-05-27-garden-board-structure.md) で確定

### 決定 3: 種ファイル本体(`garden/seeds/*.md`)は vault にミラーしない

- 種ファイルは **HMG repo のみ**(`/home/tukapontas/harappa-garden/garden/seeds/`)
- 編集は VS Code(git 管理対象、レビュー可、PR 可)
- Obsidian からは見えない(=普段触らない、見える必要がない)

**論拠**:

- 種ファイルは **コード相当**(frontmatter + 実行指示)で、git 管理が正しい依存形
- vault にコピーすると 2 箇所同期の整合性管理コストが発生(LiveSync ↔ git)
- 種編集の頻度は低い(設計確定後はランナータイム挙動の調整が中心)

ただし以下の **メタデータは vault 側にも置く**:

| ファイル | 置き場 | 用途 |
|---|---|---|
| 種実行ログ | `garden/log/{date}-{seed}.log` | 種ランチャーが書き込み・庭師が Obsidian で参照可 |
| 種一覧の MOC | `garden/README.md` or `00_MOC/種.md`(任意) | Obsidian から種の存在を俯瞰可能にする(リンクは HMG repo の GitHub URL 等) |

## VPS 側のパス整合

VPS 上の対応:

```
/home/vps-harappa/garden-mirror/    ← LiveSync の平文ミラー
├── hmc_tasks/                       ← daily-pilot 種の I/O 先(read + write)
└── garden/                          ← 連絡板・inbox・ログ(read + write)
```

**重要**: mirror-daemon は **現状 単方向(CouchDB → MD)**。種が `hmc_tasks/backlog.md` や `garden/board/` に **書き込み** たい場合の経路は未確定(セッション12 ADR の保留事項)。本 ADR では「書き込みは別 ADR で確定」とだけ明記し、配置の合意のみ先行させる。

書き込み経路の候補(Phase 3a A-1 で確定):

| 候補 | 概要 | 主トレード |
|---|---|---|
| (i) mirror-daemon の双方向化 | mirror-daemon に書き戻し機能を追加 | 実装コスト中、chunk 化暗号化を自前で書く必要 |
| (ii) PouchDB / CouchDB クライアント直接書き込み | 種が直接 CouchDB に write、mirror がそれを反映 | LiveSync の暗号化を再度自前実装 |
| (iii) vault 経由(VPS から PC vault に何らかの方法で書き込み) | 経路が複雑、回避傾向 | — |

→ Phase 3a A-1(ランチャー実装)時に実機検証して確定。

## 改訂履歴

- **2026-05-27 (S13 セッション内)**: `inbox/.archive/` → `inbox/archive/` に修正。Obsidian が `.` 先頭フォルダ作成を拒否するため(実機検証で判明)。動作上の差はなく、watcher exclude を明示的に書く必要があるだけ。

## 移行ステップ(本 ADR 確定後の作業順)

1. **`garden/board-structure` ADR を確定** ([garden-board-structure ADR](2026-05-27-garden-board-structure.md))
2. **HMG repo 側で `garden/board/` 試作領域を作る**(`.scratch/board-template/` 等)
3. **vault 側に `garden/` フォルダを新設**(Obsidian で塚越さんが作成 → LiveSync で VPS にも反映)
4. **`hmc_tasks/recurring_master.md` に `id:` を後付け**(既存 14 件程度)
5. **daily-pilot 種の prompt 内パスを実パスに統一**(`/home/vps-harappa/garden-mirror/hmc_tasks/backlog.md` 等)
6. **テスト残骸の整理**(`gardenテスト.md` 等を `archive/` に移動 or 削除)
7. **Phase 3a A-1 で書き込み経路の実機検証**

## トレードオフ

### 採用理由

- 既存 `hmc_tasks/` の継続性を守る(リネームによる事故ゼロ)
- 新規 `garden/` で HMG 領域を明確に分離(既存フォルダと干渉しない)
- 種ファイルを repo に閉じることで、コード相当の管理規律を維持

### 妥協点

- フォルダ名 `hmc_tasks/` が `HMC` のままで「HMG 化されてない」感覚は残る
  - 対策: README で「歴史的呼称・実体は HMG の daily タスク BAA」と明記
- 書き込み経路が未確定のまま配置先だけ決める
  - 対策: 配置と書き込み経路は独立して決められる(配置が決まれば書き込み実装の議論が具体化する)
- vault と repo の 2 箇所運用(ログは vault・種は repo)
  - 対策: ログは生成物・種は定義 という責務分離で正当化

## 未決事項

- `garden/log/` のログフォーマット(seeds/README.md の `.log/` 規約と整合)
- `garden/README.md` の中身(誰が書くか・MOC への参照を入れるか)
- テスト残骸の整理タイミング(塚越さんの判断)
- Phase 3a A-1 での書き込み経路確定

## 関連

- [garden-board-structure ADR](2026-05-27-garden-board-structure.md) — `garden/board/` の内部構造
- [recurring-respawn-prevention ADR](2026-05-27-recurring-respawn-prevention.md) — recurring_master の `id` 必須化の根拠
- [mirror-daemon-implementation ADR](2026-05-27-mirror-daemon-implementation.md) — mirror-daemon の現在の挙動(単方向)
- [セッション6 ADR(BAA フロー)](2026-05-25-daily-workflow-and-task-master-architecture.md)
- [garden/seeds/README.md](../../garden/seeds/README.md)
