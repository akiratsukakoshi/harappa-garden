---
type: reference
status: active
last_updated: 2026-05-26
purpose: Nginx Proxy Manager (NPM) の VPS 設定の正本
---

# Nginx Proxy Manager (NPM)

VPS 上の **`proxy-manager_nginx-proxy-manager_1`** コンテナの構成ファイル正本。

## 概要

- イメージ: `jc21/nginx-proxy-manager:latest`
- VPS 上の場所: `/home/vps-harappa/proxy-manager/`
- 管理 UI: `http://{vps_ip}:81/`(admin 認証あり)
- 公開: 80 / 443 / 81 ポート

## ドメイン管理(2026-05-26 時点)

| ドメイン | バックエンド | SSL | WebSocket |
|---|---|---|---|
| `harappa.monster` | (TBD) | LE | — |
| `bot.harappa.monster` | gaku-co5:8000 | LE | — |
| `ig-api.harappa.monster` | ig_scheduler:8000 | LE | — |
| `gardendb.harappa.monster` | garden-couchdb:5984 | LE | ON |
| `n8n-harappa.duckdns.org` | n8n(現在未使用) | LE | — |

→ 正本は **NPM 内部 DB (`data/database.sqlite`)**。本 repo では構成のみ管理し、Proxy Host 定義は定期 export で backup。

## ネットワーク

```bash
# NPM が作る default network 名
proxy-manager_default
```

他コンテナ(garden-couchdb, ig_scheduler 等)はこの network に **external 参加** することで NPM 経由公開できる。

サンプル(garden-couchdb 側 docker-compose.yml):
```yaml
networks:
  proxy_net:
    external: true
    name: proxy-manager_default
```

## デプロイ

```bash
# ローカル → VPS に転送
scp vps/proxy-manager/docker-compose.yml harappa:~/proxy-manager/docker-compose.yml

# VPS で再起動
ssh harappa "cd ~/proxy-manager && docker-compose up -d"
```

## backup(NPM 内部 DB + LetsEncrypt 証明書)

```bash
# ローカルから実行(VPS で tar.gz 作成 → ローカルに取得)
./vps/proxy-manager/export.sh

# 出力先: vps/proxy-manager/backups/npm-backup-YYYYMMDD-HHMMSS.tar.gz
# .gitignore で除外(SSL 秘密鍵を含むため)
```

定期実行(例: 週次 cron)は今後追加予定。

## 復旧

[vps/recovery.md § NPM 内部 DB 破損](../recovery.md#npm-内部-db-破損) を参照。

## 関連

- [vps/README.md](../README.md)
- [vps/recovery.md](../recovery.md)
