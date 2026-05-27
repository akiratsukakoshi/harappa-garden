# 平文 MD ミラー daemon 実装(Phase 3a A-3 完了)

- **日付**: 2026-05-27
- **記録**: セッション12
- **決定者**: 塚越さん(庭師)/ Claude
- **ステータス**: 実装完了・運用開始
- **前提 ADR**:
  - [2026-05-25-daily-workflow-and-task-master-architecture.md](2026-05-25-daily-workflow-and-task-master-architecture.md) — タスクマスタ層
  - [2026-05-25-couchdb-livesync-implementation.md](2026-05-25-couchdb-livesync-implementation.md) — LiveSync 実装

## 背景

セッション10 で CouchDB + LiveSync が完成し、E2EE オン + Path Obfuscation OFF の状態で 3 端末同期が動いた。**「VPS 上で passphrase を保持して平文 MD に展開する daemon」を実装するための前提が整った**。

セッション11 は VPS 管理体制の確立(寄り道)、本セッションで Phase 3a A-3 本命に戻る。

種(daily-pilot 4本など)は MD を素朴な操作(`cat` / `grep` / `head`)で読みたい。各種スクリプトに E2EE 復号ロジックを埋め込むのは現実的でない → daemon が一箇所で復号して **平文ミラー** を維持する、という方向。

---

## 決定 1: 単方向(CouchDB → MD)から始める

### 採用

ADR(セッション10)には「双方向」と書いていたが、本セッションで **当面は単方向に絞る** ことに合意。

| 観点 | 単方向先行の理由 |
|---|---|
| 種の用途 | 当面は MD を **読む** 用途が先(morning-briefing が backlog を読む等)。書く側は連絡板 / archive 転記が主で、これは Phase 3a A-1 本番ランチャー + 連絡板設計と密結合 |
| 競合解決 | 双方向同期は同時編集の merge 戦略が必要(LiveSync 自身がやっているのを daemon が再実装することになる) |
| デバッグ容易性 | 単方向なら mirror 側の write 主体が daemon 1 つ。バグ追跡が単純 |
| 後付け可能性 | 後から書き戻し経路を足すのは可能(連絡板 → CouchDB の PUT を別 daemon or 別経路で) |

### 含意

- 種が MD を書きたい場合は「連絡板 `garden/board/` への書き込み」として別経路を設計(Phase 3a A-1 と同期)
- mirror 側で誤って編集された場合、次回 CouchDB 側変更時に **上書きされる**(mirror は CouchDB の写しという位置づけ)

---

## 決定 2: 実装言語 = Node.js + octagonal-wheels 直接利用

### 採用

