# 2026-05-27 ADR — writeback-daemon の実装(MD → CouchDB / LiveSync E2EE 互換)

**ステータス**: Accepted(セッション14 で実装 + 動作確認、Obsidian 反映成功)

## 背景

セッション12 で mirror-daemon(CouchDB → VPS MD)を実装し、セッション13 で本番ランチャー + 種が VPS で MD を編集する経路ができた。しかし mirror-daemon は **単方向** で、VPS で claude -p が編集した MD は CouchDB に戻らず、Obsidian(PC / iPhone)に届かない。

セッション13 の vault-folder-layout ADR / garden-board-structure ADR の両方で「Phase 3a A-1 で実機検証して確定」として保留にしていた **書き戻し経路** が、セッション14 で「種の成果物が塚越さんに届かない」問題として顕在化。Phase 3a の **最後のピース** として実装した。

## 決定

### (1) アーキテクチャ: 別 daemon (writeback-daemon)、mirror-daemon は触らない

並列稼働:

```
[Obsidian] ──→ CouchDB ──→ [mirror-daemon] ──→ /mirror     (pull)
[claude -p] ──→ /mirror ──→ [writeback-daemon] ──→ CouchDB (push)
```

**理由**:
- 責務分離(読みと書きを別 daemon に)
- 既存の mirror-daemon は触らない(壊れない)
- フィードバックループは「CouchDB の現状と内容比較」で確実に防止できる

**却下した代替案**:
- (a) mirror-daemon の双方向化 — 同じプロセスで両方向の状態管理が複雑化
- (b) claude -p が CouchDB に直接 PUT — 暗号化 / chunk 計算を seed 側に埋め込むのは現実的でない

### (2) フィードバックループ防止 = 内容比較 + chunk format 検証(state 不要)

writeback の fs.watch は mirror-daemon の write も拾ってしまうため、無条件に push すると無限ループになる。

防止策(state ファイル不要、CouchDB を source of truth):

```
on fs change:
  1. content = read VPS MD
  2. existing = GET CouchDB doc by path
  3. if existing.children every starts_with("h:+"):
       cdb_content = decrypt all chunks
       if cdb_content == content: skip
  4. else (chunk format wrong):
       force re-push with correct format
  5. encrypt + push new chunk + PUT new doc rev
```

**コスト**: 1 decrypt per change(現状 MD は数 KB なので軽量)
**state 不要**: CouchDB の現状が常に正
**chunk format 検証**: 初版で誤った形式(`h:` のみで `+` なし)を push してしまった経験から追加。同様の事故からのリカバリにも有効

### (3) 単一 chunk 戦略

LiveSync は本来 doc を複数 chunk に分割するが、本 daemon は **content 全体を 1 chunk** として push する。

**理由**:
- LiveSync の読み手は `doc.children` を順に decrypt → concat するだけ(分割ロジックは LiveSync 側にしかない)
- 単一 chunk でも互換読み取り可能(mirror-daemon でも Obsidian でも検証済)
- 分割ロジック(content-defined chunking 等)を再実装する複雑さを回避

**コスト**: chunk dedup 効率は LiveSync の分割版より劣る(差分書き込みでも全 chunk が新規)。ただし MD は小さいので無視できる

### (4) LiveSync 互換 chunk ID 仕様(E2EE オン時)

```
chunkId = "h:+" + xxhash.h64(piece + "-" + hashedPassphrase + "-" + piece.length).toString(36)
```

ここで `hashedPassphrase`:

```
SALT_OF_ID = "a83hrf7fy7sa8g31"   // 17 文字、中央に ETX (U+0003)
usingLetters = Math.trunc(passphrase.length * 3 / 4)
passphraseForHash = SALT_OF_ID + passphrase.substring(0, usingLetters)
hashedPassphrase = fallbackMixedHashEach(passphraseForHash)
```

**ソース**:
- `obsidian-livesync/src/lib/src/common/models/shared.const.behabiour.ts`:
  - `SALT_OF_ID`, `PREFIX_ENCRYPTED_CHUNK = "h:+"`
- `obsidian-livesync/src/lib/src/managers/HashManager/HashManagerCore.ts`:
  - `HashEncryptedPrefix = "+"`, encryption mode は `+` prefix を追加
- `obsidian-livesync/src/lib/src/managers/HashManager/XXHashHashManager.ts`:
  - `XXHash64HashManager.computeHashWithEncryption` の式
- `obsidian-livesync/src/lib/src/managers/EntryManager/EntryManagerImpls.ts:271`:
  - `id = `${IDPrefixes.Chunk}${chunkId}`` (= `"h:"` + hash)

**E2EE オフ時**: `h:` プレフィックスのみで `+` なし、`hashedPassphrase` も使わない。本 daemon は E2EE オン環境のみサポート

**検証**: 既存 chunk `h:+22e9mmpqjhdlr` を decrypt して piece を取得、本 daemon の computeEncryptedChunkId(piece) で再計算 → **完全一致**を確認(セッション14 ログ)

### (5) doc 構造

PUT する doc:

```json
{
  "_id": "<path>",
  "_rev": "<existing rev if updating>",
  "path": "<path>",
  "type": "plain",
  "mtime": <ms since epoch>,
  "ctime": <ms since epoch, preserve existing or stat.ctimeMs>,
  "size": <byte length, Buffer.byteLength(content, "utf8")>,
  "children": ["h:+<hash>"],
  "eden": {}
}
```

chunk doc:

