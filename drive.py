import io
import json
import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PyPDF2 import PdfReader as PDFReader

logger = logging.getLogger(__name__)

class Drive:
    # Delete the authorized user file if you modify these scopes.
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, secdir=None):
        self._secrets_dir = secdir
        self._creds = None

    def _secret_filename(self, filename):
        return os.path.join(self._secrets_dir, filename)

    # The OAuth client secrets file must be supplied by you, see
    # https://developers.google.com/drive/api/quickstart/python
    # for details.
    @property
    def client_secrets_file(self):
        return self._secret_filename("credentials.json")

    # The authorized user file stores the user's access and refresh
    # tokens, and is created automatically when the authorization flow
    # completes for the first time.
    @property
    def authorized_user_file(self):
        return self._secret_filename("token.json")

    @property
    def credentials(self):
        if self._creds is None:
            if os.path.exists(self.authorized_user_file):
                try:
                    self._creds = Credentials.from_authorized_user_file(
                        self.authorized_user_file, self.SCOPES)
                except json.decoder.JSONDecodeError:
                    pass
        if self._creds and self._creds.valid:
            return self._creds

        if self._creds and self._creds.expired and self._creds.refresh_token:
            self._creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_file, self.SCOPES)
            self._creds = flow.run_local_server(port=0)

        with open(self.authorized_user_file, "w") as token:
            token.write(self._creds.to_json())
        return self._creds

    @property
    def service(self):
        return build("drive", "v3", credentials=self.credentials)

    def search(self, query):
        logger.debug(f"files().list(q={repr(query)}, ...)")
        page_token = None
        while True:
            response = self.service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, "
                       "files(id, name)",
                pageToken=page_token).execute()
            for item in response.get("files", []):
                yield item
            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break

if __name__ == "__main__":
    import re
    logging.basicConfig(level=logging.INFO)
    drive = Drive(secdir=os.path.join(os.path.dirname(__file__),
                                      "secrets"))
    [folder] = list(drive.search(" and ".join((
        "name = 'payslips'",
        "mimeType = 'application/vnd.google-apps.folder'"))))
    for item in drive.search(" and ".join((
            f"'{folder['id']}' in parents",
            "mimeType = 'application/pdf'"))):

        # XXX skip some weird (duplicate?) files.
        # XXX What are these? I can't see them other than here?!
        if re.search(r"\s+\(\d+\)\.pdf$", item["name"]) is not None:
            logger.info(f"warning: skipping {item['name']}")
            continue

        logger.info(f"Got {item}")

        request = drive.service.files().get_media(fileId=item["id"])
        stream = io.BytesIO()
        downloader = MediaIoBaseDownload(stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            logger.debug(f"{item['name']}:"
                         f" Got {int(status.progress() * 100)}%")
        #bytes = stream.getvalue()
        #print(f"{item['name']}: Got {len(bytes)} bytes")

        pdf = PDFReader(stream)
        print(f"{item['name']}: Got {len(pdf.pages)} pages")
        page = pdf.pages[0]
        text = page.extract_text()

        print(text)
        break
