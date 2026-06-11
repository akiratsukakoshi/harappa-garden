#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Open-Meteo で会場の天気予報(降水確率・風)を取る(stdlib のみ、API キー不要)。

会場名 → 緯度経度は config/venues.json。未知の会場は default 地点で引き、
出力に「(地点未登録: {会場名}は逗子の予報)」と注記する。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_VENUES_PATH = os.path.join(_HERE, "..", "config", "venues.json")

API = "https://api.open-meteo.com/v1/forecast"


def _venues() -> dict:
    with open(_VENUES_PATH, encoding="utf-8") as f:
        return json.load(f)


GEOCODE_API = "https://geocoding-api.open-meteo.com/v1/search"
GSI_API = "https://msearch.gsi.go.jp/address-search/AddressSearch"


def _geocode(name: str):
    """地名 → (表示名, lat, lon) or None。

    ① 国土地理院アドレス検索(漢字・日本語地名に強い、キー不要)
    ② Open-Meteo Geocoding(ローマ字・海外向けフォールバック)
    """
    # ① GSI(日本語地名の本命)
    try:
        url = GSI_API + "?" + urllib.parse.urlencode({"q": name})
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data:
            hit = data[0]
            lon, lat = hit["geometry"]["coordinates"]
            return hit.get("properties", {}).get("title", name), lat, lon
    except Exception:
        pass
    # ② Open-Meteo geocoding
    try:
        params = {"name": name, "count": 1, "language": "ja", "format": "json"}
        url = GEOCODE_API + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        hit = (data.get("results") or [None])[0]
        if hit:
            label = hit.get("name", name)
            admin = hit.get("admin1") or ""
            return (f"{label}({admin})" if admin and admin not in label else label,
                    hit["latitude"], hit["longitude"])
    except Exception:
        pass
    return None


def resolve_venue(name: str):
    """会場名/地名 → (表示名, lat, lon, 注記 or None)。

    解決順: ① venues.json(登録会場) ② 地名検索(任意地点のピンポイント対応)
    ③ default 会場(注記つき)
    """
    venues = _venues()
    name = (name or "").strip()
    for key, v in venues.items():
        if key == "_default":
            continue
        if key in name or any(a in name for a in v.get("aliases", []) if a):
            return key, v["lat"], v["lon"], None
    if name:
        geo = _geocode(name)
        if geo:
            label, lat, lon = geo
            return label, lat, lon, None
    dflt = venues["_default"]
    v = venues[dflt]
    note = f"地点を特定できず{dflt}の予報" if name else None
    return dflt, v["lat"], v["lon"], note


# WMO weather code → 日本語(代表値用の簡約マップ)
_WMO_JA = [
    ((0,), "快晴"), ((1, 2), "晴れ"), ((3,), "曇り"), ((45, 48), "霧"),
    ((51, 53, 55, 56, 57), "霧雨"), ((61, 63, 65, 66, 67), "雨"),
    ((71, 73, 75, 77, 85, 86), "雪"), ((80, 81, 82), "にわか雨"),
    ((95, 96, 99), "雷雨"),
]


def _code_ja(code) -> str:
    for codes, ja in _WMO_JA:
        if code in codes:
            return ja
    return ""


_DIR16 = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
          "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]


def _dir_ja(deg) -> str:
    """風向(度、吹いてくる方角)→ 16 方位の日本語。"""
    if deg is None:
        return ""
    return _DIR16[int((deg + 11.25) % 360 // 22.5)]


def forecast(venue_name: str, date: dt.date) -> dict:
    """指定日の時間別予報を 午前(6-12時)/午後(12-18時) に要約して返す。

    戻り値例: {venue, note, am: {...}, pm: {...}, summary}
    各ブロック: sky = 天気(最頻コード), pop = 最大降水確率%,
    wind/gust = 最大風速/突風 m/s, tmin/tmax = 気温範囲 ℃
    """
    key, lat, lon, note = resolve_venue(venue_name)
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation_probability,wind_speed_10m,wind_gusts_10m,"
                  "wind_direction_10m,temperature_2m,weather_code",
        "wind_speed_unit": "ms",
        "timezone": "Asia/Tokyo",
        "start_date": date.isoformat(),
        "end_date": date.isoformat(),
    }
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    pops = hourly.get("precipitation_probability") or []
    winds = hourly.get("wind_speed_10m") or []
    gusts = hourly.get("wind_gusts_10m") or []
    dirs = hourly.get("wind_direction_10m") or []
    temps = hourly.get("temperature_2m") or []
    codes = hourly.get("weather_code") or []

    def _vals(seq, idx):
        return [seq[i] for i in idx if i < len(seq) and seq[i] is not None]

    def block(h_from, h_to):
        idx = [i for i, t in enumerate(times) if h_from <= int(t[11:13]) < h_to]
        if not idx:
            return None
        cs = _vals(codes, idx)
        ts = _vals(temps, idx)
        # 風向 = ブロック内で風が最も強い時刻の向き(現場判断に効くのは最大風速時)
        wind_idx = [i for i in idx if i < len(winds) and winds[i] is not None]
        peak = max(wind_idx, key=lambda i: winds[i], default=None)
        direction = dirs[peak] if peak is not None and peak < len(dirs) else None
        return {
            "sky": _code_ja(max(cs, key=cs.count)) if cs else "",
            "pop": max(_vals(pops, idx), default=None),
            "wind": max(_vals(winds, idx), default=None),
            "gust": max(_vals(gusts, idx), default=None),
            "dir": _dir_ja(direction),
            "tmin": min(ts, default=None),
            "tmax": max(ts, default=None),
        }

    am, pm = block(6, 12), block(12, 18)

    def fmt(b):
        if not b:
            return "予報なし"
        parts = []
        if b.get("sky"):
            parts.append(b["sky"])
        if b.get("tmin") is not None and b.get("tmax") is not None:
            parts.append(f"{b['tmin']:.0f}〜{b['tmax']:.0f}℃")
        if b["pop"] is not None:
            parts.append(f"降水{b['pop']:.0f}%")
        if b["wind"] is not None:
            gust = f"(突風{b['gust']:.0f})" if b["gust"] is not None else ""
            prefix = f"{b['dir']}の" if b.get("dir") else ""
            parts.append(f"{prefix}風{b['wind']:.0f}m/s{gust}")
        return " ".join(parts)

    summary = f"午前 {fmt(am)} / 午後 {fmt(pm)}"
    if note:
        summary += f" ※{note}"
    return {"venue": key, "note": note, "am": am, "pm": pm, "summary": summary}
