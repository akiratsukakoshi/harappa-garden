#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meeting_coordinator — LINE会議調整 / Zoom発行 / Google Calendar登録。

MVP:
  monthly-ops   月次運営会議の候補抽出 → state保存 → LINE push
  spot          スポット会議の候補抽出 → state保存 → LINE push
  availability 参加者返信を state に記録
  confirm       候補を確定し、Zoom URL 発行 + Calendar 招待 + LINE 確定通知
  list          state 一覧
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

JST = dt.timezone(dt.timedelta(hours=9))
HERE = Path(__file__).resolve().parent
STATE_PATH = Path(os.environ.get("MEETING_COORDINATOR_STATE", HERE / "state" / "meetings.json"))

DEFAULT_PARTICIPANTS = {
    "akira-tsukakoshi": {
        "name": "ガクチョ",
        "email": "tukapontas@gmail.com",
        "aliases": ["ガクチョ", "ガクチョー", "塚越", "塚越さん"],
    },
    "shotaro-shimura": {
        "name": "少佐",
        "email": "shotaroshimura@icloud.com",
        "aliases": ["少佐", "正太郎さん", "志村", "志村さん"],
    },
    "yuji-wada": {
        "name": "ゆーじさん",
        "email": "yujiwada0920@gmail.com",
        "aliases": ["ゆーじさん", "ユージさん", "ゆーじ", "和田", "和田さん"],
    },
    "kei-suzuki": {
        "name": "慶ちゃん",
        "email": "kei.suzuki.2019@globis.ac.jp",
        "aliases": ["慶ちゃん", "けいちゃん", "けーちゃん", "鈴木慶", "鈴木さん"],
    },
}


def _load_env() -> None:
    path = HERE / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()


def today_jst() -> dt.date:
    return dt.datetime.now(JST).date()


def _load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"meetings": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _now_iso() -> str:
    return dt.datetime.now(JST).isoformat(timespec="seconds")


