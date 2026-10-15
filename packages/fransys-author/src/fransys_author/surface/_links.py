"""Links: `earth`, `mate`, `harness` and `rack` through the engine."""

from typing import TYPE_CHECKING
lazy from types import EllipsisType

from fransys_author.errors import AuthorError
from fransys_author.handles import Terminal
from fransys_author.surface._device import Device
from fransys_author.surface._handles import Fn
from fransys_author.surface._tags import bare
from fransys_author.surface._wire import _port
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


class Links:
    """The link calls of the surface `Design`."""

    def earth(self: "Design", *pins: Port | Terminal) -> None:
        """Join the pins to protective earth, one `PE` net.

        Does not take a name or a net kind; a terminal lands on its inner side. A later call in
        the same scope adds its pins to that scope's one `PE` net.
        """
        if not pins:
            msg = "d.earth joins at least one pin, got none"
            raise AuthorError(msg)
        self._engine.earth(*[_port(self, pin) for pin in pins])

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
        item = self._engine.harness_item(
            key,
            tag,
            self._place_node(self._place if place is ... else place),
            self._group,
            external=external,
        )
        return Device(name or tag or "", item, None, tag)

    def rack(
        self: "Design",
        tag: str,
        *,
        name: str | None = None,
        place: str | EllipsisType | None = ...,
        external: bool = False,
    ) -> Device:
        """Add the part-less PLC rack `tag` (printed `-tag`); `place=None` gives it no place.

        Put modules under it with `parent=`.
        Does not make a harness, so the modules print flat.
        """
        bare(tag, "rack")
        key = self._claim(name or tag, per_function=True)
        item = self._engine.item(
            None,
            name=key,
            tag=tag,
            at=self._place_node(self._place if place is ... else place),
            group=self._group,
            external=external,
        )
        return Device(name or tag, item, None, tag)
