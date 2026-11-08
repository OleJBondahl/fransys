"""`write_layout` (el-0003): the pages, drawn symbols and drawn wires of a solved core layout.

The planted model solves once for the module; it holds a generic box (a sized box with movable
pins) and two pages, so every record family and the box's `lengths` and `offsets` are present.
"""
# NET_POTENTIAL_CONFLICT 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# NET_SHORTED 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

import pytest
from conventions_fixtures import house
from fransys_el import ProblemError, build, lay_out_drawn
from fransys_el.codes import FINDING_CODES
from fransys_el.draw_layout import _wires as drawn_wires
from fransys_el.draw_write import write_layout_drawn
from fransys_el.drawn_identity import net_text
from fransys_el.placement_ids import net_key, symbol_key
from fransys_el.placement_nets import net_ports
from fransys_el.placement_options import options
from fransys_el.write import write_layout
from fransys_el.write_findings import kernel_findings
from fransys_el.write_ids import symbol_subjects
from fransys_el.write_pages import write_pages
from placement_fixtures import kit_for, planted_model

from electrical_symbols import LIBRARY
from fransys_layout.core import Finding, PinRef, Size, Wire, solve
from fransys_model.derive import drawn_designations, net_of, pdf_page, unit_label
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
    from fransys_layout.core.values import FindingCode
    from fransys_model.kernel import Model


class Written:
    """The planted model, its kit, its solved layout, and what `write_layout` made of them."""

    def __init__(self) -> None:
        self.model: Model = planted_model()
        self.kit = kit_for(self.model)
        conventions = house()
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


def _symbols(written: Written) -> list[DrawnSymbol]:
    """Every symbol of every page Drawing."""
    return [s for d in written.drawn.values() for s in d.symbols]


def _bodies(written: Written) -> list[DrawnSymbol]:
    """The drawn symbols that stand for a placed function: no junction dot."""
    at = {(p.x, p.y) for pg in written.layout.placement.pages for p in pg.placed}
    return [s for s in _symbols(written) if s.key != "contact-head" and (s.x, s.y) in at]


def _placed(written: Written) -> dict[tuple[int, int], Any]:
    return {(p.x, p.y): p for pg in written.layout.placement.pages for p in pg.placed}


def test_one_drawing_per_page_and_one_symbol_per_placed_function(written: Written) -> None:
    layout, out = written.layout, written.out
    assert len(layout.pages) == 2
    assert len(layout_of(out, Page)) == len(written.drawn) == len(layout.pages)
    assert len(layout_of(out, DrawingSet)) == 1
    assert len(_bodies(written)) == sum(len(p.placed) for p in layout.placement.pages)
    wires = sum(len(d.wires) for d in written.drawn.values())
    assert wires == sum(len(p.wires) for p in layout.routes.pages)


def test_a_symbol_takes_the_key_of_its_pick_and_its_position(written: Written) -> None:
    keys = {symbol_key(written.model, f): pick.key for f, pick in written.kit.items()}
    poles = {symbol_key(written.model, f): pick.poles for f, pick in written.kit.items()}
    placed = {p.sym: p for pg in written.layout.placement.pages for p in pg.placed}
    drawn = sorted((s.key, s.poles, s.x, s.y, s.orient) for s in _bodies(written))
    expected = sorted((keys[sym], poles[sym], p.x, p.y, p.orient.name if hasattr(p.orient, "name") else p.orient) for sym, p in placed.items())
    assert drawn == expected


def test_a_box_carries_its_pin_offsets_and_its_port_rows(written: Written) -> None:
    boxes = [s for s in _bodies(written) if s.key == "generic-box"]
    assert len(boxes) == 1
    box = _placed(written)[boxes[0].x, boxes[0].y]
    assert dict(boxes[0].offsets) == {p.pin: p.x - box.x for p in box.pin_xy}
    assert sorted(row[0] for row in boxes[0].texts) == sorted(dict(boxes[0].offsets))
    assert all(len(row) == 1 for row in boxes[0].texts)


def test_a_symbol_that_is_not_a_box_carries_no_texts_or_offsets(written: Written) -> None:
    plain = [s for s in _bodies(written) if s.key != "generic-box"]
    assert plain
    assert all(not s.texts and not s.offsets for s in plain)


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
    net = next(iter(net_ports(written.model)))
    found = kernel_findings(
        written.model,
        [Finding("WIRE_THROUGH_BODY", "no path", 1, net), Finding("NO_CELL", "nowhere")],
        {},
        {},
    )
    assert [(f.code, f.message) for f in found] == [
        ("WIRE_THROUGH_BODY", "no path"),
        ("NO_CELL", "nowhere"),
    ]
    assert [f.severity for f in found] == [Severity.ERROR, Severity.WARNING]
    assert [s.kind for s in found[0].subjects] == ["port"]
    assert found[1].subjects == ()
    assert all(f.fix for f in found)


