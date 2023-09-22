""" Code for interacting with Notion.
"""
# pylint: disable=import-error

# Standard library imports
import concurrent.futures
import copy
import logging
import pathlib
import re
import secrets
import shutil
import traceback

# External module imports

# Local imports
from . import files
from . import htmltools
from . import networking
from . import utils


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


logger = logging.getLogger('notion2html')
logger.setLevel(logging.WARNING)
logger.propagate = True


class NotionResult:
    """Represents the result of fetching data from Notion.
    Contains NotionPage and NotionDatabase objects.
    """

    def __init__(self):

        self._top_level_page = None
        self._all_pages = {}
        self._all_databases = {}
        self._errors = {}

        # This will be a pathlib.Path object, not a string.
        self._file_path = None


    def _add_page(self, page):
        """page: a NotionPage object."""

        # If we already have this page, don't add it again.
        if page.id in self._all_pages:
            return

        self._all_pages[page.id] = page

        # Walk the page tree and add all subpages to the list of all pages.
        if page.has_subpages():
            subpages = utils.flatten_notion_page_tree([page])
            for subpage in subpages:
                self._all_pages[subpage.id] = subpage

        # Walk the list of pages and add all databases to the list of all databases.
        #
        # TODO: This doesn't work for databases that are embedded in pages of these databases.
        for page in list(self._all_pages.values()):
            if page.has_databases():
                for database in page.get_all_databases():
                    self._add_database(database)

    def _add_database(self, database):
        """database: a NotionDatabase object."""
        self._all_databases[database.id] = database
        for page in database.get_all_pages():
            self._add_page(page)


    def _get_databases(self):
        return list(self._all_databases.values())


    def _set_file_path(self, file_path):
        self._file_path = file_path


    def get_pages(self):
        return list(self._all_pages.values())


    def get_errors(self):
        return list(self._errors.values())


    def get_file_path(self):
        return self._file_path


    def get_item_for_id(self, item_id):
        """Returns a NotionPage object or error for the given id.
        Specifically does not search databases objects because they are
        not exposed publicly.
        """

        if item_id in self._all_pages:
            return self._all_pages[item_id]

        if item_id in self._errors:
            return self._errors[item_id]

        raise ValueError(f"Item with id {item_id} not found.")


class NotionDatabase:
    """Represents a Notion database.
    """

    def __init__(self, database_id):
        self.id = database_id

        # List of title blocks that make up the database title.
        self.title_blocks = []
        self.title = ""

        # List of NotionPage objects that are top-level database items.
        self.top_level_pages = []

        # List of all NotionPage objects in the database, including sub-pages of database
        # items.
        self.all_pages = []

        # Dict that is decoded JSON of the full database properties object
        # we got from Notion.
        self.properties = {}


    def set_title_blocks(self, title_blocks):
        self.title_blocks = title_blocks
        self.title = htmltools.convert_rich_text_to_string(title_blocks)


    def set_properties(self, properties):
        self.properties = properties


    def add_pages(self, new_pages):
        """Input: a list of NotionPage objects.

        Adds this list to the existing list of pages."""

        self.top_level_pages.extend(new_pages)

        # Regenerate the flat list of all pages everytime new pages are added.
        self.all_pages = utils.flatten_notion_page_tree(self.top_level_pages)


    def get_all_pages(self):
        return self.all_pages


