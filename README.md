# NotionToHTML

NotionToHTML is a Python library for programatically getting your content from Notion and converting it to HTML.

Give it the id to a Notion database and it will fetch all pages in the database as well as ALL sub-pages, mentioned pages, and the full contents of any other databases that it finds.

Give it the id to a Notion page and, like for databases, it will automatically fetch its contents and ALL sub-pages, mentioned pages, and the full contents of any other databases that it finds.

All content and property types are supported, including attachments.

## Table of Contents

## Features

- Easy to use. Just pass in the id of a single Notion page or database and ALL pages in the page tree (subpages or mentions) are automatically downloaded.
- Attachments are fully supported and are downloaded automatically.
- All content and property types are supported. Formatting is preserved as much as possible. For example:
    - List items such as bullets are properly indented
    - To-do checked/unchecked state is accurately reflected.
    - All files attached to the page as properies are downloaded, not just files attached to the page itself.
- Database pages are downloaded and processed concurrently, speeding up the download process.
- Each page downloaded returns HTML as a string, a BeautifulSoup object, the raw Notion page blocks and page properties, and more.
    - You can use it as a generic Notion data downloader if you just need access to the raw Notion page data.


## Limitations

A flat list of all pages found is returned to the caller. Page hierarchy isn't preserved. I haven't found a 100% reliable way to tell the difference between a true subpage of a given page, and a mention of a page that's not a subpage. Until that happens there's no way for a hierarchy to be exactly right and I don't want it to be subtly wrong.

Comments aren't downloaded.

## Installation

## Usage

### Step 1: Create an integration in Notion and get an API token

The first step is to create an integration in Notion and give it access to all the pages you want to download. Follow the directions on [this page in Notion](https://developers.notion.com/docs/create-a-notion-integration) to create an internal Notion integration. Start from the beginning and go through all steps up to and including "Give your integration page permissions". Stop after that point, don't do the rest of the steps.

Be sure to save your Notion token somewhere safe as you'll need it in step 3.

### Step 2: Make sure your integration has access to your Notion pages

Be sure that the integration has access to ALL the pages you want to download. A common cause of errors are pages that link to ("mention") other pages that aren't in the page tree that the integration has access to.

### Step 3: Give your integration user capabilities if needed

If you:

- Mention users if your pages, or
- Have database properties that mention users

...and you want to these user mentions to appear in the downloaded HTML as the actual names of these users, you need to give your integration the "Read user information without email addresses" capability. See the [Notion documentation on capabilities](https://developers.notion.com/reference/capabilities) for details on how to do this.


### Step 4: Choose the page you want to download and find its page ID

The library will download all pages and databases that are linked to the page you specify. "Linked" means all pages that are either true subpages or pages that are mentioned, and databases includes both full-page and inline/embedded databases.

Once you choose the page you want to download you'll need to find its page ID. See Notion's instructions on how to do that [here](https://developers.notion.com/docs/working-with-page-content#creating-a-page-with-content); click that link and scroll down to "Where can I find my page's ID?"

### Step 5: Run the code

Here's an example of how to use the library to download a tree of pages and save them as HTML files that can be uploaded to a webserver.

This is just one of many possible uses. The returned objects contain more properties and methods that are shown below; for more details on all the objects returned see the API reference.


```python
import notiontohtml

notion_token = foo # This is the access token you got from Notion in step 1
content_id = bar # This is the page ID you got in step 4
results = notiontohtml.get_from_notion(content_id, notion_token)
```

...time passes. Downloading many pages, especially many large pages, can take minutes.

```python
# Path object from pathlib that's the directory where the HTML files will be written.
html_files_directory = <<patlib.Path>>

# Path object from pathlib that's the directory where attachment files will be stored.
attachment_files_directory = html_files_directory.joinpath("attachments")

# Create both directories if needed.
html_files_directory.mkdir(exist_ok=True, parents=True)
attachment_files_directory.mkdir(exist_ok=True, parents=True)

# results is a NotionResult object returned by get_pages().
for page in results.get_pages():

    # Print out any errors that might have occured while downloading or processing the page.
    if page.errors:
        print(f"Error(s) on page: {page.id} -- Error(s): {page.error}")

    # Fix up links to other mentioned Notion pages.
    # This is the convenience method that's provided to do this for all pages at
    # once. You can also do this page-by-page by finding all link placeholder text and
    # replacing it with your desired link path. See the API reference for details.
    page_link_path = "/"
    page.set_all_link_paths(page_link_path)

    # Fix up attachment links and save all attachments to that directory.
    # A convenience method is provided to do this as well. In this case you need to specify
    # the relative path to the attachment directory, as well as the full path to the directory
    # where the attachments will be copied to.
    attachment_link_path = "/attachments"
    page.set_attachment_paths_and_copy(attachment_link_path, attachment_files_directory)

    # Write out the html to a file.
    # Use the page ID as the filename for this example. Be sure to set the encoding appropriately.
    # The get_updated_html() method returns the HTML as a string that has been updated to reflect
    # the changes made by the set_all_link_paths() and set_attachment_paths_and_copy() methods
    # above.
    full_path_to_html_file = html_files_directory.joinpath(f"{page.id}.html")
    with full_path_to_html_file.open(mode="w", encoding="utf-8") as html_file:
        html_file.write(page.get_updated_html())

```


## API Reference

notiontohtml.get_from_notion(notion_id, notion_token, file_path=None)


## Reporting Bugs

File a [GitHub issue](https://github.com/ramseyt/NotionToHTML/issues) for any bugs you find. If relevant include the full text of the page error or exception that was raised.

## Code Structure and Info

## Contributing

Contributions are welcome, though please file a [GitHub issue](https://github.com/ramseyt/NotionToHTML/issues) first so we can discuss the change you'd like to make.

## License
