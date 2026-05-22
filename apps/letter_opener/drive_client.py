import os
import io
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from modules.utils import setup_logger

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

class DriveClient:
    def __init__(self, credentials_path="credentials.json", token_path="token.json"):
        self.logger = setup_logger("DriveClient_LetterOpener")
        self.creds = None
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.credentials_path):
            if os.path.exists(self.token_path):
                 with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                 if creds and creds.valid:
                     try:
                        service = build('drive', 'v3', credentials=creds)
                        return service
                     except Exception as e:
                        self.logger.error(f"Failed to build drive service from token: {e}")
            
            self.logger.warning(f"Credentials file not found at {self.credentials_path}. Drive integration will not work.")
            return None

        try:
            with open(self.credentials_path, 'r') as f:
                import json
                cred_data = json.load(f)
                is_service_account = cred_data.get("type") == "service_account"
        except Exception as e:
            self.logger.error(f"Failed to read credentials file: {e}")
            return None

        creds = None
        
        if is_service_account:
            try:
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES)
                self.logger.info(f"Authenticated using Service Account: {creds.service_account_email}")
            except Exception as e:
                self.logger.error(f"Service Account Auth failed: {e}")
                return None
        else:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                         self.logger.error(f"Error refreshing token: {e}")
                         creds = None
                
                if not creds:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)

        try:
            service = build('drive', 'v3', credentials=creds)
            return service
        except Exception as e:
            self.logger.error(f"Failed to build drive service: {e}")
            return None

    def list_files_in_folder(self, folder_id):
        if not self.service:
            return []
            
        results = []
        page_token = None
        while True:
            try:
                query = f"'{folder_id}' in parents and trashed = false"
                response = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            except Exception as e:
                self.logger.error(f"Error listing files: {e}")
                break
                
        return results

    def download_file(self, file_id, local_path):
        if not self.service:
            return False

        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(local_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return True
        except Exception as e:
            self.logger.error(f"Error downloading file {file_id}: {e}")
            return False

    def move_file(self, file_id, previous_folder_id, new_folder_id):
        if not self.service:
            return False
            
        try:
            file = self.service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            
            self.service.files().update(
                fileId=file_id,
                addParents=new_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error moving file {file_id}: {e}")
            return False
