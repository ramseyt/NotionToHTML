""" Code for interacting with Notion.
"""
# pylint: disable=import-error

# Standard library imports
import concurrent.futures
import logging
import traceback

# External module imports

# Local imports
from . import files
from . import htmltools
from . import networking
from . import utils


__author__ = "Ramsey Tantawi"
__maintainer__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Experimental"


logger = logging.getLogger('notion2html')
logger.setLevel(logging.WARNING)
logger.propagate = True


class NotionResult:
    """Represents the result of fetching data from Notion.
    Contains NotionPage and NotionDatabase objects.
    """

    def __init__(self):

        self.top_level_page = None
        self.all_pages = {}
        self.all_databases = {}
        self.errors = {}
        self.file_path = ''


    def add_top_level_page(self, page):
        """page: a NotionPage object."""
        self.top_level_page = page
        self.all_pages[page.id] = page

        if page.subpages:
            subpages = utils.flatten_notion_page_tree([page])
            for subpage in subpages:
                self.all_pages[subpage.id] = subpage


    def add_database(self, database):
        """database: a NotionDatabase object."""
        self.all_databases[database.id] = database


class NotionDatabase:
    """Represents a Notion database.
    """

    def __init__(self, database_id, title_blocks, properties):
        self.id = database_id

        # List of title blocks that make up the database title.
        self.title_blocks = title_blocks
        self.title = htmltools.convert_rich_text_to_string(title_blocks)

        # List of NotionPage objects that are top-level database items.
        self.top_level_pages = []

        # List of all NotionPage objects in the database, including sub-pages of database
        # items.
        self.all_pages = []

        # Dict that is decoded JSON of the full database properties object
        # we got from Notion.
        self.properties = properties


    def add_pages(self, new_pages):
        """Input: a list of NotionPage objects.

        Adds this list to the existing list of pages."""

        self.top_level_pages.extend(new_pages)

        # Regenerate the flat list of all pages everytime new pages are added.
        self.all_pages = utils.flatten_notion_page_tree(self.top_level_pages)


class NotionPage:
    """Represents a Notion page.
    """

    def __init__(self, page_id):
        self.id = page_id
        self.title = ""
        self.blocks = []

        # Dict that is decoded JSON of the full page properties object
        # we got from Notion.
        self.properties = {}

        # Dict - keys are block ids as strings, value is the entire block JSON.
        self.blocks_by_id = {}

        self.subpages = []
        self.subpage_ids = []
        self.parent_page_title = ""
        self.parent_page_id = ""
        self.soup = None
        self.html = ""

        # Dict - key is the full attachment URL, value is an Attachment object.
        self.attachments = {}

        # Dict - key is the block id of the table block, value is a list of table row blocks
        # for that table.
        self.tables_and_rows = {}

        # Dict - key is the database id, value is the NotionDatabase object.
        self.databases = {}


    def set_title(self, title):
        self.title = title


    def set_blocks(self, blocks):
        self.blocks = blocks

        for block in blocks:
            self.blocks_by_id[block.get('id')] = block


    def set_properties(self, properties):
        self.properties = properties


    def get_placeholder_text_for_url(self, url):
        return self.attachments[url].placeholder_text


    def get_block_for_block_id(self, block_id):
        return self.blocks_by_id[block_id]


    def have_subpages(self):
        return len(self.subpages) != 0


    def add_subpage(self, subpage):
        """Add a single subpage that's a NotionPage object.
        """
        self.subpages.append(subpage)
        self.subpage_ids.append(subpage.id)


    def add_parent_page_title(self, parent_page_title):
        self.parent_page_title = parent_page_title


    def add_parent_page_id(self, parent_page_id):
        self.parent_page_id = parent_page_id


    def add_html(self, html):
        self.html += html


    def add_soup(self, soup):
        self.soup = soup


    def add_attachment(self, attachment):
        self.attachments[attachment.url] = attachment


    def add_tableid_and_rows(self, table_id, table_rows):
        self.tables_and_rows[table_id] = table_rows


    def add_database(self, database):
        self.databases[database.id] = database


    def get_database_for_id(self, database_id):
        return self.databases[database_id]


class Attachment:
    """File attachment data. Includes images, PDFs, etc."""

    def __init__(self, url, notion_type, placeholder_text, full_path_to_file):
        self.url = url
        self.type = notion_type
        self.placeholder_text = placeholder_text

        # full_path_to_file is a pathlib.Path object, not a string.
        self.path = full_path_to_file


def startup(token, file_path):
    """Setup code for a single run."""

    networking.set_notion_token(token)
    if file_path:
        files.set_path_to_run_directory(file_path)
    else:
        files.set_path_to_run_directory()


def teardown():
    """Cleanup code to run after a single run is complete."""

    # Once done fetching pages, clear the list of fetched page IDs so it's
    # not carried forward if we run this function again before the calling
    # code exits.
    networking.clear_fetched_pages()
    networking.clear_notion_token()
    files.clear_path_to_run_directory()
    files.clear_run_id()


