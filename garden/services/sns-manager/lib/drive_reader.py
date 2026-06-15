"""Google Drive 読み書き(sns-manager 用、SA)。

ガクチョが SNS_DRIVE_FOLDER_ID のフォルダに金曜までに置いた候補画像を
list / download する。さらに、投稿に使った画像は `used/`(使用済み)サブフォルダへ
move して候補置き場から外す(翌週以降の候補に再掲しないため)。

move/create を行うため、フォルダは SA に **編集者(コンテンツ管理者)** で共有して
おく必要がある(閲覧者だけだと list/download は通るが move/create は 403)。
"""
import io
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .utils import setup_logger
from .google_sa import load_sa_credentials

IMAGE_MIMES = ("image/jpeg", "image/png", "image/webp")
FOLDER_MIME = "application/vnd.google-apps.folder"
USED_FOLDER_NAME = os.getenv("SNS_DRIVE_USED_FOLDER_NAME", "使用済み")


def _escape(value):
    """Drive クエリ文字列内のシングルクォートをエスケープ。"""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveReader:
    def __init__(self, creds=None):
        self.logger = setup_logger("DriveReader")
        self.service = build("drive", "v3", credentials=creds or load_sa_credentials())

    def list_images(self, folder_id):
        """フォルダ**直下**の画像ファイルを新しい順に返す(used/ サブフォルダ内は除外)。"""
        results, page_token = [], None
        while True:
            resp = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, createdTime)",
                orderBy="createdTime desc",
                pageToken=page_token,
            ).execute()
            for f in resp.get("files", []):
                if f.get("mimeType") in IMAGE_MIMES:
                    results.append(f)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        self.logger.info(f"候補画像 {len(results)} 件(folder={folder_id})")
        return results

    def find_image_by_name(self, folder_id, name):
        """フォルダ直下から同名の画像ファイルを 1 件返す(無ければ None)。"""
        resp = self.service.files().list(
            q=(f"'{folder_id}' in parents and name = '{_escape(name)}' "
               "and trashed = false"),
            fields="files(id, name, mimeType)",
            orderBy="createdTime desc",
        ).execute()
        for f in resp.get("files", []):
            if f.get("mimeType") in IMAGE_MIMES:
                return f
        return None

    def ensure_used_folder(self, parent_id, name=USED_FOLDER_NAME):
        """parent 直下の used フォルダを取得、無ければ作成して id を返す。"""
        resp = self.service.files().list(
            q=(f"'{parent_id}' in parents and name = '{_escape(name)}' "
               f"and mimeType = '{FOLDER_MIME}' and trashed = false"),
            fields="files(id, name)",
        ).execute()
        files = resp.get("files", [])
        if files:
            return files[0]["id"]
        meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
        created = self.service.files().create(body=meta, fields="id").execute()
        self.logger.info(f"used フォルダ作成: {name} (id={created['id']})")
        return created["id"]

    def move_to_used(self, file_id, parent_id, used_folder_id):
        """file を parent 直下から used フォルダへ移動する。"""
        self.service.files().update(
            fileId=file_id,
            addParents=used_folder_id,
            removeParents=parent_id,
            fields="id, parents",
        ).execute()

    def download(self, file_id, local_path):
        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(local_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return local_path
