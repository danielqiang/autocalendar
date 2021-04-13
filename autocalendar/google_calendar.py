import pathlib

from typing import List

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from autocalendar.consts import CACHE_DIR

_GCP_CREDENTIALS_FILEPATH = str(CACHE_DIR / "gcp-credentials.json")
_GCP_OAUTH_TOKEN_FILEPATH = str(CACHE_DIR / "google-calendar-token.json")


class GCPCredentials(Credentials):
    @classmethod
    def from_oauth_flow(
        cls,
        client_secrets_fpath: str = _GCP_CREDENTIALS_FILEPATH,
        scopes: List[str] = None,
    ):
        if scopes is None:
            scopes = []
        if not pathlib.Path(client_secrets_fpath).exists():
            raise ValueError(
                f"Could not locate client secrets file: {client_secrets_fpath}"
            )
        return InstalledAppFlow.from_client_secrets_file(
            client_secrets_fpath, scopes=scopes
        ).run_local_server()

    @classmethod
    def from_cache(
        cls,
        scopes: List[str] = None,
        client_secrets_fpath: str = _GCP_CREDENTIALS_FILEPATH,
        cache_fpath: str = _GCP_OAUTH_TOKEN_FILEPATH,
        clear_cache: bool = False,
    ):
        if clear_cache:
            pathlib.Path(cache_fpath).unlink(missing_ok=True)
        credentials = (
            cls.from_authorized_user_file(cache_fpath)
            if pathlib.Path(cache_fpath).exists()
            else None
        )

        if credentials is None or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                credentials = cls.from_oauth_flow(client_secrets_fpath, scopes=scopes)
            with open(cache_fpath, "w") as f:
                f.write(credentials.to_json())
        return credentials


def return_on_http_error(status_code: int, value):
    def _return_on_http_error(method):
        def wrapped(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except HttpError as e:
                if e.status_code == status_code:
                    return value
                raise

        return wrapped

    return _return_on_http_error


class GoogleCalendar:
    OAUTH_SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self):
        credentials = GCPCredentials.from_cache(
            scopes=self.OAUTH_SCOPES,
        )
        self.service = build("calendar", "v3", credentials=credentials)

    def get_calendars(self):
        return self.service.calendarList().list().execute()

    @return_on_http_error(status_code=404, value=False)
    def calendar_exists(self, name: str) -> bool:
        self.service.calendars().get(calendarId=name).execute()
        return True

    def create_calendar(
        self,
        name: str,
        timezone: str = "America/Los_Angeles",
        skip_if_exists: bool = True,
    ):
        if not (skip_if_exists and self.calendar_exists(name)):
            self.service.calendars().insert(
                body={"summary": name, "timeZone": timezone}
            ).execute()

    def delete_calendar(self, name: str) -> bool:
        for calendar in self.get_calendars()["items"]:
            if calendar["summary"] == name:
                self.service.calendars().delete(calendarId=calendar["id"]).execute()
                return True
        return False

    def create_event(self, calendar_name: str, event):
        pass