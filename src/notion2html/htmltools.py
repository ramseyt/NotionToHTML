""" Code for converting Notion page data to html as well as general HTML formatting.
"""

# Standard library imports
from datetime import datetime
import logging
import secrets
import traceback

# External module imports
from bs4 import BeautifulSoup, NavigableString

# Local imports


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


logger = logging.getLogger('notion2html')
logger.setLevel(logging.WARNING)


########################### Formatting

def page_link_text(page_title, page_id):
    """The regular expressions in method add_html() on NotionPage MUST be updated
    if this text is changed."""
    return f"~~~PageMention:::{page_id}:::{page_title}~~~"


def attachment_link_text():
    return f"~~~Attachment:{secrets.token_urlsafe(10)}~~~"


def database_placeholder_text(database_placeholder):
    return f"~~~Embedded Database was here: {database_placeholder}~~~"


def block_types_with_attachments():
    return ['image', 'video', 'audio', 'file', 'pdf']


def convert_to_local(iso_time_str):
    """Converts an ISO 8601 timestamp string to a local datetime object.
    """

    utc_time = datetime.fromisoformat(iso_time_str.replace("Z", "+00:00"))
    local_time = utc_time.astimezone()
    return local_time


def create_link_text(link_url, link_text):
    """Creates a link tag with the given URL and text.
    """

    link_tag = BeautifulSoup(features="html.parser").new_tag("a", href=link_url)
    link_tag.string = link_text
    return str(link_tag)


def create_image_text(image_url):
    """Creates a image tag with the given URL and text.
    """

    img_tag = BeautifulSoup(features="html.parser").new_tag("img")
    img_tag['src'] = image_url
    return str(img_tag)


########################### Converting Notion page data to html

def convert_page_to_html(notion_page):

    # Base HTML structure with doctype, head, title, and body tags
    base_html = f"<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>{notion_page.title}</title></head><body></body></html>"

    soup = BeautifulSoup(base_html, features="html.parser")
    body_tag = soup.body

    try:
        page_soup = extract_page_properties(notion_page, BeautifulSoup(features="html.parser"))
        body_tag.append(page_soup)
    except Exception as exc:
        error_message = ("Exception hit while constructing property HTML for page. Skipping page.\n"
                        f"Page: {notion_page}\n"
                        f"Exception: {exc}\n"
                        f"Traceback: {traceback.format_exc()}")
        logger.debug(error_message)
        notion_page.add_error(error_message)
        return notion_page

    p_tag = soup.new_tag("p")
    body_tag.append(p_tag)

    try:
        page_soup = flatten_blocks_into_html(notion_page, notion_page.blocks,
                                             BeautifulSoup(features="html.parser"))
        body_tag.append(page_soup)
    except Exception as exc:
        error_message = ("Exception hit while constructing page HTML. Skipping page:\n"
                        f"Page: {notion_page}\n"
                        f"Exception: {exc}\n"
                        f"Traceback: {traceback.format_exc()}")
        logger.debug(error_message)
        notion_page.add_error(error_message)
        return notion_page

    notion_page.add_soup(soup)
    notion_page.set_html(str(soup))

    return notion_page


def convert_rich_text_to_string(rich_text):

    if not rich_text:
        return ""

    soup = BeautifulSoup(features="html.parser")
    for text in rich_text:
        soup.append(_handle_formatting(text, soup))

    return str(soup)


