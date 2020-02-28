import io
import os
import pickle

from googleapiclient import http, errors
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GoogleDrive:
    def __init__(self):
        self.__access = self.__access()

    def __access(self):
        creds = None
        SCOPES = ["https://www.googleapis.com/auth/drive"]

        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)

            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)

        print("Accessing Google Drive")

        return build("drive", "v3", credentials=creds)

    def download_file(self, file_id, mime_type,file_path):
        request = self.__access.files().export(fileId=file_id, mimeType=mime_type)
        local_fd = io.FileIO(file_path, mode="wb")
        media_request = http.MediaIoBaseDownload(local_fd, request)

        while True:
            try:
                download_progress, done = media_request.next_chunk()
            except errors.HttpError as error:
                print("An error occurred: %s" % error)
                return
            if download_progress:
                print("Download Progress: %d%%" % int(download_progress.progress() * 100))
            if done:
                print("Download Complete")
                return

    def upload_file(self, file_path, mime_type):
        file_metadata = {"name": file_path}
        media = MediaFileUpload(file_path,mimetype=mime_type)
        self.__access.files().create(body=file_metadata, media_body=media, fields="id").execute()

    def edit_file(self, file_path, file_id, mime_type):
        file_metadata = {"name": os.path.basename(file_path).split(".")[0]}
        media = MediaFileUpload(file_path, mimetype=mime_type)

        return self.__access.files().update(fileId=file_id, body=file_metadata, media_body=media).execute()