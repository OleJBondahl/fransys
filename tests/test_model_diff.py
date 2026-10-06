"""Model diff acceptance (`derive.baseline.diff`, MODEL-DIFF work order, Part 1 of 3, M1).

Root test: built through the public API (`import fransys as fr`), the same reason
`tests/test_baseline_listing.py` and `tests/test_units_worked_example.py` are root tests. The
worked-example pair is hand-built directly from the `derive.rows` dataclasses (no `fr.build`
needed for it): board `demo-io-board`, revision `1.3` -> `1.4`, matching the spec's own worked
example (interface 2->3, connector `X2` added as an item and a boundary function, and the
`K1:A1`<->`X1:1` wire's colour changed BU->RD). The nested-unit case builds through `fr.build`,
reusing `io_board` from `tests/test_units_worked_example.py` -- but not `pump_cabinet`, which
calls `io_board` on its own internal scope and so gives no way to vary the nested board's
revision without editing that file (out of scope here); a small proxy scope forces the
revision instead, calling `io_board` unchanged.
"""

import dataclasses
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest

# `test_unit_name_worked_example.py`'s own pattern for importing a sibling root test module by
# name: `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import io_board

from fransys_model.derive.baseline import diff, listing
from fransys_model.derive.rows import (
    BaselineBoundary,
    BaselineConductor,
    BaselineItem,
    BaselineMate,
    BaselineNestedUnit,
    BaselineNet,
    BaselineUnit,
    Listing,
)
from fransys_model.kernel import SchemaError
from fransys_model.vocab.ratings import Operating, Rating

# `dict[str, Any]`, matching `tests/test_baseline_listing.py`'s own `_PROJECT` (ty can't check
# a precisely-typed `dict[str, str | int]` unpacked into `Design.project`'s per-key types).
_PROJECT: dict[str, Any] = {
    "title": "Model diff demo",
    "number": "MD-1",
    "customer": "Demo Co",
    "revision": 1,
    "author": "OJB",
}


def _new_design(parts):
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-27", text="First issue", created="OJB")
    return d


# -- hand-built worked-example listings (spec worked example, board 1.3 -> 1.4) --------------


def _board_listing(*, interface, revision, with_x2, wire_colour):
    """`demo-io-board`'s baseline listing, by hand: `A1` (bare board), `K1`, `X1`, `X1`'s
    boundary, and the two wires -- optionally with `X2` (an item and a boundary function) and
    the `K1:A1`<->`X1:1` wire's own colour, so the caller can build the before/after pair the
    worked example diffs.
    """
    items = [
        BaselineItem(
            designation="",
            mpn="DEMO-PCB-IO",
            manufacturer="Demo",
            installed=True,
            external=False,
            position=None,
        ),
        BaselineItem(
            designation="=BRD-K1",
            mpn="DEMO-RLY-2CO-24",
            manufacturer="Demo",
            installed=True,
            external=False,
            position=None,
        ),
        BaselineItem(
            designation="=BRD-X1",
            mpn="DEMO-CONN-2P",
            manufacturer="Demo",
            installed=True,
            external=False,
            position=None,
        ),
    ]
    boundary = [
        BaselineBoundary(designation="=BRD-X1:x1", ports=("1", "2"), rating=None, operating=None)
    ]
    conductors = [
        BaselineConductor(
            kind="wire",
            a="=BRD-K1:A1",
            b="=BRD-X1:1",
            carrier=None,
            colour=wire_colour,
            gauge_mm2="0.5",
            length_mm=None,
            label=None,
        ),
        BaselineConductor(
            kind="wire",
            a="=BRD-K1:A2",
            b="=BRD-X1:2",
            carrier=None,
            colour="BU",
            gauge_mm2="0.5",
            length_mm=None,
            label=None,
        ),
    ]
    if with_x2:
        items.append(
            BaselineItem(
                designation="=BRD-X2",
                mpn="DEMO-CONN-2P",
                manufacturer="Demo",
                installed=True,
                external=False,
                position=None,
            )
        )
        boundary.append(
            BaselineBoundary(
                designation="=BRD-X2:x1", ports=("1", "2"), rating=None, operating=None
            )
        )
    return Listing(
        unit=BaselineUnit(name="demo-io-board", version=1, revision=revision, interface=interface),
        items=tuple(items),
        units=(),
        boundary=tuple(boundary),
        conductors=tuple(conductors),
        mates=(),
        nets=(),
    )


