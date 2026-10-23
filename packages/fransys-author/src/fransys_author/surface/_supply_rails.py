"""Supply rail handles: `SupplyRail`, the `_Rails` base and `AcSupply` / `DcSupply`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Iterable

from fransys_author.errors import AuthorError
from fransys_author.surface._pairing import End, Ends
lazy from fransys_author.handles import Port
lazy from fransys_model.vocab import ConductorMark, WiringRow

if TYPE_CHECKING:
    from fransys_author.surface.design import Design


@dataclass(frozen=True)
class SupplyRail:
    """One rail of a supply: its source pin, the potential it carries and its conductor mark.

    Does not wire itself: it stands in a `series` as a one-conductor element.
    """

    name: str
    pin: Port
    potential: str
    mark: ConductorMark
    phase: int | None
    row: WiringRow

    def _series_width(self) -> int | None:
        return 1

    def _conductor_rows(self) -> tuple[WiringRow, ...]:
        return (self.row,)

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        end = (End(self.pin, self.mark),)
        return Ends(end, end)


class _Rails:
    """The rails of one supply by attribute; a misspelt rail raises and lists the real ones."""

    def __init__(self, name: str, rails: Iterable[SupplyRail]) -> None:
        self._name, self._rails = name, tuple(rails)
        self.__dict__.update({rail.name: rail for rail in self._rails})

    _whole_supply = True  # a series that starts on a whole supply is a power path (S3)

    def _series_width(self) -> int | None:
        return len(self._rails)

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        """The first `width` rails: a path with no N pole leaves N, the last rail, unwired."""
        # `ac_supply` appends N after the phases, so N is always the last rail.
        ends = tuple(End(rail.pin, rail.mark) for rail in self._rails[:width])
        return Ends(ends, ends)

    def _conductor_rows(self) -> tuple[WiringRow, ...]:
        return tuple(rail.row for rail in self._rails)

    if not TYPE_CHECKING:  # the subclass declares its rails; ty must see no catch-all

        def __getattr__(self, name: str) -> SupplyRail:
            """The rail `name`.

            Does not guess: an unknown rail raises and lists the rails.
            """
            if name.startswith("_"):
                raise AttributeError(name)
            names = ", ".join(rail.name for rail in self._rails)
            msg = f"no rail {name!r}; rails: {names}"
            raise AuthorError(msg)


class AcSupply(_Rails):
    """An AC supply: `L1`, `L2`, `L3` and `N` when it was given one.

    Does not hold a voltage of its own: each rail's potential carries the declared voltage.
    """

    L1: SupplyRail
    L2: SupplyRail
    L3: SupplyRail
    N: SupplyRail


class DcSupply(_Rails):
    """A DC supply: `plus`, `minus` and `mid` when the source has an M conductor.

    Stands in a series whole, as a power path's poles, or by one rail, as a control path's.
    Does not have a `mid` rail unless the source has an M conductor.
    """

    plus: SupplyRail
    minus: SupplyRail
    mid: SupplyRail
