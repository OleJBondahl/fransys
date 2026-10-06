"""WP9 acceptance skeletons and unit tests: `stages.links` (ROADMAP WP9, design/links.md 6.6)."""

import dataclasses
import itertools

import pytest
from samples import PROFILE, SHEET, built_links, connection, drawn, hid, placed

from fransys_layout.geometry import Box, LayoutError, Point
from fransys_layout.stages import (
    Connection,
    DrawnFunction,
    DrawnPort,
    LabelKind,
    LabelRequest,
    LinkCase,
    LinkMarker,
    MarkerSide,
    NetGroup,
    PlacedFunction,
    PortRef,
    RequestPartner,
    Role,
)
from fransys_layout.stages.references import LINK_FANOUT
from fransys_layout.stages.references.marker_boxes import reference_box_width
from fransys_model.kernel import Severity

# Every drawing set these tests use has a location, each a root node (one-entry path), so no
# marker text loses its prefix; `test_links_markers.py` covers the text, the box, the
# nested-location prefix and the unlocated case.
LOCATION_PATHS = frozendict(
    {1: ((hid("aspect_node", 900), "C1"),), 2: ((hid("aspect_node", 901), "C2"),)}
)


def links(connections, net_groups, placed_functions, drawn_functions, **options):
    """`stages.links` built by `texts` (S9), with this file's sheet, profile, paths and units.

    Each option is the file's own unless given.
    """
    options.setdefault("sheet", SHEET)
    options.setdefault("profile", PROFILE)
    options.setdefault("location_paths", LOCATION_PATHS)
    options.setdefault("units", frozendict())
    options.setdefault("function_units", frozendict())
    return built_links(connections, net_groups, placed_functions, drawn_functions, **options)


def test_a_connection_on_one_page_produces_nothing() -> None:
    """Same-page pairs emit no decision and no marker."""
    decisions, markers, requests, findings = links(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=304)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert (decisions, markers, requests, findings) == ((), (), (), ())


def test_a_severed_signal_gets_one_owner_and_one_user_marker() -> None:
    """Function 1 on page 1, function 2 on page 2: a marker pair naming each other."""
    decisions, markers, requests, findings = links(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96, page=1), placed(2, x=704, y=304, page=2)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert [(d.connection, d.a, d.b, d.case) for d in decisions] == [
        (hid("conductor", 1), hid("port", 12), hid("port", 21), LinkCase.SEVERED)
    ]
    assert requests == ()
    assert sorted(m.side.value for m in markers) == [MarkerSide.OWNER.value, MarkerSide.USER.value]
    by_page = {m.page: m for m in markers}
    assert by_page[1].partner_page == 2
    assert by_page[2].partner_page == 1
    assert by_page[1].side is MarkerSide.OWNER
    assert (by_page[1].port, by_page[1].at) == (hid("port", 12), Point(x=104, y=112))
    assert (by_page[2].port, by_page[2].at) == (hid("port", 21), Point(x=704, y=288))
    assert findings == ()


def test_coil_and_contact_of_one_item_are_a_tag_echo_without_markers() -> None:
    """Both functions belong to item 1: no arrow may be drawn for a tag echo."""
    contact = dataclasses.replace(drawn(2), item=hid("item", 1))
    decisions, markers, requests, _ = links(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=2)),
        (drawn(1), contact),
        sheet=SHEET,
    )
    assert [d.case for d in decisions] == [LinkCase.TAG_ECHO]
    assert markers == ()
    assert [(r.kind, r.subject) for r in requests] == [
        (LabelKind.CROSS_REFERENCE, hid("function", 1)),
        (LabelKind.CROSS_REFERENCE, hid("function", 2)),
    ]


def test_a_terminal_drawn_on_both_pages_is_a_terminal_echo() -> None:
    """Terminal 3 is placed on pages 1 and 2 and the net passes through it: no markers."""
    terminal = drawn(3, kind="terminal")
    to_terminal = connection(1, 1, 3)
    from_terminal = dataclasses.replace(connection(2, 3, 2), physical_net=to_terminal.physical_net)
    decisions, markers, _, _ = links(
        (to_terminal, from_terminal),
        (),
        (
            placed(1, x=104, y=96, page=1),
            placed(3, x=104, y=304, page=1),
            placed(3, x=104, y=96, page=2),
            placed(2, x=104, y=304, page=2),
        ),
        (drawn(1), drawn(2), terminal),
        sheet=SHEET,
    )
    assert {d.case for d in decisions} <= {LinkCase.TERMINAL_ECHO}
    assert markers == ()


def test_a_severed_net_with_two_users_on_one_page_pair_is_reported() -> None:
    """One owner on page 1 and two users on page 2, with no terminal: `LINK_FANOUT`."""
    first = connection(1, 1, 2)
    second = dataclasses.replace(connection(2, 1, 3), physical_net=first.physical_net)
    _, _, _, findings = links(
        (first, second),
        (),
        (
            placed(1, x=104, y=96, page=1),
            placed(2, x=104, y=304, page=2),
            placed(3, x=304, y=304, page=2, name="b"),
        ),
        (drawn(1), drawn(2), drawn(3)),
        sheet=SHEET,
    )
    assert [f.code for f in findings] == [LINK_FANOUT]


