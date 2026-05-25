---
type: reference
status: active
last_updated: 2026-05-25
last_updated_by: claude (with 塚越さん, セッション9)
purpose: VPS(harappa.monster)の現状把握サマリ。Phase 3a/3b の前提条件確認時に参照する
---

# VPS 現状(harappa.monster / 162.43.40.86)

> Phase 3a(種ランチャー)と Phase 3b(HMC 移植 + secret 管理)の前提条件を判断するための現状スナップショット。
> セッション9 時点(2026-05-25)で ssh 経由で実適査べた内容を記録。

## 接続情報

| 項目 | 値 |
|---|---|
| Host | `harappa`(`~/.ssh/config` 定義済) |
| HostName | `162.43.40.86` |
| User | `vps-harappa` |
| Identity | `~/.ssh/id_ed25519` |
| ホスト名 | `x162-43-40-86` |

## ハードウェア / OS

| 項目 | 値 | 評価 |
|---|---|---|
| OS | Ubuntu 24.04.2 LTS (noble) | 新しめ |
| カーネル | Linux 6.8.0-88-generic | OK |
| CPU | AMD EPYC-Milan 6 vCPU | 余裕 |
| メモリ | 7.7 GB(空き 2.4 GB + buff/cache 3.8 GB = 利用可 5.8 GB) | 余裕 |
| Swap | 2.0 GB(使用 177 MB) | OK |
| ディスク | 387 GB(使用 24 GB / 残 364 GB) | **大幅に余裕**。CouchDB 同居問題なし |
| uptime | 172 日(@2026-05-25) | 安定稼働 |
| Load avg | 2.51 / 2.52 / 2.37(6 CPU の半分弱) | 余裕 |
| Timezone | **Asia/Tokyo (JST, +0900)** | cron 式が JST そのまま使える |
| Locale | `C.UTF-8`(LC_ALL なし) | UTF-8 OK、必要なら `ja_JP.UTF-8` に変更可 |

セッション6 ADR で議論された「VPS 信頼性課題(Docker 停止)」は、最近の uptime からは再発していない可能性。並走監視は引き続き必要。

## ランタイム / バイナリ

| 項目 | 値 |
|---|---|
| Docker | v29.1.3 |
| Node.js | v22.22.0(`/usr/bin/node`) |
| Python | 3.12.3(`/usr/bin/python3`) |
| **Claude Code** | **v2.1.92 がインストール済**(`~/.npm-global/bin/claude`)。npm 最新は v2.1.150 |
| OpenAI Codex CLI | `~/codex-auth.json` 存在(過去に試した形跡) |
| npm prefix | `/home/vps-harappa/.npm-global`(writable、`sudo` 不要) |

### Claude Code の認証状態

- `~/.claude/.credentials.json` 存在(最終アクセス 2025-04-05)
- subscription auth が生きている(`claude -p "..."` でレスポンス返却を確認、セッション9 で `PONG.` を取得)
- ヘッドレス `-p` モード動作 OK → Phase 3a の前提条件クリア

### PATH の落とし穴

- `~/.bashrc` に `export PATH="$HOME/.npm-global/bin:$PATH"` あり
- ただし **ssh 非対話シェル(`ssh harappa "command"`)では `.bashrc` が読まれない**
- cron からの起動も同様 → 種ランチャーでは **フルパス `~/.npm-global/bin/claude` を明示**する必要あり

## 稼働中の Docker コンテナ

| コンテナ名 | イメージ | ポート | 用途 |
|---|---|---|---|
| `gaku-co5` | `gaku-co5_bot` | 8000/tcp(host 経由配信) | LINE Bot(本プロジェクトの主要外部入出口) |
| `ig_scheduler` | `ig_scheduler_ig_scheduler` | 127.0.0.1:8100→8000 | Instagram スケジューラー |
| `gaku-co-oc_openclaw-gateway_1` | `openclaw:local` | 127.0.0.1:18789-18790 | openclaw gateway(日次 restart 中) |
| `haramon_web_1` | `haramon_web` | 0.0.0.0:3000 | Haramon Web(Next.js 系?) |
| `proxy-manager_nginx-proxy-manager_1` | `jc21/nginx-proxy-manager` | 0.0.0.0:80/81/443 | Nginx Proxy Manager(LetsEncrypt 自動更新) |

ホーム直下の関連ディレクトリ:
- `~/gaku-co5/`(LINE Bot ソース)
- `~/gaku-co-oc/`(openclaw)
- `~/ig_scheduler/`
- `~/haramon/`
- `~/proxy-manager/`