def _before_listing():
    return _board_listing(interface="2", revision=3, with_x2=False, wire_colour="BU")


def _after_listing():
    return _board_listing(interface="3", revision=4, with_x2=True, wire_colour="RD")


def test_worked_example_diff_matches_the_spec_csv_exactly():
    """The spec's own worked example: five rows, in section-then-subject-then-field order,
    exactly the six CSV columns `changes.csv` shows."""
    result = diff(_before_listing(), _after_listing())
    assert len(result.changes) > 0
    rows = [(c.section, c.change, c.subject, c.field, c.before, c.after) for c in result.changes]
    assert rows == [
        ("unit", "changed", "demo-io-board", "interface", "2", "3"),
        ("unit", "changed", "demo-io-board", "revision", "1.3", "1.4"),
        ("items", "added", "=BRD-X2", "", "", ""),
        ("boundary", "added", "=BRD-X2:x1", "", "", ""),
        ("conductors", "changed", "=BRD-K1:A1 =BRD-X1:1", "colour", "BU", "RD"),
    ]
    detail_by_subject = {c.subject: c.detail for c in result.changes if c.change == "added"}
    assert detail_by_subject["=BRD-X2"] == "DEMO-CONN-2P, Demo"
    assert detail_by_subject["=BRD-X2:x1"] == "ports 1, 2"


def test_diffing_a_listing_against_itself_gives_no_rows():
    listing_ = _before_listing()
    result = diff(listing_, listing_)
    assert result.changes == ()


def test_a_moved_wire_gives_one_removed_and_one_added_conductor_row_never_changed():
    """A wire moved to another terminal (same `a`, a different `b`) is one removed row and
    one added row, never a `changed` row -- the identity key is the `(a, b)` pair itself."""
    before = _before_listing()
    moved = BaselineConductor(
        kind="wire",
        a="=BRD-K1:A1",
        b="=BRD-X1:3",
        carrier=None,
        colour="BU",
        gauge_mm2="0.5",
        length_mm=None,
        label=None,
    )
    after = Listing(
        unit=before.unit,
        items=before.items,
        units=before.units,
        boundary=before.boundary,
        conductors=(moved, before.conductors[1]),
        mates=before.mates,
        nets=before.nets,
    )
    result = diff(before, after)
    conductor_changes = [c for c in result.changes if c.section == "conductors"]
    assert len(conductor_changes) > 0
    assert len(conductor_changes) == 2
    assert {c.change for c in conductor_changes} == {"added", "removed"}
    assert all(c.field == "" for c in conductor_changes)


def test_diff_refuses_two_listings_of_different_unit_names():
    a = _before_listing()
    b = Listing(
        unit=BaselineUnit(name="some-other-unit", version=1, revision=3, interface="2"),
        items=(),
        units=(),
        boundary=(),
        conductors=(),
        mates=(),
        nets=(),
    )
    with pytest.raises(SchemaError):
        diff(a, b)


# -- a nested unit's own revision change (black-box: one `units` row, nothing else) ----------


class _AtRevision:
    """`io_board` calls only `.unit()` on the scope passed to it (`tests/test_units_worked_
    example.py`); this proxy forces the release's own revision there, leaving every other
    authored fact identical, so `io_board` itself needs no change to vary it."""

    def __init__(self, scope, revision):
        self._scope = scope
        self._revision = revision

    def unit(self, name, **kwargs):
        return self._scope.unit(name, **{**kwargs, "revision": self._revision})


def _cabinet_around_board(scope, *, board_revision):
    u = scope.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    grp = u.group("FLD", "Field wiring")
    board_x1, _board_scope = io_board(_AtRevision(u.scope("io"), board_revision))
    p1 = u.item("DEMO-CONN-2P", tag="P1", group=grp)
    u.mate(p1, board_x1)
    return u


