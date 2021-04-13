import pathlib
import pickle

import bs4
import requests

from autocalendar.consts import CACHE_DIR

_CANVAS_SESSION_FILEPATH = f"{CACHE_DIR}/canvas-session.pickle"


class CanvasSession(requests.Session):
    def __init__(self, user: str, password: str):
        super().__init__()

        self.headers["user-agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36"
        )
        self.login(user, password)

    def login(self, user: str, password: str):
        r = self.get(
            "https://canvas.uw.edu/login/saml/83",
            headers={"referer": "https://apps.canvas.uw.edu/"},
            allow_redirects=True,
        )
        r = self.post(
            r.url,
            data={
                "j_username": user,
                "j_password": password,
                "_eventId_proceed": "Sign in",
            },
        )

        saml_response = bs4.BeautifulSoup(r.text, "html.parser").find(
            "input", {"name": "SAMLResponse"}
        )

        assert (
            saml_response
        ), "Failed to authenticate user, username or password was incorrect"

        self.post(
            "https://canvas.uw.edu/login/saml",
            data={"SAMLResponse": saml_response["value"]},
            headers={
                "origin": "https://idp.u.washington.edu",
                "referer": "https://idp.u.washington.edu/",
            },
            allow_redirects=True,
        )

    @classmethod
    def from_cache(
        cls,
        user: str,
        password: str,
        cache_pickle_fpath: str = _CANVAS_SESSION_FILEPATH,
        clear_cache: bool = False,
    ):
        if clear_cache:
            pathlib.Path(cache_pickle_fpath).unlink(missing_ok=True)
        if pathlib.Path(cache_pickle_fpath).exists():
            with open(cache_pickle_fpath, "rb") as f:
                session = pickle.load(f)
        else:
            session = cls(user, password)
        with open(cache_pickle_fpath, "wb") as f:
            pickle.dump(session, f)
        return session

    def get(self, url, **kwargs):
        # We usually want JSON, so default to it
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].setdefault("accept", "application/json")
        return super().get(url, **kwargs)


class Canvas:
    def __init__(self, user: str, password: str):
        self.session = CanvasSession.from_cache(user, password)

    def get_courses(self):
        url = "https://canvas.uw.edu/api/v1/users/self/favorites/courses"
        return self.session.get(url).json()

    def get_quizzes(self, course_id):
        url = f"https://canvas.uw.edu/api/v1/courses/{course_id}/quizzes"
        return self.session.get(url).json()

    def get_assignments(self, course_id):
        url = f"https://canvas.uw.edu/api/v1/courses/{course_id}/assignments"
        return self.session.get(url).json()

    def get_calendar(self):
        url = f"https://canvas.uw.edu/api/v1/calendar_events"
        return self.session.get(url).json()
