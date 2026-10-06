"""Properties of the schematic pass: determinism, idempotence and stability (package-layout.md 9).

Each run is the invented cabinet through `lay_out_schematic`; `width_mm` authors a narrower sheet,
which gives every group a page of its own.
"""

from collections import Counter
from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_model.kernel import Origin, freeze, make_id
from fransys_model.layout import Profile, SheetFormat
from fransys_model.vocab import AspectNode

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Model

_ORIGIN = Origin(file="tests/engines/test_properties_digest.py", line=1, note="property tests")
_KINDS = ("drawing_set", "page", "symbol_placement", "route", "link_marker", "label")
_P2 = make_id(AspectNode, ("p2",))
# a sheet content width (mm) on which `=P2` and `=SUP` share a page once K9 joins `=P2` (V4 drew
# the rail terminal's replica over its pin, so the default sheet is one such width too)
_MERGING_WIDTH = 410  # was 400 before layout-0103 widened the PLC box for its contacts
# a width on which `=P2` stands on a page of its own, apart from `=SUP`, with or without K9
_APART_WIDTH = 360
_CONFIGS = [
    pytest.param({}, id="default"),
    pytest.param({"second_location": True}, id="two-locations"),
    pytest.param({"width_mm": 250}, id="250mm"),
]


@cache
def _run(
    *,
    reverse: bool = False,
    extra_relay: bool = False,
    second_location: bool = False,
    width_mm: int | None = None,
) -> tuple[Model, Model, tuple[Finding, ...]]:
    """The frozen cabinet, its laid-out model and the findings."""
    draft = build_cabinet(reverse=reverse, extra_relay=extra_relay, second_location=second_location)
    if width_mm is not None:
        sheet = SheetFormat(
            id=make_id(SheetFormat, ("test", "sheet")),
            key=("test", "sheet"),
            name="narrow",
            width_mm=width_mm + 20,
            height_mm=297,
            content_x_mm=10,
            content_y_mm=10,
            content_width_mm=width_mm,
            content_height_mm=277,
            frame_columns=8,
            frame_rows=6,
            module_mm=Decimal("2.5"),
        )
        profile = Profile(
            id=make_id(Profile, ("test", "profile")),
            key=("test", "profile"),
            sheet_format=sheet.id,
            column_gap=DEFAULT_PROFILE.column_gap,
            row_gap=DEFAULT_PROFILE.row_gap,
            route_margin=DEFAULT_PROFILE.route_margin,
            text_height=DEFAULT_PROFILE.text_height,
            marker_padding=DEFAULT_PROFILE.marker_padding,
            route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
            route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
            band_ranks=DEFAULT_PROFILE.band_ranks,
            group_ranks=DEFAULT_PROFILE.group_ranks,
        )
        draft.extend((sheet, profile), origin=_ORIGIN)
    model = freeze(draft)
    out, findings = lay_out_schematic(model)
    return model, out, findings


def _table(model: Model, kind: str) -> dict:
    return dict(model.tables.get(f"layout.{kind}", {}))


def _pages_holding_p2(model: Model) -> set:
    pages = _table(model, "page").values()
    return {page.id for page in pages if any(group.group == _P2 for group in page.groups)}


def _moved_off_shared_pages(plain: Model, extra: Model, group: object) -> list:
    """The page-local promise (designer): a group that shares no page with `group`, before or
    after, keeps every placement byte-identical. A group sharing such a page may shift along
    it, the price of packing. Returns the placements that break it."""
    pages = [*_table(plain, "page").values(), *_table(extra, "page").values()]
    shared = {
        g.group for page in pages if any(g.group == group for g in page.groups) for g in page.groups
    }
    free = {page.id for page in pages if not {g.group for g in page.groups} & shared}
    after = _table(extra, "symbol_placement")
    return [
        record
        for id_, record in _table(plain, "symbol_placement").items()
        if record.page in free and after.get(id_) != record
    ]


@pytest.mark.parametrize("flags", _CONFIGS)
def test_laying_out_one_model_twice_gives_one_result(flags: dict) -> None:
    """A pure pass: equal layout digest and findings, and no engineering digest moves."""
    model, out, findings = _run(**flags)
    again, again_findings = lay_out_schematic(model)
    assert again.digests["layout"] == out.digests["layout"]
    assert again_findings == findings
    assert out.digests["layout"] != model.digests["layout"]
    for engineering in ("core", "facet"):
        assert out.digests[engineering] == model.digests[engineering]


