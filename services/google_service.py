import io
import json
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from main.settings import settings


class GoogleDriveService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.service_account_file = settings.google_application_credentials
        self.root_folder_id = settings.google_drive_root_folder_id
        self.google_client_email = settings.google_client_email
        self.creds = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists('google_auth_token.json'):
            creds = Credentials.from_authorized_user_file('google_auth_token.json', self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.service_account_file, self.scopes
                )
                creds = flow.run_local_server(port=0)
            token_data = json.loads(creds.to_json())
            token_data["client_email"] = self.google_client_email
            
            with open('google_auth_token.json', 'w') as token:
                json.dump(token_data, token, ensure_ascii=False, indent=2)
            creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes
            )
        return creds
    
    def upload_video(
        self, 
        folder_name: str,
        file_path: str, 
        file_name: str,
    ):
        service = build('drive', 'v3', credentials=self.creds)
        subfolder_id = self.get_or_create_subfolder(
            self.root_folder_id,
            folder_name,
        )
        file_metadata = {
            'name': file_name,
            'parents': [subfolder_id]
        }
        service.files().create(
            body=file_metadata,
            media_body=file_path,
        ).execute()

    def get_or_create_subfolder(
        self,
        parent_folder_id: str,
        folder_name: str
    ) -> str:
        folder_id = self.find_subfolder(parent_folder_id, folder_name)
        if folder_id:
            return folder_id

        service = build('drive', 'v3', credentials=self.creds)

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }

        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        return folder.get('id')
        
    def find_subfolder(
        self,
        parent_folder_id: str,
        folder_name: str
    ) -> str | None:
        service = build('drive', 'v3', credentials=self.creds)

        query = (
            f"'{parent_folder_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and name = '{folder_name}' "
            f"and trashed = false"
        )

        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()

        folders = response.get('files', [])

        if folders:
            return folders[0]['id']
        return None