## ドメイン / リバプロ

Nginx Proxy Manager 経由で LetsEncrypt 自動更新:

| ドメイン | 用途(推測含む) |
|---|---|
| `harappa.monster` | メインドメイン |
| `bot.harappa.monster` | gaku-co5 LINE bot webhook |
| `ig-api.harappa.monster` | ig_scheduler |
| `n8n-harappa.duckdns.org` | n8n(現状の稼働状態は未確認) |

**`gardendb.harappa.monster`(CouchDB 公開用)** など新規サブドメインは同 Nginx Proxy Manager に追加できる。SSL 設定の新規作成不要(LetsEncrypt 自動)。

## cron / systemd の現状

### user crontab(`crontab -l`)

```cron
*/15 * * * * find /home/vps-harappa/.openclaw/agents/main/sessions/ -name "*.lock" -mmin +15 -delete -print >> /tmp/lock-cleaner.log 2>&1
0 19 * * * docker restart gaku-co-oc_openclaw-gateway_1 >> /tmp/openclaw-restart.log 2>&1
```

→ 既存は openclaw 関連の維持 cron のみ。**Garden 用 cron 行は新規追加可**。

### systemd user services

未使用(dbus のみ)。Garden 用 systemd timer / service の新規導入余地あり。

## ファイルシステム配置の制約

- `/opt/` は root 所有(`drwxr-xr-x 3 root root`)。`/opt/garden/` を作るには sudo 必要
- 代替として **`~/garden/`(=`/home/vps-harappa/garden/`)** で運用可能
- secret ADR の `~/.config/{service}/env` 規約と同じホームディレクトリ範囲で完結

## ポート使用状況(セッション9 時点)

| ポート | 用途 |
|---|---|
| 80 | proxy-manager(http) |
| 443 | proxy-manager(https) |
| 81 | proxy-manager(管理画面、内部) |
| 3000 | haramon_web |
| 8000 | gaku-co5(host network 経由) |
| 8100 | ig_scheduler(127.0.0.1 のみ) |
| 18789-18790 | openclaw(127.0.0.1 のみ) |

**5984(CouchDB デフォルト)は空き。** ただし新規サービスは原則 `127.0.0.1:` バインド + Nginx Proxy Manager 経由公開とするのが既存パターンと整合。

## Phase 3a の前提として確認済み事項

| 項目 | 状態 |
|---|---|
| Claude Code バイナリ存在 | ✅(v2.1.92、要 v2.1.150 アップグレード) |
| Claude Code 認証 | ✅(subscription auth 有効、`-p` モード稼働) |
| Node ランタイム | ✅(v22) |
| Python ランタイム | ✅(3.12) |
| Docker | ✅(v29.1.3) |
| Timezone JST | ✅ |
| ディスク余裕 | ✅(364 GB 空き) |
| メモリ余裕 | ✅(5.8 GB 利用可) |
| cron 追加余地 | ✅ |
| SSL 自動更新基盤 | ✅(Nginx Proxy Manager + LetsEncrypt) |

## 既知の懸念 / 未確認事項

- Claude Code v2.1.92 は58 リビジョン古い(2025-04 以降未更新)。アップグレード時に認証維持されるか要確認
- subscription auth の **同時セッション数制限**(WSL の塚越さん本人 + VPS の cron 自動実行)が出る可能性
- `~/codex-auth.json` の用途・必要性が未確認(セッション9 で塚越さんに保留)
- openclaw / haramon の安定性が Garden サービスに影響するか未確認(リソース競合は今のところなし)
- 古い `docker-compose.yml` の version 記法(`"3.9"`)が gaku-co5 等で残っている — Garden 側は新記法で書く

## 関連

- [ADR セッション6 — デイリーワークフロー種化アーキテクチャ](../decisions/2026-05-25-daily-workflow-and-task-master-architecture.md)
- [ADR セッション7 — 種スキーマ + 実行ホスト確定(VPS)](../decisions/2026-05-25-seed-schema-and-execution-host.md)
- [ADR セッション7 — VPS secret 管理方針](../decisions/2026-05-25-vps-secret-management-direction.md)
- [docs/security/README.md](../security/README.md)
- [garden/seeds/README.md](../../garden/seeds/README.md)
- [HMC ↔ gaku-co5 INTERFACE](file:///home/tukapontas/gaku-co5.0/INTERFACE.md)
