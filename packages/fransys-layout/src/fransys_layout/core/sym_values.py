"""The symbol value of the placer core: Sym and the turned views the symdef layer measured.

Split from values.py (layout-0316); frozen plain data, lengths in G.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from .errors import CoreError

if TYPE_CHECKING:
    from .values import Box, BoxSpec, Orientation, Pin, Side, Size


@dataclass(frozen=True, slots=True)
class PinTurn:
    """A pin at one orientation: its offset from the symbol origin and the side it faces."""

    dx: int
    dy: int
    side: Side


@dataclass(frozen=True, slots=True)
class Turned:
    """A symbol at one orientation, as the symdef layer measured it (SB4); the core only moves it.

    pins are in Sym.pins order. The core never derives one view from another.
    """

    body: Box
    keepout: Box
    footprint: Box
    pins: tuple[PinTurn, ...]
    row_footprint: Box | None = None


@dataclass(frozen=True, slots=True)
class Sym:
    """T1 to T3: row_group members at one column end in one row share y and use row_footprint.

    label is the size of the designation symbol; the text stage places it after the symbols and the
    footprint holds no text (R327). Text is the builder's.
    """

    id: str
    group: str | None
    unit: str
    label: Size
    pins: tuple[Pin, ...]
    nodes: tuple[tuple[str, ...], ...]
    views: Mapping[Orientation, Turned]
    box: BoxSpec | None = None
    row_group: str | None = None
    band: int | None = None
    item: str | None = None
    child_of: str | None = None
    boundary_of: str | None = None

    @property
    def r0(self) -> Turned:
        """The view at R0, which every symbol has (layout-0316: the flat reads come from it)."""
        view = self.views.get("R0")
        if view is None:
            msg = f"symbol {self.id} has no R0 view: its views are {list(self.views)}"
            raise CoreError(msg)
        return view

    @property
    def body(self) -> Box:
        """The body at R0."""
        return self.r0.body

    @property
    def keepout(self) -> Box:
        """The keep-out at R0."""
        return self.r0.keepout

    @property
    def footprint(self) -> Box:
        """The footprint at R0."""
        return self.r0.footprint

    @property
    def row_footprint(self) -> Box | None:
        """The strip-row footprint at R0, None for a symbol not in a strip."""
        return self.r0.row_footprint
