"""The engine writes the typed `SymbolPlacement` and `LinkMarker` fields, never ext keys (F1).

A placement's `view`, `ports` and `sides`, and a marker's `box_x`, `lead`, `stub_extra`,
`via_x`, `via_y` and `star`, are written from the stage results; the generic `ext` carries
nothing (an off stub's text is derived, `off_stub_text`, F1 part 3d).
"""

import dataclasses
from functools import cache

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.write_keys import write_keys
from fransys_layout.engines.schematic.write import write_layout
from fransys_layout.engines.schematic.write.markers import _marker_fields
from fransys_layout.engines.schematic.write.placements import _placement_fields
from fransys_layout.geometry import GENERIC_BOX_KEY, Box, Point, generic_box_geometry
from fransys_layout.stages import MarkerSide
from fransys_model.kernel import freeze
from fransys_model.layout import MarkerSide as ModelMarkerSide
from fransys_model.layout import PlacementView, Side, StarKind
from fransys_model.vocab.tables import items, ports


@cache
def _laid_out(*, second_location: bool = False):
    model = freeze(build_cabinet(second_location=second_location))
    results, _ = stage_results(model, read_inputs(model))
    return model, results, write_layout(model, results, write_keys(model))


def _written(model, results, placed):
    """The placements written for `results` with `placed` as the stage placements.

    Labels, outlines and markers are dropped: they name the handle of a placed function (a
    marker's key, the placement's discriminator), and a doctored placement changes that handle.
    """
    layout = dataclasses.replace(results.layout, placed=placed, labels=(), outlines=(), markers=())
    out = write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))
    return list(dict(out.tables["layout.symbol_placement"]).values())


def _generic_box(results):
    return next(p for p in results.layout.placed if p.geometry.key == GENERIC_BOX_KEY)


def test_a_plain_function_placement_has_the_function_view_and_no_ports() -> None:
    _, results, out = _laid_out()
    written = list(dict(out.tables["layout.symbol_placement"]).values())
    assert len(written) == len(results.layout.placed)
    plain = [p for p in written if p.view is PlacementView.FUNCTION]
    assert len(plain) == len(written)
    assert any(not p.ports and not p.sides for p in plain)


def test_no_placement_carries_an_ext_key() -> None:
    """The keys `view`, `ports` and `sides` replaced are gone from every placement."""
    model, results, out = _laid_out()
    generic = _generic_box(results)
    item = next(iter(items(model)))
    doctored = tuple(
        dataclasses.replace(p, function=item) if p is generic else p for p in results.layout.placed
    )
    for written in (
        dict(out.tables["layout.symbol_placement"]).values(),
        _written(model, results, doctored),
    ):
        assert not any(p.ext for p in written)


def test_an_item_view_placement_has_the_item_view_and_its_ports_and_sides() -> None:
    """The generic box of an item view always names its ports; `view is ITEM` says whose view."""
    model, results, _ = _laid_out()
    generic = _generic_box(results)
    item = next(iter(items(model)))
    doctored = tuple(
        dataclasses.replace(p, function=item) if p is generic else p for p in results.layout.placed
    )
    (viewed,) = (p for p in _written(model, results, doctored) if p.view is PlacementView.ITEM)
    assert viewed.ports
    assert len(viewed.ports) == len(viewed.sides) == len(generic.geometry.ports)
    assert set(viewed.sides) <= {Side.N, Side.S}


def test_a_pin_view_placement_has_the_pin_view() -> None:
    model, results, _ = _laid_out()
    first = results.layout.placed[0]
    pin = next(iter(ports(model)))
    doctored = (dataclasses.replace(first, function=pin), *results.layout.placed[1:])
    views = [p.view for p in _written(model, results, doctored)]
    assert views.count(PlacementView.PIN) == 1
    assert PlacementView.ITEM not in views


def test_a_generic_box_with_unsorted_names_carries_its_ports_and_sides_in_drawing_order() -> None:
    """The generic box of the cabinet (not an item view) writes its own port list."""
    _, results, out = _laid_out()
    generic = _generic_box(results)
    drawn = sorted(generic.geometry.ports, key=lambda port: (port.at.x, port.facing.value != "n"))
    names, sides, offsets = _placement_fields(generic, PlacementView.FUNCTION)
    assert names == tuple(port.name for port in drawn)
    assert sides == tuple(Side[port.facing.value.upper()] for port in drawn)
    (written,) = (p for p in dict(out.tables["layout.symbol_placement"]).values() if p.ports)
    assert (written.ports, written.sides, written.port_offsets) == (names, sides, offsets)


def test_a_box_port_standing_north_is_written_before_the_one_south_of_it() -> None:
    """RR-O4: at one x the drawing order is N then S, whatever the names sort to."""
    _, results, _ = _laid_out()
    box = dataclasses.replace(_generic_box(results), geometry=generic_box_geometry(("b", "a")))
    names, sides, _ = _placement_fields(box, PlacementView.ITEM)
    assert names == ("b", "a")
    assert sides == (Side.N, Side.S)


