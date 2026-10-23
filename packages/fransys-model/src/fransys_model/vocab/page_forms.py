"""What each page kind is: its form, its list key and whether it frames itself (model-0311).

Data only. `derive.page_preset` reads it; `fransys_pdf` maps a form and a list key to a builder.
"""

from enum import Enum

from fransys_model.kernel import register_enum

from .enums import PageKind

__all__ = ["PAGE_FORMS", "ListKey", "PageForm"]


@register_enum
class PageForm(Enum):
    """How a page kind is built: one form per builder, `LIST` for the lists a heading marks."""

    COVER = "cover"
    NOTES = "notes"
    SHEET_INDEX = "sheet_index"
    CONTENTS = "contents"
    SCHEMATIC = "schematic"
    HARNESS_DRAWING = "harness_drawing"
    BLOCK_DIAGRAM = "block_diagram"
    LIST = "list"
    CABLE_LIST = "cable_list"


@register_enum
class ListKey(Enum):
    """Which list a list page kind prints; the key of a list's builder and of its rows."""

    PLC = "plc"
    TERMINAL = "terminal"
    CONNECTOR = "connector"
    WIRE_LABEL = "wire_label"
    DESIGNATION = "designation"
    CABLE = "cable"
    BOM = "bom"


_F = PageForm
_L = ListKey
_K = PageKind

# kind -> (form, list key or None, self_framed)
PAGE_FORMS: dict[PageKind, tuple[PageForm, ListKey | None, bool]] = {
    _K.COVER: (_F.COVER, None, False),
    _K.NOTES: (_F.NOTES, None, False),
    _K.SHEET_INDEX: (_F.SHEET_INDEX, None, False),
    _K.CONTENTS: (_F.CONTENTS, None, False),
    _K.BLOCK_DIAGRAM: (_F.BLOCK_DIAGRAM, None, True),
    _K.SCHEMATIC: (_F.SCHEMATIC, None, True),
    _K.HARNESS_DRAWING: (_F.HARNESS_DRAWING, None, True),
    _K.PLC_LIST: (_F.LIST, _L.PLC, False),
    _K.TERMINAL_LIST: (_F.LIST, _L.TERMINAL, False),
    _K.CONNECTOR_LIST: (_F.LIST, _L.CONNECTOR, False),
    _K.WIRE_LABEL_LIST: (_F.LIST, _L.WIRE_LABEL, False),
    _K.DESIGNATION_LIST: (_F.LIST, _L.DESIGNATION, False),
    _K.CABLE_LIST: (_F.CABLE_LIST, _L.CABLE, False),
    _K.BOM: (_F.LIST, _L.BOM, False),
}
