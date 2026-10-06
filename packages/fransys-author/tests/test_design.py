"""Happy-path coverage of every public builder call (spec A1-A9)."""

import dataclasses
from decimal import Decimal

import pytest
from fransys_author import AuthorError, Cable, Design, Fn, Item, Location, Port, Strip, Terminal
from fransys_author.design import _required_and_defaults

from fransys_model.kernel import Draft, Record, Severity, freeze, merge
from fransys_model.layout import (
    BreakBefore,
    Chain,
    GroupHint,
    KeepTogether,
    OrderHint,
    SymbolChoice,
    default_profile,
)
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import SheetFormat as ModelSheetFormat
from fransys_model.vocab import (
    CableFacet,
    Conductor,
    CoreFacet,
    FunctionKind,
    Mate,
    Net,
    NetClass,
    Placement,
    PlcRequestFacet,
    PortRole,
    Project,
    ScalingFacet,
    SignalType,
    WireFacet,
)
from fransys_model.vocab import (
    Item as ModelItem,
)
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.tables import revisions, units
from fransys_model.vocab.validators.revisions import REVISION_CURRENT_MISSING, check_revisions


def _only[R: Record](draft: Draft, cls: type[R]) -> tuple[R, ...]:
    return tuple(r for r in draft.records() if isinstance(r, cls))


def _one[R: Record](draft: Draft, cls: type[R]) -> R:
    return _only(draft, cls)[0]


def test_required_and_defaults_splits_required_defaulted_and_excluded_fields():
    @dataclasses.dataclass
    class _Rec:
        keep_required: int
        keep_default: int = 5
        skip_me: int = 9

    required, defaults = _required_and_defaults(_Rec, exclude={"skip_me"})
    assert required == ("keep_required",)
    assert defaults == {"keep_default": 5}


def test_design_project_writes_one_project_record(parts):
    d = Design(parts)
    d.project(
        title="T",
        number="P-1",
        customer="C",
        revision=1,
        author="me",
    )
    records = d.draft().records()
    assert len(records) == 1
    project = _one(d.draft(), Project)
    assert project.title == "T"


def test_project_notice_defaults_to_empty(parts):
    d = Design(parts)
    d.project(
        title="T",
        number="P-1",
        customer="C",
        revision=1,
        author="me",
    )
    project = _one(d.draft(), Project)
    assert project.notice == ""


def test_project_notice_is_written(parts):
    d = Design(parts)
    d.project(
        title="T",
        number="P-1",
        customer="C",
        revision=1,
        author="me",
        notice="CE, IP54",
    )
    project = _one(d.draft(), Project)
    assert project.notice == "CE, IP54"


def test_location_and_group_are_distinct_aspect_nodes_with_the_same_name(parts):
    d = Design(parts)
    c1 = d.location("C1", "cabinet")
    g1 = d.group("C1", "a group happening to share the text")
    assert isinstance(c1, Location)
    assert c1.id != g1.id


