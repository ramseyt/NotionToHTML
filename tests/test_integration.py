""" Test the notion2html package.
"""

# Standard library imports
import logging

# External module imports

# Local imports
from notion2html import files
from notion2html import notion

__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


def func(x):
    return x + 1


def test_answer():
    assert func(3) == 5


def test_integration():

    # Configure logging
    logger = logging.getLogger('notion2notes')
    logger.setLevel(logging.DEBUG)

    # Add file handler
    handler = logging.FileHandler(files.get_logfile_path())
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

    notion_data = notion.get_from_notion(notion_database_id)
    for _, db in notion_data.all_databases.items():
        for page in db.all_pages:
            logger.debug(f"Page: {page.title} -- {page.id}")
