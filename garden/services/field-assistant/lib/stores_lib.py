#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STORES 予約 API クライアント + 名簿/月謝振替の集計ロジック(stdlib のみ)。

出自: /home/tukapontas/storesyoyaku/ の stores_furikae.py + stores_event_roster.py を
field_assistant 区画用に 1 ファイルへ統合移植(S42)。
追加点: 名簿行に「アレルギー等・体調面の留意事項」「緊急連絡先」を含める。

stdlib のみ(LINE コンテナ内でも host venv でもそのまま import できることが重要)。
仕様の根拠: stores_yoyaku_openapi.json (STORES 予約 API 202101)。API は参照系のみ。
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.stores.dev/reserve/202101"
JST = "+09:00"

PAYMENT_METHOD_JA = {
    "subscription": "月謝",
    "ticket": "回数券",
    "credit_card": "クレジットカード",
    "none": "なし",
}

SUBS_STATUS_JA = {
    "active": "契約継続中",
    "suspended": "請求停止中",
}

CANCELED_STATUSES = ("canceled_by_host", "canceled_by_customer")


class StoresApiError(Exception):
    pass


class StoresClient:
    def __init__(self, token, base_url=BASE_URL, verbose=True):
        if not token:
            raise StoresApiError(
                "API トークンが未設定です。環境変数 STORES_API_TOKEN を設定してください。"
            )
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose

    def _get(self, path, params=None):
        url = self.base_url + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Accept", "application/json")
        # Cloudflare が Python-urllib の UA をブロックする(Error 1010)ため
        req.add_header(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                if e.code == 429 and attempt < 4:
                    wait = 2 ** attempt
                    if self.verbose:
                        print(f"  レート制限(429)。{wait}秒待って再試行...", file=sys.stderr)
                    time.sleep(wait)
                    continue
                raise StoresApiError(f"HTTP {e.code} for {url}\n{body}") from e
            except urllib.error.URLError as e:
                raise StoresApiError(f"接続エラー: {e.reason} ({url})") from e
        raise StoresApiError(f"再試行上限を超えました: {url}")

    def _paginate(self, path, params, list_key):
        params = dict(params or {})
        page = 1
        items = []
        while True:
            params["page"] = page
            data = self._get(path, params)
            chunk = data.get(list_key, []) or []
            items.extend(chunk)
            pg = data.get("pagination") or {}
            total = pg.get("total")
            if self.verbose:
                print(f"  {path}: page {page}/{total or '?'} ({len(chunk)}件)", file=sys.stderr)
            if not total or page >= total or not chunk:
                break
            page += 1
        return items

    def list_customers(self):
        return self._paginate("/customers", {}, "customers")

    def list_reservations(self, booking_start_from, booking_start_to):
        params = {
            "booking_start_from": booking_start_from,
            "booking_start_to": booking_start_to,
        }
        return self._paginate("/reservations", params, "reservations")


# ── 日付ユーティリティ ──────────────────────────────────────


def day_bounds(date_str):
    d = dt.datetime.strptime(date_str, "%Y-%m-%d")
    return (d.strftime("%Y-%m-%dT00:00:00") + JST,
            d.strftime("%Y-%m-%dT23:59:59") + JST)


def month_range_jst(month_str):
    year, month = map(int, month_str.split("-"))
    start = dt.datetime(year, month, 1)
    nxt = dt.datetime(year + 1, 1, 1) if month == 12 else dt.datetime(year, month + 1, 1)
    end = nxt - dt.timedelta(seconds=1)
    return (start.strftime("%Y-%m-%dT%H:%M:%S") + JST,
            end.strftime("%Y-%m-%dT%H:%M:%S") + JST)


def fmt_dt(value):
    if not value:
        return ""
    try:
        d = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d.strftime("%m/%d %H:%M")
    except Exception:
        return value


# ── 名簿(roster)──────────────────────────────────────────


def profile_answer(profile_fields, *keywords):
    """profile_fields(質問/回答リスト)から、質問文にキーワードを全て含む回答を返す。"""
    for qa in profile_fields or []:
        q = qa.get("question") or ""
        if all(k in q for k in keywords):
            a = qa.get("answer")
            if a:
                return a.strip()
    return ""


def payment_label(reservation):
    pm = reservation.get("payment_method") or {}
    label = PAYMENT_METHOD_JA.get(pm.get("name"), pm.get("name") or "")
    extras = [f"残{u['remaining_tickets']}" for u in pm.get("used_products") or []
              if u.get("remaining_tickets") is not None]
    if extras:
        label += "(" + " ".join(extras) + ")"
    return label


def uses_subscription(reservation):
    return (reservation.get("payment_method") or {}).get("name") == "subscription"


def build_roster(reservations):
    """参加確定(accepted)の予約 → 名簿行。アレルギー・緊急連絡先込み(S42 追加)。"""
    rows = []
    for r in reservations:
        if r.get("status") != "accepted":
            continue
        cust = r.get("customer") or {}
        pf = cust.get("profile_fields")
        row = {
            "イベント名": r.get("booking_service_name") or "",
            "開催日時": fmt_dt(r.get("booking_start")),
            "予約番号": r.get("canonical_id"),
            "保護者名": r.get("customer_name") or cust.get("name") or "",
            "電話番号": cust.get("phone_number") or cust.get("primary_phone_number") or "",
            "会員番号": cust.get("membership_number") or "",
            "参加人数": r.get("num_attendees"),
        }
        for n in (1, 2, 3):
            row[f"子ども{n} 名前"] = profile_answer(pf, "お名前", f"子ども{n}")
            row[f"子ども{n} 生年"] = profile_answer(pf, "生年", f"子ども{n}")
        row["アレルギー・留意事項"] = profile_answer(pf, "アレルギー")
        row["緊急連絡先"] = profile_answer(pf, "緊急連絡先")
        row["支払方法"] = payment_label(r)
        rows.append(row)
    rows.sort(key=lambda x: (x["イベント名"], x["開催日時"], x["保護者名"]))
    return rows


ROSTER_COLUMNS = [
    "イベント名", "開催日時", "保護者名", "電話番号", "参加人数",
    "子ども1 名前", "子ども1 生年", "子ども2 名前", "子ども2 生年",
    "子ども3 名前", "子ども3 生年",
    "アレルギー・留意事項", "緊急連絡先", "支払方法", "会員番号", "予約番号",
]


def surname(name):
    """保護者名から苗字を取り出す(空白区切りの先頭。空白なしは全体)。"""
    return (name or "").replace("　", " ").split(" ")[0]


def kids_names(row):
    """名簿行から子どもの名前(ふりがな括弧を除いた表記)を全員分返す。"""
    names = []
    for n in (1, 2, 3):
        v = row.get(f"子ども{n} 名前") or ""
        if v:
            # 「太郎(たろう)」「結太 ゆうた」のようにふりがなが付くため、
            # 括弧前 + 先頭トークンだけ取る
            v = v.split("(")[0].split("(")[0].strip()
            v = v.replace("　", " ").split(" ")[0]
            names.append(v)
    return names


# ── 月謝振替チェック(furikae)─────────────────────────────


def active_subscription_names(customer):
    return [s.get("product_name") or f"月謝#{s.get('canonical_id')}"
            for s in customer.get("subscriptions") or []
            if s.get("contract_status") == "active"]


def attendance_detail(reservation):
    """1回の参加を『MM/DD 使用チケット』形式で表す(移植元と同形式)。"""
    date = fmt_dt(reservation.get("checked_in_at")) or fmt_dt(reservation.get("booking_start"))
    return f"{date} {payment_label(reservation)}".strip()


def build_furikae(customers, reservations):
    """月謝会員ごとの当月参加状況 → 振替対象(月謝消費 0 回)を抽出。

    移植元 stores_furikae.build_rows と同じ規準:
    参加 = チェックインあり(キャンセル除く)/ 振替対象 = 月謝消費の参加が 1 回もない人。
    戻り値: (全月謝会員の行リスト, 振替対象の行リスト)
    """
    by_customer = {}
    for r in reservations:
        cid = (r.get("customer") or {}).get("canonical_id")
        if cid is not None:
            by_customer.setdefault(cid, []).append(r)

    rows = []
    for c in customers:
        subs = active_subscription_names(c)
        if not subs:
            continue
        my_res = by_customer.get(c.get("canonical_id"), [])
        attended = [
            r for r in my_res
            if r.get("checked_in_at") and r.get("status") not in CANCELED_STATUSES
        ]
        subs_attended = [r for r in attended if uses_subscription(r)]
        rows.append({
            "顧客名": c.get("name") or "",
            "契約中の月謝": " / ".join(subs),
            "当月予約件数": len(my_res),
            "当月参加回数": len(attended),
            "うち月謝利用回数": len(subs_attended),
            "参加明細": "; ".join(attendance_detail(r) for r in attended),
            "振替要否": "不要" if subs_attended else "要",
        })
    rows.sort(key=lambda x: (x["振替要否"] != "要", x["顧客名"]))
    targets = [r for r in rows if r["振替要否"] == "要"]
    return rows, targets
