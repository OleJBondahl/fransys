"""The words a page kind, a document preset and a drawing page print as their heading (pdf-0044).

`PAGE_HEADINGS` is the title-block `page_title` of each list-like page kind; SCHEMATIC and
HARNESS_DRAWING carry their own title and scope per page, so they are not in it.
"""

from fransys_model.vocab import DocumentPreset, PageKind

__all__ = [
    "DIAGRAM_TITLE",
    "HARNESS_DRAWING_TITLE",
    "PAGE_HEADINGS",
    "PRESET_HEADINGS",
    "SCHEMATIC_TITLE",
    "continued_heading",
]

DIAGRAM_TITLE = "Block diagram"
SCHEMATIC_TITLE = "Schematic"
HARNESS_DRAWING_TITLE = "Harness drawing"

PAGE_HEADINGS: dict[PageKind, str] = {
    PageKind.COVER: "Cover",
    PageKind.NOTES: "Notes",
    PageKind.SHEET_INDEX: "Sheets",
    PageKind.CONTENTS: "Contents",
    PageKind.PLC_LIST: "PLC list",
    PageKind.TERMINAL_LIST: "Terminal list",
    PageKind.CONNECTOR_LIST: "Connector list",
    PageKind.WIRE_LABEL_LIST: "Wire label list",
    PageKind.DESIGNATION_LIST: "Designation list",
    PageKind.CABLE_LIST: "Cable list",
    PageKind.BOM: "BOM",
}
PRESET_HEADINGS: dict[DocumentPreset, str] = {
    DocumentPreset.CABINET_SCHEMATIC: "Cabinet schematic",
    DocumentPreset.HARNESS_DRAWING: HARNESS_DRAWING_TITLE,
    DocumentPreset.PCB_SCHEMATIC: "PCB schematic",
    DocumentPreset.SYSTEM: "System",
}


def continued_heading(title: str) -> str:
    """The heading a table or run carried onto a further column or page prints."""
    return f"{title} (cont.)"
