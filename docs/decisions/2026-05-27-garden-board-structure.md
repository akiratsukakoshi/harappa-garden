# 連絡板 `garden/board/` の構造設計

- **日付**: 2026-05-27
- **記録**: セッション13
- **決定者**: 塚越さん(庭師) / Claude
- **ステータス**: 内部構造(pending / processed / failed / triage / quarantine の 5 系統)は **維持**。**物理配置のみ supersede**:vault 内 → vault 外(`/home/vps-harappa/garden/board/`)に 2026-06-02 移行。詳細: [ADR 2026-06-02 board-and-log-out-of-vault](2026-06-02-board-and-log-out-of-vault.md)

## 背景

連絡板(`garden/board/`)は「**剪定依頼 + Triage 質疑応答** を行う場」として、複数 ADR で言及されてきた。

- セッション4 ADR(剪定 3 チャネル振り分け) — `board_with_notify` / `board` チャネル先
- セッション6 ADR(BAA フロー + Triage ハイブリッド) — morning-briefing の Triage 受け皿
- セッション8 — daily-pilot 4 本の draft 内で `garden/board/pending/...` が頻出
- セッション12(mirror-daemon) — 平文 MD として VPS に展開可能になり、実装が現実的に
- セッション13 — [vault-folder-layout ADR](2026-05-27-vault-folder-layout.md) で vault 直下に `garden/` を新設する方針が確定

しかし **board の内部構造そのもの**(ディレクトリ・ファイル命名・テンプレ・ライフサイクル)は未確定で、既存 draft 間でも揺れがあった:

| ファイル | 配置記述 |
|---|---|
| `monthly-shift-survey.md` | `garden/board/pending/{today}-monthly-shift-survey.md` |
| `morning-briefing.md` | `/opt/garden/board/{today}-morning-briefing.md`(直下、絶対パス) |
| `night-review.md` | `/opt/garden/tasks/...`(別カテゴリ・絶対パス) |
| `inbox-process.md` | `garden/inbox/...`(別カテゴリ) |

本 ADR で **配置・命名・テンプレ・ライフサイクル・操作経路** を統一する。

## 決定

### 決定 1: 基準パス = `/home/vps-harappa/garden-mirror/` (VPS) / `<vault root>/` (PC)

VPS 上の絶対パス基準:

```
/home/vps-harappa/garden-mirror/
├── hmc_tasks/                       (BAA + recurring_master、既存)
│   ├── backlog.md
│   ├── active_tasks.md
│   ├── archive.md
│   └── recurring_master.md
├── garden/                          (HMG 新設、vault-folder-layout ADR)
│   ├── README.md
│   ├── board/                       ← 本 ADR の射程
│   │   ├── pending/
│   │   ├── processed/
│   │   └── triage/                  (Triage 系の専用領域、後述)
│   ├── inbox/
│   │   ├── processed/
│   │   └── archive/
│   └── log/
```

種ファイルの `outputs.path` / `execute.prompt` 内パスはすべて **この基準で記述**。`/opt/garden/...` 系の旧記述は draft 修正時に統一する。

### 決定 2: board は 3 ディレクトリ(`pending/` / `processed/` / `triage/`)

```
garden/board/
├── pending/      ← 剪定待ち(配信前下書き・確認待ち)
├── processed/    ← 完了(配信済み・却下済み)
└── triage/       ← Triage 系の専用領域(質疑応答ベース)
```

**なぜ triage/ を分けるか**:

- 剪定系(`pending/processed`)は **「下書き → 承認 → 配信 → 完了」** の単方向ライフサイクル
- Triage 系(morning-briefing)は **「質問 → 回答 → 反映」** の双方向。回答後も同日中に何度もアクセスされる可能性がある
- ライフサイクルが違うので物理的に分けた方がランチャー実装(検索範囲・ファイル命名・移動規則)がシンプル

**triage/ のライフサイクル**:

```
triage/{today}-morning-briefing.md   (午前生成 → 終日参照可)
   ↓ 日次の night-review が処理(回答取り込み)
triage/archive/{today}-morning-briefing.md   (日付付きで保存、削除しない)
```

`archive/` は watcher の exclude 対象(明示的に exclude glob を指定する)。

### 決定 3: ファイル命名規約

| カテゴリ | パターン | 例 |
|---|---|---|
| 剪定系(単発) | `{YYYY-MM-DD}-{seed-name}.md` | `2026-06-01-monthly-shift-survey.md` |
| 剪定系(period 指定) | `{YYYY-MM-DD}-{seed-name}-{period_id}.md` | `2026-06-01-monthly-shift-survey-2026-08.md` |
| Triage 系 | `{YYYY-MM-DD}-{seed-name}.md` | `2026-06-01-morning-briefing.md` |
| ログ | `{YYYY-MM-DD}-{seed-name}.log`(`garden/log/` 直下) | `2026-06-01-night-review.log` |

**注意**:

