"""A connection is drawn on exactly one page, though both its ends may be on several (layout-0030).

The model is local: groups `=P1` and `=P2` on a sheet narrow enough to give each its own page
(D4: groups pack by measured width, and several may share a page, so 210 mm still splits these
two). Terminals `-X1:1` (home `=P1`), `-X1:2`, `-X1:3` and `-X1:5` (home `=P2`) each head a
chain of their own (a terminal-only column has no group of its own, so a wire from it to a
lamp of a group asks for a replica in that group's page: `replicate_terminals`). Each terminal's
internal port is wired to one lamp of the other group, and only the external ports are wired to
each other, so both wires under test are plain 2-port nets, not D9 fan-out nets, and the chains
stay one element long. Both ends of each wire are then on both pages:
`-X1:1` to `-X1:5` has one home end on each page (a tie), `-X1:2` to `-X1:3` has two on page 2.

The terminal symbol is authored with `external` at N and `internal` at S, so no wire has to
loop around a symbol (a terminal heading a chain with `internal` at N gives `ROUTE_FAILED`, a
known source defect of the engine, not this test's business).
"""

from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING

from layout_cabinet import _Builder, _specs

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import Label, LinkMarker, Page, Route, layout_of
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import SheetFormat as ModelSheetFormat
from fransys_model.vocab import Conductor, FunctionKind, Net, NetClass

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Port

_ORIGIN = Origin(file="tests/engines/test_one_page_per_connection.py", line=1, note="one page")
_COHERENCE = {
    "CONNECTION_NOT_DRAWN",
    "CONNECTION_DRAWN_TWICE",
    "ROUTE_WRONG_PORT",
    "ROUTE_SHORTS_NETS",
    "MARKER_UNPAIRED",
}
_WIDTH_MM = 210
_NET = make_id(Net, ("t", "net"))
_TIE = make_id(Conductor, ("cabinet", "wire", "6"))  # -X1:1 to -X1:5
_HOMES = make_id(Conductor, ("cabinet", "wire", "5"))  # -X1:2 to -X1:3


