# Vendor Switch Kit

> LLM / agent runner / API provider の切替を、単発の移行作業ではなく
> Garden Runtime の定期点検として扱うための正本。

## 目的

Garden は Claude Code / Codex / Gemini CLI / API provider のどれか一つに固定されない。
ただし、ベンダー名を消すこと自体が目的ではない。目的は以下を満たすこと。

- 切替点が `garden/runtime/` と runner 実装に集約されている
- Claude 固有語が「意図された依存」か「未集約の依存」か判別できる
- dry-run / read-only / scratch write / seed smoke / rollback が手順化されている
- secret / token / subscription の確認が、値を出さない形で運用できる

## 現在の切替点

| 面 | 現在 | 切替場所 | 確認すること |
|---|---|---|---|
| seed runner | `claude-code` | `garden/services/launcher/launcher.mjs` | `engine` 解決、CLI 引数、MCP 引数、timeout、cwd |
| master runner | `claude-code` | `garden/services/garden-gaku-co/brain/runner.py` | `GARDEN_GAKU_CO_ENGINE`、tool policy、エラー文面 |
| LINE/team provider | `anthropic` | `garden/services/garden-gaku-co/brain/provider.py` | API key、model、tool/function calling 差分 |
| OS grants | Claude settings renderer | `garden/runtime/grants.yml` | runner ごとの権限表現に変換できるか |
| MCP | Claude CLI flags | seed `execute.mcp` / launcher runner | config、allowed tools、strict mode の翻訳 |

詳細台帳は [`engines.yml`](engines.yml) を参照。

## 切替時に見る場所

| 場所 | 用途 |
|---|---|
| [`engines.yml`](engines.yml) | active engine と登録済み engine の台帳 |
| [`grants.yml`](grants.yml) | サブプロセス型エージェントの OS 権限正本 |
| [`audit-vendor-lock.py`](audit-vendor-lock.py) | vendor 固有語の分布監査 |
| [`checklists/`](checklists/) | engine 別の切替手順 |
| `garden/services/launcher/launcher.mjs` | seed runner の実起動 |
| `garden/services/garden-gaku-co/brain/runner.py` | master Discord / 定時あいさつ runner |
| `garden/services/garden-gaku-co/brain/provider.py` | API provider |

## 標準手順

1. `engines.yml` で切替候補の状態を確認する。
2. `audit-vendor-lock.py` を実行し、未集約の vendor 依存を読む。
3. 対象 engine の checklist を実行する。
4. runner binary / API key / subscription を値を出さずに確認する。
5. dry-run で prompt / cwd / timeout / log を確認する。
6. read-only run で repo 読み取りだけを確認する。
7. scratch write で一時領域だけに書けることを確認する。
8. 低リスク seed 1 本で smoke する。
9. master bot runner を短時間だけ切り替え、未対応 engine エラーや応答を確認する。
10. 問題があれば checklist の rollback に従って active engine を戻す。

## 監査の読み方

`audit-vendor-lock.py` は Claude / Anthropic 固有語を見つけても、即エラーにはしない。
分類が重要。

| 分類 | 意味 | 例 |
|---|---|---|
| `intended` | runner / provider / renderer として意図された依存 | `ClaudeSubprocessRunner`, `AnthropicProvider` |
| `runtime-kit` | 切替正本・監査・台帳内の依存記述 | 本ファイル、`engines.yml` |
| `live-doc` | 現在地や運用を示す生きた入口文書 | `CLAUDE.md`, `garden/MAP.md` |
| `config-surface` | seed や env 名のような明示的な切替面 | `engine: claude-code` |
| `history` | session / ADR / incident / surveyor letter の履歴 | 過去ログ |
| `unclassified` | 切替時に読むべき未分類依存 | 新しいスクリプト内の直書きなど |

`unclassified` が増えたら、まず「意図された依存として集約する」か「中立語へ直す」かを決める。

## Secret 確認ルール

secret の値は出さない。確認は set/unset か length 比較のみ。

禁止:

- `echo "$TOKEN"`
- `cat .env`
- `.env` を source する script の `bash -x`

許可:

- `if [ -n "$TOKEN" ]; then echo SET; else echo UNSET; fi`
- `test ${#TOKEN} -gt 0 && echo SET`
- `wc -c <secret-file>`

詳細は [`docs/security/README.md`](../../docs/security/README.md)。

## ロール名の分離

今後の文書では、以下を分けて書く。

| 種別 | 意味 |
|---|---|
| 実装エージェント | Garden 内で実装・反映する役割 |
| 測量士 | 外部視点でレビューする役割 |
| runner / engine | `claude-code`, `codex`, `gemini-cli` などの起動基盤 |
| provider | `anthropic`, `openai` など API 常駐チャットの実装 |

同じ Codex でも、測量士として入る時は直接編集しない。実装エージェントとして入る時は、
セッション冒頭で役割を明示して通常の実装規約に従う。
