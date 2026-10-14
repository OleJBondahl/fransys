"""One Typst table for every list: whole rows, two on each side of a split, " (cont.)" (pdf-0027).

A zero-width guide column carries the `rowspan: 2` cells that keep the first two and the last two
body rows together; a table of fewer than four rows is one unbreakable block.
"""

from ._sizes import RULE
from ._typst import literal

_MIN_SPLIT_ROWS = 4  # fewer body rows than twice the two-row rule: the table moves whole
_CONT = " (cont.)"
_PLAIN = "table.cell(stroke: none, inset: 0pt)[]"
_SPAN = "table.cell(rowspan: 2, stroke: none, inset: 0pt)[]"


def _title_cell(columns: int, title: str, label: str) -> str:
    """The header's first row: empty on the table's first fragment, the heading + (cont.) after.

    The header repeats on each fragment, and `context` re-evaluates per repeat: a fragment whose
    position is the table's own (`label`) is the first.
    """
    first = (
        f"let p = here().position(); let q = locate(<{label}>).position(); "
        "let first = p.page == q.page and calc.abs(p.x - q.x) < 3mm and calc.abs(p.y - q.y) < 5mm"
    )
    carried = (
        f"heading(level: 2, outlined: false, bookmarked: false, text({literal(title + _CONT)}))"
    )
    return (
        f"table.cell(colspan: {columns + 1}, stroke: none, inset: 0pt)"
        f"[#context {{ {first}; if first [] else {{ {carried} }} }}]"
    )


def table_source(
    widths: list[str],
    header: list[str],
    rows: list[list[str]],
    *,
    title: str = "",
    label: str = "",
) -> str:
    """`#table(...)` over `rows` of cell sources; `title` is the heading a carried table repeats.

    `label` names the table so that a repeated header can tell its first fragment (unique per
    document); `header` and each row hold one cell source per entry of `widths`.
    """
    keep_whole = len(rows) < _MIN_SPLIT_ROWS
    last = len(rows) - 1
    head = [_title_cell(len(widths), title, label)] if title else []
    cells = [f"table.header({', '.join([*head, _PLAIN, *header])})"]
    for index, row in enumerate(rows):
        if not keep_whole and index in (1, last):
            cells.extend(row)  # the second row of a span: its guide cell is the span's own
            continue
        spans = not keep_whole and index in (0, last - 1)
        cells.append(_SPAN if spans else _PLAIN)
        cells.extend(row)
    columns = ", ".join(["0pt", *widths])
    anchor = f" <{label}>" if title else ""
    table = f"table(columns: ({columns}), stroke: {RULE}, {', '.join(cells)}){anchor}"
    opener = "#block(breakable: false)[" if keep_whole else "#["
    return f"{opener}#set table.cell(breakable: false)\n#{table}\n]"
