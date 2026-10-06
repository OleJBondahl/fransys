"""T7: the case of a cut (links.md 6.6), read from its three facts by the `LINK_CASE` table."""

from typing import TYPE_CHECKING, NamedTuple

from fransys_layout.conventions import FACTS, fact, first_match, validate
from fransys_layout.conventions.references import LINK_CASE
from fransys_layout.geometry import LayoutError
from fransys_layout.stages.types import LinkCase

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.types import DrawnFunction, Handle, PortRef

    from .types import Cut, LinkWorld


class CutRead(NamedTuple):
    """A cut with what its case is read from: the net's terminals, the seats and the units."""

    cut: Cut
    terminals: Mapping[Handle, frozenset[Handle]]
    world: LinkWorld
    units: Mapping[int, Handle | None]


def drawn_of(ref: PortRef, world: LinkWorld) -> DrawnFunction:
    """A port's function as drawn; a function that is not drawn is a fault."""
    function = world.drawn_of.get(ref.function)
    if function is None:
        msg = "an end function of a connection or net group is not among the drawn functions"
        raise LayoutError(msg)
    return function


@fact("crosses_unit", kind="physical", source="the unit as a mounting assembly (IEC 61346)")
def _crosses_unit(read: CutRead) -> bool:
    """The two drawing sets of the cut belong to different units (U2)."""
    return read.units.get(read.cut.ends[0].page[0]) != read.units.get(read.cut.ends[1].page[0])


@fact("terminal_on_both_pages", kind="physical", source="terminal strip (IEC 60947-7)")
def _terminal_on_both_pages(read: CutRead) -> bool:
    """A terminal of the cut's net is seated on both of its pages."""
    pages = {end.page for end in read.cut.ends}
    return any(
        pages.issubset(read.world.where[function])
        for function in read.terminals[read.cut.physical_net]
    )


@fact("same_item", kind="physical", source="reference designation of one item (IEC 81346)")
def _same_item(read: CutRead) -> bool:
    """The two end functions are parts of one item, such as a coil and its contact."""
    first, second = (drawn_of(end.ref, read.world).item for end in read.cut.ends)
    return first == second


validate(LINK_CASE, FACTS)


def link_case(read: CutRead) -> LinkCase:
    """Which of the four cases a cut is; the first row of `LINK_CASE` that holds."""
    row = first_match(LINK_CASE, read, FACTS)
    return LinkCase(row.then if row else "severed")