def flatten_blocks_into_html(notion_page, blocks, soup):

    handlers = {
        'paragraph': _paragraph,
        'heading_1': _heading_1,
        'heading_2': _heading_2,
        'heading_3': _heading_3,
        'bulleted_list_item': _list_item,
        'numbered_list_item': _list_item,
        'to_do': _list_item,
        'toggle': _toggle,
        'child_page': _child_page,
        'image': _image,
        'video': _video,
        'audio': _audio,
        'embed': _embed,
        'code': _code,
        'equation': _equation,
        'callout': _callout,
        'quote': _quote,
        'divider': _divider,
        'table_of_contents': _table_of_contents,
        'tweet': _tweet,
        'gist': _gist,
        'drive': _drive,
        'figma': _figma,
        'file': _file,
        'pdf': _pdf,
        'bookmark': _bookmark,
        'sub_sub_header': _sub_sub_header,
        'sub_header': _sub_header,
        'table': _table,
        'table_row': _pass_handler,
        'column': _pass_handler, # Columns are already handled
        'column_list': _pass_handler, # Columns are already handled
        'breadcrumb': _pass_handler,
        'synced_block': _synced_block,
        'child_database': _child_database
    }

    for block in blocks:
        block_type = block.get('type')
        handler = handlers.get(block_type)

        if handler is None:
            notion_page.add_error(f"!!!Unknown block type! Skipping!!!: {block_type} -- Raw Block: {block}")
            continue

        # Some block types require additional arguments.
        if block_type in block_types_with_attachments():
            handler(block, soup, notion_page)

        elif block_type in ["bulleted_list_item", "numbered_list_item", "to_do", "child_page"]:
            handler(block, soup, notion_page)

        elif block_type in ["table", "synced_block"]:
            handler(block, soup, notion_page)

        else:
            handler(block, soup)

    return soup


######## Start handling of text formatting

def _handle_formatting(text, soup):
    """Doesn't handle \n line breaks. Not clear to me if we should."""

    if text.get('type', '') == 'equation':
        new_tag = _handle_equation_format(text, soup)
    else:
        new_tag = _handle_annotations_format(text, soup)

    new_tag = _handle_link_format(text, soup, new_tag)
    new_tag = _handle_page_mention(text, soup, new_tag)
    new_tag = _handle_date_mention(text, soup, new_tag)
    new_tag = _handle_person_mention(text, soup, new_tag)

    return new_tag


def _handle_equation_format(text, soup):
    content = text.get('equation', {}).get('expression', '')
    new_tag = soup.new_string(content)
    return new_tag


def _handle_annotations_format(text, soup):
    content = text.get('text', {}).get('content', '')
    new_tag = soup.new_string(content)
    annotation = text.get('annotations', {})
    new_tag = _annotations(annotation, new_tag, soup)
    return new_tag


def _handle_link_format(text, soup, new_tag):
    if text.get('text', {}).get('link', {}):
        url = text.get('text', {}).get('link', {}).get('url', '')
        temp_tag = soup.new_tag("a", href=url)
        temp_tag.append(new_tag)
        new_tag = temp_tag
    return new_tag


def _handle_page_mention(text, soup, new_tag):
    mention = text.get('mention', {}).get('type', '')
    if mention and mention == 'page':
        new_tag = _process_page_mention(text, soup, new_tag)
    return new_tag


def _handle_date_mention(text, soup, new_tag):
    mention = text.get('mention', {}).get('type', '')
    if mention and mention == 'date':
        new_tag = _process_date_mention(text, soup, new_tag)
    return new_tag


def _process_date_mention(text, soup, new_tag):
    date_info = text.get('mention', {}).get('date', {})
    start_date = date_info.get('start', '')
    end_date = date_info.get('end', '')
    time_zone = date_info.get('time_zone', '')

    date = ""
    if end_date and time_zone:
        date += f"{start_date} to {end_date}, {time_zone}"
    elif end_date:
        date += f"{start_date} to {end_date}"
    elif start_date and time_zone:
        date += f"{start_date}, {time_zone}"
    elif start_date:
        date += f"{start_date}"
    else:
        date += "Unknown date"

    temp_tag = soup.new_string(date)
    if new_tag:
        temp_tag.append(new_tag)
        new_tag = temp_tag
    else:
        new_tag = temp_tag

    return new_tag


def _process_page_mention(text, soup, new_tag):
    title_of_mentioned_page = text.get('plain_text')
    id_of_mentioned_page = text.get('mention', {}).get('page', {}).get('id', '')

    # There's a bug in Notion's API where page titles for page mentions
    # located INSIDE of table cells are returned as "Untitled" instead of
    # the actual page title. Since we have the page ID of the mention, the code
    # below will fish out the mentioned page's title from the list of all NotionPage
    # objects.
    #
    # But for now we comment out the code as we used to plumb all notion page info down
    # to here but we aren't for now to simply things as the code above changes.

    # if page_title == "Untitled" and notion_pages:
    #     page_id = text.get('mention', {}).get('page', {}).get('id', '')

    #     result = [page.title for page in notion_pages if page.id == page_id]

    #     if result and result[0]:
    #         page_title = result[0]

    #     else:
    #         page_title = "Untitled"

    # If we don't hit the bug above then it's straightforward, just use
    # the page title returned by the API.
    logger.debug(f"Page mention text: {text}")
    temp_tag = soup.new_string(page_link_text(title_of_mentioned_page, id_of_mentioned_page))

    if new_tag:
        temp_tag.append(new_tag)
        new_tag = temp_tag
    else:
        new_tag = temp_tag

    return new_tag


