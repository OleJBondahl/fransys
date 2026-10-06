"""Surface mixin for cables: `cable` and the `Cable` handle with its cores (EA5, EA7)."""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
lazy from types import EllipsisType

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._device import part_mpn
from fransys_author.surface._pairing import Ends, pair
from fransys_author.surface._strip import TerminalStrip
from fransys_author.surface._tags import floating_name
from fransys_author.surface.colours import GNYE
from fransys_model.vocab import PortRole

if TYPE_CHECKING:
    from fransys_author.handles import Cable as EngineCable
    from fransys_author.surface._device import Device
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


def _outer(end: Port | Terminal) -> Port:
    """A terminal stands for its field side, `.outer`: a cable core goes to the field."""
    return end.outer if isinstance(end, Terminal) else end


def _name(element: object) -> str:
    label = getattr(element, "_label", None) or getattr(element, "_tag", None)
    return str(label or type(element).__name__)


class Cable:
    """One cable: `W1.core(BN, a, b)` wires a core by colour or number; a series lands it.

    Does not guess a core: a doubled or missing colour raises and lists the candidates.
    """

    def __init__(self, label: str, cable: EngineCable) -> None:
        """Wrap the engine `cable` under `label`; `d.cable` makes these."""
        self._label, self._cable = label, cable

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

    def core(self, which: str | int, a: Port | Terminal, b: Port | Terminal) -> None:
        """Wire core `which` (a colour code or a 1-based number) between `a` and `b`.

        Does not accept a non-GNYE core on a PE port, or a colour twice in the part: say the number.
        """
        index = self._index(which)
        ends = (_outer(a), _outer(b))
        self._refuse_pe(index, ends)
        self._cable.core(index, *ends)

    def _series_width(self) -> None:
        """A cable sets no width: its neighbours do."""

    def _pe_end(self, element: object, ends: Ends) -> Port:
        if ends.pe is not None:
            return ends.pe
        if isinstance(element, TerminalStrip):
            return element._take_pe().outer
        msg = f"{self._label} has a GNYE core, but {_name(element)} has no PE port"
        raise AuthorError(msg)

    def _land_pe(self, pe_core: int | None, before: _Side, after: _Side) -> None:
        """Wire the GNYE core when a neighbour has a PE port; else it stays spare."""
        if pe_core is not None and any(ends.pe is not None for _, ends in (before, after)):
            self.core(pe_core, *(self._pe_end(el, ends) for el, ends in (before, after)))

    def _series_between(self, design: Design, before: _Side, after: _Side) -> None:  # noqa: ARG002 -- protocol
        """Core i joins `before`'s load i to `after`'s line i, in core order without GNYE."""
        pairs = pair(before[1].load, after[1].line)
        pe_core = next((i for i, c in enumerate(self._colours, 1) if c == GNYE), None)
        plain = [i for i in range(1, len(self._colours) + 1) if i != pe_core]
        if len(plain) < len(pairs):
            msg = f"{self._label} has {len(plain)} cores for {len(pairs)} poles"
            raise AuthorError(msg)
        for index, (a, b) in zip(plain, pairs, strict=False):
            self.core(index, a, b)
        self._land_pe(pe_core, before, after)


class Cables:
    """The `cable` call of `Design`."""

    def cable(  # noqa: PLR0913 -- the call's own spec signature (EA5), keyword-only facts
        self: Design,
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
            parent=None if parent is None else parent._item,
            external=external,
        )
        return Cable(name or tag or "", engine)
