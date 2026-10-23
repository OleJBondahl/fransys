"""`write_layout` (el-0003): the pages, drawn symbols and drawn wires of a solved core layout.

The planted model solves once for the module; it holds a generic box (a sized box with movable
pins) and two pages, so every record family and the box's `lengths` and `offsets` are present.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest
from conventions_fixtures import house, tables_on
from fransys_el import ProblemError, build, lay_out, options, write_layout
from fransys_el.draw_layout import _wires as drawn_wires
from fransys_el.draw_write import write_layout_drawn
from fransys_el.placement_ids import symbol_key
from fransys_el.placement_tables import is_table_spot
from fransys_el.write_findings import kernel_findings
from fransys_el.write_pages import write_pages
from placement_fixtures import kit_for, planted_model

from electrical_symbols import LIBRARY
from fransys_layout.core import Finding, PinRef, Wire, solve
from fransys_model.derive import net_of
from fransys_model.kernel import Origin, Severity, evolve, make_id
from fransys_model.layout import (
    DrawingSet,
    Page,
    PageRole,
    layout_of,
)
from fransys_model.vocab import Net, NetClass, ports
lazy from fransys_layout.drawing import DrawnSymbol

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout, PlacementProblem
    from fransys_model.kernel import Model


class Written:
    """The planted model, its kit, its solved layout, and what `write_layout` made of them."""

    def __init__(self, *, tables: bool = True) -> None:
        self.model: Model = planted_model()
        self.kit = kit_for(self.model)
        conventions = tables_on() if tables else house()
        self.problem: PlacementProblem
        self.problem, _ = build(self.model, self.kit, conventions, LIBRARY)
        self.layout: CoreLayout = solve(self.problem, options(conventions, LIBRARY))
        self.out, self.findings, self.drawn, _ = write_layout_drawn(
            self.model,
            None,
            self.layout,
            self.problem,
            self.kit,
            library=LIBRARY,
        )


@pytest.fixture(scope="module")
def written() -> Written:
    return Written()


def test_the_default_builds_no_table_annex_and_draws_no_head() -> None:
    """CONTACT-TABLE: `contact_tables` is off by default; on, a table annex is built per coil."""
    off, on = Written(tables=False), Written()

    def spots(w: Written) -> set[str]:
        return {a.spot for a in w.layout.annotations.annexes if is_table_spot(a.spot)}

    assert not _tables(off)
    assert not spots(off)
    assert _tables(on)
    assert spots(on)


def _symbols(written: Written) -> list[DrawnSymbol]:
    """Every symbol of every page Drawing."""
    return [s for d in written.drawn.values() for s in d.symbols]


def _bodies(written: Written) -> list[DrawnSymbol]:
    """The drawn symbols that stand for a placed function: no contact table, no junction dot."""
    at = {(p.x, p.y) for pg in written.layout.placement.pages for p in pg.placed}
    return [s for s in _symbols(written) if s.key != "contact-head" and (s.x, s.y) in at]


def _tables(written: Written) -> list[DrawnSymbol]:
    """The drawn contact tables."""
    return [s for s in _symbols(written) if s.key == "contact-head"]


def _placed(written: Written) -> dict[tuple[int, int], Any]:
    return {(p.x, p.y): p for pg in written.layout.placement.pages for p in pg.placed}


def test_one_drawing_per_page_and_one_symbol_per_placed_function(written: Written) -> None:
    layout, out = written.layout, written.out
    assert len(layout.pages) == 2
    assert len(layout_of(out, Page)) == len(written.drawn) == len(layout.pages)
    assert len(layout_of(out, DrawingSet)) == 1
    assert len(_bodies(written)) == sum(len(p.placed) for p in layout.placement.pages)
    assert _tables(written)  # a relay coil with contacts draws its table head
    wires = sum(len(d.wires) for d in written.drawn.values())
    assert wires == sum(len(p.wires) for p in layout.routes.pages)


def test_a_symbol_takes_the_key_of_its_pick_and_its_position(written: Written) -> None:
    keys = {symbol_key(written.model, f): pick.key for f, pick in written.kit.items()}
    poles = {symbol_key(written.model, f): pick.poles for f, pick in written.kit.items()}
    placed = {p.sym: p for pg in written.layout.placement.pages for p in pg.placed}
    drawn = sorted((s.key, s.poles, s.x, s.y, s.orient) for s in _bodies(written))
    expected = sorted(
        (keys[sym], poles[sym], p.x, p.y, p.orient.name if hasattr(p.orient, "name") else p.orient)
        for sym, p in placed.items()
    )
    assert drawn == expected


def test_a_box_carries_its_pin_offsets_and_its_port_rows(written: Written) -> None:
    boxes = [s for s in _bodies(written) if s.key == "generic-box"]
    assert len(boxes) == 1
    box = _placed(written)[boxes[0].x, boxes[0].y]
    assert dict(boxes[0].offsets) == {p.pin: p.x - box.x for p in box.pin_xy}
    assert sorted(row[0] for row in boxes[0].texts) == sorted(dict(boxes[0].offsets))
    assert all(len(row) == 1 for row in boxes[0].texts)


def test_a_symbol_that_is_not_a_box_carries_no_texts_but_its_tables_do(written: Written) -> None:
    plain = [s for s in _bodies(written) if s.key != "generic-box"]
    assert plain
    assert all(not s.texts for s in plain)
    tables = _tables(written)
    assert tables
    assert all(t.texts[0] == ("NO", "NC") and len(t.texts) > 1 for t in tables)
    assert all(dict(t.slots)["1.no"] or dict(t.slots)["1.nc"] for t in tables)


def test_a_symbol_that_is_not_a_box_carries_no_offsets(written: Written) -> None:
    others = [s for s in _bodies(written) if s.key != "generic-box"]
    assert others
    assert all(not s.offsets for s in others)


def test_leads_are_the_wired_pins_and_an_unwired_pin_has_none(written: Written) -> None:
    wired = dict(written.layout.wired)
    syms = {s.id: s for s in written.problem.symbols}
    placed = _placed(written)
    drawn = _bodies(written)
    for s in drawn:
        sym = placed[s.x, s.y].sym
        pins = [p.id for p in syms[sym].pins]
        assert list(s.leads) == [p for p in pins if PinRef(sym, p) in wired]
    assert any(s.leads for s in drawn)
    assert any(len(s.leads) < len(syms[placed[s.x, s.y].sym].pins) for s in drawn)


def test_a_page_keeps_its_number_and_its_groups_in_order(written: Written) -> None:
    by_number = {p.number: p for p in layout_of(written.out, Page).values()}
    pages = [by_number[plan.page] for plan in written.layout.pages]
    assert len(by_number) == len(written.layout.pages)
    assert [len(p.groups) for p in pages] == [len(plan.groups) for plan in written.layout.pages]
    assert all([g.index for g in p.groups] == list(range(len(p.groups))) for p in pages)


def test_a_symbol_whose_function_is_not_in_the_kit_is_refused(written: Written) -> None:
    some = next(iter(written.kit))
    short = type(written.kit)({f: p for f, p in written.kit.items() if f != some})
    with pytest.raises(ProblemError, match=r"pass the (build's )?kit"):
        write_layout_drawn(
            written.model,
            None,
            written.layout,
            written.problem,
            short,
            library=LIBRARY,
        )


def test_writing_twice_gives_one_model(written: Written) -> None:
    again, _ = write_layout(
        written.model,
        None,
        written.layout,
        written.problem,
        written.kit,
        library=LIBRARY,
    )
    assert again == written.out


def test_a_core_finding_keeps_its_code_text_and_the_registry_severity(written: Written) -> None:
    net = next(iter(written.model.tables["port"])).value
    found = kernel_findings(
        written.model, [Finding("ROUTE_FAILED", "no path", 1, net), Finding("NO_CELL", "nowhere")]
    )
    assert [(f.code, f.message) for f in found] == [
        ("ROUTE_FAILED", "no path"),
        ("NO_CELL", "nowhere"),
    ]
    assert [f.severity for f in found] == [Severity.ERROR, Severity.WARNING]
    assert [s.kind for s in found[0].subjects] == ["port"]
    assert found[1].subjects == ()
    assert all(f.fix for f in found)


def test_a_subject_that_is_no_record_names_no_subject(written: Written) -> None:
    (found,) = kernel_findings(written.model, [Finding("NO_BLOCK", "no block", None, "col:9")])
    assert found.subjects == ()


def test_an_unmapped_token_beside_a_mapped_one_stays_in_the_message(written: Written) -> None:
    net = next(iter(written.model.tables["port"])).value
    (found,) = kernel_findings(
        written.model, [Finding("NO_BLOCK", "no block", None, f"{net},col:9")]
    )
    assert [s.kind for s in found.subjects] == ["port"]
    assert found.message == "no block (subject not a model record: col:9)"


def test_a_fully_mapped_subject_leaves_the_message_unchanged(written: Written) -> None:
    net = next(iter(written.model.tables["port"])).value
    (found,) = kernel_findings(written.model, [Finding("ROUTE_FAILED", "no path", 1, net)])
    assert found.message == "no path"
    assert len(found.subjects) == 1


def test_a_code_the_registry_does_not_hold_is_refused(written: Written) -> None:
    with pytest.raises(ProblemError, match="LANE_TURNED"):
        kernel_findings(written.model, [Finding("LANE_TURNED", "turned")])


def test_a_bundle_is_a_trunk_and_a_single_wire_is_a_wire(written: Written) -> None:
    page = next(iter(layout_of(written.out, Page).values()))
    wires = (
        Wire("n1", page.number, ((0, 0), (8, 0)), "routed"),
        Wire("n1", page.number, ((0, 8), (8, 8)), "trunk", lane=2),
    )
    drawn = [w for _, _, w in drawn_wires(wires, written.model, {page.number: page}, 1)]
    assert [(w.style, w.lanes) for w in drawn] == [("wire", 1), ("trunk", 1)]
    assert drawn[0].id != drawn[1].id


def test_a_wire_takes_the_declared_net_of_the_port_its_net_is_named_for(written: Written) -> None:
    """A drawn wire's `net` is the value of the first port of the net its port is on."""
    model = written.model
    port_of = {port.value: port for port in ports(model)}
    wires = [w for d in written.drawn.values() for w in d.wires]
    assert wires
    for w in wires:
        net = net_of(model, port_of[w.net])
        assert net is not None
        assert w.net == net.ports[0].value


