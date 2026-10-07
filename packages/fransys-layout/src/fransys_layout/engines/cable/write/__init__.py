"""Cable engine, writing: placed blocks to derived `layout.cable_*` records (CT5 CD2)."""

from typing import TYPE_CHECKING

from fransys_layout.engines.cable.defaults import ENGINE_NAME, ENGINE_VERSION
from fransys_layout.engines.cable.write.records import block_records
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import CABLE_KINDS, derived_layout_ids

if TYPE_CHECKING:
    from fransys_layout.engines.cable.values import PlacedBlock
    from fransys_model.kernel import Model


def write_cables(model: Model, blocks: tuple[PlacedBlock, ...]) -> Model:
    """Replace every cable-kind `layout.*` record of `model` with the ones `blocks` describe."""
    stamp = f"fransys-layout/{ENGINE_NAME} {ENGINE_VERSION}"
    records = [record for block in blocks for record in block_records(block, stamp)]
    origin = Origin(file=stamp, line=1, note="derived layout record")
    remove = derived_layout_ids(model, kinds=CABLE_KINDS)
    return evolve(model, remove=remove, put=records, origin=origin)
