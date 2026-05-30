# ADR: 菌糸(Mycelium) の役割と soil 参照規約

日付: 2026-05-30
セッション: 20
ステータス: 採用(設計確定 / 実装は Stage 別)

## 文脈

[セッション20 で論点3「SKILL ↔ soil の参照規約」を議論]した際、以下が判明:

1. **各 plot は soil への依存度が大きく異なる** — daily-pilot は soil をほぼ参照しないが、shift_manager は `people/staff` 全員(29名)を必須参照する。finance / invoice_processor / minute_maker も中〜大規模に soil を引く
2. **既存 `garden/soil/index.md` が Karpathy LLM Wiki 方式の中核** で、私(Claude)が当初「新 INDEX.md を作る」と提案したのは既存設計の見落としだった
3. **LLM Wiki の核心は INDEX の存在ではなく、INDEX を active に維持する役割の存在** — soil/README.md には 3 責務(Ingest / Query / Lint)が明文化されているが、それを担うエージェント実体が未定義
4. **現状の index.md は staff 4 名のみ反映の初期化状態**(実際は active 29 名)。shift_manager 着手前にこのギャップを埋める必要がある

庭師から提起されたメタファ:「インデックスの更新をする(土を耕したり整理したりする)役割。土壌の菌糸とかかな?LLM wiki の考えもそこがキモだと思う。」

→ 「土壌維持エージェント」を Garden 語彙の新メンバー **菌糸(Mycelium)** として正式に立ち上げる。

## 決定

### 1. Garden 語彙に「菌糸(Mycelium)」を追加

[docs/garden-vocabulary.md](../garden-vocabulary.md) に正式追加。

役割マップ(更新後):

| 役割 | 振る舞いの本質 |
|---|---|
| 庭師(Gardener) | 意志を持つ。決める |
| 番人(Watcher) | 監視する。告げる(目) |
| **菌糸(Mycelium)** ← NEW | 分解する。運ぶ。整える(土の中の網目、見えない基盤) |
| 草木 / 木の精 | 表に出て話す(対話層 = ガクコ等) |

番人と菌糸の違い:番人は「見て告げる」、菌糸は「分解して運ぶ」。責務が違うため独立。

### 2. 菌糸の配置 = `garden/mycelium/`(独立トップカテゴリ)

`garden/plots/` ではなく、`garden/watchers/` でもなく、独立した配置にする。

理由:
- 菌糸は **業務 plot ではない**(daily-pilot / shift_manager と並列にすると違和感)
- 番人(watcher)とも責務が違う
- soil の維持基盤として、業務 plot とは別レイヤに置く

### 3. 菌糸の責務(soil/README L7-13 の3責務を Mode として実体化)

| Mode | 内容 | 発火源 |
|---|---|---|
| Mode 1: Ingest | 新ソース → soil 反映 + index 追記 + log | watcher(inbox 検知)or 種(cron) |
| Mode 2: Lint | 矛盾・古い記述・孤立ページ・欠損リンク → 連絡板に剪定依頼 | 種(週次 cron) |
| Mode 3: Index 更新 | soil 編集 → index.md 自動追従 | watcher(soil/ 配下の変更検知) |
| Mode 4: 関係性編み直し | `linked_*` 整備 + `[[link]]` 漏れ検出 | 種(月次 cron)or Mode 1/3 から呼ぶ |

### 4. soil 参照規約(各 plot SKILL の責務)

- 各 plot SKILL の frontmatter で **soil 依存** を declare(例: `requires_soil_index: true`)
- consumer は soil 依存 plot 起動時に [garden/soil/index.md](../../garden/soil/index.md) を on-demand Read
- 細部 soil ファイル(`soil/people/staff/kei-suzuki.md` 等)は index 経由で必要な物だけ on-demand Read
- soil 全体を SKILL や consumer に同梱しない(数千行になるため)

### 5. 実装の段階分け(Stage)

