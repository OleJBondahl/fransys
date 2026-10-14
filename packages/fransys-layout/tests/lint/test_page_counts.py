"""The two readability counts no finding states: wire crossings and a page's references.

A crossing is one wire running across a wire of another physical net, inside both runs; touching,
a shared end, a T and an overlap along one line are not crossings. The references of a page are
its coils' contact images, its star references and its page cuts.
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
