# sns-manager service

原っぱ大学の SNS 運用(Instagram / Facebook)。HMC `apps/sns_pilot/` の transplant 移植(S45)。
区画 SKILL: [garden/plots/sns_manager/SKILL.md](../../plots/sns_manager/SKILL.md)

## コマンド

```bash
PY=/home/vps-harappa/garden/services/sns-manager/.venv/bin/python
PROC=/home/vps-harappa/garden/services/sns-manager/processor.py

# 土: Drive 候補画像を DL(その週の月曜を渡す)→ Claude が Read して選定
$PY $PROC fetch-images --week 2026-06-22

# 月: 先週の Meta Insights → Sheet 記録 + MD レポート
$PY $PROC report [--dry-run]

# 承認後: 1 投稿を IG(ig_scheduler 経由)+ FB に予約
$PY $PROC schedule --image PATH --caption-file PATH \
    --publish-at 2026-06-23T20:00:00 [--platform both|ig|fb] [--dry-run]
```

## 構成

```
sns-manager/
├── processor.py           # fetch-images / report / schedule
├── config/config.json     # 投稿カレンダー・Reels KPI 目標(HMC 継承。ID は env)
├── lib/
│   ├── utils.py           # logger(HMC modules/utils 移植)
│   ├── google_sa.py       # SA 認証(Drive read + Sheets write、expense/invoice の SA 流用)
│   ├── drive_reader.py    # ガクチョが置いた候補画像を list / download
│   ├── sheets_client.py   # KPI ログ(HMC sheets_client 移植、SA + gspread)
│   └── meta_client.py     # Meta Graph API + ig_scheduler 予約(HMC meta_client 移植)
├── requirements.txt
├── .env.example           # secret テンプレ(実値は VPS のみ)
└── secrets/               # service_account.json(.gitignore。expense/invoice の SA を流用可)
```

## 認証・secret

| secret | 用途 | 入手 |
|---|---|---|
| `META_ACCESS_TOKEN` / `META_IG_ACCOUNT_ID` / `META_PAGE_ID` | Meta Graph API(インサイト・FB 予約・IG コンテナ) | HMC `.env` から流用 |
| `IG_SCHEDULER_API_URL` / `IG_SCHEDULER_API_KEY` | IG 投稿予約(VPS の ig_scheduler コンテナ共用) | HMC `.env` から流用 |
| `GOOGLE_SA_FILE`(or `secrets/service_account.json`) | Drive read(候補画像)+ Sheets write(KPI) | expense/invoice の `harappa-drive-bot` SA を流用 |
| `SNS_DRIVE_FOLDER_ID` | ガクチョが候補画像を置くフォルダ | **`1H2d9o2czgYONCCJlQLXs51QZ35RXlJdv`(ガクチョ作成・SA 共有済 S45)** |
| `SNS_SHEET_ID` | KPI ログのスプレッドシート | **HMC 既存を流用(ガクチョ決定 S45)= `1NWU7FYGsMol18aHkrvpVzEB7dxIk2YvyTlb4eUD-Ycg`** → Garden SA に Editor 共有が必要 |

> Drive は read のみ・Sheets は append のみなので SA で完結(invoice の user OAuth と違い storage quota 問題なし)。

## 投稿予約の経路(ig_scheduler)

Meta の `scheduled_publish_time` は Tech Provider 限定で動かないため、IG 写真投稿は VPS の
`ig_scheduler`(`ig-api.harappa.monster`)へ画像バイナリ + caption + publish_at を送り、サーバーが
自前ホスティングして Meta に配信する(HMC と同一サーバーを共用)。FB はバイナリ直接予約。

## MVP の範囲

火・土のフィード写真 2 本。木の Reels(動画)は当面ガクチョ手動 or 次フェーズ。
LINE@ 配信は HMC でも未実装(対象外)。