完璧な菌糸を一気に作るのは大仕事。段階分けで進める:

| Stage | 何を実装 | タイミング |
|---|---|---|
| **Stage 1** | Mode 3(Index 更新) | **shift_manager 着手より先**(前提整備) |
| Stage 2 | Mode 2(Lint = 週次 cron) | shift_manager 安定後 |
| Stage 3 | Mode 1(Ingest = 議事録・メール対応) | meetings 連携 / inbox-process と同期 |
| Stage 4 | Mode 4(関係性 = 月次 cron) | 運用成熟後 |

### 6. INDEX の更新方式は LLM(半自動)継続。動的生成(機械的)は採用しない

LLM Wiki 哲学に従い、「ingest のたびに LLM が要約・分類・関係付けて更新」する方式を継続。frontmatter からの機械的集約だけでは「staff 29 名(運営 4 / フィールド 20 / 写真 5)」のような **意味的分類** が出せないため。

## 代替案と却下理由

| 案 | 内容 | 却下理由 |
|---|---|---|
| **新 INDEX.md を新設** | 既存 index.md とは別に新規 INDEX | 既存 index.md(LLM Wiki 方式)と完全に同位置づけ。重複を生むだけ。**統合採用** |
| **動的生成スクリプト** | bot 起動時に soil/ を scan して index 自動構築 | LLM Wiki の核心(LLM による意味的更新)に反する。frontmatter 集約だけだと分類サマリが出せない |
| **plot SKILL に soil 全体同梱** | 各 plot SKILL に必要 soil 全体を frontmatter 経由で同梱 | staff 29 名 + business 21 ファイル等で prompt 肥大、shift_manager 単体で数千行 |
| **菌糸を番人カテゴリの中に置く** | `garden/watchers/mycelium/` | 番人(監視・告げる)と菌糸(分解・運ぶ)は責務が違う。独立カテゴリが筋 |
| **菌糸を plots の中に置く** | `garden/plots/mycelium/` | 業務 plot ではなく Garden 基盤。並列にすると違和感 |

## 影響

### 即時(セッション20)

- [docs/garden-vocabulary.md](../garden-vocabulary.md) に「菌糸(Mycelium)」追加 + 役割の責務マップ追加
- [garden/CHARTER.md](../../garden/CHARTER.md) に soil 参照規約節を追加
- [garden/mycelium/](../../garden/mycelium/) ディレクトリ新設 + [README.md](../../garden/mycelium/README.md)(位置づけ + Mode 設計 + Stage 分け)
- 本 ADR

### 次セッション(Stage 1 実装着手 — shift_manager より先)

- `garden/mycelium/SKILL.md` 起草(Mode 3 を中心に)
- `garden/mycelium/watcher.py` 実装(soil/ 配下の `fs.watch` + reconcile scan、writeback-daemon と同パターン)
- 現状の `garden/soil/index.md` を菌糸 Stage 1 で full scan → staff 29 名 + business 21 ファイル分の最新化
- 以降、soil 編集が起きたら index 自動追従
- Stage 1 完了後、shift_manager 立ち上げの前提が整う

### 長期

- Stage 2-4 の実装
- Garden の生態系(庭師・番人・菌糸・木の精)が完成して、各役割が独立して動く構造

## 関連

- 直前 ADR(セッション20): [Garden CHARTER 導入とトーン統一](./2026-05-30-garden-charter.md)
- 直前 ADR(セッション19): [種(seed) と SKILL の責務分離](./2026-05-30-skill-and-seed-separation.md)
- soil 設計: [garden/soil/README.md](../../garden/soil/README.md) — Karpathy LLM Wiki 哲学
- Karpathy の LLM Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- 関連ファイル: [garden/mycelium/README.md](../../garden/mycelium/README.md) / [garden/soil/index.md](../../garden/soil/index.md) / [garden/CHARTER.md](../../garden/CHARTER.md)
