# mirror-daemon 運用観察ログ

> 稼働中の `garden-mirror-daemon` の挙動を時系列で記録する。`README.md` が設計、本ファイルが運用。

## 観察すべき指標(チェックリスト)

| カテゴリ | 指標 | 想定範囲 | 異常 / 要対応の閾値 |
|---|---|---|---|
| **コンテナ健全性** | `docker ps` で `Up` か | 24/7 Up | 1 回でも Down |
| | restart 回数 | 0 / week | 1 以上 |
| | メモリ使用量 | < 200MB | > 500MB |
| | CPU 使用率(idle 時) | < 5% | 継続的に > 30% |
| **同期遅延** | LiveSync `[put]` → daemon ログ反映までの秒数 | 1〜5 秒 | > 30 秒 |
| | 初期同期(再起動時)の所要時間 | 56 ファイルで 5〜10 秒 | > 60 秒 |
| **整合性** | `path_by_id` のエントリ数 | vault 内 MD ファイル数 ±10% | 明らかな乖離 |
| | mirror ディレクトリの MD ファイル数 | vault と一致 | 一致しない |
| | state.json の last_seq | 増加し続ける | 24 時間以上停止 |
| **chunk キャッシュ** | プロセスのメモリ使用量(LRU 5000 件) | < 50MB | > 200MB |
| | 再起動後の再 fetch / 再復号速度 | 56 ファイルで 5〜10 秒 | > 30 秒 |
| **ディスク** | `/home/vps-harappa` の空き容量 | > 100GB | < 20GB |
| | mirror ディレクトリのサイズ | < 1GB(MD のみ) | > 5GB |
| **エラー** | docker logs 内の `[error]` / `[fatal]` | 0 件 / day | 1 件以上 |
| | `_changes` feed の途絶 | 0 回 / week | 1 回以上 |

## 現状スナップショット — 2026-05-27 16:40 JST(セッション13 終了時点)

### コンテナ
- name: `garden-mirror-daemon`
- 稼働時間: 約 7 時間(セッション12 でデプロイから)
- restart 履歴: 0 回
- `docker ps` 結果: `Up 7 hours`

### 同期状態
- 初期同期: 58 docs 走査 → 56 MD ファイル書き出し(2 docs は MD 以外でスキップ)
- 追加同期: `gardenテスト.md` / `野比買い出し.md` / `garden-livesync-test.md.md` 等のテスト残骸が複数追加
- 現状の MD ファイル数(mirror): **58 ファイル**
- 現状の path_by_id エントリ数: **58 件**
- last_seq: `2907-...`(初期 2867 から増加 = ライブ同期動作中)

### 動作確認実績
- 塚越さん PC で MD 編集 → 3〜5 秒で daemon に `[put]` ログ + mirror ファイル更新
- `active_tasks.md` への連続更新(編集中の小刻みな保存)も正しく処理(2026-05-27 06:57〜07:25 で 6 回更新)
- 60 秒未満の連続書き込みも追従(`野比買い出し.md` を 1B → 24B まで段階的に成長させた履歴あり)

### ボリュームマウント
- `/home/vps-harappa/garden/services/mirror-daemon/data` → `/data`(state.json 保持)
- `/home/vps-harappa/garden-mirror` → `/mirror`(平文 MD 出力先)

### ディスク
- ルート(`/`): 24G/387G 使用(7%)
- mirror ディレクトリ: 計測未実施(後追い: `du -sh /home/vps-harappa/garden-mirror`)

## 既知の挙動

### 正常範囲
- LiveSync 編集 → mirror 反映の遅延は **2〜5 秒**(passphrase HKDF 復号 + chunk フェッチ + atomic write)
- chunk キャッシュは in-memory(再起動でリセット)
- 削除イベントは `state.json` の `path_by_id` を引いてファイル削除

### 留意点
- vault 編集時に **複数バージョン(編集 → 保存 → 編集 → 保存)** が短時間で発生すると、すべて per-update で書き出される(debounce なし)
  - LiveSync 側の chunk チャンク化が冪等なので問題は起きないが、ログが多くなる
- `_changes` feed の再接続失敗時の挙動は未検証(本セッションでは観察未到達)
- chunk キャッシュ 5000 件超過時の LRU eviction は未検証(運用観察待ち)

## 運用イベント

### 2026-05-27 17:53 JST — 権限修正(セッション13 続き)

**問題**: daemon コンテナが root(uid 0)で動いていたため、書き出しファイルすべてが root 所有。VPS host の vps-harappa(uid 1000)から走る種(claude -p)が `EACCES` で書き込み不可。

**修正**:
1. `docker-compose.yml` に `user: "1000:1000"` 追加
2. `docker-compose -p garden-mirror-daemon down`
3. `sudo chown -R vps-harappa:vps-harappa /home/vps-harappa/garden-mirror /home/vps-harappa/garden/services/mirror-daemon/data`
4. `docker-compose -p garden-mirror-daemon up -d`

**結果**:
- コンテナ内 `id` = `uid=1000(node) gid=1000(node)`
- 起動後 last_seq から再開(state.json の継続性 OK)
- 新規書き出しが vps-harappa 所有で生成 → claude -p からの書き込み成功
- recurring-spawn 実走で `## 定期` セクションと `- [ ] **暗号資産の相場確認** (5/27締切・定期) <!-- recur:r001@2026-05-27 -->` の追記に成功

### 2026-05-27 17:16 頃 — LiveSync 削除イベント不帰問題(別課題)

**現象**: 塚越さんが Obsidian で `gardenテスト.md` / `garden-livesync-test.md.md` を削除しても、CouchDB に削除 doc が残り続け、mirror にも残る。`recurring_master.md` 等の更新 PUT は正常に届く一方、削除イベントだけ届かない。

**現時点の仮説**:
- Obsidian の「Files & Links → Deleted files」設定が「Move to system trash」になっていて、ファイルが OS ゴミ箱(WSL の場合は別場所)に移動 → vault 監視外
- LiveSync が削除を検知できていない可能性

**保留**: 本セッションの本筋(A-1)が完了したため別タスクへ。次回以降に Obsidian + LiveSync 設定の調査。

## 後追い観察事項(時間経過待ち)

- [ ] 1 週間連続稼働後の restart 回数 / メモリ使用量 / chunk キャッシュサイズ
- [ ] 大量編集時(50+ ファイル / 1 時間)の遅延・スループット
- [ ] 削除イベント(vault でファイル削除 → mirror から削除)の動作確認
- [ ] chunk キャッシュ 5000 件超過時の挙動
- [ ] LiveSync 設定変更(passphrase 変更等)時の挙動
- [ ] CouchDB 一時停止 → 再開時の `_changes` feed 再接続

## 関連

- [README.md](README.md) — 設計
- [mirror-daemon-implementation ADR](../../../docs/decisions/2026-05-27-mirror-daemon-implementation.md)
- [vault-folder-layout ADR](../../../docs/decisions/2026-05-27-vault-folder-layout.md)