def test_item_by_mpn_stamps_functions_and_ports(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    assert isinstance(k1, Item)
    names = {fn.name for fn in k1.functions}
    assert names == {"coil", "no_1", "co_2"}
    assert k1.fn("coil").kind is FunctionKind.COIL
    assert isinstance(k1.fn("coil")["A1"], Port)
    assert k1["A1"].name == "A1"


def test_item_with_only_name_leaves_designation_unset_for_numbering(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", name="run")
    record = _one(d.draft(), ModelItem)
    assert record.tag is None


def test_item_with_tag_sets_designation_and_is_also_the_name(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1")
    record = _one(d.draft(), ModelItem)
    assert record.tag == "K1"
    assert record.key == ("K1",)


def test_item_with_manufacturer_tuple_disambiguates(parts):
    d = Design(parts)
    a = d.item(("Alpha", "TEST-SHARED"), tag="A1")
    b = d.item(("Beta", "TEST-SHARED"), tag="A2")
    assert a.id != b.id


def test_part_less_item_has_no_functions(parts):
    d = Design(parts)
    item = d.item(None, tag="A1")
    assert item.functions == ()


def test_item_at_and_group_write_two_placements(parts):
    """`at=`/`group=` are both placements (spec A8): one at `+`, one at `=`, no hints."""
    d = Design(parts)
    c1 = d.location("C1", "cabinet")
    g1 = d.group("G1", "group")
    k1 = d.item("TEST-RLY-2CO", tag="K1", at=c1, group=g1)
    placements = _only(d.draft(), Placement)
    assert len(placements) == 2
    assert {p.node for p in placements} == {c1.id, g1.id}
    assert _only(d.draft(), GroupHint) == ()
    assert k1.functions


def test_item_parent_sets_containment(parts):
    d = Design(parts)
    board = d.item(None, tag="A1")
    d.item("TEST-RLY-2CO", tag="K1", parent=board, position=2)
    record = next(r for r in _only(d.draft(), ModelItem) if r.key == ("K1",))
    assert record.parent == board.id
    assert record.position == 2


def test_item_none_mpn_records_description_installed_and_position(parts):
    d = Design(parts)
    d.item(None, tag="A1", description="motor pump enclosure", installed=False, position=3)
    record = _one(d.draft(), ModelItem)
    assert record.description == "motor pump enclosure"
    assert record.installed is False
    assert record.position == 3


def test_item_by_mpn_description_and_installed_are_passed_through(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1", description="motor pump relay", installed=False)
    record = next(r for r in _only(d.draft(), ModelItem) if r.id == k1.id)
    assert record.description == "motor pump relay"
    assert record.installed is False


def test_strip_and_terminal_expose_inner_outer_by_role(parts):
    d = Design(parts)
    c1 = d.location("C1", "cabinet")
    x1 = d.strip("X1", at=c1)
    assert isinstance(x1, Strip)
    t1 = x1.terminal("TEST-TB")
    assert isinstance(t1, Terminal)
    assert t1.inner.role is PortRole.INTERNAL
    assert t1.outer.role is PortRole.EXTERNAL


def test_terminal_in_a_unit_scope_is_stamped_with_that_unit(parts):
    """`Strip._unit` (the strip's own scope's unit) is stamped onto every item it makes."""
    d = Design(parts)
    u = d.scope("u1").unit("cab", revision=1, interface="1")
    x1 = u.strip("X1")
    t1 = x1.terminal("TEST-TB")
    record = next(r for r in _only(d.draft(), ModelItem) if r.id == t1.id)
    assert record.unit == u.unit_id


def test_terminal_index_counts_up_per_group_text(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    l1 = x1.terminal("TEST-TB", "L")
    l2 = x1.terminal("TEST-TB", "L")
    n1 = x1.terminal("TEST-TB", "N")
    assert l1.key[-1] == "1"
    assert l2.key[-1] == "2"
    assert n1.key[-1] == "1"


def test_terminal_explicit_index_is_used_and_bumps_the_counter(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t5 = x1.terminal("TEST-TB", index=5)
    t6 = x1.terminal("TEST-TB")
    assert t5.key[-1] == "5"
    assert t6.key[-1] == "6"


def test_terminal_with_group_writes_a_placement_not_a_hint(parts):
    d = Design(parts)
    g1 = d.group("G1", "group")
    x1 = d.strip("X1")
    t1 = x1.terminal("TEST-TB", group=g1)
    placements = _only(d.draft(), Placement)
    assert len(placements) == 1
    assert placements[0].node == g1.id
    assert placements[0].item == t1.id
    assert _only(d.draft(), GroupHint) == ()


def test_cable_core_writes_its_index_and_leaves_the_colour_to_the_part(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1 = x1.terminal("TEST-TB")
    t2 = x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1", length_mm=5000)
    assert isinstance(w1, Cable)
    w1.core(1, t1.outer, t2.outer)
    core_facet = _one(d.draft(), CoreFacet)
    assert core_facet.index == 1
    cable_facet = _one(d.draft(), CableFacet)
    assert cable_facet.length_mm == 5000


def test_cable_conductor_is_kind_core(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1")
    w1.core(2, t1.outer, t2.outer)
    conductor = _one(d.draft(), Conductor)
    assert conductor.kind is ConductorKind.CORE
    assert conductor.carrier == w1.id


def test_cable_from_a_nested_scope_prefixes_the_key_and_takes_a_parent(parts):
    d = Design(parts)
    u = d.scope("p1")
    board = u.item(None, tag="A1")
    w1 = u.cable("TEST-CBL-2", tag="W1", parent=board)
    record = next(r for r in _only(d.draft(), ModelItem) if r.id == w1.id)
    assert record.key[0] == "p1"
    assert record.parent == board.id
    assert record.tag == "W1"
    assert record.description == ""
    assert record.installed is True
    assert record.unit is None
    assert record.external is False
    assert record.position is None
    assert record.part is not None


def test_cable_core_at_the_same_index_with_different_ports_is_a_name_clash(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2, t3 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1")
    w1.core(1, t1.outer, t2.outer)
    with pytest.raises(AuthorError, match="already names a different"):
        w1.core(1, t1.outer, t3.outer)


def test_cable_length_mm_defaults_to_none(parts):
    d = Design(parts)
    w1 = d.cable("TEST-CBL-2", tag="W1")
    assert isinstance(w1, Cable)
    cable_facet = _one(d.draft(), CableFacet)
    assert cable_facet.length_mm is None
    assert cable_facet.subject == w1.id
    assert cable_facet.ext == frozendict()


def test_harness_is_a_part_less_item(parts):
    d = Design(parts)
    harness = d.harness(tag="WH1")
    assert harness.functions == ()
    record = _one(d.draft(), ModelItem)
    assert record.part is None
    assert record.tag == "WH1"


def test_wiring_writes_conductor_and_facet(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, t2.inner)
    conductor = _one(d.draft(), Conductor)
    facet = _one(d.draft(), WireFacet)
    assert conductor.kind is ConductorKind.WIRE
    assert facet.colour == "BU"
    assert facet.gauge_mm2 == Decimal("0.75")


def test_wiring_overrides_the_wire_maker_defaults(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75", label="W1")
    wire(t1.inner, t2.inner, colour="BN", label="W2")
    facet = _one(d.draft(), WireFacet)
    assert facet.colour == "BN"
    assert facet.label == "W2"


def test_wire_n_distinguishes_two_parallel_wires(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, t2.inner)
    wire(t1.inner, t2.inner, n=2)
    conductors = _only(d.draft(), Conductor)
    assert len(conductors) == 2
    assert conductors[0].id != conductors[1].id


def test_wiring_from_a_nested_scope_prefixes_the_conductor_key(parts):
    d = Design(parts)
    u = d.scope("p1")
    x1 = u.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = u.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, t2.inner)
    conductor = _one(d.draft(), Conductor)
    assert conductor.key[0] == "p1"
    assert {conductor.a, conductor.b} == {t1.inner.id, t2.inner.id}
    assert conductor.kind is ConductorKind.WIRE
    assert conductor.carrier is None


def test_wire_n_distinguishes_two_different_port_pairs_sharing_one_n(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2, t3, t4 = (
        x1.terminal("TEST-TB"),
        x1.terminal("TEST-TB"),
        x1.terminal("TEST-TB"),
        x1.terminal("TEST-TB"),
    )
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, t2.inner, n=1)
    wire(t3.inner, t4.inner, n=1)
    conductors = _only(d.draft(), Conductor)
    assert len(conductors) == 2
    assert conductors[0].key != conductors[1].key


def test_wire_falls_back_to_the_maker_s_own_non_none_label(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75", label="DEFAULT")
    wire(t1.inner, t2.inner)
    facet = _one(d.draft(), WireFacet)
    assert facet.label == "DEFAULT"


def test_wire_run_makes_one_wire_per_neighbouring_pair(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2, t3 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    wire.run(t1.inner, t2.inner, t3.inner)
    conductors = _only(d.draft(), Conductor)
    assert len(conductors) == 2


def test_net_writes_ports_class_and_potential(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    d.net("P24", t1.outer, t2.outer, cls="power", potential="+24V")
    net = _one(d.draft(), Net)
    assert net.net_class is NetClass.POWER
    assert net.potential == "+24V"
    assert set(net.ports) == {t1.outer.id, t2.outer.id}


def test_net_defaults_to_control_class_and_no_potential(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    d.net("N1", t1.outer, t2.outer)
    net = _one(d.draft(), Net)
    assert net.net_class is NetClass.CONTROL
    assert net.potential is None
    assert net.name == "N1"
    assert net.key == ("net", "N1")


def test_net_key_carries_scope_prefix(parts):
    d = Design(parts)
    u = d.scope("p1")
    x1 = u.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    u.net("N1", t1.outer, t2.outer)
    net = _one(d.draft(), Net)
    assert net.key == ("p1", "net", "N1")


def test_mate_joins_two_connector_functions(parts):
    d = Design(parts)
    housing = d.item("TEST-CONN-2P", tag="X1")
    edge = d.item("TEST-EDGE-2P", tag="J1")
    d.mate(housing.fn("conn"), edge.fn("conn"))
    mate = _one(d.draft(), Mate)
    assert {mate.a, mate.b} == {housing.fn("conn").id, edge.fn("conn").id}


def test_mate_accepts_single_function_items(parts):
    d = Design(parts)
    housing = d.item("TEST-CONN-2P", tag="X1")
    edge = d.item("TEST-EDGE-2P", tag="J1")
    d.mate(housing, edge)
    assert len(_only(d.draft(), Mate)) == 1


def test_mate_key_is_the_same_regardless_of_argument_order(parts):
    d1 = Design(parts)
    housing1 = d1.item("TEST-CONN-2P", tag="X1")
    edge1 = d1.item("TEST-EDGE-2P", tag="J1")
    d1.mate(housing1.fn("conn"), edge1.fn("conn"))

    d2 = Design(parts)
    housing2 = d2.item("TEST-CONN-2P", tag="X1")
    edge2 = d2.item("TEST-EDGE-2P", tag="J1")
    d2.mate(edge2.fn("conn"), housing2.fn("conn"))

    mate1 = _one(d1.draft(), Mate)
    mate2 = _one(d2.draft(), Mate)
    assert mate1.key == mate2.key


def test_mate_from_a_nested_scope_prefixes_the_key(parts):
    d = Design(parts)
    u = d.scope("p1")
    housing = u.item("TEST-CONN-2P", tag="X1")
    edge = u.item("TEST-EDGE-2P", tag="J1")
    u.mate(housing.fn("conn"), edge.fn("conn"))
    mate = _one(d.draft(), Mate)
    assert mate.key[0] == "p1"


def test_bridge_makes_one_jumper_per_consecutive_pair_on_internal_ports(parts):
    """Spec T1's worked example: three terminals bridged give two `jumper` conductors."""
    d = Design(parts)
    x01 = d.strip("X01")
    l1 = [x01.terminal("TEST-TB", "L1") for _ in range(3)]
    d.bridge(*l1)
    conductors = _only(d.draft(), Conductor)
    assert len(conductors) == 2
    assert {frozenset((c.a, c.b)) for c in conductors} == {
        frozenset((l1[0].inner.id, l1[1].inner.id)),
        frozenset((l1[1].inner.id, l1[2].inner.id)),
    }
    assert all(c.kind is ConductorKind.JUMPER for c in conductors)
    assert _only(d.draft(), WireFacet) == ()


def test_bridge_jumper_carries_no_carrier_and_keys_under_the_scopes_prefix(parts):
    d = Design(parts)
    u = d.scope("p1")
    x01 = u.strip("X01")
    l1 = [x01.terminal("TEST-TB", "L1") for _ in range(2)]
    u.bridge(*l1)
    conductor = _one(d.draft(), Conductor)
    assert conductor.carrier is None
    assert conductor.key[0] == "p1"
    assert conductor.kind is ConductorKind.JUMPER
    assert {conductor.a, conductor.b} == {l1[0].inner.id, l1[1].inner.id}


def test_bridge_gives_each_consecutive_pair_a_distinct_key(parts):
    d = Design(parts)
    x01 = d.strip("X01")
    l1 = [x01.terminal("TEST-TB", "L1") for _ in range(3)]
    d.bridge(*l1)
    conductors = _only(d.draft(), Conductor)
    assert len({c.key for c in conductors}) == 2


def test_bridge_puts_every_bridged_terminal_in_one_terminal_rows_group(parts):
    from fransys_model.derive import terminal_rows
    from fransys_model.kernel import freeze, merge

    d = Design(parts)
    x01 = d.strip("X01")
    l1 = [x01.terminal("TEST-TB", "L1") for _ in range(3)]
    d.bridge(*l1)
    model = freeze(merge(parts, d.draft()))
    rows = terminal_rows(model, x01.id)
    assert {row.jumper_group for row in rows} == {1}


def test_chain_indexes_functions_in_argument_order(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    d.chain(t1, k1.fn("coil"), t2)
    chain = _one(d.draft(), Chain)
    ordered = sorted(chain.entries, key=lambda e: e.index)
    assert [e.function for e in ordered] == [t1.function.id, k1.fn("coil").id, t2.function.id]


def test_keep_together_stores_groups_sorted_by_id(parts):
    d = Design(parts)
    g1, g2 = d.group("G1"), d.group("G2")
    d.keep_together(g2, g1)
    record = _one(d.draft(), KeepTogether)
    assert record.groups == tuple(sorted((g1.id, g2.id)))


def test_break_before_names_the_group(parts):
    d = Design(parts)
    g1 = d.group("G1")
    d.break_before(g1)
    record = _one(d.draft(), BreakBefore)
    assert record.group == g1.id


def test_order_writes_one_hint_per_neighbour_pair(parts):
    d = Design(parts)
    g1, g2, g3 = d.group("G1"), d.group("G2"), d.group("G3")
    d.order(g1, g2, g3)
    hints = _only(d.draft(), OrderHint)
    assert len(hints) == 2
    pairs = {(h.before, h.after) for h in hints}
    assert pairs == {(g1.id, g2.id), (g2.id, g3.id)}


def test_order_needs_at_least_two_groups(parts):
    d = Design(parts)
    g1 = d.group("G1")
    with pytest.raises(AuthorError, match="at least 2 groups"):
        d.order(g1)


def test_order_hint_key_carries_scope_prefix(parts):
    d = Design(parts)
    u = d.scope("p1")
    g1, g2 = u.group("G1"), u.group("G2")
    u.order(g1, g2)
    hint = _one(d.draft(), OrderHint)
    assert hint.key[0] == "p1"


def test_symbol_on_a_function_writes_one_choice(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    d.symbol(k1.fn("coil"), "operating-device", {"A1": "in"})
    choice = _one(d.draft(), SymbolChoice)
    assert choice.function == k1.fn("coil").id
    assert choice.part is None
    assert choice.kind is None
    assert choice.port_map["A1"] == "in"
    assert choice.key == (*k1.fn("coil").key, "symbol_choice")


def test_symbol_on_an_item_fans_out_to_every_function(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    d.symbol(k1, "generic")
    choices = _only(d.draft(), SymbolChoice)
    assert len(choices) == len(k1.functions)
    assert {c.function for c in choices} == {fn.id for fn in k1.functions}


def test_symbol_with_no_port_map_defaults_to_empty(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    d.symbol(k1.fn("coil"), "generic")
    choice = _one(d.draft(), SymbolChoice)
    assert choice.port_map == frozendict({})


def test_symbol_by_function_kind_value_writes_a_kind_choice(parts):
    d = Design(parts)
    d.symbol(FunctionKind.TERMINAL, "terminal", {"internal": "n", "external": "s"})
    choice = _one(d.draft(), SymbolChoice)
    assert choice.kind is FunctionKind.TERMINAL
    assert choice.function is None
    assert choice.port_map["internal"] == "n"
    assert choice.port_map["external"] == "s"


def test_symbol_by_kind_string_is_equivalent_to_the_enum(parts):
    d = Design(parts)
    d.symbol("terminal", "terminal")
    choice = _one(d.draft(), SymbolChoice)
    assert choice.kind is FunctionKind.TERMINAL


def test_symbol_by_kind_from_a_nested_scope_prefixes_the_key(parts):
    d = Design(parts)
    u = d.scope("p1")
    u.symbol(FunctionKind.TERMINAL, "terminal")
    choice = _one(d.draft(), SymbolChoice)
    assert choice.key == ("p1", "symbol", "terminal")


def test_sheet_and_profile_round_trip_every_required_number(parts):
    d = Design(parts)
    sheet = d.sheet(
        "A3",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    sheet_record = _one(d.draft(), ModelSheetFormat)
    assert sheet_record.id == sheet
    assert sheet_record.name == "A3"
    assert sheet_record.key == ("sheet", "A3")
    assert sheet_record.width_mm == 420
    assert sheet_record.height_mm == 297
    assert sheet_record.content_x_mm == 10
    assert sheet_record.content_y_mm == 10
    assert sheet_record.content_width_mm == 400
    assert sheet_record.content_height_mm == 277
    assert sheet_record.frame_columns == 8
    assert sheet_record.frame_rows == 6
    assert sheet_record.module_mm == Decimal("2.5")
    d.profile(
        sheet=sheet,
        column_gap=4,
        row_gap=4,
        route_margin=2,
        text_height=3,
        marker_padding=1,
        route_turn_penalty=1,
        route_crossing_penalty=2,
    )
    profile = _one(d.draft(), ModelProfile)
    assert profile.sheet_format == sheet
    assert profile.column_gap == 4
    assert profile.band_ranks == default_profile().band_ranks


def test_profile_accepts_the_optional_rank_maps(parts):
    d = Design(parts)
    sheet = d.sheet(
        "A3",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    d.profile(
        sheet=sheet,
        column_gap=4,
        row_gap=4,
        route_margin=2,
        text_height=3,
        marker_padding=1,
        route_turn_penalty=1,
        route_crossing_penalty=2,
        band_ranks=frozendict({"coil": 0}),
    )
    profile = _one(d.draft(), ModelProfile)
    assert profile.band_ranks == frozendict({"coil": 0})


def _fields_but_identity(profile: ModelProfile) -> dict[str, object]:
    return {
        f.name: getattr(profile, f.name)
        for f in dataclasses.fields(profile)
        if f.name not in {"id", "key"}
    }


def test_profile_with_no_arguments_is_the_house_profile(parts):
    d = Design(parts)
    d.profile()
    profile = _one(d.draft(), ModelProfile)
    assert _fields_but_identity(profile) == _fields_but_identity(default_profile())
    assert profile.sheet_format is None


def test_profile_sets_one_field_and_replaces_it_whole(parts):
    d = Design(parts)
    d.profile(group_ranks=frozendict({"=A": 0}))
    profile = _one(d.draft(), ModelProfile)
    house = default_profile()
    assert profile.group_ranks == frozendict({"=A": 0})
    assert profile.band_ranks == house.band_ranks
    assert profile.column_gap == house.column_gap


def test_profile_rank_map_given_is_not_merged_with_the_house_map(parts):
    d = Design(parts)
    d.profile(band_ranks=frozendict({"coil": 0}))
    assert _one(d.draft(), ModelProfile).band_ranks == frozendict({"coil": 0})


def test_scope_prefixes_every_key_it_writes(parts):
    d = Design(parts)
    u = d.scope("p1")
    k = u.item("TEST-RLY-2CO", name="run")
    assert k.key == ("p1", "run")


def test_scope_inherits_at_and_group_as_defaults(parts):
    d = Design(parts)
    c1 = d.location("C1", "cabinet")
    g1 = d.group("G1", "group")
    u = d.scope("p1", at=c1, group=g1)
    u.item("TEST-RLY-2CO", tag="K1")
    placements = _only(d.draft(), Placement)
    assert len(placements) == 2
    assert {p.node for p in placements} == {c1.id, g1.id}


def test_scope_call_can_override_the_inherited_default(parts):
    d = Design(parts)
    c1 = d.location("C1", "cabinet")
    c2 = d.location("C2", "second cabinet")
    u = d.scope("p1", at=c1)
    u.item("TEST-RLY-2CO", tag="K1", at=c2)
    placement = _one(d.draft(), Placement)
    assert placement.node == c2.id


def test_nested_scope_extends_the_prefix(parts):
    d = Design(parts)
    u = d.scope("p1")
    inner = u.scope("sub")
    k = inner.item("TEST-RLY-2CO", name="run")
    assert k.key == ("p1", "sub", "run")


def test_plc_and_scale_return_the_function_for_chaining(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    coil = k1.fn("coil")
    result = coil.plc("do", "PUMP1_RUN", priority=5).scale("m", raw=(0, 100), eng=("0", "10"))
    assert isinstance(result, Fn)
    plc = _one(d.draft(), PlcRequestFacet)
    scaling = _one(d.draft(), ScalingFacet)
    assert plc.signal_name == "PUMP1_RUN"
    assert plc.signal is SignalType.DO
    assert plc.priority == 5
    assert plc.subject == coil.id
    assert scaling.eng_max == Decimal(10)
    assert scaling.subject == coil.id
    assert scaling.raw_min == 0
    assert scaling.raw_max == 100
    assert scaling.eng_min == Decimal(0)
    assert scaling.unit == "m"


def test_draft_returns_only_the_design_s_own_records_not_the_parts(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1")
    part_ids = {r.id for r in parts.records()}
    design_ids = {r.id for r in d.draft().records()}
    assert part_ids.isdisjoint(design_ids)


def test_draw_in_writes_one_group_hint_and_nothing_else(parts):
    """spec A8: `draw_in` is the only way to hint a group; `group=` stays a placement."""
    d = Design(parts)
    p1, es = d.group("P1"), d.group("ES")
    estop = d.item("TEST-RLY-2CO", tag="S0", group=es)
    d.draw_in(estop.fn("co_2"), p1)
    hint = _one(d.draft(), GroupHint)
    assert hint.function == estop.fn("co_2").id
    assert hint.group == p1.id
    placements = _only(d.draft(), Placement)
    assert len(placements) == 1
    assert placements[0].node == es.id


def test_cable_group_writes_a_second_placement(parts):
    d = Design(parts)
    c1 = d.location("C1", "cabinet")
    sup = d.group("SUP", "supply")
    w1 = d.cable("TEST-CBL-2", tag="W1", at=c1, group=sup)
    placements = _only(d.draft(), Placement)
    assert {p.node for p in placements} == {c1.id, sup.id}
    assert all(p.item == w1.id for p in placements)


def test_the_full_worked_example_shape_freezes(parts):
    """Not the spec's literal MPNs (not in the hand-made catalogue) -- same shape."""
    d = Design(parts)
    d.project(
        title="T",
        number="P-1",
        customer="C",
        revision=1,
        author="me",
    )
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    c1 = d.location("C1", "cabinet")
    sup = d.group("SUP", "supply")
    p1 = d.group("P1", "pump 1")
    x1 = d.strip("X1", at=c1)
    t1 = x1.terminal("TEST-TB", group=sup)
    t2 = x1.terminal("TEST-TB", group=sup)
    k1 = d.item("TEST-RLY-2CO", name="run", at=c1, group=p1)
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, k1.fn("coil")["A1"])
    wire.run(k1.fn("coil")["A2"], t2.inner)
    d.net("P24", t1.outer, cls="power", potential="+24V")
    w1 = d.cable("TEST-CBL-2", tag="W1", length_mm=12000)
    w1.core(1, t2.outer, k1["13"])
    k1.fn("coil").plc("do", "PUMP1_RUN")
    d.chain(t1, k1.fn("coil"), t2)
    model = freeze(merge(parts, d.draft()))
    assert model.digests["core"]
    assert model.digests["facet"]
    assert model.digests["layout"]


def test_three_instances_of_one_unit_release_with_no_entry_give_one_error(parts):
    """SC5: `relay-board` rev 01 built in three scopes, no entry authored: ONE ERROR, not three."""
    d = Design(parts)
    for prefix in ("a", "b", "c"):
        d.scope(prefix).unit("relay-board", revision=1, interface="1")
    model = freeze(merge(parts, d.draft()))
    assert len(units(model)) == 3
    assert not revisions(model)
    (finding,) = [f for f in check_revisions(model) if f.code == REVISION_CURRENT_MISSING]
    assert finding.severity is Severity.ERROR
    assert "revision(" not in finding.message


def test_profile_hide_unused_pins_is_off_by_house_value_and_set_by_the_switch(parts):
    off = Design(parts)
    off.profile()
    assert _one(off.draft(), ModelProfile).hide_unused_pins is False
    on = Design(parts)
    on.profile(hide_unused_pins=True)
    assert _one(on.draft(), ModelProfile).hide_unused_pins is True
