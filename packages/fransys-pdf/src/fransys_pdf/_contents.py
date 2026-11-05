"""The CONTENTS page: one table over the subject harness's cables."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    cell_text,
    column_values,
    contents_rows,
    harness_cables_for,
    list_columns,
    list_pdf_heading,
)

from ._sizes import rule_of
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.derive import DocumentRow
    from fransys_model.kernel import Model
    from fransys_model.vocab import PageKind


def contents_page(model: Model, record: DocumentRow, pages: tuple[PageKind, ...]) -> str:
    """The CONTENTS table (rows `ContentsRow`, model-0106, pdf-0016); `""` if no cable."""
    cables = harness_cables_for(model, record.id, pages)
    if not cables:
        return ""
    columns = list_columns(model, "contents")
    headings = [list_pdf_heading(model, "contents", f) for f in columns]
    header = "table.header(" + ", ".join(f"strong(text({literal(h)}))" for h in headings) + ")"
    cells = [header]
    for row in contents_rows(cables):
        values = column_values(row, columns)
        cells.extend(f"text({literal(cell_text(value))})" for value in values)
    return f"#table(columns: {len(headings)}, stroke: {rule_of(model)}, " + ", ".join(cells) + ")"
