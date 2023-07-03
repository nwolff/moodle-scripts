import requests
from munch import munchify

"""
Didn't find a good library that covers our needs to connect to moodle from python.

I ended up borrowing some of the code from  https://github.com/mrcinv/moodle_api.py
and wrapped it into a class that contains the configuration, and added the munchify 
convenience to it.
"""


def rest_api_parameters(in_args, prefix="", out_dict=None):
    """Transform dictionary/array structure to a flat dictionary, with key names
    defining the structure.

    Example usage:
    >>> rest_api_parameters({'courses':[{'id':1,'name': 'course1'}]})
    {'courses[0][id]':1,
     'courses[0][name]':'course1'}
    """
    if out_dict == None:
        out_dict = {}
    if not type(in_args) in (list, dict):
        out_dict[prefix] = in_args
        return out_dict
    if prefix == "":
        prefix = prefix + "{0}"
    else:
        prefix = prefix + "[{0}]"
    if type(in_args) == list:
        for idx, item in enumerate(in_args):
            rest_api_parameters(item, prefix.format(idx), out_dict)
    elif type(in_args) == dict:
        for key, item in in_args.items():
            rest_api_parameters(item, prefix.format(key), out_dict)
    return out_dict


class MoodleClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token

    def __call__(this, fname, **kwargs):
        """Calls moodle API function with function name fname and keyword arguments.

        Example:
        >>> call_mdl_function('core_course_update_courses',
                               courses = [{'id': 1, 'fullname': 'My favorite course'}])
        """
        parameters = rest_api_parameters(kwargs)
        parameters.update(
            {"wstoken": this.token, "moodlewsrestformat": "json", "wsfunction": fname}
        )
        response = requests.post(this.url, parameters)
        response = response.json()
        if type(response) == dict and response.get("exception"):
            raise SystemError("Error calling Moodle API\n", response)
        return munchify(response)
