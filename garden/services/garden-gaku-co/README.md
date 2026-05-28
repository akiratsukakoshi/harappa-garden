---
type: service
status: 段3稼働(夜の一言 cron + 会話 bot オンライン、2026-05-28)
last_updated: 2026-05-28
purpose: Garden の対話層(interaction layer)。塚越さんの秘書対話(Discord master)+ 将来チーム channel。内側専用・社外ガクコとはデプロイ分離
---

# garden-gaku-co

Garden の **接客器官(interaction layer)**。種(claude -p)が苦手な「人との対話・配信・記憶」を担う。

- **内側専用**: 塚越さん(Discord master)+ 将来チーム(LINE staff/core)。**社外(Digital 原っぱ / AIBOU LAB)とはデプロイから分離**(エアギャップ)
- **真実は Garden の MD 一箇所**: `/home/vps-harappa/garden-mirror/`(mirror/writeback-daemon が両方向同期)を読み書きすることで Garden に参加。書いた変更は writeback → CouchDB → Obsidian に伝播
- **頭脳はチャネル単位**: 塚越さん(Discord master)= claude -p(サブスク・Garden ツール込み)/ チーム = gaku-co API(後の段)

設計判断: [docs/decisions/2026-05-28-garden-gaku-co-interaction-layer.md](../../../docs/decisions/2026-05-28-garden-gaku-co-interaction-layer.md)

## なぜ別サービスか(既存 gaku-co5.0 との関係)

gaku-co5.0(`/home/tukapontas/gaku-co5.0/`、別 repo)は LINE/Discord 対応の会話エージェント。塚越さんの整理では「**Garden の前段階の設計**」。本サービスはその思想を継ぎつつ、**Garden ネイティブに最小から育てる**:

- gaku-co5.0 を丸ごと写経せず、最小 bot から始める
- 3層記憶・2段階発言・承認ゲートは、チーム channel を足す段で**意図的に移植**
- 既存 gaku-co5.0 は無傷のまま運用継続 → 将来「社外ガクコ」に痩せていく

## スタック

段階で導入物が変わる:

- **段1-2(疎通 + 夜の一言)= ホストスクリプト + cron**(launcher と同じパターン)
  - Discord 送信は **REST のみ**(`send.py`、Python 標準ライブラリだけ。依存ゼロ・Docker 不要・discord.py 不要)
  - **頭脳**: VPS の `claude`(Claude Code ヘッドレス、サブスク認証)を subprocess 起動。launcher と同じ `~/.npm-global/bin/claude` フルパス。夜の一言は「テキスト入力→テキスト出力」の純生成のみ(ファイルツール不要)
- **段3(朝の対話)= discord.py の常駐 gateway**(受信して往復)。container か host systemd かは段3で決める
- **段4** で gaku-co の 3層記憶・2段階発言・承認ゲートを意図的に移植

## ロードマップ(育て方)

| 段 | 着手 | 状態 |
|---|---|---|
| **0** | 足場(README + .env.example)+ ADR | ✅ 済 |
| **1** | Discord 送信(`send.py`)+ 疎通 "hello" | ✅ 稼働(2026-05-28 疎通 OK) |
| **2** | **夜の一言**(`night_cheer.py`): archive 読み → claude -p(ペルソナ)生成 → push | ✅ 稼働(テスト送信 OK / cron 22:40 登録済) |
| **3** | **会話 bot**: master 受信 → claude -p(ペルソナ + garden-mirror 文脈 + 直近履歴)→ 返信 | ✅ 稼働 v1(オンライン・会話可。read-only。タスク更新は次段) |
| **4** | チーム channel(LINE staff/core)+ gaku-co の承認ゲート・情報境界を移植 | 未 |

## 配置と起動

### 段1-2(現状)— ホストスクリプト
```
~/garden/services/garden-gaku-co/
├── send.py             # Discord REST 送信(段1 疎通 / 段2 出口、依存ゼロ)
├── night_cheer.py      # 夜の一言: archive 読み → claude -p で生成 → send
├── run-night-cheer.sh  # cron ラッパー(.env を source して実行)
├── persona/g-gaku-co.md # 秘書の人格・トーン(塚越さんと共作)
├── .env.example
└── .env                # chmod 600、VPS 上のみ(git 除外)
```

デプロイは dev-flow 系統(b): ローカル本 repo で編集 → `scp/rsync` で VPS へ → `.env` を VPS 上で記入 → cron 登録。

- **疎通テスト**: `python3 send.py "hello"`
- **夜の一言(手動)**: `./run-night-cheer.sh`
- **cron**(JST、night-review 22:30 の後): `40 22 * * * .../run-night-cheer.sh >> .../garden/log/night-cheer.log 2>&1`

### 段3(稼働)— discord.py 常駐 gateway
```
~/garden/services/garden-gaku-co/
├── bot.py              # discord.py 常駐。on_message → claude -p → 返信
├── requirements.txt    # discord.py
├── run-bot.sh          # キープアライブ(pidfile + nohup、落ちたら起こす)
└── venv/               # python3 -m venv --without-pip + get-pip(sudo 不可のため)
```
- **常駐方式**: sudo 不可のため systemd は使わず、**cron キープアライブ**(`*/2 * * * *` + `@reboot` が `run-bot.sh`)。pidfile で二重起動防止
- **頭脳**: `claude -p --system-prompt <persona> --strict-mcp-config --model sonnet`(MCP 不使用で軽量、サブスク OAuth 利用のため `--bare` は使わない)
- **記憶**: プロセス内の直近 12 発話(再起動で消える)。永続記憶は段4 で gaku-co から移植
- **制約 v1**: read-only(タスク更新はしない)。`message_content` intent 必須(Developer Portal で ON 済)
- ログ: `garden/log/bot.log`(本体)/ `garden/log/bot-keepalive.log`(cron)

## 環境変数

[.env.example](.env.example) 参照。`DISCORD_BOT_TOKEN` は **VPS 上の .env に直接記入**(chat に貼らない / git に入れない)。

## 秘書のペルソナ(塚越さんの領分)

「対話で整理される」「ねぎらいの一言がご褒美」という体験の核は**秘書の声**にある(hmc_pilot の "Be a partner, not just a tool" の系譜)。`persona/` のトーンは塚越さんと共作する。Claude が初稿を出し、レビューで調整。

## 関連

- [ADR: garden-gaku-co interaction layer](../../../docs/decisions/2026-05-28-garden-gaku-co-interaction-layer.md)
- [writeback-daemon](../writeback-daemon/README.md) — 共有 substrate(MD → CouchDB)
- [mirror-daemon](../mirror-daemon/README.md) — 共有 substrate(CouchDB → MD)
- [launcher](../launcher/README.md) — claude -p サブスク起動の先例
- gaku-co5.0(別 repo)— 移植元・社外ガクコの母体
