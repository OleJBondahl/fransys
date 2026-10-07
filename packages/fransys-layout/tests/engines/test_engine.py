"""The engine loop `stage_results` on the invented cabinet (foundations.md 3, engine.md 7;
layout-0021, 0024).

The default sheet holds `=P1` and `=P2` on one page. An authored narrow sheet (`_run` with a
width) splits the cabinet over several pages, which is what makes a terminal echo, a severed marker
and a tag echo show. Functions are found by authoring key, never by designation.
"""

import dataclasses
from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING

import pytest
from layout_cabinet import build_cabinet
from routing import route
from samples import NO_HINTS, PROFILE, SHEET, drawn, hid, placed
from wired_cabinet import wired_cabinet

from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import StageInputs, read_inputs, reading
from fransys_layout.engines.schematic.read.harness_lines import line_reads
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.geometry import Box, Facing, overlaps
from fransys_layout.lint._segments import runs_of
from fransys_layout.stages import (
    Home,
    LabelKind,
    LabelRequest,
    LinkCase,
    PlacedLabel,
)
from fransys_layout.stages.pagerun import PageInputs, PageState, finish_page
from fransys_layout.stages.references import LINK_PARTNER_UNLOCATED
from fransys_layout.stages.space import crosses
from fransys_model.derive import natural_key
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import GroupHint, Profile, SheetFormat
from fransys_model.vocab import AspectNode, Function, Item

if TYPE_CHECKING:
    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_model.kernel import Finding

_ORIGIN = Origin(file="tests/engines/test_engine.py", line=1, note="engine tests")
_X2 = ("cabinet", "x2", "1", "fn", "terminal")
_COHERENCE = {
    "CONNECTION_NOT_DRAWN",
    "CONNECTION_DRAWN_TWICE",
    "ROUTE_WRONG_PORT",
    "ROUTE_SHORTS_NETS",
    "MARKER_UNPAIRED",
}


@cache
def _run(
    width_mm: int | None = None,
    *,
    reverse: bool = False,
    second_location: bool = False,
    k8_coil_in_p1: bool = False,
    wired: bool = False,
) -> tuple[StageInputs, StageResults, tuple[Finding, ...]]:
    """The cabinet through `stage_results`; with `width_mm`, on an authored sheet that wide.

    With `k8_coil_in_p1` the coil of the spare relay `-K8` carries a `layout.group_hint` to
    `=P1` while its contact stays in `=SUP`: the one item's two functions then stand in two
    groups. With `wired` the cable `W1`'s cores are wires (`wired_cabinet`), not a line (HL1).
    """
    build = wired_cabinet if wired else build_cabinet
    draft = build(reverse=reverse, second_location=second_location)
    if k8_coil_in_p1:
        hint_key = ("cabinet", "k8", "fn", "coil", "group_hint")
        hint = GroupHint(
            id=make_id(GroupHint, hint_key),
            key=hint_key,
            function=make_id(Function, ("cabinet", "k8", "fn", "coil")),
            group=make_id(AspectNode, ("p1",)),
        )
        draft.extend((hint,), origin=_ORIGIN)
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
        # the default profile on the authored sheet: only the sheet's width changes
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
    inputs = read_inputs(model)
    results, findings = stage_results(model, inputs)
    return inputs, results, findings


def test_run_stages_returns_the_layout_the_drawn_functions_and_the_findings() -> None:
    """The public triple is `stage_results`' layout, drawn functions and findings."""
    inputs, results, findings = _run()
    model = freeze(build_cabinet())
    assert run_stages(model, inputs) == (results.layout, results.drawn, findings)


def _function(inputs: StageInputs, key: tuple[str, ...]):
    (spec,) = (s for s in inputs.functions if s.key == key)
    return spec.function


def _pages_of(results: StageResults, function) -> list[tuple[int, int]]:
    return sorted((p.drawing_set, p.page) for p in results.layout.placed if p.function == function)


def _replicas_of(results: StageResults, inputs: StageInputs, key: tuple[str, ...]):
    """The surviving replicas of the terminal function keyed `key`, one column each.

    A replica is a column of its own, or a replica cell attached in another group's column
    (R7 B8: the terminal stands at the head of the column that a wire from it feeds).
    """
    function = _function(inputs, key)
    return [
        c
        for c in results.columns
        if any(cell.function == function and cell.home is Home.ELSEWHERE for cell in c.cells)
    ]


