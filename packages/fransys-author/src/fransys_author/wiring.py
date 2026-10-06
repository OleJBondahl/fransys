"""`d.wiring(...)`: a wire maker with defaults (spec A6)."""

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Protocol
lazy from decimal import Decimal

from fransys_model.kernel import AuthoringKey, make_id
from fransys_model.vocab import Conductor, ConductorKind, WireFacet

from ._decimal import as_decimal
from ._keys import scoped, sorted_pair, spliced
from ._origin import caller_origin
from .errors import AuthorError
lazy from .handles import Port, as_port

if TYPE_CHECKING:
    from fransys_model.kernel import Origin, Record

_MINIMUM_RUN_POINTS = 2


class _Recorder(Protocol):
    """What a `Wiring` needs back from the `Design` that made it."""

    def _add(self, record: Record, origin: Origin) -> None: ...


@dataclass(frozen=True, slots=True)
class Wiring:
    """A wire maker: `wire(a, b, **overrides)` and `wire.run(a, b, c, ...)` (spec A6)."""

    _recorder: _Recorder
    _prefix: AuthoringKey
    colour: str
    gauge: Decimal
    label: str | None

    def __call__(  # noqa: PLR0913 -- the two ports and four per-wire overrides (spec A6)
        self,
        a: Port,
        b: Port,
        *,
        n: int | None = None,
        colour: str | None = None,
        gauge: str | Decimal | None = None,
        label: str | None = None,
    ) -> None:
        """One wire between `a` and `b`, keyed by its ports; a parallel one needs `n=2` (A6)."""
        a, b = as_port(a), as_port(b)
        ends = sorted_pair(a.key, b.key)
        key = scoped(self._prefix, "wire", spliced(ends[0]), spliced(ends[1]))
        if n is not None:
            key = scoped(key, "n", str(n))
        conductor = Conductor(
            id=make_id(Conductor, key),
            key=key,
            a=a.id,
            b=b.id,
            kind=ConductorKind.WIRE,
            carrier=None,
        )
        origin = caller_origin()
        self._recorder._add(conductor, origin)
        facet_key = scoped(key, "facet")
        facet = WireFacet(
            id=make_id(WireFacet, facet_key),
            key=facet_key,
            subject=conductor.id,
            colour=colour if colour is not None else self.colour,
            gauge_mm2=as_decimal(gauge if gauge is not None else self.gauge, field="gauge"),
            length_mm=None,
            label=label if label is not None else self.label,
        )
        self._recorder._add(facet, origin)

    def run(
        self,
        *ports: Port,
        n: int | None = None,
        colour: str | None = None,
        gauge: str | Decimal | None = None,
        label: str | None = None,
    ) -> None:
        """One wire between each neighbouring pair of `ports`: a daisy chain (spec A6)."""
        if len(ports) < _MINIMUM_RUN_POINTS:
            msg = f"wire.run needs at least {_MINIMUM_RUN_POINTS} ports, got {len(ports)}"
            raise AuthorError(msg)
        for a, b in pairwise(ports):
            self(a, b, n=n, colour=colour, gauge=gauge, label=label)


_LINK_KINDS = {
    "mount": ConductorKind.MOUNT,
    "bus": ConductorKind.BUSBAR,
    "rail": ConductorKind.RAIL,
}


class _Linkable(Protocol):
    """What `LinkScope.link` reads of its `Scope`."""

    @property
    def _prefix(self) -> AuthoringKey: ...

    @property
    def _design(self) -> _Recorder: ...


class LinkScope:
    """The `link` method of `Scope`, kept here because `design.py` has no room to grow."""

    __slots__ = ()

    def link(self: _Linkable, a: Port, b: Port, *, kind: str) -> None:
        """A link, `"mount"`, `"bus"` or `"rail"`: closes its net, never a wire (author-0012)."""
        if kind not in _LINK_KINDS:
            msg = f"{kind!r} is not a valid link kind; valid: {', '.join(_LINK_KINDS)}"
            raise AuthorError(msg)
        if a.id == b.id:
            msg = f"d.link needs two different ports; got '{'/'.join(a.key)}' twice"
            raise AuthorError(msg)
        ends = sorted_pair(a.key, b.key)
        key = scoped(self._prefix, "link", kind, spliced(ends[0]), spliced(ends[1]))
        conductor = Conductor(
            id=make_id(Conductor, key),
            key=key,
            a=a.id,
            b=b.id,
            kind=_LINK_KINDS[kind],
            carrier=None,
        )
        self._design._add(conductor, caller_origin())