def _marker(**changes):
    _, results, _ = _laid_out()
    base = next(m for m in results.layout.markers if m.star)
    plain = {
        "shared_box": False,
        "lead": True,
        "stub_extra": 0,
        "turn": None,
    }  # a shifted box is shared
    return dataclasses.replace(base, **plain | changes)


_BOX = Box(x=40, y=8, width=12, height=4)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        pytest.param(
            {"shared_box": True, "lead": False},
            (40, False, 0, None, None),
            id="shared box, not the lead",
        ),
        pytest.param(
            {"shared_box": True, "lead": True}, (40, True, 0, None, None), id="shared box, lead"
        ),
        pytest.param(
            {"shared_box": False, "lead": False},
            (None, True, 0, None, None),
            id="not shared: no box x, lead reads True even when the stage says False",
        ),
        pytest.param({"stub_extra": 6}, (None, True, 6, None, None), id="stub extra copies"),
        pytest.param(
            {"turn": Point(x=5, y=6)},
            (40, True, 0, 5, 6),
            id="a turn gives via x and y and the box x (M7: render reads the side from it)",
        ),
        pytest.param({"turn": None}, (None, True, 0, None, None), id="no turn gives neither"),
    ],
)
def test_marker_fields_come_from_the_stage_marker(changes: dict, expected: tuple) -> None:
    assert _marker_fields(_marker(box=_BOX, **changes)) == expected


def _written_markers(model, results, markers):
    layout = dataclasses.replace(results.layout, markers=tuple(markers))
    out = write_layout(model, dataclasses.replace(results, layout=layout), write_keys(model))
    return list(dict(out.tables["layout.link_marker"]).values())


def test_a_star_marker_writes_the_marker_fields_from_its_stage_marker() -> None:
    model, results, _ = _laid_out()
    stars = [m for m in results.layout.markers if m.star]
    doctored = [
        dataclasses.replace(m, turn=Point(x=5, y=6), shared_box=True, lead=False) for m in stars
    ]
    written = _written_markers(model, results, doctored)
    assert len(written) == len(stars)
    assert {(m.via_x, m.via_y, m.lead) for m in written} == {(5, 6, False)}
    assert {m.box_x for m in written} == {m.box.x for m in stars}
    assert sorted(m.stub_extra for m in written) == sorted(m.stub_extra for m in stars)


def test_a_pair_marker_writes_the_marker_fields_and_carries_no_ext() -> None:
    """An owner and a user record take box x, lead, stub and via from their stage marker."""
    model, results, _ = _laid_out()
    base = next(m for m in results.layout.markers if m.star)
    numbers = sorted(p.number for p in results.layout.pages if p.drawing_set == base.drawing_set)
    assert len(numbers) > 1, "a cut needs two pages of one drawing set"
    owner = dataclasses.replace(
        base,
        page=numbers[0],
        star="",
        side=MarkerSide.OWNER,
        shared_box=True,
        lead=False,
        stub_extra=4,
        turn=Point(x=5, y=6),
    )
    user = dataclasses.replace(
        owner, side=MarkerSide.USER, page=numbers[1], shared_box=False, turn=None
    )
    by_side = {m.side: m for m in _written_markers(model, results, (owner, user))}
    written_owner, written_user = by_side[ModelMarkerSide.OWNER], by_side[ModelMarkerSide.USER]
    assert (written_owner.box_x, written_owner.lead, written_owner.stub_extra) == (
        owner.box.x,
        False,
        4,
    )
    assert (written_owner.via_x, written_owner.via_y) == (5, 6)
    assert (written_user.box_x, written_user.lead, written_user.stub_extra) == (None, True, 4)
    assert (written_user.via_x, written_user.via_y) == (None, None)
    assert written_owner.star is None
    assert not written_owner.ext
    assert not written_user.ext


def test_a_star_marker_maps_its_kind_and_carries_no_ext() -> None:
    _, results, out = _laid_out(second_location=True)
    written = list(dict(out.tables["layout.link_marker"]).values())
    # D9 (F7): the reference on the stub's port is that one marker, an off stub; a reference of
    # a turned pair (M12) stands alone on a port with no stub
    assert {m.star for m in written} == {StarKind.OFF, StarKind.BRANCH, StarKind.REF}
    stub_ports = {m.port for m in written if m.star is StarKind.OFF}
    assert not [m for m in written if m.star is StarKind.REF and m.port in stub_ports]
    assert not any(m.ext for m in written)
    stubs = [m for m in written if m.star is StarKind.OFF]
    assert stubs
    assert not any(m.ext for m in stubs)
    assert all(m.far is not None and m.facing is not None for m in stubs)
    assert not any(m.far or m.carrier or m.facing for m in written if m.star is not StarKind.OFF)
    assert {m.star.value for m in written} == {
        "off" if m.text else m.star for m in results.layout.markers
    }


def test_a_cabinet_with_only_reference_and_branch_stars_carries_no_marker_ext() -> None:
    _, _, out = _laid_out()
    written = list(dict(out.tables["layout.link_marker"]).values())
    assert {m.star for m in written} == {StarKind.REF, StarKind.BRANCH}
    assert not any(m.ext for m in written)
