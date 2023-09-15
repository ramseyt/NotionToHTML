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

    try:
        notion_data = notion2html.get_from_notion(notion_database_id, token)
        for _, db in notion_data._all_databases.items():
            logger.debug(f"Database title: {db.title} -- {db.id}")
            for page in db.all_pages:
                logger.debug(f"Page: {page.title} -- {page.id}")

        logger.debug("\n\n\n\n\n")
        logger.debug("All Pages!!!!")
        for page in notion_data.get_pages():

            logger.debug(f"Page: {page.title} -- {page.id}")
            if page.has_errors():
                for error in page.get_errors():
                    logger.debug(f"Error: {error}")

            # Write out the html to a file
            html_file_full_path = logfile.parent.joinpath(f"{page.id}.html")
            with html_file_full_path.open(mode="w", encoding="utf-8") as html_file:
                html_file.write(page.html)

    except Exception as exc:
        logger.exception(exc)

    finally:
        with logfile.open(mode="a", encoding="utf-8") as log_file:
            log_file.write(caplog.text)

    assert "Exception" not in caplog.text