```json
{
  "_id": "h:+<hash>",
  "data": "%=<base64-encoded HKDF+AES-GCM ciphertext>",
  "type": "leaf",
  "e_": true
}
```

**eden field**: 常に空 `{}`。本来 LiveSync の Eden 機構は小さい doc のインライン格納用らしいが、空でも動作確認済

### (6) 削除

inotify の file unlink は `rename` イベントで通知される → stat で 404 を確認して CouchDB に `_deleted: true` の PUT。

```json
{"_id": "<path>", "_rev": "<rev>", "_deleted": true}
```

### (7) 409 conflict 処理

同時編集で `_rev` が古くなった場合: **warn log 出して skip**(次の変更で再試行)。
検証フェーズの単純策。production 化時は retry ロジックを追加予定。

### (8) 暗号化ライブラリ

mirror-daemon と同じ `octagonal-wheels`(`encryption/hkdf`)を使用:
- `encrypt(input, passphrase, pbkdf2Salt)` → `%=<base64>` 文字列を返す
- HKDF + AES-GCM、PBKDF2-SHA256(310,000 iterations)
- `pbkdf2Salt` は CouchDB の `_local/obsidian_livesync_sync_parameters` から取得

xxhash + fallbackMixedHashEach も同パッケージから:
- `xxhashNew()` → `{h64, h64ToString, h32, h32ToString, ...}`
- `fallbackMixedHashEach(string)` → murmur3 + FNV-1a の混合ハッシュ文字列

## 設定 (.env)

mirror-daemon の `.env` をそのままコピー可能(同じ COUCHDB / E2EE secret を使う)。追加項目:

| 変数 | 既定値 | 用途 |
|---|---|---|
| `DEBOUNCE_MS` | `1500` | 連続書き込みのファイナル待ち(ms) |

## Docker 構成

mirror-daemon と同様、`garden-couchdb_default` external network に参加。mirror は **読み専用** マウント(`:ro`)で安全側に倒す。

## 動作確認

セッション14 にて:

| 項目 | 結果 |
|---|---|
| 初版実装(chunk ID 形式間違い、`h:` のみ) | ⚠️ Obsidian に反映されず — 原因調査の入口 |
| LiveSync ソース解析 → アルゴリズム特定 | ✅ |
| 既存 chunk `h:+22e9mmpqjhdlr` で computed_id == expected_id | ✅ アルゴリズム正確性確認 |
| 修正版実装 + chunk format アップグレード判定追加 | ✅ |
| 4 ファイル正しい形式で push(active_tasks / backlog / archive / writeback-test) | ✅ |
| **Obsidian での反映**(PC / iPhone 両方) | ✅ 塚越さん確認済 |
| ループ防止(mirror-daemon pull → fs.watch → skip 判定) | ✅ `[skip] xxx.md (no change vs CouchDB)` 出力 |

## 影響

- **Phase 3a 完成**: claude -p (種) → VPS MD → CouchDB → LiveSync → Obsidian の経路が初めて両方向に動く
- **明朝の morning-briefing が Obsidian で読める**: cron 自動発火 → backlog 抽出 → active_tasks 生成 → writeback → LiveSync → 塚越さんが iPhone で確認
- 連絡板(`garden/board/triage/*.md`)も Obsidian で見える: morning-briefing が生成した Triage 質問を塚越さんが直接編集できる(LiveSync 経由で VPS に届く + watcher daemon が resume 起動)
- **書き戻し経路に依存していた他の保留事項**(garden-board-structure ADR / vault-folder-layout ADR の「書き戻し経路は Phase 3a A-1 で実機検証して確定」)が解消

## 制約と既知の課題

1. **single chunk**: 分割なし、大ファイルでもメモリに乗る前提(MD なら問題なし)
2. **conflict skip**: 409 はリトライせず次回変更で再試行(検証フェーズ)
3. **バッドチャンク掃除未実装**: 初版で作った `h:` プレフィックスの orphan chunks が CouchDB に残置(参照されていないので動作に影響なし)
4. **削除は file unlink のみ**: mv による rename は doc の path 変更として扱えていない(将来課題)
5. **eden field**: 常に空で運用。本来用途は未調査
6. **`fs.watch` recursive**: Linux + Node 20+ 必須(本環境は Node 22)
7. **E2EE オン環境のみサポート**: オフ環境は `h:` プレフィックス + `hashedPassphrase` 不使用に分岐が要る

## 関連

- [garden/services/writeback-daemon/README.md](../../garden/services/writeback-daemon/README.md) — 運用ドキュメント
- [garden/services/writeback-daemon/writeback.mjs](../../garden/services/writeback-daemon/writeback.mjs) — 実装
- [docs/decisions/2026-05-27-mirror-daemon-implementation.md](2026-05-27-mirror-daemon-implementation.md) — 逆方向の daemon の ADR
- [docs/decisions/2026-05-25-couchdb-livesync-implementation.md](2026-05-25-couchdb-livesync-implementation.md) — LiveSync 全体
- [obsidian-livesync source](https://github.com/vrtmrz/obsidian-livesync) — chunk ID 仕様の根拠
  - `src/lib/src/common/models/shared.const.behabiour.ts`(`SALT_OF_ID`, `PREFIX_ENCRYPTED_CHUNK`)
  - `src/lib/src/managers/HashManager/HashManagerCore.ts`(`HashEncryptedPrefix`)
  - `src/lib/src/managers/HashManager/XXHashHashManager.ts`(`XXHash64HashManager`)
  - `src/lib/src/managers/EntryManager/EntryManagerImpls.ts:271`(chunk ID 組み立て)
