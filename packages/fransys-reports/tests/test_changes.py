"""`changes_csv`/`changes_markdown` acceptance (MODEL-DIFF work order, Part 2 of 3, M2).

The worked-example `Listing` pair is re-hand-built here (not imported from the root
`tests/test_model_diff.py`, which this package's own tests cannot reach): board
`demo-io-board`, revision `1.3` -> `1.4`, matching the baseline spec's own worked example
(interface 2->3, connector `X2` added as an item and a boundary function, and the
`K1:A1`<->`X1:1` wire's colour changed BU->RD).
"""

import dataclasses
from decimal import Decimal

from fransys_reports import changes_csv, changes_markdown

from fransys_model.derive.baseline import diff
from fransys_model.derive.rows import (
    BaselineBoundary,
    BaselineConductor,
    BaselineItem,
    BaselineMate,
    BaselineNestedUnit,
    BaselineNet,
    BaselineUnit,
    Listing,
    ListingDiff,
)
from fransys_model.vocab.ratings import Rating

_WORKED_EXAMPLE_MARKDOWN = """\
# demo-io-board: changes from 1.3 to 1.4

Interface 2 to 3.

## Items

- Added `=BRD-X2`: DEMO-CONN-2P, Demo.

## Boundary

- Added `=BRD-X2:x1`: ports 1, 2.

## Conductors

- Changed between `=BRD-K1:A1` and `=BRD-X1:1`: colour BU to RD."""

_WORKED_EXAMPLE_CSV = (
    "section,change,subject,field,before,after\n"
    "unit,changed,demo-io-board,interface,2,3\n"
    "unit,changed,demo-io-board,revision,1.3,1.4\n"
    "items,added,=BRD-X2,,,\n"
    "boundary,added,=BRD-X2:x1,,,\n"
    "conductors,changed,=BRD-K1:A1 =BRD-X1:1,colour,BU,RD\n"
)


def _board_listing(*, interface, revision, with_x2, wire_colour):
    """`demo-io-board`'s baseline listing, by hand (mirrors `tests/test_model_diff.py`)."""
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


def _worked_example_diff() -> ListingDiff:
    return diff(_before_listing(), _after_listing())


def test_changes_markdown_matches_the_worked_example_byte_for_byte():
    assert changes_markdown(_worked_example_diff()) == _WORKED_EXAMPLE_MARKDOWN


def test_changes_csv_matches_the_worked_example_byte_for_byte():
    assert changes_csv(_worked_example_diff()) == _WORKED_EXAMPLE_CSV


def test_changes_markdown_of_a_revision_only_bump_is_no_changes():
    """Interface unchanged and every non-`unit` section identical: no `Interface` line, no `##`
    sections, body is exactly `No changes.`."""
    before = _before_listing()
    after = _board_listing(interface="2", revision=4, with_x2=False, wire_colour="BU")
    result = diff(before, after)
    assert len(result.changes) > 0
    assert changes_markdown(result) == "# demo-io-board: changes from 1.3 to 1.4\n\nNo changes."


# -- untested sections (MODEL-DIFF-FIX1): mates, nets, items-changed, units bullets -----------


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


def test_changes_markdown_and_csv_render_mates_and_nets_with_no_detail():
    """`mates`/`nets` `added`/`removed` rows carry no `detail` -- the bare `.` bullet
    (`_bullet`'s no-detail branch), never exercised by items/boundary (both always have one)."""
    before = dataclasses.replace(
        _empty_listing(),
        mates=(BaselineMate(a="=K1:A1", b="=X1:1"),),
        nets=(
            BaselineNet(name="N1", net_class="24V-DC", potential=None, ports=("=X1:1", "=X2:1")),
        ),
    )
    after = dataclasses.replace(
        _empty_listing(),
        mates=(BaselineMate(a="=K1:A2", b="=X1:2"),),
        nets=(
            BaselineNet(name="N2", net_class="24V-DC", potential=None, ports=("=X3:1", "=X4:1")),
        ),
    )
    result = diff(before, after)
    md = changes_markdown(result)
    assert (
        "## Mates\n\n- Removed between `=K1:A1` and `=X1:1`.\n- Added between `=K1:A2` and `=X1:2`."
        in md
    )
    assert "## Nets\n\n- Removed `N1`.\n- Added `N2`." in md
    csv = changes_csv(result)
    assert "mates,removed,=K1:A1 =X1:1,,,\n" in csv
    assert "mates,added,=K1:A2 =X1:2,,,\n" in csv
    assert "nets,removed,N1,,,\n" in csv
    assert "nets,added,N2,,,\n" in csv


def test_changes_markdown_renders_a_units_section_bullet_with_joined_fields():
    """A nested unit's `changed` bullet: the `units` identity (`_identity`'s own branch, l.37-
    38, untested until now) and several changed fields joined by `; ` in one bullet."""
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
                name="board-a", version=1, revision=2, interface="2", instances=("=A1",)
            ),
        ),
    )
    result = diff(before, after)
    md = changes_markdown(result)
    assert "## Units\n\n- Changed `=A1` (board-a): interface 1 to 2; revision 1.1 to 1.2." in md


def test_changes_markdown_and_csv_render_nested_units_removed_and_added():
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
    md = changes_markdown(result)
    assert "- Removed `=A1` (board-a)." in md
    assert "- Added `=A2` (board-b)." in md
    csv = changes_csv(result)
    assert "units,removed,board-a =A1,,,\n" in csv
    assert "units,added,board-b =A2,,,\n" in csv


