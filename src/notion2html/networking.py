""" All networking related code.
"""

# Standard library imports
import logging
import os
import threading
import time

# External module imports
import requests

# Local imports
from notion2html import files

__author__ = "Ramsey Tantawi"
__maintainer__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Experimental"


NOTION_VERSION = "2022-06-28"
NOTION_TOKEN = ""
NOTION_API_BASE_URL = "https://api.notion.com/v1"
FETCHED_PAGES = None
logger = logging.getLogger('notion2notes')


class Error404NotFound(Exception):
    """Raised when a 404 is returned from a network request."""


class FetchedPages:
    """Holds the pages that have been fetched from Notion."""

    def __init__(self):
        self._notion_page_ids = set()  # A set to hold the fetched NotionPage ids
        self._notion_pages = {} # A dict to hold the fetched NotionPage objects keyed by id
        self._lock = threading.Lock()  # A lock to ensure thread safety


    def record_fetched_page(self, notion_page):
        with self._lock:
            self._notion_page_ids.add(notion_page.id)
            self._notion_pages[notion_page.id] = notion_page


    def get_all_pageids_fetched(self):
        with self._lock:
            return list(self._notion_page_ids)


    def get_page_for_id(self, page_id):
        with self._lock:
            return self._notion_pages[page_id]


def add_page_to_fetched(notion_page):
    global FETCHED_PAGES
    if FETCHED_PAGES is None:
        FETCHED_PAGES = FetchedPages()

    FETCHED_PAGES.record_fetched_page(notion_page)


def get_fetched_pageids():
    global FETCHED_PAGES
    if FETCHED_PAGES is None:
        FETCHED_PAGES = FetchedPages()

    return FETCHED_PAGES.get_all_pageids_fetched()


def get_fetched_page_for_id(page_id):
    global FETCHED_PAGES
    if FETCHED_PAGES is None:
        FETCHED_PAGES = FetchedPages()

    return FETCHED_PAGES.get_page_for_id(page_id)


def clear_fetched_pageids():
    global FETCHED_PAGES
    if FETCHED_PAGES:
        FETCHED_PAGES = None


def download_file_and_save(url, file_name):
    """Download a file from a url.
    Returns the full path to the downloaded file.
    """

    logger.debug(f"Starting file download for url: {url}")
    response = get_network_data(url, "get", file_download=True)

    attachment_directory = files.get_attachment_path()
    full_file_path = attachment_directory.joinpath(file_name)
    logger.debug(f"Saving file to: {str(full_file_path)}")

    if response is not None:
        with open(full_file_path, "wb") as f:
            f.write(response.content)
    else:
        raise ValueError("response is None while trying to write download to a file!")

    logger.debug((f"Finished file download for: \n"
                  f"url: {url} \n"
                  f"full file path: {full_file_path}"))
    return full_file_path


def fetch_block(block_id):
    url = f"{NOTION_API_BASE_URL}/blocks/{block_id}"

    returned_data = get_network_data(url, "get")
    if returned_data is None:
        raise RuntimeError(f"Error fetching block with ID: {block_id}")

    return returned_data


def fetch_database_info(database_id):
    url = f"{NOTION_API_BASE_URL}/databases/{database_id}"

    returned_data = get_network_data(url, "get")
    if returned_data is None:
        raise RuntimeError(f"Error fetching database info for database_id: {database_id}")

    return returned_data


def fetch_pages_info_from_database(database_id, start_cursor=None):
    url = f"{NOTION_API_BASE_URL}/databases/{database_id}/query"

    logger.debug("Start fetching database pages.")
    logger.debug(f"Start cursor: {start_cursor}")

    if start_cursor is None:
        returned_data = get_network_data(url, "post")
    else:
        returned_data = get_network_data(url, "post", \
                                         payload={"start_cursor": start_cursor})

    if returned_data is None:
        raise RuntimeError(f"Error fetching pages from database for database_id: {database_id}")

    # If has more is false then we got all the results. If not, we need to deal with pagination.
    if not returned_data.get('has_more'): # type: ignore
        logger.debug("End fetching database pages.")
        return returned_data.get('results', []) # type: ignore
    else:
        # concatenate results with next set of results
        # pylint: disable=line-too-long
        new_results = fetch_pages_info_from_database(database_id, returned_data.get('next_cursor')) # type: ignore
        return returned_data.get('results', []) + new_results # type: ignore


