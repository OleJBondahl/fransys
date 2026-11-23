"""The drawing scopes of the core path: one per location of the placed functions (PAGE-02, Ruling 50).

`drawing_scopes` splits the kit's symbols by the location of their function; `frame_titles`, `bare_pins` and `cut_lines` read the model for them.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import (
    drawn_pieces,
    far_pins,
    function_abroad,
    function_is_idle_terminal,
    function_item,
    function_replicas,
    function_scopes,
    item_unit,
    port_function,
    stub_far,
    unit_index,
    unit_location,
    unit_parent,
)
from fransys_model.derive.drawing_text import external_frame_title, outline_title
from fransys_model.derive.order import locations_in_order, units_in_order
from fransys_model.kernel import render_id

from .kit_keys import function_of
from .placement_ids import net_key, pin_ports, symbol_key

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.core import PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Port, Unit

    from .placement_kit import PickKey, SymbolKit


__all__ = ["DrawingScope", "bare_pins", "cut_lines", "drawing_scopes", "frame_titles", "piece_names"]


@dataclass(frozen=True, slots=True)
class DrawingScope:
    """One drawing set: its unit (`None` for the top level), its location and its symbol ids."""

    of_unit: Id[Unit] | None
    location: Id[AspectNode] | None
    symbols: frozenset[str]
    copies: frozenset[str] = frozenset()
    replicas: frozenset[str] = frozenset()
    abroad: frozenset[str] = frozenset()
    frames: tuple[tuple[str, frozenset[str]], ...] = ()

    @property
    def away(self) -> frozenset[str]:
        """The symbols drawn here but homed in another set: copies and replicas."""
        return self.copies | self.replicas


type _Filed = dict[tuple[Id[Unit] | None, Id[AspectNode] | None], set[str]]


def _filed(model: Model, kit: SymbolKit) -> tuple[_Filed, _Filed, _Filed, _Filed]:
    """The symbols each set draws, of them the copies, the replicas and the ends printed in another document."""
    found: _Filed = {}
    copied: _Filed = {}
    replicated: _Filed = {}
    abroad: _Filed = {}
    for function in kit:
        home, *copies = function_scopes(model, function_of(model, function))
        replicas = function_replicas(model, function_of(model, function))
        for key in function_abroad(model, function_of(model, function)):
            abroad.setdefault(key, set()).add(symbol_key(model, function))
        key_of = symbol_key(model, function)
        for key in (home, *copies):
            found.setdefault(key, set()).add(key_of)
            if key in replicas:
                replicated.setdefault(key, set()).add(key_of)
            elif key != home:
                copied.setdefault(key, set()).add(key_of)
    return found, copied, replicated, abroad


type _Framed = dict[tuple[Id[Unit] | None, Id[AspectNode] | None], dict[str, set[str]]]


def home_unit(model: Model, function: PickKey) -> Id[Unit] | None:
    """The unit of a function's item: its own, never a scope it is drawn in as a rail replica (R830)."""
    return item_unit(model, function_item(model, function_of(model, function)))


def frame_titles(model: Model, kit: SymbolKit) -> dict[str, tuple[str, str]]:
    """Each frame key `DrawingScope.frames` holds -> its es symbol key and its title: a unit's, or the external root's own, empty by default."""
    roots = unit_index(model).external_root
    found: dict[str, tuple[str, str]] = {}
    for function in kit:
        if (home := home_unit(model, function)) is not None:
            found[render_id(home)] = ("unit-outline", outline_title(model, home))
        if (root := roots.get(function_item(model, function_of(model, function)))) is not None:
            found[render_id(root)] = ("unit-outline-by-others", external_frame_title())
    return found


def _replica_frames(model: Model, function: PickKey, found: _Framed) -> None:
    """File `function`'s symbol under its home unit's frame in each unit set that draws it as a replica (R900 G9)."""
    home = home_unit(model, function)
    for key in function_replicas(model, function_of(model, function)):
        if home is not None and key[0] is not None:
            found.setdefault(key, {}).setdefault(render_id(home), set()).add(symbol_key(model, function))


