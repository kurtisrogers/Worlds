"""Locate a review quote in chapter text.

start_offset counts UTF-16 code units, the same index a browser textarea
or contenteditable caret uses. The server only stores an offset when the
quote occurs verbatim. Reading an anchor never writes the chapter.
"""

_MAX_QUOTE = 120


def utf16_len(text):
    """UTF-16 code units in text. A code point above U+FFFF counts as two."""
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text)


def place_quote(chapter, quote):
    """Return the stored quote and its UTF-16 offset, or (None, None)."""
    if not quote or quote not in chapter:
        return None, None
    index = chapter.find(quote)
    stored = quote[:_MAX_QUOTE]
    return stored, utf16_len(chapter[:index])


def resolve_anchor(chapter, quote, start_offset):
    """Compare a stored anchor with the chapter as it is now.

    Returns (anchor_status, start_offset or None). Does not write anything.

    ok, with an offset: the quote is at the stored offset, or it is not
    there and occurs exactly once elsewhere. The returned offset is the
    location in the current text and is not written back.
    changed, with no offset: the quote no longer appears anywhere.
    none, with no offset: the finding never had an anchor, or the quote
    now appears more than once and is not at the stored offset.
    """
    if not quote:
        return "none", None
    if start_offset is not None and _quote_at(chapter, quote, start_offset):
        return "ok", start_offset
    matches = _find_all(chapter, quote)
    if len(matches) == 1:
        return "ok", utf16_len(chapter[: matches[0]])
    if not matches:
        return "changed", None
    return "none", None


def present_finding(row, chapter):
    """The finding as the panel reads it. The row and the chapter stay put."""
    status, offset = resolve_anchor(chapter or "", row.quote, row.start_offset)
    return {
        "id": row.id,
        "question": row.question,
        "status": row.status,
        "start_offset": offset,
        "quote": row.quote or None,
        "anchor_status": status,
    }


def _quote_at(chapter, quote, start_offset):
    index = _python_index(chapter, start_offset)
    if index is None:
        return False
    return chapter[index : index + len(quote)] == quote


def _python_index(text, utf16_offset):
    if utf16_offset < 0:
        return None
    units = 0
    for index, char in enumerate(text):
        if units == utf16_offset:
            return index
        units += 2 if ord(char) > 0xFFFF else 1
        if units > utf16_offset:
            return None
    if units == utf16_offset:
        return len(text)
    return None


def _find_all(text, quote):
    found = []
    start = 0
    while True:
        index = text.find(quote, start)
        if index < 0:
            return found
        found.append(index)
        start = index + 1