########################### Transform data from Notion
#
# These functions call into the fetch Notion functions below to get
# data from Notion, and then transforms and formats it.
#

def get_from_notion(notion_id, notion_token, file_path=None):

    logger.debug(f"Notion id passed in: {notion_id}")
    startup(notion_token, file_path)

    page = None
    database = None
    result = NotionResult()

    try:
        page = get_page_with_id(notion_id)
    except networking.Error404NotFound:
        logger.debug(f"Page not found in Notion: {notion_id}")

    try:
        database = get_database_from_notion(notion_id)
    except networking.Error404NotFound:
        logger.debug(f"Database not found in Notion: {notion_id}")

    teardown()

    if page:
        result.add_top_level_page(page)
        return result

    elif database:
        result.add_database(database)
        return result

    else:
        return result


def get_page_with_id(page_id):
    """Input: page id as a string.
       Return: NotionPage object."""

    logger.debug(f"Attempting page fetch from Notion with page id: {page_id}")
    page = networking.fetch_page(page_id)
    return get_page(page)


def get_database_from_notion(database_id):
    """Input: database id as a string.
       Return: NotionDatabase object."""

    logger.debug(f"Attempting database fetch from Notion database id: {database_id}")
    all_db_info = networking.fetch_database_info(database_id)
    db_id = all_db_info.get('id', '')
    db_title_blocks = all_db_info.get('title', [])

    database = NotionDatabase(db_id, db_title_blocks, all_db_info)
    pages_info = networking.fetch_pages_info_from_database(database_id)

    logger.debug(f"Total number of database pages found: {len(pages_info)}")
    database.add_pages(get_pages_concurrently(pages_info))

    return database


