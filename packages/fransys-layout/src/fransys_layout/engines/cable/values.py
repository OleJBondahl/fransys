"""The cable engine's values: the reader's facts of a block and the placer's geometry (CT5 CD2)."""

from typing import Any

from fransys_layout.geometry import Box, Point
from fransys_model.kernel import Id, value


@value
class CoreFacts:
    """One core: its key (core number), conductor, its two ports (`end_a` first), text width.

    `link` is a row link (CD5 at L1): both ends in one row, drawn at the row, never in the box.
    """

    key: int
    conductor: Id[Any]
    end_a: Id[Any]
    end_b: Id[Any]
    text_width: int
    link: bool = False


@value
class CableFacts:
    """The block's one cable: whether it is by others, its heading width, its cores in order."""

    cable: Id[Any]
    external: bool
    heading_width: int
    cores: tuple[CoreFacts, ...]


@value
class PinFacts:
    """One drawn pin of an end, in drawing order: its port, landed or free, its marking's width.

    `cores` are the conductors landing on it in core-key order, one place each (CD6, P1).
    """

    port: Id[Any]
    landed: bool
    marking_width: int
    cores: tuple[Id[Any], ...] = ()

    @property
    def places(self) -> int:
        """The cell's width in pitches: one per core, one for a free pin."""
        return max(1, len(self.cores))


@value
class EndFacts:
    """One end item: dashed (by others), blank (CD11), its label's width and its drawn pins."""

    item: Id[Any]
    dashed: bool
    blank: bool
    label_width: int
    pins: tuple[PinFacts, ...]

    @property
    def places(self) -> int:
        """The box's width in pitches: the places of its pins."""
        return sum(pin.places for pin in self.pins)


@value
class BlockFacts:
    """What the reader hands the placer for one drawable block.

    `cables` run by designation, then `wires` (HA-H1 A1); `cores` is both, cables' first.
    `harness_width` is None when the subject is a cable (no dashed box, CD9).
    """

    subject: Id[Any]
    unit: Id[Any] | None
    sheet_format: Id[Any] | None
    text_height: int
    turn_penalty: int
    crossing_penalty: int
    pad: int
    cables: tuple[CableFacts, ...]
    top: tuple[EndFacts, ...]
    bottom: tuple[EndFacts, ...]
    harness_width: int | None = None
    wires: tuple[CoreFacts, ...] = ()

    @property
    def cores(self) -> tuple[CoreFacts, ...]:
        """Every core of the block: the cables' cores in print order, then the single wires."""
        return (*(core for cable in self.cables for core in cable.cores), *self.wires)


@value
class CorePlace:
    """One place of a wide cell: the core that lands there and the centre x of the place."""

    core: Id[Any]
    x: int


@value
class PlacedCell:
    """One pin cell: its port, its centre x, whether a core lands and where each core lands.

    A cell is one pitch wide per core (P1); `landings` pairs each core with the centre x of its
    place, in core-key order. `x` is the centre of the whole cell.
    """

    port: Id[Any]
    x: int
    width: int
    landed: bool
    landings: tuple[CorePlace, ...] = ()


@value
class PlacedEnd:
    """One end box placed in the block, top row or bottom row, with its cells left to right."""

    item: Id[Any]
    top: bool
    dashed: bool
    blank: bool
    x: int
    y: int
    width: int
    height: int
    cells: tuple[PlacedCell, ...]


@value
class PlacedWire:
    """One core: a run from `end_a`'s box to the cable box, one from it to `end_b`'s; its text.

    The runs stop at the closed cable box's edges; `text_x` is the text's centre, on the axis.
    """

    conductor: Id[Any]
    run_a: tuple[Point, ...]
    run_b: tuple[Point, ...]
    text_x: int
    text_y: int
    stub_a: bool
    stub_b: bool


@value
class PlacedCable:
    """One cable's box in the block: the cable, whether it is by others, and the box."""

    cable: Id[Any]
    external: bool
    box: Box


@value
class PlacedBlock:
    """One block's geometry in G from its top-left corner; `harness` is the dashed box, if any."""

    subject: Id[Any]
    unit: Id[Any] | None
    sheet_format: Id[Any] | None
    width: int
    height: int
    pitch: int
    boxes: tuple[PlacedCable, ...]
    harness: Box | None
    ends: tuple[PlacedEnd, ...]
    wires: tuple[PlacedWire, ...]
