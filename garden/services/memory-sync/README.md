# memory-sync — repo ↔ VPS 同期スクリプト

`garden/memory/` を repo と VPS garden-mirror の間で同期する単方向 rsync スクリプト 2 本。
soil-sync と並列の責務分離(対称設計だが「raw 除外」の点だけ異なる)。

詳細な設計判断は [ADR: memory の正本と sync ルール](../../../docs/decisions/2026-06-03-memory-source-of-truth.md)。

## 何のためのスクリプトか

memory は 3 箇所に配置されている(soil と同じ構造):

- **repo**: `~/harappa-garden/garden/memory/`(git 管理、構造ファイル正本)
- **vault**: `~/Dropbox/gakuchovault/garden/memory/`(Obsidian、LiveSync 経由)
- **VPS**: `/home/vps-harappa/garden-mirror/garden/memory/`(ingest-raw 種 / bot 書き込み正本)

このうち **vault ↔ VPS は LiveSync で双方向自動同期**。**repo ↔ VPS の経路** を本スクリプトが担う。

## soil-sync との違い:raw を除外する

memory には **`master/raw/*.md`(対話 RAW ログ)** という独自カテゴリがある:

- 機密扱い(Discord 対話の生ログ = ガクチョの判断含む)
- `.gitignore` で `garden/memory/**/raw/*.md` を除外
- **書き手は bot.py / memory_logger.py のみ**(VPS 専属)
- 同期しても repo には載らず無意味 + 機密リスク

そのため両スクリプトは `--exclude='*/raw/*.md'` を必ず付ける。`.gitkeep` は除外対象外なのでディレクトリ存在保証は保たれる。

## ファイル別正本マトリクス

| パス | 書き手 | 正本 | sync 対象 |
|---|---|---|---|
| `memory/README.md` | 人(Claude) | repo | ✅ pull/push |
| `memory/master/raw/.gitkeep` | 人 | repo | ✅ pull/push |
| `memory/master/raw/*.md` | bot.py / memory_logger.py | VPS | ❌ 除外(git にも上げない) |
| `memory/master/wiki/*.md` | ingest-raw 種(VPS) + 人(repo / vault) | **VPS 主・repo 従** | ✅ pull/push |
| `memory/master/wiki/index.md` | 同上 | 同上 | ✅ pull/push |

「VPS 主・repo 従」の理由:`ingest-raw` が毎晩 03:30 に積み上げる = **VPS が事実上の主正本**。repo は (1) git 履歴を残す (2) Claude が編集して push する経路。両方向あるが **`pull` を `push` より優先する**(セッション開始時 pull → 編集 → 終了時 push の順)。

## 使い方

### Claude セッション開始時(memory wiki を参照する場合)

```bash
./garden/services/memory-sync/pull-from-vps.sh
```

VPS で ingest-raw / bot が書いた最新の wiki/*.md と index.md を repo に取り込む。

### Claude セッション終了時 / commit 前(memory wiki を編集した場合)

```bash
./garden/services/memory-sync/push-to-vps.sh
```

Claude がセッション中に編集した wiki/*.md / index.md / README.md を VPS に反映。LiveSync が VPS → vault も自動同期するため、vault は手当不要。

### dry-run(差分プレビュー)

```bash
./garden/services/memory-sync/pull-from-vps.sh --dry-run
./garden/services/memory-sync/push-to-vps.sh --dry-run
```

## 環境変数

| 変数 | デフォルト | 用途 |
|---|---|---|
| `MEMORY_SYNC_SSH_HOST` | `harappa` | `~/.ssh/config` の Host エントリ名 |

## 安全策

- 初版は `rsync --delete` 不使用(誤削除リスク回避)。soil-sync と同様、運用観察で採用判断
- dry-run オプションあり、本番実行前のプレビュー可
- `--exclude='*/raw/*.md'` は両方向に必ず付与(raw が repo に漏れない構造保証)

## 既知のエッジケース

- **VPS 側の wiki/* と repo 側の wiki/* が両方編集された場合**: rsync は新しい mtime を勝たせる。両側で同一ファイルを同時編集した場合、最後の `pull` または `push` の方向に依存して片方が消える。発生時は手動マージ。運用上は「セッション開始 pull → 編集 → 終了 push」の規律で回避
- **`ingest-raw` cron(03:30)と Claude セッションが同時刻に被る場合**: 競合は理論上発生し得る。発生時は手動 pull/push を挟む
- **vault で直接編集された場合**: LiveSync 経由で VPS に反映され、次回 `pull-from-vps` で repo に来る(repo が事後的に勝つ)

## 関連

- ADR: [2026-06-03 memory の正本と sync ルール](../../../docs/decisions/2026-06-03-memory-source-of-truth.md)
- 並列スクリプト: [garden/services/soil-sync/](../soil-sync/)
- memory README: [garden/memory/README.md](../../memory/README.md)
- ingest-raw 種(VPS 主正本側の書き手): [garden/seeds/mycelium/ingest-raw.md](../../seeds/mycelium/ingest-raw.md)
- 三層分離 ADR: [2026-05-31 memory-three-layer-and-soil-routing](../../../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md)