- 日付は **発火日(JST)**、種実行ログの `started_at` を切り捨てた日付
- 同日複数発火は seed 側の `idempotency.guard` で防止(原則 1 日 1 ファイル)
- `{period_id}` は案 E の `period_id` と一致(daily/monthly/yearly 等)

### 決定 4: board ファイルのテンプレート(必須セクション)

すべての board ファイルは **frontmatter + 本文セクション** の構造を持つ。

#### 剪定系(`pending/`)テンプレート

```markdown
---
type: board
seed: {seed-name}                  # 例: monthly-shift-survey
plot: {plot}                       # 例: shift_manager
period_id: {YYYY-MM} or {YYYY-MM-DD}  # 該当する場合
status: awaiting_pruning           # awaiting_pruning | approved | rejected | sent | send_failed
created: YYYY-MM-DD HH:MM
last_updated: YYYY-MM-DD HH:MM
audit:
  triggered_by: {seed-name}
  log: garden/log/{YYYY-MM-DD}-{seed-name}.log
---

# {一行サマリ}

## 配信本文
{この section の本文がそのまま配信される。塚越さんは編集可}

## 添付情報
{フォーム URL / 関連リンク / 補足}

## 庭師アクション
- [ ] 承認(status → approved に変更して保存)
- [ ] 却下(status → rejected に変更して保存)
- メモ: {庭師の修正コメント・自由記述}

## 種からの注記
{Q列未完了等の警告 / 改善提案 等}
```

**`## 配信本文`** は **必須セクション**。`post_approval.body.message_from` がこのセクション全文を読んで送信する(セクション切り出し規約)。

**status の遷移**:

| 状態 | 意味 | 遷移条件 |
|---|---|---|
| `awaiting_pruning` | 剪定待ち | 種が生成した直後 |
| `approved` | 承認済み | 庭師が手動で status 変更 → post_approval が発火 |
| `rejected` | 却下 | 庭師が手動で status 変更 |
| `sent` | 配信成功 | post_approval の on_send_success |
| `send_failed` | 配信失敗 | post_approval の on_send_failure |

#### Triage 系(`triage/`)テンプレート

```markdown
---
type: triage
seed: morning-briefing
status: awaiting_response          # awaiting_response | resolved
created: YYYY-MM-DD HH:MM
last_updated: YYYY-MM-DD HH:MM
audit:
  triggered_by: morning-briefing
---

# {today} Triage

## Q1: 締切確認が必要なタスク
- {タスク名}: 締切?
  → 回答: {庭師回答 ここ}

## Q2: 締切の数値化
- {自然言語表現} → ?
  → 回答: {庭師回答 ここ}

## Q3: AI 支援提案
- {タスク名}: AI 支援する?(yes/no)
  → 回答: {庭師回答 ここ}

## 庭師アクション
- 回答完了したら status を `resolved` に変更して保存
- もしくは LINE 短文返信(自然言語)→ ガクコが本ファイルに書き戻し
```

### 決定 5: 庭師の操作は 2 系統(board 直接編集 / LINE 短文返信)

両方とも **board ファイルへの書き込み** に正規化される:

| 経路 | 流れ |
|---|---|
| (i) board 直接編集 | 庭師が Obsidian で board ファイルを編集 → LiveSync で VPS にも反映 → ランチャー / 種が status 変化を検知 |
| (ii) LINE 短文返信 | 庭師が LINE で短文返信 → ガクコが受信 → ガクコが該当 board ファイルに書き戻し → (i) と同じ後続処理 |

**ガクコ側の責任**:

- LINE 返信から該当 board ファイルを特定(直近の通知 reference を保持)
- 該当ファイルに書き込み(Triage の `→ 回答:` 行 / 剪定系の `## 庭師アクション` のメモ)
- 書き込み経路は **Phase 3a A-1 で確定**(セッション12 の保留事項)

### 決定 6: 書き戻し経路は Phase 3a A-1 で確定

mirror-daemon が **単方向(CouchDB → MD)** なので、board への書き込み経路は別途実装が必要。候補:

| 候補 | 概要 |
|---|---|
| (i) mirror-daemon 双方向化 | daemon に書き戻し追加(暗号化処理を自前で持つ) |
| (ii) CouchDB クライアント直接 | 種が CouchDB に直接 write(LiveSync 暗号スキームを実装) |
| (iii) 別の VPS → vault パイプ | rsync 等で簡易書き戻し(LiveSync を経由しない) |

→ Phase 3a A-1 で実機検証して確定([vault-folder-layout ADR](2026-05-27-vault-folder-layout.md) と同じ宿題)。

### 決定 7: 案 E マーカーとの連動(board → backlog 反映時)

board ファイルが backlog/archive に何かを反映する場合(例: night-review が `[x]` を archive に転記)、 **案 E の `<!-- recur:... -->` マーカー保持規律** に従う:

- board に記述されたタスクが `recurring_master` 由来であれば、backlog 行末のマーカーをそのまま保持
- night-review が `[x]` → archive 転記する際、 **元行を完全保持**(案 E ADR で確定済)
- board ファイル自体は recur マーカーを持たない(board は中継、永続化先は backlog/archive)