def test_a_port_on_two_nets_is_refused(written: Written) -> None:
    port = next(iter(ports(written.model)))
    nets = tuple(
        Net(
            id=make_id(Net, (name,)),
            key=(name,),
            name=None,
            net_class=NetClass.SIGNAL,
            ports=(port,),
        )
        for name in ("one", "two")
    )
    model = evolve(written.model, put=nets, origin=Origin(file="t", line=0, note="t"))
    page = next(iter(layout_of(written.out, Page).values()))
    wire = Wire(port.value, page.number, ((0, 0), (8, 0)), "routed")
    with pytest.raises(ProblemError, match="is on 2 nets"):
        drawn_wires((wire,), model, {page.number: page}, 1)


def test_wire_styles_exist(written: Written) -> None:
    page = next(iter(layout_of(written.out, Page).values()))
    wires = (
        Wire("n", page.number, ((0, 0), (8, 0)), "routed"),
        Wire("n", page.number, ((0, 8), (8, 8)), "trunk", lane=0),
    )
    styles = {w.style for _, _, w in drawn_wires(wires, written.model, {page.number: page}, 1)}
    assert styles == {"trunk", "wire"}
    assert styles <= {w.id for w in LIBRARY.wires}


def test_a_page_whose_first_group_holds_a_power_net_is_a_power_page(written: Written) -> None:
    every_port = tuple(ports(written.model))
    net = Net(
        id=make_id(Net, ("all",)),
        key=("all",),
        name=None,
        net_class=NetClass.POWER,
        ports=every_port,
    )
    model = evolve(written.model, put=(net,), origin=Origin(file="t", line=0, note="t"))
    out, _ = write_layout(
        model,
        None,
        written.layout,
        written.problem,
        written.kit,
        library=LIBRARY,
    )
    grouped = [p for p in layout_of(out, Page).values() if p.groups]
    assert grouped
    assert {p.role for p in grouped} == {PageRole.POWER}
    before = {p.role for p in layout_of(written.out, Page).values() if p.groups}
    assert before != {PageRole.POWER}


def test_a_page_with_no_group_is_a_control_page(written: Written) -> None:
    plan = replace(written.layout.pages[0], groups=())
    _, pages = write_pages(written.model, (plan,), None, {}, "stamp")
    assert pages[plan.page].role is PageRole.CONTROL


def test_the_same_net_in_two_drawing_sets_makes_distinct_wires(written: Written) -> None:
    page = next(iter(layout_of(written.out, Page).values()))
    wires = (Wire("n1", page.number, ((0, 0), (8, 0)), "routed"),)
    first = drawn_wires(wires, written.model, {page.number: page}, 1)
    second = drawn_wires(wires, written.model, {page.number: page}, 2)
    assert first[0][1] != second[0][1]


def test_a_kit_with_no_function_for_the_symbols_is_refused(written: Written) -> None:
    with pytest.raises(ProblemError, match="the kit: has no function"):
        lay_out(written.model, frozendict(), written.problem, house(), LIBRARY)