def test_every_drawn_function_is_placed_and_no_route_or_coherence_error_remains() -> None:
    """The cabinet lays out whole: nothing is unplaced, no route fails, coherence is clean."""
    inputs, results, findings = _run()
    placed = {one.function for one in results.layout.placed}
    assert {spec.function for spec in inputs.functions} <= placed
    codes = {finding.code for finding in findings}
    assert not codes & _COHERENCE
    assert "ROUTE_FAILED" not in codes


def test_findings_of_every_stage_are_returned_sorted() -> None:
    """A very narrow sheet trips several stages at once: each finding is kept, one sorted order.

    Decision layout-0038 (open-questions.md 13.18) closed the route/coherence gap this fixture
    used to
    show, so this sheet gives no `ROUTE_FAILED` or `CONNECTION_NOT_DRAWN` (`route` and
    `check_coherence` have their own can-fail tests elsewhere).

    D13/D4 (deep dive): every text reserves its measured width only, so the cabinet packs far
    narrower than the prototype's fixed slots did. `WIRE_OVER_LABEL` and `LABEL_UNPLACED` no
    longer arise at any width of this fixture. 40 mm (content 128 G) is narrower than one
    130 G keep-out and than the 74 G box of a coil's contact image (D7): the page
    split (`GROUP_SPLIT`) and the label leaving the content box (`OUT_OF_CONTENT_BOX`) both
    show, next to the resolve and columns findings the fixture always gives.
    """
    _, _, findings = _run(40)
    codes = {finding.code for finding in findings}
    assert {
        "SYMBOL_DEFAULTED",  # resolve
        "FUNCTION_UNPLACED_IN_COLUMN",  # columns
        "GROUP_SPLIT",  # partition
        "OUT_OF_CONTENT_BOX",  # lint_geometry
    } <= codes
    assert "ROUTE_FAILED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes
    assert list(findings) == sorted(findings, key=lambda f: (f.code, f.subjects, f.message))


def test_the_run_does_not_depend_on_authoring_order() -> None:
    """The same design authored in two orders gives equal results and equal findings."""
    _, forward, forward_findings = _run()
    _, backward, backward_findings = _run(reverse=True)
    assert forward == backward
    assert forward_findings == backward_findings


def test_a_terminal_wired_from_two_groups_is_placed_once_on_each_page() -> None:
    """X2:1 is at home in `=SUP` and replicated for `=P1`: two pages, one placement on each."""
    inputs, results, _ = _run()
    pages = _pages_of(results, _function(inputs, _X2))
    assert pages == [(1, 1), (1, 2)]


def test_a_replica_is_dropped_when_its_page_already_holds_the_terminal() -> None:
    """`=P1` and `=P2` share a page: the replica for `=P2` is dropped, the one for `=P1` stays."""
    inputs, results, _ = _run()
    assert len(_replicas_of(results, inputs, _X2)) == 1


def test_a_replica_is_kept_on_a_page_that_does_not_hold_the_terminal() -> None:
    """On a narrow sheet `=P1` and `=P2` have pages of their own: each keeps its replica.

    X2:1 is at home in `=SUP` (page 3) and wired from `=P1` (page 1) and `=P2` (page 2): it
    stands once on each of the three pages, a replica on each of the first two (D4: groups
    pack onto pages by their measured widths, so 250 mm still gives each pump its own page).
    """
    inputs, results, _ = _run(250)
    assert len(_replicas_of(results, inputs, _X2)) == 2
    assert _pages_of(results, _function(inputs, _X2)) == [(1, 1), (1, 2), (1, 3)]


