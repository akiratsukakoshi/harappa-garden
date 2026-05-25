# CouchDB + Obsidian Self-hosted LiveSync 実装(Phase 3a A-2 完了)

- **日付**: 2026-05-25
- **記録**: セッション10
- **決定者**: 塚越さん(庭師)/ Claude
- **ステータス**: 実装完了・運用開始
- **前提 ADR**: [2026-05-25-daily-workflow-and-task-master-architecture.md](2026-05-25-daily-workflow-and-task-master-architecture.md)(タスクマスタ層の設計合意)

## 背景

セッション6 ADR で「タスクマスタの置き場 = Obsidian LiveSync + VPS CouchDB」が合意済。Phase 3a A-2 がその実装フェーズ。
本セッションで「今日から使えるレベル」(数秒 push 同期 / E2EE / 3端末同期)に到達した実装決定を記録する。

---

## 決定 1: 既存 vault `gakuchovault` をそのまま LiveSync 化

### 採用

塚越さんの既存 Obsidian vault(`/mnt/c/Users/tukap/Dropbox/gakuchovault/`、4.3MB / 65ファイル)を Garden 専用に分けず、**vault 全体を CouchDB 同期に切り替え**。

### 構成

```
[既存 vault: gakuchovault]
├── 00_MOC/, archive/, development/, digihara/, Inbox/, newsletter/, personal/, 経営/, AGENTS.md
├── hmc_tasks/             ← 既存。HMC の active_tasks/backlog/archive/recurring_master が動いている
│   ├── active_tasks.md
│   ├── archive.md
│   ├── backlog.md
│   └── recurring_master.md
└── (将来) garden/         ← Phase 3a daily-pilot 種の作業領域はここに配置
    ├── board/
    └── inbox/
```

### 検討した代替と却下理由

| 代替 | 却下理由 |
|---|---|
| harappa-garden を vault 化 | 設計レポと運用データが混ざる。git 履歴が肥大化 |
| Garden 専用新規 vault | 塚越さんの hmc_tasks/ が既に動いており、移行コスト > 利益。LiveSync は vault 単位なので、結局 vault を切り替える操作が必要 |
| 既存 vault は Remotely Sync のままで Garden だけ別 vault | LiveSync の利点(push 同期)を hmc_tasks/ にも適用したい |

### 含意

- **Remotely Sync は無効化**(LiveSync と二重書き込みになるため)
- Dropbox 同期はそのまま放置(別経路、競合しない)— 二重バックアップとして機能
- 既存の `hmc_tasks/` が **そのまま** Phase 3a 種のターゲットになる
- iPhone は **新規 vault `gakuchovault-ls`** を作って Fetch(既存 vault は触らない、ダメージ 0 戦略)

---

## 決定 2: CouchDB を NPM の Docker ネットワークに参加させる(2NIC 方式)

### 課題

VPS 上で:
- Nginx Proxy Manager は `proxy-manager_default` ネットワーク(172.20.0.0/16)
- garden-couchdb は `garden-couchdb_default` ネットワーク(172.21.0.0/16)
- 別ネットワークなので互いに直接通信不可

CouchDB を `127.0.0.1:5984` だけにバインドしている(WAN 直公開しない方針)ため、NPM から到達経路を作る必要があった。

### 採用: external network 参加

`garden-couchdb/docker-compose.yml` に **`proxy-manager_default` ネットワーク を external として参加**させる方式:

```yaml
services:
  couchdb:
    networks:
      - default
      - npm

networks:
  default:
  npm:
    external: true
    name: proxy-manager_default
```

これで CouchDB コンテナが 2つのネットワークに同時所属:
- `garden-couchdb_default`(自分の compose プロジェクト)
- `proxy-manager_default`(NPM と共有)

NPM の Proxy Host 設定で **Forward Hostname = `garden-couchdb`** とすると、Docker 内蔵 DNS で解決され、NPM 内部から CouchDB に到達する。

