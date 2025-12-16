from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload


from main.settings import settings


class GoogleDriveService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.service_credentials: dict = settings.google_application_credentials
        self.root_folder_id = settings.google_drive_root_folder_id
        self.creds = Credentials.from_authorized_user_info(self.service_credentials, self.scopes)

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
        media = MediaFileUpload(file_path, resumable=True)
        service.files().create(
            body=file_metadata,
            media_body=media,
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