class NotionPage:
    """Represents a Notion page.
    """

    def __init__(self, page_id):

        ##### Page data
        self.id = page_id
        self.title = ""
        self.blocks = []

        # Dict that is decoded JSON of the full page properties object from Notion.
        self.properties = {}

        # Dict - keys are block ids as strings, value is the entire block JSON.
        self.blocks_by_id = {}

        # Dict - key is the block id of table block, value is a list of table row blocks
        self.tables_and_rows = {}

        self.errors = []

        ##### Parent pages and Sub pages
        self.subpages = []
        self.subpage_ids = []
        self.parent_page_title = ""
        self.parent_page_id = ""

        ##### HTML related
        self.soup = None
        self.original_html = ""
        self.updated_html = ""

        # Dict - key is the page id, value is the placeholder text for the page link.
        self.page_links = {}

        ##### Attachments
        # Dict - key is the full attachment URL, value is an Attachment object.
        self.attachments = {}

        ##### Databases
        # List of NotionDatabase objects that are embedded in the page content.
        self.databases = []

        ##### Users
        # All possible users who could be mentioned in this page.
        self.all_users = networking.USERS_FROM_NOTION


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


    def has_subpages(self):
        return len(self.subpages) != 0


    def has_databases(self):
        return len(self.databases) != 0


    def add_subpage(self, subpage):
        """Add a single subpage that's a NotionPage object.
        """
        self.subpages.append(subpage)
        self.subpage_ids.append(subpage.id)


    def add_parent_page_title(self, parent_page_title):
        self.parent_page_title = parent_page_title


    def add_parent_page_id(self, parent_page_id):
        self.parent_page_id = parent_page_id


    def set_html(self, html):
        self.original_html = html

        # Find all page link placeholders
        pattern = r'~~~PageMention:::([A-Za-z0-9-]+):::(.+?)~~~'
        matches = re.finditer(pattern, html)
        self.page_links = {match.group(1): match.group(0) for match in matches}

        self.updated_html = copy.copy(html)


    def get_original_html(self):
        return self.original_html


    def get_updated_html(self):
        return self.updated_html


    def set_all_link_paths(self, path):
        """path: a string representing the relative path that html pages
        will live in.
        """

        if self.page_links:
            # Replace all page link placeholders with the correct link.
            for page_id, placeholder_text in self.page_links.items():

                link_path = f"{path}{page_id}.html"
                link_text = placeholder_text.split(":::")[2].rstrip("~~~")

                page_link_replacement_html = htmltools.create_link_text(link_path, link_text)
                self.updated_html = self.updated_html.replace(placeholder_text, page_link_replacement_html)


    def set_attachment_paths_and_copy(self, link_path, directory_path):

        if self.attachments:
            for attachment in self.attachments.values():
                filename = attachment.path.name
                attachment_directory_name = secrets.token_urlsafe(10)

                full_link_path = f"{link_path}/{attachment_directory_name}/{filename}"
                copy_destination_directory = pathlib.Path(directory_path).joinpath(attachment_directory_name)
                copy_destination_directory.mkdir(exist_ok=False, parents=True)

                # Create new link tags and update all references in the HTML
                if attachment.is_image:
                    attachment_link_replacement_html = htmltools.create_image_text(full_link_path)
                else:
                    attachment_link_replacement_html = htmltools.create_link_text(full_link_path, filename)

                self.updated_html = self.updated_html.replace(attachment.placeholder_text,
                                                              attachment_link_replacement_html)

                # Copy the attachment to the new directory
                shutil.copy(attachment.path, copy_destination_directory)


    def copy_all_attachments_to_path(self, directory):
        """directory: a pathlib.Path object, not a string."""

        logger.debug(f"Copying attachments to directory: {directory}")
        if self.attachments:
            for attachment in self.get_attachments():
                files.copy_file(attachment.path, directory)


    def add_soup(self, soup):
        self.soup = soup


    def add_attachment(self, attachment):
        self.attachments[attachment.url] = attachment


    def has_attachment(self):
        return len(self.attachments) != 0


    def get_attachments(self):
        return list(self.attachments.values())


    def add_tableid_and_rows(self, table_id, table_rows):
        self.tables_and_rows[table_id] = table_rows


    def add_database(self, database):
        logger.debug(f"Adding database to page: {self.id}, {self.title} -- Database: {database.id}, {database.title}")
        self.databases.append(database)
        logger.debug(f"databases is now: {self.databases} for page: {self.id}, {self.title}")


    def get_all_databases(self):

        # Don't need to get all databases in the database's page tree here; that's
        # handled elsewhere.

        # for subpage in self.subpages:
        #     self.databases.extend(subpage.get_all_databases())
        # return self.databases

        return self.databases


    def get_username_for_user_id(self, user_id):

        if user_id in self.all_users:
            return self.all_users[user_id]

        # If we don't have the user in our list of users, return an empty string.
        return ""


    def has_errors(self):
        return len(self.errors) != 0


    def get_errors(self):
        return self.errors


    def add_error(self, error):
        logger.debug(f"ERROR ADDED: Page ID: {self.id} -- Title: {self.title} -- Error: {error}")
        self.errors.append(error)



