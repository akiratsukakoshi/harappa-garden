#!/usr/bin/env python3
"""garden-gaku-co — Discord master channel への送信(REST, 依存ゼロ).

使い方:
    DISCORD_BOT_TOKEN=... DISCORD_MASTER_CHANNEL_ID=... python3 send.py "本文"
    echo "本文" | python3 send.py            # 標準入力からも可

段1(疎通)と段2(夜の一言)の出口。gateway は不要(Discord REST のみ)。
discord.py は受信して対話する段3で導入する。
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://discord.com/api/v10"
MAX_LEN = 1900  # Discord の 1 メッセージ上限は 2000。安全側に分割。


def send(content: str) -> dict:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    channel = os.environ.get("DISCORD_MASTER_CHANNEL_ID")
    if not token or not channel:
        raise SystemExit("[send] missing DISCORD_BOT_TOKEN / DISCORD_MASTER_CHANNEL_ID")
    content = (content or "").strip()
    if not content:
        raise SystemExit("[send] empty content")

    chunks = [content[i : i + MAX_LEN] for i in range(0, len(content), MAX_LEN)]
    last: dict = {}
    for chunk in chunks:
        req = urllib.request.Request(
            f"{API}/channels/{channel}/messages",
            data=json.dumps({"content": chunk}).encode("utf-8"),
            headers={
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
                # Discord API はカスタム User-Agent を要求する
                "User-Agent": "garden-gaku-co (https://github.com/akiratsukakoshi/harappa-garden, 0.1)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                last = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # エラー本文に token は含まれない(出しても安全)
            body = e.read().decode("utf-8", "replace")
            raise SystemExit(f"[send] HTTP {e.code}: {body}")
    return last


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]).strip() or sys.stdin.read()
    res = send(msg)
    print(f"[send] ok id={res.get('id')}")
