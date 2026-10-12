"""The two-column flow of the list pages: tables down one column, then the next, then a page."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def flow_columns(sections: Iterable[str], *, share_pct: float, gutter_pct: float) -> str:
    """Typst for `sections` in two columns of `share_pct` width, `gutter_pct` apart (pdf-0026).

    Down the left column, then the right, then a new page; Typst keeps a heading with its table's
    first row and repeats the header row. The block is as wide as both columns and the gutter.
    """
    body = "\n".join(section for section in sections if section)
    if not body:
        return ""
    total = 2 * share_pct + gutter_pct
    gutter = gutter_pct / total * 100
    return f"#block(width: {total:g}%)[#columns(2, gutter: {gutter:g}%)[\n{body}\n]]"