def _cabinet_listing_with_board_revision(revision):
    parts = fransys_parts.load("demo_parts")
    d = _new_design(parts)
    u = _cabinet_around_board(d.scope("cab"), board_revision=revision)
    result = fr.build(parts, d.draft())
    return listing(result.model, u.unit_id)


def test_a_nested_units_revision_change_gives_exactly_one_units_row():
    """Units spec: a nested unit is a black box -- only its `(interface, version, revision)`
    triple is compared; the diff never recurses into its content (the cabinet's own `P1`,
    mated cross-unit to the board's `X1`, is unaffected by the board's own revision bump)."""
    before = _cabinet_listing_with_board_revision(3)
    after = _cabinet_listing_with_board_revision(4)
    assert before != after

    result = diff(before, after)
    assert len(result.changes) > 0
    assert len(result.changes) == 1
    change = result.changes[0]
    assert change.section == "units"
    assert change.change == "changed"
    assert change.field == "revision"
    assert change.before == "1.3"
    assert change.after == "1.4"


# -- untested sections (MODEL-DIFF-FIX1): mates, nets, item/boundary/nested-unit branches -----


def _empty_listing(*, revision=1):
    return Listing(
        unit=BaselineUnit(name="u", version=1, revision=revision, interface="1"),
        items=(),
        units=(),
        boundary=(),
        conductors=(),
        mates=(),
        nets=(),
    )


def test_mates_added_and_removed_give_rows_with_no_field_never_matched_by_likeness():
    """`mates` has no changed field (spec table) -- a mate moved to another pair of functions
    is one `removed` row and one `added` row, the same never-matched-by-likeness rule as a
    moved wire."""
    before = dataclasses.replace(_empty_listing(), mates=(BaselineMate(a="=K1:A1", b="=X1:1"),))
    after = dataclasses.replace(_empty_listing(), mates=(BaselineMate(a="=K1:A2", b="=X1:2"),))
    result = diff(before, after)
    mate_changes = [c for c in result.changes if c.section == "mates"]
    assert len(mate_changes) == 2
    assert {(c.change, c.subject, c.field) for c in mate_changes} == {
        ("removed", "=K1:A1 =X1:1", ""),
        ("added", "=K1:A2 =X1:2", ""),
    }


def test_nets_added_removed_and_changed_cover_named_and_unnamed_identity():
    """Named nets are keyed and subjected by `name`; an unnamed net by its own `ports` tuple
    (spec: "the name; an unnamed net by its sorted member ports"). `changed` covers all three
    fields: `class`, `potential` (`None` to a value) and `ports` (the joined port list)."""
    before = dataclasses.replace(
        _empty_listing(),
        nets=(
            BaselineNet(name="N1", net_class="24V-DC", potential=None, ports=("=X1:1", "=X2:1")),
            BaselineNet(name=None, net_class="24V-DC", potential=None, ports=("=X3:1", "=X4:1")),
        ),
    )
    after = dataclasses.replace(
        _empty_listing(),
        nets=(
            BaselineNet(
                name="N1", net_class="0V-DC", potential="0V", ports=("=X1:1", "=X2:1", "=X5:1")
            ),
            BaselineNet(name="N2", net_class="24V-DC", potential=None, ports=("=X6:1", "=X7:1")),
        ),
    )
    result = diff(before, after)
    net_changes = {
        (c.change, c.subject, c.field): (c.before, c.after)
        for c in result.changes
        if c.section == "nets"
    }
    assert net_changes[("removed", "=X3:1 =X4:1", "")] == ("", "")
    assert net_changes[("added", "N2", "")] == ("", "")
    assert net_changes[("changed", "N1", "class")] == ("24V-DC", "0V-DC")
    assert net_changes[("changed", "N1", "potential")] == ("", "0V")
    assert net_changes[("changed", "N1", "ports")] == ("=X1:1; =X2:1", "=X1:1; =X2:1; =X5:1")


