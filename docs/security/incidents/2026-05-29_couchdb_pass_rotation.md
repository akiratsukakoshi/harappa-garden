# 2026-05-29 CouchDB admin パスワード露出・ローテーション

## 概要

Garden の CouchDB(`garden-couchdb`、Obsidian Self-hosted LiveSync の同期先)の admin (`garden-admin`) パスワードが、セッション14(2026-05-27)の writeback-daemon 開発中に **AI 会話トランスクリプトへ露出**していた。セッション17(2026-05-29)で当該パスワードのローテーションを完了。新パスは CouchDB・mirror-daemon・writeback-daemon・Obsidian(PC/iPhone)の全消費者へ反映し、旧パスを失効させた。

E2EE パスフレーズ(LiveSync の暗号化鍵)は**別の秘密**であり、露出も変更もしていない。今回変えたのは CouchDB への basic auth パスワードのみ。

## 発覚経緯

セッション14 で writeback-daemon をデバッグ中、`wget --password=...` のエラー出力に CouchDB パスワード値が含まれ、AI 会話履歴に残った。同セッションのサマリ([2026-05-27-session14.md](../../sessions/2026-05-27-session14.md) 「⚠️ セキュリティインシデント発生」)で「セッション終了後 rotation 必須」と記録。以後 S15〜S17 にわたり MAP の **最優先・継続宿題**として持ち越されていた(3セッション)。

## 漏洩経路

| 経路 | 露出形態 | 対応 |
|---|---|---|
| S14 AI 会話トランスクリプト(ローカル) | `wget --password=<value>` のエラー出力に平文 | ✅ ローテートで旧値を失効(トランスクリプト自体は旧値=無効値なので実害ゼロ化) |
| git リポジトリ | `.env` は `.gitignore` 済、追跡は `.env.example`(placeholder)のみ | ✅ 露出なし(`git ls-files` で確認) |
| VPS `~/.bash_history` | `wget --password=` 該当 0 件 | ✅ 残存なし(非対話 ssh 実行は履歴非記録のため) |

## リスク評価

- このパスワードは **単一の共有 admin パスワード**であり、CouchDB admin / mirror-daemon / writeback-daemon / LiveSync クライアント(PC・iPhone)の **5 消費者**すべてで使い回されていた。
- 取得されれば `https://gardendb.harappa.monster`(WAN 公開、Nginx Proxy Manager 経由)へ basic auth でアクセスし、DB の暗号化ドキュメントの読み書き・admin 操作が可能。ただし中身は E2EE 済(passphrase 未露出)なので平文タスクデータの直接読取りは不可。
- 露出先はローカル AI トランスクリプトのみで外部公開はないが、3セッション放置していたため即時ローテを実施。

## 対応内容(すべて 2026-05-29)

### 1. 新パスワード生成(VPS 上、値は非表示)

```bash
NEWPASS="$(openssl rand -base64 48 | tr -d '\n/+=' | head -c 32)"   # 英数字32文字(sed/shell 安全)
```

### 2. CouchDB admin パスワード変更(`_config` API、即時反映・永続)

```bash
# 旧パスで認証して新パスを設定。CouchDB がハッシュ化して保存
curl -X PUT -u "garden-admin:$OLDPASS" \
  -H 'Content-Type: application/json' --data-binary "\"$NEWPASS\"" \
  http://127.0.0.1:5984/_node/_local/_config/admins/garden-admin
```

- 書き込み先 = config チェーン最後の writable ファイル = `local.d/local.ini`(= host マウント `~/garden/services/couchdb/local.ini`)。**コンテナ recreate でも生存**することを、running config のハッシュと host `local.ini` のハッシュが一致することで確認済。
- CouchDB コンテナの再起動は**不要**(`_config` は即時反映)。

### 3. 3つの `.env` を新パスへ書換(VPS、いずれも chmod 600)

- `~/garden/services/couchdb/.env`(`COUCHDB_PASSWORD`)
- `~/garden/services/mirror-daemon/.env`(`COUCHDB_PASS`)
- `~/garden/services/writeback-daemon/.env`(`COUCHDB_PASS`)

### 4. daemon 2本を recreate(新 `.env` 反映)

