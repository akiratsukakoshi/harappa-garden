---
type: service
status: test
last_updated: 2026-06-27
purpose: core_team LINE の会議調整、Zoom URL 発行、Google Calendar 登録を担う。
---

# meeting-coordinator

`meeting_coordinator` 区画の実処理サービス。

## コマンド

```bash
/home/vps-harappa/garden/services/garden-gaku-co/venv/bin/python processor.py monthly-ops --dry-run
/home/vps-harappa/garden/services/garden-gaku-co/venv/bin/python processor.py spot --title "会議名" --participants "少佐,ゆーじさん" --month 2026-07 --dry-run
/home/vps-harappa/garden/services/garden-gaku-co/venv/bin/python processor.py availability --meeting-id <id> --participant "少佐" --text "AとCならOK"
/home/vps-harappa/garden/services/garden-gaku-co/venv/bin/python processor.py confirm --meeting-id <id> --candidate-id A --dry-run
/home/vps-harappa/garden/services/garden-gaku-co/venv/bin/python processor.py list
```

VPS では当面、既存の `garden-gaku-co/venv` を共有する。将来、複数区画で Google / LINE / Zoom 系依存が増えたら Garden 共通 runtime venv へ切り出す。

## secret / env

値は `.env` に置き、repo には入れない。

```bash
LINE_CORE_TEAM_ACCESS_TOKEN=
MEETING_LINE_TO=              # 未設定なら FIELD_LINE_TO / LINE_CORE_TEAM_GROUP_ID を使う

ZOOM_ACCOUNT_ID=
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=
ZOOM_USER_ID=me

GARDEN_CALENDAR_DIR=/home/vps-harappa/garden/services/calendar
```

Google Calendar の OAuth token は `garden/services/calendar/` の既存 token を使う。

## 状態

`state/meetings.json` に調整中・確定済みの会議を保存する。secret は入れない。