def test_items_changed_field_covers_mpn_installed_and_position_none_to_int():
    """The intersection loop's `changed` branch (untested until now: every prior fixture only
    added/removed whole items, never changed one field of a surviving designation)."""
    before = dataclasses.replace(
        _empty_listing(),
        items=(
            BaselineItem(
                designation="=X1",
                mpn="OLD-MPN",
                manufacturer="Demo",
                installed=True,
                external=False,
                position=None,
            ),
        ),
    )
    after = dataclasses.replace(
        _empty_listing(),
        items=(
            BaselineItem(
                designation="=X1",
                mpn="NEW-MPN",
                manufacturer="Demo",
                installed=False,
                external=False,
                position=3,
            ),
        ),
    )
    result = diff(before, after)
    item_changes = {c.field: (c.before, c.after) for c in result.changes if c.section == "items"}
    assert item_changes == {
        "mpn": ("OLD-MPN", "NEW-MPN"),
        "installed": ("True", "False"),
        "position": ("", "3"),
    }


def test_nested_units_removed_and_added_are_never_matched_by_likeness():
    """A nested unit's identity is `(name, instance)`; a renamed/reinstanced board is one
    `removed` row and one `added` row, never `changed` -- the same rule as a moved wire."""
    before = dataclasses.replace(
        _empty_listing(),
        units=(
            BaselineNestedUnit(
                name="board-a", version=1, revision=1, interface="1", instances=("=A1",)
            ),
        ),
    )
    after = dataclasses.replace(
        _empty_listing(),
        units=(
            BaselineNestedUnit(
                name="board-b", version=1, revision=1, interface="1", instances=("=A2",)
            ),
        ),
    )
    result = diff(before, after)
    unit_changes = [c for c in result.changes if c.section == "units"]
    assert len(unit_changes) == 2
    assert {(c.change, c.subject) for c in unit_changes} == {
        ("removed", "board-a =A1"),
        ("added", "board-b =A2"),
    }


def test_a_removed_boundary_function_gives_a_removed_row_with_its_ports_as_detail():
    before = dataclasses.replace(
        _empty_listing(),
        boundary=(
            BaselineBoundary(designation="=X1:x1", ports=("2", "1"), rating=None, operating=None),
        ),
    )
    after = _empty_listing()
    result = diff(before, after)
    boundary_changes = [c for c in result.changes if c.section == "boundary"]
    assert len(boundary_changes) == 1
    change = boundary_changes[0]
    assert change.change == "removed"
    assert change.subject == "=X1:x1"
    assert change.detail == "ports 1, 2"


def test_conductors_changed_field_covers_kind_and_length_mm():
    """`_conductor_field_text`'s `kind` (plain `str`) and `length_mm` (`int | None`) branches --
    every prior fixture only changed `colour`."""
    before = dataclasses.replace(
        _empty_listing(),
        conductors=(
            BaselineConductor(
                kind="wire",
                a="=K1:A1",
                b="=X1:1",
                carrier=None,
                colour="BU",
                gauge_mm2="0.5",
                length_mm=None,
                label=None,
            ),
        ),
    )
    after = dataclasses.replace(
        _empty_listing(),
        conductors=(
            BaselineConductor(
                kind="cable-core",
                a="=K1:A1",
                b="=X1:1",
                carrier=None,
                colour="BU",
                gauge_mm2="0.5",
                length_mm=250,
                label=None,
            ),
        ),
    )
    result = diff(before, after)
    conductor_changes = {
        c.field: (c.before, c.after) for c in result.changes if c.section == "conductors"
    }
    assert conductor_changes == {
        "kind": ("wire", "cable-core"),
        "length_mm": ("", "250"),
    }


def _x1_boundary(*, rating=None, operating=None):
    return dataclasses.replace(
        _empty_listing(),
        boundary=(
            BaselineBoundary(
                designation="=X1:x1", ports=("1",), rating=rating, operating=operating
            ),
        ),
    )


