# API Reference

Your code will call the get_from_notion() method to download pages from Notion, like this:

```python
import notiontohtml

notion_token = foo # This is the access token you got from Notion in step 1
content_id = bar # This is the page ID you got in step 4
results = notiontohtml.get_from_notion(content_id, notion_token)
```

The get_from_notion() method returns a NotionResult object. Typically you will call the get_pages() method on the NotionResult object to return a list of NotionPage objects. Each NotionPage object represents a single page in Notion. These methods and objects are documented below.


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
    - 'ValueError' -- If the page_id is not found in the downloaded pages.

```python
get_file_path()
```

- **Purpose**: Returns the path to the directory where attachments are downloaded.
- **Parameters**:
    - None.
- **Returns**: Path to the directory where attachments are downloaded. Type: pathlib.Path.
- **Raises**:
    - 'ValueError' -- If the page_id is not found in the downloaded pages.
