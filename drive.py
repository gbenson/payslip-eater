import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

class Drive:
    # Delete the authorized user file if you modify these scopes.
    SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

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

if __name__ == "__main__":
    drive = Drive(secdir=os.path.join(os.path.dirname(__file__),
                                      "secrets"))
    print(drive.credentials)
