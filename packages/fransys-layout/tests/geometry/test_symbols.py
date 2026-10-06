"""WP2: `geometry.symbols` (ROADMAP WP2, docs/design/geometry.md 5.2).

These run against the real symbol library: the adapter is the one place it is used.
"""

import dataclasses
import re
from itertools import pairwise

import graphical_symbols
import pytest
from graphical_symbols import Direction as LibraryDirection
from graphical_symbols import Line, Style, Weight
from graphical_symbols import Orientation as LibraryOrientation
from graphical_symbols import Point as LibraryPoint

import electrical_symbols
from electrical_symbols import LIBRARY
from fransys_layout.geometry import (
    Box,
    Facing,
    GeometryError,
    Orientation,
    Point,
    PortGeometry,
    ThroughPath,
    UnknownSymbolError,
    contains,
    library_version,
    on_wiring_grid,
    symbol_geometry,
)
from fransys_layout.geometry.symbols import convert


def test_make_contact_ports_are_integer_grid_points() -> None:
    """`make-contact` has `in` at (0, -2 M) facing N and `out` at (0, 2 M) facing S."""
    geometry = symbol_geometry("make-contact")
    ports = {port.name: port for port in geometry.ports}
    assert ports["in"].at == Point(x=0, y=-16)
    assert ports["in"].facing is Facing.N
    assert ports["out"].at == Point(x=0, y=16)
    assert ports["out"].facing is Facing.S


def test_every_port_is_on_the_wiring_grid_in_every_orientation() -> None:
    """The library contract the router relies on holds after conversion and orientation."""
    for orientation in Orientation:
        geometry = symbol_geometry("make-contact", orientation=orientation)
        assert all(on_wiring_grid(port.at) for port in geometry.ports)


def test_ports_and_slots_are_sorted_and_keepout_covers_body() -> None:
    """`ports` is sorted by name, `slots` by slot, and the keep-out box contains the body."""
    geometry = symbol_geometry("make-contact")
    assert [p.name for p in geometry.ports] == sorted(p.name for p in geometry.ports)
    assert [s.slot for s in geometry.slots] == sorted(s.slot for s in geometry.slots)
    assert contains(geometry.keepout, geometry.body)


def test_poles_repeat_the_symbol() -> None:
    """Three poles give ports `1.in` .. `3.out`."""
    geometry = symbol_geometry("make-contact", poles=3)
    assert geometry.poles == 3
    assert [p.name for p in geometry.ports] == ["1.in", "1.out", "2.in", "2.out", "3.in", "3.out"]


def test_rotation_turns_ports_and_facings() -> None:
    """R90 is a clockwise quarter turn: the N-facing port at (0, -16) faces E at (16, 0)."""
    geometry = symbol_geometry("make-contact", orientation=Orientation.R90)
    ports = {port.name: port for port in geometry.ports}
    assert ports["in"].at == Point(x=16, y=0)
    assert ports["in"].facing is Facing.E


def test_unknown_symbol_raises_and_names_the_key() -> None:
    """An unknown key raises; no placeholder geometry is returned."""
    with pytest.raises(UnknownSymbolError) as excinfo:
        symbol_geometry("no-such-symbol")
    assert excinfo.value.key == "no-such-symbol"


def test_same_arguments_return_the_cached_object() -> None:
    """Results are cached per `(key, poles, orientation)`."""
    assert symbol_geometry("make-contact", poles=2) is symbol_geometry("make-contact", poles=2)


def test_library_version_names_both_libraries() -> None:
    """The recorded version names both distributions; the numbers are not asserted."""
    version = library_version()
    assert "electrical-symbols" in version
    assert "graphical-symbols" in version


def test_library_version_joins_the_two_exported_constants() -> None:
    """The version is read from `LIBRARY_VERSION` of each package, not from package metadata."""
    assert library_version() == (
        f"electrical-symbols {electrical_symbols.LIBRARY_VERSION}"
        f" / graphical-symbols {graphical_symbols.LIBRARY_VERSION}"
    )


def test_an_off_grid_library_coordinate_raises() -> None:
    """A port at x = 0.1 M is not a multiple of 0.125 M: `to_grid` refuses it."""
    symbol = LIBRARY.get("make-contact")
    port = symbol.ports[0]
    bent = dataclasses.replace(port, position=LibraryPoint(0.1, port.position.y))
    fake = dataclasses.replace(symbol, ports=(bent, *symbol.ports[1:]))
    with pytest.raises(GeometryError):
        convert(fake, poles=1, orientation=Orientation.R0)


def test_the_unchanged_library_symbol_converts() -> None:
    """The same conversion accepts the real symbol."""
    symbol = LIBRARY.get("make-contact")
    assert convert(symbol, poles=1, orientation=Orientation.R0) == symbol_geometry("make-contact")


def test_one_pole_keeps_unprefixed_port_names_and_names_the_through_path() -> None:
    """`repeat` is skipped for one pole: ports are `in` and `out`, which is the through path."""
    geometry = symbol_geometry("make-contact")
    assert [p.name for p in geometry.ports] == ["in", "out"]
    assert geometry.through is not None
    assert (geometry.through.start, geometry.through.end) == ("in", "out")


def test_poles_on_a_symbol_without_a_through_path_raise() -> None:
    """`earth` has no through path, so it cannot be repeated: refused before the library."""
    assert symbol_geometry("earth").through is None
    with pytest.raises(GeometryError):
        symbol_geometry("earth", poles=3)


def test_three_poles_are_two_library_pole_pitches_wider() -> None:
    """Pole pitch is the library's own, 4 M when a symbol states none: 32 G per extra pole."""
    pitch = LIBRARY.get("make-contact").pole_pitch or 4
    one = symbol_geometry("make-contact")
    three = symbol_geometry("make-contact", poles=3)
    assert three.body.width - one.body.width == 2 * pitch * 8


def test_four_quarter_turns_and_two_mirrors_are_the_identity() -> None:
    """R90 four times and MR0 twice give R0 back: R180 is R90 twice, R270 three times."""
    base = {p.name: (p.at, p.facing) for p in symbol_geometry("make-contact").ports}
    quarter = symbol_geometry("make-contact", orientation=Orientation.R90)
    half = symbol_geometry("make-contact", orientation=Orientation.R180)
    turned = {p.name: p.at for p in quarter.ports}
    assert {n: Point(x=-at.y, y=at.x) for n, (at, _) in base.items()} == turned
    assert {n: Point(x=-at.x, y=-at.y) for n, (at, _) in base.items()} == {
        p.name: p.at for p in half.ports
    }
    mirrored = symbol_geometry("make-contact", orientation=Orientation.MR0)
    assert {p.name: Point(x=-p.at.x, y=p.at.y) for p in mirrored.ports} == {
        n: at for n, (at, _) in base.items()
    }


@dataclasses.dataclass(frozen=True)
class _CarriesAFloat:
    x: float


def _leaves(obj: object) -> list[object]:
    if isinstance(obj, tuple):
        return [leaf for item in obj for leaf in _leaves(item)]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return [leaf for f in dataclasses.fields(obj) for leaf in _leaves(getattr(obj, f.name))]
    return [obj]


def test_the_leaf_walk_finds_a_float_nested_in_tuples_and_dataclasses() -> None:
    """Positive control: the walk recurses, so a clean result below means something."""
    assert _leaves((_CarriesAFloat(x=1.5), (2,))) == [1.5, 2]


def test_no_float_anywhere_in_a_returned_geometry() -> None:
    """Integers above the adapter: walk the value and find no `float`."""
    leaves = _leaves(symbol_geometry("make-contact", poles=3, orientation=Orientation.MR90))
    assert any(isinstance(leaf, int) for leaf in leaves)
    assert not any(isinstance(leaf, float) for leaf in leaves)


# The eight orientations as (mirror in x first?, clockwise quarter turns), written out here
# independently of the library so the adapter's output is checked against a second source.
_TRANSFORMS = {
    Orientation.R0: (False, 0),
    Orientation.R90: (False, 1),
    Orientation.R180: (False, 2),
    Orientation.R270: (False, 3),
    Orientation.MR0: (True, 0),
    Orientation.MR90: (True, 1),
    Orientation.MR180: (True, 2),
    Orientation.MR270: (True, 3),
}
_MIRRORED_FACING = {Facing.N: Facing.N, Facing.E: Facing.W, Facing.S: Facing.S, Facing.W: Facing.E}
_TURNED_FACING = {Facing.N: Facing.E, Facing.E: Facing.S, Facing.S: Facing.W, Facing.W: Facing.N}


def _mirror(at: Point) -> Point:
    return Point(x=-at.x, y=at.y)


def _turn(at: Point) -> Point:
    return Point(x=-at.y, y=at.x)


def _transformed(at: Point, facing: Facing, orientation: Orientation) -> tuple[Point, Facing]:
    mirrored, turns = _TRANSFORMS[orientation]
    if mirrored:
        at, facing = _mirror(at), _MIRRORED_FACING[facing]
    for _ in range(turns):
        at, facing = _turn(at), _TURNED_FACING[facing]
    return at, facing


