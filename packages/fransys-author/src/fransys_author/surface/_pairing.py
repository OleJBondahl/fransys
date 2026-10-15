"""The pole rule and the pairing of series ends, pure functions over the part's facts."""

from typing import TYPE_CHECKING, NamedTuple, Protocol, cast, runtime_checkable

from fransys_author.errors import AuthorError
from fransys_model.kernel import make_id
from fransys_model.vocab import (
    ConductorMark,
    FunctionTemplate,
    InternalLink,
    LinkKind,
    PlcChannelFacet,
    PlcRequestFacet,
    PortRole,
    PortTemplate,
    function_poles,
    pole_order,
    port_order_key,
)
from fransys_model.vocab import Port as ModelPort

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_author.handles import Fn, Port
    from fransys_model.kernel import Draft, Id
    from fransys_model.vocab import Function, Pole

    from .design import Design

_PHASE = tuple(ConductorMark)
NO_SIDE_FIX = (
    "its part states no line side. The part's author adds the port key `side` in the part file; "
    "otherwise wire its pins with d.detail.wire(pin, pin, wire=...)"
)
PARTLESS_FIX = (
    "{what} belongs to a device with no part, so this call cannot read its poles. A series takes "
    "such a device only as its last element: make it the last element, or wire it per core "
    "with d.detail.wire(pin, pin, wire=...)"
)
_BY_HAND = "wire the poles one by one with d.detail.wire(pin, pin, wire=...)"


def label_of(element: object) -> str:
    """The printed name of a series element, for a message: `Q1`, `K1.coil`, `X1`, `230V`."""
    fn = getattr(element, "_fn", None)
    label = (
        getattr(element, "_label", None)
        or getattr(element, "_tag", None)
        or getattr(element, "_name", None)
    )
    if fn is not None and label:
        return f"{label}.{fn.name}"
    return str(label or type(element).__name__)


class End(NamedTuple):
    """One end of a series element: a port and its conductor mark, `None` when unstated.

    Does not read a marking or a name: the mark is the part's `conductor_mark` fact.
    """

    port: Port
    mark: ConductorMark | None


class Ends(NamedTuple):
    """The line ends, the load ends and the optional PE port of one series element.

    Does not pair anything: `pair` joins one element's load ends to the next one's line ends.
    """

    line: tuple[End, ...]
    load: tuple[End, ...]
    pe: Port | None = None


@runtime_checkable
class SeriesElement(Protocol):
    """What a handle needs to stand in a series; `Device`, `Fn` and `Pin` are dispatched apart.

    Does not take a `Design` it does not need: `design` is the one the series is written in.
    """

    def _series_ends(self, design: Design, width: int | None) -> Ends: ...

    def _series_width(self) -> int | None: ...


class PartFacts:
    """The part library's port templates, function templates and links, indexed once.

    Does not copy the design: it asks the design draft for each handle's template.
    """

    def __init__(self, library: Draft, design: Draft) -> None:
        """Index `library`; `design` is the engine draft the handles' records live in."""
        self._design = design
        self.templates: dict[Id[PortTemplate], PortTemplate] = {}
        self._functions: dict[Id[FunctionTemplate], FunctionTemplate] = {}
        self._channels: dict[Id[FunctionTemplate], PlcChannelFacet] = {}
        for record in library.records():
            if isinstance(record, PortTemplate):
                self.templates[record.id] = record
            elif isinstance(record, FunctionTemplate):
                self._functions[record.id] = record
            elif isinstance(record, PlcChannelFacet):
                self._channels[record.subject] = record
        self._links: dict[Id[FunctionTemplate], list[InternalLink]] = {}
        for record in library.records():
            if isinstance(record, InternalLink):
                owner = self.templates[record.a].function
                self._links.setdefault(owner, []).append(record)

    def port_template(self, port: Port) -> PortTemplate:
        """The template of the engine `port`.

        Raises `AuthorError` for a port made without a part: it has no template.
        """
        record = cast("ModelPort", self._design.record_of(port.id))
        if record.template is None:
            raise AuthorError(PARTLESS_FIX.format(what=f"pin {port.name!r}"))
        return self.templates[record.template]

    def function_template(self, fn: Fn) -> FunctionTemplate:
        """The template of the engine function `fn`.

        Raises `AuthorError` for a function made without a part: it has no template.
        """
        record = cast("Function", self._design.record_of(fn.id))
        if record.template is None:
            raise AuthorError(PARTLESS_FIX.format(what=f"function {fn.name!r}"))
        return self._functions[record.template]

    def partless(self, fn: Fn) -> bool:
        """Whether `fn` belongs to a device made without a part (`template` is `None`)."""
        return cast("Function", self._design.record_of(fn.id)).template is None

    def channel(self, fn: Fn) -> PlcChannelFacet | None:
        """The `plc_channel` fact of the function `fn`, `None` when it is no PLC channel.

        A function made without a part has no template and is no channel.
        """
        record = cast("Function", self._design.record_of(fn.id))
        return self._channels.get(cast("Id[FunctionTemplate]", record.template))

    def requests(self) -> dict[Id[Function], PlcRequestFacet]:
        """The PLC request of each function that has one, as the design stands now.

        Does not cache: a request made after the last call counts.
        """
        found = (r for r in self._design.records() if isinstance(r, PlcRequestFacet))
        return {r.subject: r for r in found}

    def links(self, fn: Fn) -> list[InternalLink]:
        """The internal links of the function `fn`, in no order.

        Does not decide which link is a pole: `function_poles` does.
        """
        return self._links.get(self.function_template(fn).id, [])

    def mark(self, port: Port) -> ConductorMark | None:
        """The conductor mark of `port`, `None` when the part does not state one.

        Does not infer a mark from the pin's name or marking.
        """
        if cast("ModelPort", self._design.record_of(port.id)).template is None:
            return None
        return self.port_template(port).conductor_mark


