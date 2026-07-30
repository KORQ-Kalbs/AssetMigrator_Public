"""
drive_service.py

Uploads image bytes to Google Drive and returns a public view URL in the
same format the current website already expects:

    https://drive.google.com/uc?export=view&id=FILE_ID
"""

import io
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from loguru import logger

import config

EXT_TO_MIME = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "webp": "image/webp",
}


class DriveService:
    def __init__(self, creds: Credentials):
        self.service = build("drive", "v3", credentials=creds)

    def upload_image(self, image_bytes: bytes, filename: str, ext: str, folder_id: str) -> str:
        """Upload one image and return its public view URL."""
        mime_type = EXT_TO_MIME.get(ext.lower(), "application/octet-stream")

        for attempt in range(1, config.RETRY_ATTEMPTS + 1):
            try:
                file_metadata = {"name": filename, "parents": [folder_id]}
                media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type, resumable=False)
                file = self.service.files().create(
                    body=file_metadata, media_body=media, fields="id"
                ).execute()
                file_id = file["id"]

                # Make it publicly viewable (anyone with the link)
                self.service.permissions().create(
                    fileId=file_id,
                    body={"role": "reader", "type": "anyone"},
                ).execute()

                url = f"https://drive.google.com/uc?export=view&id={file_id}"
                logger.info(f"Uploaded '{filename}' -> {url}")
                return url

            except Exception as e:
                logger.warning(f"Upload attempt {attempt} failed for '{filename}': {e}")
                if attempt < config.RETRY_ATTEMPTS:
                    time.sleep(config.RETRY_DELAY_SECONDS)
                else:
                    raise
