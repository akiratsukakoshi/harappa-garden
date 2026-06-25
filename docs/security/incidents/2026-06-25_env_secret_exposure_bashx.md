# 2026-06-25 `bash -x` による .env secret の AI ログ露出・ローテーション

## 概要

セッション60(測量士提案2 = master bot の AgentRunner 化)のデプロイ後、bot 再起動の不具合切り分けで Claude Code が **`bash -x ./run-bot.sh`** を実行した。run-bot.sh は内部で `set -a; . ./.env; set +a` により .env を source しており、`bash -x` のトレースが **.env の全変数を値ごと標準エラーに展開** → Claude Code のセッション出力(transcript)に複数の本番 secret が平文で露出した。

ガクチョ判断で **DISCORD_BOT_TOKEN と ANTHROPIC_API_KEY をローテーション**。LINE 系トークンは影響軽微として今回は据え置き(必要時に別途)。

## 発覚経緯

bot 再起動シーケンス(`pkill → sleep → run-bot.sh`)が exit 255 で失敗し bot がダウン。原因究明のため `bash -x ./run-bot.sh` を実行したところ、`. ./.env` のトレースで secret が出力された。実行者(Claude Code)が即座に気づき、復旧後にガクチョへ報告。

## 露出した secret(VPS `garden-gaku-co/.env`)

| 変数 | 系統 | ローテーション |
|---|---|---|
| `DISCORD_BOT_TOKEN` | master Discord bot の認証 | ✅ 実施(本インシデント) |
| `ANTHROPIC_API_KEY` | API パス(brain/provider = LINE/team の頭脳) | ✅ 実施(本インシデント) |
| `LINE_CORE_TEAM_ACCESS_TOKEN` | LINE Messaging API | ⏸️ 据え置き(ガクチョ判断・影響軽微) |
| `LINE_CORE_TEAM_CHANNEL_SECRET` | LINE webhook 署名検証 | ⏸️ 据え置き |
| `LINE_CORE_TEAM_GROUP_ID` | (ID であり secret 性は低い) | ⏸️ 据え置き |

`~/.claude/cron-secrets.env`(S59 の `CLAUDE_CODE_OAUTH_TOKEN` = setup-token)は **露出していない**(run-bot.sh は読まない)。別系統につき触らない。

## 漏洩経路

| 経路 | 露出形態 | 対応 |
|---|---|---|
| Claude Code セッション transcript | `bash -x` のトレースで `. ./.env` の全変数が平文展開 | ⏸️ transcript は事後削除不可 → secret 失効(ローテート)で無効化 |
| VPS `garden-gaku-co/.env` | 元から平文(secret の正本・600・gitignore) | 変更なし(設計どおり) |

実 secret は VPS の `.env` 1ファイルのみに存在(`.env.example` はキー名のみのテンプレート、実値なし)。repo / git には secret は入っていない。

## リスク評価

- **DISCORD_BOT_TOKEN**: 漏洩すると bot を乗っ取り、master チャンネルでの成りすまし・Garden 操作が可能。影響大 → 即ローテート。
- **ANTHROPIC_API_KEY**: 漏洩すると当該 API キーで Anthropic API を従量課金で悪用可能。影響大 → 即ローテート。
- transcript はローカル/クラウドにキャッシュされ得るため「一度出たら漏れた」前提で扱う(失効が唯一の確実な対策)。

## 対応内容

### 1. 即時復旧(完了)

- bot ダウン → `./run-bot.sh` を通常実行(`bash -x` ではなく)で再起動。PID 2799670 で online 復帰、ガクチョが Discord で応答確認済み。

### 2. ローテーション(役割分担)

新トークンを **AI セッションに貼らない**(貼ると再露出)。値を持つガクチョが portal 再発行 + .env 更新、Claude Code は再起動と検証のみ担当。

| 手順 | 担当 | 内容 |
|---|---|---|
| A. 鍵再発行 | ガクチョ | Discord Developer Portal で Reset Token / Anthropic Console で新 API Key 作成 |
| B. .env 更新 | ガクチョ(自分の端末) | `read -s` で値を受け、.env を書き換え(値は transcript に出さない)。手順は本incident末尾 |
| C. デーモン再起動 | Claude Code | bot.py / line.app(uvicorn:8011) を再起動 |
| D. 検証 | Claude Code | プロセス online・auth エラー無し・set/unset 確認(値は出さない) |
| E. 旧鍵失効 | ガクチョ | 新鍵動作確認後、Anthropic Console で旧 API Key を Delete(Discord は Reset で旧側即無効) |

