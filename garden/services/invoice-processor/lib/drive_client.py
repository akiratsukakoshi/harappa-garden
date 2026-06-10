"""Google Drive client(invoice-processor 用)。

expense-processor 版(SA / OAuth pickle 両対応)と違い、本 service は
**user OAuth(lib/user_google.py)一本**。理由:
- fetch で請求書 PDF を Drive にアップロードする。SA だとファイルが SA 所有になり
  storage quota で失敗する(My Drive 共有フォルダへの SA アップロードは不可)。
  HMC でも fetch は gog = user 認証だった。
- 認証を 1 token に集約して secrets を減らす(Gmail / Sheets と共用)。

list/download/move/upload のロジックは expense-processor 版と同一。
"""
import io
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

from .utils import setup_logger
from .user_google import load_credentials


class DriveClient:
    def __init__(self, creds=None):
        self.logger = setup_logger("DriveClient")
        self.creds = creds or load_credentials()
        self.service = build("drive", "v3", credentials=self.creds)

    def list_files_in_folder(self, folder_id):
        results = []
        page_token = None
        while True:
            try:
                query = f"'{folder_id}' in parents and trashed = false"
                response = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                ).execute()
                results.extend(response.get("files", []))
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break
            except Exception as e:
                self.logger.error(f"Error listing files: {e}")
                break
        return results

    def download_file(self, file_id, local_path):
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(local_path, "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return True
        except Exception as e:
            self.logger.error(f"Error downloading file {file_id}: {e}")
            return False

    def move_file(self, file_id, previous_folder_id, new_folder_id):
        try:
            file = self.service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents"))
            self.service.files().update(
                fileId=file_id,
                addParents=new_folder_id,
                removeParents=previous_parents,
                fields="id, parents",
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error moving file {file_id}: {e}")
            return False

    def upload_file(self, local_path, parent_id, name=None):
        try:
            file_metadata = {
                "name": name or os.path.basename(local_path),
                "parents": [parent_id],
            }
            media = MediaFileUpload(local_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata, media_body=media, fields="id"
            ).execute()
            return file.get("id")
        except Exception as e:
            self.logger.error(f"Error uploading file {local_path}: {e}")
            return None
