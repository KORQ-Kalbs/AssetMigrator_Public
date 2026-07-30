"""
auth.py

Handles the one-time OAuth login flow and token refresh/reuse, shared by
both the Drive and Sheets services (same scopes, same token file).
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from loguru import logger

import config


def get_credentials() -> Credentials:
    creds = None

    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Google token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(config.CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{config.CREDENTIALS_FILE}' not found. Download it from Google Cloud "
                    f"Console (OAuth Client ID, Desktop App type) and place it next to main.py."
                )
            logger.info("Opening browser for Google login (first run only)...")
            flow = InstalledAppFlow.from_client_secrets_file(config.CREDENTIALS_FILE, config.SCOPES)
            creds = flow.run_local_server(port=0)

        with open(config.TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds
