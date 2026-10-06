"""Baseline listing acceptance (`docs/specs/2026-09-23-baseline.md`, L2, step 1).

Root test: built through the public API (`import fransys as fr`), which
`packages/fransys-model/tests` cannot reach without a layering exception (the same reason
`tests/test_units_worked_example.py` is a root test). The fixtures below are a small,
invented shape of the baseline spec's own worked example (one `demo-io-board` unit with a
boundary connector wired to a relay, nested twice in `demo-pump-cabinet` units), built with
`fr.build(parts, d.draft())` -- no `Document`, so no layout runs and every build here stays
well under 1 s.
"""

import json
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest

from fransys_model.derive import baseline
from fransys_model.kernel import SchemaVersionError

_PROJECT: dict[str, Any] = {
    "title": "Baseline demo",
    "number": "BL-1",
    "customer": "Demo Co",
    "revision": 1,
    "author": "OJB",
}


def _board(scope):
    """A minimal `demo-io-board` unit: `A1` holds `X1` (the boundary) wired to `K1`, matching
    the baseline spec's own worked example ("A worked example")."""
    u = scope.unit("demo-io-board", revision=3, interface="2")
    u.revision(3, date="2026-01-01", text="First release", created="XX")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", tag="A1", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", tag="K1", parent=board, group=grp)
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.boundary(x1)
    return u, x1


def _cabinet(scope, *, mate_to_spare=False):
    """A minimal `demo-pump-cabinet` nesting one board, `P1` mated to its `X1`.

    `mate_to_spare=True` mates `P1` to an unrelated spare connector instead, for the mates
    can-fail probe.
    """
    u = scope.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    grp = u.group("FLD", "Field wiring")
    board_u, board_x1 = _board(u.scope("io"))
    p1 = u.item("DEMO-CONN-2P", tag="P1", group=grp)
    if mate_to_spare:
        spare = u.item("DEMO-CONN-2P", tag="X9", group=grp)
        u.mate(p1, spare)
    else:
        u.mate(p1, board_x1)
    return u, board_u, p1


def _new_design(parts):
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    return d


@pytest.fixture(scope="module")
def two_cabinet_system():
    """Two identical `demo-pump-cabinet` instances, each nesting one `demo-io-board`."""
    parts = fransys_parts.load("demo_parts")
    d = _new_design(parts)
    cab1_u, board1_u, _p1 = _cabinet(d.scope("cab1"))
    cab2_u, board2_u, _p2 = _cabinet(d.scope("cab2"))
    result = fr.build(parts, d.draft())
    return result, cab1_u.unit_id, board1_u.unit_id, cab2_u.unit_id, board2_u.unit_id


def test_board_own_listing_matches_the_worked_example_text():
    """The board's own listing matches `docs/specs/2026-09-23-baseline.md`'s worked example,
    corrected as the spec's own note allows: `items` entries carry `external` (the
    external-items amendment folded into L2 after the example was written). `boundary`'s
    key is `function` -- the ruling table's prose describes the field's content, not its
    JSON key, exactly as `mates`' "two connector function designations" prints as `a`/`b`,
    not `designation_a`/`designation_b`; the example's own literal JSON, amended 2026-09-26
    to add `rating`/`operating`, kept `function` deliberately."""
    parts = fransys_parts.load("demo_parts")
    d = _new_design(parts)
    u, _x1 = _board(d)
    result = fr.build(parts, d.draft())

    text = baseline.dumps(baseline.listing(result.model, u.unit_id))

    expected = {
        "listing_version": 1,
        "unit": {"name": "demo-io-board", "version": 1, "revision": 3, "interface": "2"},
        "items": [
            {
                "designation": "",
                "mpn": "DEMO-PCB-IO",
                "manufacturer": "Demo",
                "installed": True,
                "external": False,
                "position": None,
            },
            {
                "designation": "=BRD-K1",
                "mpn": "DEMO-RLY-2CO-24",
                "manufacturer": "Demo",
                "installed": True,
                "external": False,
                "position": None,
            },
            {
                "designation": "=BRD-X1",
                "mpn": "DEMO-CONN-2P",
                "manufacturer": "Demo",
                "installed": True,
                "external": False,
                "position": None,
            },
        ],
        "units": [],
        "boundary": [
            {"function": "=BRD-X1:x1", "ports": ["1", "2"], "rating": None, "operating": None}
        ],
        "conductors": [
            {
                "kind": "wire",
                "a": "=BRD-K1:A1",
                "b": "=BRD-X1:1",
                "carrier": None,
                "colour": "BU",
                "gauge_mm2": "0.5",
                "length_mm": None,
                "label": None,
            },
            {
                "kind": "wire",
                "a": "=BRD-K1:A2",
                "b": "=BRD-X1:2",
                "carrier": None,
                "colour": "BU",
                "gauge_mm2": "0.5",
                "length_mm": None,
                "label": None,
            },
        ],
        "mates": [],
        "nets": [],
    }
    assert json.loads(text) == expected


def test_both_board_instances_and_both_cabinets_give_equal_listings(two_cabinet_system):
    """Units spec U7: two instances of one unit number alike, so their baseline listings --
    designation-relative -- are equal, board and cabinet alike."""
    result, cab1_id, board1_id, cab2_id, board2_id = two_cabinet_system

    board1 = baseline.listing(result.model, board1_id)
    board2 = baseline.listing(result.model, board2_id)
    assert board1 == board2

    cab1 = baseline.listing(result.model, cab1_id)
    cab2 = baseline.listing(result.model, cab2_id)
    assert cab1 == cab2
    assert len(cab1.units) == 1
    assert cab1.units[0].name == "demo-io-board"
    assert cab1.units[0].instances == ("=BRD-A1",)
    assert len(cab1.mates) == 1
    assert {cab1.mates[0].a, cab1.mates[0].b} == {"=BRD-A1/=BRD-X1:x1", "=FLD-P1:x1"}


def test_standalone_board_listing_equals_the_nested_instances_own_listing(two_cabinet_system):
    """The board's own listing, built standalone, equals the same unit's listing read out of
    the system build that nests it (baseline spec L2's own worked-example claim)."""
    parts = fransys_parts.load("demo_parts")
    d = _new_design(parts)
    u, _x1 = _board(d)
    standalone_result = fr.build(parts, d.draft())
    standalone_listing = baseline.listing(standalone_result.model, u.unit_id)

    result, _cab1_id, board1_id, _cab2_id, _board2_id = two_cabinet_system
    nested_listing = baseline.listing(result.model, board1_id)

    assert standalone_listing == nested_listing


def test_loads_dumps_round_trip(two_cabinet_system):
    result, cab1_id, _board1_id, _cab2_id, _board2_id = two_cabinet_system
    original = baseline.listing(result.model, cab1_id)
    assert baseline.loads(baseline.dumps(original)) == original


def test_loads_refuses_an_unknown_listing_version(two_cabinet_system):
    result, cab1_id, _board1_id, _cab2_id, _board2_id = two_cabinet_system
    text = baseline.dumps(baseline.listing(result.model, cab1_id))
    bad = text.replace('"listing_version":1', '"listing_version":2')
    assert '"listing_version":2' in bad
    with pytest.raises(SchemaVersionError):
        baseline.loads(bad)


def test_system_listing_names_the_project_and_the_top_level_units(two_cabinet_system):
    """`listing(model, unit=None)` (baseline spec L2): `unit` comes from the model's one
    `Project`, and `units` holds the top-level units -- here both cabinets, one release with
    two instances, since they share `(name, version, revision)`."""
    result, _cab1_id, _board1_id, _cab2_id, _board2_id = two_cabinet_system

    system = baseline.listing(result.model, None)

    assert system.unit.name == _PROJECT["number"]
    assert system.boundary == ()
    assert len(system.units) == 1
    assert system.units[0].name == "demo-pump-cabinet"
    assert len(system.units[0].instances) == 2