def _on_body_side(port: PortGeometry, body: Box) -> bool:
    return {
        Facing.N: port.at.y == body.y,
        Facing.S: port.at.y == body.y + body.height,
        Facing.W: port.at.x == body.x,
        Facing.E: port.at.x == body.x + body.width,
    }[port.facing]


def test_our_orientation_and_facing_members_match_the_library_by_name() -> None:
    """The adapter maps enums by member name, so the names must stay equal."""
    assert {o.name for o in Orientation} == {o.name for o in LibraryOrientation}
    assert {d.name for d in Facing} == {d.name for d in LibraryDirection}


@pytest.mark.parametrize("orientation", list(Orientation))
def test_ports_and_slots_follow_an_independent_model_of_each_orientation(
    orientation: Orientation,
) -> None:
    """Every port and slot of `make-contact` lands where mirror-then-turn puts it."""
    base = symbol_geometry("make-contact")
    turned = symbol_geometry("make-contact", orientation=orientation)
    assert [(p.name, p.at, p.facing) for p in turned.ports] == [
        (p.name, *_transformed(p.at, p.facing, orientation)) for p in base.ports
    ]
    assert [(s.slot, s.at, s.side) for s in turned.slots] == [
        (s.slot, *_transformed(s.at, s.side, orientation)) for s in base.slots
    ]


@pytest.mark.parametrize("orientation", list(Orientation))
def test_a_port_sits_on_the_body_side_it_faces_in_every_orientation(
    orientation: Orientation,
) -> None:
    """The wiring contract survives orientation: the router can leave a port straight out."""
    geometry = symbol_geometry("make-contact", orientation=orientation)
    assert all(_on_body_side(port, geometry.body) for port in geometry.ports)


def test_the_body_side_check_can_fail() -> None:
    """A port one unit inside the body is not on the side it faces."""
    body = Box(x=-8, y=-16, width=8, height=32)
    assert _on_body_side(PortGeometry(name="in", at=Point(x=0, y=-16), facing=Facing.N), body)
    assert not _on_body_side(PortGeometry(name="in", at=Point(x=0, y=-15), facing=Facing.N), body)


def test_turning_the_result_by_a_quarter_walks_the_orientation_ring() -> None:
    """R90 turned once more is R180, and so on round to R0; MR0 mirrored is R0."""
    ring = [Orientation.R0, Orientation.R90, Orientation.R180, Orientation.R270, Orientation.R0]
    for before, after in pairwise(ring):
        expected = [
            (p.name, _turn(p.at), _TURNED_FACING[p.facing])
            for p in symbol_geometry("make-contact", orientation=before).ports
        ]
        actual = [
            (p.name, p.at, p.facing)
            for p in symbol_geometry("make-contact", orientation=after).ports
        ]
        assert expected == actual
    mirrored = symbol_geometry("make-contact", orientation=Orientation.MR0)
    assert [(p.name, _mirror(p.at), _MIRRORED_FACING[p.facing]) for p in mirrored.ports] == [
        (p.name, p.at, p.facing) for p in symbol_geometry("make-contact").ports
    ]


def test_body_and_keepout_boxes_are_the_library_boxes_in_grid_units() -> None:
    """`make-contact`: body 1 x 4 M, keep-out reaches the `tag` slot on the left."""
    geometry = symbol_geometry("make-contact")
    assert geometry.body == Box(x=-8, y=-16, width=8, height=32)
    assert geometry.keepout == Box(x=-60, y=-16, width=74, height=32)


def test_slot_boxes_are_absolute_and_stay_upright() -> None:
    """The `tag` box is 48 x 8 G before and after R90; only its place and side change."""
    tag = {s.slot: s for s in symbol_geometry("make-contact").slots}["tag"]
    assert (tag.at, tag.side, tag.box) == (
        Point(x=-12, y=0),
        Facing.W,
        Box(x=-60, y=-4, width=48, height=8),
    )
    turned = {
        s.slot: s for s in symbol_geometry("make-contact", orientation=Orientation.R90).slots
    }["tag"]
    assert (turned.at, turned.side, turned.box) == (
        Point(x=0, y=-12),
        Facing.N,
        Box(x=-24, y=-20, width=48, height=8),
    )


# `connection-point` is a junction dot whose four ports all sit at its centre, inside its body
# box, so it is the one library symbol that does not put a port on the side it faces (geometry.md
# 5.2).
_OFF_BODY_SIDE_CONTRACT = {"connection-point"}