### 検討した代替と却下理由

| 代替 | 却下理由 |
|---|---|
| CouchDB を `0.0.0.0:5984` で全方向公開 | WAN にも開く形になり、Nginx Proxy Manager の前段防御を迂回する |
| NPM 側 compose に external network 追加 | NPM は既存稼働サービスで、変更すると他ドメイン(harappa.monster / bot.harappa.monster / ig-api.harappa.monster)に影響する可能性 |
| docker network connect の手動接続 | コンテナ再作成時にリセット、永続化されない |

### Garden サービス追加パターンの確立

今後、Garden で新規サービスを追加する場合は **同じパターン**を採用:
1. 自分の docker-compose で `127.0.0.1:` バインド(WAN 直公開しない)
2. `proxy-manager_default` を external network として参加
3. NPM の Proxy Host で `garden-{service-name}` を Forward Hostname に指定

これにより、新規ドメイン追加時に SSL は Let's Encrypt 自動取得、防御は NPM 一元化、サービス間ネットワーク疎結合の状態を維持。

---

## 決定 3: E2EE オン / Path Obfuscation OFF / Obfuscate Properties OFF

### 設定

| 項目 | 値 | 理由 |
|---|---|---|
| End-to-End Encryption | **ON** | Cloud に同期するデータの基本要件。passphrase が漏れない限り CouchDB ダンプから内容は読めない |
| Path Obfuscation | **OFF** | Phase 3a A-3(平文 MD ミラー daemon)が CouchDB から ID(=ファイルパス)を読んで MD に展開する必要がある |
| Obfuscate Properties | **OFF** | Dataview / Bases 等 frontmatter を使うプラグインに影響しないため + path obfuscation と一貫性 |
| Case-Sensitive | **OFF** | Windows(NTFS)/ iPhone(APFS)とも case-insensitive なので、CouchDB だけ case-sensitive にすると同期衝突が起きる |
| Chunk size | **60** (約 6MB 上限) | V3 Rabin-Karp + Self-hosted CouchDB 推奨値。`0`(旧 default)だと過剰に小さい chunk になり doc 数が無駄に多くなる |
| Per-file Customisation Sync | ON | Customisation Sync 本体は OFF だが、将来 ON にした時に新方式で動く準備 |

### 信頼境界モデル

- VPS 管理者 = 塚越さん本人(secret ADR の前提と一致)
- CouchDB ダンプは塚越さん本人ならいつでも可能だが、E2EE のおかげで passphrase なしでは復号不能
- 平文 MD ミラー daemon は **VPS 上で passphrase を保持** して MD に展開できる(Phase 3a A-3 実装時に詳細)
- WAN 公開部分は NPM + Let's Encrypt SSL + CouchDB Basic 認証で多層防御

### 検討した代替

- **Path Obfuscation ON** — VPS daemon が暗号化された ID から元のパスを再構築できなくなる。daemon に passphrase を渡せば可能だが、複雑度が増す。当面 OFF
- **E2EE OFF** — VPS daemon の実装は簡単になるが、CouchDB ダンプから内容が直接読める。secret ADR の方針(rotation あり、信頼境界明示)と整合させて E2EE オン

---

## 決定 4: 端末追加は Setup URI 方式

### 課題

iPhone セットアップで Wizard の最初の選択肢を間違え、「新規セットアップ」モードに入った結果、「Restart and Initialise Server」(CouchDB 上書き)しか進める選択肢がなくなった。これを押すと PC からアップロードした 337 docs が消える。

### 採用: Setup URI でのコピー

PC で全設定(URI / user / password / E2EE passphrase / chunk size / case-sensitivity 等)を **暗号化された URI 1本**に圧縮し、それを iPhone でペーストして自動セットアップ。

利点:
- passphrase の入力ミスが起きない(PC 側で 1回だけ正しく入れれば、iPhone は自動同期)
- 全設定が PC と一致する保証
- 端末追加時の選択肢は「**Use the copied setup URI from another device**」を選ぶだけ

