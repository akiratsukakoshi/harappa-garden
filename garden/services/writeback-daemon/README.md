---
type: service
status: draft
last_updated: 2026-05-27
purpose: VPS 平文 MD への変更を CouchDB(LiveSync E2EE)に書き戻す daemon。mirror-daemon の逆方向
---

# garden-writeback-daemon

`garden-mirror/` 配下の `.md` ファイル変更を inotify で検知し、**LiveSync E2EE 互換形式で CouchDB に書き戻す** 常駐 daemon。`mirror-daemon` の逆方向。

これにより、VPS 上で claude -p(種)が編集した結果が Obsidian(PC / iPhone)に LiveSync 経由で届く。

## なぜこれが必要か

セッション 12 で `mirror-daemon`(CouchDB → MD)を実装し、セッション 13 で本番ランチャー + 種を稼働させた結果、**種が VPS 上で MD を編集しても Obsidian には反映されない** ことが判明(セッション 14 で具体化)。

書き戻し経路を持たない限り、塚越さんは種の成果物を目視できない。この daemon が「最後のピース」。

## アーキテクチャ

```
[claude -p (seed)] ──write──> /home/vps-harappa/garden-mirror/*.md
                                                │
                                                │ inotify
                                                ▼
                                  [writeback-daemon] (このサービス)
                                                │ encrypt + PUT
                                                ▼
                            CouchDB (gakuchovault, E2EE)
                                  ├──→ [PC Obsidian]
                                  └──→ [iPhone Obsidian]
```

mirror-daemon と並列稼働:

```
[Obsidian] ──→ CouchDB ──→ [mirror-daemon] ──→ /mirror   (pull)
[claude -p] ──→ /mirror ──→ [writeback-daemon] ──→ CouchDB (push)
```

## フィードバックループの防止

mirror-daemon が `/mirror` に MD を書き込んだ瞬間、writeback の inotify が発火する。これをそのまま push すると無限ループになる。

対策: **push 前に CouchDB の現在の chunks を decrypt して内容比較**。同じなら skip。

- 比較対象: 文字列の完全一致
- コスト: 1 decrypt per change(現状の MD は数 KB なので十分軽い)
- state 不要(CouchDB が source of truth)

## 配置と起動

### VPS 上

```
~/garden/services/writeback-daemon/
├── docker-compose.yml      # 本 repo と同一
├── Dockerfile              # 同上
├── package.json            # 同上
├── writeback.mjs           # 同上
└── .env                    # chmod 600、VPS 上のみ(mirror-daemon と同値)
```

### 起動手順

```bash
# 1. VPS にコピー(初回のみ、または writeback.mjs を更新したとき)
scp -r writeback.mjs package.json Dockerfile docker-compose.yml \
    harappa:~/garden/services/writeback-daemon/

# 2. .env を VPS 側で作成(mirror-daemon の .env を流用可能)
ssh harappa
cd ~/garden/services/writeback-daemon
cp ~/garden/services/mirror-daemon/.env .env
chmod 600 .env

# 3. 起動
docker-compose -p garden-writeback-daemon up -d --build

# 4. ログ確認
docker logs -f garden-writeback-daemon
```

## 動作の仕組み

### 監視対象(スコープ限定)

- `MIRROR_DIR`(`/mirror` = `/home/vps-harappa/garden-mirror/`)配下の `.md` ファイル
- **`WRITEBACK_SCOPE`(既定 `hmc_tasks/,garden/`)のプレフィックス配下のみ** が対象
  - 種(claude -p)が書くのは `hmc_tasks/` と `garden/` だけ。それ以外は塚越さんの個人ノートで VPS 側では編集されない → 対象外にして一切触れない
  - スコープ外を push すると無関係なノートを巻き込む + 大文字小文字問題(後述)を踏むため、限定が安全(S15 教訓)
- 隠しファイル(`.` 始まり)、tmp ファイル(`.tmp.` 含む)はスキップ

### 2 系統の検知: fs.watch + reconcile scan

