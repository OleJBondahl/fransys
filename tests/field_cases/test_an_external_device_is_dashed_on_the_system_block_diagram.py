"""Field case: seven connector devices joined by six cables, two of them supplied by others (external=True), read at system level.
The bug: a unit's block diagram drew no dashed box for its two external devices (external-items spec Y3 left its set unmarked).
Fixed by OUTLINES BO4 (2026-10-14, block-diagrams BD4), each external device is dashed on the system block diagram."""

from test_a_cable_tree_draws_on_the_block_diagram_without_crossings import _TAGS, _built

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_diagrams

_EXTERNAL = ("P3", "P6")


def test_the_system_reading_dashes_each_external_device() -> None:
    diagrams, _ = lay_out_diagrams(_built(external=_EXTERNAL).model, LIBRARY)
    boxes = tuple(box for d in diagrams.diagrams for sheet in d.sheets for box in sheet.boxes)
    assert len(boxes) == len(_TAGS)
    assert sum(box.dashed for box in boxes) == len(_EXTERNAL)