def _handle_person_mention(text, soup, new_tag):
    mention_type = text.get('mention', {}).get('type', '')

    if mention_type and mention_type == 'user':
        user_name = text.get('plain_text', '')

        temp_tag = soup.new_string(user_name)
        if new_tag:
            temp_tag.append(new_tag)
            new_tag = temp_tag
        else:
            new_tag = temp_tag

    return new_tag


def _annotations(annotation, new_tag, soup):
    if annotation.get('bold', False):
        temp_tag = soup.new_tag("b")
        temp_tag.append(new_tag)
        new_tag = temp_tag

    if annotation.get('italic', False):
        temp_tag = soup.new_tag("i")
        temp_tag.append(new_tag)
        new_tag = temp_tag

    if annotation.get('strikethrough', False):
        temp_tag = soup.new_tag("s")
        temp_tag.append(new_tag)
        new_tag = temp_tag

    if annotation.get('underline', False):
        temp_tag = soup.new_tag("u")
        temp_tag.append(new_tag)
        new_tag = temp_tag

    if annotation.get('code', False):
        temp_tag = soup.new_tag("code")
        temp_tag.append(new_tag)
        new_tag = temp_tag

    return new_tag

######## End handling of text formatting

def _paragraph(block, soup):
    texts = block.get('paragraph', {}).get('rich_text', [])

    # Create a new paragraph tag
    para_tag = soup.new_tag("p")

    # Handle formatting for all elements in the "rich_text" list for the paragraph
    for text in texts:
        para_tag.append(_handle_formatting(text, soup))

    # Append the paragraph tag and a line break to the soup object
    soup.append(para_tag)


def _heading_1(block, soup):
    texts = block.get('heading_1', {}).get('rich_text', [])
    heading = " ".join(text.get('plain_text') for text in texts)

    new_tag = soup.new_tag("h1")
    new_tag.string = heading
    soup.append(new_tag)


def _heading_2(block, soup):
    texts = block.get('heading_2', {}).get('rich_text', [])
    heading = " ".join(text.get('plain_text') for text in texts)

    new_tag = soup.new_tag("h2")
    new_tag.string = heading
    soup.append(new_tag)


def _heading_3(block, soup):
    texts = block.get('heading_3', {}).get('rich_text', [])
    heading = " ".join(text.get('plain_text') for text in texts)

    new_tag = soup.new_tag("h3")
    new_tag.string = heading
    soup.append(new_tag)


######## Start handling of List items

def _list_item(block, soup, notion_page):
    # Create a new "li" tag
    li_tag = _create_list_item_tag(block, soup)

    # Check if this block has any children
    if block['has_children']:
        # Process child blocks
        li_tag = _process_child_blocks(block, li_tag, soup, notion_page)

    # Process parent block
    _process_parent_block(block, li_tag, soup, notion_page)

    return li_tag


def _create_list_item_tag(block, soup):
    li_tag = soup.new_tag("li")

    # Handle formatting for all elements in the "rich_text" list for the item
    item_type = block['type']
    texts = block.get(item_type, {}).get('rich_text', [])

    # If the block type is "to_do", create a checkbox input tag
    if item_type == "to_do":
        checkbox = soup.new_tag("input")
        checkbox["type"] = "checkbox"

        # If there's a 'checked' attribute in the block, set it.
        # NOTE: This is based on assumption. Modify as necessary if the block structure is
        # different.
        logger.debug(f"To Do Block: {block}")
        if block.get(item_type, {}).get('checked', False):
            checkbox["checked"] = "checked"

        li_tag.append(checkbox)

    for text in texts:
        li_tag.append(_handle_formatting(text, soup))

    return li_tag