def test_a_tag_echo_gets_a_cross_reference_label_on_both_pages() -> None:
    """The second `place_slot_labels` call: relay K8's coil and contact echo across two pages.

    D1 (deep dive): the `LATCH` net links K8's coil and contact, two poles, into one chain, so
    the cabinet as authored never cuts them. D2: a chain splits where the authored group
    changes, so with the coil hinted into `=P1` and the contact left in `=SUP` they stand on
    two pages, and the one net between them is cut as a tag echo (both ends are one item).
    D7: a coil's contact image and each contact's coil reference are cross references too, so
    the tag echo's two are the ones on the `tag` slot of the item's two functions.
    """
    inputs, results, _ = _run(k8_coil_in_p1=True)
    echoed = [d for d in results.layout.decisions if d.case is LinkCase.TAG_ECHO]
    assert len(echoed) == 1
    ends = {echoed[0].a, echoed[0].b}
    owner = {p.port: d.function for d in results.drawn for p in d.ports}
    coil, contact = (_function(inputs, ("cabinet", "k8", "fn", name)) for name in ("coil", "no_1"))
    assert {owner[end] for end in ends} == {coil, contact}
    pages = {(p.drawing_set, p.page) for p in results.layout.placed}
    references = [
        x
        for x in results.layout.labels
        if x.kind is LabelKind.CROSS_REFERENCE and x.slot == "tag" and x.subject in {coil, contact}
    ]
    assert {x.subject for x in references} == {coil, contact}
    assert len(references) == 2
    for label in references:
        assert (label.drawing_set, label.page) in _pages_of(results, label.subject)
    assert len({(label.drawing_set, label.page) for label in references}) == 2
    assert {(label.drawing_set, label.page) for label in references} <= pages
    for label in references:  # each names the page of the item's other function
        other = contact if label.subject == coil else coil
        assert {(x.drawing_set, x.page) for x in label.partners} == set(_pages_of(results, other))
    for label in references:
        others = [
            x.box
            for x in results.layout.labels
            if (x.drawing_set, x.page) == (label.drawing_set, label.page) and x != label
        ]
        assert not any(overlaps(label.box, box) for box in others)


@pytest.mark.parametrize("width_mm", [400, 300, 210, 200, 190, 180, 160, 150, 120, 100])
def test_no_conductor_is_lost_at_any_narrow_content_width(width_mm: int) -> None:
    """13.18/layout-0038: every width the WP14 sweep measured draws every conductor.

    Measured on main (a7757da), before this decision: 190, 180, 160 and 150 mm each gave
    `ROUTE_FAILED: 2` / `CONNECTION_NOT_DRAWN: 2`, and 100 mm gave `ROUTE_FAILED: 1` /
    `CONNECTION_NOT_DRAWN: 1` -- this test fails on main at five of its ten widths, measured
    with `claude-tools/sweep_13_18.py` against a worktree at that commit, not asserted.
    """
    _, _, findings = _run(width_mm)
    codes = {f.code for f in findings}
    assert "ROUTE_FAILED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes


_LINES_SEEN = (
    "layout-0158 F1: the harness-ink checks see the cabinet's W1 line through a symbol "
    "(WIRE_THROUGH_SYMBOL), still after F5; named for the designer"
)