- **fs.watch**(`recursive: true`): 低レイテンシの fast-path(ベストエフォート)
- **reconcile scan**(`SCAN_INTERVAL_MS` 既定 15s): スコープ配下を mtime ベースで走査する **信頼できる backbone**
- 理由: Node の `fs.watch` recursive は時間経過で **既存ファイルの変更イベントを silently 取りこぼす**(S14→S15 で実機確認)。新規ファイル作成は拾うが、既存ファイルの modify を落とす。scan を真の source of truth にする

### debounce

- 同じパスへの連続変更は `DEBOUNCE_MS`(既定 1500ms)後に 1 回だけ処理
- fs.watch と scan の両方が同じパスを叩いても 1 回にまとまる

### 大文字小文字(LiveSync Case-Sensitive = OFF 対応)

LiveSync は **Case-Sensitive = OFF**(本 vault の設定)のとき、doc の `_id` を **パスの小文字化** で保存し、`path` フィールドに元の大文字を保持する。ファイルもディスク上は元の大文字。

→ 書き戻し時は **`_id = path.toLowerCase()`、`path` フィールド = 元の大文字** にしなければならない。
元の大文字を `_id` に使うと、`AGENTS.md`(`_id=agents.md` が正)に対して `_id=AGENTS.md` の **重複 doc** を作ってしまう(S15 で発生・修復済)。

### 単一 chunk 戦略

LiveSync は doc を chunk に分割するが、本 daemon は **コンテンツ全体を 1 chunk** として扱う:

- chunk ID = `h:` + `digestHash([content])`(xxhash)
- 既存 chunk と ID が一致すれば skip(LiveSync は読み戻し時に concat するだけなので問題なし)
- LiveSync 由来の chunk(複数)と writeback 由来の chunk(単一)が混在しても、読み手は正しく内容を取り出せる

### 削除

- inotify は file remove イベントを `rename` で通知(削除時) → stat で 404 を確認して CouchDB に `_deleted: true` の doc を PUT

### 409 conflict

- 同時編集で `_rev` が古くなった場合、warn log を出して **skip**(次の変更で再試行)
- 検証フェーズの単純策。production では retry ロジックを足す

## 環境変数

| 変数 | 既定値 | 用途 |
|---|---|---|
| `COUCHDB_URL` | - | mirror-daemon と同値 |
| `COUCHDB_USER` | - | 同上 |
| `COUCHDB_PASS` | - | 同上 |
| `DATABASE` | `gakuchovault` | 同上 |
| `E2EE_PASSPHRASE` | - | LiveSync と完全一致(同上) |
| `MIRROR_DIR` | `/mirror` | コンテナ内マウントパス |
| `DEBOUNCE_MS` | `1500` | 連続変更のファイナル待ち(ms) |

## 制約と境界

- **`.md` ファイルのみ**(他の拡張子は無視)
- **single chunk**(分割なし。大ファイルでもメモリに乗る前提)
- **暗号方式は LiveSync v0.x 互換**(HKDF + AES-GCM via octagonal-wheels)
- **double-write はしない**(content 比較で同一ならスキップ → ループ防止)
- **`fs.watch` recursive**(Linux + Node 20+ 必須)
- **conflict はスキップ**(retry なし、再変更で再試行)

## トラブルシュート

### 「Obsidian に変更が反映されない」

1. writeback log で push 記録を確認: `docker logs garden-writeback-daemon | tail`
2. CouchDB に doc が書き込まれているか: `curl ...` で _rev を確認
3. PC/iPhone Obsidian の LiveSync が動作しているか(ステータスバー)

### 「ループしている(?)」

- log に `[skip] xxx.md (no change vs CouchDB)` が出ているはず
- 連続して `[put]` が出続けるなら、decrypt 失敗で skip 判定が誤動作している可能性
- E2EE_PASSPHRASE が mirror-daemon と完全一致しているか確認

### 「state を初期化したい」

writeback は state を持たない(CouchDB が source of truth)。初期化不要。

## 関連

- [garden/services/mirror-daemon/README.md](../mirror-daemon/README.md) — 逆方向の daemon
- [docs/decisions/2026-05-27-mirror-daemon-implementation.md](../../../docs/decisions/2026-05-27-mirror-daemon-implementation.md) — LiveSync 暗号方式の根拠
- [docs/decisions/2026-05-25-couchdb-livesync-implementation.md](../../../docs/decisions/2026-05-25-couchdb-livesync-implementation.md) — LiveSync 全体
