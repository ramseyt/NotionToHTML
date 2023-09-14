""" Utility functions.
"""

# Standard library imports
import datetime
from urllib.parse import unquote, urlparse
import pathlib
import logging
import secrets

# External module imports

# Local imports


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


RUN_ID = None
RUN_DIRECTORY_FULL_PATH = None


logger = logging.getLogger('notion2html')
logger.setLevel(logging.WARNING)


def extract_filename_from_url(url):
    # Parse the URL into its components
    url_path = urlparse(url).path

    # The filename is the last component of the path
    filename = url_path.split('/')[-1]

    # The filename might be URL-encoded, so decode it just in case
    filename = unquote(filename)

    return filename


def get_attachment_path():
    """Returns a path that's:

    /<the run directory> + /attachments/ + <a directory that's a random string of characters>

    This avoids collisions if we have attachemnts with the same name.
    This also creates the directory.

    Returns a pathlib.Path object."""

    attachment_path = pathlib.Path.joinpath(get_path_to_run_directory(), \
                                            "attachments", \
                                            secrets.token_urlsafe(10))
    attachment_path.mkdir(exist_ok=False, parents=True)
    return attachment_path


def get_path_to_run_directory():
    """Returns a pathlib.Path object of the run directory full path.
    """

    if RUN_DIRECTORY_FULL_PATH:
        return RUN_DIRECTORY_FULL_PATH

    raise RuntimeError("Run directory not defined.")


def set_path_to_run_directory(custom_path=None):
    """Sets the path to the run directory. This is useful for testing."""

    global RUN_DIRECTORY_FULL_PATH
    if RUN_DIRECTORY_FULL_PATH:
        return RUN_DIRECTORY_FULL_PATH

    if custom_path is None:
        root_path = pathlib.Path.home()
    else:
        root_path = pathlib.Path(custom_path)


    full_directory_path = pathlib.Path.joinpath(root_path, \
                                                "logs-notion2html", \
                                                _get_directory_name_for_run())
    full_directory_path.mkdir(exist_ok=True, parents=True)

    RUN_DIRECTORY_FULL_PATH = full_directory_path
    return RUN_DIRECTORY_FULL_PATH


def clear_path_to_run_directory():
    """Set path to run directory to None."""

    global RUN_DIRECTORY_FULL_PATH
    RUN_DIRECTORY_FULL_PATH = None


def clear_run_id():
    """Clear run ID."""

    global RUN_ID
    RUN_ID = None


def _get_directory_name_for_run() -> str:
    now = datetime.datetime.now()
    year = str(now.year)
    month = str(now.month).zfill(2)
    day = str(now.day).zfill(2)
    hour = str(now.hour).zfill(2)
    minute = str(now.minute).zfill(2)
    return f"{year}-{month}-{day}--{hour}-{minute}--{_get_run_id()}"


def _get_run_id():
    """Get the ID for this run. """

    global RUN_ID
    if RUN_ID is None:
        RUN_ID = secrets.token_urlsafe(10)

    return RUN_ID