def test_cabinets_differ_when_a_boards_mate_partner_differs():
    """Fixed-designations acceptance's sibling case for `mates`: two cabinets alike except
    that one mates `P1` to a spare connector instead of its own board's `X1` must give
    different listings, naming `mates` (this is CAN-FAIL 2's own probe: with the `mates`
    section cut, this assertion is exactly what breaks)."""
    parts = fransys_parts.load("demo_parts")
    d = _new_design(parts)
    cab1_u, _board1_u, _p1 = _cabinet(d.scope("cab1"))
    cab2_u, _board2_u, _p2 = _cabinet(d.scope("cab2"), mate_to_spare=True)
    result = fr.build(parts, d.draft())

    cab1 = baseline.listing(result.model, cab1_u.unit_id)
    cab2 = baseline.listing(result.model, cab2_u.unit_id)
    assert cab1 != cab2
    assert "mates" in baseline.differing_sections(cab1, cab2)


def _cabinet_with_boundary_net(scope):
    """A `demo-pump-cabinet` nesting one board, with a CABINET-declared net that also reaches
    the board's own boundary pin (`X1`'s port `"2"`, already mated to `P1`'s `"2"`).

    Designer ruling 2026-09-27: `nets` follows U6's lowest-common-unit rule too, the same as
    `conductors`/`mates` -- the literal "a member port on an item of U itself" wording would
    put this net in the board's OWN listing too (the pin is, after all, its own item), so the
    board's standalone listing would differ from its nested one (the net does not exist when
    it is built alone), breaking this spec's own acceptance.
    """
    u = scope.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    grp = u.group("FLD", "Field wiring")
    board_u, board_x1 = _board(u.scope("io"))
    p1 = u.item("DEMO-CONN-2P", tag="P1", group=grp)
    u.mate(p1, board_x1)
    u.net("shared", p1["2"], board_x1["2"])
    return u, board_u, p1


def test_a_cabinet_declared_net_through_a_boards_boundary_pin_stays_out_of_the_boards_own_listing():
    """Acceptance: the board's listing is equal standalone and nested; the net appears only
    in the cabinet's own listing (this is CAN-FAIL 3's own probe: with `nets` reverted to the
    literal "on an item of U itself" scoping, the board's listing gains the net too, and the
    equality assertion below is exactly what breaks)."""
    parts = fransys_parts.load("demo_parts")
    d = _new_design(parts)
    cab_u, board_u, _p1 = _cabinet_with_boundary_net(d.scope("cab"))
    nested_result = fr.build(parts, d.draft())
    errors = [f for f in fr.check(nested_result) if f.severity is fr.Severity.ERROR]
    assert errors == [], errors

    standalone_d = _new_design(parts)
    standalone_u, _x1 = _board(standalone_d)
    standalone_result = fr.build(parts, standalone_d.draft())
    standalone_listing = baseline.listing(standalone_result.model, standalone_u.unit_id)

    nested_board_listing = baseline.listing(nested_result.model, board_u.unit_id)
    cabinet_listing = baseline.listing(nested_result.model, cab_u.unit_id)

    assert nested_board_listing == standalone_listing
    assert nested_board_listing.nets == ()
    assert len(cabinet_listing.nets) == 1
    assert cabinet_listing.nets[0].name == "shared"


def test_two_releases_of_one_unit_in_one_cabinet_give_two_distinct_units_entries():
    """Fixed-designations acceptance 7b: a board release at `1.5` and the same unit's release
    at `2.1`, each instantiated once in one cabinet, give two distinct `units` entries keyed
    by `(name, version, revision)`, not collapsed into one by name alone."""
    parts = fransys_parts.load("demo_parts")
    d = _new_design(parts)
    u = d.scope("cab").unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")

    board_a = u.scope("ioA").unit("demo-io-board", version=1, revision=5, interface="2")
    board_a.revision(5, date="2026-01-01", text="v1", created="XX")
    grp_a = board_a.group("BRD", "I/O board")
    board_a.item("DEMO-PCB-IO", tag="A1", group=grp_a)

    board_b = u.scope("ioB").unit("demo-io-board", version=2, revision=1, interface="2")
    board_b.revision(1, date="2026-01-01", text="v2", created="XX")
    grp_b = board_b.group("BRD", "I/O board")
    board_b.item("DEMO-PCB-IO", tag="A1", group=grp_b)

    result = fr.build(parts, d.draft())
    cab_listing = baseline.listing(result.model, u.unit_id)

    assert len(cab_listing.units) == 2
    assert all(row.name == "demo-io-board" for row in cab_listing.units)
    assert {(row.version, row.revision) for row in cab_listing.units} == {(1, 5), (2, 1)}