def _parse_month(value: str | None, *, base: dt.date | None = None) -> tuple[int, int]:
    base = base or today_jst()
    if not value or value in ("今月", "this-month"):
        return base.year, base.month
    if value in ("来月", "next-month"):
        first_next = (base.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        return first_next.year, first_next.month
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", value.strip())
    if not m:
        raise ValueError("--month は YYYY-MM / 今月 / 来月 のいずれかで指定してください")
    return int(m.group(1)), int(m.group(2))


def _participant_registry() -> dict[str, dict[str, Any]]:
    """soil が読める環境では email/nickname を補完。失敗時は既定値だけ使う。"""
    reg = json.loads(json.dumps(DEFAULT_PARTICIPANTS))
    soil_dir = Path(os.environ.get(
        "SOIL_STAFF_DIR",
        "/home/vps-harappa/garden-mirror/garden/soil/people/staff",
    ))
    if not soil_dir.exists():
        local = HERE.parents[2] / "soil" / "people" / "staff"
        soil_dir = local if local.exists() else soil_dir
    if not soil_dir.exists():
        return reg
    for path in soil_dir.glob("*.md"):
        if path.name.startswith(("_", "README")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        fm = parts[1]
        slug = path.stem
        if slug not in reg:
            continue
        emails = re.findall(r"^\s*-\s*([^@\s]+@[^@\s]+)\s*$", fm, re.M)
        if emails:
            reg[slug]["email"] = emails[0]
        nick_block = re.search(r"nicknames:\n((?:\s*-\s*.+\n)+)", fm)
        if nick_block:
            aliases = [n.strip() for n in re.findall(r"-\s*(.+)", nick_block.group(1))]
            reg[slug]["aliases"] = sorted(set(reg[slug]["aliases"] + aliases))
    return reg


def resolve_participants(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        raw_names = [p.strip() for p in re.split(r"[,、\s]+", value) if p.strip()]
    else:
        raw_names = [str(p).strip() for p in value if str(p).strip()]
    reg = _participant_registry()
    resolved = []
    for raw in raw_names:
        hit = None
        for slug, info in reg.items():
            if raw == slug or raw == info["name"] or raw in info.get("aliases", []):
                hit = slug
                break
        if hit is None:
            raise ValueError(f"参加者を解決できません: {raw}")
        if hit not in resolved:
            resolved.append(hit)
    return resolved


def _calendar_module():
    cal_dir = Path(os.environ.get("GARDEN_CALENDAR_DIR", ""))
    if not cal_dir:
        cal_dir = HERE.parents[1] / "calendar"
    if str(cal_dir) not in sys.path:
        sys.path.insert(0, str(cal_dir))
    import calendar_cli  # type: ignore
    return calendar_cli


def _calendar_service():
    return _calendar_module().get_service()


def _date_range_5_to_9(year: int, month: int) -> list[dt.date]:
    days = []
    for day in range(5, 10):
        d = dt.date(year, month, day)
        if d.weekday() < 5:
            days.append(d)
    return days


def _candidate_windows(day: dt.date) -> list[tuple[dt.datetime, dt.datetime, str]]:
    windows = [
        (dt.time(9, 0), dt.time(12, 0), "午前"),
        (dt.time(13, 0), dt.time(17, 0), "午後"),
        (dt.time(19, 0), dt.time(21, 30), "夜"),
    ]
    return [
        (
            dt.datetime.combine(day, start, tzinfo=JST),
            dt.datetime.combine(day, end, tzinfo=JST),
            label,
        )
        for start, end, label in windows
    ]


def _busy_events(start: dt.datetime, end: dt.datetime) -> list[tuple[dt.datetime, dt.datetime]]:
    svc = _calendar_service()
    res = svc.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        timeZone="Asia/Tokyo",
    ).execute()
    busy = []
    for ev in res.get("items", []):
        s = ev.get("start", {}).get("dateTime")
        e = ev.get("end", {}).get("dateTime")
        if not s or not e:
            # 終日予定はその日全体を busy とみなす
            d = ev.get("start", {}).get("date")
            if d:
                day = dt.date.fromisoformat(d)
                busy.append((
                    dt.datetime.combine(day, dt.time(0, 0), tzinfo=JST),
                    dt.datetime.combine(day, dt.time(23, 59), tzinfo=JST),
                ))
            continue
        busy.append((dt.datetime.fromisoformat(s).astimezone(JST),
                     dt.datetime.fromisoformat(e).astimezone(JST)))
    return busy


def _subtract_busy(start: dt.datetime, end: dt.datetime, busy: list[tuple[dt.datetime, dt.datetime]]):
    free = [(start, end)]
    for bs, be in sorted(busy):
        next_free = []
        for fs, fe in free:
            if be <= fs or bs >= fe:
                next_free.append((fs, fe))
                continue
            if fs < bs:
                next_free.append((fs, bs))
            if be < fe:
                next_free.append((be, fe))
        free = next_free
    return free


def find_candidates(year: int, month: int, duration_min: int, limit: int = 6) -> list[dict[str, Any]]:
    """毎月5〜9日の平日から、午前→午後→夜の順に空き候補を返す。"""
    dates = _date_range_5_to_9(year, month)
    if not dates:
        return []
    range_start = dt.datetime.combine(min(dates), dt.time(0, 0), tzinfo=JST)
    range_end = dt.datetime.combine(max(dates), dt.time(23, 59), tzinfo=JST)
    busy = _busy_events(range_start, range_end)
    candidates = []
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for window_start, window_end, label in [w for d in dates for w in _candidate_windows(d)]:
        for free_start, free_end in _subtract_busy(window_start, window_end, busy):
            if (free_end - free_start) >= dt.timedelta(minutes=duration_min):
                start = free_start
                end = start + dt.timedelta(minutes=duration_min)
                candidates.append({
                    "id": labels[len(candidates)],
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "label": label,
                })
                break
        if len(candidates) >= limit:
            return candidates
    return candidates


def _meeting_id(prefix: str, title: str) -> str:
    stamp = dt.datetime.now(JST).strftime("%Y%m%d%H%M%S")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()[:24] or "meeting"
    return f"{prefix}-{stamp}-{slug}"


def _candidate_line(c: dict[str, Any]) -> str:
    start = dt.datetime.fromisoformat(c["start"]).astimezone(JST)
    end = dt.datetime.fromisoformat(c["end"]).astimezone(JST)
    dow = "月火水木金土日"[start.weekday()]
    return f"{c['id']}. {start.month}/{start.day}({dow}) {start.strftime('%H:%M')}-{end.strftime('%H:%M')}（{c['label']}）"


def _participants_line(slugs: list[str]) -> str:
    reg = _participant_registry()
    return "、".join(reg.get(s, {}).get("name", s) for s in slugs)


def _mention_targets(slugs: list[str]) -> str:
    reg = _participant_registry()
    names = [reg.get(s, {}).get("name", s) for s in slugs if s != "akira-tsukakoshi"]
    return " ".join(f"@{name}" for name in names)


def _open_existing(meeting_type: str, year_month: str | None = None) -> dict[str, Any] | None:
    state = _load_state()
    for m in state.get("meetings", {}).values():
        if m.get("meeting_type") != meeting_type:
            continue
        if year_month and m.get("year_month") != year_month:
            continue
        if m.get("status") in ("open", "confirmed"):
            return m
    return None


def create_meeting(
    *,
    title: str,
    meeting_type: str,
    participants: list[str],
    year: int,
    month: int,
    duration_min: int,
    proposer: str,
    confirmer: str,
    related_workflows: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    candidates = find_candidates(year, month, duration_min)
    if not candidates:
        raise RuntimeError("候補時間が見つかりませんでした")
    meeting = {
        "id": _meeting_id(meeting_type, title),
        "status": "open",
        "title": title,
        "meeting_type": meeting_type,
        "year_month": f"{year:04d}-{month:02d}",
        "duration_min": duration_min,
        "participants": participants,
        "proposer": proposer,
        "confirmer": confirmer,
        "related_workflows": related_workflows,
        "candidates": candidates,
        "availability": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    if not dry_run:
        state = _load_state()
        state.setdefault("meetings", {})[meeting["id"]] = meeting
        _save_state(state)
    return meeting


def create_custom_meeting(
    *,
    title: str,
    meeting_type: str,
    participants: list[str],
    starts: list[str],
    duration_min: int,
    proposer: str,
    confirmer: str,
    related_workflows: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    """指定済み候補だけで会議stateを作る。イレギュラー調整用。"""
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    candidates = []
    for idx, start_text in enumerate(starts):
        start = dt.datetime.strptime(start_text, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
        end = start + dt.timedelta(minutes=duration_min)
        hour_label = "午前" if start.hour < 12 else "午後" if start.hour < 18 else "夜"
        candidates.append({
            "id": labels[idx],
            "start": start.isoformat(),
            "end": end.isoformat(),
            "label": hour_label,
        })
    if not candidates:
        raise ValueError("候補日時を1つ以上指定してください")
    year_month = dt.datetime.fromisoformat(candidates[0]["start"]).strftime("%Y-%m")
    meeting = {
        "id": _meeting_id(meeting_type, title),
        "status": "open",
        "title": title,
        "meeting_type": meeting_type,
        "year_month": year_month,
        "duration_min": duration_min,
        "participants": participants,
        "proposer": proposer,
        "confirmer": confirmer,
        "related_workflows": related_workflows,
        "candidates": candidates,
        "availability": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "note": "custom candidates",
    }
    if not dry_run:
        state = _load_state()
        state.setdefault("meetings", {})[meeting["id"]] = meeting
        _save_state(state)
    return meeting


def render_request(meeting: dict[str, Any]) -> str:
    lines = [
        f"📅 {meeting['title']} の日程調整です",
        _mention_targets(meeting["participants"]),
        f"参加: {_participants_line(meeting['participants'])}",
        f"候補: {meeting['year_month']} / {meeting['duration_min']}分",
        "",
        "都合のよい候補を A/B/C で返信してください。",
    ]
    for c in meeting["candidates"]:
        lines.append(_candidate_line(c))
    lines.extend([
        "",
        "返信例:",
        "・少佐/ゆーじさん: AならOK、Bは難しい",
        "・ガクチョ確定: 運営会議 Aで確定",
    ])
    return "\n".join(lines)


def _line_push(text: str, to: str | None = None) -> list[str]:
    token = os.environ.get("LINE_CORE_TEAM_ACCESS_TOKEN", "")
    targets = [t.strip() for t in (
        to or os.environ.get("MEETING_LINE_TO")
        or os.environ.get("FIELD_LINE_TO")
        or os.environ.get("LINE_CORE_TEAM_GROUP_ID", "")
    ).split(",") if t.strip()]
    if not token:
        raise SystemExit("LINE_CORE_TEAM_ACCESS_TOKEN が未設定")
    if not targets:
        raise SystemExit("MEETING_LINE_TO / FIELD_LINE_TO / LINE_CORE_TEAM_GROUP_ID が未設定")
    for target in targets:
        message = _line_message(text[:4800], mention_enabled=target.startswith(("C", "R")))
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps({"to": target, "messages": [message]}, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise SystemExit(f"LINE push failed HTTP {e.code}: {body}")
    return targets


def _line_user_map() -> dict[str, str]:
    paths = [
        Path(os.environ.get("MEETING_LINE_USERS_PATH", "")),
        HERE.parent / "field-assistant" / "config" / "line_users.json",
        Path("/home/vps-harappa/garden/services/field-assistant/config/line_users.json"),
    ]
    for path in paths:
        if not str(path):
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def _line_message(text: str, *, mention_enabled: bool) -> dict[str, Any]:
    if not mention_enabled:
        return {"type": "text", "text": text}
    users = _line_user_map()
    if not users:
        return {"type": "text", "text": text}
    substitution = {}
    counter = 0

    def repl(match):
        nonlocal counter
        name = match.group(1)
        uid = users.get(name)
        if not uid:
            return match.group(0)
        counter += 1
        key = f"m{counter}"
        substitution[key] = {
            "type": "mention",
            "mentionee": {"type": "user", "userId": uid},
        }
        return "{" + key + "}"

    names = sorted(users.keys(), key=len, reverse=True)
    pattern = "@(" + "|".join(re.escape(n) for n in names) + ")"
    converted = re.sub(pattern, repl, text)
    if not substitution:
        return {"type": "text", "text": text}
    return {"type": "textV2", "text": converted, "substitution": substitution}


def _zoom_token() -> str:
    account_id = os.environ.get("ZOOM_ACCOUNT_ID", "")
    client_id = os.environ.get("ZOOM_CLIENT_ID", "")
    client_secret = os.environ.get("ZOOM_CLIENT_SECRET", "")
    if not (account_id and client_id and client_secret):
        raise RuntimeError("Zoom env が未設定です(ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET)")
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    url = "https://zoom.us/oauth/token?" + urllib.parse.urlencode({
        "grant_type": "account_credentials",
        "account_id": account_id,
    })
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def _create_zoom_meeting(title: str, start: dt.datetime, duration_min: int) -> dict[str, str]:
    token = _zoom_token()
    user_id = urllib.parse.quote(os.environ.get("ZOOM_USER_ID", "me"), safe="")
    body = {
        "topic": title,
        "type": 2,
        "start_time": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "timezone": "Asia/Tokyo",
        "duration": duration_min,
        "settings": {
            "join_before_host": False,
            "waiting_room": True,
        },
    }
    req = urllib.request.Request(
        f"https://api.zoom.us/v2/users/{user_id}/meetings",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return {"id": str(data.get("id", "")), "join_url": data.get("join_url", "")}


def _create_calendar_event(meeting: dict[str, Any], candidate: dict[str, Any], zoom_url: str) -> dict[str, str]:
    svc = _calendar_service()
    start = dt.datetime.fromisoformat(candidate["start"]).astimezone(JST)
    end = dt.datetime.fromisoformat(candidate["end"]).astimezone(JST)
    reg = _participant_registry()
    attendees = [
        {"email": reg[p]["email"], "displayName": reg[p]["name"]}
        for p in meeting["participants"]
        if reg.get(p, {}).get("email")
    ]
    body = {
        "summary": meeting["title"],
        "description": (
            f"Zoom: {zoom_url}\n\n"
            f"meeting_id: {meeting['id']}\n"
            f"meeting_type: {meeting['meeting_type']}\n"
            f"related_workflows: {', '.join(meeting.get('related_workflows', []))}"
        ),
        "location": zoom_url,
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Tokyo"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Tokyo"},
        "attendees": attendees,
    }
    ev = svc.events().insert(calendarId="primary", body=body, sendUpdates="all").execute()
    return {"id": ev.get("id", ""), "htmlLink": ev.get("htmlLink", "")}


def _get_meeting(meeting_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _load_state()
    meeting = state.get("meetings", {}).get(meeting_id)
    if not meeting:
        raise KeyError(f"meeting not found: {meeting_id}")
    return state, meeting


def resolve_meeting_id(meeting_id: str | None = None, meeting_type: str | None = None) -> str:
    """meeting_id 省略時に、最新の open meeting を解決する。LINE自然文用。"""
    if meeting_id:
        return meeting_id
    state = _load_state()
    meetings = [
        m for m in state.get("meetings", {}).values()
        if m.get("status") == "open" and (not meeting_type or m.get("meeting_type") == meeting_type)
    ]
    if not meetings:
        raise KeyError("open meeting が見つかりません")
    meetings.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return meetings[0]["id"]


def add_availability(meeting_id: str, participant: str, text: str) -> dict[str, Any]:
    slugs = resolve_participants(participant)
    if len(slugs) != 1:
        raise ValueError("availability の participant は1名で指定してください")
    state, meeting = _get_meeting(meeting_id)
    entry = {"participant": slugs[0], "text": text, "recorded_at": _now_iso()}
    meeting.setdefault("availability", []).append(entry)
    meeting["updated_at"] = _now_iso()
    _save_state(state)
    return entry


def confirm_meeting(meeting_id: str | None, candidate_id: str, *, dry_run: bool = False, meeting_type: str | None = None) -> str:
    meeting_id = resolve_meeting_id(meeting_id, meeting_type=meeting_type)
    state, meeting = _get_meeting(meeting_id)
    candidate = next((c for c in meeting["candidates"] if c["id"] == candidate_id), None)
    if not candidate:
        raise ValueError(f"候補 {candidate_id} が見つかりません")
    start = dt.datetime.fromisoformat(candidate["start"]).astimezone(JST)
    if dry_run:
        zoom = {"id": "dry-run", "join_url": "https://zoom.us/j/dry-run"}
        cal = {"id": "dry-run", "htmlLink": "https://calendar.google.com/dry-run"}
    else:
        zoom = _create_zoom_meeting(meeting["title"], start, int(meeting["duration_min"]))
        cal = _create_calendar_event(meeting, candidate, zoom["join_url"])
        meeting["status"] = "confirmed"
        meeting["confirmed_candidate_id"] = candidate_id
        meeting["zoom"] = zoom
        meeting["calendar"] = cal
        meeting["confirmed_at"] = _now_iso()
        meeting["updated_at"] = _now_iso()
        _save_state(state)
    line = "\n".join([
        f"✅ {meeting['title']} を確定しました",
        _candidate_line(candidate),
        f"Zoom: {zoom['join_url']}",
    ])
    if not dry_run:
        _line_push(line)
    return line


def cmd_monthly_ops(args) -> int:
    base = dt.date.fromisoformat(args.today) if args.today else today_jst()
    if args.month:
        year, month = _parse_month(args.month, base=base)
    elif base.day > 9:
        year, month = _parse_month("来月", base=base)
    else:
        year, month = _parse_month(None, base=base)
    ym = f"{year:04d}-{month:02d}"
    existing = _open_existing("operations_monthly", ym)
    if existing:
        print(f"[meeting-coordinator] existing {existing['status']}: {existing['id']}")
        print(render_request(existing))
        return 0
    meeting = create_meeting(
        title=f"{year}年{month}月 運営会議",
        meeting_type="operations_monthly",
        participants=["akira-tsukakoshi", "shotaro-shimura", "yuji-wada"],
        year=year,
        month=month,
        duration_min=int(args.duration),
        proposer="akira-tsukakoshi",
        confirmer="akira-tsukakoshi",
        related_workflows=["monthly-cycle"],
        dry_run=args.dry_run,
    )
    text = render_request(meeting)
    if args.dry_run:
        print("---- dry-run(push/state保存せず表示)----")
        print(text)
    else:
        targets = _line_push(text)
        print(f"[meeting-coordinator] pushed to {len(targets)} target(s): {meeting['id']}")
    return 0


def cmd_spot(args) -> int:
    year, month = _parse_month(args.month)
    participants = resolve_participants(args.participants)
    if "akira-tsukakoshi" not in participants:
        participants.insert(0, "akira-tsukakoshi")
    meeting = create_meeting(
        title=args.title,
        meeting_type="spot",
        participants=participants,
        year=year,
        month=month,
        duration_min=int(args.duration),
        proposer=args.proposer,
        confirmer=args.confirmer or args.proposer,
        related_workflows=[],
        dry_run=args.dry_run,
    )
    text = render_request(meeting)
    if args.dry_run:
        print("---- dry-run(push/state保存せず表示)----")
        print(text)
    else:
        targets = _line_push(text)
        print(f"[meeting-coordinator] pushed to {len(targets)} target(s): {meeting['id']}")
    return 0


def cmd_custom(args) -> int:
    participants = resolve_participants(args.participants)
    meeting = create_custom_meeting(
        title=args.title,
        meeting_type=args.meeting_type,
        participants=participants,
        starts=args.start,
        duration_min=int(args.duration),
        proposer=args.proposer,
        confirmer=args.confirmer or args.proposer,
        related_workflows=args.workflow or [],
        dry_run=args.dry_run,
    )
    text = render_request(meeting)
    if args.dry_run:
        print("---- dry-run(push/state保存せず表示)----")
        print(text)
    elif args.no_push:
        print("---- state保存のみ(LINE pushなし)----")
        print(text)
    else:
        targets = _line_push(text)
        print(f"[meeting-coordinator] pushed to {len(targets)} target(s): {meeting['id']}")
    return 0


def cmd_availability(args) -> int:
    entry = add_availability(args.meeting_id, args.participant, args.text)
    print(f"recorded: {entry['participant']} / {entry['text']}")
    return 0


def cmd_confirm(args) -> int:
    print(confirm_meeting(args.meeting_id, args.candidate_id, dry_run=args.dry_run, meeting_type=args.meeting_type))
    return 0


def cmd_list(args) -> int:
    state = _load_state()
    meetings = list(state.get("meetings", {}).values())
    if not meetings:
        print("(meeting state empty)")
        return 0
    for m in sorted(meetings, key=lambda x: x.get("created_at", "")):
        print(f"{m['id']} [{m['status']}] {m['title']} / {m['year_month']}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="meeting_coordinator processor")
    sub = p.add_subparsers(dest="cmd", required=True)

    mo = sub.add_parser("monthly-ops", help="月次運営会議の候補を作る")
    mo.add_argument("--today", help="基準日 YYYY-MM-DD")
    mo.add_argument("--month", help="対象月 YYYY-MM / 今月 / 来月")
    mo.add_argument("--duration", default=90, help="会議時間(分)")
    mo.add_argument("--dry-run", action="store_true")
    mo.set_defaults(fn=cmd_monthly_ops)

    sp = sub.add_parser("spot", help="スポット会議の候補を作る")
    sp.add_argument("--title", required=True)
    sp.add_argument("--participants", required=True, help="参加者名をカンマ区切りで指定")
    sp.add_argument("--month", default="今月", help="対象月 YYYY-MM / 今月 / 来月")
    sp.add_argument("--duration", default=90, help="会議時間(分)")
    sp.add_argument("--proposer", default="akira-tsukakoshi")
    sp.add_argument("--confirmer")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(fn=cmd_spot)

    cu = sub.add_parser("custom", help="指定候補だけで会議調整stateを作る")
    cu.add_argument("--title", required=True)
    cu.add_argument("--participants", required=True, help="参加者名をカンマ区切りで指定")
    cu.add_argument("--start", action="append", required=True, help='候補開始 "YYYY-MM-DD HH:MM"。複数指定可')
    cu.add_argument("--duration", default=90, help="会議時間(分)")
    cu.add_argument("--meeting-type", default="spot")
    cu.add_argument("--workflow", action="append", help="related_workflows。複数指定可")
    cu.add_argument("--proposer", default="akira-tsukakoshi")
    cu.add_argument("--confirmer")
    cu.add_argument("--dry-run", action="store_true")
    cu.add_argument("--no-push", action="store_true", help="state保存のみでLINEへ送らない")
    cu.set_defaults(fn=cmd_custom)

    av = sub.add_parser("availability", help="参加者返信を記録")
    av.add_argument("--meeting-id", required=True)
    av.add_argument("--participant", required=True)
    av.add_argument("--text", required=True)
    av.set_defaults(fn=cmd_availability)

    cf = sub.add_parser("confirm", help="候補を確定し Zoom + Calendar + LINE 通知")
    cf.add_argument("--meeting-id")
    cf.add_argument("--candidate-id", required=True)
    cf.add_argument("--meeting-type", help="meeting_id 省略時に絞り込む meeting_type")
    cf.add_argument("--dry-run", action="store_true")
    cf.set_defaults(fn=cmd_confirm)

    ls = sub.add_parser("list", help="調整 state 一覧")
    ls.set_defaults(fn=cmd_list)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