def test_boundary_rating_none_to_a_value_is_one_changed_row_empty_before():
    """Designer ruling 2026-09-27 (MODEL DIFF FIX2 Part 4): `rating`/`operating` are diffed as
    changed fields, one row per changed key, field `rating.<key>` / `operating.<key>`. A key
    absent on one side (the whole `rating` was `None` there) reads an empty `before`/`after`."""
    before = _x1_boundary(rating=None)
    after = _x1_boundary(rating=Rating(voltage_dc_v=Decimal(24)))
    result = diff(before, after)
    boundary_changes = [c for c in result.changes if c.section == "boundary"]
    assert len(boundary_changes) == 1
    change = boundary_changes[0]
    assert change.change == "changed"
    assert change.subject == "=X1:x1"
    assert change.field == "rating.voltage_dc_v"
    assert change.before == ""
    assert change.after == "24"


def test_boundary_rating_value_to_another_value_is_one_changed_row():
    before = _x1_boundary(rating=Rating(voltage_dc_v=Decimal(24)))
    after = _x1_boundary(rating=Rating(voltage_dc_v=Decimal(48)))
    result = diff(before, after)
    boundary_changes = [c for c in result.changes if c.section == "boundary"]
    assert len(boundary_changes) == 1
    change = boundary_changes[0]
    assert change.field == "rating.voltage_dc_v"
    assert change.before == "24"
    assert change.after == "48"


def test_boundary_operating_two_changed_keys_give_two_rows_and_no_more():
    """Two `operating` keys change at once: exactly two rows, one per key, and a field
    untouched on both sides (here `voltage_dc_v`, both `None`) produces no row."""
    before = _x1_boundary(
        operating=Operating(nominal_voltage_v=Decimal(24), min_voltage_v=Decimal(18))
    )
    after = _x1_boundary(
        operating=Operating(nominal_voltage_v=Decimal(28), min_voltage_v=Decimal(20))
    )
    result = diff(before, after)
    boundary_changes = {
        c.field: (c.before, c.after) for c in result.changes if c.section == "boundary"
    }
    assert len(boundary_changes) == 2
    assert boundary_changes == {
        "operating.nominal_voltage_v": ("24", "28"),
        "operating.min_voltage_v": ("18", "20"),
    }


def test_a_change_on_a_blank_designation_row_names_the_unit_in_items_and_boundary():
    """Model-0132: a sole unit root's `""` row is named `<unit> <V>.<R>`, never `""`, in the
    `items` and `boundary` sections (rating rows included); the listings keep the `""`."""

    def _blank_row(mpn, rating):
        return dataclasses.replace(
            _empty_listing(revision=2),
            items=(
                BaselineItem(
                    designation="",
                    mpn=mpn,
                    manufacturer="",
                    installed=True,
                    external=False,
                    position=None,
                ),
            ),
            boundary=(
                BaselineBoundary(designation="", ports=("1",), rating=rating, operating=None),
            ),
        )

    result = diff(_blank_row("A", None), _blank_row("B", Rating(voltage_dc_v=Decimal(24))))
    rows = [(c.section, c.subject, c.parts, c.field) for c in result.changes]
    assert rows == [
        ("items", "u 1.2", ("u 1.2",), "mpn"),
        ("boundary", "u 1.2", ("u 1.2",), "rating.voltage_dc_v"),
    ]


def test_change_rows_print_numbers_in_numeric_order():
    """Items `=BRD-X10` and `=BRD-X2` added: the change list prints `:2` before `:10` (model-0149).

    The stored listing keeps its plain order, the digest's; only the printed rows sort naturally.
    """
    before = _before_listing()
    extra = tuple(
        BaselineItem(
            designation=designation,
            mpn="DEMO-CONN-2P",
            manufacturer="Demo",
            installed=True,
            external=False,
            position=None,
        )
        for designation in ("=BRD-X10", "=BRD-X2")
    )
    after = dataclasses.replace(before, items=(*before.items, *extra))
    rows = [c.subject for c in diff(before, after).changes if c.section == "items"]
    assert rows == ["=BRD-X2", "=BRD-X10"]