obsidian-livesync の暗号モジュール本体である [`octagonal-wheels`](https://github.com/vrtmrz/octagonal-wheels) を npm 経由でそのまま使う。

### 検討した代替と却下理由

| 代替 | 却下理由 |
|---|---|
| Python で PBKDF2 + HKDF + AES-GCM を自前実装 | 仕様変更追従コスト高。LiveSync が暗号方式を変更した場合に都度合わせる必要 |
| Python 本体 + Node.js を subprocess で呼ぶハイブリッド | オーバーヘッドあり、エラー伝播も複雑 |
| Rust / Go で再実装 | 同上の追従コスト。並行性も daemon 規模では不要 |

### 実装の薄さ

復号本体は 1 行:

```js
import { decrypt as decryptHkdf } from "octagonal-wheels/encryption/hkdf";
const plaintext = await decryptHkdf(chunk.data, passphrase, pbkdf2Salt);
```

毎日 npm が `octagonal-wheels` の新版を出しても、API が変わらなければ daemon に変更不要。

---

## 決定 3: 暗号方式の理解(LiveSync の `%=` プレフィックス)

LiveSync の chunk doc の `data` フィールドは `%=` プレフィックス付き base64 文字列。これは `octagonal-wheels/encryption/hkdf.ts` の `HKDF_ENCRYPTED_PREFIX` に対応。

### スキーム

```
data = "%=" + base64( IV(12B) | hkdfSalt(32B) | ciphertext+GCMTag )
```

復号フロー:

1. PBKDF2-SHA256(passphrase, pbkdf2Salt, 310_000 iters) → master key (32B)
2. HKDF-SHA256(masterKey, hkdfSalt, info=空) → chunk key (32B)
3. AES-GCM(chunkKey, iv) で復号

### PBKDF2 salt の所在(本セッションの主要発見)

セッション10 時点では「passphrase 1 つで復号できる」と考えていたが、**実際には PBKDF2 salt も必須**で、これは **CouchDB の `_local/obsidian_livesync_sync_parameters` doc** に格納されている(`pbkdf2salt` フィールド、base64 エンコード)。

LiveSync は「Security Seed」と呼んでいる(updates_old.md より)。passphrase の総当たり攻撃を遅らせる salt として、サーバ側で初回作られ、以後固定。

→ daemon は起動時にこの doc を取りに行く。passphrase が同じでも salt が違えば復号不能(セキュリティ的に妥当)。

### doc 構造

```json
{
  "_id": "agents.md",          // lowercase path (Case-Sensitive OFF)
  "_rev": "1-...",
  "path": "AGENTS.md",          // 元の大文字小文字
  "children": ["h:+4yz...", ...], // chunk doc id 配列
  "ctime": 1779148637314,
  "mtime": 1779683815788,
  "size": 7213,
  "type": "plain",              // または "newnote"
  "eden": {}
}
```

chunk doc:

```json
{
  "_id": "h:+4yz8facvrx56",
  "_rev": "1-...",
  "data": "%=NN0HCoO...",       // 暗号化 base64
  "type": "leaf",
  "e_": true                    // E2EE フラグ
}
```

---

## 決定 4: 配置先 = VPS `/home/vps-harappa/garden-mirror/`

セッション10 ADR で「VPS daemon は平文 MD を扱う前提」とした方向に沿う。種は VPS で動くので、VPS 上の一箇所に置くのが最短経路。

ローカル WSL にも同期するかは将来課題(LiveSync 経由で既に PC Obsidian が持っているので、現状ニーズなし)。

---

## 決定 5: スコープ = MD のみ

vault には添付ファイル(画像・PDF 等)も含まれるが、**MD ファイルのみ**を mirror 対象とする。

理由:
- 種は MD しか読まない見込み
- バイナリは base64 chunk 経由の復号で処理コストが高い
- ディスク容量(vault 全体 4.3MB のうち画像が多くを占める)

将来必要になれば、`doc.path` の拡張子判定を緩めるだけで対応可能。

---

## 決定 6: chunk キャッシュ in-memory + LRU 風

LiveSync の chunk は **content-addressed**(`h:{hash}` ID で内容固定)なので、一度復号すれば再利用できる。

daemon は in-memory Map にキャッシュし、`CHUNK_CACHE_MAX = 5000` を超えたら古いものから落とす。

state.json には保存しない(再起動時は再 fetch / 再復号)。これは復旧時間と引き換えにシンプル化を優先した選択。

---

## 決定 7: state.json による last_seq 永続化

`_changes?feed=continuous&since={last_seq}` の `last_seq` を `/data/state.json` に保存。再起動後は中断地点から再開。

合わせて `path_by_id: { [_id]: path }` を保持。これは **削除イベント時に `path` フィールドが消える** ため、mirror 側のどのファイルを消すか引くのに必要。

書き込みは atomic(`*.tmp` → rename)。

---

## 決定 8: Garden サービスの追加パターン適用

セッション10 で確立した「Garden サービス追加パターン」の 2 例目。

- 自分の docker-compose で他コンテナと接続するため、`garden-couchdb_default` を **external network** として参加
- `garden-couchdb` を container_name で DNS 解決(`http://garden-couchdb:5984` で到達)
- NPM 側は触らない(WAN 公開不要なので)

```yaml
networks:
  couchdb:
    external: true
    name: garden-couchdb_default
```

CouchDB は同時に 2 ネットワーク(`garden-couchdb_default` と `proxy-manager_default`)に所属しているため、mirror-daemon は LAN 経由(内側)で CouchDB に接続できる一方、NPM は WAN 公開の役割を継続。

---

## 実装ファイルツリー

```
garden/services/mirror-daemon/
├── README.md            # 役割・起動手順・トラブルシュート
├── Dockerfile           # node:20-alpine ベース、3 ステップ
├── docker-compose.yml   # version:3.8 + external network
├── package.json         # octagonal-wheels のみ
├── mirror.mjs           # daemon 本体(約 230 行)
├── .env.example         # COUCHDB_USER / COUCHDB_PASS / E2EE_PASSPHRASE / MIRROR_HOST_PATH
└── .gitignore           # .env / node_modules / data / package-lock.json

VPS:
~/garden/services/mirror-daemon/
├── (上記同一の構成)
├── .env                 # chmod 600
└── data/                # state.json(last_seq + path_by_id)

~/garden-mirror/         # 平文 MD ミラー先(daemon が write)
├── AGENTS.md
├── hmc_tasks/
├── 00_MOC/
├── archive/
├── digihara/
├── development/
├── newsletter/
├── personal/
└── 経営/
```

---

## 動作確認結果

| 項目 | 結果 |
|---|---|
| 初期同期 | 58 docs 走査 → 56 MD ファイル書き出し(2 docs スキップ = MD 以外) |
| ライブ同期 | 塚越さん PC で `gardenテスト.md` 新規作成 → 数秒で daemon の `[put]` ログ + mirror に書き出し |
| 復号正当性 | UTF-8 日本語(`AGENTS.md` の冒頭 200 文字)を平文一致確認 |
| atomic write | `*.tmp` → rename で書き込み中の不完全状態が外部から見えない |
| state.json | last_seq + path_by_id を永続化、再起動で中断地点復帰 |
| network 接続 | `garden-couchdb_default` external network 経由で疎通 |
| restart policy | `unless-stopped` で daemon 落ちても自動復帰 |

---

## 制約と将来課題

### 当面の制約

- **MD のみ**(添付ファイルなし)
- **単方向**(書き戻しなし)
- **chunk キャッシュは in-memory**(再起動でリセット)
- **削除はソフト**(空ディレクトリ放置)

### 後フェーズで対応する課題

- **書き戻し経路**: 種が連絡板に MD を書く時、何経由で CouchDB に届けるか(Phase 3a A-1 / 連絡板設計と同期)
- **garden-mirror の git 管理**: 現状 daemon は VPS 単独。万一 daemon が壊れて全 wipe したら CouchDB から再構築は可能だが時間がかかる。バックアップ要否を判断
- **PBKDF2 salt のローテーション**: E2EE passphrase ローテ時は salt も変わる可能性。daemon 側で sync_parameters を定期再取得するか、起動時のみで運用するか
- **ヘルスチェック**: 現状は `docker logs` 目視。Phase 3b で番人 watcher が監視する想定

---

## 関連

- [garden/services/mirror-daemon/README.md](../../garden/services/mirror-daemon/README.md)
- [garden/services/mirror-daemon/mirror.mjs](../../garden/services/mirror-daemon/mirror.mjs)
- [octagonal-wheels/encryption/hkdf.ts](https://github.com/vrtmrz/octagonal-wheels/blob/main/src/encryption/hkdf.ts)
- [obsidian-livesync sync.definition.ts](https://github.com/vrtmrz/livesync-commonlib/blob/main/src/common/models/sync.definition.ts) — `DOCID_SYNC_PARAMETERS` / `pbkdf2salt` の定義場所
- [前提 ADR セッション10: LiveSync 実装](2026-05-25-couchdb-livesync-implementation.md)
- [VPS 管理方針](2026-05-26-vps-management-policy.md)
