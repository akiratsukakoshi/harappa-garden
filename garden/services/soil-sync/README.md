# soil-sync — repo ↔ VPS 同期スクリプト

`garden/soil/` を repo と VPS garden-mirror の間で同期する単方向 rsync スクリプト 2 本。

詳細な設計判断は [ADR: soil の正本と 3 箇所配置の同期ルール](../../../docs/decisions/2026-06-02-soil-source-of-truth.md)。

## 何のためのスクリプトか

soil は 3 箇所に配置されている:

- **repo**: `~/harappa-garden/garden/soil/`(git 管理、構造ファイル正本)
- **vault**: `~/Dropbox/gakuchovault/garden/soil/`(Obsidian 読み取り専用ビュー)
- **VPS**: `/home/vps-harappa/garden-mirror/garden/soil/`(菌糸産ログ正本)

このうち **vault ↔ VPS は LiveSync で双方向自動同期** されている。残りの **repo ↔ VPS の経路** を本スクリプトが担う。

## 使い方

### Claude セッション開始時

```bash
./garden/services/soil-sync/pull-from-vps.sh
```

VPS で菌糸 / ガクコが書いた最新の `log.md` / `index.md` を repo に取り込む。

### Claude セッション終了時 / commit 前

```bash
./garden/services/soil-sync/push-to-vps.sh
```

Claude がセッション中に編集した構造ファイル(staff / business 等)を VPS に反映。LiveSync が VPS → vault も自動同期するため、vault は手当不要。

### dry-run(差分プレビュー)

```bash
./garden/services/soil-sync/pull-from-vps.sh --dry-run
./garden/services/soil-sync/push-to-vps.sh --dry-run
```

## 環境変数

| 変数 | デフォルト | 用途 |
|---|---|---|
| `SOIL_SYNC_SSH_HOST` | `harappa` | `~/.ssh/config` の Host エントリ名 |

## 安全策

- 初版は `rsync --delete` 不使用(誤削除リスク回避)。運用 1〜2 週で問題が出なければ採用判断
- dry-run オプションあり、本番実行前のプレビュー可
- ssh は ガクチョの個人鍵経由(VPS 側 `vps-harappa` ユーザー)

## 既知のエッジケース

- **菌糸 cron(03:00)と Claude セッションが同時刻に被る場合**: 競合は理論上発生し得る。発生時は手動 pull/push を挟む。運用観察で頻度を測る
- **vault で直接編集された場合**: LiveSync 経由で VPS に反映され、次回 `pull-from-vps` で repo に来る(repo が事後的に勝つ)
- **VPS 側で `chmod` が変わった場合**: rsync は権限も同期するため、repo 側の権限が VPS 由来に書き換わる可能性。問題発生時は `--no-perms` 等の調整を検討

## 関連

- ADR: [2026-06-02 soil の正本と 3 箇所配置の同期ルール](../../../docs/decisions/2026-06-02-soil-source-of-truth.md)
- soil README: [garden/soil/README.md](../../soil/README.md)
- 関連 daemon: [garden/services/mirror-daemon/](../mirror-daemon/) / [garden/services/writeback-daemon/](../writeback-daemon/)
