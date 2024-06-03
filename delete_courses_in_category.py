#! /usr/bin/env python

"""
Recursively deletes courses under a given category.

**Warning** Course backups are deleted with the courses
(deleting a course manually does the same thing)

We need this script because doing so manually for a large number
of courses just hangs.

Uses the Moodle API
"""

import argparse
import os
import sys

import dotenv
import progressbar
import structlog

from lib.moodle_api import URL, MoodleClient

log = structlog.get_logger()


def delete_moodle_courses(moodle: MoodleClient, category_id: str):
    categories_to_delete = moodle(
        "core_course_get_categories", criteria=[{"key": "id", "value": category_id}]
    )
    courses_to_delete = []
    for category in categories_to_delete:
        log.info(
            "collecting courses",
            category=category.name,
            course_count=category.coursecount,
        )
        courses_in_category = moodle(
            "core_course_get_courses_by_field", field="category", value=category.id
        )
        courses_to_delete.extend(courses_in_category.courses)

    if not courses_to_delete:
        print("No courses found, nothing to do")
        return

    for i, course in enumerate(courses_to_delete):
        log.info(
            "course",
            index=i,
            shortname=course.shortname,
            categoryname=course.categoryname,
        )

    print()
    user_input = input(
        f"Do you want to delete these {len(courses_to_delete)} courses (yes/no): "
    )
    if user_input.lower() != "yes":
        print("Aborting")
        return

    # We delete the courses one by one even though the API can do many at a
    # time. This is because we are weary of the php script time limit.
    for course in progressbar.progressbar(courses_to_delete):
        log.info("deleting course", course=course.shortname)
        result = moodle("core_course_delete_courses", courseids=[course.id])
        print(result)  # XXX


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deletes all moodle courses living under a given category"
    )
    parser.add_argument(
        "category_id",
        help="The root category containing the courses to delete",
    )
    args = parser.parse_args()

    dotenv.load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        sys.exit("Missing environment variable 'TOKEN'")
    log.info("connecting", url=URL)
    moodle = MoodleClient(URL, token)

    delete_moodle_courses(moodle, args.category_id)
