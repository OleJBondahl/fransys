"""Derived layout kinds of the cable drawing: one block per reading and subject.

They are page-less: a block holds boxes and core wires, in grid units from the block's own
top-left corner. `lay_out_cables` writes them and replaces only these kinds (`CABLE_KINDS`).
Decision model-0158. Texts are never stored: render prints the derive functions, layout
only measured them.
"""

from fransys_model.kernel import AuthoringKey, Id, Value, record, value
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item, Port, Unit

from .enums import BlockRow, BoxKind, EndStyle
from .formats import SheetFormat
from .order import by_index, holder_of
from .results import RoutePoint


@record(kind="layout.cable_block")
class CableBlock:
    """One drawing block: a cable, or a harness of cables, in one reading.

    `unit` is the reading (`None` is the absolute one); `subject` is the cable or its harness.
    `width`/`height` is the block's size and `pitch` the row step, all in G. `sheet_format`
    names the authored sheet that scales it; `None` is the house sheet, which is no record.
    """

    id: Id[CableBlock]
    key: AuthoringKey
    subject: Id[Item]
    unit: Id[Unit] | None
    width: int
    height: int
    pitch: int
    sheet_format: Id[SheetFormat] | None
    produced_by: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.cable_box")
class CableBox:
    """The box of one cable in a block; a harness block also has one `BoxKind.HARNESS` box.

    `item` is the cable, or the harness for the dashed box. `external` is true for a cable
    drawn dashed because its end is by others. `x`, `y` is the top-left corner.
    """

    id: Id[CableBox]
    key: AuthoringKey
    block: Id[CableBlock]
    item: Id[Item]
    kind: BoxKind
    external: bool
    x: int
    y: int
    width: int
    height: int
    produced_by: str
    ext: frozendict[str, Value] = frozendict()


@value
class PinCell:
    """One cell of an `EndBox`; `index` is its place left to right.

    `x` is the cell centre x, where its core lands; `width` is the cell's width, which render
    reads for the divider on its left edge (layout-0152).
    """

    index: int
    port: Id[Port]
    x: int
    width: int
    landed: bool


@record(kind="layout.end_box")
class EndBox:
    """The one box of an item in a block's top or bottom row, with its pins.

    `style` says how the box is drawn: solid, dashed (by others) or blank (CD11).
    `pins` are stored in `index` order.
    """

    id: Id[EndBox]
    key: AuthoringKey
    block: Id[CableBlock]
    item: Id[Item]
    row: BlockRow
    style: EndStyle
    x: int
    y: int
    width: int
    height: int
    pins: tuple[PinCell, ...]
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `pins` in `index` order; a repeated `index` is refused."""
        pins = by_index(self.pins, PinCell, kind="layout.end_box", holder=holder_of(self))
        if pins is not None:
            object.__setattr__(self, "pins", pins)


@record(kind="layout.core_wire")
class CoreWire:
    """One core drawn between the two rows of a block, with its text position.

    A core is two runs that stop at the closed cable box's edges: `run_a` from `end_a`'s box,
    `run_b` to `end_b`'s, points in `index` order. `stub_a`/`stub_b` mark a blank end's stub.
    `text_x` and `text_y` are the centre of the core text, turned to read upward on its axis.
    """

    id: Id[CoreWire]
    key: AuthoringKey
    block: Id[CableBlock]
    conductor: Id[Conductor]
    run_a: tuple[RoutePoint, ...]
    run_b: tuple[RoutePoint, ...]
    text_x: int
    text_y: int
    stub_a: bool
    stub_b: bool
    produced_by: str
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store each run's points in `index` order; a repeated `index` is refused."""
        for name, found in (("run_a", self.run_a), ("run_b", self.run_b)):
            points = by_index(found, RoutePoint, kind="layout.core_wire", holder=holder_of(self))
            if points is not None:
                object.__setattr__(self, name, points)