### 教訓

iPhone Wizard の **最初の選択肢**で「既存の同期構成に端末を追加」を選ばないと、後から方向修正できない場合がある。**新規 vault に追加端末を入れる時は最初から Setup URI 方式**で進める。

---

## 決定 5: CouchDB の local.ini 主要設定

```ini
[couchdb]
single_node = true
max_document_size = 50000000

[cluster]
n = 1
q = 1

[chttpd]
require_valid_user = true
max_http_request_size = 4294967296
bind_address = 0.0.0.0
enable_cors = true

[chttpd_auth]
require_valid_user = true
authentication_redirect = /_utils/session.html

[httpd]
WWW-Authenticate = Basic realm="couchdb"
enable_cors = true

[cors]
origins = app://obsidian.md,capacitor://localhost,http://localhost
credentials = true
headers = accept, authorization, content-type, origin, referer
methods = GET, PUT, POST, HEAD, DELETE
max_age = 3600
```

### 重要ポイント

- **`[cluster] n=1, q=1`**: これがないと CouchDB が "Request to create N=3 DB but only 1 node(s)" エラーで `_users` 作成に失敗する
- **`[cors] origins`**: `app://obsidian.md` と `capacitor://localhost` は LiveSync(Obsidian デスクトップ / iOS)の origin 識別子。両方必須
- **`max_document_size = 50MB`**: LiveSync が大きな chunk を書き込むため拡張
- **healthcheck は外した**: apache/couchdb:3.4 image に curl/wget 含まれていないので healthcheck が永久失敗 → restart loop。`require_valid_user=true` のため `/_up` も 401 を返す。LiveSync 側で動作確認するため、container healthcheck は不要

---

## 決定 6: docker-compose v1.29 互換のため `version: '3.8'` 表記

### 課題

VPS には `docker-compose` v1.29.2(legacy)のみインストールされており、Docker Compose v2 plugin は未導入。
v1 では `name:` トップレベルキー / `version:` キー無しの新記法は理解されない。

### 採用

`docker-compose.yml` に `version: '3.8'` を明示し、起動時は `-p garden-couchdb` でプロジェクト名指定:

```bash
docker-compose -p garden-couchdb up -d
```

### 制約

- docker-compose v1.29 は 2023 年に EOL
- 新しい image の `image_config['ContainerConfig']` 仕様変更との非互換が出る(コンテナ recreate 時の `KeyError`)
- 対応策: `down → up` のクリーン再作成サイクルを使う(`up -d` 単独だと recreate でコケる場合あり)
- 将来課題: Compose v2 plugin への移行(`apt install docker-compose-plugin`)

---

## 決定 7: secret 管理

| secret | 保管場所 | アクセス手段 |
|---|---|---|
| CouchDB admin password | VPS `~/garden/services/couchdb/.env`(chmod 600)+ ローカル `docs/security/secrets/garden-couchdb.md`(git 除外) | `cat` で直接 |
| E2EE passphrase | 上記 secrets ファイル | 同上 |
| NPM admin password | 塚越さん本人記憶 + 各自パスワードマネージャ | NPM UI |
| Setup URI 暗号化 passphrase | 一時的(URI 受け渡し完了後不要) | 不要 |

`.gitignore` に `docs/security/secrets/*` パターンを追加(`!.gitkeep` で空ディレクトリは追跡)。

### rotation 方針

secret ADR(セッション7)の方針通り:
- 発覚時 + 年1強制
- 次回 rotation 目安: 2027-05-25
- 記録: `docs/security/incidents/`

---

## 決定 8: NPM admin パスワードリセットは bcrypt(node-bcrypt) で

### 課題

NPM の auth テーブルは bcrypt ハッシュで保存。`bcryptjs`(純 JS)は image に含まれず、`bcrypt`(ネイティブ)のみインストール済。
最初の試みで `bcryptjs` を指定 → ハッシュが空のまま UPDATE 実行 → ログイン完全不可状態に陥った。

