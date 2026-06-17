# ruff: noqa: ANN001 ANN003 ANN204

import requests
from munch import munchify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

"""
Didn't find a good library that covers our needs to connect to moodle from python.

I ended up borrowing some of the code from  https://github.com/mrcinv/moodle_api.py
and wrapped it into a class that contains the configuration, and added the munchify
convenience to it.
"""

URL = "https://moodle.gymnasedebeaulieu.ch/webservice/rest/server.php"

# (connect timeout, read timeout) in seconds. The read timeout is generous
# because some calls (e.g. deleting a course) can be slow server-side.
DEFAULT_TIMEOUT = (10, 300)

# Retry transient failures so a single network blip doesn't abort a long
# run (e.g. the hour-plus course-deletion script). We retry on connection
# errors and 5xx responses. Moodle web-service calls all use POST, so we
# explicitly opt POST into the retried methods. The risk of retrying a POST
# whose side effect actually went through (e.g. a duplicate cohort) is
# acceptable here: these scripts are run interactively and their results are
# diffed against Moodle afterwards.
DEFAULT_RETRY = Retry(
    total=3,
    backoff_factor=1.0,
    status_forcelist=(500, 502, 503, 504),
    allowed_methods=frozenset(["POST"]),
)


class MoodleApiError(Exception):
    """Raised when the Moodle web service returns an exception payload."""

    def __init__(self, fname, response):
        self.fname = fname
        self.response = response
        super().__init__(f"Error calling Moodle API function {fname!r}: {response}")


def rest_api_parameters(in_args, prefix="", out_dict=None):
    """Transform dictionary/array structure to a flat dictionary, with key names
    defining the structure.

    Example usage:
    >>> rest_api_parameters({'courses':[{'id':1,'name': 'course1'}]})
    {'courses[0][id]':1,
     'courses[0][name]':'course1'}
    """
    if out_dict is None:
        out_dict = {}
    if type(in_args) not in (list, dict):
        out_dict[prefix] = in_args
        return out_dict
    if prefix == "":
        prefix = prefix + "{0}"
    else:
        prefix = prefix + "[{0}]"
    if isinstance(in_args, list):
        for idx, item in enumerate(in_args):
            rest_api_parameters(item, prefix.format(idx), out_dict)
    elif isinstance(in_args, dict):
        for key, item in in_args.items():
            rest_api_parameters(item, prefix.format(key), out_dict)
    return out_dict


class MoodleClient:
    def __init__(self, url, token, timeout=DEFAULT_TIMEOUT):
        self.url = url
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=DEFAULT_RETRY)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def __call__(self, fname, **kwargs):
        """Calls moodle API function with function name fname and keyword arguments.

        Example:
        >>> client('core_course_update_courses',
                               courses = [{'id': 1, 'fullname': 'My favorite course'}])
        """
        parameters = rest_api_parameters(kwargs)
        parameters.update(
            {"wstoken": self.token, "moodlewsrestformat": "json", "wsfunction": fname}
        )
        response = self.session.post(self.url, parameters, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("exception"):
            raise MoodleApiError(fname, payload)
        return munchify(payload)
