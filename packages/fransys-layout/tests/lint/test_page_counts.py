"""The two readability counts no finding states: wire crossings and a page's references.

A crossing is one wire running across a wire of another physical net or a cable core line, inside
both runs; touching, a shared end, a T and an overlap along one line are not crossings. The
references of a page are its coils' contact images, its star references and its page cuts.
"""

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.lint.page_counts import ReferenceCounts, reference_counts, wire_crossings
from fransys_layout.stages import (
    LabelKind,
    LinkMarker,
    MarkerSide,
    PlacedLabel,
    RequestPartner,
    Route,
    RoutePoint,
)
from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLeg, DrawnLine

_BOX = Box(x=0, y=0, width=8, height=8)


def _route(net: int, *points: tuple[int, int]) -> Route:
    return Route(
        connection=hid("conductor", net),
        physical_net=hid("net", net),
        drawing_set=1,
        page=1,
        a=hid("port", net),
        b=hid("port", net + 100),
        points=tuple(RoutePoint(index=i, at=Point(x=x, y=y)) for i, (x, y) in enumerate(points)),
    )


def test_two_wires_of_two_nets_that_cross_are_one_crossing() -> None:
    assert wire_crossings([_route(1, (0, 8), (16, 8)), _route(2, (8, 0), (8, 16))]) == 1


def test_a_vertical_wire_across_two_horizontals_is_two_crossings() -> None:
    horizontals = [_route(1, (0, 4), (16, 4)), _route(2, (0, 12), (16, 12))]
    assert wire_crossings([*horizontals, _route(3, (8, 0), (8, 16))]) == 2


def test_two_wires_of_one_net_do_not_cross() -> None:
    assert wire_crossings([_route(1, (0, 8), (16, 8)), _route(1, (8, 0), (8, 16))]) == 0


def test_a_wire_that_ends_on_another_is_a_junction_not_a_crossing() -> None:
    assert wire_crossings([_route(1, (0, 8), (16, 8)), _route(2, (8, 8), (8, 16))]) == 0


def test_a_wire_that_stops_on_another_from_the_side_is_not_a_crossing() -> None:
    assert wire_crossings([_route(1, (0, 8), (8, 8)), _route(2, (8, 0), (8, 16))]) == 0


def test_a_corner_of_one_wire_on_another_is_not_a_crossing() -> None:
    assert wire_crossings([_route(1, (0, 8), (16, 8)), _route(2, (4, 0), (8, 0), (8, 8))]) == 0


def test_wires_that_miss_each_other_do_not_cross() -> None:
    assert wire_crossings([_route(1, (0, 8), (6, 8)), _route(2, (8, 0), (8, 16))]) == 0


def test_a_wire_with_a_bend_counts_each_run() -> None:
    bent = _route(1, (0, 4), (16, 4), (16, 12), (0, 12))
    assert wire_crossings([bent, _route(2, (8, 0), (8, 16))]) == 2


def _pts(*points: tuple[int, int]) -> tuple[Point, ...]:
    return tuple(Point(x=x, y=y) for x, y in points)


def _line(harness: int, *points: tuple[int, int]) -> DrawnLine:
    return DrawnLine(
        harness=hid("harness", harness),
        branch=1,
        drawing_set=1,
        page=1,
        points=_pts(*points),
        text=Point(x=0, y=0),
        label=_BOX,
    )


def _fan(harness: int, *legs: tuple[tuple[int, int], ...]) -> DrawnFanOut:
    return DrawnFanOut(
        harness=hid("harness", harness),
        branch=1,
        drawing_set=1,
        page=1,
        at=Point(x=0, y=0),
        legs=tuple(
            DrawnLeg(conductor=hid("conductor", 50 + i), points=_pts(*leg))
            for i, leg in enumerate(legs)
        ),
    )


def test_a_fan_leg_across_a_foreign_wire_is_a_crossing() -> None:
    """Layout-0260: a leg counts against another net's wire.

    # UNDO: lint/page_counts.py, `wire_crossings` reads `fans` as empty (the leg crossing goes)
    """
    fan = _fan(1, ((8, 0), (8, 16)))
    assert wire_crossings([_route(2, (0, 8), (16, 8))], fans=[fan]) == 1


def test_a_fan_leg_across_another_cables_line_is_a_crossing() -> None:
    fan = _fan(1, ((8, 0), (8, 16)))
    assert wire_crossings([], [_line(2, (0, 8), (16, 8))], [fan]) == 1


def test_legs_of_one_fan_and_its_own_cables_line_do_not_count() -> None:
    fan = _fan(1, ((8, 0), (8, 16)), ((4, 8), (12, 8)))
    assert wire_crossings([], [_line(1, (0, 4), (16, 4))], [fan]) == 0


