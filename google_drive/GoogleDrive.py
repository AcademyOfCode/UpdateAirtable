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

    def downloadFile(self, fileId, mimeType,filePath):
        request = self.__access.files().export(fileId=fileId, mimeType=mimeType)
        localFD = io.FileIO(filePath, mode="wb")
        mediaRequest = http.MediaIoBaseDownload(localFD, request)

        while True:
            try:
                downloadProgress, done = mediaRequest.next_chunk()
            except errors.HttpError as error:
                print("An error occurred: %s" % error)
                return
            if downloadProgress:
                print("Download Progress: %d%%" % int(downloadProgress.progress() * 100))
            if done:
                print("Download Complete")
                return

    def uploadFile(self, filePath, mimeType):
        file_metadata = {"name": filePath}
        media = MediaFileUpload(filePath,mimetype=mimeType)
        self.__access.files().create(body=file_metadata, media_body=media, fields="id").execute()

    def editFile(self, filePath, fileId, mimeType):
        file_metadata = {"name": os.path.basename(filePath).split(".")[0]}
        media = MediaFileUpload(filePath, mimetype=mimeType)

        return self.__access.files().update(fileId=fileId, body=file_metadata, media_body=media).execute()