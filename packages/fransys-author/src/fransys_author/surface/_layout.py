"""Layout hints: `d.layout.order`, `symbol` and more, through the engine."""

from typing import TYPE_CHECKING, NoReturn

from fransys_author.surface._removed import refuse
lazy from fransys_author.design import Design as EngineDesign
lazy from fransys_author.handles import Group

if TYPE_CHECKING:
    from fransys_author.surface.design import Design


class Layout:
    """The drawing hints of one design, each written through the engine.

    Does not draw or place anything itself: every hint only advises the layout engine.
    """

    def __init__(self, engine: EngineDesign) -> None:
        """Hold the engine `Design`; `d.layout` makes these."""
        self._engine = engine

    def order(self, *groups: Group) -> None:
        """Advise that each neighbour pair of function groups is drawn in this order.

        Does not draw or place anything: it only advises the layout engine.
        """
        self._engine.order(*groups)

    def profile(self, *, hide_unused_pins: bool | None = None) -> None:
        """Advise the layout numbers of the model, at most one profile.

        Does not draw anything; a keyword left out keeps its house value.
        """
        given = {} if hide_unused_pins is None else {"hide_unused_pins": hide_unused_pins}
        self._engine.profile(**given)

    if not TYPE_CHECKING:

        def __getattr__(self, name: str) -> NoReturn:
            refuse("Layout", name)


class Layouts:
    """The `layout` property of the surface `Design`."""

    @property
    def layout(self: "Design") -> Layout:
        """The drawing hints: `d.layout.order` and the rest.

        Does not draw anything: its hints only advise the layout engine.
        """
        return Layout(self._engine)
