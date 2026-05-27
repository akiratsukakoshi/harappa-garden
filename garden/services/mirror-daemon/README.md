---
type: service
status: active
last_updated: 2026-05-27
purpose: CouchDB(LiveSync E2EE)から平文 MD を VPS 上にミラーする daemon。種(seeds)が読む共通データ層
---

# garden-mirror-daemon

CouchDB(`gakuchovault` DB)の `_changes` feed を購読し、Obsidian LiveSync の E2EE 暗号化された doc を **平文 MD ファイル** として VPS 上のディレクトリに書き出す常駐 daemon。

種(seeds)は CouchDB のクエリ言語や暗号鍵を意識せず、**普通のファイルシステム上の MD** として vault を読める。

## なぜこれが必要か

- Phase 3a A-2 で完成した LiveSync は **E2EE オン** のため、CouchDB に格納される doc は暗号化されている
- 種(daily-pilot 4本など)は MD を `grep` / `cat` / `head` 相当の素朴な操作で読みたい
- 各種のスクリプトに E2EE 復号ロジックを埋め込むのは現実的でない
- → daemon が一箇所で復号して **平文ミラー** を維持する

## アーキテクチャ

```
[PC Obsidian] ─┐
[iPhone Obsidian] ─┼─→ CouchDB (gakuchovault, E2EE) ──┐
                                                      │ _changes feed
                                                      ▼
                                          [mirror-daemon] (このサービス)
                                                      │ decrypt + write
                                                      ▼
                                    /home/vps-harappa/garden-mirror/
                                                      │
                                                      ▼
                                             [seeds 各種が読む]
```

**単方向**(CouchDB → MD のみ)。書き戻しは行わない。

## 配置と起動

### VPS 上

```
~/garden/services/mirror-daemon/
├── docker-compose.yml      # 本 repo と同一
├── Dockerfile              # 同上
├── package.json            # 同上
├── mirror.mjs              # 同上
├── .env                    # chmod 600、VPS 上のみ
└── data/                   # state.json(last_seq + path 索引)— docker volume
```

ミラー先(コンテナ外):

```
/home/vps-harappa/garden-mirror/
├── AGENTS.md
├── 00_moc/
├── archive/
├── digihara/
├── hmc_tasks/              # 既存のタスクマスタ
├── garden/                 # Phase 3a 連絡板等(将来)
├── 経営/
└── ...
```

### 起動手順

```bash
# 1. VPS にコピー(初回のみ、または mirror.mjs を更新したとき)
scp -r mirror.mjs package.json Dockerfile docker-compose.yml harappa:~/garden/services/mirror-daemon/

# 2. .env を VPS 側で作成(secret は本 repo に commit しない)
ssh harappa
cd ~/garden/services/mirror-daemon
cp .env.example .env
chmod 600 .env
vi .env   # COUCHDB_PASS / E2EE_PASSPHRASE / MIRROR_HOST_PATH を埋める

# 3. ミラー先ディレクトリを用意
mkdir -p /home/vps-harappa/garden-mirror

# 4. 起動
docker-compose -p garden-mirror-daemon up -d --build

# 5. ログ確認
docker logs -f garden-mirror-daemon
```

## 動作の仕組み

### 初期同期(state.last_seq が 0 の時)

1. `_local/obsidian_livesync_sync_parameters` から PBKDF2 salt を取得
2. `_all_docs?include_docs=true` で全 doc を走査
3. `type == "plain" or "newnote"` かつ `.md` で終わる doc を対象に:
   - `children` フィールドの chunk ID 配列を `_all_docs (POST keys)` で一括取得
   - 各 chunk の `data` フィールド(`%=` プレフィックス)を AES-GCM + HKDF + PBKDF2 で復号
   - 連結して `MIRROR_DIR/{doc.path}` に atomic write(temp + rename)
4. CouchDB の `update_seq` を `state.last_seq` に保存

### 継続同期

1. `_changes?feed=continuous&include_docs=true&since={last_seq}&heartbeat=30000` を購読
2. 各 change イベントについて:
   - `id` が `_` または `h:` で始まる → スキップ(local doc / chunk doc は対象外)
   - `_deleted: true` → `state.path_by_id` から元 path を引いて mirror から削除
   - それ以外 → `syncDoc()` で復号 + 書き出し
3. 10 件ごとに `state.json` を保存(再起動時の続行用)

### 復号

`octagonal-wheels/encryption/hkdf` の `decrypt(input, passphrase, pbkdf2Salt)` をそのまま使う:
- 入力: `%=` プレフィックス + base64( IV(12B) | hkdfSalt(32B) | ciphertext+GCMtag )
- PBKDF2-SHA256(310_000 iterations, pbkdf2Salt) で master key
- HKDF-SHA256(masterKey, hkdfSalt) で chunk key
- AES-GCM(chunkKey, iv) で復号

## 制約と境界

- **MD ファイルのみ**(添付ファイル・画像・PDF などのバイナリは現状ミラーしない)
- **単方向**(mirror → CouchDB の書き戻しはしない。種が書きたい場合は Phase 3a A-1 の本番ランチャー + 連絡板で別途設計)
- **削除はソフト**(空ディレクトリの掃除はしない)
- **競合解決なし**(LiveSync 側で起きた競合 doc は最後の write が勝つ)
- **chunk キャッシュは in-memory**(再起動で消える。LRU 風に CHUNK_CACHE_MAX 件で打ち切り)
- **コンテナは uid 1000(vps-harappa)で動作**(`docker-compose.yml: user: "1000:1000"`)— mirror に書き出すファイルは vps-harappa 所有になる。これにより VPS 上の同ユーザの種(`claude -p`)から書き込みが可能になる(セッション13 で修正)

## トラブルシュート

### 「全部ミラーされない」「途中で止まる」

`docker logs garden-mirror-daemon` でエラーを確認:
- `[err] decrypt failed`: E2EE_PASSPHRASE が間違っている
- `[err] missing chunk`: 該当 chunk doc が CouchDB に存在しない(LiveSync の途中状態)— 再起動で改善することが多い
- `_changes -> 401`: COUCHDB_USER / COUCHDB_PASS が間違っている

### 「state を初期化したい」

```bash
docker stop garden-mirror-daemon
rm ./data/state.json
docker start garden-mirror-daemon
# 全 doc を再走査する
```

ミラー先ディレクトリの内容も消す場合:

```bash
rm -rf /home/vps-harappa/garden-mirror/*
```

### 「mirror が古い気がする」

```bash
# CouchDB の現在の update_seq と state.last_seq を比較
docker exec garden-mirror-daemon cat /data/state.json | grep last_seq
curl -s -u "garden-admin:$COUCHDB_PASS" https://gardendb.harappa.monster/gakuchovault | jq -r .update_seq
```

両者が一致していない場合、daemon が落ちているか、change feed が切れている可能性。

## 関連

- [docs/decisions/2026-05-25-couchdb-livesync-implementation.md](../../../docs/decisions/2026-05-25-couchdb-livesync-implementation.md) — LiveSync の前提
- [docs/decisions/2026-05-27-mirror-daemon-implementation.md](../../../docs/decisions/2026-05-27-mirror-daemon-implementation.md) — 本 daemon の ADR
- [garden/services/couchdb/README.md](../couchdb/README.md) — CouchDB サービス
- [vps/README.md](../../../vps/README.md) — VPS 全体マップ
- [octagonal-wheels/encryption/hkdf.ts](https://github.com/vrtmrz/octagonal-wheels/blob/main/src/encryption/hkdf.ts) — 暗号方式の根拠
