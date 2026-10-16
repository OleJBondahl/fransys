"""`COVER_OVERFLOW`: Typst measures the cover and its revision table at write (pdf-0047).

The cover source carries a hidden `#context` block that measures the cover text and the table at
the page's margin box and panics when they would overlap; the facade's compile step hands the
panic text to `cover_overflow_finding`. The panic format lives only here.
"""

import re
from typing import TYPE_CHECKING

from fransys_model.kernel import Finding, Severity

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab import Document

_PANIC = re.compile(
    r"COVER_OVERFLOW cover=(?P<cover>[\d.]+) table=(?P<table>[\d.]+) available=(?P<avail>[\d.]+)"
)


def measuring_block(*, has_table: bool) -> str:
    """The Typst that panics when `fr-cover` and `fr-table` (when there is one) do not both fit."""
    table = "measure(block(width: size.width, fr-table)).height" if has_table else "0pt"
    return (
        "#place(hide(context layout(size => {\n"
        "  let cover = measure(block(width: size.width, fr-cover)).height\n"
        f"  let table = {table}\n"
        "  if cover + table > size.height {\n"
        "    let mm = h => str(calc.round(h.mm(), digits: 1))\n"
        '    panic("COVER_OVERFLOW cover=" + mm(cover) + " table=" + mm(table)'
        ' + " available=" + mm(size.height))\n'
        "  }\n"
        "})))"
    )


def cover_overflow_finding(document: Id[Document], typst_error: str) -> Finding | None:
    """The `COVER_OVERFLOW` ERROR for a Typst panic from `measuring_block`, else `None`."""
    found = _PANIC.search(typst_error)
    if found is None:
        return None
    return Finding(
        code="COVER_OVERFLOW",
        severity=Severity.ERROR,
        subjects=(document,),
        message=(
            f"cover text {found['cover']} mm plus revision table {found['table']} mm exceeds "
            f"the {found['avail']} mm content box"
        ),
    )
