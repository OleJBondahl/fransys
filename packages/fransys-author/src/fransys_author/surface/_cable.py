"""Surface mixin for cables: `cable` and the `Cable` handle with its cores ."""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
lazy from types import EllipsisType

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._bar import take_screw
from fransys_author.surface._carry import earth_pin, element_name, refuse_carried
from fransys_author.surface._device import part_mpn
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import Ends, label_of, pair
from fransys_author.surface._parent import cable_parent_item
from fransys_author.surface._strip import TerminalStrip
from fransys_author.surface._tags import floating_name
from fransys_author.surface._unit_strip import take, take_pe
from fransys_author.surface.colours import GNYE, SH
from fransys_model.vocab import PortRole
lazy from fransys_author.surface._device import Device

if TYPE_CHECKING:
    from fransys_author.handles import Cable as EngineCable
    from fransys_author.surface.design import Design

_MM_PER_M = 1000
type _Side = tuple[object, Ends]


def _length_mm(length_m: float | str | Decimal | None) -> int | None:
    """Metres as the engine's whole millimetres; read through `str`, so 4.35 is 4350."""
    if length_m is None:
        return None
    if isinstance(length_m, bool) or not isinstance(length_m, int | float | str | Decimal):
        msg = f"length_m is a number of metres, not {length_m!r}"
        raise AuthorError(msg)
    try:
        mm = Decimal(str(length_m)) * _MM_PER_M
    except InvalidOperation:
        msg = f"length_m {length_m!r} is not a number"
        raise AuthorError(msg) from None
    if not mm.is_finite() or mm != mm.to_integral_value():
        msg = f"length_m {length_m!r} is not a whole number of millimetres"
        raise AuthorError(msg)
    return int(mm)


def _outer(end: Port | Terminal | TerminalStrip | Fn, design: Design | None = None) -> Port:
    """A terminal stands for its field side, `.outer`: a cable core goes to the field.

    A strip or run stands for its next free terminal, the step `d.series` takes.
    """
    if isinstance(end, Fn):
        return take_screw(design, end)
    if isinstance(end, TerminalStrip):
        end = take(end, design, 1)[0]
    return end.outer if isinstance(end, Terminal) else end


