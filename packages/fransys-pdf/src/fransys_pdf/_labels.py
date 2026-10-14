"""Viewer page labels (NV4): a sheet shows its sheet text, every other page its roman page number.

Typst writes a label from a numbering pattern and the page counter, so each page sets the counter.
No page shows another page's label.
"""

import re

from ._typst import literal

ROMAN = 'numbering: "i", footer: none'
"""The `#set page` arguments every page starts from: a roman label and no printed page number."""

RESTART = "#context counter(page).update(here().page());"
"""Opens a page that is not a sheet: its counter, and so its roman label, is its physical page."""

LAST_PAGE = "fr-last"
"""The label of the end marker `document.source` appends: the frame's "of M" is its page."""


def sheet_label(text: str) -> tuple[str, str]:
    """The `#page` numbering argument, comma first, and the body opening that label sheet `text`.

    The counter holds one run of digits, the rest is literal text with no counting symbol `1`:
    `10.3` is `1.3` on counter 10, `2.1` is `2.` on counter 1; `10.1` takes the roman label.
    """
    for run in reversed(list(re.finditer(r"\d+", text))):
        rest = text[: run.start()] + "1" + text[run.end() :]
        if rest.count("1") == 1:
            return f", numbering: {literal(rest)}", f"#counter(page).update({run.group()})"
    return "", RESTART
