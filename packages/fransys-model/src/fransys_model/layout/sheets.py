"""Derived layout kind of a cable or block-diagram sheet (model-0355).

A sheet is a page-less drawing the facade lays out in memory; `LayoutSheet` names it so
membership rows can point at it. No pass writes it yet.
"""

from fransys_model.kernel import AuthoringKey, Id, Value, record

from .enums import SheetKind
from .formats import SheetFormat


@record(kind="layout.sheet")
class LayoutSheet:
    """One sheet of a cable list or block diagram; `document` is the reading it belongs to.

    `number` runs 1..n within the document. `sheet_format` is the paper, `None` for the
    default. Example: `LayoutSheet(sheet_kind=SheetKind.CABLE, document="cables", number=1, ...)`.
    """

    id: Id[LayoutSheet]
    key: AuthoringKey
    sheet_kind: SheetKind
    document: str
    number: int
    sheet_format: Id[SheetFormat] | None
    produced_by: str
    ext: frozendict[str, Value] = frozendict()