def _external_frames(model: Model, function: PickKey, found: _Framed) -> None:
    """File an external `function`'s symbol under its root's frame in each set of a page with no unit above it (UNIT-SCOPE, R631 B6)."""
    root = unit_index(model).external_root.get(function_item(model, function_of(model, function)))
    if root is None:
        return
    for key in function_scopes(model, function_of(model, function)):
        if key[0] is None or unit_parent(model, key[0]) is None:
            found.setdefault(key, {}).setdefault(render_id(root), set()).add(symbol_key(model, function))


def _framed(model: Model, kit: SymbolKit) -> _Framed:
    """Per set, the symbols it draws grouped by frame key: replicas by their own unit (never a place set, R833), external symbols by their root."""
    found: _Framed = {}
    for function in kit:
        _replica_frames(model, function, found)
        _external_frames(model, function, found)
    return found


def drawing_scopes(model: Model, kit: SymbolKit) -> tuple[DrawingScope, ...]:
    """The scopes of the kit's functions, filed as today's engine files them (layout-0081).

    Top level first: by location in `derive.order` order, no location last. Then one set per unit
    in `units_in_order`, at the unit's own location; a unit's functions are never split by place.
    """
    found, copied, replicated, abroad = _filed(model, kit)
    framed = _framed(model, kit)
    located = locations_in_order(model, (p for u, p in found if u is None and p is not None))
    top = [*located, *([None] if (None, None) in found else [])]
    keys = [(None, place) for place in top]
    keys += [(unit, None) for unit in units_in_order(model, (u for u, _ in found if u is not None))]
    return tuple(
        DrawingScope(
            unit,
            place if unit is None else unit_location(model, unit),
            frozenset(found[unit, place]),
            frozenset(copied.get((unit, place), ())),
            frozenset(replicated.get((unit, place), ())),
            frozenset(abroad.get((unit, place), ())),
            tuple((k, frozenset(s)) for k, s in framed.get((unit, place), {}).items()),
        )
        for unit, place in keys
    )


def bare_pins(model: Model, kit: SymbolKit) -> frozenset[PinRef]:
    """The pins a cut net never ends at: none leaves them by a conductor, or an unreached terminal.

    No conductor leaves a pin when `derive.far_pins` finds none at its ports: its function's through path is no conductor (R1544). A
    terminal no wire inside its drawing reaches is drawn only by its table (L7).
    """
    found = set()
    for pin, names in pin_ports(model, kit).items():
        function = port_function(model, names[0])
        idle = function is not None and function_is_idle_terminal(model, function)
        if idle or not far_pins(model, names):
            found.add(pin)
    return frozenset(found)


def cut_lines(model: Model, kit: SymbolKit) -> Mapping[PinRef, str]:
    """The line each pin leaves by: the harness `derive.stub_far` names and the connector it joins.

    The pins of one connector of one harness are one line (R481); a pin with no harness has none.
    """
    found = {}
    for pin, names in pin_ports(model, kit).items():
        ends = stub_far(model, names)
        function = port_function(model, names[0])
        if ends and ends[0][2] is not None and function is not None:
            found[pin] = f"{ends[0][2].value}/{function.value}"
    return found


def piece_names(model: Model, kit: SymbolKit, scope: DrawingScope, joins: Iterable[tuple[Id[Port], Id[Port]]]) -> Mapping[PinRef, str]:
    """Each pin of `scope` with the name of the piece of its net that the scope itself joins (`derive.drawn_pieces`, KI-1090).

    `joins` are the pairs a symbol holds at one node (`placement_joins.node_joins`). The name is the `net_key` of the piece's ports:
    a net id that `net_ports` reads back to a port of the piece.
    """
    of_port = {port: pin for pin, ports in pin_ports(model, kit).items() if pin.sym in scope.symbols for port in ports}
    return {of_port[port]: net_key(model, piece) for piece in drawn_pieces(model, of_port, joins) for port in piece}