class Cable:
    """One cable: `W1.core(BN, a, b)` wires a core by colour or number; a series lands it.

    Does not guess a core: a doubled or missing colour raises and lists the candidates.
    """

    def __init__(self, label: str, cable: EngineCable, design: Design | None = None) -> None:
        """Wrap the engine `cable` under `label`; `d.cable` makes these, `design` its own."""
        self._label, self._cable, self._design = label, cable, design
        self._used: set[int] = set()
        self._by: dict[int, str] = {}  # core number -> the series that landed or parked it

    @property
    def _colours(self) -> tuple[str, ...]:
        return self._cable._core_colours

    def _index(self, which: str | int) -> int:
        """The 1-based core number of colour code or number `which`."""
        if isinstance(which, int) and not isinstance(which, bool):
            return which
        hits = [i for i, colour in enumerate(self._colours, 1) if colour == which]
        if not isinstance(which, str) or not hits:
            msg = f"{self._label} has no {which!r} core; its colours: {', '.join(self._colours)}"
            raise AuthorError(msg)
        if len(hits) > 1:
            msg = f"{self._label} has {len(hits)} {which} cores, numbers {hits}: say the number"
            raise AuthorError(msg)
        return hits[0]

    def _refuse_pe(self, index: int, ends: tuple[Port, Port]) -> None:
        """Only the GNYE core may land on a PE-role port."""
        known = 1 <= index <= len(self._colours)
        if known and self._colours[index - 1] != GNYE and any(p.role is PortRole.PE for p in ends):
            msg = f"core {index} is {self._colours[index - 1]}: the PE core is GNYE (IEC 60204-1)"
            raise AuthorError(msg)

    def _claim(self, index: int) -> None:
        """Take core `index` for a wire or a mark; a second claim is an error."""
        if index in self._used:
            by = f" by {self._by[index]}" if index in self._by else ""
            free = [str(i) for i in range(1, len(self._colours) + 1) if i not in self._used]
            msg = (
                f"{self._label} core {index} is already wired or marked spare{by}; "
                f"free cores: {', '.join(free) or 'none'}, "
                "so wire core(<number>, a, b) with one of them"
            )
            raise AuthorError(msg)
        self._used.add(index)

    def core(
        self,
        which: str | int,
        a: Port | Terminal | TerminalStrip | Fn,
        b: Port | Terminal | TerminalStrip | Fn | None = None,
    ) -> None:
        """Detail: wire core `which` (a colour or a 1-based number) between `a` and `b`.

        Try `d.series` first: it takes the next free core. `core(which, a)` is for `SH` only.
        Does not accept a colour twice, or a non-GNYE core on a PE port.
        """
        index = self._index(which)
        if b is None:
            self._screen_end(index, a)
            return
        ends = (_outer(a, self._design), _outer(b, self._design))
        refuse_carried(self._design, ends)
        self._refuse_pe(index, ends)
        self._claim(index)
        self._cable.core(index, *ends)

    def _screen_end(self, index: int, a: Port | Terminal | TerminalStrip | Fn) -> None:
        if self._colours[index - 1] != SH:
            msg = f"{self._label} core {index} is not SH: park a spare with spare(..., at=)"
            raise AuthorError(msg)
        self._claim(index)
        self._cable.open_core(index, _outer(a, self._design))

    def spare(
        self, *cores: str | int, at: Port | Terminal | TerminalStrip | Fn | None = None
    ) -> None:
        """Core: mark cores spare: `spare(GY)`, `spare(BK, at=x1[7])`, or `spare()`.

        `spare()` marks every core not wired or marked so far, so wire first. `at=` parks one
        core on a pin. Does not take `at=` for an `SH` core (use `core(which, a)`).
        """
        if at is not None and len(cores) != 1:
            msg = f"{self._label} spare(at=) takes exactly one core, got {len(cores)}"
            raise AuthorError(msg)
        indexes = [self._index(c) for c in cores] or [
            i for i in range(1, len(self._colours) + 1) if i not in self._used
        ]
        if at is not None and self._colours[indexes[0] - 1] == SH:
            msg = f"{self._label} core {indexes[0]} is SH: earth it with core(which, a)"
            raise AuthorError(msg)
        for index in indexes:
            self._claim(index)
            self._cable.open_core(index, None if at is None else _outer(at, self._design))

    def _series_width(self) -> None:
        """A cable sets no width: its neighbours do."""

    def _pe_end(self, design: Design, element: object, ends: Ends) -> Port | None:
        """The PE port `element` offers a protective core, `None` when it offers none."""
        if ends.pe is not None:
            return ends.pe
        if isinstance(element, TerminalStrip) and element._pe_mpn is not None:
            return take_pe(element, design).outer
        return None

    def _land_pe(self, design: Design, pe_core: int | None, sides: tuple[_Side, _Side]) -> None:
        """Land the GNYE core on a neighbour's PE port; else mark it spare (CC4, author-0044).

        A load's PE port takes the far end, the strip's next free PE terminal the near end. A side
        with none stays open, earthed as `d.earth` earths a pin; with no PE end at all it is spare.
        """
        if pe_core is None or pe_core in self._used:
            return
        series = self._by[pe_core]
        found = [self._pe_end(design, element, ends) for element, ends in sides]
        landed = tuple(port for port in found if port is not None)
        if not landed:
            self.spare(pe_core)
            return
        if len(landed) == len(found):
            self.core(pe_core, *landed)
        else:
            self._claim(pe_core)
            self._cable.open_core(pe_core, landed[0])
            earth_pin(design, landed[0])
        self._carry(design, sides, found, series)

    @staticmethod
    def _carry(
        design: Design, sides: tuple[_Side, _Side], found: list[Port | None], series: str
    ) -> None:
        """Remember each load PE port the core landed on, so a later wire there is refused."""
        for (element, ends), port in zip(sides, found, strict=True):
            if ends.pe is not None and port is not None:
                design._carried[port.id] = (f"{element_name(element)}:{port.name}", series)

    def _series_between(
        self, design: Design, before: _Side, after: _Side, series: str = "a series"
    ) -> None:
        """Core i joins `before`'s load i to `after`'s line i, in core order without GNYE.

        Each pass of a cable takes its next free cores, so a return leg takes the next core.
        `series` names the call in a later refusal.
        """
        pairs = pair(before[1].load, after[1].line, (label_of(before[0]), label_of(after[0])))
        pe_core = next((i for i, c in enumerate(self._colours, 1) if c == GNYE), None)
        taken = self._used | {pe_core}
        plain = [i for i in range(1, len(self._colours) + 1) if i not in taken]
        if len(plain) < len(pairs):
            msg = (
                f"{self._label} has {len(plain)} free cores for {len(pairs)} poles: "
                "use a cable with more cores"
            )
            raise AuthorError(msg)
        for index, (a, b) in zip(plain, pairs, strict=False):
            self.core(index, a, b)
        if pe_core is not None:
            self._by.setdefault(pe_core, series)
        self._land_pe(design, pe_core, (before, after))


class Cables:
    """The `cable` call of `Design`."""

    def cable(  # noqa: PLR0913 -- the call's own spec signature, keyword-only facts
        self: "Design",
        tag: str | None,
        part: str | type[Device],
        *,
        length_m: float | str | Decimal | None = None,
        place: str | EllipsisType | None = ...,
        parent: Device | None = None,
        name: str | None = None,
        external: bool = False,
    ) -> Cable:
        """Add cable `tag` (printed `-tag`) of `part`; `length_m` is metres, stored as whole mm.

        Does not take a prefixed tag or length_mm. `None` needs `name=`; `external=True` flags it.
        """
        name = floating_name(tag, name, "cable")
        mm = _length_mm(length_m)
        where = self._place if place is ... else place
        key = self._claim(name or tag or "", per_function=True)
        engine = self._engine.cable(
            part_mpn(part),
            name=key,
            tag=tag,
            length_mm=mm,
            at=self._place_node(where),
            group=self._group,
            parent=None if parent is None else cable_parent_item(parent),
            external=external,
        )
        return Cable(name or tag or "", engine, self)
