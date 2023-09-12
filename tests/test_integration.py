""" Test the notion2html package.
"""
# pylint: disable=import-error

# Standard library imports
import logging
import os

# External module imports

# Local imports

import notion2html


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


def func(x):
    return x + 1


def test_answer():
    assert func(3) == 5


def test_integration():

    # Configure logging
    logger = logging.getLogger('notion2html-test')
    logger.setLevel(logging.DEBUG)

    # Add file handler
    handler = logging.FileHandler(notion2html.get_logfile_path())
    handler.setLevel(logging.DEBUG)
    # pylint: disable=line-too-long
    formatter = logging.Formatter('%(asctime)s - %(filename)s / %(funcName)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # DEBUG: Add stream handler - will remove this later.
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # The Notion database id for testing.
    notion_database_id = "ce3f1480e9a0476fb4d814a5dc0b0828" # This is the inbox

    token = os.environ.get("NOTION_TOKEN")
    notion_data = notion2html.get_from_notion(notion_database_id, token)
    for _, db in notion_data.all_databases.items():
        for page in db.all_pages:
            logger.debug(f"Page: {page.title} -- {page.id}")

    assert 4 == 5