def test_changes_markdown_joins_multiple_changed_item_fields_in_one_bullet():
    """The `_subject_groups` append-to-existing-group branch (l.70, untested until now): one
    surviving designation with several changed fields is one bullet, not several."""
    before = dataclasses.replace(
        _empty_listing(),
        items=(
            BaselineItem(
                designation="=X1",
                mpn="OLD",
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
                mpn="NEW",
                manufacturer="Demo",
                installed=False,
                external=False,
                position=3,
            ),
        ),
    )
    result = diff(before, after)
    md = changes_markdown(result)
    assert (
        "## Items\n\n- Changed `=X1`: installed True to False; mpn OLD to NEW; position  to 3."
        in md
    )
    csv = changes_csv(result)
    assert "items,changed,=X1,installed,True,False\n" in csv
    assert "items,changed,=X1,mpn,OLD,NEW\n" in csv
    assert "items,changed,=X1,position,,3\n" in csv


def test_changes_markdown_and_csv_render_a_removed_boundary_function_with_its_ports_detail():
    before = dataclasses.replace(
        _empty_listing(),
        boundary=(
            BaselineBoundary(designation="=X1:x1", ports=("2", "1"), rating=None, operating=None),
        ),
    )
    after = _empty_listing()
    result = diff(before, after)
    md = changes_markdown(result)
    assert "## Boundary\n\n- Removed `=X1:x1`: ports 1, 2." in md
    csv = changes_csv(result)
    assert "boundary,removed,=X1:x1,,,\n" in csv


def _x1_boundary_listing(ports, *, rating=None, operating=None):
    return dataclasses.replace(
        _empty_listing(),
        boundary=(
            BaselineBoundary(designation="=X1:x1", ports=ports, rating=rating, operating=operating),
        ),
    )


def test_changes_markdown_and_csv_render_an_existing_boundary_functions_ports_added():
    """Ports added only, on an untouched-designation function: one grouped 'Changed' bullet,
    not the whole-subject 'Added' bullet (the bug this fix corrects)."""
    before = _x1_boundary_listing(("1",))
    after = _x1_boundary_listing(("1", "2", "3"))
    result = diff(before, after)
    md = changes_markdown(result)
    assert "## Boundary\n\n- Changed `=X1:x1`: ports added 2, 3." in md
    csv = changes_csv(result)
    assert "boundary,added,=X1:x1,ports,,2\n" in csv
    assert "boundary,added,=X1:x1,ports,,3\n" in csv


def test_changes_markdown_and_csv_render_an_existing_boundary_functions_ports_removed():
    before = _x1_boundary_listing(("1", "2", "3"))
    after = _x1_boundary_listing(("1",))
    result = diff(before, after)
    md = changes_markdown(result)
    assert "## Boundary\n\n- Changed `=X1:x1`: ports removed 2, 3." in md
    csv = changes_csv(result)
    assert "boundary,removed,=X1:x1,ports,2,\n" in csv
    assert "boundary,removed,=X1:x1,ports,3,\n" in csv


def test_changes_markdown_and_csv_render_an_existing_boundary_functions_ports_added_and_removed():
    before = _x1_boundary_listing(("1", "2"))
    after = _x1_boundary_listing(("2", "3"))
    result = diff(before, after)
    md = changes_markdown(result)
    assert "## Boundary\n\n- Changed `=X1:x1`: ports added 3; ports removed 1." in md
    csv = changes_csv(result)
    assert "boundary,added,=X1:x1,ports,,3\n" in csv
    assert "boundary,removed,=X1:x1,ports,1,\n" in csv


def test_changes_markdown_and_csv_render_a_boundary_functions_changed_rating_key():
    """Designer ruling 2026-09-27 (MODEL DIFF FIX2 Part 4): the Markdown clause for a changed
    `rating`/`operating` key reads `rating.<key> <before> to <after>`, the spec's own wording
    verbatim."""
    before = _x1_boundary_listing(("1",), rating=Rating(voltage_dc_v=Decimal(24)))
    after = _x1_boundary_listing(("1",), rating=Rating(voltage_dc_v=Decimal(48)))
    result = diff(before, after)
    md = changes_markdown(result)
    assert "## Boundary\n\n- Changed `=X1:x1`: rating.voltage_dc_v 24 to 48." in md
    csv = changes_csv(result)
    assert "boundary,changed,=X1:x1,rating.voltage_dc_v,24,48\n" in csv


def test_changes_markdown_renders_a_port_added_and_a_rating_change_in_one_bullet():
    """A mixed group -- one designation, a port added AND a rating key changed -- is one
    bullet: `_bullet`'s clause order is ports added, then ports removed, then each `changed`
    row in row order (`_boundary_changes` sorts rows by `(subject, field)`, so `ports` sorts
    before `rating.voltage_dc_v`)."""
    before = _x1_boundary_listing(("1",), rating=Rating(voltage_dc_v=Decimal(24)))
    after = _x1_boundary_listing(("1", "2"), rating=Rating(voltage_dc_v=Decimal(48)))
    result = diff(before, after)
    md = changes_markdown(result)
    assert "## Boundary\n\n- Changed `=X1:x1`: ports added 2; rating.voltage_dc_v 24 to 48." in md
