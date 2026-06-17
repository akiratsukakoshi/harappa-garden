"""sweep_client — クライアント soil の差分世話役(client_steward MVP / Mode S)。

active クライアントの `primary_domain` で Gmail を `last_synced` 以降だけ引き、
「変化と要フォロー」を digest にする。本文は Gmail に残し、soil 正本は要点 +
thread_id 参照(SKILL の機密作法)。

承認境界(SKILL):
  - 生取り込み(新メールの要点)= 自動でよい
  - 解釈(確度変更・新規案件・freee反映の断定)= board → ガクチョ剪定
  本 MVP は **digest を出すだけ**(soil への自動書き込みはしない)。append/board は次段。

認証: invoice_processor の user OAuth token を流用(新規 secret 不要)。
  - 既定 token = garden/services/invoice-processor/secrets/user_token.json
  - CLIENT_STEWARD_TOKEN / INVOICE_USER_TOKEN で上書き可

Plaud(打合せ)側の差分は MCP 越しのため本 cron サービスには含めない(homework)。
当面 Plaud はエージェントが対話時に MCP で引く(S48 と同方式)。
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import sys

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CLIENTS_DIR = os.path.join(REPO, "garden", "soil", "clients")
DEFAULT_TOKEN = os.path.join(
    REPO, "garden", "services", "invoice-processor", "secrets", "user_token.json"
)
TOKEN_PATH = (
    os.environ.get("CLIENT_STEWARD_TOKEN")
    or os.environ.get("INVOICE_USER_TOKEN")
    or DEFAULT_TOKEN
)
STATE_DIR = os.path.join(os.path.dirname(__file__), "state")

# read 用途。invoice token は gmail.modify を持つので読み取り可。
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

OUR_DOMAIN = "harappa-daigaku.jp"
FINANCE_KEYWORDS = ["請求", "見積", "入金", "振込", "お支払", "支払処理", "ご請求"]
SCHEDULE_KEYWORDS = ["日程", "打ち合わせ", "打合せ", "下見", "MTG", "ミーティング", "開催", "当日"]


# ---------- frontmatter 読み(PyYAML 非依存の軽量パーサ) ----------

def read_frontmatter(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    body = text[3:end]
    out = {}
    for line in body.splitlines():
        m = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            val = re.sub(r"\s+#.*$", "", val).strip().strip('"')
            out[key] = val
    return out


def list_active_clients():
    """soil/clients/{slug}/README.md を持つ slug を列挙(primary_domain ありのみ)。"""
    found = []
    if not os.path.isdir(CLIENTS_DIR):
        return found
    for slug in sorted(os.listdir(CLIENTS_DIR)):
        readme = os.path.join(CLIENTS_DIR, slug, "README.md")
        fm = read_frontmatter(readme)
        if fm.get("primary_domain"):
            found.append((slug, fm))
    return found


# ---------- Gmail ----------

def gmail_service():
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(
            f"user token が見つかりません: {TOKEN_PATH}\n"
            "→ invoice_processor の token を流用します。secrets/user_token.json を配置してください。"
        )
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            try:
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            except OSError:
                pass
        else:
            raise RuntimeError("user token 失効。invoice_processor の issue_token.py で再発行を。")
    return build("gmail", "v1", credentials=creds)


def _headers(msg):
    out = {"Subject": "", "From": "", "Date": "", "To": ""}
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name") in out:
            out[h["name"]] = h.get("value", "")
    return out


def _parse_date(date_str):
    try:
        from email.utils import parsedate_to_datetime
        d = parsedate_to_datetime(date_str)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d
    except Exception:
        return None


def sweep_domain(svc, domain, since_dt, max_threads=40):
    """domain に関係する thread を since 以降で集め、要点と要フォロー signal を返す。"""
    after = since_dt.strftime("%Y/%m/%d")
    q = f"(from:{domain} OR to:{domain}) after:{after}"
    resp = svc.users().threads().list(userId="me", q=q, maxResults=max_threads).execute()
    thread_ids = [t["id"] for t in resp.get("threads", [])]

    threads = []
    contacts = {}
    for tid in thread_ids:
        tr = svc.users().threads().get(userId="me", id=tid, format="metadata",
                                       metadataHeaders=["Subject", "From", "To", "Date"]).execute()
        msgs = tr.get("messages", [])
        if not msgs:
            continue
        first_h = _headers(msgs[0])
        last = msgs[-1]
        last_h = _headers(last)
        last_dt = _parse_date(last_h["Date"])
        if last_dt and last_dt < since_dt:
            continue  # since 以降に動きがない

        # contacts(差出人の domain 一致分)
        for m in msgs:
            frm = _headers(m)["From"]
            mm = re.search(r"<([^>]+)>", frm) or re.search(r"([\w.\-+]+@[\w.\-]+)", frm)
            if mm and domain in mm.group(1).lower():
                addr = mm.group(1).lower()
                name = frm.split("<")[0].strip().strip('"') if "<" in frm else ""
                contacts.setdefault(addr, name)

        # signal: 最後の発話が先方か(=こちらが返す番)
        last_from = last_h["From"].lower()
        awaiting_us = (OUR_DOMAIN not in last_from)
        days_since = (dt.datetime.now(dt.timezone.utc) - last_dt).days if last_dt else None

        subj = first_h["Subject"]
        finance = any(k in subj for k in FINANCE_KEYWORDS)
        schedule = any(k in subj for k in SCHEDULE_KEYWORDS)

        threads.append({
            "thread_id": tid,
            "subject": subj,
            "msgs": len(msgs),
            "last_date": last_h["Date"][:22],
            "last_dt": last_dt,
            "awaiting_us": awaiting_us,
            "days_since": days_since,
            "finance": finance,
            "schedule": schedule,
        })
    threads.sort(key=lambda t: t["last_dt"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                 reverse=True)
    return threads, contacts


# ---------- digest ----------

def build_digest(slug, fm, threads, contacts, since_dt):
    lines = []
    company = fm.get("company", slug)
    lines.append(f"## {company}({fm.get('primary_domain')}) — {since_dt.date()} 以降")
    if not threads:
        lines.append("  (新しい動きなし)")
        return "\n".join(lines)

    # 要フォロー(こちらが返す番 / 一定日数放置)
    awaiting = [t for t in threads if t["awaiting_us"]]
    if awaiting:
        lines.append("\n**🔴 要フォロー(こちらが返す番)**")
        for t in awaiting:
            d = f"{t['days_since']}日" if t["days_since"] is not None else "?"
            lines.append(f"  - [{t['last_date']}] {t['subject'][:50]}({d}前・{t['msgs']}通)")

    fin = [t for t in threads if t["finance"]]
    if fin:
        lines.append("\n**💰 finance シグナル(見積/請求/入金)**")
        for t in fin:
            lines.append(f"  - [{t['last_date']}] {t['subject'][:50]} → freee 突合要")

    lines.append("\n**📨 動いたスレッド**")
    for t in threads:
        flags = []
        if t["awaiting_us"]:
            flags.append("要返信")
        if t["finance"]:
            flags.append("💰")
        if t["schedule"]:
            flags.append("📅")
        fl = (" [" + "/".join(flags) + "]") if flags else ""
        lines.append(f"  - [{t['last_date']}] {t['subject'][:50]}({t['msgs']}通){fl}")

    if contacts:
        lines.append("\n**👤 登場した担当者(署名/アドレス)**")
        for addr, name in contacts.items():
            lines.append(f"  - {name or '(名前なし)'} <{addr}>")
    return "\n".join(lines)


# ---------- state(watermark) ----------

def load_watermark(slug, default_days):
    path = os.path.join(STATE_DIR, f"{slug}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                s = json.load(f)
            return dt.datetime.fromisoformat(s["last_synced"])
        except Exception:
            pass
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=default_days)


def save_watermark(slug):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{slug}.json")
    with open(path, "w") as f:
        json.dump({"last_synced": dt.datetime.now(dt.timezone.utc).isoformat()}, f)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="client_steward Sweep(Gmail 差分 digest)")
    ap.add_argument("--client", help="slug(例 mti)。未指定なら全 active client")
    ap.add_argument("--since", help="YYYY-MM-DD。未指定なら watermark or 既定日数前")
    ap.add_argument("--days", type=int, default=14, help="watermark 不在時の遡及日数(既定14)")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="digest を出すだけ(MVP は常に dry-run。soil 書込なし)")
    ap.add_argument("--commit-watermark", action="store_true",
                    help="今回時刻を watermark に保存(次回はここから差分)")
    args = ap.parse_args()

    targets = ([(args.client, read_frontmatter(
        os.path.join(CLIENTS_DIR, args.client, "README.md")))]
        if args.client else list_active_clients())
    if not targets or (args.client and not targets[0][1].get("primary_domain")):
        print(f"対象 client なし(primary_domain を持つ soil/clients/ が必要): {args.client}")
        return 1

    svc = gmail_service()
    print(f"# client_steward Sweep  ({dt.datetime.now().strftime('%Y-%m-%d %H:%M')})\n")
    for slug, fm in targets:
        domain = fm.get("primary_domain")
        since_dt = (dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc)
                    if args.since else load_watermark(slug, args.days))
        threads, contacts = sweep_domain(svc, domain, since_dt)
        print(build_digest(slug, fm, threads, contacts, since_dt))
        print()
        if args.commit_watermark:
            save_watermark(slug)
            print(f"  (watermark 更新: {slug})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