@pytest.mark.xfail(strict=True, reason=_LINES_SEEN)
@pytest.mark.parametrize("width_mm", [250, 150])
def test_a_severed_signal_has_a_marker_pair_that_no_wire_runs_over(width_mm: int) -> None:
    """The K1 to K2 signal is cut; no wire ever runs over a MARKER box, at either width.

    The marker guarantee (decision layout-0038, open-questions.md 13.18) is asserted directly
    below with
    the same primitives `lint_geometry` uses. `Finding.subjects` is sorted on construction, so
    it cannot tell a marker crossing from a route's own endpoint identity by position -- the
    K1/K2 route's own `b` legitimately equals its own marker's port, so a subjects-membership
    check false-positives on it; that is why the check is not written that way.

    D13 (deep dive): the prototype's 150 mm sheet gave a wire on a marker's stub lane and,
    with it, one `LABEL_UNPLACED` and one `WIRE_OVER_LABEL`. Every text now reserves its
    measured width, and no wire runs through a marker box at either width (the lane loop
    below finds no hit at 60 to 410 mm), so neither label finding occurs. What can fail here
    is therefore the cut itself (links.md 6.6, the `links` stage): the K1 aux to K2 aux conductor
    is one `SEVERED` decision whose two ports each carry one marker, the owner's on the
    earlier page and the user's on the later one.
    """
    inputs, results, findings = _run(width_mm)
    layout = results.layout
    assert {marker.side.value for marker in layout.markers} == {"owner", "user"}
    assert "WIRE_THROUGH_SYMBOL" not in {f.code for f in findings}
    for one_route in layout.routes:
        here = (one_route.drawing_set, one_route.page)
        markers = tuple(m for m in layout.markers if (m.drawing_set, m.page) == here)
        runs = runs_of(one_route)
        for marker in markers:
            assert not any(crosses(marker.box, run) for run in runs)
    assert "WIRE_OVER_LABEL" not in {f.code for f in findings}
    # V8 (owner 2026-10-02): a schematic page prints no wire label, so no text goes unplaced
    assert "LABEL_UNPLACED" not in {f.code for f in findings}
    owner = {p.port: d.function for d in results.drawn for p in d.ports}
    aux = {_function(inputs, ("cabinet", name, "fn", "aux")) for name in ("k1", "k2")}
    (cut,) = (
        d
        for d in layout.decisions
        if d.case is LinkCase.SEVERED and {owner[d.a], owner[d.b]} == aux
    )
    # the loop above only sees routes that exist: a route dropped without a trace passes it, so
    # the run must hold routes, none may have failed or gone undrawn, and the cut conductor is
    # drawn as its marker pair alone (a severed conductor has no route, docs/design/links.md 6.6)
    assert layout.routes
    assert not {f.code for f in findings} & {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN"}
    assert not [
        f
        for f in findings
        if f.code in {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN"} and cut.connection in f.subjects
    ]
    assert cut.connection not in {r.connection for r in layout.routes}
    pair = [m for m in layout.markers if m.port in {cut.a, cut.b}]
    assert sorted(m.side.value for m in pair) == ["owner", "user"]
    (owner_marker,) = (m for m in pair if m.side.value == "owner")
    (user_marker,) = (m for m in pair if m.side.value == "user")
    assert owner_marker.port != user_marker.port
    assert (owner_marker.drawing_set, owner_marker.page) < (
        user_marker.drawing_set,
        user_marker.page,
    )


@pytest.mark.parametrize("width_mm", [400, 250, 150, 100])
def test_no_marker_box_covers_a_sibling_ports_lane(width_mm: int) -> None:
    """WIRE-X56, decision layout-0054: an N/S marker box never covers a sibling port's lane.

    The vertical lane straight out of every other port of the marker's own function, on the
    marker's own side, stays off the box's interior (the router grants a marker's box to its
    own port only). At 250 and 150 mm the K1 aux marker's box covered its sibling's lane. The
    test is the router's own, closed: a lane on the box's edge is covered too, which is what
    makes 400 and 100 mm fail without the shift as well; `checked` counts the lanes tested. On the
    wired cabinet: the lanes checked are the lamp `-H1`'s, whose branch marker HL1 drops with `W1`.

    UNDO: in `marker_lanes.clear_of_sibling_lanes` change `found[index] = replace(...)` to `pass`.
    """
    _, results, _ = _run(width_mm, wired=True)
    layout = results.layout
    owner = {p.port: d.function for d in results.drawn for p in d.ports}
    checked = 0
    for marker in layout.markers:
        box, at = marker.box, marker.at
        south = box.y >= at.y
        if marker.turn is not None or not (south or box.y + box.height <= at.y):
            continue
        if not box.x <= at.x <= box.x + box.width:
            continue
        for one in layout.placed:
            if one.function != owner[marker.port] or (one.drawing_set, one.page) != (
                marker.drawing_set,
                marker.page,
            ):
                continue
            for port in one.geometry.ports:
                x, y = one.at.x + port.at.x, one.at.y + port.at.y
                lane = x != at.x and port.facing is (Facing.S if south else Facing.N)
                if lane and (y < box.y + box.height if south else y > box.y):
                    checked += 1
                    assert not box.x <= x <= box.x + box.width
    assert checked


@pytest.mark.parametrize("width_mm", [250, 150])
def test_each_page_routes_against_its_own_boxes_only(width_mm: int) -> None:
    """Routing one page again with that page's boxes gives the same result.

    D9 (deep dive): a net of 3 or more ports is drawn as markers, and a severed conductor is a
    marker pair, so neither is routed, and (HL1) a core of a line (the cable `W1`) is drawn as
    its line: the page's conductors are the ones the layout drew on it. The positive half is that
    every conductor drawn on no page is one of those three, and `W1`'s cores are a drawn line's.
    """
    inputs, results, _ = _run(width_mm)
    layout = results.layout
    routed = {one_route.connection for one_route in layout.routes}
    cut = {d.connection for d in layout.decisions if d.case is LinkCase.SEVERED}
    star_ports = {m.port for m in layout.markers if m.star}
    line_of = {
        core: line.owner
        for line in line_reads(freeze(build_cabinet())).lines
        for core in line.conductors
    }
    drawn_lines = {one.harness for one in results.lines.lines}
    unrouted = [c for c in inputs.connections if c.handle not in routed]
    assert unrouted
    assert {c.handle for c in unrouted} & line_of.keys()
    for c in unrouted:
        in_line = line_of.get(c.handle) in drawn_lines
        assert c.handle in cut or {c.a.port, c.b.port} & star_ports or in_line
    for plan in layout.pages:
        here = (plan.drawing_set, plan.number)
        placed = tuple(p for p in layout.placed if (p.drawing_set, p.page) == here)
        labels = [x for x in layout.labels if (x.drawing_set, x.page) == here]
        markers = [m for m in layout.markers if (m.drawing_set, m.page) == here]
        slot_boxes = tuple(x.box for x in labels)
        reserved = slot_boxes
        on_page = {r.connection for r in layout.routes if (r.drawing_set, r.page) == here}
        drawn_here = tuple(c for c in inputs.connections if c.handle in on_page)
        routes, _ = route(
            drawn_here,
            inputs.net_groups,
            placed,
            results.drawn,
            reserved=reserved,
            markers=tuple(markers),
            profile=inputs.profile,
            sheet=inputs.sheet,
        )
        assert routes == tuple(r for r in layout.routes if (r.drawing_set, r.page) == here)


def test_the_second_reserve_call_avoids_the_labels_of_the_first() -> None:
    """A first-call label on the cross-reference's preferred place pushes it to another one."""
    inputs = PageInputs(
        functions=(),
        connections=(),
        net_groups=(),
        groups=(),
        locations=(),
        units=(),
        hints=NO_HINTS,
        profile=PROFILE,
        sheet=SHEET,
        top_headroom_lanes=0,
        bottom_headroom_lanes=0,
    )
    function = placed(1, x=104, y=96)
    # the tag slot's box is (120, 92); the cross-reference prefers one text height below it
    first = PlacedLabel(
        kind=LabelKind.MARKING,
        subject=hid("port", 11),
        slot="marking.in",
        drawing_set=1,
        page=1,
        box=Box(x=120, y=100, width=32, height=8),
    )
    request = LabelRequest(
        kind=LabelKind.CROSS_REFERENCE, subject=hid("function", 1), slot="tag", text="/2.5"
    )
    _, labels, _ = finish_page(
        PageState((function,), (first,), ()), (drawn(1),), inputs, references=(request,)
    )
    (cross,) = (x for x in labels if x.kind is LabelKind.CROSS_REFERENCE)
    assert not overlaps(cross.box, first.box)


def test_the_location_labels_reach_links() -> None:
    """Two located drawing sets: a marker across them needs no unlocated-partner warning."""
    _, results, findings = _run(second_location=True)
    assert {plan.drawing_set for plan in results.layout.pages} == {1, 2}
    sets = {marker.drawing_set for marker in results.layout.markers}
    assert sets == {1, 2}
    assert LINK_PARTNER_UNLOCATED not in {finding.code for finding in findings}


def test_the_terminal_sort_keys_tolerate_an_unnumbered_item() -> None:
    """R5: an item with no designation (before the numbering pass) sorts as an empty one."""
    unnumbered = Draft()
    for original in build_cabinet().records():
        record = original
        if isinstance(record, Item) and record.tag == "K8":
            record = dataclasses.replace(record, tag=None)
        unnumbered.add(record, origin=_ORIGIN)
    model = freeze(unnumbered)
    specs = reading.drawn_functions(model, build_indexes(model))
    keys = reading.terminal_sort_keys(model, specs)
    (k8,) = (spec.function for spec in specs if spec.key == ("cabinet", "k8", "fn", "coil"))
    assert keys[k8] == (1, natural_key(""), "", 0)
