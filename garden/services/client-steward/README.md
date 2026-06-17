# client-steward service

[client_steward 区画](../../plots/client_steward/SKILL.md)の実装。クライアント soil 台帳を Gmail/Plaud の差分で世話する。

## sweep_client.py(Mode S / Mode B の Gmail 部分)

active クライアントの `primary_domain` で Gmail を `last_synced` 以降だけ引き、**digest**(要フォロー / finance シグナル / 動いたスレッド / 登場担当者)を出す。**MVP は digest を出すだけ**(soil への自動書込なし。解釈は board → 剪定)。

```bash
PY=garden/services/client-steward/.venv/bin/python   # or repo .venv
# 1社、指定日以降
$PY sweep_client.py --client mti --since 2026-05-20
# 全 active client、watermark から差分(週次種の動き)
$PY sweep_client.py --commit-watermark
```

- `--client {slug}` 省略で全 active client(`soil/clients/{slug}/README.md` に `primary_domain` を持つもの)。
- `--since YYYY-MM-DD` 省略で watermark(`state/{slug}.json`)or `--days`(既定14)前から。
- `--commit-watermark` で今回時刻を保存(次回はそこから差分)。

## 認証(新規 secret 不要)

invoice_processor の user OAuth token を流用(`gmail.modify`=読取可)。既定 = `../invoice-processor/secrets/user_token.json`。`CLIENT_STEWARD_TOKEN` / `INVOICE_USER_TOKEN` で上書き可。

## 既知の polish(homework)

- 「ありがとうございました」等の儀礼クロージングも「要返信」に出うる(種 prompt で判断、watermark 運用で軽減)。
- Plaud(打合せ)差分は MCP 越しのため本サービス未対応 → 対話時にエージェントが MCP で引く。cron 取り込みは MCP ブリッジが homework。
- soil への自動 append + board 起草(`update_client_ledger` / `draft_client_board`)は次段。

## デプロイ(test 昇格時)

rsync → venv(google-api-python-client / google-auth)→ user_token 配置(invoice と共有)→ cron(種 `weekly-client-sweep` = 月 08:20)→ settings.json で venv python を絶対パス `:*` 許可 → bot 配線(「クライアント見て」)。