- `docker-compose up -d --force-recreate` は **固定 `container_name` + project ラベル不一致で衝突**したため、`docker stop && docker rm && docker-compose up -d` で作り直し。
- mirror-daemon: state(host ボリューム)復元 → `_changes` 購読再開 → `[put]` 成功(認証OK)。
- writeback-daemon: `initial reconcile done (17 md files)` → `[skip] (no change vs CouchDB)`(読み比較成功=認証OK)。
- いずれも 401 なし。

### 5. Obsidian クライアント(ガクチョ手動)

- 新パスは VPS の `~/garden-newpass.txt`(chmod 600)に置き、**ガクチョご自身の別ターミナルで `cat`** して取得(AI チャットを経由させない=§1.4 遵守)。
- PC: LiveSync の **Password 欄のみ**新パスへ。URI / Username / Database / **E2EE passphrase** は不変。「Test Database Connection」成功を確認。
- iPhone: Setup URI 方式で再構成(S10 の確立パターン)。
- 両端末で同期再開を確認。

### 6. クリーンアップ

- `~/garden-newpass.txt` を `shred -u` で消去。
- VPS bash 履歴に CouchDB パスワード残存なしを確認(掃除対象なし)。

## 検証(ゲート)

| ゲート | 結果 |
|---|---|
| 旧パスで `/_up` 認証(変更前) | HTTP 200 ✅ |
| `_config` PUT admins | HTTP 200 ✅ |
| 新パスで `/_session`(`_admin` ロール) | `{"ok":true,...,"roles":["_admin"]}` ✅ |
| 旧パスで `/_up`(変更後) | HTTP 401 ✅(失効) |
| `_config` 書込が host `local.ini` に着地 | running hash == host hash ✅(recreate 生存) |
| mirror / writeback daemon 再接続 | 401 なし、pull / 比較成功 ✅ |
| Obsidian PC / iPhone | Test 成功・同期再開 ✅ |

## 知見(次回ローテのための教訓)

1. **CouchDB パスは単一共有・5消費者**(CouchDB admin / mirror / writeback / Obsidian×2)。1個変えると全部更新が必要。将来は LiveSync 用に非 admin の専用 DB ユーザーを分けると blast radius を下げられる(未実施・改善余地)。
2. **`_config` API が正道**:即時反映 + host `local.ini`(チェーン最後)へ永続。CouchDB 再起動不要。
3. **`/_up` も認証必須**(`require_valid_user = true`)。PUT 直後に一瞬 401 が出る(伝播ブリップ)が数秒で解消。慌てて二重変更しないこと。
4. **この VPS は docker-compose v1**(ハイフン)。`--force-recreate` は固定 `container_name` と衝突 → `stop && rm && up` が確実。
5. **秘密の受け渡し**は VPS の chmod 600 ファイル + ガクチョ自身のターミナルで `cat`。AI チャットに値を出さない(§1.4)。iPhone は Setup URI で手打ち回避。
6. **非対話 ssh 実行は VPS bash 履歴に残らない** → ローテ作業のコマンドは履歴汚染しない(好都合)。

## 残作業 / 別件

- [ ] **付随発見(別 secret)**: VPS `~/.bash_history` に旧 n8n デプロイの `N8N_BASIC_AUTH_PASSWORD` が平文で2行残存(現在 n8n コンテナは非稼働)。CouchDB とは無関係。扱い(履歴掃除 / n8n パス rotation / 放置)はガクチョ判断待ち。
- [ ] **年1強制ローテ**の起点に本日を記録([VPS secret 管理方針 ADR §6.4](../../decisions/2026-05-25-vps-secret-management-direction.md))。
- [ ] 将来改善: LiveSync 用の非 admin 専用 CouchDB ユーザー分離(blast radius 低減)。

## 関連

- 運用ルール本体: [`../README.md`](../README.md)(§1.4 secret 確認コマンド・§4 緊急時対応原則)
- VPS secret 管理方針: [decisions/2026-05-25-vps-secret-management-direction.md](../../decisions/2026-05-25-vps-secret-management-direction.md)(決定4: rotation = 発覚時 + 年1強制)
- 露出元セッション: [sessions/2026-05-27-session14.md](../../sessions/2026-05-27-session14.md)
- 前例(手順の踏襲元): [2026-05-23 GOG keyring 漏洩](2026-05-23_gog_keyring_rotation.md)
- CouchDB サービス: [garden/services/couchdb/README.md](../../../garden/services/couchdb/README.md)
