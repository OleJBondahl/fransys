"""Acceptance skeletons and unit tests: `stages.links`."""

import dataclasses

import pytest
from samples import PROFILE, SHEET, built_links, connection, drawn, hid, placed

from fransys_layout.geometry import Box, LayoutError, Point
from fransys_layout.stages import (
    Connection,
    DrawnFunction,
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
    """`stages.links` built by `texts`, with this file's sheet, profile, paths and units.

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


def _net_group(number: int, ports: tuple[tuple[int, int], ...]) -> NetGroup:
    """Net `number` over `(function, port)` pairs, with no conductors."""
    return NetGroup(
        net=hid("net", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        ports=tuple(PortRef(function=hid("function", f), port=hid("port", p)) for f, p in ports),
    )


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
    user's faces N, so its box ends one stub short of the port (decision
    layout-0038). Each is centred on its port, turned (a text height wide, the
    sheet's fixed reference width long), never measured from its own text.
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


def _shifted(number: int, page: int, *, x: int, dx: int) -> PlacedFunction:
    """Function `number` whose symbol has its ports `dx` right of its origin."""
    one = _at(number, page, x=x, y=304)
    ports = tuple(
        dataclasses.replace(port, at=Point(x=port.at.x + dx, y=port.at.y))
        for port in one.geometry.ports
    )
    return dataclasses.replace(one, geometry=dataclasses.replace(one.geometry, ports=ports))


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


# --- cross-unit cuts ---------------------------------------------------


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


# --- ends drawn on several pages ------------------------------------------------------


# --- net groups -----------------------------------------------------------------------


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


# --- engine-assembly faults -----------------------------------------------------------


_PLAIN = ((connection(1, 1, 2),), (_at(1, 1), _at(2, 2, x=704)), (drawn(1), drawn(2)))


def _cut_pair(*, connections=_PLAIN[0], net_groups=(), functions=_PLAIN[1], drawings=_PLAIN[2]):
    """The plain two-page conductor of the skeletons, with any argument replaced."""
    return links(connections, net_groups, functions, drawings, sheet=SHEET)


def test_one_function_placed_twice_on_one_page_raises() -> None:
    """Two placements of one function on one page are an assembly fault."""
    with pytest.raises(LayoutError):
        _cut_pair(functions=(_at(1, 1), _at(1, 1, x=304), _at(2, 2, x=704)))
