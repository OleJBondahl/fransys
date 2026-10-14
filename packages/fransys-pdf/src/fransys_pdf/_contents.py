"""The CONTENTS page: one table over the subject harness's cables."""

from typing import TYPE_CHECKING

from fransys_model.derive import CONTENTS_COLUMNS, cell_text, column_values, contents_rows

from ._drawings import harness_cables_for
from ._sizes import RULE
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab import Document, PageKind

_HEADERS = ("Designation", "MPN", "Description", "Cores", "Gauge", "Length mm", "Ends")


def contents_page(model: Model, record: Document, pages: tuple[PageKind, ...]) -> str:
    """The CONTENTS table (rows `ContentsRow`, model-0106, pdf-0016); `""` if no cable."""
    cables = harness_cables_for(model, record, pages)
    if not cables:
        return ""
    header = "table.header(" + ", ".join(f"strong(text({literal(h)}))" for h in _HEADERS) + ")"
    cells = [header]
    for row in contents_rows(cables):
        values = column_values(row, CONTENTS_COLUMNS)
        cells.extend(f"text({literal(cell_text(value))})" for value in values)
    return f"#table(columns: {len(_HEADERS)}, stroke: {RULE}, " + ", ".join(cells) + ")"