def test_a_subject_that_is_no_record_names_no_subject(written: Written) -> None:
    (found,) = kernel_findings(written.model, [Finding("NO_BLOCK", "no block", None, "col:9")], {}, {})
    assert found.subjects == ()


def test_an_unmapped_token_beside_a_mapped_one_stays_in_the_message(written: Written) -> None:
    net = next(iter(net_ports(written.model)))
    (found,) = kernel_findings(written.model, [Finding("NO_BLOCK", "no block", None, f"{net},col:9")], {}, {})
    assert [s.kind for s in found.subjects] == ["port"]
    assert found.message == "no block (subject not a model record: col:9)"


@pytest.mark.rule("NO-SILENT-DROP")
def test_a_core_symbol_id_maps_to_its_record(written: Written) -> None:
    """A core symbol id maps to the function it draws, so a fix naming `<subject>` gets one.

    Open gap: CARD_OVERFULL and NO_BLOCK pass a box (blocks_card.py:125, blocks_check.py:24), and
    WIRE_MEETS_NET can pass ids outside the map. Covered by SPEC-022 (finding subject
    """
    from typing import get_args

    from fransys_layout import FINDING_CODES as LAYOUT_CODES
    from fransys_layout.core.values import FindingCode

    emitted = set(get_args(FindingCode))
    wants = sorted(info.code for info in (*LAYOUT_CODES, *FINDING_CODES) if info.code in emitted and "<subject>" in info.fix)
    assert {"ANNEX_UNPLACED", "LANE_WIRE_DROPPED", "WIRE_MEETS_NET"} <= set(wants)
    symbols = symbol_subjects(written.model, written.kit)
    sym = next(iter(symbols))
    net = next(iter(net_ports(written.model)))
    for code in wants:
        subject = net if code == "WIRE_MEETS_NET" else sym
        core = Finding(cast("FindingCode", code), "text", None, subject)
        (found,) = kernel_findings(written.model, [core], symbols, {})
        assert [s.kind for s in found.subjects] in (["function"], ["port"]), code


def test_a_page_overflow_names_the_set_the_page_and_the_designations_of_its_row(written: Written) -> None:
    short = solve(replace(written.problem, area=Size(written.problem.area.w, 80)), options(house(), LIBRARY))
    found = kernel_findings(written.model, short.findings, symbol_subjects(written.model, written.kit), {})
    (first, *_) = (f for f in found if f.code == "PAGE_OVERFLOW")
    assert first.message.startswith("page 1, row 0 (devices -B1, ")
    assert "set" not in first.message.partition("(devices")[0]
    assert "function:" not in first.message
    devices = first.message.partition("(devices ")[2].partition(")")[0].split(", ")
    assert devices == list(dict.fromkeys(devices))
    assert "enlarge the page" in first.message


def test_a_page_drawing_carries_the_measured_rows_of_its_layout(written: Written) -> None:
    rows = [r for d in written.drawn.values() for r in d.rows]
    assert [(r.height_g, r.width_g, r.term) for r in rows] == [(m.height, m.width, m.term) for m in written.layout.rows]
    assert rows
    assert all(r.devices and all(drawn_designations(written.model, r.devices)) for r in rows)
    assert all(len(set(r.devices)) == len(r.devices) for r in rows)


def test_a_row_finding_prints_the_page_number_its_pdf_prints(written: Written) -> None:
    """A set drawn after another set's page prints its core page 1 as a later PDF page."""
    short = solve(replace(written.problem, area=Size(written.problem.area.w, 80)), options(house(), LIBRARY))
    laid, _ = write_layout(written.model, None, short, written.problem, written.kit, library=LIBRARY)
    earlier = DrawingSet(id=make_id(DrawingSet, ("e",)), key=("e",), location=None, number=0, produced_by="t")
    cover = Page(
        id=make_id(Page, ("e", "1")),
        key=("e", "1"),
        drawing_set=earlier.id,
        number=1,
        role=PageRole.POWER,
        sheet_format=None,
        groups=(),
        produced_by="t",
    )
    model = evolve(laid, put=(earlier, cover), origin=Origin(file="t", line=0, note="t"))
    page = min(layout_of(laid, Page).values(), key=lambda p: p.number)
    core_number = page.number
    assert pdf_page(model, page) != core_number
    found = kernel_findings(model, short.findings, symbol_subjects(written.model, written.kit), {core_number: page})
    first = next(f for f in found if f.code == "PAGE_OVERFLOW")
    assert first.message.startswith(f"page {pdf_page(model, page)}, row 0 (devices ")


