""" Utility functions.
"""
# pylint: disable=import-error

# Standard library imports
import logging

# External module imports

# Local imports
from . import htmltools


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


logger = logging.getLogger('notion2html')
logger.setLevel(logging.WARNING)


def find_page_id(page):

    page_id = page.get('id', '')
    if not page_id:
        logger.debug(f"Raising exception - page ID not found for page: {page}")
        raise ValueError("Page ID not found")

    return page_id


def find_page_title(page):

    # I am pretty sure this is incomplete.

    if page.get('properties', {}).get('Name', {}):
        title = page['properties']['Name']['title'][0]['text']['content']

    elif page.get('properties', {}).get('title', {}):
        title = page['properties']['title']['title'][0]['text']['content']

    # Case where the title is a property of the page.
    elif page.get('properties', {}):
        all_properties = page.get('properties', {})

        for _, property_info in all_properties.items():
            if property_info.get('type', '') == 'title':
                title_rich_text = property_info.get('title', [])

        title = htmltools.convert_rich_text_to_string(title_rich_text)

    else:
        logger.debug(f"Can't get page title for page: \n{page}")
        raise RuntimeError("Can't get the page title!")

    return title


def find_url_for_block(block, block_type):
    url = block.get(block_type, {}).get('file', {}).get('url', '')

    if url == "" and block_type == "image":
        url = block.get(block_type, {}).get('external', {}).get('url', '')

    if url == "" and block_type == "image":
        url = block.get(block_type, {}).get('internal', {}).get('url', '')

    if not url:
        logger.debug(("In a block type that has an attachment but our URL is empty.\n"
                      f"Block type: {block_type} \n"
                      f"Block: {block}"))
        raise RuntimeError("Trying to download attachment but URL is empty for a block \
                            type that has one.")

    return url


def flatten_notion_page_tree(page_list):
    """
    This function takes a list of NotionPage objects and returns a flat list of all
    NotionPage objects, including subpages.

    Args:
        page_list (list): A list of NotionPage objects.

    Returns:
        flat_list (list): A flat list of all NotionPage objects.
    """

    flat_list = []
    for page in page_list:
        flat_list.append(page)
        if page.has_subpages():
            flat_list.extend(flatten_notion_page_tree(page.subpages))

    deduplicated_pages = list({x.id: x for x in flat_list}.values())
    return deduplicated_pages
