"""Links: `earth`, `net`, `busbar`, `rail_bond`, `mate` and `harness` through the engine (EA7)."""

from typing import TYPE_CHECKING
lazy from types import EllipsisType

from fransys_author.errors import AuthorError
from fransys_author.handles import Terminal
from fransys_author.surface._device import Device
from fransys_author.surface._handles import Fn
from fransys_author.surface._signals import CONTROL
from fransys_author.surface._tags import bare
from fransys_author.surface._wire import _port
from fransys_model.vocab import NetClass
lazy from fransys_author.handles import Port

if TYPE_CHECKING:
    from fransys_author.handles import Fn as EngineFn
    from fransys_author.handles import Item
    from fransys_author.surface.design import Design


def engine_handle(
    target: object, call: str, *, terminal: bool = False
) -> Item | EngineFn | Terminal:
    """The engine handle of a surface `Device` or `Fn` (a `Terminal` too when `terminal`)."""
    if isinstance(target, Device):
        return target._item
    if isinstance(target, Fn):
        return target._fn
    if terminal and isinstance(target, Terminal):
        return target
    msg = f"{call} takes a device or a function, got {type(target).__name__}"
    raise AuthorError(msg)


def _kind(kind: object) -> NetClass:
    if not isinstance(kind, NetClass):
        msg = f"a kind is a name: NetClass.X, got {kind!r}"
        raise AuthorError(msg)
    if kind is NetClass.PE:
        msg = "d.net does not make a protective earth net: use d.earth"
        raise AuthorError(msg)
    if kind is NetClass.POWER:
        msg = "d.net does not make a power net: use a supply's rails (d.ac_supply, d.dc_supply)"
        raise AuthorError(msg)
    return kind


class Links:
    """The link calls of the surface `Design`."""

    def earth(self: "Design", *pins: Port | Terminal) -> None:
        """Join the pins to protective earth, one `PE` net.

        Does not take a name or a net kind; a terminal lands on its inner side.
        """
        if not pins:
            msg = "d.earth joins at least one pin, got none"
            raise AuthorError(msg)
        self._engine.net("PE", *[_port(pin) for pin in pins], cls="pe")

    def net(self: "Design", name: str, *pins: Port | Terminal, kind: NetClass = CONTROL) -> None:
        """Declare the signal net `name` over the pins, of the `NetClass` `kind`.

        Does not make a `PE` or `POWER` net (earth and supplies own those) or take a potential.
        """
        net_class = _kind(kind)
        self._engine.net(name, *[_port(pin) for pin in pins], cls=net_class.value)

    def busbar(self: "Design", a: Port | Terminal, b: Port | Terminal) -> None:
        """Join two pins by a busbar: a conductor of kind `bus`.

        Does not make a wire; the same pin twice raises.
        """
        self._engine.link(_port(a), _port(b), kind="bus")

    def rail_bond(self: "Design", a: Port | Terminal, b: Port | Terminal) -> None:
        """Join two pins of one rail by a bond: a conductor of kind `rail`.

        Does not make a wire; the same pin twice raises.
        """
        self._engine.link(_port(a), _port(b), kind="rail")

    def mate(self: "Design", a: Device | Fn, b: Device | Fn) -> None:
        """Plug connector `a` into connector `b`.

        Does not take pins, strings or terminals; a device needs exactly one function.
        """
        self._engine.mate(engine_handle(a, "d.mate"), engine_handle(b, "d.mate"))  # ty: ignore[invalid-argument-type] -- Item | Fn | Terminal narrowed by the call's own check

    def harness(
        self: "Design",
        tag: str | None = None,
        *,
        name: str | None = None,
        place: str | EllipsisType | None = ...,
        external: bool = False,
    ) -> Device:
        """Add the part-less harness `tag` (printed `-tag`); `place=None` gives it no place.

        Does not take a prefixed tag or a part. `external=True` flags it as supplied by others.
        """
        if tag is not None:
            bare(tag, "harness")
        elif name is None:
            msg = "give a tag, or name= for a harness with no tag"
            raise AuthorError(msg)
        key = self._claim(name or tag or "", per_function=True)
        item = self._engine.item(
            None,
            name=key,
            tag=tag,
            at=self._place_node(self._place if place is ... else place),
            group=self._group,
            external=external,
        )
        return Device(name or tag or "", item)