再起動が必要な常駐デーモン: `bot.py`(DISCORD_BOT_TOKEN) / `line.app` uvicorn:8011(ANTHROPIC_API_KEY)。
cron 起動(`send_pending` / `morning_greet` / `night_cheer` / `log_watcher`)は次回発火で新 .env を自動取得 = 再起動不要。

#### ローテーション影響範囲の事前確認(値を出さず sha256 比較)

ANTHROPIC_API_KEY / DISCORD_BOT_TOKEN は VPS 内に同名キーを持つ .env が複数あったが、**値はすべて相違**(別アプリは別鍵)を sha256 ハッシュ比較で確認 → garden の鍵を回しても gaku-co5 / gaku-co-oc / openclaw は無傷。ローテーションは garden-gaku-co/.env に隔離。

#### 検証結果(2026-06-25 完了)

- `bot.py`: Discord Reset 後に keepalive cron が更新後 .env で再起動 → **新トークンでログイン成功**(online as Gaku-co#0661)。ログイン成功自体が新トークンである証拠(旧=Reset 済で失敗するはず)。
- `line.app`: `run-line-container.sh` で `docker rm -f` → `docker run --env-file .env` し**新 .env でコンテナ再作成**。health `status:ok`。
- **新 ANTHROPIC_API_KEY の実 API 疎通**: コンテナ内で `AnthropicProvider().chat(max_tokens=5)` を実行 → **WORKS**(新キーが実際に通ることを旧キー削除前に確認)。
- 重複プロセスなし(line.app 1 / コンテナ 1 / bot 1)。
- 残: ガクチョが Anthropic Console で旧 API Key を Delete(新キー稼働確認済につき安全) / `.env.bak-rotate-20260625` は様子見後 shred。

### 3. 再発防止

- **`bash -x` を .env / secret を source するスクリプトに使わない**。デバッグは `set -x` 範囲を絞るか、source 行を除いた部分のみトレースする。
- 既存ルール([docs/security/README.md](../README.md) §1.4 = 値が出る確認構文の禁止)に **「`bash -x` で secret を source するスクリプトをトレースしない」を追記**(本インシデントで明文化)。
- 切り分けは「プロセスが起動するか/ログに何が出るか」を `tail`・`pgrep` で見るに留め、起動スクリプト自体のトレースは secret を含まないと確認できる場合に限る。

## .env セキュア更新手順(ガクチョが自分の端末で実行)

値を transcript に出さないため、ガクチョの **自分のターミナル**(この AI セッションの外)で実行する:

```bash
ssh harappa
cd /home/vps-harappa/garden/services/garden-gaku-co
cp .env .env.bak-rotate-20260625          # バックアップ
read -rs -p "new DISCORD_BOT_TOKEN: " D; echo
read -rs -p "new ANTHROPIC_API_KEY: " A; echo
python3 - "$D" "$A" <<'PY'
import sys, pathlib
d, a = sys.argv[1], sys.argv[2]
p = pathlib.Path(".env"); lines = p.read_text().splitlines(); out = []
for ln in lines:
    if ln.startswith("DISCORD_BOT_TOKEN="):   out.append("DISCORD_BOT_TOKEN=" + d)
    elif ln.startswith("ANTHROPIC_API_KEY="): out.append("ANTHROPIC_API_KEY=" + a)
    else: out.append(ln)
p.write_text("\n".join(out) + "\n")
print("rewrote", sum(ln.startswith(("DISCORD_BOT_TOKEN=","ANTHROPIC_API_KEY=")) for ln in out), "keys")
PY
unset D A
```

完了をガクチョが Claude Code に伝えたら、Claude Code が bot.py / line.app を再起動して検証する。

## 関連

- 運用ルール本体: [`../README.md`](../README.md)
- 前例(同種の値露出副次事故あり): [`2026-05-23_gog_keyring_rotation.md`](2026-05-23_gog_keyring_rotation.md) §副次的に発生した事故
- 発端セッション: S60(測量士 2026-06-24 提案2 の実装)
