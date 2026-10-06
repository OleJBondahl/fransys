"""`_symbol_geometry.oriented_symbol` (the D6 recipe) against the real layout goldens.

The marker-facing derivation (D8, layout-0038) rests on one property: for every real
`layout.link_marker`, exactly one port of the owning placement's oriented symbol lands
on the marker's own recorded `(x, y)`. This is proven here, directly, over both goldens,
because it is the foundation every later marker-drawing test builds on -- if this ever
stops holding for a real placement, that is a stop-and-ask, not a fallback (orchestrator
and designer ruling, 2026-09-22).
"""

import dataclasses

from fransys_render._symbol_geometry import _generic_box_port_names, oriented_symbol, to_grid

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Orientation,
    Page,
    PageRole,
    PlacementView,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole
from fransys_model.vocab.tables import ports

_ORIGIN = Origin(
    file="packages/fransys-render/tests/test_symbol_geometry.py", line=1, note="invented"
)

# The narrow golden holds 7 markers, not 9. The removed pair is the K1:aux:13 <-> S0:nc_2:22 wire
# (wire 17): K1's aux now stands on page 1 (layout-0049, D2: the aux stands second in =P1), so
# the wire is drawn on page 1 and is no longer cut.
# Step 5 (layout-0093, M12): a wire that turns back round its device is a reference pair, so the
# wide golden holds 8 markers and the narrow one 9.
# DRAWN-ENDS (layout-0099 V5, layout-0103): a contact moves under its far pin, so one more wire
# is drawn whole: 7 and 8.
_EXPECTED_MARKER_COUNTS = {
    "cabinet_laid_out": 7,
    "cabinet_narrow_laid_out": 8,
}


def _owning_placement(model, marker: LinkMarker) -> SymbolPlacement:
    function = ports(model)[marker.port].function
    placements = [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.function == function and p.page == marker.page
    ]
    assert len(placements) == 1, (marker.id, placements)
    return placements[0]


def _matching_ports(model, placement: SymbolPlacement, marker: LinkMarker) -> list[str]:
    symbol = oriented_symbol(model, placement)
    assert symbol is not None, placement.symbol
    matches = []
    for port in symbol.ports:
        abs_x = placement.x + to_grid(port.position.x)
        abs_y = placement.y + to_grid(port.position.y)
        if (abs_x, abs_y) == (marker.x, marker.y):
            matches.append(port.id)
    return matches


def _assert_every_marker_has_exactly_one_matching_port(model, expected_count: int) -> None:
    markers = layout_of(model, LinkMarker)
    assert len(markers) == expected_count
    assert len(markers) > 0

    for marker in markers.values():
        placement = _owning_placement(model, marker)
        matches = _matching_ports(model, placement, marker)
        assert len(matches) == 1, (marker.id, placement.symbol, matches)


def test_every_wide_cabinet_marker_has_exactly_one_matching_port(cabinet_laid_out):
    """The exactly-one-match proof on the wide golden (count asserted non-zero first)."""
    _assert_every_marker_has_exactly_one_matching_port(
        cabinet_laid_out, _EXPECTED_MARKER_COUNTS["cabinet_laid_out"]
    )


def test_every_narrow_cabinet_marker_has_exactly_one_matching_port(cabinet_narrow_laid_out):
    """The exactly-one-match proof on the narrow golden (count asserted non-zero first)."""
    _assert_every_marker_has_exactly_one_matching_port(
        cabinet_narrow_laid_out, _EXPECTED_MARKER_COUNTS["cabinet_narrow_laid_out"]
    )


def test_a_marker_moved_off_its_port_matches_no_port(cabinet_narrow_laid_out):
    """The matching check can fail: a real marker nudged one grid unit matches zero ports."""
    marker = next(iter(layout_of(cabinet_narrow_laid_out, LinkMarker).values()))
    placement = _owning_placement(cabinet_narrow_laid_out, marker)
    assert len(_matching_ports(cabinet_narrow_laid_out, placement, marker)) == 1
    moved = dataclasses.replace(marker, x=marker.x + 1)
    assert _matching_ports(cabinet_narrow_laid_out, placement, moved) == []


def test_a_truly_unknown_symbol_key_gives_no_oriented_symbol(cabinet_laid_out):
    """`oriented_symbol` returns `None`, never raises, for a key the library doesn't have."""
    placement = next(iter(layout_of(cabinet_laid_out, SymbolPlacement).values()))
    bogus = dataclasses.replace(placement, symbol="no-such-symbol-key")
    assert oriented_symbol(cabinet_laid_out, bogus) is None