def test_a_code_the_registry_does_not_hold_is_refused(written: Written) -> None:
    with pytest.raises(ProblemError, match="LANE_TURNED"):
        kernel_findings(written.model, [Finding("LANE_TURNED", "turned")], {}, {})


def test_a_bundle_is_a_trunk_and_a_single_wire_is_a_wire(written: Written) -> None:
    page = next(iter(layout_of(written.out, Page).values()))
    wires = (
        Wire("n1", page.number, ((0, 0), (8, 0)), "routed"),
        Wire("n1", page.number, ((0, 8), (8, 8)), "trunk", lane=2),
    )
    drawn = [w for _, w in drawn_wires(wires, written.model, {page.number: page}, 1)]
    assert [(w.style, w.lanes) for w in drawn] == [("wire", 1), ("trunk", 1)]
    assert drawn[0].id != drawn[1].id


def test_a_wire_takes_the_declared_net_of_the_port_its_net_is_named_for(written: Written) -> None:
    """A drawn wire's `net` is the `net_key` of the net its lead port is on."""
    model = written.model
    lead_of = net_ports(model)
    wires = [w for d in written.drawn.values() for w in d.wires]
    assert wires
    for w in wires:
        net = net_of(model, lead_of[w.net])
        assert net is not None
        assert w.net == net_key(model, net.ports)


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
    wire = Wire(net_text(model, port), page.number, ((0, 0), (8, 0)), "routed")
    with pytest.raises(ProblemError, match="is on 2 nets"):
        drawn_wires((wire,), model, {page.number: page}, 1)


def test_wire_styles_exist(written: Written) -> None:
    page = next(iter(layout_of(written.out, Page).values()))
    wires = (
        Wire("n", page.number, ((0, 0), (8, 0)), "routed"),
        Wire("n", page.number, ((0, 8), (8, 8)), "trunk", lane=0),
    )
    styles = {w.style for _, w in drawn_wires(wires, written.model, {page.number: page}, 1)}
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
    _, pages = write_pages(written.model, (plan,), None, {})
    assert pages[plan.page].role is PageRole.CONTROL


def test_the_same_net_in_two_drawing_sets_makes_distinct_wires(written: Written) -> None:
    page = next(iter(layout_of(written.out, Page).values()))
    wires = (Wire("n1", page.number, ((0, 0), (8, 0)), "routed"),)
    first = drawn_wires(wires, written.model, {page.number: page}, 1)
    second = drawn_wires(wires, written.model, {page.number: page}, 2)
    assert first[0][1] != second[0][1]


def test_a_kit_with_no_function_for_the_symbols_is_refused(written: Written) -> None:
    with pytest.raises(ProblemError, match="the kit: has no function"):
        lay_out_drawn(written.model, frozendict(), written.problem, house(), LIBRARY)


def test_a_call_without_the_symbol_map_is_a_type_error(written: Written) -> None:
    with pytest.raises(TypeError, match="symbols"):
        cast("Any", kernel_findings)(written.model, [Finding("NO_CELL", "nowhere")])


def test_a_fill_under_min_text_names_the_unit_label_not_its_id(written: Written) -> None:
    unit = next(iter(written.model.tables["unit"]))
    core = Finding("FILL_UNDER_MIN", f"unit {unit.value}, block b: page filled 5%", 2, "b")
    (found,) = kernel_findings(written.model, [core], {}, {})
    assert unit.value not in found.message
    assert found.message.startswith(f"unit {unit_label(written.model, unit)}, block b")


def test_the_drawn_net_text_is_the_net_key_of_its_port_not_the_first_port_value(written: Written) -> None:
    """R1615: `net_text` spells a port's net as `Net.id` does (`net_key`), so power leads and markers name the core's net."""
    model = written.model
    for port in list(ports(model))[:20]:
        net = net_of(model, port)
        assert net is not None
        assert net_text(model, port) == net_key(model, net.ports) != net.ports[0].value