### 採用

```bash
HASH=$(docker exec -w /app proxy-manager_nginx-proxy-manager_1 \
  node -e "console.log(require('bcrypt').hashSync(process.argv[1], 13))" "$TEMPPASS")
```

- `-w /app` で cwd を NPM の app ルートにする(node_modules が解決される)
- `bcrypt`(`bcryptjs` ではない)を require
- rounds は 13(NPM のデフォルト)
- ハッシュ生成後、長さチェック(60 字未満なら abort)してから UPDATE

### 教訓

VPS 側のリセット操作は **生成 → 長さ assertion → DB 反映** の三段で必ず行う。途中失敗時に DB が壊れる事故を防ぐ。

---

## 実装ファイルツリー

```
harappa-garden/
├── garden/services/couchdb/
│   ├── docker-compose.yml      # version: '3.8' + 2 networks
│   ├── local.ini               # CORS / single_node / cluster / chunk 等
│   ├── README.md               # 用途 / 構成 / デプロイ手順 / 関連
│   ├── .env.example            # admin user/password テンプレ
│   └── .gitignore              # data/ と .env 除外
└── docs/
    ├── security/secrets/
    │   ├── .gitkeep
    │   └── garden-couchdb.md   # admin / passphrase 保管(git 除外)
    └── decisions/
        └── 2026-05-25-couchdb-livesync-implementation.md  # 本ファイル

VPS (vps-harappa@x162-43-40-86):
~/garden/services/couchdb/
├── docker-compose.yml
├── local.ini
├── .env                        # chmod 600
└── data/                       # CouchDB データボリューム(uid 5984)
```

---

## 動作確認結果

| 項目 | 結果 |
|---|---|
| PC Obsidian 初回 upload | 65 ファイル → 337 docs(chunk 分割込み)、数秒で完了 |
| iPhone Setup URI Fetch | 65 ファイル取得、数秒で完了 |
| PC → CouchDB → iPhone(往路) | ✅ ほぼリアルタイム |
| iPhone → CouchDB → PC(復路) | ✅ ほぼリアルタイム |
| CouchDB doc_count(両端設定後) | 341 |
| CouchDB DB サイズ | 668 KB(E2EE 暗号化済) |
| SSL | Let's Encrypt 自動取得 OK |
| 認証経路 | NPM → garden-couchdb:5984 → Basic 認証 |

---

## 適用範囲

### 即時(本セッション完了)

- 上記ファイル群すべて起草・配置
- VPS デプロイ + 起動 + 初期化 + 動作確認
- 塚越さん PC + iPhone のセットアップ完了
- 認証情報の secret ファイル保管

### Phase 3a 残課題(次セッション以降)

- **A-1: 本番ランチャー設計**(`.scratch/` を育てる)
- **A-3: 平文 MD ミラー daemon の実装**(`_changes` feed リスナで CouchDB ↔ VPS `/home/vps-harappa/garden-mirror/` 双方向)
- **A-4: watcher daemon**(event 種用)
- **連絡板 `garden/board/` の構造設計**
- gakuchovault 内に `garden/` フォルダ作成 + recurring_master.md の整備

---

## 関連

- [ADR セッション6 — タスクマスタアーキテクチャ](2026-05-25-daily-workflow-and-task-master-architecture.md)
- [ADR セッション7 — 種スキーマ + 実行ホスト](2026-05-25-seed-schema-and-execution-host.md)
- [ADR セッション7 — VPS secret 管理方針](2026-05-25-vps-secret-management-direction.md)
- [garden/services/couchdb/README.md](../../garden/services/couchdb/README.md)
- [docs/vps/current-state.md](../vps/current-state.md)
- [docs/security/secrets/garden-couchdb.md](../security/secrets/garden-couchdb.md)(git 除外)
- [Obsidian Self-hosted LiveSync 公式](https://github.com/vrtmrz/obsidian-livesync)
