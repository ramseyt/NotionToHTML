# API Reference

The documentation below defines the public interfaces for the library. These will remain stable and backwards-compatible. All other classes, methods, or attributes are considered private are subject to change without notice.

Your code will call the get_from_notion() method to download pages from Notion, like this:

```python
import notiontohtml

notion_token = foo # This is the access token you got from Notion in step 1
content_id = bar # This is the page ID you got in step 4
results = notiontohtml.get_from_notion(content_id, notion_token)
```

The get_from_notion() method returns a NotionResult object. Typically you will call the get_pages() method on the NotionResult object to return a list of NotionPage objects. Each NotionPage object represents a single page in Notion. These methods and objects are documented below.

<br>

## notiontohtml

This is the primary interface for the library and exposes one method: get_from_notion().

### Attributes

There are no public attributes.

### Methods

```python
notiontohtml.get_from_notion(content_id, notion_token, file_path=None)
```

- **Purpose**: Takes the Notion page or database referenced by the content_id. Recursively downloads all pages in the full page tree consisting of all sub-pages and mentioned pages, and the full contents of all databases encountered.
- **Parameters**:
    - **content_id** -- Notion ID of the database or page you want to download. See Notion's instructions [here](https://developers.notion.com/docs/working-with-page-content#creating-a-page-with-content) on how to find the page ID. Type: String.
    - **notion_token** -- The Notion access token you got from creating an integration. See [this page for more information](https://developers.notion.com/docs/create-a-notion-integration). Type: String.
    - **file_path** -- By default attachments are downloaded into a directory named "notion2html" in the user's home directory. You can change the location of the notion2html by passing in your desired path to this parameter. Type: pathlib.Path.
- **Returns**: A NotionResult object.

<br>

## NotionResult

An object of this class is returned by the get_from_notion() method, representing the results of the download.

### Attributes

There are no public attributes.


### Methods

```python
get_pages()
```

- **Purpose**: Returns a list of all pages downloaded from Notion as NotionPage objects. One Notion page corresponds to one (and only one) NotionPage object.
- **Parameters**:
    - None.
- **Returns**: A list of NotionPage objects. Type: List.


```python
get_page_for_id(page_id)
```

- **Purpose**: Returns a NotionPage object for the given id. Useful if you want a specific page in the set of downloaded pages.
- **Parameters**:
    - **page_id** -- Notion ID of page you want. Type: String.
- **Returns**: A list of NotionPage objects. Type: List.
- **Raises**:
    - `ValueError` -- If the page_id is not found in the downloaded pages.

```python
get_file_path()
```

- **Purpose**: Returns the path to the directory where attachments are downloaded.
- **Parameters**:
    - None.
- **Returns**: Path to the directory where attachments are downloaded. Type: pathlib.Path.

<br>

## NotionPage

Each NotionPage object represents a single page in Notion and holds the downloaded contents of that page in multiple forms.

### Attributes

- `id` -- Type: string. The Notion ID of the page.
- `title` -- Type: string. Title of the page.
- `original_soup` -- Type: BeautifulSoup soup object. A BeautifulSoup object corresponding to the original HTML downloaded from Notion.
- `original_html` -- Type: string. The original HTML downloaded from Notion as string.
- `updated_html` -- Type: string. HTML as a string that has been updated to reflect any changes made by the set_all_link_paths() and set_attachment_paths_and_copy() methods. If those methods have not been called, this will be a copy (not a reference) of the original_html attribute.
- `blocks` -- Type: list. A list of the decoded Notion blocks that make up the content of the page. See the [Notion API block documentation](https://developers.notion.com/reference/block) for block details.
- `properties` -- Type: dictionary. A dictionary of the decoded Notion page properties. See the [Notion API page property documentation](https://developers.notion.com/reference/page) for property details.

### Methods

```python
has_attachment()
```
- **Purpose**: Easy way to determine if the page has any attachments.
- **Parameters**:
    - None
- **Returns**: True if the page has attachments, False if it doesn't. Type: Boolean.


```python
get_attachments()
```
- **Purpose**: Get all attachments for the page.
- **Parameters**:
    - None
- **Returns**: A list of Attachment objects, one object for each file or image attached to the page. Type: List, that contains Attachment objects.


```python
has_errors()
```
- **Purpose**: Easy way to determine if any errors were encountered while downloading or processing the page.
- **Parameters**:
    - None
- **Returns**: True if the page has errors, False if it doesn't. Type: Boolean.


```python
get_errors()
```
- **Purpose**: Get all errors that occured while downloading or processing the page.
- **Parameters**:
    - None
- **Returns**: A list of errors that occured while downloading or processing the page. If there are no errors this list will be empty. Type: List, that contains strings.


```python
set_all_link_paths(path)
```
- **Purpose**: Replaces all text placeholders representing links to other Notion pages with a proper link given the relative path passed in. This is the convenience method that's provided to do this for all Notion pages linked in the pages contents. To do this for each link individually see the get_notionlink_for_placeholder_text() and get_all_notionlinks() methods.
- **Parameters**:
    - **path** -- Relative path to the directory that all HTML files will live in. Most commonly this will be "/". Type: string.
- **Returns**: No return value.


```python
set_attachment_paths_and_copy(link_path, directory_path)
```
- **Purpose**: Replaces all text placeholders representing links to attachments with a proper link given the relative path passed in. This is the convenience method that's provided to do this for all attachments linked in the pages contents. It also copies all attachment files to a uniquely-named directory inside the directory specified. This structure is created to prevent name collisions between files with the same name.
- **Parameters**:
    - **attachment_link_path** -- Directory that all attachment files will live in relative to where all HTML files live. One common example is "/attachments". Type: string.
    - **directory_path** -- Full path to the directory on disk where all attachment files will be copied to. Type: pathlib.Path.
- **Returns**: No return value.


```python
get_all_notionlinks()
```
- **Purpose**: Links to other Notion pages are represented in a page's HTML as text placeholders. This method returns a list of NotionPageLink objects, one object for each link to other Notion pages in the page's contents.
- **Parameters**:
    - None
- **Returns**: A list of NotionPageLink objects, one object for each link to other Notion pages in the page's contents. Type: List, that contains NotionPageLink objects.


```python
get_notionlink_for_placeholder_text(notionlink_placeholder_text)
```
- **Purpose**: Links to other Notion pages are represented in a page's HTML as text placeholders. This method takes placeholder text and returns the corresponding NotionPageLink object.
- **Parameters**:
    - **notionlink_placeholder_text** -- The placeholder text for the link you want to get the NotionPageLink object for. Type: string.
- **Returns**: A NotionPageLink object. Type: NotionPageLink.

<br>

## NotionPageLink

Each NotionPageLink object holds data corresponding to a link to another Notion page.

### Attributes

- `page_id` -- Type: string. The Notion page id of the page this link points to.
- `page_title` -- Type: string. The title of the page this link points to.
- `placeholder_text` -- Type: string. The placeholder text in the page's original HTML that's positioned where the link occurred in the original Notion page.

<br>

## Attachment

Each Attachment object represents a single file (including images) attachment on a Notion page.

### Attributes

- `type` -- Type: string. Describes the type of attachment. This will be one of: 'image', 'video', 'audio', 'file', or 'pdf'.
- `path` -- Type: pathlib.Path. The full path to the file downloaded locally on disk, as a pathlib.Path object.
- `placeholder_text` -- Type: string. When converting the page to HTML links to files are replaced with placeholder text that is unique for each file. The intent is for the user to replace the placeholder text with the desired link path. This attribute holds the placeholder text for this attachment.
