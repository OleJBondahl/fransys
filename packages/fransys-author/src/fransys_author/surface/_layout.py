"""Layout hints: `d.layout.chain`, `order`, `symbol` and more, through the engine (EA11)."""

from typing import TYPE_CHECKING
lazy from collections.abc import Mapping
lazy from decimal import Decimal

from fransys_author.errors import AuthorError
from fransys_author.handles import Item
from fransys_author.surface._links import engine_handle
from fransys_author.surface._side import hint_side
from fransys_model.vocab import FunctionKind
lazy from fransys_author.design import Design as EngineDesign
lazy from fransys_author.handles import Group, Terminal
lazy from fransys_author.surface._device import Device
lazy from fransys_author.surface._handles import Fn
lazy from fransys_author.surface._strip import TerminalStrip
lazy from fransys_model.kernel import Id
lazy from fransys_model.layout import SheetFormat, Side

if TYPE_CHECKING:
    from fransys_author.surface.design import Design


class Layout:
    """The drawing hints of one design, each written through the engine.

    Does not draw or place anything itself: every hint only advises the layout engine.
    """

    def __init__(self, engine: EngineDesign) -> None:
        """Hold the engine `Design`; `d.layout` makes these."""
        self._engine = engine

    def chain(self, *functions: Fn | Device | Terminal) -> None:
        """Advise one drawn current path through the functions, source first.

        Does not connect anything: it only advises the layout engine.
        """
        handles = [engine_handle(f, "d.layout.chain", terminal=True) for f in functions]
        self._engine.chain(*handles)

    def keep_together(self, *groups: Group) -> None:
        """Advise that these function groups share a page when they fit.

        Does not place anything: it only advises the layout engine.
        """
        self._engine.keep_together(*groups)

    def break_before(self, group: Group) -> None:
        """Advise a new page before this function group.

        Does not draw or place anything: it only advises the layout engine.
        """
        self._engine.break_before(group)

    def order(self, *groups: Group) -> None:
        """Advise that each neighbour pair of function groups is drawn in this order.

        Does not draw or place anything: it only advises the layout engine.
        """
        self._engine.order(*groups)

    def symbol(
        self,
        target: Fn | Device | FunctionKind,
        symbol: str,
        port_map: dict[str, str] | None = None,
    ) -> None:
        """Advise the library symbol `symbol` for a function, a device or a function kind.

        Does not draw anything itself; a kind is a name (`FunctionKind.X`), never a string.
        """
        if isinstance(target, str):
            msg = f"d.layout.symbol: a kind is a name: FunctionKind.X, got {target!r}"
            raise AuthorError(msg)
        kind = isinstance(target, FunctionKind)
        handle = target if kind else engine_handle(target, "d.layout.symbol")
        self._engine.symbol(handle, symbol, port_map)  # ty: ignore[invalid-argument-type] -- Item | Fn | FunctionKind, narrowed above

    def draw_in(self, function: Fn | Device, group: Group) -> None:
        """Advise drawing the function in this group, whatever its device's place says.

        Does not place the device: it only advises the layout engine.
        """
        handle = engine_handle(function, "d.layout.draw_in")
        fn = handle.as_function() if isinstance(handle, Item) else handle
        self._engine.draw_in(fn, group)  # ty: ignore[invalid-argument-type] -- terminal=False never returns a Terminal

    def side(self, target: Fn | Device | Terminal | TerminalStrip, side: Side) -> None:
        """Advise the edge, `fr.ABOVE` or `fr.BELOW`, a unit's interface stands on.

        Does not move anything itself: it only advises the layout engine. `target` is a field of
        the unit's interface, as `u1.bus_in`; an interface with no harness line ignores it.
        """
        hint_side(self._engine, target, side)

    def sheet(self, name: str, **numbers: int | Decimal) -> Id[SheetFormat]:
        """Advise a sheet format by name and numbers; returns its handle for `profile`.

        Does not draw anything: it only advises the layout engine.
        """
        return self._engine.sheet(name, **numbers)

    def profile(  # noqa: PLR0913 -- one keyword per profile field, as the model's `Profile` has
        self,
        *,
        sheet: Id[SheetFormat] | None = None,
        column_gap: int | None = None,
        row_gap: int | None = None,
        row_spacing: int | None = None,
        route_margin: int | None = None,
        text_height: int | None = None,
        marker_padding: int | None = None,
        route_turn_penalty: int | None = None,
        route_crossing_penalty: int | None = None,
        hide_unused_pins: bool | None = None,
        band_ranks: Mapping[str, int] | None = None,
        group_ranks: Mapping[str, int] | None = None,
    ) -> None:
        """Advise the layout numbers of the model, at most one profile.

        Does not draw anything; a keyword left out keeps its house value, a rank map replaces whole.
        """
        given = {
            "column_gap": column_gap,
            "row_gap": row_gap,
            "row_spacing": row_spacing,
            "route_margin": route_margin,
            "text_height": text_height,
            "marker_padding": marker_padding,
            "route_turn_penalty": route_turn_penalty,
            "route_crossing_penalty": route_crossing_penalty,
            "hide_unused_pins": hide_unused_pins,
            "band_ranks": None if band_ranks is None else frozendict(band_ranks),
            "group_ranks": None if group_ranks is None else frozendict(group_ranks),
        }
        self._engine.profile(sheet=sheet, **{k: v for k, v in given.items() if v is not None})


class Layouts:
    """The `layout` property of the surface `Design`."""

    @property
    def layout(self: "Design") -> Layout:
        """The drawing hints: `d.layout.chain`, `order`, `symbol` and the rest.

        Does not draw anything: its hints only advise the layout engine.
        """
        return Layout(self._engine)
