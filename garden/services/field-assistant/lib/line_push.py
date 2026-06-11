#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LINE push(stdlib のみ)— field_assistant 種から core_team グループへの能動送信。

- token: env `LINE_CORE_TEAM_ACCESS_TOKEN`(garden-gaku-co と同一チャネル)
- 宛先: env `FIELD_LINE_TO`(グループ ID。本番グループ投入までは ガクチョの userId で 1:1 テスト)
  カンマ区切りで複数可(テスト時に複数 userId へ送る用)。
- メンション: config/line_users.json(ニックネーム → userId)に登録があれば textV2 の
  mention に変換。未登録の相手は「@名前 さん」のテキスト表記のままフォールバック。
  userId はグループ投入後に webhook の発話イベントから収集して登録する(SKILL 参照)。
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

PUSH_URL = "https://api.line.me/v2/bot/message/push"
_HERE = os.path.dirname(os.path.abspath(__file__))
_USERS_PATH = os.path.join(_HERE, "..", "config", "line_users.json")

MAX_LEN = 4800  # textV2 の上限 5000 の安全側


def _user_map() -> dict:
    try:
        with open(_USERS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _to_text_v2(text: str):
    """本文中の `@名前` を textV2 の mention に変換(登録済みの名前のみ)。"""
    users = _user_map()
    if not users:
        return {"type": "text", "text": text}
    substitution = {}
    counter = [0]

    def repl(m):
        name = m.group(1)
        uid = users.get(name)
        if not uid:
            return m.group(0)
        counter[0] += 1
        key = f"m{counter[0]}"
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


def push(text: str, to: str | None = None) -> list[str]:
    """text を FIELD_LINE_TO(または引数 to)へ push。戻り値 = 送信先リスト。"""
    token = os.environ.get("LINE_CORE_TEAM_ACCESS_TOKEN", "")
    targets = [t.strip() for t in (to or os.environ.get("FIELD_LINE_TO", "")).split(",") if t.strip()]
    if not token:
        raise SystemExit("[line_push] LINE_CORE_TEAM_ACCESS_TOKEN が未設定")
    if not targets:
        raise SystemExit("[line_push] FIELD_LINE_TO が未設定(グループ ID or テスト userId)")
    text = (text or "").strip()
    if not text:
        raise SystemExit("[line_push] empty text")

    for target in targets:
        # LINE 仕様: メンションは group(C…)/room(R…)宛のみ。user(U…)宛 1:1 に
        # textV2 mention を送ると 400 になるため、宛先ごとに変換可否を判定する。
        if target.startswith(("C", "R")):
            message = _to_text_v2(text[:MAX_LEN])
        else:
            message = {"type": "text", "text": text[:MAX_LEN]}
        req = urllib.request.Request(
            PUSH_URL,
            data=json.dumps({"to": target, "messages": [message]}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise SystemExit(f"[line_push] HTTP {e.code} to {target[:6]}…: {body}")
    return targets