def get_pages_concurrently(pages):
    """Get all pages from a Notion database."""

    notion_pages = []

    # Using a maximum of 50 max workers for now. I tried 500 but got exceptions about
    # too many open files.
    maximum_workers = 50
    number_of_pages = len(pages)
    if number_of_pages < maximum_workers:
        maximum_workers = number_of_pages

    logger.debug("Start concurrent page data fetching...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=maximum_workers) as executor:
        page_futures = {executor.submit(get_page, page): page for page in pages}
        for future in concurrent.futures.as_completed(page_futures):
            page = page_futures[future]
            try:
                notion_pages.append(future.result())
            except Exception as exc:
                logger.debug((f"Exception hit while doing concurrent data fetch for: \n"
                              f"Page ID: {page['id']} \n"
                              f"Page title: {utils.find_page_title(page)} \n"
                              f"Exception: {exc} \n"
                              f"Traceback: {traceback.format_exc()}"))

    logger.debug("End concurrent page data fetching")

    # Filter out list elements where the returned value from page fetching is None.
    filtered_pages = [x for x in notion_pages if x is not None]

    # Deduplicate list of returned pages.
    deduplicated_pages = list({x.id: x for x in filtered_pages}.values())
    logger.debug(f"Original fetch: {len(notion_pages)} pages. Ids (not counting None): {[x.id for x in notion_pages if x is not None]}"
                 f"After removing none: {len(filtered_pages)} pages. Ids: {[x.id for x in filtered_pages]}"
                 f"After deduplication: {len(deduplicated_pages)} pages. Ids: {[x.id for x in deduplicated_pages]}")
    return deduplicated_pages


def get_page(page, parent_page=None):

    page_id = utils.find_page_id(page)
    notion_page = NotionPage(page_id)
    notion_page.set_title(utils.find_page_title(page))
    notion_page.set_properties(page)

    # Record the page id we're fetching so we can avoid fetching it again
    # if it's a subpage of another page, or mentioned again. This is protected
    # by a lock so we are basically doing a test-and-set. If this returns true
    # we don't have this page yet so we continue fetching. If it returns false we already
    # have the page so we return None.
    if networking.add_page_to_fetched(notion_page) is False:
        logger.debug(f"Already fetched page. Returning None. ID: {notion_page.id} "
                     f"Title: {notion_page.title}")
        return None

    logger.debug(f"Don't have page yet. Continuing with fetch. ID: {notion_page.id} "
                     f"Title: {notion_page.title}")

    notion_page.set_blocks(networking.fetch_all_blocks(page_id))

    # If we have a parent page add the parent ID and title to the current page.
    if parent_page:
        notion_page.add_parent_page_title(parent_page.title)
        notion_page.add_parent_page_id(parent_page.id)

    # Handle special cases including attachments.
    handle_page_special_cases(notion_page)

    # Do HTML conversion.
    htmltools.convert_page_to_html(notion_page)

    # Recursively fetch all subpages. This will get all subpages of subpages
    # and so on for the entire tree of pages at any depth.
    subpages = get_subpages_of_page(notion_page)
    for subpage in subpages:
        if subpage:
            notion_page.add_subpage(subpage)

    # Log info about the complete fetch.
    logger.debug((f"Fetch complete (including any subpages) for this Notion page: \n"
                  f"Title: {notion_page.title}\n"
                  f"Id: {notion_page.id}\n"
                  f"Subpages: {notion_page.subpages}\n"
                  f"Subpage IDs: {notion_page.subpage_ids}\n"
                  f"Tables and Rows:\n{notion_page.tables_and_rows}\n"
                  f"Blocks: \n{notion_page.blocks}\n\n"))

    return notion_page


def handle_page_special_cases(notion_page):
    """Handles attachments, tables, column blocks, and embedded databases."""

    blocks_with_attachments = htmltools.block_types_with_attachments()

    for i, block in enumerate(notion_page.blocks):
        block_type = block.get('type', '')
        block_id = block.get('id', '')

        # Handle tables. Find all table block types and then fetch all blocks that are
        # children of that block. We already have all blocks so fetching the children is
        # redundant but it's slightly easier than parsing the blocks and possibly messing
        # up, especially for pages with multiple tables.
        if block_type == 'table':
            table_row_blocks = networking.fetch_all_blocks(block.get('id', ''))
            notion_page.add_tableid_and_rows(block.get('id', ''), table_row_blocks)

        # Handle column blocks. Once we get them we need to put them into the list
        # of blocks in the proper order.
        if block_type == 'column_list':
            column_blocks = get_column_blocks(block)
            notion_page.blocks = notion_page.blocks[:i] + column_blocks + notion_page.blocks[i:]

        # Handle databases embedded in the page content.
        if block_type == "child_database":
            database = get_database_from_notion(block_id)
            notion_page.add_database(database)

        # Hande attachments.
        if block_type in blocks_with_attachments:

            url = utils.find_url_for_block(block, block_type)
            filename = files.extract_filename_from_url(url)

            # full_file_path is a pathlib.Path object, not a string.
            full_file_path = networking.download_file_and_save(url, filename)

            # Get placeholder text and save attachment info on the file object
            placeholder_text =  htmltools.attachment_link_text()

            attachment = Attachment(url, block_type, placeholder_text, full_file_path)
            notion_page.add_attachment(attachment)


def get_subpages_of_page(notion_page):
    """I originally tried to detect only true subpages as opposed to page mentions (which are links
    to pages outside the page tree of the current page). But ultimately I couldn't figure out how to
    reliably detect true subpages.

    So instead now just detect all page mentions and assume they're subpages, but also keep track of
    the pages that have already been fetched and deduplicate pages before returning the ultimate
    set of results. (Note that deduplication happens higher up the call stack, not down here.) This
    will prevent fetch loops, and avoid missing pages.
    """

    subpage_ids = []
    subpages = []

    # Determine if there's any subpages of this page. If so, get their IDs.
    # There are two known ways to detect page mentions:
    #
    # 1) Look for blocks of type child_page.
    # 2) Look for blocks of type 'mention'.
    for block in notion_page.blocks:
        block_id = block.get('id')

        # A child_page block is always a subpage, when a block is of type child_page, the
        # id property of the block is ALSO the page ID of the subpage.
        if block.get('type') == 'child_page':
            subpage_ids.append(block_id)

        # The mention object can be anywhere in the list of rich_text objects, so we
        # need to look through all of them.
        elif block.get('type') in ['table_row', 'paragraph']:
            texts = []

            # We need to search inside blocks AND the table contents.
            # table_row blocks are included with the rest of the blocks, but the object structure
            # is different so we need to handle them separately.
            if block.get('type') == 'table_row':
                for cell in block.get('table_row', {}).get('cells', []):
                    texts.extend(cell)
            else: # block.get('type') == 'paragraph'
                texts = block.get('paragraph', {}).get('rich_text', [])

            for text in texts:
                if text.get('mention', {}) and text.get('mention', {}).get('page', {}):
                    mentioned_page_id = text.get('mention', {}).get('page', {}).get('id', '')
                    subpage_ids.append(mentioned_page_id)

    # If we have subpages fetch them.
    if subpage_ids:
        for subpageid in subpage_ids:

            # If we already fetched this page don't fetch again AND don't count it as a subpage.
            # This will prevent a page from appearing at multiple places in the page tree. The
            # downside is that it's not determinstic which page will be fetched first if pages are
            # fetched concurrently, and even if they're not it's not clear which page will be the
            # parent page if it's mentoned from multiple places. This is the best we can do without
            # a way to reliably detect true subpages.
            if subpageid in networking.get_fetched_pageids():
                continue

            subpage = networking.fetch_page(subpageid)
            fetched_sub_page = get_page(subpage, notion_page)
            subpages.append(fetched_sub_page)

    return subpages


def get_column_blocks(block):
    all_column_blocks = []
    column_list_block_id = block.get('id', '')

    # Get the column children
    column_list_blocks = networking.fetch_all_blocks(column_list_block_id)
    for column in column_list_blocks:
        column_id = column.get('id', '')
        column_blocks = networking.fetch_all_blocks(column_id)
        all_column_blocks.extend(column_blocks)

    return all_column_blocks
