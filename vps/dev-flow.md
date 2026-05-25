---
type: reference
status: active
last_updated: 2026-05-26
purpose: VPS 上のリソースを開発・デプロイする時のフロー定義。2系統(ガクコ系 / その他系)
---

# 開発フロー

VPS 上のリソースは **2系統** に分かれる。

## (a) ガクコ系

**正本**: ローカル PC `/home/tukapontas/gaku-co5.0/` (`.git` あり、origin = `akiratsukakoshi/gaku-co5.0`)
**配信**: GitHub 経由
**VPS 上の場所**: `~/gaku-co5/`(`.git` 無し、ローカル PC のミラー + ビルド)

### 通常デプロイ

```
1. ローカル PC で開発 (~/gaku-co5.0/)
2. git commit + git push (origin/main)
3. VPS で ~/gaku-co5/deploy.sh 実行
   - GitHub から fetch
   - docker-compose build + restart
4. 動作確認(LINE personal でテストメッセージ)
```

### secret 配置

- ローカル `~/gaku-co5.0/.env`(git 除外)
- VPS `~/gaku-co5/.env`(git 無し、ローカルから手動 scp)
- 変更時はローカル → VPS の片方向(両方を編集して同期する運用ではない)

### 緊急時

- VPS 上で直接編集することは **避ける**(次の deploy で消える)
- どうしても緊急修正が必要な場合は: VPS で hotfix → 動作確認 → ローカル PC に持ち帰って commit → push → 再 deploy

## (b) その他 VPS 系(本 repo で正本管理)

**正本**: 本 repo `/home/tukapontas/harappa-garden/vps/` 配下
**配信**: GitHub 経由(本 repo) + scp / rsync(VPS への手動転送)
**VPS 上の場所**: サービスごとに `~/proxy-manager/`, `~/ig_scheduler/`, `~/garden/services/*/` 等

### 通常デプロイ

```
1. ローカル PC の本 repo (vps/proxy-manager/ 等) を編集
2. git commit + git push
3. ローカル → VPS に scp / rsync で転送
   例: scp vps/proxy-manager/docker-compose.yml harappa:~/proxy-manager/docker-compose.yml
4. VPS で docker compose up -d --build(or restart)
5. 動作確認
```

### secret 配置

- 本 repo の `.env.example` をテンプレに、VPS 上 `~/{service}/.env` を直接編集
- ローカル PC には secret 値は基本置かない(必要なら `docs/security/secrets/{service}.md` に保管 + git 除外)
- VPS の `.env` を変更したら、内容を `docs/security/secrets/{service}.md` にも反映(信頼境界はローカル WSL)

### Garden 専用サービス([garden/services/](../garden/services/))の扱い

NPM や ig_scheduler は `vps/` 配下だが、**Garden の種が依存するサービス**(現状は CouchDB)は [garden/services/](../garden/services/) 配下。理由:

- 種(seeds) / 区画(plots)からの距離が近い
- 「Garden の運用」と「VPS インフラ運用」を概念的に分離

実体的な差はないが、命名空間で分けることで設計議論がしやすくなる。

## 共通: 復旧手順

サービス別の復旧手順は [recovery.md](recovery.md) を参照。

## 共通: VPS 上の手書き禁止リスト

以下は VPS 上で直接編集すると、本 repo との乖離が発生して復旧不能になる。**必ずローカル PC で編集 → push → 転送** の順で。

- `~/proxy-manager/docker-compose.yml`
- `~/ig_scheduler/{Dockerfile, app.py, requirements.txt, docker-compose.yml}`
- `~/garden/services/*/docker-compose.yml`
- `~/garden/services/*/local.ini` 等の設定ファイル
- `crontab -e` の内容(編集後は [vps/cron/](cron/) にスナップショット更新が必要)

**例外**(VPS 上で編集 OK):
- 各サービスの `.env`(secret)— ローカルに置かない方針
- NPM の Proxy Host 設定(UI 経由のため。export スクリプトで定期取得)

## 共通: 動作確認

| サービス | 確認方法 |
|---|---|
| ガクコ | LINE personal で適当なメッセージ → 反応確認 |
| NPM | `https://{domain}/` で 200/30x が返ること |
| CouchDB | `curl -u admin:xxx https://gardendb.harappa.monster/_all_dbs` |
| ig_scheduler | `curl http://127.0.0.1:8100/` on VPS(host bind のため) |
| cron | `tail -f /tmp/{job}.log` |

## 関連

- [vps/README.md](README.md)
- [vps/recovery.md](recovery.md)
- [VPS 管理体制 ADR](../docs/decisions/2026-05-26-vps-management-policy.md)