def _sheet(width_mm: int) -> tuple[ModelSheetFormat, ModelProfile]:
    sheet = ModelSheetFormat(
        id=make_id(ModelSheetFormat, ("test", "sheet")),
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
    profile = ModelProfile(
        id=make_id(ModelProfile, ("test", "profile")),
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
    return sheet, profile


def build(*, net_group: bool = False, width_mm: int = _WIDTH_MM) -> Draft:
    """The two-group model; with `net_group` the -X1:1 to -X1:5 wire is a declared net instead."""
    b = _Builder(second_location=False)
    parts = {spec.key: b.part(spec) for spec in _specs()}
    strip = b.strip("X1")
    b.choice(FunctionKind.TERMINAL, "terminal", {"internal": "s", "external": "n"})
    t1 = b.terminal(parts["terminal"], strip, 1, "p1")
    t2 = b.terminal(parts["terminal"], strip, 2, "p2")
    t3 = b.terminal(parts["terminal"], strip, 3, "p2")
    t5 = b.terminal(parts["terminal"], strip, 5, "p2")
    lamp_a = b.stamp(parts["lamp"], ("t", "ha"), "HA", "p1")
    lamp_b = b.stamp(parts["lamp"], ("t", "hb"), "HB", "p1")
    lamp_c = b.stamp(parts["lamp"], ("t", "hc"), "HC", "p2")
    ext: dict[str, Id[Port]] = {
        name: t.port("terminal", "external")
        for name, t in (("t1", t1), ("t2", t2), ("t3", t3), ("t5", t5))
    }
    # a lamp of the other group is wired to each terminal's internal port, so each terminal is
    # shown on both pages (wires 1 to 4)
    b.wire(t2.port("terminal", "internal"), lamp_a.port("lamp", "1"))
    b.wire(t3.port("terminal", "internal"), lamp_a.port("lamp", "2"))
    b.wire(t5.port("terminal", "internal"), lamp_b.port("lamp", "1"))
    b.wire(t1.port("terminal", "internal"), lamp_c.port("lamp", "1"))
    for name, terminal in (("t1", t1), ("t2", t2), ("t3", t3), ("t5", t5)):
        b.chain(("t", name), (terminal, "terminal"))
    b.wire(ext["t2"], ext["t3"])  # wire 5: -X1:2 to -X1:3, both at home on page 2
    if net_group:
        b.add(
            Net(
                id=_NET,
                key=("t", "net"),
                name="LINK",
                net_class=NetClass.CONTROL,
                ports=(ext["t1"], ext["t5"]),
            )
        )
    else:
        b.wire(ext["t1"], ext["t5"])  # wire 6: -X1:1 (home page 1) to -X1:5 (home page 2)
    draft = Draft()
    draft.extend(b.records, origin=_ORIGIN)
    draft.extend(_sheet(width_mm), origin=_ORIGIN)
    return draft


@cache
def run(*, net_group: bool = False) -> tuple[Model, tuple[Finding, ...]]:
    """The model laid out."""
    return lay_out_schematic(freeze(build(net_group=net_group)))


def _pages_of(model: Model, *, conductor: Id[Conductor] | None = None, net: Id[Net] | None = None):
    """The page numbers of the routes of one conductor or net, in order."""
    pages = layout_of(model, Page)
    return sorted(
        pages[route.page].number
        for route in layout_of(model, Route).values()
        if (route.conductor, route.net) == (conductor, net)
    )


def test_a_model_whose_wires_have_two_common_pages_lays_out() -> None:
    """Both ends of a wire on two pages once ended in a `SchemaError` (two routes, one id)."""
    model, findings = run()
    assert len(layout_of(model, Page)) == 2
    assert not _COHERENCE & {finding.code for finding in findings}


def test_a_wire_is_routed_on_the_page_holding_most_of_its_home_ends() -> None:
    """-X1:2 and -X1:3 are at home on page 2 and replicas on page 1: page 2, not the earliest."""
    model, _ = run()
    assert _pages_of(model, conductor=_HOMES) == [2]


def test_a_tie_in_home_ends_takes_the_earliest_page() -> None:
    """-X1:1 is at home on page 1 and -X1:5 on page 2: one each, so page 1."""
    model, _ = run()
    assert _pages_of(model, conductor=_TIE) == [1]


def test_both_ends_of_each_wire_stand_on_both_pages() -> None:
    """The fixture's precondition: each end of both wires is placed on page 1 and on page 2.

    Without it the two tests above would hold for a wire with one common page. The replicas
    come from `replicate_terminals` (a wire from a terminal to a function of another group).
    """
    model = freeze(build())
    inputs = read_inputs(model)
    results, _ = stage_results(model, inputs)
    ends = {
        c.handle: (c.a.function, c.b.function)
        for c in inputs.connections
        if c.handle in {_HOMES, _TIE}
    }
    assert set(ends) == {_HOMES, _TIE}
    for functions in ends.values():
        for function in functions:
            pages = [
                (p.drawing_set, p.page) for p in results.layout.placed if p.function == function
            ]
            assert sorted(pages) == [(1, 1), (1, 2)]


def test_a_net_group_edge_with_two_common_pages_is_routed_once() -> None:
    """The same rule for the edge of a declared net between -X1:1 and -X1:5: a tie, page 1."""
    model, findings = run(net_group=True)
    assert _pages_of(model, net=_NET) == [1]
    assert not _COHERENCE & {finding.code for finding in findings}


def test_a_wire_drawn_on_one_page_has_no_marker_and_no_wire_label() -> None:
    """Both ends are visible on the chosen page: nothing is cut, and no label is printed (V8)."""
    # S20 M12: a lamp-to-terminal wire of the fixture turns back round its device and is a
    # reference pair, so only the markers at the two wires under test are counted
    model, _ = run()
    ends = {
        ref.port
        for c in read_inputs(model).connections
        if c.handle in {_HOMES, _TIE}
        for ref in (c.a, c.b)
    }
    assert len(ends) == 4
    assert not [m for m in layout_of(model, LinkMarker).values() if m.port in ends]
    assert {r.conductor for r in layout_of(model, Route).values()} >= {_HOMES, _TIE}
    assert not [label for label in layout_of(model, Label).values() if label.conductor is not None]


def test_a_wire_with_a_common_page_is_not_cut_and_has_no_decision() -> None:
    """`links` decides only the cuts: a wire both of whose ends share a page is drawn, not cut."""
    model = freeze(build())
    results, _ = stage_results(model, read_inputs(model))
    handles = {decision.connection for decision in results.layout.decisions}
    assert not handles & {_HOMES, _TIE}
    # S20 M12: the fixture's lamp-to-terminal wires may turn back, so only these two are counted
    assert not [m for m in results.layout.markers if m.connection in {_HOMES, _TIE}]


def test_a_second_run_gives_the_same_layout_digest() -> None:
    """Choosing the page is a function of the model: a rerun on the result changes nothing."""
    for net_group in (False, True):
        once, _ = run(net_group=net_group)
        twice, _ = lay_out_schematic(once)
        assert twice.digests["layout"] == once.digests["layout"]
