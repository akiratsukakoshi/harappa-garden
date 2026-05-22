"""
Instagram投稿用の画像をGoogle Driveにアップロードして公開URLを取得する。
Instagramの画像投稿スケジュールにはPublicなURLが必須のため。
"""
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from modules.utils import setup_logger

logger = setup_logger("DriveUploader")

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_PATH = "credentials.json"


class DriveUploader:
    def __init__(self):
        folder_id = os.environ.get("SNS_DRIVE_FOLDER_ID")
        if not folder_id:
            raise EnvironmentError("SNS_DRIVE_FOLDER_ID が .env に未設定です。")
        self.folder_id = folder_id

        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        self.service = build("drive", "v3", credentials=creds)

    def upload_and_get_public_url(self, local_path: str) -> str:
        """
        ローカル画像ファイルをDriveにアップロードし、公開ダウンロードURLを返す。
        返り値: https://drive.google.com/uc?export=download&id={file_id}
        """
        filename = os.path.basename(local_path)
        mime = "image/jpeg" if local_path.lower().endswith((".jpg", ".jpeg")) else "image/png"

        logger.info(f"Drive アップロード: {filename}")
        file_metadata = {"name": filename, "parents": [self.folder_id]}
        media = MediaFileUpload(local_path, mimetype=mime)

        uploaded = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True,  # 共有ドライブ対応
        ).execute()
        file_id = uploaded["id"]

        # 公開パーミッション付与
        self.service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
        ).execute()

        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        logger.info(f"公開URL取得完了: {url}")
        return url

    def delete_file(self, file_id: str):
        """投稿完了後にDriveから一時ファイルを削除する"""
        self.service.files().delete(fileId=file_id).execute()
        logger.info(f"Drive一時ファイル削除: {file_id}")
