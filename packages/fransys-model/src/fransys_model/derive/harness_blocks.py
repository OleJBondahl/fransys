"""The cable blocks a harness document draws: its cables, and the block each draws at (pdf-0015)."""

from fransys_model.vocab import DocumentPreset, PageKind
from fransys_model.vocab.tables import items, parts
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document, Item

from .cable_drawing import cable_block_key, cable_subject
from .document_scope import document_scope
from .rows_cable_run import CableBlockRef
lazy from .rows import HarnessCable

__all__ = [
    "cable_blocks",
    "harness_cables_for",
    "requests_harness_pages",
    "system_has_no_top_level_cables",
]


def requests_harness_pages(pages: tuple[PageKind, ...]) -> bool:
    """Whether `pages` holds `CONTENTS` or `HARNESS_DRAWING`, the page kinds that show cables.

    The one home of this test: `harness_cables_for` reads it, since the
    `CONTENTS` table prints the cables' rows and `HARNESS_DRAWING` draws them.
    """
    return PageKind.CONTENTS in pages or PageKind.HARNESS_DRAWING in pages


def harness_cables_for(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[HarnessCable, ...]:
    """The subject's cables: SYSTEM all top-level, a unit its own only."""
    if not requests_harness_pages(pages):
        return ()
    return document_scope(model, record).cables


def system_has_no_top_level_cables(
    record: Document, cables_found: tuple[HarnessCable, ...]
) -> bool:
    """A SYSTEM document whose model has no top-level cable at all."""
    return record.preset is DocumentPreset.SYSTEM and not cables_found


def _part_line(cable: HarnessCable) -> str:
    """The page's part line (pdf-0021): mpn, description, cores x gauge; unset ones omitted."""
    composite = None
    if cable.core_count is not None and cable.gauge_mm2 is not None:
        composite = f"{cable.core_count} x {cable.gauge_mm2} mm²"
    return _join_part_line(cable.mpn, cable.description, composite)


def _join_part_line(*texts: str | None) -> str:
    """The one part-line format, the lone cable's and the harness's: set texts, comma-joined."""
    return ", ".join(text for text in texts if text)


def _harness_block(model: Model, subject: Id[Item], key: str) -> CableBlockRef:
    """A harness block: in the run of the harness's own part, or of none."""
    part_id = items(model)[subject].part
    if part_id is None:
        return CableBlockRef(key=key, mpn="", line="")
    part = parts(model)[part_id]
    return CableBlockRef(key=key, mpn=part.mpn, line=_join_part_line(part.mpn, part.description))


def cable_blocks(
    model: Model, record: Document, cables: tuple[HarnessCable, ...]
) -> tuple[CableBlockRef, ...]:
    """The document's blocks, one per `cable_subject`, each at its first cable's place.

    A document reads absolutely unless it is a unit document, whose reading is its unit. A
    harness with wires gets its one block too (`DocumentScope.harnesses`), after the cable blocks.
    """
    scope = document_scope(model, record)
    unit = scope.unit
    blocks: dict[str, CableBlockRef] = {}
    for cable in cables:
        subject = cable_subject(model, cable.cable)
        key = cable_block_key(unit, subject)
        if key in blocks:
            continue
        blocks[key] = (
            CableBlockRef(key=key, mpn=cable.mpn or "", line=_part_line(cable))
            if subject == cable.cable
            else _harness_block(model, subject, key)
        )
    for wired in scope.harnesses:
        key = cable_block_key(unit, wired)
        blocks.setdefault(key, _harness_block(model, wired, key))
    return tuple(blocks.values())