def _process_child_blocks(block, li_tag, soup, notion_page):
    # Create a new "ul" or "ol" tag for the children based on the block type
    item_type = block['type']
    list_tag = soup.new_tag("ul") if (item_type == "bulleted_list_item" or item_type == "to_do") \
                                      else soup.new_tag("ol")

    # Get the child blocks for this block
    current_block_id = block.get('id', '')
    child_block_ids = [child_block.get('id', '') for child_block in notion_page.blocks \
                       if child_block.get('parent', {}).get('block_id', '') == current_block_id]

    # Recursively build the HTML for each child block
    for child_block_id in child_block_ids:
        child_html = _list_item(notion_page.get_block_for_block_id(child_block_id), soup, notion_page)

        # Add the child HTML to the list tag
        list_tag.append(child_html)

    # Append the list tag to the li tag
    li_tag.append(list_tag)

    return li_tag


def _process_parent_block(block, li_tag, soup, notion_page):
    # Check the parent of this block
    parent_block_id = block.get('parent', {}).get('block_id', '')
    if parent_block_id:
        parent_block = notion_page.get_block_for_block_id(parent_block_id)
        if parent_block and parent_block['type'] in ['bulleted_list_item', 'numbered_list_item', 'to_do']:
            # If the parent block is also a list item, we find the parent's
            # "li" tag and append this "li" tag to it
            parent_li_tag = soup.find('li', {'data-block-id': parent_block_id})
            if parent_li_tag:
                parent_li_tag.find('ul' if (block['type'] == "bulleted_list_item" or block['type'] == "to_do") \
                                            else 'ol').append(li_tag)
        else:
            # If the parent block is not a list item, we append this
            # "li" tag directly to the soup object
            list_tag = soup.new_tag("ul" if (block['type'] == "bulleted_list_item" or block['type'] == "to_do") \
                                    else 'ol')
            list_tag.append(li_tag)
            soup.append(list_tag)
    else:
        # If this block doesn't have a parent, we append it directly to the soup object
        list_tag = soup.new_tag("ul" if (block['type'] == "bulleted_list_item" or block['type'] == "to_do") \
                                else 'ol')
        list_tag.append(li_tag)
        soup.append(list_tag)

######## End handling of List items


def _toggle(block, soup):
    # Unfortunately the toggle block doesn't include the content that's actually inside
    # the toggle. Nor does it include any pointers to the blocks that are inside the toggle.
    # So just create the toggle with the title. Content blocks will appear immediately after
    # the toggle but I think that's the best we can do without any more information?

    logger.debug(f"Toggle block: {block}")
    texts = block.get('toggle', {}).get('rich_text', [])

    details_tag = soup.new_tag("details")
    summary_tag = soup.new_tag("summary")

    for text in texts:
        summary_tag.append(_handle_formatting(text, soup))

    details_tag.append(summary_tag)
    soup.append(details_tag)


def _child_page(block, soup, notion_page):

    logger.debug(f"!!!!! Child page block found: {block}")

    page_id = block.get('id', '')
    page_title = block.get('child_page', {}).get('title', '')

    new_tag = soup.new_tag("p")
    new_tag.string = page_link_text(page_title, page_id)
    soup.append(new_tag)


def _embed(block, soup):
    embed_url = block.get('embed', {}).get('url')
    new_tag = soup.new_tag("a", href=embed_url)
    new_tag.string = embed_url
    soup.append(new_tag)


def _code(block, soup):
    texts = block.get('code', {}).get('rich_text', [])
    code = " ".join(text.get('plain_text') for text in texts)

    pre_tag = soup.new_tag("pre")
    code_tag = soup.new_tag("code")
    code_tag.string = code
    pre_tag.append(code_tag)
    soup.append(pre_tag)


def _equation(block, soup):
    expression = block.get('equation', {}).get('expression', '')

    new_tag = soup.new_tag("p")
    new_tag.string = expression
    soup.append(new_tag)


def _callout(block, soup):
    texts = block.get('callout', {}).get('rich_text', [])

    new_tag = soup.new_tag("div", style='border: 1px solid; padding: 10px; margin: 10px;')
    for text in texts:
        new_tag.append(_handle_formatting(text, soup))
    soup.append(new_tag)


