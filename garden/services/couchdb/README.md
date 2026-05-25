---
type: service
status: active
last_updated: 2026-05-25
purpose: VPS 上の CouchDB(Obsidian Self-hosted LiveSync の同期先)
---

# garden-couchdb

Obsidian Self-hosted LiveSync の同期先となる CouchDB。VPS(harappa.monster)上で Docker 稼働。

## 役割

- 塚越さんの Obsidian vault(`gakuchovault`)を **数秒 push 同期** で複数端末間で同期
- VPS 側 daemon(`_changes` feed リスナ)が CouchDB を購読し、平文 MD ミラーへ展開(Phase 3a A-3)
- Garden の種(daily-pilot 等)は **平文 MD ミラー** を読み書き(CouchDB を直接触らない設計)
- E2EE オン: VPS 管理者(=塚越さん本人)が DB ダンプしても中身は読めない

詳細: [ADR セッション6 — タスクマスタアーキテクチャ](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md)

## 構成

| ファイル | 役割 |
|---|---|
| `docker-compose.yml` | apache/couchdb:3.4、`127.0.0.1:5984` バインド、データは `./data/` ボリューム |
| `local.ini` | LiveSync 用設定(CORS、single_node、最大ドキュメントサイズ等) |
| `.env.example` | admin user/password テンプレ。実体は VPS 側 `.env` (chmod 600) |
| `data/` | CouchDB データボリューム(.gitignore 対象) |

## 公開

- Nginx Proxy Manager 経由 `https://gardendb.harappa.monster` で WAN 公開
- WebSocket サポート必須(LiveSync が `_changes` feed を WebSocket で使う)
- SSL は Let's Encrypt 自動更新

## デプロイ手順(VPS 側)

```bash
# 1. ディレクトリ作成
ssh harappa
mkdir -p ~/garden/services/couchdb
cd ~/garden/services/couchdb

# 2. docker-compose.yml と local.ini を harappa-garden から手動コピー
#    (将来は LiveSync で自動同期される領域)

# 3. .env 作成(admin password 生成)
cat > .env <<EOF
COUCHDB_USER=garden-admin
COUCHDB_PASSWORD=$(openssl rand -base64 32)
EOF
chmod 600 .env

# 4. 起動
docker compose up -d

# 5. 動作確認
curl -fsS http://127.0.0.1:5984/_up
curl -fsS -u garden-admin:$(grep COUCHDB_PASSWORD .env | cut -d= -f2) http://127.0.0.1:5984/

# 6. システムデータベース初期化(初回のみ)
for db in _users _replicator; do
  curl -X PUT -u garden-admin:$(grep COUCHDB_PASSWORD .env | cut -d= -f2) http://127.0.0.1:5984/$db
done
```

## バックアップ

- データボリューム `./data/` の日次 tarball 化(Phase 3a 後追い)
- CouchDB API 経由の `_all_docs` ダンプ + 平文 MD ミラー git コミット(冗長性)

## 既知の制約

- ポート 5984 は **127.0.0.1 のみ**(Nginx Proxy Manager 経由 SSL 必須)
- E2EE は LiveSync プラグイン側で実施(CouchDB は暗号化済みドキュメントを保管)
- passphrase を紛失すると DB は復号不能 → 各端末ローカルからの再構築になる

## 関連

- [ADR セッション6](../../../docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md)
- [VPS 現状](../../../docs/vps/current-state.md)
- [Obsidian Self-hosted LiveSync 公式](https://github.com/vrtmrz/obsidian-livesync)
