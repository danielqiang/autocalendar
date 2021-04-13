import configparser
import json
from pprint import pprint

from autocalendar.canvas import Canvas
from autocalendar.google_calendar import GoogleCalendar


def main():
    config = configparser.ConfigParser()
    config.read("credentials.cfg")

    user = config["credentials"]["user"]
    password = config["credentials"]["password"]

    canvas = Canvas(user, password)
    courses = canvas.get_courses()

    assignments = {
        course["name"]: canvas.get_assignments(course["id"]) for course in courses
    }

    pprint(f"Courses: {courses}")
    pprint(f"Assignments: {assignments}")

    with open("test.json", "w") as f:
        json.dump(assignments, f)

    auto_calendar = GoogleCalendar()
    auto_calendar.service.calendarList().list().execute()


if __name__ == "__main__":
    main()