def fetch_page(page_id):
    url = f"{NOTION_API_BASE_URL}/pages/{page_id}"

    returned_data = get_network_data(url, "get")
    if returned_data is None:
        raise RuntimeError(f"Error fetching page with ID: {page_id}")

    return returned_data


def fetch_all_blocks(parent_id):
    """As far as I can tell parent ID can be EITHER a page ID or a block ID."""

    if not parent_id:
        raise RuntimeError("Error fetching all blocks: parent ID is empty or None.")

    url = f"{NOTION_API_BASE_URL}/blocks/{parent_id}/children"
    data = get_network_data(url, "get")

    if data is None:
        raise RuntimeError(f"Error fetching all blocks for parent ID: {parent_id}")

    block_children = []
    for block in data.get("results", []): # type: ignore
        block_children.append(block)

        # If the block has children and is a child page then we DON'T want to fetch its children.
        # That will result in us pulling in content from our child pages. which we don't want.
        if (block.get("has_children")) and (block.get("type") != "child_page"):
            block_children.extend(fetch_all_blocks(block["id"]))

    return block_children


###################################################
#
# Functions that actually make the network requests.
#

def get_network_data(url, method, file_download=False, payload=None):
    headers = _get_headers(file_download)

    for i in range(4, 0, -1):
        try:
            response = _execute_request(method, url, headers, payload)
            data, should_retry = _handle_response(response, file_download)
            if not should_retry:
                return data

        except Error404NotFound:
            raise

        except ValueError:
            logger.debug(("Network request: Most likely unhandled method/payload combination "
                          "passed to requests. Re-raising."))
            raise

        except requests.exceptions.Timeout as e:
            logger.debug(("Network request: timeout hit. "
                          "Logging exception below then waiting and then retrying..."))
            logger.debug(str(e))
            time.sleep(10)

        except Exception as e:
            logger.debug(("Network request: Exception while fetching data! \n"
                          f"{str(e)} \n"
                          "Retrying..."))
            time.sleep(5)

        # If we get here that means we still need to retry but we don't have
        # any more retries left. So we raise an exception.
        if i == 1:
            logger.debug(("Network request: No more retries left and we haven't been able to "
                          "get data! Raising exception."))
            raise RuntimeError("No more retries left!")


def _get_headers(file_download=False):

    global NOTION_TOKEN
    if not NOTION_TOKEN:
        NOTION_TOKEN = os.environ.get("NOTION_TOKEN")

    if file_download is False:
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }

    else:
        headers = {}

    return headers


def _execute_request(method, url, headers, payload=None):

    if method == "get":
        response = requests.get(url, headers=headers, timeout=32)

    elif method == "post" and payload is None:
        response = requests.post(url, headers=headers, timeout=32)

    elif method == "post" and payload is not None:
        response = requests.post(url, headers=headers, json=payload, timeout=32)

    else:
        raise ValueError("Invalid method!")

    return response


def _handle_response(response, file_download=False):

    data = None
    if response is None:
        return None, True

    # Parse JSON right away unless we're downloading a file.
    if not file_download:
        try:
            data = response.json()
            if data is None:
                return None, True

        except Exception as e:
            logger.debug("Exception while parsing JSON! Retrying...")
            logger.debug(str(e))
            return None, True

    # Handle various errors
    if response.status_code == 429:
        retry_after = int(response.headers['Retry-After'])
        logger.debug(f"Rate limited. Retrying in {retry_after} seconds...")
        time.sleep(retry_after + 2)
        return None, True

    if response.status_code == 404 and data.get('code', '') == 'object_not_found':
        message = data.get('message', '')
        error_message = ("404 not found. WON'T RETRY. \n"
                         f"URL: {response.url} \n"
                         f"Response message: {message} \n"
                         f"Response headers: {response.headers} \n"
                         f"Response full text: {response.text}")
        logger.debug(error_message)
        raise Error404NotFound(error_message)

    if response.ok is False:
        logger.debug(("Got non-200 status code. \n"
                      f"URL: {response.url} \n"
                      f"Response headers: {response.headers} \n"
                      f"Response: {response.text} \n"
                      f"Sleeping momentarily then retrying..."))
        time.sleep(10)
        return None, True

    if file_download:
        return response, False

    # If we're here we have a valid JSON response without error, so return.
    return data, False


#
#
#
###################################################