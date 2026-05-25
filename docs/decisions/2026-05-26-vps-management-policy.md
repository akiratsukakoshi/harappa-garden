---
title: VPS 管理体制方針(ガクコ系 / ガクコ以外系の2系統 + 本 repo `vps/` 配下集約)
date: 2026-05-26
status: accepted
session: 11
authors: [塚越さん, claude]
related:
  - docs/decisions/2026-05-25-vps-secret-management-direction.md
  - docs/vps/current-state.md
---

# VPS 管理体制方針

## 背景

VPS(harappa.monster / 162.43.40.86)上には HARAPPA 事業の主要リソースが多数稼働している(ガクコ, NPM, garden-couchdb, openclaw, ig_scheduler, haramon, cron 等)。セッション10 終了時点では:

- `gaku-co5.0` はローカル開発 → GitHub → VPS で fetch + rebuild のフローが確立済(復旧可能)
- `garden/services/couchdb/` は本 repo に commit 済(復旧可能)
- **それ以外のリソース(NPM, ig_scheduler, proxy-manager, cron, etc.)は VPS 上に直書きされ git 管理が不在 or 不徹底**
- 特に **NPM 内部 DB(Proxy Host / SSL 設定)** は手動 UI 投入のみで、コンテナ volume が消えれば復旧手段なし

要件:
1. ステータスがドキュメント化される(常時最新の見取り図)
2. 別リポの AI からも状況把握できる(本 repo + ガクコ repo 横断で読める)
3. GitHub にプッシュされ、トラブル時に復旧できる

## 決定

### 1. 管理範囲を「ハラッパ事業直結」で線引きする

| 範囲 | 対象 | 管理場所 |
|---|---|---|
| **本 repo `vps/` で集約** | NPM(proxy-manager), ig_scheduler, cron, gaku-co5(参照のみ) | [vps/](../../vps/) |
| **本 repo `garden/services/`** | CouchDB 等 Garden 専用サービス(種が依存) | [garden/services/](../../garden/services/) |
| **別 repo で完結** | gaku-co5.0(`akiratsukakoshi/gaku-co5.0`), haramon(`akiratsukakoshi/haramon`) | 各 GitHub repo |
| **管理対象外** | gaku-co-oc(`openclaw/openclaw` の上流 fork)、n8n(旧設定残骸) | VPS 上のみ |

判断理由:
- ig_scheduler は **HMC の sns_pilot SKILL の一環**(Instagram 投稿予約)なのでハラッパ直結
- haramon は別 repo で完結しており開発フローも独立、本 repo に取り込む必要なし
- openclaw は上流 fork で公開コード、ハラッパ事業との結合度が低い

### 2. ガクコは別 repo 継続 + 本 repo から参照のみ

- ガクコ(`/home/tukapontas/gaku-co5.0/` ↔ GitHub: `akiratsukakoshi/gaku-co5.0`)は既に開発フロー確立済
- 本 repo に submodule 取り込み等はしない(submodule 運用の煩雑さを避ける)
- 本 repo の [vps/README.md](../../vps/README.md) から GitHub URL と INTERFACE.md を参照させる
- ガクコ repo 側 README にも「VPS 全体管理は harappa-garden の `vps/` を参照」と1行追加

### 3. NPM 内部設定は定期 export スクリプト + 本 repo に commit

- NPM の Proxy Host / SSL / カスタム Nginx 設定は `proxy-manager/data/database.sqlite` + `letsencrypt/` に保存される
- これを **定期 export スクリプト** で tar.gz 化、本 repo の [vps/backups/](../../vps/backups/) に取得
- **ただし SSL 秘密鍵を含むため git 除外**(`.gitignore` に `vps/backups/`)
- 実体はローカル WSL にだけ保管(secret と同じ信頼境界)
- 「commit」の意味は「定期実行 + 機械的保管 + 復旧手順の文書化」を指す。GitHub への push は将来課題(暗号化前提)

### 4. secret 管理は既存方針を継続

- [`docs/security/secrets/`](../security/secrets/) にローカル平文保管、git 除外
- WSL 全壊時のリスクは [2026-05-25 secret 管理 ADR](2026-05-25-vps-secret-management-direction.md) と同じ信頼境界
- Phase 3b で外部 storage(1Password 等)への二重化を検討

### 5. 開発フローを2系統で明確化

**(a) ガクコ系** = ローカル PC が正本、GitHub 経由配信
```
local PC (~/gaku-co5.0/, .git あり)  →  GitHub  →  VPS ~/gaku-co5/ (.git 無し、deploy.sh で取得)
```

**(b) その他 VPS 系** = 本 repo `vps/` が正本、ssh 経由配信
```
local PC (~/harappa-garden/vps/, .git あり)  →  GitHub  →  VPS ~/garden/, ~/proxy-manager/, ~/ig_scheduler/ (rsync or scp)
```

詳細は [vps/dev-flow.md](../../vps/dev-flow.md)。

## 影響

### 新設

- [vps/](../../vps/) ディレクトリ + 全配下ファイル
- [docs/decisions/2026-05-26-vps-management-policy.md](2026-05-26-vps-management-policy.md)(本 ADR)

### 更新

- [garden/MAP.md](../../garden/MAP.md) — 区画表に VPS 管理を追加
- ガクコ repo `README.md` — 本 repo への参照を1行追加
- 本 repo `.gitignore` — `vps/backups/`, `vps/ig_scheduler/.env` 等の secret 系除外

### 残課題(Phase 3b 以降)

- NPM backup の **暗号化 → GitHub push** 経路(現状はローカル WSL のみ)
- secret の **WSL 外** バックアップ(1Password / 暗号化 zip 等)
- gaku-co-oc のローカル差分(未コミット変更)の上流 PR 化 or 内部 repo 化判断
- VPS の **状態スナップショット自動化**(`docker ps` / `df -h` / 構成差分の cron 取得 → `vps/snapshots/`)

## 棚卸し(@2026-05-26 時点)

| ディレクトリ on VPS | git | リモート | 本 repo での扱い |
|---|---|---|---|
| `~/gaku-co5/` | ❌ | 別 repo `akiratsukakoshi/gaku-co5.0` | [vps/README.md](../../vps/README.md) から参照 + INTERFACE.md 写し |
| `~/gaku-co-oc/` | ✅ | `openclaw/openclaw` + ローカル差分 | 管理対象外(別途検討) |
| `~/haramon/` | ✅ | 別 repo `akiratsukakoshi/haramon` | 管理対象外 |
| `~/ig_scheduler/` | ❌ | なし | [vps/ig_scheduler/](../../vps/ig_scheduler/) で正本管理 |
| `~/proxy-manager/` | ❌ | なし | [vps/proxy-manager/](../../vps/proxy-manager/) で正本管理 |
| `~/garden/` | ❌ | なし | 本 repo の [garden/services/](../../garden/services/) + [vps/](../../vps/) で正本管理 |
| crontab | ❌ | — | [vps/cron/crontab.snapshot](../../vps/cron/) で版管理 |

## 関連

- [VPS 現状サマリ(セッション9)](../vps/current-state.md)
- [VPS secret 管理方針(セッション7)](2026-05-25-vps-secret-management-direction.md)
- [garden/MAP.md](../../garden/MAP.md)
