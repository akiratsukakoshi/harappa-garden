#!/usr/bin/env python3
"""Garden 共有カレンダーツール — Google Calendar 読み書き(HMC manage_calendar.py から移植)。

headless 専用: token が失効して refresh も不可なら input() でブロックせず例外を投げる
(再認可は別フロー garden/services/calendar/README.md 参照)。

認証情報はスクリプトと同じディレクトリ(or 環境変数 GARDEN_CALENDAR_DIR):
  - oauth_credentials.json : OAuth クライアント(desktop 型)
  - token.json            : 認可済みトークン(refresh_token 入り、chmod 600)

利用者:
  - daily-pilot/morning-briefing 種(launcher computed_inputs から `briefing` を呼ぶ)
  - garden-gaku-co bot(朝の対話で予定参照、将来 add-event も)
"""
import os
import sys
import argparse
import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
JST = datetime.timezone(datetime.timedelta(hours=9))

BASE_DIR = os.environ.get('GARDEN_CALENDAR_DIR') or os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'oauth_credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')


def get_service():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"token not found at {TOKEN_FILE}. 再認可が必要(README 参照)")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
        else:
            raise RuntimeError(
                "token invalid and cannot refresh (no refresh_token or revoked). "
                "再認可が必要(README 参照)")
    elif creds.expiry and (creds.expiry - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)) < datetime.timedelta(minutes=10):
        # 期限間近 → 先回り更新
        try:
            creds.refresh(Request())
            _save_token(creds)
        except Exception:
            pass
    return build('calendar', 'v3', credentials=creds)


def _save_token(creds):
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(creds.to_json())


def _events_for(target_date_str=None):
    svc = get_service()
    if target_date_str:
        now = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=JST)
    else:
        now = datetime.datetime.now(JST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    res = svc.events().list(calendarId='primary', timeMin=start, timeMax=end,
                            singleEvents=True, orderBy='startTime',
                            timeZone='Asia/Tokyo').execute()
    return now.date(), res.get('items', [])


def _fmt_line(event):
    start = event['start'].get('dateTime', event['start'].get('date'))
    if 'T' in start:
        dt = datetime.datetime.fromisoformat(start).astimezone(JST)
        t = dt.strftime('%H:%M')
    else:
        t = '終日'
    return f"- {t} {event.get('summary', '(無題)')}"


def cmd_get_events(date):
    d, events = _events_for(date)
    print(f"# {d} (JST) の予定: {len(events)}件")
    for e in events:
        print(_fmt_line(e))


def cmd_briefing(date):
    """morning-briefing 種に埋め込む用。常に exit 0、失敗も1行で返す。"""
    try:
        _, events = _events_for(date)
    except Exception as e:
        print(f"- ⚠️ カレンダー取得失敗（{type(e).__name__}）")
        return
    if not events:
        print("- (予定なし)")
        return
    for e in events:
        print(_fmt_line(e))


def cmd_add_event(title, start_str, duration):
    svc = get_service()
    if len(start_str) == 5:  # HH:MM → today
        today = datetime.datetime.now(JST).date()
        start_dt = datetime.datetime.strptime(f"{today} {start_str}", "%Y-%m-%d %H:%M")
    else:
        start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M")
    end_dt = start_dt + datetime.timedelta(minutes=int(duration))
    body = {
        'summary': title,
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Tokyo'},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Tokyo'},
    }
    ev = svc.events().insert(calendarId='primary', body=body).execute()
    print(f"created: {ev.get('htmlLink')}")


def main():
    p = argparse.ArgumentParser(description='Garden Calendar CLI')
    sub = p.add_subparsers(dest='cmd', required=True)

    g = sub.add_parser('get-events', help='本日 or 指定日の予定(人間向け)')
    g.add_argument('--date', help='YYYY-MM-DD')

    b = sub.add_parser('briefing', help='種埋め込み用(常に exit 0)')
    b.add_argument('--date', help='YYYY-MM-DD')

    a = sub.add_parser('add-event', help='予定追加')
    a.add_argument('--title', required=True)
    a.add_argument('--start', required=True, help='HH:MM or "YYYY-MM-DD HH:MM"')
    a.add_argument('--duration', default=60)

    args = p.parse_args()
    if args.cmd == 'get-events':
        cmd_get_events(args.date)
    elif args.cmd == 'briefing':
        cmd_briefing(args.date)
    elif args.cmd == 'add-event':
        cmd_add_event(args.title, args.start, args.duration)


if __name__ == '__main__':
    main()
