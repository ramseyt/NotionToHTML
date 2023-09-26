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

### Methods

```python
get_from_notion(content_id, notion_token, file_path=None)```

- **Purpose**: Takes the Notion page or database referenced by the content_id. Recursively downloads all pages in the full page tree consisting of all sub-pages and mentioned pages, and the full contents of all databases encountered.
- **Parameters**:
    - **content_id** -- Notion ID of the database or page you want to download. See Notion's instructions [here](https://developers.notion.com/docs/working-with-page-content#creating-a-page-with-content) on how to find the page ID. Type: String.
    - **notion_token** -- The Notion access token you got from creating an integration. See [this page for more information](https://developers.notion.com/docs/create-a-notion-integration). Type: String.
    - **file_path** -- By default attachments are downloaded into a directory named "notion2html" in the user's home directory. You can change the location of the notion2html by passing in your desired path to this parameter. Type: pathlib.Path.