def test_every_library_symbol_converts_in_every_orientation() -> None:
    """No library symbol trips `to_grid`, and its ports, slots and boxes satisfy the contract."""
    for key, symbol in LIBRARY.symbols.items():
        through_paths = [path for path in symbol.paths if path.through]
        assert len(through_paths) <= 1  # `convert` reads the through path from the first one
        for poles in (1, 3) if through_paths else (1,):
            for orientation in Orientation:
                geometry = symbol_geometry(key, poles=poles, orientation=orientation)
                assert geometry.key == key
                assert all(on_wiring_grid(port.at) for port in geometry.ports)
                assert contains(geometry.keepout, geometry.body)
                assert all(contains(geometry.keepout, slot.box) for slot in geometry.slots)
                if key not in _OFF_BODY_SIDE_CONTRACT:
                    assert all(_on_body_side(port, geometry.body) for port in geometry.ports)


def test_the_one_symbol_off_the_body_side_contract_is_still_off_it() -> None:
    """When the library fixes `connection-point`, this fails and the exception can go."""
    geometry = symbol_geometry("connection-point")
    assert not all(_on_body_side(port, geometry.body) for port in geometry.ports)


@pytest.mark.parametrize("poles", [0, -3])
def test_fewer_than_one_pole_raises(poles: int) -> None:
    """A pole count below one is refused, not turned into a one-pole geometry."""
    with pytest.raises(GeometryError):
        symbol_geometry("make-contact", poles=poles)
    assert symbol_geometry("make-contact", poles=1).poles == 1


def test_a_symbol_without_a_through_path_is_fine_at_one_pole() -> None:
    """`earth` converts with `through=None`; only repeating it is refused."""
    geometry = symbol_geometry("earth")
    assert geometry.through is None
    assert [p.name for p in geometry.ports] == ["earth"]


def test_the_through_path_names_the_base_ports_at_any_pole_count() -> None:
    """`through` is `com` -> `no` for a change-over contact, unprefixed even at three poles."""
    one = symbol_geometry("change-over-contact")
    three = symbol_geometry("change-over-contact", poles=3)
    assert one.through == ThroughPath(start="com", end="no")
    assert three.through == one.through
    assert [p.name for p in three.ports][:3] == ["1.com", "1.nc", "1.no"]


def test_marking_slots_repeat_per_pole_and_tag_stays_single() -> None:
    """Two poles give `marking.1.*` and `marking.2.*`, and one `tag` slot."""
    geometry = symbol_geometry("make-contact", poles=2)
    assert [s.slot for s in geometry.slots] == [
        "marking.1.in",
        "marking.1.out",
        "marking.2.in",
        "marking.2.out",
        "tag",
    ]


def test_default_arguments_and_explicit_ones_share_one_cached_object() -> None:
    """`symbol_geometry("k")` and the same call spelled out are one object."""
    assert symbol_geometry("make-contact") is symbol_geometry(
        "make-contact", poles=1, orientation=Orientation.R0
    )
    assert symbol_geometry("make-contact") is not symbol_geometry("make-contact", poles=2)


def test_an_off_grid_slot_or_body_coordinate_raises() -> None:
    """`to_grid` guards the slots and the body box, not only the ports."""
    symbol = LIBRARY.get("make-contact")
    slot = symbol.slots[0]
    bent_slot = dataclasses.replace(slot, position=LibraryPoint(0.1, slot.position.y))
    with pytest.raises(GeometryError):
        convert(
            dataclasses.replace(symbol, slots=(bent_slot, *symbol.slots[1:])),
            poles=1,
            orientation=Orientation.R0,
        )
    stray = Line(LibraryPoint(0.0, 0.0), LibraryPoint(0.3, 0.0), Weight.NORMAL, Style.SOLID)
    with pytest.raises(GeometryError):
        convert(
            dataclasses.replace(symbol, elements=(*symbol.elements, stray)),
            poles=1,
            orientation=Orientation.R0,
        )


def test_terminals_four_ports_are_one_declared_node() -> None:
    """`terminal.toml` declares one node with all four ports (geometry.md 5.2, `nodes_of`)."""
    geometry = symbol_geometry("terminal")
    assert geometry.nodes == (("e", "n", "s", "w"),)


def test_a_symbol_with_no_declared_nodes_has_only_implicit_singletons() -> None:
    """`make-contact` declares no node: each port is its own implicit singleton node."""
    assert symbol_geometry("make-contact").nodes == (("in",), ("out",))


def test_library_version_has_a_version_after_each_name() -> None:
    """Each distribution name is followed by a version token."""
    assert re.fullmatch(r"electrical-symbols \S+ / graphical-symbols \S+", library_version())
