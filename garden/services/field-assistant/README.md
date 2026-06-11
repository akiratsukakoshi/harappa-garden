# field-assistant — フィールド運営アシスタント service

区画 [field_assistant](../../plots/field_assistant/SKILL.md) の実処理。S42 新設(plot_gardener seedling 初適用)。

## コマンド

```bash
.venv/bin/python processor.py weekly [--dry-run]            # 週初めリマインド(月 08:10 種)
.venv/bin/python processor.py brief [--date D] [--dry-run]  # D-2 ブリーフ(毎朝 07:30 種)
.venv/bin/python processor.py roster --date D [--to-sheet]  # 任意日の名簿(対話 tool / 手動)
.venv/bin/python processor.py furikae [--month M] [--if-last-day] [--dry-run]
.venv/bin/python processor.py clear-sheets                  # 名簿 WB の月末掃除
.venv/bin/python processor.py sync-line-users               # 収集 userId を soil と照合 → line_users.json
.venv/bin/python processor.py weather --place 箱根 --date D  # 任意地点の天気・気温・風(16日先まで)
```

## 認証・参照(すべて read-only)

- シフトカレンダー: shift-manager の SA + config_ids.json 流用(`monthly_ui_id`)
- STORES 予約 API: `.env` の `STORES_API_TOKEN`(参照系のみの API)
- 天気: Open-Meteo(キー不要)。会場→座標 = `config/venues.json`
- 名簿スプシ: `FIELD_ROSTER_SHEET_ID`(ガクチョ所有 WB を SA に Editor 共有)
- LINE push: `LINE_CORE_TEAM_ACCESS_TOKEN` + `FIELD_LINE_TO`(garden-gaku-co とチャネル共有)

## メンションの仕組み(S42 実測の LINE 仕様)

textV2 + substitution。**userId 必須・group/room 宛のみ**(1:1 は line_push が自動でテキストにフォールバック)。
収集チェーン: グループ発話 → garden-gaku-co `line/app.py` 収集フック → `config/line_collected.json` →
`sync-line-users` が soil 運営ページの `line_display_name:` と照合 → `config/line_users.json`(全ニックネーム → userId)。

## デプロイ

```bash
rsync -avh -e ssh --exclude '.env' --exclude 'output/' --exclude '__pycache__' \
  --exclude 'config/line_users.json' --exclude 'config/line_collected.json' \
  garden/services/field-assistant/ harappa:/home/vps-harappa/garden/services/field-assistant/
```

⚠️ **`config/line_users.json` と `config/line_collected.json` は VPS が正本**(webhook 収集 + sync で育つ)。
repo からの rsync で上書きしないこと(上の exclude を必ず付ける)。`.env` は VPS のみ(600)。

## cron(vps/cron/crontab.snapshot 参照)

- `10 8 * * 1` weekly-prep-reminder / `30 7 * * *` daily-event-brief / `30 19 28-31 * *` monthly-furikae-check
