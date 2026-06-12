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
import re
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

    def get_customer(self, canonical_id):
        """顧客詳細(一覧と違い subscriptions / ticket_books の product_name を含む)。"""
        data = self._get(f"/customers/{canonical_id}")
        return data.get("customer") or data

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


def _short_product(name):
    """商品名の表示用短縮(「おやこ学部 振替チケット 」→「振替チケット」)。"""
    return re.sub(r"^(おやこ|こども|おとな)学部[・\s ]*", "", (name or "").strip())


def product_name_map(client, customer_ids):
    """顧客詳細から {商品ID: 商品名} を引く(used_products.canonical_id と突合用)。

    同一人物が月謝と回数券を併有するケースで「今回どれを使ったか」を名前で
    出すために必要(used_products には ID しか入っていない。実測 S43)。
    """
    m = {}
    for cid in customer_ids:
        if cid is None:
            continue
        try:
            cust = client.get_customer(cid)
        except StoresApiError:
            continue  # 名前が引けないだけなら名簿自体は止めない
        for s in cust.get("subscriptions") or []:
            m[s.get("product_canonical_id")] = s.get("product_name") or ""
        for t in cust.get("ticket_books") or []:
            m[t.get("product_canonical_id")] = t.get("product_name") or ""
    return m


def payment_label(reservation, product_names=None):
    """支払方法の表示。商品名マップがあれば「今回使った月謝/回数券の名前」を添える。"""
    pm = reservation.get("payment_method") or {}
    label = PAYMENT_METHOD_JA.get(pm.get("name"), pm.get("name") or "")
    bits = []
    for u in pm.get("used_products") or []:
        name = _short_product((product_names or {}).get(u.get("canonical_id"), ""))
        rem = u.get("remaining_tickets")
        bit = name
        if rem is not None:
            bit = (f"{name} " if name else "") + f"残{rem}"
        if bit:
            bits.append(bit)
    if bits:
        label += "(" + "・".join(bits) + ")"
    return label


def uses_subscription(reservation):
    return (reservation.get("payment_method") or {}).get("name") == "subscription"


def build_roster(reservations, client=None):
    """参加確定(accepted)の予約 → 名簿行。アレルギー・緊急連絡先込み(S42 追加)。

    client を渡すと顧客詳細を引き、支払方法に「今回使った月謝/回数券の商品名」を
    添える(S43。1 顧客 1 GET 増えるが日次名簿の件数なら軽い)。
    """
    accepted = [r for r in reservations if r.get("status") == "accepted"]
    pmap = {}
    if client is not None:
        ids = {(r.get("customer") or {}).get("canonical_id") for r in accepted}
        pmap = product_name_map(client, ids)
    rows = []
    for r in accepted:
        cust = r.get("customer") or {}
        pf = cust.get("profile_fields")
        primary = r.get("customer_name") or cust.get("name") or ""
        row = {
            "イベント名": r.get("booking_service_name") or "",
            "開催日時": fmt_dt(r.get("booking_start")),
            "予約番号": r.get("canonical_id"),
            "保護者名": primary,
            "苗字": parent_surname(primary, cust.get("name") or ""),
            "電話番号": cust.get("phone_number") or cust.get("primary_phone_number") or "",
            "会員番号": cust.get("membership_number") or "",
            "参加人数": r.get("num_attendees"),
        }
        for n in (1, 2, 3):
            row[f"子ども{n} 名前"] = profile_answer(pf, "お名前", f"子ども{n}")
            row[f"子ども{n} 生年"] = profile_answer(pf, "生年", f"子ども{n}")
        row["アレルギー・留意事項"] = profile_answer(pf, "アレルギー")
        row["緊急連絡先"] = profile_answer(pf, "緊急連絡先")
        row["支払方法"] = payment_label(r, pmap)
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


def parent_surname(primary, registry=""):
    """保護者の姓。予約者名(primary)と顧客台帳名(registry)を突き合わせて判定する。

    予約者名が「祥子 黒川」のように名・姓逆で入っているケースがあるため(実測 S43)、
    台帳名が分かち書きならその先頭を正とし、そうでなければ逆順の痕跡を見る。
    """
    p_tokens = [t for t in (primary or "").replace("　", " ").split(" ") if t]
    r_tokens = [t for t in (registry or "").replace("　", " ").split(" ") if t]
    if len(r_tokens) >= 2:
        return r_tokens[0]
    reg_flat = "".join(r_tokens)
    if (len(p_tokens) >= 2 and reg_flat
            and not reg_flat.startswith(p_tokens[0])
            and reg_flat.startswith(p_tokens[-1])):
        return p_tokens[-1]
    return p_tokens[0] if p_tokens else reg_flat


_HIRAGANA_ONLY = re.compile(r"^[ぁ-ゖー]+$")
_KIDS_EMPTY_MARKERS = {"なし", "ナシ", "無し", "無", "-", "ー"}


def kids_names(row):
    """名簿行から子どもの名前を全員分返す(1 回答 = 1 名)。

    回答の実測バリエーション(S43): 「結太　ゆうた」「依莉・えり」「穣(じょう)」
    「津野　太志、たいし」(姓つき)など。括弧内とひらがなのみのトークン(ふりがな)を
    落とし、保護者の姓と同じトークンも落として本名 1 つを選ぶ。
    """
    surname_ = (row.get("苗字") or "").strip()
    names = []
    for n in (1, 2, 3):
        raw = (row.get(f"子ども{n} 名前") or "").strip()
        if not raw:
            continue
        s = re.sub(r"[((][^))]*[))]?", "", raw)  # ふりがな括弧(閉じ忘れ含む)除去
        tokens = [t for t in re.split(r"[\s 、,・/／]+", s) if t]
        tokens = [t for t in tokens if t not in _KIDS_EMPTY_MARKERS]
        if surname_:
            tokens = [t for t in tokens if t != surname_]
        if not tokens:
            continue
        # 漢字・カタカナ表記を優先(ひらがなのみはふりがなの可能性が高い)。
        # 全トークンがひらがなならそれが本名なので先頭を採る。
        pick = next((t for t in tokens if not _HIRAGANA_ONLY.match(t)), tokens[0])
        names.append(pick)
    return names


# ── 月謝振替チェック(furikae)─────────────────────────────


def active_subscription_names(customer):
    return [s.get("product_name") or f"月謝#{s.get('canonical_id')}"
            for s in customer.get("subscriptions") or []
            if s.get("contract_status") == "active"]


def attendance_detail(reservation, product_names=None):
    """1回の参加を『MM/DD 使用チケット』形式で表す(移植元と同形式)。"""
    date = fmt_dt(reservation.get("checked_in_at")) or fmt_dt(reservation.get("booking_start"))
    return f"{date} {payment_label(reservation, product_names)}".strip()


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

    # 顧客一覧に契約情報が乗っていれば商品名マップを作る(参加明細の表示用)
    pmap = {}
    for c in customers:
        for s in c.get("subscriptions") or []:
            pmap[s.get("product_canonical_id")] = s.get("product_name") or ""
        for t in c.get("ticket_books") or []:
            pmap[t.get("product_canonical_id")] = t.get("product_name") or ""

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
            "参加明細": "; ".join(attendance_detail(r, pmap) for r in attended),
            "振替要否": "不要" if subs_attended else "要",
        })
    rows.sort(key=lambda x: (x["振替要否"] != "要", x["顧客名"]))
    targets = [r for r in rows if r["振替要否"] == "要"]
    return rows, targets
