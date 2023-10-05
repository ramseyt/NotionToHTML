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

        # This is the NotionLink test page id
        notion_test_id = "d9a63744f67c49cca3ac417187990986"
        token = os.environ.get("NOTION_TOKEN")

        # Get the data from Notion - there should only be one page returned
        notion_test_page = notion2html.get_from_notion(notion_test_id, token)[0]

        # Get NotionLinks
        notion_links = notion_test_page.get_all_notionlinks()
        assert len(notion_links) == 3

        link_page_ids = [link.page_id for link in notion_links]
        link_titles = [link.title for link in notion_links]

        # Test expected page ids and titles
        assert "462732ba8c8247429dfc61c880c8b405" in link_page_ids
        assert "b0655b19a95942929dde9641f0fa7a4b" in link_page_ids
        assert "0acf9625b8ea43428a574afdc91995ce" in link_page_ids

        assert "Test - All Elements" in link_titles
        assert "Page 2" in link_titles
        assert "Page 1" in link_titles


        for link in notion_links:
            if link.id == "0acf9625b8ea43428a574afdc91995ce":
                retrieved_link = notion_test_page.get_notionlink_for_placeholder_text(link.placeholder_text)

                assert retrieved_link.id == "0acf9625b8ea43428a574afdc91995ce"
                assert retrieved_link.title == "Page 1"

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
