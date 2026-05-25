---
type: reference
status: active
last_updated: 2026-05-26
purpose: ig_scheduler(Instagram 投稿予約)の VPS 設定の正本
---

# ig_scheduler

VPS 上の **`ig_scheduler`** コンテナの構成ファイル正本。

## 位置づけ

- HMC の **sns_pilot SKILL** の一環(Instagram 投稿予約 API)
- HARAPPA 公式 Instagram アカウント(`@harappa_official` 等)への投稿を時刻指定でスケジューリング
- 認証: APScheduler + SQLite + Meta Graph API

## 接続情報

- VPS 上の場所: `/home/vps-harappa/ig_scheduler/`
- コンテナ: `ig_scheduler`
- 内部公開: `127.0.0.1:8100 → 8000`(host bind のみ、Nginx Proxy Manager 経由で `ig-api.harappa.monster`)
- データ: Docker volume `ig_scheduler_scheduler_data` → コンテナ `/data/`

## ファイル構成

```
vps/ig_scheduler/
├── docker-compose.yml   # external network proxy-manager_default に参加
├── Dockerfile           # python:3.12-slim + uvicorn
├── requirements.txt
├── app.py               # FastAPI + APScheduler
├── .env.example         # secret テンプレ
└── README.md            # 本ファイル
```

## secret

VPS 上 `~/ig_scheduler/.env`(本 repo `.gitignore` で除外):
- `META_ACCESS_TOKEN` — Meta Graph API トークン
- `META_IG_ACCOUNT_ID` — `17841404542535531`(HARAPPA Instagram Business Account)
- `SCHEDULER_API_KEY` — 内部 API 認証キー(`openssl rand -hex 32`)
- `SMTP_*` — エラー通知メール(Gmail App Password)

→ secret 値は別途 [docs/security/secrets/ig_scheduler.md](../../docs/security/secrets/) に保管予定(現在未整備、Phase 3b で集約)。

## デプロイ

```bash
# ローカル → VPS に転送
scp vps/ig_scheduler/{docker-compose.yml,Dockerfile,requirements.txt,app.py,.env.example} harappa:~/ig_scheduler/

# VPS で rebuild
ssh harappa "cd ~/ig_scheduler && docker-compose up -d --build"

# 動作確認(VPS 上から)
ssh harappa "curl -s http://127.0.0.1:8100/"
```

## 復旧

[vps/recovery.md § ig_scheduler](../recovery.md#ig_scheduler) を参照。

## 関連

- [vps/README.md](../README.md)
- HMC 側 sns_pilot SKILL(別 repo)
