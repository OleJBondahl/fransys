"""`d.detail`: the calls for a case no core call writes (author-0042, API-CLARITY C2)."""

from typing import TYPE_CHECKING, NoReturn

from fransys_author.errors import AuthorAttributeError, AuthorError
from fransys_author.surface._detail_rows import wire_pairs
from fransys_author.surface._signals import CONTROL
from fransys_author.surface._wire import PoleWire, RowWire, WireArg, _port, _wire_port, read_wire
from fransys_model.vocab import NetClass
lazy from fransys_author.handles import Port, Terminal
lazy from fransys_author.surface._handles import Fn
lazy from fransys_author.surface._strip import TerminalStrip

if TYPE_CHECKING:
    from fransys_author.surface.design import Design

_MINIMUM_PINS = 2
MOVED_SECTION = "the-detail-calls"  # the heading of moving-to-0.19.md the raise points to


def _kind(kind: object) -> NetClass:
    if not isinstance(kind, NetClass):
        msg = f"a kind is a name: NetClass.X, got {kind!r}"
        raise AuthorError(msg)
    if kind is NetClass.PE:
        msg = "d.detail.net does not make a protective earth net: use d.earth"
        raise AuthorError(msg)
    if kind is NetClass.POWER:
        msg = (
            "d.detail.net does not make a power net: use a supply's rails "
            "(d.ac_supply, d.dc_supply)"
        )
        raise AuthorError(msg)
    return kind


def _check_targets(src: object, targets: object) -> None:
    """Raise `AuthorError` naming the fix when `targets` is not a non-empty list of other pins."""
    if not isinstance(targets, tuple | list):
        msg = (
            "d.detail.star takes its targets as a tuple or list: "
            "one target is d.detail.wire(src, target)"
        )
        raise AuthorError(msg)
    if not targets:
        msg = "d.detail.star needs at least one target: pass (t1, t2, ...)"
        raise AuthorError(msg)
    if any(target is src for target in targets):
        msg = "d.detail.star: src is also one of the targets: drop it from targets"
        raise AuthorError(msg)
    if len({id(target) for target in targets}) != len(targets):
        msg = "d.detail.star: a target is given twice: name each target once"
        raise AuthorError(msg)


def _check_ports(source: Port, ports: list[Port]) -> None:
    """Raise `AuthorError` when two targets, or the source and a target, resolve to one port."""
    if source in ports:
        msg = "d.detail.star: src is also one of the targets: drop it from targets"
        raise AuthorError(msg)
    if len(set(ports)) != len(ports):
        msg = "d.detail.star: a target is given twice: name each target once"
        raise AuthorError(msg)


class Detail:
    """The detail calls of one design: `d.detail.wire`, `star`, `net`, `busbar` and `rail_bond`.

    Each is for a case no core call writes; try `d.series` first.
    Does not pair poles or take the next free terminal, as `d.series` does.
    """

    def __init__(self, design: "Design") -> None:  # noqa: UP037 -- Design imports this module: unquoted, inspect.signature raises NameError
        """Hold the surface `Design`; `d.detail` makes these."""
        self._design = design

    def wire(
        self,
        *pins: Port | Terminal | TerminalStrip | Fn,
        wire: WireArg = None,
        label: str | None = None,
        n: int | None = None,
    ) -> None:
        """Wire the pins: two make one wire, more make a daisy chain, one wire per pair.

        For two named pins off a path, or a hop whose wire differs; try `d.series` first.
        Does not pick a wire or find pins; a terminal lands on its inner side.
        A strip or run as a pin stands for its next free terminal, each place it appears.
        """
        if len(pins) < _MINIMUM_PINS:
            msg = f"d.detail.wire joins at least {_MINIMUM_PINS} pins, got {len(pins)}"
            raise AuthorError(msg)
        ports = [_wire_port(self._design, pin) for pin in pins]
        read = read_wire(self._design, wire)
        if isinstance(read, PoleWire):
            msg = "wire= per pole belongs to d.series: give d.detail.wire one (colour, size)"
            raise AuthorError(msg)
        if isinstance(read, RowWire):
            wire_pairs(self._design, ports, read, n=n, label=label)
        else:
            read.run(*ports, n=n, label=label)

    def star(
        self,
        src: Port | Terminal | TerminalStrip | Fn,
        targets: tuple[Port | Terminal | TerminalStrip | Fn, ...]
        | list[Port | Terminal | TerminalStrip | Fn],
        *,
        wire: WireArg = None,
    ) -> None:
        """Wire `src` to each of `targets`: one wire per target, none between the targets.

        For one point that feeds many; `d.detail.wire(src, *targets)` chains them instead.
        Does not chain the targets, take `label=` or `n=`, or give a strip source two terminals.
        """
        design = self._design
        _check_targets(src, targets)
        source = _wire_port(design, src)
        ports = [_wire_port(design, target) for target in targets]
        _check_ports(source, ports)
        for port in ports:
            self.wire(source, port, wire=wire)

    def net(self, name: str, *pins: Port | Terminal, kind: NetClass = CONTROL) -> None:
        """Declare the signal net `name` over the pins, of the `NetClass` `kind`.

        The pins belong to one net. Wires or one board must realise it; otherwise
        NET_UNREALISED warns.
        Does not make a `PE` or `POWER` net (earth and supplies own those) or take a potential.
        """
        net_class = _kind(kind)
        ports = [_port(self._design, pin) for pin in pins]
        self._design._engine.net(name, *ports, cls=net_class.value)

    def busbar(self, a: Port | Terminal, b: Port | Terminal) -> None:
        """Join two pins by a busbar: a conductor of kind `bus`.

        Does not make a wire; the same pin twice raises.
        """
        design = self._design
        design._engine.link(_port(design, a), _port(design, b), kind="bus")

    def rail_bond(self, a: Port | Terminal, b: Port | Terminal) -> None:
        """Join two pins of one rail by a bond: a conductor of kind `rail`.

        Does not make a wire; the same pin twice raises.
        """
        design = self._design
        design._engine.link(_port(design, a), _port(design, b), kind="rail")


class _Moved:
    """A name that moved to `d.detail`: looking it up raises and names the new home."""

    def __init__(self, core_path: str = "") -> None:
        self._core_path = core_path

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, _instance: object, owner: type | None = None) -> NoReturn:
        name = self._name
        path = f"; a current path is {self._core_path}:" if self._core_path else ":"
        msg = (
            f"d.{name} moved to d.detail.{name} in 0.19.0{path} see moving-to-0.19#{MOVED_SECTION}"
        )
        raise AuthorAttributeError(msg)


class Details:
    """The `detail` property of the surface `Design`, and the four names that left `d`."""

    wire = _Moved("d.series(...)")
    net = _Moved()
    busbar = _Moved()
    rail_bond = _Moved()

    @property
    def detail(self: Design) -> Detail:
        """The detail calls: `d.detail.wire`, `star`, `net`, `busbar` and `rail_bond`.

        Does not wire anything itself: each call is for a case no core call writes.
        """
        return Detail(self)
