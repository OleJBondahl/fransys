"""Private to `write/`: the `SymbolPlacement` builder (engine.md 7, model layout-namespace.md)."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import PREFIX, real_function, view_of
from fransys_layout.geometry import generic_box_geometry
from fransys_layout.geometry import library_version as symbol_library_version
from fransys_model.kernel import make_id
from fransys_model.layout import PlacementView, Side, SymbolPlacement

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.stages.types import PlacedFunction
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.layout import DrawingSet, Page

_UNGROUPED = ("ungrouped",)


def placements(
    keys: WriteKeys,
    results: StageResults,
    page_of: Mapping[PageId, Page],
    sets: Mapping[int, DrawingSet],
    stamp: str,
) -> tuple[list[SymbolPlacement], dict[tuple[Id[Any], int, int], AuthoringKey]]:
    """The symbol placements, and each one's discriminator for the labels drawn on it."""
    nodes = keys.aspect_node
    columns = {column.key: column for column in results.columns}
    records = []
    discriminator: dict[tuple[Id[Any], int, int], AuthoringKey] = {}
    attached = {
        (cell.function, column.key)
        for column in results.columns
        for cell in column.cells
        if cell.replica
    }
    for placed in results.layout.placed:
        extra: AuthoringKey = ()
        if placed.column in results.replicas or (placed.function, placed.column) in attached:
            group = columns[placed.column].group
            extra = nodes[group] if group is not None else _UNGROUPED
            extra = (*extra, "drawing_set", *sets[placed.drawing_set].key[len(PREFIX) + 1 :])
        real, pin = real_function(keys, placed.function)
        if pin is not None:
            extra = (*extra, "pin", pin)
        view = view_of(keys, placed.function)
        # an item view stands on a function drawn apart too
        extra = (*extra, "view") if view is PlacementView.ITEM else extra
        discriminator[placed.function, placed.drawing_set, placed.page] = extra
        port_names, port_sides, offsets = _placement_fields(placed, view)
        key = (*PREFIX, "symbol_placement", *keys.function[real], *extra)
        records.append(
            SymbolPlacement(
                id=make_id(SymbolPlacement, key),
                key=key,
                function=real,
                page=page_of[placed.drawing_set, placed.page].id,
                x=placed.at.x,
                y=placed.at.y,
                orientation=placed.geometry.orientation,
                poles=placed.geometry.poles,
                symbol=placed.geometry.key,
                library_version=symbol_library_version(),
                produced_by=stamp,
                # R7 B2: an item view: render draws the box with all the item's ports
                view=view,
                ports=port_names,
                sides=port_sides,
                port_offsets=offsets,
            )
        )
    return records, discriminator


def _placement_fields(
    placed: PlacedFunction,
    view: PlacementView,
) -> tuple[tuple[str, ...], tuple[Side, ...], tuple[int, ...]]:
    """R7 C5 a generic box's names and sides, model-0129 its pin x when wide."""
    geometry = placed.geometry
    if not geometry.generic_box:
        return (), (), ()
    # C2/C5: the box's own port list, in drawing order (left to right, N before S at one
    # x), and each port's side: render rebuilds exactly this box
    drawn = sorted(geometry.ports, key=lambda port: (port.at.x, port.facing.value != "n"))
    names: list[str] = [port.name for port in drawn]
    sides = [port.facing.value for port in drawn]
    plain = {p.name: p.at.x for p in generic_box_geometry(tuple(names), tuple(sides)).ports}
    offsets = tuple(port.at.x for port in drawn)  # grid units, model-0129
    wide = any(plain[port.name] != port.at.x for port in drawn)
    alternating = ["n" if i % 2 == 0 else "s" for i in range(len(drawn))]
    if wide or view is PlacementView.ITEM or names != sorted(names) or sides != alternating:
        return (
            tuple(names),
            tuple(Side[side.upper()] for side in sides),
            offsets if wide else (),
        )
    return (), (), ()