class Attachment:
    """File attachment data. Includes images, PDFs, etc."""

    def __init__(self, url, block_type, placeholder_text, full_path_to_file):
        self.url = url
        self.block_type = block_type
        self.placeholder_text = placeholder_text

        # full_path_to_file is a pathlib.Path object, not a string.
        self.path = full_path_to_file

        if self.block_type == "image":
            self.is_image = True
        else:
            self.is_image = False


def startup(token, file_path):
    """Setup code for a single run."""

    networking.set_notion_token(token)
    networking.create_fetched_object()

    if file_path:
        files.set_path_to_run_directory(file_path)
    else:
        files.set_path_to_run_directory()

    networking.get_notion_users()


def teardown():
    """Cleanup code to run after a single run is complete."""

    # Once done fetching pages, clear the list of fetched page IDs so it's
    # not carried forward if we run this function again before the calling
    # code exits.
    networking.clear_fetched_objects()
    networking.clear_notion_token()
    networking.clear_notion_users()
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
    result._set_file_path(files.get_path_to_run_directory())

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
        result._add_page(page)
        for found_db in page.get_all_databases():
            result._add_database(found_db)

    if database:
        result._add_database(database)
        logger.debug(f"Added database to result: {database.title} -- {database.id}")

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
    database = NotionDatabase(database_id)

    # Record the database id we're fetching so we can avoid fetching it again
    # if it's mentioned from another page. This is protected
    # by a lock so we are basically doing a test-and-set. If this returns true
    # we don't have this page yet so we continue fetching. If it returns false we already
    # have the page so we return None.
    if networking.add_object_to_fetched(database) is False:
        logger.debug(f"Already fetched Database. Returning None. DB ID: {database.id}")
        return None

    logger.debug(f"Don't have Database yet. Continuing with fetch. DB ID: {database.id}")

    all_db_info = networking.fetch_database_info(database_id)
    database.set_properties(all_db_info)
    database.set_title_blocks(all_db_info.get('title', []))

    pages_info = networking.fetch_pages_info_from_database(database_id)
    logger.debug(f"Database id: {database.id} Title: {database.title} "
                 f"Total number of database pages found: {len(pages_info)}")
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


def get_page(page_properties, parent_page=None):

    page_id = utils.find_page_id(page_properties)
    notion_page = NotionPage(page_id)

    # Record the page id we're fetching so we can avoid fetching it again
    # if it's a subpage of another page, or mentioned again. This is protected
    # by a lock so we are basically doing a test-and-set. If this returns true
    # we don't have this page yet so we continue fetching. If it returns false we already
    # have the page so we return None.
    if networking.add_object_to_fetched(notion_page) is False:
        logger.debug(f"Already fetched page. Returning None. ID: {notion_page.id} "
                     f"Title: {notion_page.title}")
        return None

    logger.debug(f"Don't have page yet. Continuing with fetch. ID: {notion_page.id} "
                     f"Title: {notion_page.title}")

    notion_page.set_title(utils.find_page_title(page_properties))
    notion_page.set_properties(page_properties)
    notion_page.set_blocks(networking.fetch_all_blocks(notion_page.id))

    # If we have a parent page add the parent ID and title to the current page.
    if parent_page:
        notion_page.add_parent_page_title(parent_page.title)
        notion_page.add_parent_page_id(parent_page.id)

    # Handle special cases including attachments.
    handle_page_special_cases(notion_page)

    # Do HTML conversion.
    htmltools.convert_page_to_html(notion_page)

    # Recursively fetch all subpages or subdatabases.
    subpages_or_subdatabases = get_subpages_or_subdatabases(notion_page)
    for item in subpages_or_subdatabases:
        logger.debug(f"Adding this subpage or subdatabase: {item.id}, {item.title}")

        if isinstance(item, NotionPage):
            notion_page.add_subpage(item)
            logger.debug(f"ADDED THIS SUBPAGE: {item.id}, {item.title}")

        if isinstance(item, NotionDatabase):
            notion_page.add_database(item)
            logger.debug(f"ADDED THIS DATABASE: {item.id}, {item.title}")

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
        # if block_type == 'column_list':
        #     column_blocks = get_column_blocks(block)
        #     notion_page.blocks = notion_page.blocks[:i] + column_blocks + notion_page.blocks[i:]

        # Handle databases embedded in the page content.
        if block_type == "child_database":
            database = get_database_from_notion(block_id)
            notion_page.add_database(database)

        # Handle attachments.
        if block_type in blocks_with_attachments:
            attachment_type = block.get(block_type, {}).get('type', '')

            # Only to download and handle Notion-hosted attachments. External "attachments" are
            # really just embedded links and they will be handled as such in HTML processing.
            if attachment_type == 'file':
                url = utils.find_url_for_block(block, block_type)
                filename = files.extract_filename_from_url(url)
                handle_attachments(notion_page, block_type, url, filename)

    # Handle attachments in properties
    all_files_properties = htmltools.extract_files_properties_only(notion_page)
    if all_files_properties:
        logger.debug(f"files_properties: {all_files_properties}")

        for single_property_files in all_files_properties:
            for file_info in single_property_files.get('files', []):
                url = file_info.get('file', {}).get('url', '')
                filename = files.extract_filename_from_url(url)
                handle_attachments(notion_page, 'from_property', url, filename)


