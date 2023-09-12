""" Test the notion2html package.
"""
# pylint: disable=import-error

# Standard library imports
import datetime
import logging
import os
import pathlib
import secrets

# External module imports

# Local imports
import notion2html


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


def create_log():

    # log directory name
    now = datetime.datetime.now()
    year = str(now.year)
    month = str(now.month).zfill(2)
    day = str(now.day).zfill(2)
    hour = str(now.hour).zfill(2)
    minute = str(now.minute).zfill(2)
    directory_name =  f"{year}-{month}-{day}--{hour}-{minute}--{secrets.token_urlsafe(10)}"

    # Add file handler
    test_log_file = pathlib.Path.joinpath(pathlib.Path.home(),
                                        "testlogs-notion2html",
                                        directory_name,
                                        "logs-notion2html.log")
    pathlib.Path(test_log_file).parent.mkdir(exist_ok=False, parents=True)

    return test_log_file


def func(x):
    return x + 1


def test_answer():
    assert func(4) == 5


def test_integration(caplog):

    caplog.set_level(logging.DEBUG, logger="notion2html")
    logfile = create_log()

    logger = logging.getLogger("notion2html")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    for handler in logger.handlers:
        handler.setFormatter(formatter)

    # The Notion database id for testing.
    notion_database_id = "ce3f1480e9a0476fb4d814a5dc0b0828" # This is the inbox
    token = os.environ.get("NOTION_TOKEN")

    notion_data = notion2html.get_from_notion(notion_database_id, token)
    for _, db in notion_data.all_databases.items():
        for page in db.all_pages:
            logger.debug(f"Page: {page.title} -- {page.id}")

    with logfile.open(mode="a", encoding="utf-8") as log_file:
        log_file.write(caplog.text)