### 決定 8: 配信本文セクション切り出し規約

`post_approval.body.message_from` の指定方法:

```yaml
post_approval:
  body:
    message_from: "## 配信本文"   # この見出しから次の見出しまでを抽出
```

実装規約:

- 値は **見出し文字列**(`## 配信本文` 等)
- 抽出範囲 = 該当見出しの次行から、 **次の `## ...` 見出し or ファイル末尾** まで
- 改行・空行・装飾・引用ブロックはそのまま保持
- frontmatter / 他セクションは含めない
- 本セクションが存在しない場合は post_approval 失敗(on_send_failure 経路)

## ファイルライフサイクル全体図

```
[種発火]
   ↓
[board/pending/{date}-{seed}.md 生成]  (status: awaiting_pruning)
   ↓ 庭師通知(LINE / board_with_notify)
   ↓
[庭師が status → approved or rejected]
   ↓
   ├─ approved → [post_approval 発火]
   │              ↓
   │              ├─ 配信成功 → [board/processed/ へ移動]  (status: sent)
   │              └─ 配信失敗 → [board/pending/ に残置]   (status: send_failed)
   │
   └─ rejected → [board/processed/ へ移動]  (status: rejected)
```

Triage 系の補足:

```
[morning-briefing 発火]
   ↓
[board/triage/{today}-morning-briefing.md 生成]  (status: awaiting_response)
   ↓ 庭師通知(LINE)
   ↓
[庭師が回答(直接編集 or LINE 返信 → ガクコ書き戻し)]
   ↓
[morning-briefing resume 発火 or 翌日 night-review が取り込み]
   ↓
[board/triage/archive/ へ日付付きで保管]  (status: resolved)
```

## 既存 draft への反映タスク(本 ADR 確定後)

| ファイル | 修正内容 |
|---|---|
| `monthly-shift-survey.md` | パスを `garden/board/pending/...` のまま維持(基準パスは前提として明示) |
| `morning-briefing.md` | `board/{today}-morning-briefing.md` → `garden/board/triage/{today}-morning-briefing.md` |
| `night-review.md` | `/opt/garden/tasks/...` → `hmc_tasks/...`(vault-folder-layout ADR の確定) |
| `inbox-process.md` | `garden/inbox/...` 系のパスを vault-folder-layout の構造に揃える |

修正は Phase 3a A-1 着手前に一括で行う。本 ADR とセットで実施。

## トレードオフ

### 採用理由

- 既存 draft の慣例(`pending/processed`)を継承しつつ、Triage 専用領域を分離して責務を明確化
- frontmatter status による状態管理は LiveSync(plain text)と相性が良い
- 庭師の操作経路 2 系統を「board への書き込み」に正規化することで、種側は board 監視だけで状態遷移を扱える
- 案 E マーカー連動の規律が明確(board は中継、永続化は backlog/archive)

### 妥協点

- ディレクトリ階層が増える(`board/pending`, `board/processed`, `board/triage`, `board/triage/archive`)
  - 対策: Obsidian の bookmarks 機能で頻用パスをショートカット化(塚越さん側で運用)
- 配信本文セクション切り出しが「見出し文字列マッチ」で、表記揺れに弱い
  - 対策: テンプレ強制(種が生成する際は規約見出しを必ず使う)+ post_approval 失敗時の fallback
- ガクコ側の書き戻し実装が未確定(Phase 3a A-1 待ち)
  - 対策: 当面は board 直接編集だけで運用可能(LINE 返信は後追い実装)

## 未決事項

- 書き戻し経路(mirror-daemon 双方向化 vs CouchDB 直書き)— Phase 3a A-1
- ガクコ側「LINE 返信 → board MD 書き戻し」の最小ループ実装
- board のサイズ閾値(processed/ の月別分割 / 古い処理済みの整理)
- triage の resume 機構詳細(morning-briefing 自身が読みに行くか、別種に分けるか)

## 関連

- [vault-folder-layout ADR](2026-05-27-vault-folder-layout.md) — vault 内の `garden/` 配置全体
- [recurring-respawn-prevention ADR](2026-05-27-recurring-respawn-prevention.md) — 案 E マーカー連動の前提
- [seed-schema-extensions ADR](2026-05-27-seed-schema-extensions.md) — `channel: none` 等の運用
- [セッション4 ADR(剪定振り分け)](2026-05-23-seeds-design-direction.md) — board_with_notify / board の使い分け
- [セッション6 ADR(BAA フロー + Triage)](2026-05-25-daily-workflow-and-task-master-architecture.md)
- [mirror-daemon-implementation ADR](2026-05-27-mirror-daemon-implementation.md) — 書き戻し経路の保留
- [garden/seeds/daily-pilot/](../../garden/seeds/daily-pilot/) — 既存 draft(本 ADR 確定後にパス統一)
- [garden/seeds/shift_manager/monthly-shift-survey.md](../../garden/seeds/shift_manager/monthly-shift-survey.md)
