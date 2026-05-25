---
type: reference
status: active
last_updated: 2026-05-26
last_updated_by: claude (with 塚越さん, セッション11)
purpose: VPS(harappa.monster)の全体マップ。別 repo の AI も含めて「VPS 上に何があり、どこが正本か」を1ページで把握する入口
---

# VPS 全体マップ(harappa.monster / 162.43.40.86)

> **本 repo は HARAPPA 事業の VPS リソース全体の管理拠点**。各リソースの「正本」がどこにあるか、開発フロー、復旧手順を集約する。
>
> 詳細な現状サマリは [docs/vps/current-state.md](../docs/vps/current-state.md)、方針 ADR は [docs/decisions/2026-05-26-vps-management-policy.md](../docs/decisions/2026-05-26-vps-management-policy.md)。

## このディレクトリは何か

VPS 上の構成ファイル(docker-compose / Dockerfile / 設定 / cron / バックアップ取得スクリプト等)の **正本** を本 repo で版管理するためのもの。VPS 全壊時はここから再構築する。

**スコープ内**(本 repo で正本管理):
- NPM(Nginx Proxy Manager)
- ig_scheduler(Instagram 投稿予約、HMC sns_pilot の一環)
- cron(VPS 全体の cron スナップショット)
- garden サービス群は [garden/services/](../garden/services/) 配下(本 vps/ ではなく garden/ に置く。種が依存する Garden 専用サービスのため)

**スコープ外**(別 repo or 管理対象外):
- ガクコ(gaku-co5) → [akiratsukakoshi/gaku-co5.0](https://github.com/akiratsukakoshi/gaku-co5.0)
- haramon → [akiratsukakoshi/haramon](https://github.com/akiratsukakoshi/haramon)
- openclaw(gaku-co-oc) → [openclaw/openclaw](https://github.com/openclaw/openclaw)(上流 fork)
- n8n 残骸(現在未使用)

## VPS リソース一覧

| コンテナ / リソース | 正本の場所 | secret | 開発フロー | 復旧 |
|---|---|---|---|---|
| `gaku-co5` | [GitHub: akiratsukakoshi/gaku-co5.0](https://github.com/akiratsukakoshi/gaku-co5.0) | ローカル PC `~/gaku-co5.0/.env`(git 除外) | [dev-flow.md § ガクコ系](dev-flow.md#a-ガクコ系) | [recovery.md § ガクコ](recovery.md#ガクコ-rollback--全壊) |
| `garden-couchdb` | [garden/services/couchdb/](../garden/services/couchdb/) | [docs/security/secrets/garden-couchdb.md](../docs/security/secrets/garden-couchdb.md) | [dev-flow.md § その他 VPS 系](dev-flow.md#b-その他-vps-系本-repo-で正本管理) | [recovery.md § CouchDB](recovery.md#couchdb-データ破損--全壊) |
| `proxy-manager_nginx-proxy-manager_1`(NPM) | [vps/proxy-manager/](proxy-manager/) | NPM admin password(UI 設定、secret 別途記録要) | 同上 | [recovery.md § NPM](recovery.md#npm-内部-db-破損) |
| `ig_scheduler` | [vps/ig_scheduler/](ig_scheduler/) | VPS 上 `~/ig_scheduler/.env`(本 repo 除外) | 同上 | [recovery.md § ig_scheduler](recovery.md#ig_scheduler) |
| crontab(vps-harappa user) | [vps/cron/](cron/) | — | 手動編集 + スナップショット commit | [recovery.md § cron](recovery.md#cron-消失) |
| `gaku-co-oc_openclaw-gateway_1` | [openclaw/openclaw](https://github.com/openclaw/openclaw) + VPS ローカル差分 | VPS 上 `~/gaku-co-oc/.env` | 管理対象外(Phase 3b で扱い検討) | 上流 fork から再 clone + .env 配置 |
| `haramon_web_1` | [akiratsukakoshi/haramon](https://github.com/akiratsukakoshi/haramon) | VPS 上 `~/haramon/.env` | 別 repo で完結 | 別 repo の README 参照 |

## ドメイン / リバプロ(Nginx Proxy Manager 経由)

| ドメイン | 用途 | 設定場所 |
|---|---|---|
| `harappa.monster` | メイン | NPM UI |
| `bot.harappa.monster` | gaku-co5 LINE bot webhook | 同上 |
| `ig-api.harappa.monster` | ig_scheduler | 同上 |
| `gardendb.harappa.monster` | CouchDB(Obsidian LiveSync) | 同上 |
| `n8n-harappa.duckdns.org` | n8n(旧、現状未使用) | 同上 |

→ Proxy Host 定義の **正本は NPM 内部 DB**。定期 export で [proxy-manager/backups/](proxy-manager/backups/)(git 除外)にローカル保管。

## ディレクトリ構造

```
vps/
├── README.md          ← 本ファイル(常時最新の入口)
├── dev-flow.md        ← 開発フロー2系統(ガクコ系 / その他系)
├── recovery.md        ← 復旧シナリオ別の手順
├── proxy-manager/     ← NPM の docker-compose ミラー + export スクリプト + backups
│   ├── docker-compose.yml
│   ├── README.md
│   ├── export.sh      ← NPM data + letsencrypt を tar.gz 化
│   └── backups/       ← .gitignore で除外、ローカル WSL のみ保管
├── ig_scheduler/      ← ig_scheduler の構成一式
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── app.py
│   └── README.md
├── cron/              ← crontab スナップショット
│   ├── crontab.snapshot
│   └── README.md
└── backups/           ← 横断的 backup 置き場(git 除外)
```

## VPS 接続

```bash
ssh harappa
# = ssh vps-harappa@162.43.40.86 (~/.ssh/config 定義済)
```

## 別 repo の AI が本 repo を読む時に知ってほしいこと

- **ガクコ(`akiratsukakoshi/gaku-co5.0`)を開発する AI へ**: VPS 全体の構成は本 repo の [vps/README.md](README.md) を参照。デプロイ後の動作確認に NPM / CouchDB の設定が必要なら [vps/proxy-manager/README.md](proxy-manager/README.md) を見てください。連携仕様(INTERFACE)はガクコ repo の `INTERFACE.md` が正本。
- **haramon を開発する AI へ**: ハラッパ事業全体の文脈は本 repo の [docs/concept.md](../docs/concept.md) と [garden/MAP.md](../garden/MAP.md) を参照。VPS 上の haramon コンテナは本 repo の管理対象外、別 repo で完結。
- **本 repo の HMG セッション**を継続する AI へ: VPS リソースを触る時はまず本ファイル + [docs/decisions/2026-05-26-vps-management-policy.md](../docs/decisions/2026-05-26-vps-management-policy.md) を読んでから。

## 関連

- [VPS 現状サマリ](../docs/vps/current-state.md) — ハードウェア / OS / バイナリ等の詳細
- [VPS 管理体制方針 ADR](../docs/decisions/2026-05-26-vps-management-policy.md)
- [VPS secret 管理方針 ADR](../docs/decisions/2026-05-25-vps-secret-management-direction.md)
- [CouchDB + LiveSync 実装 ADR](../docs/decisions/2026-05-25-couchdb-livesync-implementation.md)
- [garden/MAP.md](../garden/MAP.md)
