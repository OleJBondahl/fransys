"""The hidden headings that anchor a sheet: its destination label and its outline entries (NV3)."""

from typing import TYPE_CHECKING

from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.derive.page_nav import OutlineSheet

_HEADING = "heading(level: {level}, outlined: false, bookmarked: true, {text})"


def sheet_mark(entry: OutlineSheet) -> str:
    """A hidden level-1 heading labelled with the sheet's destination, its designations below.

    `outlined: false` keeps any printed outline untouched; `bookmarked: true` writes the PDF's own.
    """
    below = "".join(f"#{_HEADING.format(level=2, text=literal(name))}" for name in entry.entries)
    top = _HEADING.format(level=1, text=literal(entry.title))
    return f"#place(hide[#{top} <{entry.destination}>{below}])"


LIST_HEADING = "#heading(level: 2, "


def list_mark(body: str, title: str) -> str:
    """`body` led by a hidden level-1 heading of `title`, when it holds an outlined list heading.

    The list page's designations nest under it as a sheet's do (NV3); a body with none stays as is.
    """
    if LIST_HEADING not in body:
        return body
    top = _HEADING.format(level=1, text=literal(title))
    return f"#place(hide[#{top}])\n{body}"