def _quote(block, soup):
    texts = block.get('quote', {}).get('rich_text', [])

    # Append "Quote:<br>" to the start of a quote
    new_tag = soup.new_tag("p")
    new_tag.append("Quote:")
    #new_tag.append(soup.new_tag("br"))

    #new_tag.append(soup.new_tag("blockquote"))
    for text in texts:
        new_tag.append(_handle_formatting(text, soup))
    soup.append(new_tag)


def _divider(_, soup):
    new_tag = soup.new_tag("hr")
    soup.append(new_tag)


def _table_of_contents(_, soup):
    new_tag = soup.new_tag("p")
    new_tag.string = "Table of Contents was here before"
    soup.append(new_tag)


def _tweet(block, soup):
    tweet_url = block.get('tweet', {}).get('url')
    new_tag = soup.new_tag("a", href=tweet_url)
    new_tag.string = tweet_url
    soup.append(new_tag)


def _gist(block, soup):
    gist_url = block.get('gist', {}).get('url')
    new_tag = soup.new_tag("a", href=gist_url)
    new_tag.string = "Gist"
    soup.append(new_tag)


def _drive(block, soup):
    drive_url = block.get('drive', {}).get('url')
    new_tag = soup.new_tag("a", href=drive_url)
    new_tag.string = "Google Drive Document"
    soup.append(new_tag)


def _figma(block, soup):
    figma_url = block.get('figma', {}).get('url')
    new_tag = soup.new_tag("a", href=figma_url)
    new_tag.string = "Figma"
    soup.append(new_tag)


def _bookmark(block, soup):
    bookmark_url = block.get('bookmark', {}).get('url')
    bookmark_caption = block.get('bookmark', {}).get('caption')

    if not bookmark_caption:
        bookmark_caption = bookmark_url

    new_tag = soup.new_tag("a", href=bookmark_url)
    new_tag.string = bookmark_caption
    soup.append(new_tag)


def _sub_sub_header(block, soup):
    texts = block.get('sub_sub_header', {}).get('rich_text', [])
    heading = " ".join(text.get('plain_text') for text in texts)

    new_tag = soup.new_tag("h4")
    new_tag.string = heading
    soup.append(new_tag)


def _sub_header(block, soup):
    texts = block.get('sub_header', {}).get('rich_text', [])
    heading = " ".join(text.get('plain_text') for text in texts)

    new_tag = soup.new_tag("h3")
    new_tag.string = heading
    soup.append(new_tag)


def _table(block, soup, notion_page):

    # Create new table tag
    table_tag = soup.new_tag("table")

    # Retrieve table information
    table_id = block.get('id', '')
    table_info = block.get('table', {})
    has_column_header = table_info.get('has_column_header', False)
    has_row_header = table_info.get('has_row_header', False)

    # Get the table rows
    rows = notion_page.tables_and_rows[table_id]

    for i, row in enumerate(rows):
        # Create new row tag
        row_tag = soup.new_tag("tr")

        cells = row.get('table_row', {}).get('cells', [])
        for j, cell in enumerate(cells):
            # Determine if the cell is a header
            is_header = (i == 0 and has_column_header) or (j == 0 and has_row_header)

            # Choose the appropriate tag
            cell_tag_name = "th" if is_header else "td"
            cell_tag = soup.new_tag(cell_tag_name)

            # Fill the cell with content
            for text in cell:
                cell_tag.append(_handle_formatting(text, soup))

            # Add the cell to the row
            row_tag.append(cell_tag)

        # Add the row to the table
        table_tag.append(row_tag)

    # Add the table to the soup
    soup.append(table_tag)


def _synced_block(block, soup, notion_page):

    synced_blocks = block.get('synced_block', {}).get('children', [])
    flatten_blocks_into_html(notion_page, synced_blocks, soup)


def _child_database(block, soup):

    # Create a new paragraph tag
    para_tag = soup.new_tag("p")

    # Get database name and title
    # database_id = block.get('id', '')
    database_title = block.get('child_database', {}).get('title', '')

    # Append database name
    text = soup.new_string(database_placeholder_text(database_title))
    para_tag.append(text)

    # Append the paragraph tag to the soup object
    soup.append(para_tag)


