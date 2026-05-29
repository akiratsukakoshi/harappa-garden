---
type: service
status: 稼働(2026-05-29 移植・morning-briefing 連携)
last_updated: 2026-05-29
purpose: Garden 共有カレンダーツール。Google Calendar の読み(将来書き)を内側サービスに提供する
---

# calendar — Garden 共有カレンダーツール

HMC(`harappa-cockpit`)の `hmc_pilot/scripts/manage_calendar.py` を Garden に移植した、Google Calendar 読み書きの最小 CLI。**MCP を立てずに**カレンダー連携を実現する(MAP 宿題「Google Calendar MCP の VPS 認証」をこの移植で解決)。

## 利用者

- **daily-pilot/morning-briefing 種**: launcher の `computed_inputs` で `briefing` を事前取得し、prompt に注入 → active_tasks の `## スケジュール` に転記(claude には credential を渡さない)
- **garden-gaku-co bot**(予定): 朝の対話で予定を参照し、手持ちタスクと突き合わせて時間割を整理。将来 `add-event` で予定書き込みも

## 使い方

```
python3 calendar_cli.py briefing [--date YYYY-MM-DD]   # 種埋め込み用。1行/予定、常に exit 0
python3 calendar_cli.py get-events [--date YYYY-MM-DD]  # 人間向け
python3 calendar_cli.py add-event --title T --start "YYYY-MM-DD HH:MM" [--duration 60]
```

`briefing` は失敗しても `- ⚠️ カレンダー取得失敗（…）` を1行返して exit 0(種が落ちない)。

## 認証(重要)

- OAuth は **HMC と同じクライアント/アカウントを共有**(ガクチョ承認済)。`oauth_credentials.json`(desktop 型)+ `token.json`(refresh_token 入り)の2ファイル。
- **scope**: `https://www.googleapis.com/auth/calendar`(読み書きフル)
- 認証情報は **VPS 上のみ・chmod 600・git 除外**(`.gitignore`)。リポジトリには絶対に入れない。
- 配置: `~/garden/services/calendar/{oauth_credentials.json, token.json}`(= スクリプトと同ディレクトリ。`GARDEN_CALENDAR_DIR` で上書き可)
- token は HMC 本番(Published)化後に再同意して発行したクリーンな refresh_token。Production なので無期限の想定。

### 再認可が必要になったら(token 失効時)

`briefing` が `⚠️ カレンダー取得失敗` を返し続ける場合、refresh_token が失効している。ローカル(google ライブラリのある環境)で InstalledAppFlow を回し、`redirect_uri=http://localhost` + コード貼り付けで新しい `token.json` を発行 → VPS に scp し直す(2026-05-29 の初回移植と同手順)。

## ランタイム

- Python は **garden-gaku-co の venv を共用**(`~/garden/services/garden-gaku-co/venv/bin/python3`)。両者とも内側サービスで、bot も対話でカレンダーを使うため。
- 依存: `requirements.txt`(google-auth / google-auth-oauthlib / google-api-python-client)

## 関連

- 移植元: `harappa-cockpit/.agent/skills/hmc_pilot/scripts/manage_calendar.py`
- 連携先: [daily-pilot/morning-briefing](../../seeds/daily-pilot/morning-briefing.md)、[garden-gaku-co](../garden-gaku-co/README.md)
- セキュリティ運用: [docs/security/README.md](../../../docs/security/README.md)