def _net_group(number: int, ports: tuple[tuple[int, int], ...]) -> NetGroup:
    """Net `number` over `(function, port)` pairs, with no conductors."""
    return NetGroup(
        net=hid("net", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        ports=tuple(PortRef(function=hid("function", f), port=hid("port", p)) for f, p in ports),
    )


def test_a_net_group_spanning_two_pages_is_cut_at_its_lowest_port_on_each_page() -> None:
    """Ports 12 and 32 on page 1, port 21 on page 2: the pair stands at ports 12 and 21."""
    decisions, markers, _, _ = links(
        (),
        (_net_group(7, ((1, 12), (2, 21), (3, 32))),),
        (
            placed(1, x=104, y=96, page=1),
            placed(3, x=304, y=96, page=1, name="b"),
            placed(2, x=104, y=304, page=2),
        ),
        (drawn(1), drawn(2), drawn(3)),
        sheet=SHEET,
    )
    assert [(d.connection, d.a, d.b) for d in decisions] == [
        (hid("net", 7), hid("port", 12), hid("port", 21))
    ]
    assert {(m.page, m.port, m.side) for m in markers} == {
        (1, hid("port", 12), MarkerSide.OWNER),
        (2, hid("port", 21), MarkerSide.USER),
    }


def test_a_net_group_on_one_page_is_not_cut() -> None:
    """All ports on one page: `route` draws the tree, `links` has nothing to say."""
    decisions, markers, requests, findings = links(
        (),
        (_net_group(7, ((1, 12), (2, 21))),),
        (placed(1, x=104, y=96), placed(2, x=104, y=304)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert (decisions, markers, requests, findings) == ((), (), (), ())


def test_a_fanned_out_net_anchored_at_a_terminal_is_not_reported() -> None:
    """The same fan-out as above, but through terminal 4 drawn on both pages: no finding."""
    first = connection(1, 1, 4)
    second = dataclasses.replace(connection(2, 4, 2), physical_net=first.physical_net)
    third = dataclasses.replace(connection(3, 4, 3), physical_net=first.physical_net)
    _, markers, _, findings = links(
        (first, second, third),
        (),
        (
            placed(1, x=104, y=96, page=1),
            placed(4, x=104, y=304, page=1),
            placed(4, x=104, y=96, page=2),
            placed(2, x=104, y=304, page=2),
            placed(3, x=304, y=304, page=2, name="b"),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4, kind="terminal")),
        sheet=SHEET,
    )
    assert markers == ()
    assert findings == ()


# --- helpers for the unit tests -------------------------------------------------------


def _at(
    number: int, page: int, *, x: int = 104, y: int = 96, drawing_set: int = 1
) -> PlacedFunction:
    """Function `number` on `page` of `drawing_set`, its origin at `(x, y)`."""
    return dataclasses.replace(placed(number, x=x, y=y, page=page), drawing_set=drawing_set)


def _joined(one: Connection, net: int) -> Connection:
    """`one` moved onto physical net `net`."""
    return dataclasses.replace(one, physical_net=hid("net", net))


def _same_item(number: int, item: int, *, kind: str = "contact_no") -> DrawnFunction:
    """Function `number` drawn as belonging to item `item`."""
    return dataclasses.replace(drawn(number, kind=kind), item=hid("item", item))


def _cases(decisions):
    return [(d.connection, d.a, d.b, d.case) for d in decisions]


def _owner_and_user(markers):
    """The port of the owner marker and of the user marker of one severed cut."""
    return tuple(next(m.port for m in markers if m.side is side) for side in MarkerSide)


# --- markers: order, position, text ---------------------------------------------------


def test_a_severed_cut_gives_exactly_these_two_markers() -> None:
    """Every field of both markers, in the order the stage sorts them.

    The owner's port faces S, so its box starts one wiring-grid stub past the port; the
    user's faces N, so its box ends one stub short of the port (open-questions.md 13.18, decision
    layout-0038). Each is centred on its port, turned (S20 M1/M2: a text height wide, the
    sheet's fixed reference width (LD3 (c)) long), never measured from its own text.
    """
    decisions, markers, _, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 1), _at(2, 2, x=704, y=304)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    width = reference_box_width(SHEET, PROFILE)
    assert markers == (
        LinkMarker(
            connection=hid("conductor", 1),
            port=hid("port", 12),
            side=MarkerSide.OWNER,
            drawing_set=1,
            page=1,
            at=Point(x=104, y=112),
            box=Box(x=104 - 4, y=112 + 8, width=8, height=width),
            partner_page=2,
            vertical=True,
        ),
        LinkMarker(
            connection=hid("conductor", 1),
            port=hid("port", 21),
            side=MarkerSide.USER,
            drawing_set=1,
            page=2,
            at=Point(x=704, y=288),
            box=Box(x=704 - 4, y=288 - 8 - width, width=8, height=width),
            partner_page=1,
            vertical=True,
        ),
    )
    assert [(d.a, d.b) for d in decisions] == [(hid("port", 12), hid("port", 21))]


def test_the_owner_is_the_end_on_the_earlier_page_whatever_the_port_order() -> None:
    """Function 1 (the lower port handle) on page 2, function 2 on page 1: 2 owns."""
    _, markers, _, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 2), _at(2, 1, x=704)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert _owner_and_user(markers) == (hid("port", 21), hid("port", 12))
    assert [(m.page, m.partner_page) for m in markers] == [(2, 1), (1, 2)]


@pytest.mark.parametrize(
    ("first", "second", "owner_port"),
    [
        pytest.param((1, 5), (2, 1), 12, id="an-earlier-drawing-set-owns-though-its-page-is-later"),
        pytest.param((1, 5), (1, 1), 21, id="in-one-drawing-set-the-earlier-page-owns"),
        pytest.param((2, 1), (1, 5), 21, id="the-lower-drawing-set-owns-whichever-function-it-is"),
    ],
)
def test_pages_are_ordered_by_drawing_set_then_page(first, second, owner_port) -> None:
    """Page numbers restart in each drawing set, so the page alone would rank them wrongly."""
    _, markers, _, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, first[1], drawing_set=first[0]), _at(2, second[1], drawing_set=second[0])),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert _owner_and_user(markers)[0] == hid("port", owner_port)


def test_a_marker_carries_its_own_drawing_set_and_the_partners_page_only() -> None:
    """The marker's drawing set is its end's; the text cites the partner's page."""
    _, markers, _, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 5, drawing_set=1), _at(2, 1, drawing_set=2)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert [(m.drawing_set, m.page, m.partner_page) for m in markers] == [(1, 5, 1), (2, 1, 5)]