def handle_attachments(notion_page, block_type, url, filename):

    # full_file_path is a pathlib.Path object, not a string.
    try:
        full_file_path = networking.download_file_and_save(url, filename)
    except RuntimeError as exc:
        error_message = (f"Exception downloading attachment. Skipping this attachment. {url} -- {filename} -- {exc} -- {traceback.format_exc()}")
        logger.debug(error_message)
        notion_page.add_error(error_message)
        full_file_path = None

    if full_file_path:
                # Get placeholder text and save attachment info on the file object
        placeholder_text =  htmltools.attachment_link_text()

        attachment = Attachment(url, block_type, placeholder_text, full_file_path)
        notion_page.add_attachment(attachment)


def get_subpages_or_subdatabases(notion_page):
    """I originally tried to detect only true subpages as opposed to page mentions (which are links
    to pages outside the page tree of the current page). But ultimately I couldn't figure out how to
    reliably detect true subpages.

    So instead now just detect all page mentions and assume they're subpages, but also keep track of
    the pages that have already been fetched and deduplicate pages before returning the ultimate
    set of results. (Note that deduplication happens higher up the call stack, not down here.) This
    will prevent fetch loops, and avoid missing pages.
    """

    sub_page_ids = []
    sub_database_ids = []
    sub_pages_or_sub_databases = []

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
            sub_page_ids.append(block_id)

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
                # This detects mentioned pages
                if text.get('mention', {}) and text.get('mention', {}).get('page', {}):
                    mentioned_page_id = text.get('mention', {}).get('page', {}).get('id', '')
                    sub_page_ids.append(mentioned_page_id)

                # Thid detects mentioned databases
                if text.get('mention', {}) and text.get('mention', {}).get('database', {}):
                    mentioned_database_id = text.get('mention', {}).get('database', {}).get('id', '')
                    sub_database_ids.append(mentioned_database_id)

    # If we have subpages fetch them.
    if sub_page_ids:
        logger.debug(f"Found sub-PAGES for page: {notion_page.id} -- {notion_page.title} -- "
                     f"Sub-page IDs: {sub_page_ids}")
        for subpageid in sub_page_ids:
            subpage = networking.fetch_page(subpageid)
            fetched_sub_page = get_page(subpage, notion_page)
            if fetched_sub_page:
                sub_pages_or_sub_databases.append(fetched_sub_page)
                logger.debug(f"Page appended -- Processing subpage id: {subpageid} "
                             f"-- for parent page: {notion_page.id}")
            else:
                logger.debug(f"PAGE NOT APPENDED -- Processing subpage id: {subpageid} "
                             f"-- for parent page: {notion_page.id}")

    if sub_database_ids:
        logger.debug(f"Found sub-DATABASES for page: {notion_page.id} -- {notion_page.title} "
                     f"Sub-database IDs: {sub_database_ids}")
        for sub_db_id in sub_database_ids:
            db = get_database_from_notion(sub_db_id)
            if db:
                sub_pages_or_sub_databases.append(db)
                logger.debug(f"Database appended -- Processing database id: {sub_db_id} "
                             f"-- for parent page: {notion_page.id}")
            else:
                logger.debug(f"DATABASE NOT APPENDED -- Processing database id: {sub_db_id} "
                             f"-- for parent page: {notion_page.id}")

    return sub_pages_or_sub_databases


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