@pytest.mark.parametrize("flags", _CONFIGS)
def test_two_insertion_orders_give_one_layout_digest(flags: dict) -> None:
    """The same design authored in opposite orders lays out to one digest."""
    model, out, findings = _run(**flags)
    shuffled, shuffled_out, shuffled_findings = _run(reverse=True, **flags)
    assert shuffled.digests == model.digests
    assert shuffled_out.digests["layout"] == out.digests["layout"]
    assert shuffled_findings == findings


@pytest.mark.parametrize("flags", _CONFIGS)
def test_laying_out_a_laid_out_model_replaces_and_never_stacks(flags: dict) -> None:
    """The pass on its own output: same digests, same record count per derived kind."""
    _, once, findings = _run(**flags)
    twice, again_findings = lay_out_schematic(once)
    counts = {kind: len(_table(once, kind)) for kind in _KINDS}
    assert all(counts[kind] for kind in ("page", "symbol_placement", "route", "label"))
    assert {kind: len(_table(twice, kind)) for kind in _KINDS} == counts
    assert twice.digests == once.digests
    assert again_findings == findings


@pytest.mark.parametrize("width_mm", [None, 250])
def test_a_relay_in_one_group_changes_records_only_on_the_pages_of_that_group(
    width_mm: int | None,
) -> None:
    """K9 joins `=P2`: every changed or new placement, route and label is on a page holding it."""
    _, plain, _ = _run(width_mm=width_mm)
    _, extra, _ = _run(extra_relay=True, width_mm=width_mm)
    p2_pages = _pages_holding_p2(extra)
    for kind in ("symbol_placement", "route", "label"):
        before = _table(plain, kind)
        changed = [
            record for id_, record in _table(extra, kind).items() if before.get(id_) != record
        ]
        assert changed
        assert {record.page for record in changed} <= p2_pages
    placements = _table(extra, "symbol_placement")
    k9 = [record for record in placements.values() if record.key[3:6] == ("cabinet", "k9", "fn")]
    assert k9
    assert not {record.id for record in k9} & set(_table(plain, "symbol_placement"))
    # page-local: every group with no page in common with `=P2` is byte-identical
    assert _moved_off_shared_pages(plain, extra, _P2) == []


def test_the_page_local_check_can_fail() -> None:
    """A group on a page of its own that also changes is caught: `=P2` is asked about a
    layout it shares no page with (the 250 mm sheet's own layout, moved by the relay)."""
    _, plain, _ = _run(width_mm=250)
    _, extra, _ = _run(extra_relay=True, width_mm=250)
    assert _moved_off_shared_pages(plain, extra, make_id(AspectNode, ("nowhere",))) != []


@pytest.mark.parametrize(
    ("width_mm", "cut", "lost_counts"),
    [
        (_APART_WIDTH, 1, {"route": 1}),
        (_MERGING_WIDTH, 1, {"page": 1, "route": 1}),
    ],
)
def test_ids_survive_the_repagination_except_a_route_the_new_page_break_cuts(
    width_mm: int | None, cut: int, lost_counts: dict[str, int]
) -> None:
    """`=P2` leaves the page it shared with `=P1`: the K1 to K2 wire is cut.

    This pins the exact set of ids the repagination loses. On the default sheet it is the cut
    route alone: `=P2` stands on a page of its own, and `=SUP` keeps its own page (D7: a lane
    that carries a contact image reserves its width, so `=P2` and `=SUP` no longer fit together).
    On a sheet wide enough for `=P2` and `=SUP` to share a page (`_MERGING_WIDTH`) it is also the
    one page keyed by its first group (`=SUP`, merged into the next page). A star marker's key
    names no partner (layout-0052), so K9's group adding an earlier branch renames no reference
    marker: a lost marker of any kind, or a second page, fails here.
    """
    # UNDO: the expected count `"page": 1` -> `"page": 2` (a second lost page must fail; the
    # `_MERGING_WIDTH` case)
    _, plain, _ = _run(width_mm=width_mm)
    _, extra, _ = _run(extra_relay=True, width_mm=width_mm)
    lost = [
        (kind, record)
        for kind in _KINDS
        for id_, record in _table(plain, kind).items()
        if id_ not in _table(extra, kind)
    ]
    assert Counter(kind for kind, _ in lost) == lost_counts
    for kind, record in lost:
        if kind == "route":
            assert record.page in _pages_holding_p2(plain)
        else:  # keyed by its first group, which is still drawn after
            sup = make_id(AspectNode, ("sup",))
            assert record.groups[0].group == sup
            assert any(
                g.group == sup for page in _table(extra, "page").values() for g in page.groups
            )
    # only the cut wire's pair is new among the pair markers (K9's star markers are not pairs)
    pairs = [
        len([m for m in _table(model, "link_marker").values() if m.star is None])
        for model in (plain, extra)
    ]
    assert pairs[1] - pairs[0] == 2 * cut


