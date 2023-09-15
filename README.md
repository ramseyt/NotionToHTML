# NotionToHTML

NotionToHTML is a Python library for programatically getting your content from Notion and converting it to HTML.

Given it the id to a Notion database and it will fetch all pages in the database as well as ALL sub-pages, mentioned pages, and the full contents of any other databases that it finds.

Given it the id to a Notion page and, like for databases, it will automatically fetch its contents and ALL sub-pages, mentioned pages, and the full contents of any other databases that it finds.

All content and property types are supported, including attachments.

## Table of Contents

## Features

- Simple to use - just one method call.
- You don't need to worry about the distinction between Notion pages and databases. Just pass in a content ID and the library does the rest.
- Attachments are supported. All attachments are automatically downloaded.
- All content and property types are supported. Formatting is preserved as much as possible. List items such as bullets are properly indented and todo checked/unchecked state is accurately reflected.
- Database pages are downloaded and processed concurrently, speeding up the download process.
- For each page downloaded it returns HTML, a BeautifulSoup object, the raw Notion page blocks and page properties, and more.
    - So it can also be used as a generic Notion data downloader if you just need access to the raw Notion page data.

## Limitations

**A flat list of all pages found is returned to the caller; page hierarchy isn't preserved.**
- Due to Notion API limitations it's not possible to tell the difference between a subpage and a mention of a page that's not a subpage. This makes it impossible for any hierarchy to be exactly right and it's probably the worst of all cases to be subtly wrong.

**Links to attachments, other downloaded Notion pages, and other Notion databases are not HTML links.**

They are instead placeholder strings in a structured format containing the ids of the objects they refer to. Callers can easily do a find and replace to replace these placeholders with HTML as needed; the intent is to allow callers to programatically structure downloaded content into any directory structure you want. Of course all other links *are* preserved in the returned HTML as-is.


## Installation

## Usage

```
notion_token = FOO # you got this from Notion above in step YYYY
content_id = BAR # 32-character identifier you got from Notion in...
results = notiontohtml.get_from_notion(content_id, notion_token)
```

...time passes; downloading many pages, especially many large pages, can take minutes...

```
# results is a NotionResult object
for page in results.get_pages()
    # page is a NotionPage object
    page.title # title of the page
    page.html # page contents converted to HTML

# I have the ID of a specific page that I want
page_id = BAZ
page = results.get_item_for_id(page_id)

# Does this page have attachments? If so give me the full paths to all.
if page.has_attachment():
    for file in page.get_attachments():
        file.path # full path to the attachment file, as a pathlib.Path object.

```


## API Reference

notiontohtml.get_from_notion(notion_id, notion_token, file_path=None)


## Reporting Bugs

## Code Structure and Info

## Contributing

## License