def _pass_handler(_, __):
    pass


######## Block types with attachments below

def _file(block, soup, notion_page):
    url_type = block.get('file', {}).get('type', '')
    file_url = block.get('file', {}).get(url_type, {}).get('url', '')

    if url_type == 'external':
        new_tag = soup.new_tag("a", href=file_url)
        new_tag.string = file_url

    else:
        new_tag = NavigableString(notion_page.get_placeholder_text_for_url(file_url))

    soup.append(new_tag)


def _pdf(block, soup, notion_page):
    url_type = block.get('pdf', {}).get('type', '')
    pdf_url = block.get('pdf', {}).get(url_type, {}).get('url', '')

    if url_type == 'external':
        new_tag = soup.new_tag("a", href=pdf_url)
        new_tag.string = pdf_url

    else:
        new_tag = NavigableString(notion_page.get_placeholder_text_for_url(pdf_url))

    soup.append(new_tag)


def _image(block, soup, notion_page):
    url_type = block.get('image', {}).get('type', '')
    image_url = block.get('image', {}).get(url_type, {}).get('url', '')

    if url_type == 'external':
        new_tag = soup.new_tag('img', src=image_url)

    else:
        new_tag = NavigableString(notion_page.get_placeholder_text_for_url(image_url))

    soup.append(new_tag)


def _video(block, soup, notion_page):
    url_type = block.get('video', {}).get('type', '')
    url = block.get('video', {}).get(url_type, {}).get('url', '')


    if url_type == 'external':
        # Embedding video is weird and platform-specific. Just link instead.
        new_tag = soup.new_tag("a", href=url)
        new_tag.string = url
    else:
        new_tag = NavigableString(notion_page.get_placeholder_text_for_url(url))

    soup.append(new_tag)


def _audio(block, soup, notion_page):
    url_type = block.get('audio', {}).get('type', '')
    url = block.get('audio', {}).get(url_type, {}).get('url', '')

    if url_type == 'external':
        audio_tag = soup.new_tag('audio', controls=True)
        source_tag = soup.new_tag('source', src=url, type="audio/mpeg")
        audio_tag.append(source_tag)
        audio_tag.string = "Your browser does not support the audio element."
    else:
        audio_tag = NavigableString(notion_page.get_placeholder_text_for_url(url))

    soup.append(audio_tag)


########################### Extract Properties

def extract_files_properties_only(notion_page):

    properties = notion_page.properties.get('properties', {})

    files_properties = []
    for property_name, property_value in properties.items():
        property_type = property_value.get('type')

        if property_type == 'files':
            logger.debug(f"Found files property: Name: {property_name} -- Value: {property_value}")
            files_properties.append(property_value)

    return files_properties


def extract_page_properties(notion_page, soup):
    """
    This function takes a Notion page object as input and returns the page properties
    as a BeautifulSoup object.

    Args:
        page (dict): A dictionary representing a Notion page object.

    Returns:
        BeautifulSoup object representing the page properties.
    """

    handlers = {
        'title': _title,
        'rich_text': _rich_text,
        'number': _number,
        'select': _select,
        'multi_select': _multi_select,
        'date': _date,
        'files': _files,
        'checkbox': _checkbox,
        'url': _url,
        'email': _email,
        'phone_number': _phone_number,
        'created_time': _created_time,
        'last_edited_time': _last_edited_time,
        'formula': _formula,
        'relation': _relation,
        'rollup': _rollup,
        'status': _status,
        'people': _people,
        'created_by': _created_by,
        'last_edited_by': _last_edited_by,
        'unique_id': _unique_id
    }

    # These are the properties we're interested in.
    properties = notion_page.properties.get('properties', {})

    for property_name, property_value in properties.items():
        property_type = property_value.get('type')
        handler = handlers.get(property_type)

        if handler is None:
            notion_page.add_error(f"!!!!!!!! Unknown property type! Skipping!!!!!!!: {property_type} -- Value: {property_value}")
            continue

        if property_type in ['people', 'created_by', 'last_edited_by', 'files']:
            handler(property_name, property_value, soup, notion_page)

        else:
            handler(property_name, property_value, soup)

    return soup


def _title(_, __, ___):
    # We don't need a title property because we already have the page title. So pass.
    pass


