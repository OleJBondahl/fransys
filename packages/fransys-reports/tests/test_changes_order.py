"""`changes_markdown` lists a boundary's added and removed ports in natural order (0135)."""

import dataclasses

from fransys_reports import changes_markdown

from fransys_model.derive.baseline import diff
from fransys_model.derive.rows_baseline import BaselineBoundary, BaselineUnit, Listing


def _unit(interface):
    return BaselineUnit(name="u", version=1, revision=1, interface=interface)


def _x1_boundary_listing(ports):
    empty = Listing(
        unit=BaselineUnit(name="u", version=1, revision=1, interface="1"),
        items=(),
        units=(),
        boundary=(),
        conductors=(),
        mates=(),
        nets=(),
    )
    boundary = (BaselineBoundary(designation="=X1:x1", ports=ports, rating=None, operating=None),)
    return dataclasses.replace(empty, boundary=boundary)


def test_changes_markdown_lists_ports_added_and_removed_in_natural_order():
    before = _x1_boundary_listing(("1", "3", "20"))
    after = _x1_boundary_listing(("1", "2", "10", "11"))
    md = changes_markdown(diff(before, after))
    assert "ports added 2, 10, 11; ports removed 3, 20." in md


def test_the_unit_rows_print_as_the_interface_line_and_never_as_a_section():
    before = dataclasses.replace(_x1_boundary_listing(("1",)), unit=_unit("1"))
    after = dataclasses.replace(_x1_boundary_listing(("1", "2")), unit=_unit("2"))
    md = changes_markdown(diff(before, after))
    assert "Interface 1 to 2." in md
    assert "## Unit\n" not in md
    assert "## Boundary" in md