def _shifted(number: int, page: int, *, x: int, dx: int) -> PlacedFunction:
    """Function `number` whose symbol has its ports `dx` right of its origin."""
    one = _at(number, page, x=x, y=304)
    ports = tuple(
        dataclasses.replace(port, at=Point(x=port.at.x + dx, y=port.at.y))
        for port in one.geometry.ports
    )
    return dataclasses.replace(one, geometry=dataclasses.replace(one.geometry, ports=ports))


def test_the_marker_stands_at_the_partners_port_not_at_its_origin() -> None:
    """The marker stands at the port, x = 180, not at the function's origin, x = 100."""
    _, markers, _, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 1), _shifted(2, 2, x=100, dx=80)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    by_page = {m.page: m for m in markers}
    assert by_page[2].at == Point(x=180, y=288)


# --- the three cases ------------------------------------------------------------------


def _terminal_case(*, pages_of_terminal, kind="terminal", other_net=False, terminal=3):
    """Conductor 1 joins functions 1 and 2 on two pages; conductor 2 puts function 3 on its net.

    Function 1 is on page 1, function 2 on page 2, and function `terminal` (of `kind`) is
    placed on `pages_of_terminal` and joined to function 1 by conductor 2. Function 0 has the
    lowest port handles, so it is the `a` end of that conductor; function 3 is the `b` end.
    """
    direct = connection(1, 1, 2)
    to_terminal = _joined(connection(2, 1, terminal), 9 if other_net else 1)
    return links(
        (direct, to_terminal),
        (),
        (
            _at(1, 1),
            _at(2, 2, x=704),
            *(_at(terminal, page, x=304) for page in pages_of_terminal),
        ),
        (drawn(1), drawn(2), drawn(terminal, kind=kind)),
        sheet=SHEET,
    )


@pytest.mark.parametrize("terminal", [3, 0])
def test_a_cut_whose_net_has_a_terminal_on_both_pages_is_a_terminal_echo(terminal) -> None:
    """The direct conductor is cut, and drawn as nothing: the terminal names itself.

    Terminal 0 is the `a` end of its conductor and terminal 3 the `b` end; either counts.
    """
    decisions, markers, requests, findings = _terminal_case(
        pages_of_terminal=(1, 2), terminal=terminal
    )
    assert _cases(decisions) == [
        (hid("conductor", 1), hid("port", 12), hid("port", 21), LinkCase.TERMINAL_ECHO)
    ]
    assert (markers, requests, findings) == ((), (), ())


@pytest.mark.parametrize(
    ("pages_of_terminal", "kind", "other_net"),
    [
        pytest.param((1,), "terminal", False, id="terminal-on-only-the-owner-page"),
        pytest.param((2,), "terminal", False, id="terminal-on-only-the-user-page"),
        pytest.param((1, 3), "terminal", False, id="terminal-on-a-third-page-instead"),
        pytest.param((1, 2), "contact_no", False, id="a-function-of-another-kind-on-both"),
        pytest.param((1, 2), "terminal", True, id="a-terminal-of-another-net-on-both"),
    ],
)
def test_without_a_terminal_of_the_net_on_both_pages_the_cut_is_severed(
    pages_of_terminal, kind, other_net
) -> None:
    """Each variant differs from the echo above by one thing, and gets a marker pair."""
    decisions, markers, requests, _ = _terminal_case(
        pages_of_terminal=pages_of_terminal, kind=kind, other_net=other_net
    )
    assert [d.case for d in decisions if d.connection == hid("conductor", 1)] == [LinkCase.SEVERED]
    assert len([m for m in markers if m.connection == hid("conductor", 1)]) == 2
    assert requests == ()


def _grouped(net: int, physical: int, ports: tuple[tuple[int, int], ...]) -> NetGroup:
    """Net `net` on physical net `physical`, over `(function, port)` pairs."""
    return dataclasses.replace(_net_group(net, ports), physical_net=hid("net", physical))


def _group_with_terminal(pages_of_terminal, kind):
    """A net group of functions 1 (page 1) and 2 (page 2), and function 3 on `pages_of_terminal`.

    The group's own net handle (7) differs from its physical net (9), so a terminal test
    that keyed on the wrong one would find nothing.
    """
    return links(
        (),
        (_grouped(7, 9, ((1, 12), (2, 21), (3, 31))),),
        (_at(1, 1), _at(2, 2), *(_at(3, page, x=304) for page in pages_of_terminal)),
        (drawn(1), drawn(2), drawn(3, kind=kind)),
        sheet=SHEET,
    )


def test_a_terminal_at_a_net_groups_port_makes_its_cuts_echoes() -> None:
    """The net group's terminal (function 3) is drawn on both pages of the cut."""
    decisions, markers, _, _ = _group_with_terminal((1, 2), "terminal")
    assert [d.case for d in decisions] == [LinkCase.TERMINAL_ECHO]
    assert markers == ()


@pytest.mark.parametrize(
    ("pages_of_terminal", "kind"),
    [
        pytest.param((1,), "terminal", id="terminal-on-page-1-only"),
        pytest.param((2,), "terminal", id="terminal-on-page-2-only"),
        pytest.param((1, 2), "contact_no", id="another-kind-on-both-pages"),
    ],
)
def test_a_net_group_without_a_terminal_on_both_pages_is_severed(pages_of_terminal, kind) -> None:
    """Each variant differs from the echo above by one thing."""
    decisions, markers, _, _ = _group_with_terminal(pages_of_terminal, kind)
    assert [d.case for d in decisions] == [LinkCase.SEVERED]
    assert len(markers) == 2