def _rich_text(property_name, property_value, soup):
    p_tag = soup.new_tag("p")
    b_tag = soup.new_tag("b")
    b_tag.string = f"{property_name}: "
    p_tag.append(b_tag)

    rich_text = property_value.get('rich_text', [])
    for text in rich_text:
        p_tag.append(_handle_formatting(text, soup))

    soup.append(p_tag)


def _number(property_name, property_value, soup):
    number = str(property_value.get('number', ''))
    if number is None:
        number = ' '

    _format_property(property_name, number, soup)


def _select(property_name, property_value, soup):
    logger.debug(f"Select (only) property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    select_prop = property_value.get('select', {})
    if select_prop:
        select = select_prop.get('name', '')
    else:
        select = ' '

    _format_property(property_name, select, soup)


def _multi_select(property_name, property_value, soup):
    multi_select = ', '.join([option.get('name', '') for option in property_value.get('multi_select', [])])
    logger.debug(f"Multi-Select property -- Prop Name: {property_name} -- Prop Value: {property_value}")

    _format_property(property_name, multi_select, soup)


def _date(property_name, property_value, soup):
    date = property_value.get('date', {})

    if date:
        start_date = date.get('start', '')
        end_date = date.get('end', '')

        if start_date and end_date:
            _format_property(property_name, f"{start_date} to {end_date}", soup)

        elif start_date:
            _format_property(property_name, start_date, soup)

        else:
            _format_property(property_name, " ", soup)

    else:
        _format_property(property_name, " ", soup)


def _files(property_name, property_value, soup, notion_page):
    logger.debug(f"Files property -- Prop Name: {property_name} -- Prop Value: {property_value}")

    all_files = property_value.get('files', [])
    placeholder_text = ""
    for file in all_files:
        file_url = file.get('file', {}).get('url', '')

        placeholder_text += f"{notion_page.get_placeholder_text_for_url(file_url)}, "

    placeholder_text = placeholder_text.rstrip(', ')
    _format_property(property_name, placeholder_text, soup)


def _checkbox(property_name, property_value, soup):
    checkbox = property_value.get('checkbox', '')

    if checkbox:
        _format_property(property_name, "Checked", soup)

    else:
        _format_property(property_name, "Unchecked", soup)


def _url(property_name, property_value, soup):
    url = property_value.get('url', '')
    if url is None:
        url = ' '

    p_tag = soup.new_tag("p")
    b_tag = soup.new_tag("b")
    a_tag = soup.new_tag("a", href=url)

    b_tag.string = f"{property_name}: "
    p_tag.append(b_tag)
    p_tag.append(a_tag)
    soup.append(p_tag)


def _email(property_name, property_value, soup):
    # logger.debug(f"Email property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    email = property_value.get('email', '')
    if email is None:
        email = ' '

    email_url = f"mailto:{email}"

    p_tag = soup.new_tag("p")
    b_tag = soup.new_tag("b")
    a_tag = soup.new_tag("a", href=email_url)

    a_tag.string = email
    b_tag.string = f"{property_name}: "
    p_tag.append(b_tag)
    p_tag.append(a_tag)
    soup.append(p_tag)


def _phone_number(property_name, property_value, soup):
    phone_number = property_value.get('phone_number', '')
    if phone_number is None:
        phone_number = ' '

    _format_property(property_name, phone_number, soup)


def _created_time(property_name, property_value, soup):
    created_time_raw = property_value.get('created_time', '')
    if created_time_raw is None:
        created_time = ' '
    else:
        created_time = convert_to_local(created_time_raw).strftime('%Y-%m-%d %H:%M:%S')

    _format_property(property_name, created_time, soup)


def _last_edited_time(property_name, property_value, soup):
    last_edited_time_raw = property_value.get('last_edited_time', '')
    if last_edited_time_raw is None:
        last_edited_time = ' '
    else:
        last_edited_time = convert_to_local(last_edited_time_raw).strftime('%Y-%m-%d %H:%M:%S')

    _format_property(property_name, last_edited_time, soup)


def _formula(property_name, property_value, soup):

    formula_type = property_value.get('formula', {}).get('type', '')
    formula_result = property_value.get('formula', {}).get(formula_type, '')
    if formula_result is None:
        formula_result = ' '
    formula_result = str(formula_result)

    _format_property(property_name, formula_result, soup)


def _relation(property_name, property_value, soup):
    logger.debug(f"Relation property -- Prop Name: {property_name} -- Prop Value: {property_value}")

    relation_values = property_value.get('relation', [])
    if relation_values is None:
        relation_values = []
    ids = [x.get('id', '') for x in relation_values]

    relation = str(ids).lstrip('[').rstrip(']').replace('\'', '').replace(' ', '')
    logger.debug(f"Relation value: {relation}")
    _format_property(property_name, relation, soup)


# As of 2023-09-12 the API documentation for rollup type is here, but I think
# the example is wrong? The type of the example is relation, not rollup.
# https://developers.notion.com/reference/page-property-values#rollup
def _rollup(property_name, property_value, soup):
    logger.debug(f"Rollup property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    rollup_type = property_value.get('rollup', {}).get('type', '')

    rollup_value = str(property_value.get('rollup', {}).get(rollup_type, ''))
    logger.debug(f"Rollup value: {rollup_value}")
    _format_property(property_name, rollup_value, soup)


def _status(property_name, property_value, soup):
    logger.debug(f"Status property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    status_text = property_value.get('status', {}).get('name', '')
    if status_text is None:
        status_text = ' '

    status_text = str(status_text)
    _format_property(property_name, status_text, soup)


def _unique_id(property_name, property_value, soup):
    logger.debug(f"Unique ID property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    prefix = property_value.get('unique_id', {}).get('prefix', '')
    if prefix is None:
        prefix = ''

    number = property_value.get('unique_id', {}).get('number', '')
    unique_id = f"{prefix}{number}"

    _format_property(property_name, unique_id, soup)


def _people(property_name, property_value, soup, notion_page):
    logger.debug(f"People property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    people = property_value.get('people', [])

    all_people_names = ""
    for person in people:
        user_id = person.get('id', '')
        username = notion_page.get_username_for_user_id(user_id)

        if not username:
            notion_page.add_error(f"Could not find username for user ID {user_id}. This may "
                                   "be because the Notion token used is not authorized to fetch "
                                   "users. User information capabilities are required to access "
                                   "Notion users. See "
                                   "https://developers.notion.com/reference/capabilities#user-capabilities for "
                                   "more information. Using user ID instead.")
            all_people_names += f"{user_id}, "
        else:
            all_people_names += f"{username}, "

    all_people_names = all_people_names.rstrip(', ')
    _format_property(property_name, all_people_names, soup)


def _created_by(property_name, property_value, soup, notion_page):
    logger.debug(f"Created By property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    user_id = str(property_value.get('created_by', {}).get('id', ''))
    username = notion_page.get_username_for_user_id(user_id)

    if not username:
        notion_page.add_error(f"Created By property - Could not find username for user ID {user_id}. This may "
                                "be because the Notion token used is not authorized to fetch "
                                "users. User information capabilities are required to access "
                                "Notion users. See "
                                "https://developers.notion.com/reference/capabilities#user-capabilities for "
                                "more information. Using user ID instead.")
        username = user_id

    _format_property(property_name, username, soup)


def _last_edited_by(property_name, property_value, soup, notion_page):
    logger.debug(f"Last Edited By property -- Prop Name: {property_name} -- Prop Value: {property_value}")
    user_id = str(property_value.get('last_edited_by', {}).get('id', ''))
    username = notion_page.get_username_for_user_id(user_id)

    if not username:
        notion_page.add_error(f"Last Edited By property - Could not find username for user ID {user_id}. This may "
                                "be because the Notion token used is not authorized to fetch "
                                "users. User information capabilities are required to access "
                                "Notion users. See "
                                "https://developers.notion.com/reference/capabilities#user-capabilities for "
                                "more information. Using user ID instead.")
        username = user_id

    _format_property(property_name, username, soup)


def _format_property(property_name, property_value, soup):
    p_tag = soup.new_tag("p")
    b_tag = soup.new_tag("b")
    b_tag.string = f"{property_name}: "
    p_tag.append(b_tag)
    p_tag.append(str(property_value))
    soup.append(p_tag)
