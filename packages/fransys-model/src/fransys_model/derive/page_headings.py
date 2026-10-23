"""The words a page kind, a document preset and a drawing page print as their heading (pdf-0044).

`page_headings` is the title-block `page_title` of each list-like page kind; the schematic and
harness drawing carry their own title and scope per page, so they are not in it. Each heading is
a `[words]` entry of the house settings.
"""

from fransys_model.vocab import DocumentPreset, PageKind
lazy from fransys_model.kernel import Model

from .house_settings import word

__all__ = [
    "continued_heading",
    "diagram_title",
    "harness_drawing_title",
    "page_headings",
    "preset_headings",
    "schematic_title",
]

# the `[words]` key of each list-like page kind's heading
_PAGE_WORDS: dict[PageKind, str] = {
    PageKind.COVER: "cover",
    PageKind.NOTES: "notes",
    PageKind.SHEET_INDEX: "sheets",
    PageKind.CONTENTS: "contents",
    PageKind.PLC_LIST: "plc_list",
    PageKind.TERMINAL_LIST: "terminal_list",
    PageKind.CONNECTOR_LIST: "connector_list",
    PageKind.WIRE_LABEL_LIST: "wire_label_list",
    PageKind.DESIGNATION_LIST: "designation_list",
    PageKind.CABLE_LIST: "cable_list",
    PageKind.BOM: "bom",
}
_PRESET_WORDS: dict[DocumentPreset, str] = {
    DocumentPreset.CABINET_SCHEMATIC: "cabinet_schematic",
    DocumentPreset.HARNESS_DRAWING: "harness_drawing",
    DocumentPreset.PCB_SCHEMATIC: "pcb_schematic",
    DocumentPreset.SYSTEM: "system",
}


def diagram_title(model: Model) -> str:
    """The title-block page title of a block-diagram sheet."""
    return word(model, "block_diagram")


def schematic_title(model: Model) -> str:
    """The title-block page title of a schematic page with no title of its own."""
    return word(model, "schematic")


def harness_drawing_title(model: Model) -> str:
    """The title-block page title of a harness drawing with no cable run."""
    return word(model, "harness_drawing")


def page_headings(model: Model) -> dict[PageKind, str]:
    """The heading of each list-like page kind."""
    return {kind: word(model, key) for kind, key in _PAGE_WORDS.items()}


def preset_headings(model: Model) -> dict[DocumentPreset, str]:
    """The heading words of each document preset."""
    return {preset: word(model, key) for preset, key in _PRESET_WORDS.items()}


def continued_heading(model: Model, title: str) -> str:
    """The heading a table or run carried onto a further column or page prints."""
    return f"{title} {word(model, 'continued')}"