_RAIL = ("cabinet", "x2", "1", "fn", "terminal", "port", "external")
_SIGNAL = (
    ("cabinet", "k1", "fn", "aux", "port", "14"),
    ("cabinet", "k2", "fn", "aux", "port", "13"),
)


def _groups_sharing_a_page_with_p2(*models: Model) -> set:
    """Every group that stands on a page with `=P2`, in any of `models`."""
    pages = [page for model in models for page in _table(model, "page").values()]
    return {
        entry.group
        for page in pages
        if any(entry.group == _P2 for entry in page.groups)
        for entry in page.groups
    }


@pytest.mark.parametrize(
    ("width_mm", "cut", "replica", "page_lost"),
    [(_APART_WIDTH, 1, True, False), (_MERGING_WIDTH, 1, False, True), (250, 0, False, False)],
)
def test_a_relay_in_one_group_keeps_every_id_but_a_repacked_page_and_a_redrawn_net(
    *, width_mm: int | None, cut: int, replica: bool, page_lost: bool
) -> None:
    """D4, D9, D17: a device keeps its id whatever page it moves to; only what the repacking
    or K9's net changes is lost.

    K9 joins the 24 V rail net of `-X2:1`, so a member wire of that net may become markers (D9),
    and a page is keyed by its first group, so one whose group moves onto P2's page is lost
    (`page_lost`). On the default sheet and on `_MERGING_WIDTH` `=P2` leaves the page it shared
    with `=P1`, so the K1:14 to K2:13 wire, the only one across the two, is cut and gets its
    marker pair (links.md 6.6): `cut` is 1 there and 0 on the 250 mm sheet, where every group has a
    page of its own before and after. On the default sheet (D7) `=P2` also stands apart from
    `=SUP`, whose page keeps its key, so `=P2`'s page needs its own replica of the rail terminal
    `-X2:1` (`replica`), a new placement of `-X2`.
    """
    _, plain, _ = _run(width_mm=width_mm)
    model, extra, _ = _run(extra_relay=True, width_mm=width_mm)
    port_key = {id_: port.key for id_, port in model.tables["port"].items()}
    signal_ports = {id_ for id_, key in port_key.items() if key in _SIGNAL}
    lost = {
        kind: [
            record for id_, record in _table(plain, kind).items() if id_ not in _table(extra, kind)
        ]
        for kind in _KINDS
    }
    # a device never changes id when its page does; the new ones are K9 and its terminal X5:1,
    # and the rail terminal's replica where =P2 no longer shares a page with its home group
    assert lost["symbol_placement"] == []
    placements = _table(extra, "symbol_placement")
    added = set(placements) - set(_table(plain, "symbol_placement"))
    assert {placements[id_].key[3:5] for id_ in added} == {
        ("cabinet", "k9"),
        ("cabinet", "x5"),
        *([("cabinet", "x2")] if replica else []),
    }
    # a page is keyed by its first group: only one whose groups now stand with =P2 is lost
    sharing = _groups_sharing_a_page_with_p2(plain, extra)
    assert bool(lost["page"]) is page_lost
    assert all({entry.group for entry in page.groups} <= sharing for page in lost["page"])
    # a lost route is the cut wire, or a wire of the rail net that K9 grew (D9)
    ends = [{port_key[route.a], port_key[route.b]} for route in lost["route"]]
    assert ends
    assert all(end == set(_SIGNAL) or _RAIL in end for end in ends)
    assert sum(end == set(_SIGNAL) for end in ends) == cut
    # its wire label goes with it, and only wire labels are lost
    wires = {route.key[3:] for route in lost["route"]}
    assert all(label.kind.value == "wire" and label.key[3:-1] in wires for label in lost["label"])
    # the signal's marker pair keeps its ids; it is new exactly when the wire was cut
    pair = {
        id_ for id_, marker in _table(extra, "link_marker").items() if marker.port in signal_ports
    }
    before = {
        id_ for id_, marker in _table(plain, "link_marker").items() if marker.port in signal_ports
    }
    assert before <= pair
    assert len(pair - before) == 2 * cut
    # every other lost marker is a star marker of a port that still has one
    lost_ports = {marker.port for marker in lost["link_marker"]}
    assert not lost_ports & signal_ports
    assert lost_ports <= {marker.port for marker in _table(extra, "link_marker").values()}