def test_legs_of_two_fans_count_one_crossing_each() -> None:
    """Layout-0260: two fans are two cables, so each crossing of their legs counts.

    # UNDO: lint/page_counts.py, `wire_crossings` skips a leg against a leg again
    """
    fans = [_fan(1, ((8, 0), (8, 16))), _fan(2, ((0, 8), (16, 8)))]
    assert wire_crossings([], fans=fans) == 1
    more = [_fan(1, ((8, 0), (8, 16)), ((12, 0), (12, 16))), _fan(2, ((0, 8), (16, 8)))]
    assert wire_crossings([], fans=more) == 2


def test_legs_of_one_fan_do_not_count_against_each_other() -> None:
    assert wire_crossings([], fans=[_fan(1, ((8, 0), (8, 16)), ((0, 8), (16, 8)))]) == 0


def _label(
    slot: str, partners: int, kind: LabelKind = LabelKind.CROSS_REFERENCE, partner_page: int = 2
) -> PlacedLabel:
    return PlacedLabel(
        kind=kind,
        subject=hid("function", 1),
        slot=slot,
        drawing_set=1,
        page=1,
        box=_BOX,
        partners=tuple(
            RequestPartner(port=hid("port", n), drawing_set=1, page=partner_page, x=n)
            for n in range(partners)
        ),
    )


def _marker(*, star: str = "", port: int = 1, partner: int = 0, symbol: str = "") -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 1),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=0, y=0),
        box=_BOX,
        partner_page=1,
        star=star,
        star_partner=hid("port", partner) if star else None,
        star_partner_set=1 if star else 0,
        symbol=symbol,
    )


def _branch(of: int) -> LinkMarker:
    return _marker(star="branch", port=50 + of, partner=1)


def test_a_page_with_no_references_counts_none() -> None:
    assert reference_counts((), ()) == ReferenceCounts()


def test_a_coils_contact_image_counts_its_contacts_and_one_contact_stands_alone() -> None:
    found = reference_counts((_label("contacts", 1), _label("contacts", 3)), ())
    assert (found.contact_images, found.contact_image_targets, found.single_contact_images) == (
        2,
        4,
        1,
    )


def test_a_single_image_whose_contact_is_on_its_own_page_is_no_other_page_image() -> None:
    labels = (_label("contacts", 1), _label("contacts", 1, partner_page=1), _label("contacts", 3))
    found = reference_counts(labels, ())
    assert (found.single_contact_images, found.single_contact_images_other_page) == (2, 1)


def test_a_contacts_own_reference_to_its_coil_is_no_contact_image() -> None:
    assert reference_counts((_label("tag", 1),), ()).contact_images == 0


def test_a_tag_is_no_reference() -> None:
    assert reference_counts((_label("tag", 0, LabelKind.TAG),), ()).contact_images == 0


def test_a_star_counts_the_branches_that_name_it() -> None:
    markers = (_marker(star="ref", port=1, partner=50), _branch(1), _branch(2))
    found = reference_counts((), markers)
    assert (found.stars, found.star_branches, found.single_branch_stars) == (1, 2, 0)


def test_a_star_with_one_branch_stands_alone() -> None:
    found = reference_counts((), (_marker(star="ref", port=1, partner=50), _branch(1)))
    assert (found.stars, found.star_branches, found.single_branch_stars) == (1, 1, 1)


def test_a_page_cut_is_no_star_and_a_star_is_no_page_cut() -> None:
    cut = reference_counts((), (_marker(),))
    star = reference_counts((), (_marker(star="ref", partner=50), _branch(1)))
    assert (cut.page_cuts, cut.stars) == (1, 0)
    assert (star.page_cuts, star.stars) == (0, 1)


def test_a_power_end_is_no_reference() -> None:
    assert reference_counts((), (_marker(symbol="ground"),)).page_cuts == 0


def _core(branch: int, *points: tuple[int, int]) -> DrawnLine:
    return DrawnLine(
        harness=hid("item", 9),
        branch=branch,
        drawing_set=1,
        page=1,
        points=tuple(Point(x=x, y=y) for x, y in points),
        text=Point(x=0, y=0),
        label=_BOX,
    )


def test_a_wire_across_a_cable_core_line_is_a_crossing() -> None:
    """Layout-0258: a reader sees a core line as a wire; the cabinet's `W1.3` is one."""
    core = _core(3, (8, 0), (8, 16))
    assert wire_crossings([_route(1, (0, 8), (16, 8))], [core]) == 1
    assert wire_crossings([_route(1, (0, 8), (16, 8))]) == 0


def test_a_wire_ending_on_a_core_line_or_two_core_lines_are_no_crossing() -> None:
    assert wire_crossings([_route(1, (0, 8), (8, 8))], [_core(3, (8, 0), (8, 16))]) == 0
    assert wire_crossings([], [_core(1, (0, 8), (16, 8)), _core(2, (8, 0), (8, 16))]) == 0