# --- _generic_box_port_names: a function with zero ports has no entry in `ports_by_function`
# (`Indexes`' own docstring: "a record nothing refers to has no entry, so read one with
# `.get(key, ())`"), so a mutant default of `None` in place of `()` turns "this function owns no
# ports" into `for port_id in None`, a crash, on a real model shape (not an invented one) ---------


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _drawing_set(key_part):
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=1, produced_by="test"
    )


def _page(key_part, *, drawing_set):
    key = ("page", key_part)
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by="test",
    )


def _item(key_part, designation):
    key = ("item", key_part)
    return Item(
        id=make_id(Item, key),
        key=key,
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="Invented",
    )


def _function(key_part, *, item, name):
    key = ("function", key_part)
    return Function(
        id=make_id(Function, key),
        key=key,
        item=item.id,
        template=None,
        name=name,
        kind=FunctionKind.GENERIC,
    )


def _port(key_part, *, function, name):
    key = ("port", key_part)
    return Port(
        id=make_id(Port, key),
        key=key,
        function=function.id,
        template=None,
        name=name,
        role=PortRole.GENERIC,
    )


def _placement(key_part, *, function, page, view):
    key = ("symbol_placement", key_part)
    return SymbolPlacement(
        id=make_id(SymbolPlacement, key),
        key=key,
        function=function.id,
        page=page.id,
        x=0,
        y=0,
        orientation=Orientation.R0,
        poles=1,
        symbol="unused",
        library_version="irrelevant",
        produced_by="test",
        view=view,
    )


def _item_with_one_pinned_and_one_bare_function():
    """One item, two functions: `with_port` owns a port, `bare` owns none at all."""
    drawing_set = _drawing_set("gbp")
    page = _page("gbp", drawing_set=drawing_set)
    item = _item("gbp", "K1")
    with_port = _function("gbp-with-port", item=item, name="a")
    port = _port("gbp-with-port-1", function=with_port, name="1")
    bare = _function("gbp-bare", item=item, name="b")
    model = _model(drawing_set, page, item, with_port, port, bare)
    return model, with_port, bare, page


def test_item_view_skips_a_zero_port_function_instead_of_crashing():
    """ITEM view collects every function's ports; a function that owns none contributes none,
    not a `TypeError` from iterating a missing-key default of `None`."""
    model, with_port, _bare, page = _item_with_one_pinned_and_one_bare_function()
    placement = _placement("gbp-item", function=with_port, page=page, view=PlacementView.ITEM)

    names = _generic_box_port_names(model, placement)

    assert names == ("a.1",)


def test_plain_view_of_a_zero_port_function_returns_empty_instead_of_crashing():
    """The non-ITEM branch's own function, with zero ports, gives `()` cleanly."""
    model, _with_port, bare, page = _item_with_one_pinned_and_one_bare_function()
    placement = _placement("gbp-plain", function=bare, page=page, view=PlacementView.FUNCTION)

    names = _generic_box_port_names(model, placement)

    assert names == ()


# --- oriented_symbol: `poles > 1` is what triggers `repeat`, which multiplies the port count;
# `poles == 1` never calls it. A mutant threshold of `> 2` would leave `poles=2` unrepeated too,
# collapsing this test's two symbols to the same port count -----------------------------------


def test_two_poles_repeats_the_symbol_doubling_its_ports(cabinet_laid_out):
    """A real, repeatable library symbol at `poles=2` has exactly twice the ports of `poles=1`."""
    placement = next(iter(layout_of(cabinet_laid_out, SymbolPlacement).values()))
    one_pole = dataclasses.replace(placement, symbol="make-contact", poles=1)
    two_poles = dataclasses.replace(placement, symbol="make-contact", poles=2)

    symbol_one = oriented_symbol(cabinet_laid_out, one_pole)
    symbol_two = oriented_symbol(cabinet_laid_out, two_poles)

    assert symbol_one is not None
    assert symbol_two is not None
    assert len(symbol_two.ports) == 2 * len(symbol_one.ports)


def test_render_draws_a_generic_box_at_the_placements_port_offsets():
    """model-0129: the placement's offsets (grid units) place the ports, not the default pitch."""
    # UNDO: _symbol_geometry.py `oriented_symbol` drops the offsets argument: ports stand at 0, 2
    import dataclasses

    from fransys_render._symbol_geometry import oriented_symbol

    from electrical_symbols import GENERIC_BOX_KEY
    from fransys_model.layout import Side

    model, with_port, _bare, page = _item_with_one_pinned_and_one_bare_function()
    base = _placement("off", function=with_port, page=page, view=PlacementView.FUNCTION)
    box = dataclasses.replace(
        base,
        symbol=GENERIC_BOX_KEY,
        ports=("a", "b"),
        sides=(Side.N, Side.N),
        port_offsets=(0, 80),
    )
    symbol = oriented_symbol(model, box)
    assert symbol is not None
    assert sorted(port.position.x for port in symbol.ports) == [0, 10]
