# Rich-Text Editor

The in-app editor uses **TipTap** for a modern writing experience.

## Features

- Bold, italic, strikethrough
- Headings (H2)
- Blockquotes
- Bullet and numbered lists
- Scene breaks (horizontal rule)
- Undo / redo
- Autosave every 2 seconds

## Storage

Content is saved as sanitized HTML with `content_format: html`. Legacy plain-text chapters are converted to HTML paragraphs when opened in the editor.

## Reading

HTML chapters render with the `prose-rich` stylesheet. All content is sanitized with bleach before save and display.
