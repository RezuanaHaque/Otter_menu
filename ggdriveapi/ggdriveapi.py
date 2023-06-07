import io
import shutil
# from gglogin import gglogin
from mimetypes import MimeTypes
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
# from ggdriveapi.ggdriveapi import DriveAPI
# from gglogin import gglogin
# from gglogin import gglogin
from ggdriveapi.gglogin import gglogin


class DriveAPI:
    def __init__(self):
        creds = gglogin()
        self.service = build('drive', 'v3', credentials=creds)

    def getFileNameById(self, fileId):
        file = self.service.files().get(fileId = fileId).execute()
        fileName = file['name']
        return fileName

    #  returns -1 if the file does not exist
    def getIdByPath(self, rootFolderId, path):
        path = path.split('/')
        folderId = rootFolderId

        for fileName in path:
            fileName = fileName.replace("'", "\\'")
            response = self.service.files().list(q = "name = '{fileName}' "
                                                     "and '{folderId}' in parents "
                                                     "and trashed = false"
                                                     .format(fileName = fileName, folderId = folderId),
                                                 spaces='drive',
                                                 fields='files(id, name)',
                                                ).execute()

            files = response.get('files', [])
            if len(files) != 1:
                return -1
            folderId = files[0].get('id')

        fileId = folderId
        return fileId
    
    # returns fileId
    def createFolder(self, parentFolderId, folderName):
        metadata = {
            'name': folderName,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents':[parentFolderId]
        }

        folder = self.service.files().create(body=metadata, fields='id').execute()
        
        return folder.get('id')

    #  returns file name (not path)
    def download(self, fileId, downloadToFolder = '.'):
        fileName = self.getFileNameById(fileId)
        request = self.service.files().get_media(fileId = fileId)
        fh = io.BytesIO()
        
        # Initialise a downloader object to download the file
        downloader = MediaIoBaseDownload(fh, request, chunksize=204800)
        done = False

        # Download the data in chunks
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        
        file = downloadToFolder + '/' + fileName

        # Write the received data to the file
        with open(file, 'wb') as f:
            shutil.copyfileobj(fh, f)

        return fileName

    # returns fileId and url link
    def upload(self, parentFolderId, localFilePath):
        fileName = localFilePath.split('/')[-1]
        mimetype = MimeTypes().guess_type(fileName)[0]
        fileMetadata = {'name': fileName, 'parents':[parentFolderId]}
        media = MediaFileUpload(localFilePath, mimetype=mimetype)
        file = self.service.files().create(body=fileMetadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('id'), file.get('webViewLink')


    def update(self, fileId, localFilePath):
        fileName = localFilePath.split('/')[-1]
        mimetype = MimeTypes().guess_type(fileName)[0]
        media = MediaFileUpload(localFilePath, mimetype=mimetype)
        self.service.files().update(fileId = fileId, media_body = media).execute()


if __name__ == "__main__":
    obj = DriveAPI()
    fileId = obj.getIdByPath('1B4E7YXiVpkrqGM1U88gVKxt-PTVMQxYg', 'test/kongPao2.csv')
    obj.update(fileId, 'kongPao2.csv')
