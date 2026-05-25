---
type: reference
status: active
last_updated: 2026-05-26
purpose: VPS リソース復旧シナリオ別の手順。トラブル発生時に最初に開く
---

# 復旧手順

シナリオ別に必要なリソースと手順を集約。

## 前提:必須リソースの保管場所

| リソース | 保管場所 | 復旧時の必要性 |
|---|---|---|
| 本 repo (`harappa-garden`) | GitHub(`akiratsukakoshi/harappa-garden`)+ ローカル WSL | 全シナリオで必要 |
| ガクコ repo (`gaku-co5.0`) | GitHub(`akiratsukakoshi/gaku-co5.0`)+ ローカル WSL | ガクコ復旧時 |
| secret 全般 | [docs/security/secrets/](../docs/security/secrets/)(WSL ローカル平文、git 除外) | 全シナリオで必要 |
| NPM backup(`data` + `letsencrypt` tar.gz) | [vps/proxy-manager/backups/](proxy-manager/backups/)(WSL ローカル、git 除外) | NPM 復旧時 |
| CouchDB データ | LiveSync 経由で PC + iPhone Obsidian 内に常時同期 | CouchDB 復旧時 |
| SSH 鍵 | `~/.ssh/id_ed25519` + VPS の `~/.ssh/authorized_keys` | VPS 接続全般 |

**WSL 全壊リスク**: 上記の WSL ローカル部分が消えると致命的。Phase 3b で外部 storage(1Password / 暗号化 zip)への二重化を予定。

## VPS 全壊(再構築)

新しい VPS を Xserver で建ててから:

```bash
# 1. SSH 接続セットアップ
# ~/.ssh/config の harappa エントリの HostName を新 IP に更新
# VPS に SSH 鍵を投入

# 2. 基本セットアップ
ssh harappa
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER  # 再ログイン要

# 3. proxy-manager 起動
mkdir -p ~/proxy-manager
cd ~/proxy-manager
# 本 repo から docker-compose.yml を scp
docker-compose up -d
# 続いて NPM data の復元(後述「NPM 内部 DB 破損」参照)

# 4. garden サービス起動(CouchDB)
mkdir -p ~/garden/services/couchdb
# 本 repo の garden/services/couchdb/ を scp -r
# .env は docs/security/secrets/garden-couchdb.md から作成
cd ~/garden/services/couchdb
docker-compose up -d
# 続いて CouchDB データ復旧(後述「CouchDB データ破損」参照)

# 5. ig_scheduler 起動
mkdir -p ~/ig_scheduler
# 本 repo の vps/ig_scheduler/ を scp -r
# .env を docs/security/secrets/ig_scheduler.md から作成
cd ~/ig_scheduler
docker-compose up -d --build

# 6. ガクコ起動
mkdir -p ~/gaku-co5
cd ~/gaku-co5
git clone https://github.com/akiratsukakoshi/gaku-co5.0.git .
# .env を local PC の ~/gaku-co5.0/.env から scp
./deploy.sh

# 7. cron 復旧
crontab -e
# 本 repo の vps/cron/crontab.snapshot の内容を投入

# 8. DNS A レコードを新 IP に更新(Xserver / お名前.com 等)

# 9. 動作確認
docker ps  # 全コンテナ Up 確認
# 各ドメインに https アクセス → 200 / 30x 確認
```

## NPM 内部 DB 破損

NPM の Proxy Host / SSL 設定が消失した場合。

```bash
# 1. 最新の backup を確認
ls -lt vps/proxy-manager/backups/

# 2. VPS の現状を退避
ssh harappa "cd ~/proxy-manager && docker-compose down && mv data data.broken-$(date +%Y%m%d) && mv letsencrypt letsencrypt.broken-$(date +%Y%m%d)"

# 3. backup を VPS に転送 + 展開
scp vps/proxy-manager/backups/npm-backup-YYYYMMDD.tar.gz harappa:~/
ssh harappa "cd ~/proxy-manager && tar -xzf ~/npm-backup-YYYYMMDD.tar.gz"

# 4. パーミッション復元(NPM コンテナの uid 想定)
ssh harappa "sudo chown -R root:root ~/proxy-manager/data ~/proxy-manager/letsencrypt"

# 5. NPM 再起動
ssh harappa "cd ~/proxy-manager && docker-compose up -d"

# 6. 動作確認
# - NPM UI(https://{vps_ip}:81)にログイン
# - Proxy Host 一覧が復元されていること
# - 各ドメインに https アクセス → 200/30x
```

backup が無い場合は **手動再投入**(NPM UI で Proxy Host を1つずつ追加)。本 repo [vps/README.md § ドメイン](README.md#ドメイン--リバプロnginx-proxy-manager-経由) のドメイン一覧を参照。

## CouchDB データ破損 / 全壊

LiveSync で PC / iPhone Obsidian 側に常時同期されているため、データ自体は端末から復元可能。

```bash
# 1. VPS で CouchDB 再起動 or 再構築
ssh harappa
cd ~/garden/services/couchdb
docker-compose down -v  # データボリュームごと削除
docker-compose up -d
# 数秒待ってヘルスチェック
curl -u admin:$(cat .env | grep COUCHDB_PASSWORD | cut -d= -f2) http://127.0.0.1:5984/

# 2. PC Obsidian で LiveSync 設定画面を開く
# 3. "Overwrite Server" を実行 → PC の vault が CouchDB に再アップロード
# 4. iPhone Obsidian で "Fetch from Server" → 再取得

# admin / passphrase は docs/security/secrets/garden-couchdb.md から取得
```

## ガクコ rollback / 全壊

```bash
# rollback(特定 commit に戻す)
ssh harappa
cd ~/gaku-co5
git fetch
git reset --hard <commit_sha>
./deploy.sh  # or fetch.sh

# 全壊(コンテナ消失)
cd ~/gaku-co5
docker-compose down
git pull
./deploy.sh
```

詳細はガクコ repo の README.md / deploy.sh を参照。

## ig_scheduler 復旧

```bash
ssh harappa
cd ~/ig_scheduler
docker-compose down

# 構成ファイルが消えた場合は本 repo から scp
scp vps/ig_scheduler/{Dockerfile,docker-compose.yml,requirements.txt,app.py,.env.example} harappa:~/ig_scheduler/

# .env は docs/security/secrets/ig_scheduler.md から作成
docker-compose up -d --build

# 動作確認: VPS 上で
curl http://127.0.0.1:8100/
```

## cron 消失

```bash
# 1. snapshot 確認
cat vps/cron/crontab.snapshot

# 2. VPS に流し込む
scp vps/cron/crontab.snapshot harappa:/tmp/crontab.snapshot
ssh harappa "crontab /tmp/crontab.snapshot && crontab -l"
```

## SSL 証明書失効

LetsEncrypt は NPM が自動更新。失敗時は NPM UI で手動 renew。継続的に失敗するなら:

```bash
# NPM コンテナ内の certbot を確認
ssh harappa "docker exec proxy-manager_nginx-proxy-manager_1 certbot certificates"
# letsencrypt ディレクトリの権限確認
ssh harappa "ls -la ~/proxy-manager/letsencrypt/"
```

## 関連

- [vps/README.md](README.md)
- [vps/dev-flow.md](dev-flow.md)
- [docs/security/secrets/](../docs/security/secrets/)
- [VPS 管理体制 ADR](../docs/decisions/2026-05-26-vps-management-policy.md)
