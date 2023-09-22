""" An example of a client using notion2html.
"""
# pylint: disable=import-error

# Standard library imports
import logging
import os

# External module imports

# Local imports
import test_integration
import notion2html


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


def test_example_client(caplog):
    """Mimic the expected path of how a client would use notion2html to export HTML and create
    HTML files ready to upload to a webserver."""

    ##### Logging setup - for testing only
    caplog.set_level(logging.DEBUG, logger="notion2html")
    logfile_path = test_integration.create_log()

    logger = logging.getLogger("notion2html")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    #####


    #### Start client code
    #
    #

    try:

        # The Notion database id for testing.
        notion_database_id = "ce3f1480e9a0476fb4d814a5dc0b0828" # This is the inbox
        token = os.environ.get("NOTION_TOKEN")

        # Get the data from Notion
        notion_data = notion2html.get_from_notion(notion_database_id, token)

        # Path to the directory where the HTML files will be written
        html_files_directory = logfile_path.parent.joinpath("html")
        attachment_files_directory = html_files_directory.joinpath("attachments")
        attachment_files_directory.mkdir(exist_ok=False, parents=True)

        # Fix up links, save attachments, and write out HTML
        for page in notion_data.get_pages():

            # Fix up page mention links
            page_link_path = "/"
            page.set_all_link_paths(page_link_path)

            # Fix up attachment links and save all attachments to that directory
            attachment_link_path = "/attachments"
            page.set_attachment_paths_and_copy(attachment_link_path, attachment_files_directory)

            # Write out the html to a file
            full_path_to_html_file = html_files_directory.joinpath(f"{page.id}.html")
            with full_path_to_html_file.open(mode="w", encoding="utf-8") as html_file:
                html_file.write(page.get_updated_html())

    except Exception as exc:
        logger.exception(exc)

    finally:
        with logfile_path.open(mode="a", encoding="utf-8") as log_file:
            log_file.write(caplog.text)

    assert "Exception" not in caplog.text
    assert "exception" not in caplog.text
    assert "ERROR" not in caplog.text
    assert "Error" not in caplog.text
    assert "ERROR ADDED:" not in caplog.text