def test_a_terminal_that_is_the_lowest_port_on_both_pages_gives_one_echo_decision() -> None:
    """Both ends of the cut are the terminal's one port: the decision names it twice."""
    decisions, markers, _, _ = links(
        (),
        (_net_group(7, ((3, 31), (4, 41))),),
        (_at(3, 1), _at(3, 2), _at(4, 2, x=304)),
        (drawn(3, kind="terminal"), drawn(4)),
        sheet=SHEET,
    )
    assert _cases(decisions) == [
        (hid("net", 7), hid("port", 31), hid("port", 31), LinkCase.TERMINAL_ECHO)
    ]
    assert markers == ()


def test_one_terminal_of_the_net_on_both_pages_is_enough() -> None:
    """Terminal 3 is on both pages, terminal 4 on page 1 only: the cut is still an echo."""
    decisions, markers, _, _ = links(
        (
            connection(1, 1, 2),
            _joined(connection(2, 1, 3), 1),
            _joined(connection(3, 1, 4), 1),
        ),
        (),
        (
            _at(1, 1),
            _at(2, 2, x=704),
            _at(3, 1, x=304),
            _at(3, 2, x=304),
            _at(4, 1, x=504),
        ),
        (drawn(1), drawn(2), drawn(3, kind="terminal"), drawn(4, kind="terminal")),
        sheet=SHEET,
    )
    assert [d.case for d in decisions] == [LinkCase.TERMINAL_ECHO]
    assert markers == ()


def test_a_terminal_echo_wins_over_a_tag_echo() -> None:
    """Coil and contact of one item, with a terminal of the net on both pages: no labels."""
    decisions, markers, requests, _ = links(
        (connection(1, 1, 2), _joined(connection(2, 1, 3), 1)),
        (),
        (_at(1, 1), _at(2, 2), _at(3, 1, x=304), _at(3, 2, x=304)),
        (drawn(1), _same_item(2, 1), drawn(3, kind="terminal")),
        sheet=SHEET,
    )
    assert [d.case for d in decisions if d.connection == hid("conductor", 1)] == [
        LinkCase.TERMINAL_ECHO
    ]
    assert (markers, requests) == ((), ())


def test_a_tag_echo_asks_each_function_to_cite_the_other() -> None:
    """Coil 1 on page 1 (column 1), contact 2 on page 2 (column 5): one request each."""
    _, markers, requests, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 1), _at(2, 2, x=704)),
        (drawn(1), _same_item(2, 1)),
        sheet=SHEET,
    )
    assert markers == ()
    assert requests == (
        LabelRequest(
            kind=LabelKind.CROSS_REFERENCE,
            subject=hid("function", 1),
            slot="tag",
            text="p2:5A",
            partners=(RequestPartner(port=hid("port", 21), drawing_set=1, page=2, x=704),),
        ),
        LabelRequest(
            kind=LabelKind.CROSS_REFERENCE,
            subject=hid("function", 2),
            slot="tag",
            text="p1:1A",
            partners=(RequestPartner(port=hid("port", 12), drawing_set=1, page=1, x=104),),
        ),
    )


def test_two_functions_of_different_items_are_a_severed_signal() -> None:
    """The twin of the tag echo: the same geometry with two items gets markers, no requests."""
    decisions, markers, requests, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 1), _at(2, 2, x=704)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert [d.case for d in decisions] == [LinkCase.SEVERED]
    assert len(markers) == 2
    assert requests == ()


# --- cross-unit cuts (units spec U2) ---------------------------------------------------


def test_a_cut_between_two_units_drawing_sets_is_cross_unit() -> None:
    """Two ends in different units' drawing sets: cross-unit, no marker, no request."""
    decisions, markers, requests, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 1, drawing_set=1), _at(2, 2, drawing_set=2, x=704)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
        units=frozendict({1: hid("unit", 1), 2: hid("unit", 2)}),
    )
    assert [d.case for d in decisions] == [LinkCase.CROSS_UNIT]
    assert markers == ()
    assert requests == ()


def test_the_same_cut_within_one_unit_is_still_severed() -> None:
    """The near-identical twin: both drawing sets in one unit, an ordinary severed cut."""
    decisions, markers, _, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 1, drawing_set=1), _at(2, 2, drawing_set=2, x=704)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
        units=frozendict({1: hid("unit", 1), 2: hid("unit", 1)}),
    )
    assert [d.case for d in decisions] == [LinkCase.SEVERED]
    assert len(markers) == 2


def test_cross_unit_wins_over_a_tag_echo() -> None:
    """Read top to bottom: cross-unit is checked before the tag-echo test, so it wins even
    when the two ends belong to one item."""
    decisions, _, requests, _ = links(
        (connection(1, 1, 2),),
        (),
        (_at(1, 1, drawing_set=1), _at(2, 2, drawing_set=2, x=704)),
        (drawn(1), _same_item(2, 1)),
        sheet=SHEET,
        units=frozendict({1: hid("unit", 1), 2: hid("unit", 2)}),
    )
    assert [d.case for d in decisions] == [LinkCase.CROSS_UNIT]
    assert requests == ()


def _boundary_pair(**options):
    """Functions 1 and 2, both of unit 1: each has a home page in set 2 (the unit's, pages 1 and
    2) and a black-box replica page in the unit-less set 1 (pages 1 and 2), where the replica of
    function 1 is the earliest page of each end, and a conductor between them (decision
    layout-0078)."""
    return links(
        (connection(1, 1, 2),),
        (),
        (
            _at(1, 1, drawing_set=1),
            _at(1, 1, drawing_set=2),
            _at(2, 2, drawing_set=1, x=704),
            _at(2, 2, drawing_set=2, x=704),
        ),
        (drawn(1), drawn(2)),
        sheet=SHEET,
        units=frozendict({1: None, 2: hid("unit", 1)}),
        **options,
    )


