# 2026-06-25 VPS の `claude -p` 認証を長期トークン(setup-token)に切替

## 背景 — セッション59 で発生した全 cron 停止

2026-06-24 夜から、VPS の全 cron 種(launcher 経由の `claude -p`)が
`Failed to authenticate. API Error: 401 Invalid authentication credentials` で
連続失敗した。番人が 5 件のアラートを Discord master に通知。

落ちた種(すべて同一原因):
- daily-pilot/night-review(22:30 JST 6/24 — 最初の失敗)
- mycelium/index-refresh, ingest-raw, consolidate-wiki(03:00〜03:50)
- daily-pilot/recurring-spawn(06:25), morning-briefing(06:30)

派生症状: night-review が落ちたため朝の active_tasks が前日のまま →
「active_tasks の日付が今日でない」警告も発火した。

## 根本原因

VPS の Claude 認証は session9 で `claude login`(個人サブスク OAuth)で設定されていた。
この **アクセストークンが 2026-06-24 05:25 UTC に失効し、リフレッシュも 401 で拒否**された。

- `~/.claude/.credentials.json` の `expiresAt` = 2026-06-24T05:25 UTC、subscriptionType=`pro`
- 同時刻、ローカル端末は subscriptionType=`max` で新しく有効
- → 同一アカウントをローカルで再ログイン(Max 化)した際に **OAuth リフレッシュトークンが回転し、
  VPS 側セッションが無効化された**(個人サブスク `claude login` をヘッドレス cron で使う構成の弱点)

## 決定 — ヘッドレス専用の長期トークンに切替

`claude login`(対話セッションと回転衝突する)をやめ、**`claude setup-token`** で発行する
**1 年有効の長期トークン**を使う。これは headless/CI 用途向けで、ローカルの対話ログインと
回転衝突しない = 同じ失効が再発しにくい。

### 配線(secret を repo に置かない)

1. トークンは VPS の `~/.claude/cron-secrets.env`(chmod 600)に
   `CLAUDE_CODE_OAUTH_TOKEN=...` 形式で置く。**値は repo に置かない**。
2. launcher.mjs が起動時にこのファイルを読み、`process.env` に注入する
   (既存 env は上書きしない)。spawn 時 `{...process.env}` で `claude -p` に継承される。
   - 環境変数で上書き可: `GARDEN_CRON_SECRETS`
   - cron は最小 env で起動するため、この読み込みが無いとトークンが claude に届かない

```js
const CRON_SECRETS_FILE = process.env.GARDEN_CRON_SECRETS || `${process.env.HOME}/.claude/cron-secrets.env`;
try {
  for (const line of fs.readFileSync(CRON_SECRETS_FILE, 'utf8').split('\n')) {
    const m = /^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/.exec(line);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
} catch { /* ファイル不在ならスキップ */ }
```

## 復旧手順(再発時はこれを踏む)

1. VPS に SSH ログイン(`ssh harappa`)
2. `claude setup-token` を実行 → 表示 URL をブラウザで承認(Max アカウント)→ コードを貼り戻す
3. 出力された `sk-ant-oat01-...` を `~/.claude/cron-secrets.env` に
   `CLAUDE_CODE_OAUTH_TOKEN=<token>` 形式で書く(chmod 600)。**接頭辞 `CLAUDE_CODE_OAUTH_TOKEN=` を忘れない**
4. 検証: `set -a; . ~/.claude/cron-secrets.env; set +a; claude -p 'reply OK'`(値は表示しない)
5. 落ちた種を launcher 経由で手動リカバリ(`node launcher.mjs --seed <key>`)。
   ただし **night-review は実行時刻から日付を計算する**ため、当日分が未処理でも
   日中の再実行はしない(誤って当日タスクを締める)。定刻 cron に任せる。

## 副作用 / メモ

- 今回のリカバリで repo HEAD の launcher.mjs(S54 の MCP フラグ対応を含む)を VPS にデプロイ。
  VPS は古い版を動かしていた drift があり、これも併せて解消した。
- 失効した旧 credentials は `~/.claude/.credentials.json.bak-401-20260625` に退避。
- このトークンは復旧時にチャットへ露出したため、気になる場合は setup-token で再発行し、
  **ターミナルから直接** cron-secrets.env に上書きする(チャットに貼らない)こと。
- secret 取扱いは [docs/security/README.md](../security/README.md) のルールに従った
  (値は length / set-unset 判定のみで確認、`echo "$VAR"` は使わない)。
