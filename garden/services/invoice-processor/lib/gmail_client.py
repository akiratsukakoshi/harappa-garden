"""gmail_client — Gmail API クライアント(HMC fetcher.py の gog CLI 置き換え)。

HMC は gog CLI + keyring password(PTY)で Gmail を叩いていたが、VPS cron では
keyring が使えず、過去に keyring 絡みのインシデントもある(docs/security/incidents/)。
Garden では Gmail API + user OAuth token(lib/user_google.py)に置き換える。
業務ロジック(検索クエリ・ラベル運用)は HMC fetcher.py をそのまま継承。
"""
import base64

from googleapiclient.discovery import build

from .utils import setup_logger
from .user_google import load_credentials

logger = setup_logger("GmailClient")

# --- HMC fetcher.py から継承するラベル運用 ---
LABEL_PROCESSED = "処理済"        # register 成功後に付与
LABEL_FETCHED = "Invoice_Fetched"  # fetch 済みの中間状態
LABEL_PENDING = "Invoice_Pending"  # 件名キーワードに合わないメールを手動で対象化する印


class GmailClient:
    def __init__(self, creds=None):
        self.creds = creds or load_credentials()
        self.service = build("gmail", "v1", credentials=self.creds)
        self._label_ids = None  # name -> id(遅延ロード)

    # --- labels ---

    def _labels(self, refresh=False):
        if self._label_ids is None or refresh:
            resp = self.service.users().labels().list(userId="me").execute()
            self._label_ids = {
                l["name"]: l["id"] for l in resp.get("labels", [])
            }
        return self._label_ids

    def label_id(self, name, create=False):
        """ラベル名 → id。create=True なら無ければ作る(gog の自動作成相当)。"""
        labels = self._labels()
        if name in labels:
            return labels[name]
        if not create:
            return None
        created = (
            self.service.users()
            .labels()
            .create(userId="me", body={"name": name})
            .execute()
        )
        logger.info(f"Created Gmail label: {name}")
        self._labels(refresh=True)
        return created["id"]

    # --- search / read ---

    def search_threads(self, query, max_results=30):
        """クエリに合う thread id のリストを返す。"""
        resp = (
            self.service.users()
            .threads()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        return [t["id"] for t in resp.get("threads", [])]

    def get_thread(self, thread_id):
        """thread の全 message(payload 込み)を返す。"""
        resp = (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        return resp.get("messages", [])

    @staticmethod
    def headers(message):
        """message から {Subject, From, Date} を取り出す。"""
        out = {"Subject": "", "From": "", "Date": ""}
        for h in message.get("payload", {}).get("headers", []):
            if h.get("name") in out:
                out[h["name"]] = h.get("value", "")
        return out

    @staticmethod
    def find_attachments(message, valid_extensions=None):
        """message payload を再帰して添付の {filename, attachmentId} を列挙する。"""
        found = []

        def walk(parts):
            for part in parts:
                filename = part.get("filename")
                att_id = part.get("body", {}).get("attachmentId")
                if filename and att_id:
                    if valid_extensions:
                        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                        if ext not in valid_extensions:
                            continue
                    found.append({"filename": filename, "attachmentId": att_id})
                if part.get("parts"):
                    walk(part["parts"])

        payload = message.get("payload", {})
        if payload.get("parts"):
            walk(payload["parts"])
        return found

    def download_attachment(self, message_id, attachment_id, local_path):
        """添付を local_path に保存する。"""
        att = (
            self.service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        data = base64.urlsafe_b64decode(att["data"])
        with open(local_path, "wb") as f:
            f.write(data)
        return local_path

    # --- modify ---

    def modify_thread(self, thread_id, add_labels=None, remove_labels=None):
        """thread にラベル名で add/remove を適用する(無いラベルは add 時に自動作成)。

        remove に 'INBOX' を含めるとアーカイブになる(HMC register 後の挙動と同じ)。
        """
        add_ids = [self.label_id(n, create=True) for n in (add_labels or [])]
        remove_ids = []
        for n in remove_labels or []:
            lid = "INBOX" if n == "INBOX" else self.label_id(n)
            if lid:
                remove_ids.append(lid)
        body = {}
        if add_ids:
            body["addLabelIds"] = add_ids
        if remove_ids:
            body["removeLabelIds"] = remove_ids
        if not body:
            return
        self.service.users().threads().modify(
            userId="me", id=thread_id, body=body
        ).execute()