def test_a_cut_of_two_ends_of_one_unit_stands_on_the_units_own_pages() -> None:
    """With `function_units` naming the unit the markers are on set 2, the unit's, and the cut
    is severed; without it the pages are the ones the old rule gave, so it is the twin that
    proves `function_units` is what moves the marker."""
    unit = hid("unit", 1)
    decisions, markers, _, _ = _boundary_pair(
        function_units=frozendict({hid("function", 1): unit, hid("function", 2): unit})
    )
    assert [d.case for d in decisions] == [LinkCase.SEVERED]
    assert {(m.drawing_set, m.page) for m in markers} == {(2, 1), (2, 2)}
    decisions, markers, _, _ = _boundary_pair()
    assert [d.case for d in decisions] == [LinkCase.SEVERED]
    assert {(m.drawing_set, m.page) for m in markers} == {(1, 1), (1, 2)}


def test_a_boundary_end_with_a_replica_page_first_is_severed_not_cross_unit() -> None:
    """Case (b): function 1 is a boundary function of unit 1 with a replica page in the unit-less
    set 1 and its home page in unit 1's set 2; its peer, function 2, is in set 2 only. The old
    rule cut between the replica page and the peer's page, two units' sets: `CROSS_UNIT`, no
    marker. Now the cut stands on set 2 and is `SEVERED`, with or without `function_units`."""
    unit = hid("unit", 1)
    for function_units in (
        frozendict(),
        frozendict({hid("function", 1): unit, hid("function", 2): unit}),
    ):
        decisions, markers, _, _ = links(
            (connection(1, 1, 2),),
            (),
            (_at(1, 1, drawing_set=1), _at(1, 1, drawing_set=2), _at(2, 2, drawing_set=2, x=704)),
            (drawn(1), drawn(2)),
            sheet=SHEET,
            units=frozendict({1: None, 2: unit}),
            function_units=function_units,
        )
        assert [d.case for d in decisions] == [LinkCase.SEVERED]
        assert {(m.drawing_set, m.page) for m in markers} == {(2, 1), (2, 2)}


def test_a_function_with_several_partners_keeps_one_label_in_page_column_order() -> None:
    """Coil 1 cites `p2:1A p2:5A p10:2A`: numbers sorted as numbers, one request for the coil."""
    _, _, requests, _ = links(
        (connection(1, 1, 2), connection(2, 1, 3), connection(3, 1, 4)),
        (),
        (_at(1, 1), _at(2, 2, x=704), _at(3, 2, x=104), _at(4, 10, x=304)),
        (drawn(1), _same_item(2, 1), _same_item(3, 1), _same_item(4, 1)),
        sheet=SHEET,
    )
    assert [(r.subject, r.text) for r in requests] == [
        (hid("function", 1), "p2:1A p2:5A p10:2A"),
        (hid("function", 2), "p1:1A"),
        (hid("function", 3), "p1:1A"),
        (hid("function", 4), "p1:1A"),
    ]


def test_a_partner_cited_twice_is_listed_once() -> None:
    """Two conductors between the same two functions do not repeat the text."""
    second = Connection(
        handle=hid("conductor", 5),
        physical_net=hid("net", 5),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", 1), port=hid("port", 11)),
        b=PortRef(function=hid("function", 2), port=hid("port", 22)),
    )
    _, _, requests, _ = links(
        (connection(1, 1, 2), second),
        (),
        (_at(1, 1), _at(2, 2, x=704)),
        (drawn(1), _same_item(2, 1)),
        sheet=SHEET,
    )
    assert [r.text for r in requests] == ["p2:5A", "p1:1A"]


def test_a_net_group_cut_can_be_a_tag_echo() -> None:
    """The cut's two end functions decide, whether it came from a conductor or a net group."""
    decisions, markers, requests, _ = links(
        (),
        (_net_group(7, ((1, 12), (2, 21))),),
        (_at(1, 1), _at(2, 2, x=704)),
        (drawn(1), _same_item(2, 1)),
        sheet=SHEET,
    )
    assert [d.case for d in decisions] == [LinkCase.TAG_ECHO]
    assert markers == ()
    assert [r.subject for r in requests] == [hid("function", 1), hid("function", 2)]


# --- ends drawn on several pages ------------------------------------------------------


def test_a_connection_whose_ends_share_a_page_through_a_terminal_is_not_cut() -> None:
    """Terminal 3 is on pages 1 and 2 and function 2 on page 2: route draws it, links is silent."""
    decisions, markers, requests, findings = links(
        (connection(1, 2, 3),),
        (),
        (_at(2, 2), _at(3, 2, x=304), _at(3, 1, x=304)),
        (drawn(2), drawn(3, kind="terminal")),
        sheet=SHEET,
    )
    assert (decisions, markers, requests, findings) == ((), (), (), ())


@pytest.mark.parametrize("terminal", [3, 0])
def test_a_connection_to_a_terminal_on_other_pages_is_cut_at_the_terminals_earliest_page(
    terminal,
) -> None:
    """Function 2 on page 2, the terminal on pages 3 and 1 (at x = 304, 504): the cut is 2 to 1.

    Terminal 0 is the `a` end of the conductor and terminal 3 the `b` end; the terminal's
    marker sits where it is placed on page 1, not on page 3.
    """
    decisions, markers, _, _ = links(
        (connection(1, 2, terminal),),
        (),
        (_at(2, 2, x=704), _at(terminal, 3, x=304), _at(terminal, 1, x=504)),
        (drawn(2), drawn(terminal, kind="terminal")),
        sheet=SHEET,
    )
    assert [d.case for d in decisions] == [LinkCase.SEVERED]
    assert {(m.port, m.side, m.page, m.partner_page, m.at) for m in markers} == {
        (hid("port", terminal * 10 + 1), MarkerSide.OWNER, 1, 2, Point(x=504, y=80)),
        (hid("port", 22), MarkerSide.USER, 2, 1, Point(x=704, y=112)),
    }