def _need_sides(fn: Fn, found: tuple[Pole, ...]) -> None:
    """Raise when a pole has no line side; its pins are named in the message only."""
    for pole in found:
        if pole.line is None:
            a, b = pole.ends
            msg = f"{fn.name!r} pole {a.name}/{b.name} has no line side: {NO_SIDE_FIX}"
            raise AuthorError(msg)


def _phase(end: End) -> int:
    return _PHASE.index(cast("ConductorMark", end.mark))


def marking_order(facts: PartFacts, ports: list[Port]) -> list[Port]:
    """`ports` in the vocab's marking order: the key `pole_order` sorts a pole's ends by."""
    templates = {port: facts.port_template(port) for port in ports}
    return sorted(ports, key=lambda port: port_order_key(templates[port]))


def _line_load(facts: PartFacts, ports: list[Port]) -> list[tuple[Port, Port]]:
    """The vocab's pole of two pins, as (line, load); empty when neither pin is a line side."""
    a, b = (facts.port_template(port) for port in ports)
    key = (*a.key, "pair", b.name)
    link = InternalLink(
        id=make_id(InternalLink, key), key=key, a=a.id, b=b.id, kind=LinkKind.SWITCHED
    )
    (pole,) = pole_order([link], facts.templates)
    if pole.line is None:
        return []
    by_template = {facts.port_template(port).id: port for port in ports}
    return [(by_template[pole.ends[0].id], by_template[pole.ends[1].id])]


def _without_links(facts: PartFacts, fn: Fn) -> list[tuple[Port, Port]]:
    """One-port function, a line/load pair of pins, or pins carrying marks (a motor)."""
    ports = [port for port in fn.ports if port.role is not PortRole.PE]
    if len(ports) == 1:
        return [(ports[0], ports[0])]
    if len(ports) == 2 and (pair_ := _line_load(facts, ports)):  # noqa: PLR2004 -- a pole has two ends
        return pair_
    if ports and all(facts.mark(port) is not None for port in ports):
        return [(port, port) for port in marking_order(facts, ports)]
    return []


def poles(facts: PartFacts, fn: Fn, *, partless_ok: bool = False) -> list[tuple[Port, Port]]:
    """The poles of `fn` as (line port, load port), in the model's pole order.

    Layout twin: `fransys_layout.stages.resolve.poles_and_pairs`; the model's `function_poles`.
    Does not read a name or a marking or guess a side. `partless_ok`: pins are poles, in order.
    """
    if partless_ok and facts.partless(fn):
        return [(port, port) for port in fn.ports if port.role is not PortRole.PE]
    template = facts.function_template(fn)
    found = function_poles(template.kind, facts.links(fn), facts.templates)
    if not found:
        return _without_links(facts, fn)
    _need_sides(fn, found)
    by_template = {facts.port_template(port).id: port for port in fn.ports}
    return [(by_template[pole.ends[0].id], by_template[pole.ends[1].id]) for pole in found]


def ends_of(facts: PartFacts, fn: Fn, *, partless_ok: bool = False) -> Ends:
    """The line ends, load ends and PE port of `fn`, one pair per pole of `poles`.

    Does not pair them with another element's ends: `pair` does.
    """
    pairs = poles(facts, fn, partless_ok=partless_ok)
    pe = next((port for port in fn.ports if port.role is PortRole.PE), None)
    line = tuple(End(a, facts.mark(a)) for a, _ in pairs)
    load = tuple(End(b, facts.mark(b)) for _, b in pairs)
    return Ends(line, load, pe)


def _by_mark(
    source: Sequence[End], load: Sequence[End], names: tuple[str, str]
) -> list[tuple[Port, Port]]:
    first, second = sorted(source, key=_phase), sorted(load, key=_phase)
    a, b = [e.mark.value for e in first], [e.mark.value for e in second]  # ty: ignore[unresolved-attribute] -- marks checked by `pair`
    if a != b:
        msg = (
            f"{names[0]} carries {', '.join(a)} where {names[1]} takes {', '.join(b)}: "
            f"conductors pair by name, so {_BY_HAND}"
        )
        raise AuthorError(msg)
    return [(x.port, y.port) for x, y in zip(first, second, strict=True)]


def _ends_text(ends: Sequence[End]) -> str:
    """`2 poles (L1, N)`: the count, then each end's conductor or pin."""
    named = ", ".join(e.mark.value if e.mark is not None else e.port.name for e in ends)
    return f"{len(ends)} pole{'' if len(ends) == 1 else 's'} ({named})"


def pair(
    source: Sequence[End], load: Sequence[End], names: tuple[str, str] = ("the source", "the load")
) -> list[tuple[Port, Port]]:
    """Pair `source` ends with `load` ends: by conductor mark when all have one, else by position.

    Does not pair unequal counts: the message names both elements, their poles and the call.
    """
    if len(source) != len(load):
        msg = (
            f"{names[0]} leaves with {_ends_text(source)} but {names[1]} takes "
            f"{_ends_text(load)}: use a function of {len(source)} poles there, or {_BY_HAND}"
        )
        raise AuthorError(msg)
    ends = (*source, *load)
    if ends and all(end.mark is not None for end in ends):
        return _by_mark(source, load, names)
    return [(a.port, b.port) for a, b in zip(source, load, strict=True)]
