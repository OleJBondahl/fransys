"""What each document preset contains by default (root DESIGN 9). The types are the model's."""

from fransys_model.vocab import DocumentPreset, PageKind

_K = PageKind

PRESET_PAGES: frozendict[DocumentPreset, tuple[PageKind, ...]] = frozendict(
    {
        DocumentPreset.CABINET_SCHEMATIC: (
            _K.COVER,
            _K.NOTES,
            _K.SCHEMATIC,
            _K.PLC_LIST,
            _K.TERMINAL_LIST,
            _K.BOM,
        ),
        DocumentPreset.HARNESS_DRAWING: (
            _K.COVER,
            _K.NOTES,
            _K.CONTENTS,
            _K.HARNESS_DRAWING,
            _K.BOM,
        ),
        DocumentPreset.PCB_SCHEMATIC: (
            _K.COVER,
            _K.NOTES,
            _K.SCHEMATIC,
            _K.CONNECTOR_LIST,
            _K.BOM,
        ),
        # Only SYSTEM carries BLOCK_DIAGRAM; no unit document has it by default (BD-Q3 A),
        # `add=` puts it on any.
        DocumentPreset.SYSTEM: (
            _K.COVER,
            _K.NOTES,
            _K.BLOCK_DIAGRAM,
            _K.HARNESS_DRAWING,
            _K.CABLE_LIST,
            _K.BOM,
        ),
    }
)


def page_kinds(
    preset: DocumentPreset,
    *,
    add: tuple[PageKind, ...] = (),
    remove: tuple[PageKind, ...] = (),
) -> tuple[PageKind, ...]:
    """The pages of a document: the preset's pages plus `add`, minus `remove`, in canonical order.

    `remove` wins over `add`. Whether a NOTES page is actually produced also depends on the
    document having notes text; that is decided when the document is assembled.
    """
    wanted = (set(PRESET_PAGES[preset]) | set(add)) - set(remove)
    return tuple(kind for kind in PageKind if kind in wanted)