def test_the_earliest_page_of_an_end_is_earliest_by_drawing_set_then_page() -> None:
    """Terminal 3 on (drawing set 2, page 1) and (drawing set 1, page 3): (1, 3) is earlier."""
    _, markers, _, _ = links(
        (connection(1, 2, 3),),
        (),
        (_at(2, 2), _at(3, 1, drawing_set=2), _at(3, 3)),
        (drawn(2), drawn(3, kind="terminal")),
        sheet=SHEET,
    )
    assert {(m.side, m.drawing_set, m.page) for m in markers} == {
        (MarkerSide.OWNER, 1, 2),
        (MarkerSide.USER, 1, 3),
    }


# --- net groups -----------------------------------------------------------------------


def test_a_net_group_on_three_pages_is_cut_twice_and_the_middle_page_holds_two_markers() -> None:
    """Pages 1, 2, 3: cuts (1, 2) and (2, 3); page 2's port is a user and an owner marker."""
    decisions, markers, _, _ = links(
        (),
        (_net_group(7, ((1, 12), (2, 21), (3, 32))),),
        (_at(1, 1), _at(2, 2, x=304), _at(3, 3, x=704)),
        (drawn(1), drawn(2), drawn(3)),
        sheet=SHEET,
    )
    assert _cases(decisions) == [
        (hid("net", 7), hid("port", 12), hid("port", 21), LinkCase.SEVERED),
        (hid("net", 7), hid("port", 21), hid("port", 32), LinkCase.SEVERED),
    ]
    assert [(m.port, m.side, m.page, m.partner_page) for m in markers] == [
        (hid("port", 12), MarkerSide.OWNER, 1, 2),
        (hid("port", 21), MarkerSide.OWNER, 2, 3),
        (hid("port", 21), MarkerSide.USER, 2, 1),
        (hid("port", 32), MarkerSide.USER, 3, 2),
    ]
    assert {m.connection for m in markers} == {hid("net", 7)}


def test_a_net_group_decision_is_in_port_handle_order_and_the_owner_follows_the_page() -> None:
    """Function 3's port (the higher handle) is on page 1: `a` is port 12, the owner is port 32."""
    decisions, markers, _, _ = links(
        (),
        (_net_group(7, ((1, 12), (3, 32))),),
        (_at(3, 1), _at(1, 2)),
        (drawn(1), drawn(3)),
        sheet=SHEET,
    )
    assert [(d.a, d.b) for d in decisions] == [(hid("port", 12), hid("port", 32))]
    assert _owner_and_user(markers) == (hid("port", 32), hid("port", 12))


def test_decisions_are_sorted_by_port_handles_not_by_page_order() -> None:
    """Pages 1 to 4 hold ports 32, 41, 12, 21; the cuts arise as (32, 41), (12, 41), (12, 21)."""
    decisions, _, _, _ = links(
        (),
        (_net_group(7, ((3, 32), (4, 41), (1, 12), (2, 21))),),
        (_at(3, 1), _at(4, 2), _at(1, 3), _at(2, 4)),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        sheet=SHEET,
    )
    assert [(d.a, d.b) for d in decisions] == [
        (hid("port", 12), hid("port", 21)),
        (hid("port", 12), hid("port", 41)),
        (hid("port", 32), hid("port", 41)),
    ]


def test_one_port_marking_two_cuts_as_owner_gives_its_markers_in_page_order() -> None:
    """Terminal 3 is on pages 1 and 3, function 1 on page 2 and function 2 on page 4.

    Port 31 is the lowest of its pages, so it owns two cuts: `(net, port, side)` repeats,
    and the markers come out in page order because the cuts are generated in it.
    """
    _, markers, _, _ = links(
        (),
        (_net_group(7, ((3, 31), (1, 12), (2, 21))),),
        (_at(3, 1), _at(1, 2), _at(3, 3), _at(2, 4)),
        (drawn(1), drawn(2), drawn(3, kind="terminal")),
        sheet=SHEET,
    )
    assert [(m.port, m.side, m.page) for m in markers] == [
        (hid("port", 12), MarkerSide.OWNER, 2),
        (hid("port", 12), MarkerSide.USER, 2),
        (hid("port", 21), MarkerSide.USER, 4),
        (hid("port", 31), MarkerSide.OWNER, 1),
        (hid("port", 31), MarkerSide.OWNER, 3),
        (hid("port", 31), MarkerSide.USER, 3),
    ]


def test_a_net_groups_pages_are_ordered_by_drawing_set_then_page() -> None:
    """Function 1 on (drawing set 2, page 1), function 2 on (drawing set 1, page 5): 2 owns."""
    _, markers, _, _ = links(
        (),
        (_net_group(7, ((1, 12), (2, 21))),),
        (_at(1, 1, drawing_set=2), _at(2, 5)),
        (drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert _owner_and_user(markers) == (hid("port", 21), hid("port", 12))


def test_a_net_group_of_one_port_is_not_cut() -> None:
    """A single port has one page; there is nothing to cut."""
    result = links((), (_net_group(7, ((1, 12),)),), (_at(1, 1),), (drawn(1),), sheet=SHEET)
    assert result == ((), (), (), ())


# --- LINK_FANOUT ----------------------------------------------------------------------


def _fanout_case(*, second_net=1, second_user_page=2, users_share_item=False):
    """Conductors 1 and 2 leave function 1 (page 1) for functions 2 and 3.

    Both are on physical net 1 unless `second_net` says otherwise; function 3 is on
    `second_user_page`; `users_share_item` makes both users belong to function 1's item.
    """
    first = connection(1, 1, 2)
    second = _joined(connection(2, 1, 3), second_net)
    return links(
        (first, second),
        (),
        (_at(1, 1), _at(2, 2, x=704), _at(3, second_user_page, x=304)),
        (
            drawn(1),
            _same_item(2, 1) if users_share_item else drawn(2),
            _same_item(3, 1) if users_share_item else drawn(3),
        ),
        sheet=SHEET,
    )


def test_two_severed_cuts_of_one_net_between_two_pages_give_one_warning() -> None:
    """The finding names both conductors, in handle order."""
    _, _, _, findings = _fanout_case()
    assert [(f.code, f.severity, f.subjects) for f in findings] == [
        (LINK_FANOUT, Severity.WARNING, (hid("conductor", 1), hid("conductor", 2)))
    ]


@pytest.mark.parametrize(
    "variant",
    [
        pytest.param({"second_net": 9}, id="two-nets"),
        pytest.param({"second_user_page": 3}, id="two-page-pairs"),
        pytest.param({"users_share_item": True}, id="tag-echoes-not-severed"),
    ],
)
def test_the_fanout_needs_one_net_one_page_pair_and_severed_cuts(variant) -> None:
    """Each variant changes one thing from the case above and is not reported."""
    assert _fanout_case(**variant)[3] == ()


def test_three_cuts_of_one_net_and_page_pair_are_still_one_warning() -> None:
    """The finding is per net and page pair, not per pair of cuts."""
    _, _, _, findings = links(
        (
            connection(1, 1, 2),
            _joined(connection(2, 1, 3), 1),
            _joined(connection(3, 1, 4), 1),
        ),
        (),
        (_at(1, 1), _at(2, 2, x=704), _at(3, 2, x=304), _at(4, 2, x=504)),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        sheet=SHEET,
    )
    assert [f.subjects for f in findings] == [
        (hid("conductor", 1), hid("conductor", 2), hid("conductor", 3))
    ]


def test_a_net_groups_cut_counts_as_a_severed_cut_of_its_physical_net() -> None:
    """The group's own handle differs from its physical net; the net decides."""
    group = NetGroup(
        net=hid("net", 7),
        physical_net=hid("net", 9),
        role=Role.CONTROL,
        ports=(
            PortRef(function=hid("function", 1), port=hid("port", 12)),
            PortRef(function=hid("function", 2), port=hid("port", 21)),
        ),
    )
    other = _joined(connection(1, 3, 4), 9)
    _, _, _, findings = links(
        (other,),
        (group,),
        (_at(1, 1), _at(2, 2), _at(3, 1, x=304), _at(4, 2, x=304)),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        sheet=SHEET,
    )
    assert [f.subjects for f in findings] == [(hid("conductor", 1), hid("net", 7))]


def test_the_fanout_page_pair_includes_the_drawing_set() -> None:
    """Both cuts run from page 1 to page 2, but the second user is in drawing set 2: two pairs."""
    first = connection(1, 1, 2)
    second = _joined(connection(2, 1, 3), 1)
    _, _, _, findings = links(
        (first, second),
        (),
        (_at(1, 1), _at(2, 2, x=704), _at(3, 2, x=304, drawing_set=2)),
        (drawn(1), drawn(2), drawn(3)),
        sheet=SHEET,
    )
    assert findings == ()


def test_a_fanout_is_found_whichever_end_of_each_conductor_is_the_owner() -> None:
    """Function 0's port has the lowest handle, so it is conductor 2's `a` end and the user's."""
    _, _, _, findings = links(
        (connection(1, 1, 2), _joined(connection(2, 0, 1), 1)),
        (),
        (_at(1, 1), _at(2, 2, x=704), _at(0, 2, x=304)),
        (drawn(0), drawn(1), drawn(2)),
        sheet=SHEET,
    )
    assert [f.subjects for f in findings] == [(hid("conductor", 1), hid("conductor", 2))]


def test_two_fanned_out_nets_give_two_warnings_in_subject_order() -> None:
    """Nets 1 and 4 each leave a function on page 1 for two functions on page 2."""
    _, _, _, findings = links(
        (
            connection(4, 4, 5),
            _joined(connection(3, 4, 6), 4),
            connection(1, 1, 2),
            _joined(connection(2, 1, 3), 1),
        ),
        (),
        (
            _at(1, 1),
            _at(4, 1, x=304),
            _at(2, 2, x=104),
            _at(3, 2, x=304),
            _at(5, 2, x=504),
            _at(6, 2, x=704),
        ),
        tuple(drawn(n) for n in (1, 2, 3, 4, 5, 6)),
        sheet=SHEET,
    )
    assert [f.subjects for f in findings] == [
        (hid("conductor", 1), hid("conductor", 2)),
        (hid("conductor", 3), hid("conductor", 4)),
    ]


# --- order and shuffle ----------------------------------------------------------------


def test_decisions_come_out_in_connection_order() -> None:
    """Conductor 2 (ports 12, 21) given first; conductor 1 (ports 32, 41) still sorts first."""
    decisions, _, _, _ = links(
        (connection(2, 1, 2), connection(1, 3, 4)),
        (),
        (_at(1, 1), _at(2, 2), _at(3, 1, x=304), _at(4, 2, x=304)),
        tuple(drawn(n) for n in (1, 2, 3, 4)),
        sheet=SHEET,
    )
    assert [d.connection for d in decisions] == [hid("conductor", 1), hid("conductor", 2)]


def test_nothing_to_link_gives_nothing() -> None:
    """No connections, no net groups, no pages."""
    assert links((), (), (), (), sheet=SHEET) == ((), (), (), ())


def _busy_page_set():
    """Every case at once: severed with fan-out, tag echo, terminal echo, cross-unit, two
    net groups. Functions 16/17 (drawing sets 1 and 2, a unit each) are the cross-unit pair;
    the rest all sit on drawing set 1, so `units`'s one entry for drawing set 2 (`_UNIT`,
    below) never touches them."""
    connections = (
        connection(1, 1, 2),
        _joined(connection(2, 1, 3), 1),
        connection(3, 4, 5),
        connection(4, 6, 7),
        _joined(connection(5, 6, 8), 4),
        connection(6, 9, 10),
        connection(7, 16, 17),
    )
    groups = (
        _net_group(30, ((11, 112), (12, 121), (13, 132))),
        _net_group(31, ((14, 142), (15, 151))),
    )
    functions = (
        _at(1, 1),
        _at(2, 2, x=704),
        _at(3, 2, x=304),
        _at(4, 1, x=504),
        _at(5, 3, x=104),
        _at(6, 1, x=704),
        _at(7, 2, x=504),
        _at(8, 1, x=904),
        _at(8, 2, x=904),
        _at(9, 1, x=1104),
        _at(10, 3, x=304),
        _at(11, 1, x=104, y=400),
        _at(12, 2, x=104, y=400),
        _at(13, 3, x=104, y=400),
        _at(14, 2, x=104, y=500),
        _at(15, 3, x=104, y=500),
        _at(16, 1, x=1304),
        _at(17, 1, x=104, drawing_set=2),
    )
    drawings = (
        *(drawn(n) for n in (1, 2, 3, 4, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17)),
        _same_item(5, 4),
        drawn(8, kind="terminal"),
        _same_item(10, 9),
    )
    return connections, groups, functions, drawings


# Drawing set 2's unit, in `_busy_page_set`'s own `units` mapping below: the fixture's other
# entities all sit on drawing set 1, which the mapping leaves unentered (`None`), so this is
# the only unit boundary the fixture ever crosses.
_UNIT = hid("unit", 99)


def test_the_result_is_equal_under_every_input_shuffle() -> None:
    """Connections, net groups, placed and drawn functions all permute freely."""
    connections, groups, functions, drawings = _busy_page_set()
    units = frozendict({2: _UNIT})
    forward = links(connections, groups, functions, drawings, sheet=SHEET, units=units)
    decisions, markers, requests, findings = forward
    assert {d.case for d in decisions} == set(LinkCase)
    assert markers != ()
    assert requests != ()
    assert findings != ()
    for permuted in itertools.islice(itertools.permutations(connections), 0, 720, 37):
        for step in (1, -1):
            assert (
                links(
                    permuted,
                    groups[::step],
                    functions[::step],
                    drawings[::step],
                    sheet=SHEET,
                    units=units,
                )
                == forward
            )


# --- engine-assembly faults -----------------------------------------------------------


_PLAIN = ((connection(1, 1, 2),), (_at(1, 1), _at(2, 2, x=704)), (drawn(1), drawn(2)))


def _cut_pair(*, connections=_PLAIN[0], net_groups=(), functions=_PLAIN[1], drawings=_PLAIN[2]):
    """The plain two-page conductor of the skeletons, with any argument replaced."""
    return links(connections, net_groups, functions, drawings, sheet=SHEET)


def test_the_plain_cut_used_by_the_fault_tests_does_not_raise() -> None:
    """The twin of every fault below."""
    assert len(_cut_pair()[1]) == 2


def test_one_function_placed_twice_on_one_page_raises() -> None:
    """Two placements of one function on one page are an assembly fault."""
    with pytest.raises(LayoutError):
        _cut_pair(functions=(_at(1, 1), _at(1, 1, x=304), _at(2, 2, x=704)))


def test_a_terminal_placed_on_two_pages_does_not_raise() -> None:
    """The twin: one function on two different pages is what a terminal is."""
    _cut_pair(functions=(_at(1, 1), _at(1, 3), _at(2, 2, x=704)))


def test_a_conductor_end_that_is_not_placed_raises() -> None:
    """Every page is placed before `links` runs, so an unplaced end is a fault."""
    with pytest.raises(LayoutError):
        _cut_pair(functions=(_at(1, 1),))


def test_a_net_group_port_that_is_not_placed_raises() -> None:
    """The same for a net group."""
    group = _net_group(7, ((1, 12), (2, 21)))
    assert _cut_pair(connections=(), net_groups=(group,))[0] != ()
    with pytest.raises(LayoutError):
        _cut_pair(connections=(), net_groups=(group,), functions=(_at(1, 1),))


def test_a_conductor_end_that_is_not_drawn_raises() -> None:
    """The function has no `DrawnFunction`, so its kind and item are unknown."""
    with pytest.raises(LayoutError):
        _cut_pair(drawings=(drawn(1),))


def test_a_same_page_conductor_end_that_is_not_drawn_raises_too() -> None:
    """The stage reads every end's kind to find the terminals of a net, cut or not."""
    same_page = (_at(1, 1), _at(2, 1, x=304))
    _cut_pair(functions=same_page)
    with pytest.raises(LayoutError):
        _cut_pair(functions=same_page, drawings=(drawn(1),))


def test_a_net_group_port_that_is_not_drawn_raises() -> None:
    """A terminal test needs every port's function drawn."""
    group = _net_group(7, ((1, 12), (2, 21)))
    with pytest.raises(LayoutError):
        _cut_pair(connections=(), net_groups=(group,), drawings=(drawn(1),))


def test_a_port_that_is_not_a_drawn_port_of_its_function_raises() -> None:
    """Port 99 is not one of function 1's drawn ports."""
    stray = Connection(
        handle=hid("conductor", 1),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", 1), port=hid("port", 99)),
        b=PortRef(function=hid("function", 2), port=hid("port", 21)),
    )
    with pytest.raises(LayoutError):
        _cut_pair(connections=(stray,))


def test_a_symbol_port_the_placed_symbol_lacks_raises() -> None:
    """Function 1's port 12 is drawn at `nowhere`, which its geometry does not have."""
    lost = dataclasses.replace(
        drawn(1), ports=(DrawnPort(port=hid("port", 12), symbol_port="nowhere"),)
    )
    with pytest.raises(LayoutError):
        _cut_pair(drawings=(lost, drawn(2)))
