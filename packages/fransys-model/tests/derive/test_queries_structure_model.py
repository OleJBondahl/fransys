"""WP16 tests: board netlists, aspect trees and `ext` usage. Plus `schematic_functions`."""

from decimal import Decimal

import pytest
from plant import Plant
from query_builders import (
    make_board,
    make_footprint,
    make_node,
    make_part,
    make_pin,
    make_placement,
    make_tree,
    reversed_tables,
    with_ext,
)

from fransys_model.derive import (
    board_netlist,
    effective_placement,
    ext_usage,
    is_sole_unit_root,
    items_at,
    schematic_functions,
    subtree,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Aspect, FunctionKind, PartCategory
from fransys_model.vocab.facets.cable import CableProductFacet
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.tables import aspect_nodes, placements
from fransys_model.vocab.templates import Part
from fransys_model.vocab.validators.connectivity import NET_SHORTED, check_connectivity


def _board_part(plant: Plant, key: str) -> Id[Part]:
    """A part that carries the `pcb` facet, keyed distinctly so a test can add several."""
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.BOARD,
        class_code="A",
    )
    facet = PcbFacet(
        id=make_id(PcbFacet, (key, "pcb")), key=(key, "pcb"), subject=part.id, revision="A"
    )
    plant.add(part, facet)
    return part.id


def test_board_netlist_lists_footprinted_descendants_sorted_by_designation_naturally() -> None:
    """Grandchildren count, an item without a footprint and a foreign item do not; `R2` < `R10`."""
    plant = Plant()
    board = make_board(plant)
    sub = plant.item("sub", parent=board, designation="B1")
    plant.item("c1", parent=sub, part=make_footprint(plant, "c", "C_0603"), designation="C1")
    plant.item("plain", parent=board, part=make_part(plant, "plain", "P-1"), designation="P1")
    plant.item("noparts", parent=board, designation="P2")
    plant.item("foreign", part=make_footprint(plant, "f", "F_0603"), designation="F1")
    netlist = board_netlist(plant.model(), board)
    assert (netlist.board, netlist.board_designation) == (board, "A1")
    assert [
        (p.designation, p.mpn, p.footprint_library, p.footprint_name) for p in netlist.parts
    ] == [
        ("C1", "MPN-c", "ExampleLib", "C_0603"),
        ("R2", "MPN-r", "ExampleLib", "R_0603"),
        ("R10", "MPN-r", "ExampleLib", "R_0603"),
    ]


def test_board_netlist_ties_on_designation_fall_to_the_item_id() -> None:
    """Two parts numbered alike (the same `R1` twice) come out in id order."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    footprint = make_footprint(plant, "r", "R_0603")
    for key in ("r-b", "r-a"):
        plant.item(key, parent=board, part=footprint, designation="R1")
    netlist = board_netlist(plant.model(), board)
    assert [p.item for p in netlist.parts] == sorted(make_id(Item, (k,)) for k in ("r-a", "r-b"))


def test_board_netlist_relative_designations_drop_the_chain_up_to_the_board() -> None:
    """`K1`, not `-A1-K1` (model-0040, spec B3's KiCad refinement): the board's own
    `item_designation` prefix is stripped from every part's, `board_designation` unchanged."""
    plant = Plant()
    board_part = _board_part(plant, "board")
    board = plant.item("board", part=board_part, designation="A1")
    footprint = make_footprint(plant, "r", "R_0603")
    plant.item("k1", parent=board, part=footprint, designation="K1")
    netlist = board_netlist(plant.model(), board)
    assert netlist.board_designation == "A1"
    (part,) = netlist.parts
    assert part.designation == "K1"


def test_board_netlist_relative_designations_keep_an_inner_boards_own_segment() -> None:
    """A board inside another board: netlisting the outer board drops only the outer
    board's own chain segment, keeping the inner board's (model-0040)."""
    plant = Plant()
    outer_part = _board_part(plant, "outer")
    inner_part = _board_part(plant, "inner")
    outer = plant.item("outer", part=outer_part, designation="A2")
    inner = plant.item("inner", part=inner_part, parent=outer, designation="B1")
    footprint = make_footprint(plant, "r", "R_0603")
    plant.item("k1", parent=inner, part=footprint, designation="K1")
    netlist = board_netlist(plant.model(), outer)
    assert netlist.board_designation == "A2"
    (part,) = netlist.parts
    assert part.designation == "B1-K1"


def test_board_netlist_relative_designations_do_nothing_without_a_pcb_facet() -> None:
    """`board` need not carry a `pcb` facet (existing rule): nothing to strip, so a part's
    designation is unchanged, as the pre-model-0040 tests above already prove."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    footprint = make_footprint(plant, "r", "R_0603")
    plant.item("k1", parent=board, part=footprint, designation="K1")
    netlist = board_netlist(plant.model(), board)
    (part,) = netlist.parts
    assert part.designation == "K1"


def test_board_netlist_holds_the_nets_wholly_on_the_board_named_and_sorted() -> None:
    """A net with a port off the board or with no ports is left out.

    The name is `Net.name`, or the authoring key when there is none. Every pin here belongs
    to only one declared net, so `port_groups`' union-find (decision model-0042) never merges
    two of these nets through a shared pin -- that scenario is its own test below.
    """
    plant = Plant()
    board = make_board(plant)
    p1 = make_pin(plant, "u1", "U1", parent=board)
    p2 = make_pin(plant, "u2", "U2", parent=board)
    p3 = make_pin(plant, "u3", "U3", parent=board)
    p4 = make_pin(plant, "u4", "U4", parent=board)
    off = make_pin(plant, "off", "O1")
    plant.net("a-key", (p1, p2))
    plant.net("named", (p3,), name="z-Named")
    plant.net("crosses", (p4, off))
    plant.net("empty", ())
    netlist = board_netlist(plant.model(), board)
    assert [(n.name, n.pins) for n in netlist.nets] == [
        ("a-key", tuple(sorted((p1, p2)))),
        ("z-Named", (p3,)),
    ]


# -- board_netlist's connected groups (decision model-0042) ------------------------------


def test_board_netlist_names_an_undeclared_group_from_its_smallest_pin_board_relative() -> None:
    """Two board-internal conductors give two undeclared nets, each `Net-(ref-pin)`
    (decision model-0042): the reference is board-relative `item_designation`, the pin is
    `Port.name`, and the smaller `(reference, pin)` wins -- `K1-A1` and `K1-A2` beat `X1-1`
    and `X1-2`, `K1` sorting before `X1`.
    """
    plant = Plant()
    board = plant.item("board", designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    k1 = plant.item("k1", parent=board, designation="K1")
    x1_fn = plant.function(x1, "x1")
    k1_fn = plant.function(k1, "coil")
    x1_1, x1_2 = plant.port(x1_fn, "1"), plant.port(x1_fn, "2")
    k1_a1, k1_a2 = plant.port(k1_fn, "A1"), plant.port(k1_fn, "A2")
    plant.wire(x1_1, k1_a1, key="w1")
    plant.wire(x1_2, k1_a2, key="w2")
    netlist = board_netlist(plant.model(), board)
    assert [(n.name, n.pins) for n in netlist.nets] == [
        ("Net-(K1-A1)", tuple(sorted((x1_1, k1_a1)))),
        ("Net-(K1-A2)", tuple(sorted((x1_2, k1_a2)))),
    ]


def test_board_netlist_a_group_holding_a_declared_ports_name_takes_it() -> None:
    """A board-internal conductor's group, one of whose ports is also a declared net's own
    (even a net naming only that single port), takes the declared name, not the undeclared
    `Net-(...)` form (decision model-0042)."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    k1 = plant.item("k1", parent=board, designation="K1")
    x1_port = plant.port(plant.function(x1, "x1"), "1")
    k1_port = plant.port(plant.function(k1, "coil"), "A1")
    plant.wire(x1_port, k1_port, key="w")
    plant.net("sig", (k1_port,), name="SIG")
    netlist = board_netlist(plant.model(), board)
    assert [(n.name, n.pins) for n in netlist.nets] == [("SIG", tuple(sorted((x1_port, k1_port))))]


def test_board_netlist_a_conductor_with_one_end_off_the_board_is_excluded() -> None:
    """A conductor that leaves the board is never a board-internal edge, even when its
    on-board pin also carries a real board-internal conductor: `X1`'s one pin wires both to
    `K1` (on the board) and off the board, and the `K1` group must appear regardless of the
    off-board wire -- this is what the both-ends-on-board filter protects, not merely that an
    isolated off-board pin gets no net of its own (decision model-0042)."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    k1 = plant.item("k1", parent=board, designation="K1")
    off = plant.item("off", designation="O1")
    x1_port = plant.port(plant.function(x1, "x1"), "1")
    k1_port = plant.port(plant.function(k1, "coil"), "A1")
    off_port = plant.port(plant.function(off, "f"), "1")
    plant.wire(x1_port, k1_port, key="w-on")
    plant.wire(x1_port, off_port, key="w-off")
    netlist = board_netlist(plant.model(), board)
    assert [(n.name, n.pins) for n in netlist.nets] == [
        ("Net-(K1-A1)", tuple(sorted((x1_port, k1_port))))
    ]


def test_board_netlist_two_declared_names_in_one_group_is_net_shorted_and_takes_the_smaller() -> (
    None
):
    """A board-internal conductor across two singly-declared nets makes one physical net that
    both `check_connectivity`'s `NET_SHORTED` (over the real closure) and `board_netlist`'s
    own grouping see (decision model-0042 adds no new check, per the ruling): the existing
    validator reports it, and the netlist names the group by the smaller `(name, net id)`,
    `connector_rows`' own tie-break."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    k1 = plant.item("k1", parent=board, designation="K1")
    x1_port = plant.port(plant.function(x1, "x1"), "1")
    k1_port = plant.port(plant.function(k1, "coil"), "A1")
    plant.wire(x1_port, k1_port, key="w")
    alpha = plant.net("alpha", (x1_port,), name="Alpha")
    beta = plant.net("beta", (k1_port,), name="Beta")
    model = plant.model()

    shorted = [f for f in check_connectivity(model) if f.code == NET_SHORTED]
    assert len(shorted) == 1
    assert shorted[0].subjects == tuple(sorted((alpha, beta)))

    netlist = board_netlist(model, board)
    assert [(n.name, n.pins) for n in netlist.nets] == [
        ("Alpha", tuple(sorted((x1_port, k1_port))))
    ]


def test_board_netlist_an_off_board_declared_net_names_nothing_and_joins_nothing() -> None:
    """The board-edge amendment to model-0042: a declared net reaching off the board takes no
    part in the netlist at all -- it must not pull a board-internal group's name away from
    its own undeclared form, the defect the amendment fixes. `X1`'s pin carries a
    board-internal conductor to `K1` and is also listed, together with an off-board port, in
    a declared net `SIG`; the kept group is the board-internal wire alone, named
    `Net-(K1-A1)`, never `SIG`."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    k1 = plant.item("k1", parent=board, designation="K1")
    off = plant.item("off", designation="O1")
    x1_port = plant.port(plant.function(x1, "x1"), "1")
    k1_port = plant.port(plant.function(k1, "coil"), "A1")
    off_port = plant.port(plant.function(off, "f"), "1")
    plant.wire(x1_port, k1_port, key="w-on")
    plant.net("sig", (x1_port, off_port), name="SIG")
    netlist = board_netlist(plant.model(), board)
    assert [(n.name, n.pins) for n in netlist.nets] == [
        ("Net-(K1-A1)", tuple(sorted((x1_port, k1_port))))
    ]


def test_board_netlist_is_invariant_under_off_board_wiring_and_declared_nets() -> None:
    """Board-edge amendment to model-0042: a board's own netlist is byte-identical whether it
    is read alone or in a larger design that adds off-board wiring, a net reaching past it and
    an off-board cable -- a board is released and frozen on its own and serves many parents.
    The declared-net half: a cabinet's own `SIG` net (`X1`'s pin plus an off-board port) and an
    off-board conductor bridging two other off-board ports. The cable-item half: a cable item
    outside the board with one core bridging `X1:1` and `X1:2` -- a core lands on two board
    pins but is carried by an off-board cable, so it does not join them either."""

    def _build(*, with_off_board: bool):
        plant = Plant()
        board = plant.item("board", designation="A1")
        x1 = plant.item("x1", parent=board, designation="X1")
        k1 = plant.item("k1", parent=board, designation="K1")
        x1_fn = plant.function(x1, "x1")
        k1_fn = plant.function(k1, "coil")
        x1_1, x1_2 = plant.port(x1_fn, "1"), plant.port(x1_fn, "2")
        k1_a1, k1_a2 = plant.port(k1_fn, "A1"), plant.port(k1_fn, "A2")
        plant.wire(x1_1, k1_a1, key="w1")
        plant.wire(x1_2, k1_a2, key="w2")
        if with_off_board:
            p1 = plant.item("p1", designation="P1")
            p1_fn = plant.function(p1, "p1")
            p1_1, p1_2 = plant.port(p1_fn, "1"), plant.port(p1_fn, "2")
            plant.wire(p1_1, p1_2, key="off-bridge")
            plant.net("sig", (x1_1, p1_1), name="SIG")
            off_cable = plant.item("cable", designation="W1")
            plant.core(x1_1, x1_2, key="off-board-core", carrier=off_cable)
        return board_netlist(plant.model(), board)

    assert _build(with_off_board=True) == _build(with_off_board=False)


def test_board_netlist_a_loose_wire_between_two_board_pins_merges_their_groups() -> None:
    """The documented limit (decision model-0042): the model cannot tell a loose wire between
    two pins of one board from board wiring, so it counts as board wiring too, unlike a cable
    core carried off the board. A plain `Conductor` (no `carrier`) directly joining `X1`'s two
    pins merges the two otherwise separate `K1` groups into one."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    k1 = plant.item("k1", parent=board, designation="K1")
    x1_fn = plant.function(x1, "x1")
    k1_fn = plant.function(k1, "coil")
    x1_1, x1_2 = plant.port(x1_fn, "1"), plant.port(x1_fn, "2")
    k1_a1, k1_a2 = plant.port(k1_fn, "A1"), plant.port(k1_fn, "A2")
    plant.wire(x1_1, k1_a1, key="w1")
    plant.wire(x1_2, k1_a2, key="w2")
    plant.wire(x1_1, x1_2, key="bridge")
    netlist = board_netlist(plant.model(), board)
    assert [(n.name, n.pins) for n in netlist.nets] == [
        ("Net-(K1-A1)", tuple(sorted((x1_1, x1_2, k1_a1, k1_a2))))
    ]


def test_board_netlist_tolerates_a_parent_cycle_and_never_lists_the_board() -> None:
    """The board reached again through its own descendants is not its own part."""
    plant = Plant()
    footprint = make_footprint(plant, "r", "R_0603")
    board_id = make_id(Item, ("board",))
    child = plant.item("child", parent=board_id, part=footprint, designation="R1")
    plant.add(
        Item(
            id=board_id,
            key=("board",),
            part=footprint,
            parent=child,
            position=None,
            tag="A1",
            description="Invented",
            installed=True,
        )
    )
    netlist = board_netlist(plant.model(), board_id)
    assert [p.item for p in netlist.parts] == [child]


def test_board_netlist_refuses_an_unnumbered_board_or_part() -> None:
    """The board's designation is rendered even when nothing is listed on it; so is a part's."""
    plant = Plant()
    board = plant.item("board")
    with pytest.raises(SchemaError):
        board_netlist(plant.model(), board)
    numbered = Plant()
    top = numbered.item("board", designation="A1")
    numbered.item("r1", parent=top, part=make_footprint(numbered, "r", "R_0603"))
    with pytest.raises(SchemaError):
        board_netlist(numbered.model(), top)


def test_board_netlist_refuses_an_unknown_board() -> None:
    """Unknown identity: `SchemaError`."""
    plant = Plant()
    plant.item("board", designation="A1")
    with pytest.raises(SchemaError):
        board_netlist(plant.model(), make_id(Item, ("nope",)))


def test_board_netlist_refuses_an_unknown_board_naming_its_kind_and_id() -> None:
    """The `SchemaError` names the `item` kind and the unknown board id itself."""
    plant = Plant()
    plant.item("board", designation="A1")
    model = plant.model()
    unknown = make_id(Item, ("nope",))
    with pytest.raises(SchemaError) as excinfo:
        board_netlist(model, unknown)
    assert excinfo.value.kind == "item"
    assert excinfo.value.record_id == unknown


def test_subtree_is_every_descendant_by_parent_whatever_the_aspect_sorted_by_id() -> None:
    """The node itself and the unrelated tree are not in it."""
    plant = Plant()
    ids = make_tree(plant)
    model = plant.model()
    assert subtree(model, ids["root"]) == tuple(sorted((ids["left"], ids["leaf"], ids["right"])))
    assert subtree(model, ids["left"]) == (ids["leaf"],)
    assert subtree(model, ids["leaf"]) == ()


def test_subtree_and_items_at_end_a_parent_cycle() -> None:
    """Two nodes each other's parent: every descendant once, no hang."""
    plant = Plant()
    a, b = make_id(AspectNode, ("a",)), make_id(AspectNode, ("b",))
    plant.add(make_node("a", b), make_node("b", a))
    plant.add(make_placement("p", plant.item("i", designation="I1"), a))
    model = plant.model()
    assert subtree(model, a) == (b,)
    assert subtree(model, b) == (a,)
    assert items_at(model, b) == (make_id(Item, ("i",)),)


def test_items_at_is_every_item_at_the_node_or_below_once_each_in_id_order() -> None:
    """An item placed twice below the node is still one entry; items elsewhere are not listed."""
    plant = Plant()
    ids = make_tree(plant)
    placed = {
        name: plant.item(name, designation=name.upper())
        for name in ("top", "mid", "bottom", "away")
    }
    plant.add(
        make_placement("p-top", placed["top"], ids["root"]),
        make_placement("p-mid", placed["mid"], ids["left"]),
        make_placement("p-mid-again", placed["mid"], ids["leaf"]),
        make_placement("p-bottom", placed["bottom"], ids["right"]),
        make_placement("p-away", placed["away"], ids["lone"]),
    )
    crowd = [plant.item(f"crowd-{n}", designation=f"C{n}") for n in range(8)]
    plant.add(*(make_placement(f"p-crowd-{n}", item, ids["leaf"]) for n, item in enumerate(crowd)))
    model = plant.model()
    assert items_at(model, ids["root"]) == tuple(
        sorted((placed["top"], placed["mid"], placed["bottom"], *crowd))
    )
    assert items_at(model, ids["left"]) == tuple(sorted((placed["mid"], *crowd)))
    assert items_at(model, ids["lone"]) == (placed["away"],)


def test_items_at_includes_an_unplaced_boards_own_item_by_inheritance() -> None:
    """A board placed at a node lists a nested item with no placement of its own too
    (`effective_placement`, decision model-0040); an item with its own, different
    placement is not double-counted or moved."""
    plant = Plant()
    node = make_node("c1", None)
    elsewhere = make_node("c2", None)
    plant.add(node, elsewhere)
    board = plant.item("board", designation="A1")
    connector = plant.item("conn", parent=board, designation="X1")
    placed_child = plant.item("placed", parent=board, designation="P1")
    plant.add(
        make_placement("p-board", board, node.id),
        make_placement("p-placed-child", placed_child, elsewhere.id),
    )
    model = plant.model()
    assert items_at(model, node.id) == tuple(sorted((board, connector)))
    assert items_at(model, elsewhere.id) == (placed_child,)


def test_subtree_and_items_at_refuse_an_id_that_is_not_an_aspect_node() -> None:
    """Unknown identity: `SchemaError`."""
    plant = Plant()
    make_tree(plant)
    model = plant.model()
    with pytest.raises(SchemaError):
        subtree(model, make_id(AspectNode, ("nope",)))
    with pytest.raises(SchemaError):
        items_at(model, make_id(AspectNode, ("nope",)))


def test_subtree_refuses_an_unknown_node_naming_its_kind_and_id() -> None:
    """The `SchemaError` names the `aspect_node` kind and the unknown id itself."""
    plant = Plant()
    make_tree(plant)
    model = plant.model()
    unknown = make_id(AspectNode, ("nope",))
    with pytest.raises(SchemaError) as excinfo:
        subtree(model, unknown)
    assert excinfo.value.kind == "aspect_node"
    assert excinfo.value.record_id == unknown


def test_items_at_refuses_an_unknown_node_naming_its_kind_and_id() -> None:
    """The `SchemaError` names the `aspect_node` kind and the unknown id itself."""
    plant = Plant()
    make_tree(plant)
    model = plant.model()
    unknown = make_id(AspectNode, ("nope",))
    with pytest.raises(SchemaError) as excinfo:
        items_at(model, unknown)
    assert excinfo.value.kind == "aspect_node"
    assert excinfo.value.record_id == unknown


def test_ext_usage_counts_top_level_keys_per_kind_sorted_with_subjects_in_id_order() -> None:
    """One row per `(kind, key)`; nested keys are not walked; nothing in `ext` means no row."""
    plant = Plant()
    plant.item("clean", designation="K1")
    made = [plant.item(key, designation=key.upper()) for key in ("i-a", "i-b", "i-c")]
    more = [plant.item(f"i-{n}", designation=f"M{n}") for n in range(8)]
    for item_id in more:
        with_ext(plant, item_id, {"beta": "x"})
    nested = frozendict({"deep": 1})
    with_ext(plant, made[0], {"beta": "x", "nest": nested})
    with_ext(plant, made[1], {"beta": "x", "nest": nested})
    with_ext(plant, made[2], {"alpha": 1})
    part = make_part(plant, "p", "P-1")
    with_ext(plant, part, {"alpha": "y"})
    rows = ext_usage(plant.model())
    assert [(r.kind, r.key, r.count) for r in rows] == [
        ("item", "alpha", 1),
        ("item", "beta", 10),
        ("item", "nest", 2),
        ("part", "alpha", 1),
    ]
    assert rows[1].subjects == tuple(sorted((*made[:2], *more)))
    assert rows[0].subjects == (made[2],)
    assert rows[3].subjects == (part,)
    model = plant.model()
    assert ext_usage(reversed_tables(model)) == rows


def test_ext_usage_of_a_model_with_no_ext_is_empty() -> None:
    """Nothing stored in `ext` anywhere: no rows."""
    plant = Plant()
    plant.item("k1", designation="K1")
    assert ext_usage(plant.model()) == ()


# -- schematic_functions (model-0039) -----------------------------------------------


def test_schematic_functions_excludes_a_cable_items_own_function() -> None:
    """A cable item's own function is excluded; an ordinary item's function is not."""
    plant = Plant()
    cable_part = Part(
        id=make_id(Part, ("cable-part",)),
        key=("cable-part",),
        mpn="MPN-cable",
        manufacturer="Example Co",
        description="Invented cable",
        category=PartCategory.CABLE,
        class_code="W",
    )
    plant.add(cable_part)
    cable_product = CableProductFacet(
        id=make_id(CableProductFacet, ("cable-part", "product")),
        key=("cable-part", "product"),
        subject=cable_part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    plant.add(cable_product)
    cable_item = plant.item("cable", part=cable_part.id, designation="W1")
    plant.function(cable_item, "core")
    plain_item = plant.item("plain", designation="K1")
    plain_fn = plant.function(plain_item, "coil")
    model = plant.model()
    assert len(model.tables["function"]) == 2
    assert schematic_functions(model) == (plain_fn,)


def test_schematic_functions_excludes_a_function_on_or_under_a_board_item() -> None:
    """A function on the board itself and on a nested descendant are both excluded.

    The exclusion walks the whole ancestor chain, board item included, not only a board's
    descendants -- `grandchild` is two `parent` hops below `board` and still excluded.
    """
    plant = Plant()
    board_part = plant.board_part()
    board = plant.item("board", part=board_part, designation="A1")
    plant.function(board, "sense")
    child = plant.item("child", parent=board, designation="R1")
    plant.function(child, "coil")
    grandchild = plant.item("grandchild", parent=child, designation="R2")
    plant.function(grandchild, "coil")
    plain_item = plant.item("plain", designation="K1")
    plain_fn = plant.function(plain_item, "coil")
    model = plant.model()
    assert len(model.tables["function"]) == 4
    assert schematic_functions(model) == (plain_fn,)


def test_schematic_functions_includes_an_ordinary_function() -> None:
    """A function neither of a cable item nor on or under a board item is included."""
    plant = Plant()
    item = plant.item("k1", designation="K1")
    fn = plant.function(item, "coil")
    model = plant.model()
    assert len(model.tables["function"]) == 1
    assert schematic_functions(model) == (fn,)


def test_schematic_functions_includes_a_connector_on_a_board_item() -> None:
    """A `CONNECTOR` function on the board item itself is drawn (model-0040, spec B1);
    the board's other function stays excluded."""
    plant = Plant()
    board_part = plant.board_part()
    board = plant.item("board", part=board_part, designation="A1")
    connector_fn = plant.function(board, "x1", kind=FunctionKind.CONNECTOR)
    relay_item = plant.item("relay", parent=board, designation="K1")
    plant.function(relay_item, "coil", kind=FunctionKind.COIL)
    plain_item = plant.item("plain", designation="K2")
    plain_fn = plant.function(plain_item, "coil")
    model = plant.model()
    assert len(model.tables["function"]) == 3
    assert schematic_functions(model) == tuple(sorted((connector_fn, plain_fn)))


def test_schematic_functions_includes_a_connector_two_levels_under_a_board_item() -> None:
    """The `CONNECTOR` exception applies through the whole ancestor chain, not only the
    board item's own functions (model-0040, spec B1)."""
    plant = Plant()
    board_part = plant.board_part()
    board = plant.item("board", part=board_part, designation="A1")
    child = plant.item("child", parent=board, designation="R1")
    grandchild = plant.item("grandchild", parent=child, designation="X1")
    connector_fn = plant.function(grandchild, "x1", kind=FunctionKind.CONNECTOR)
    model = plant.model()
    assert len(model.tables["function"]) == 1
    assert schematic_functions(model) == (connector_fn,)


def test_schematic_functions_can_fail_a_terminal_on_a_board_item_stays_excluded() -> None:
    """Can-fail twin of the connector-on-a-board case: the same board, the same function,
    only its `kind` changed from `CONNECTOR` to `TERMINAL` -- then it is excluded again,
    proving the exception is on `kind`, not merely on being the board's own function."""
    plant = Plant()
    board_part = plant.board_part()
    board = plant.item("board", part=board_part, designation="A1")
    plant.function(board, "x1", kind=FunctionKind.TERMINAL)
    model = plant.model()
    assert len(model.tables["function"]) == 1
    assert schematic_functions(model) == ()


# -- schematic_functions and is_sole_unit_root (units spec U1's board-unit ruling, model-0041) --

_BOARD_UNIT_FUNCTION_COUNT = 2  # the board's own edge connector plus the relay coil


def test_schematic_functions_includes_a_board_functions_when_the_board_is_its_own_unit() -> None:
    """A board that is the *sole* root item of its own `Unit` is a nested unit (units spec U1):
    its non-`CONNECTOR` function (the relay coil) is drawn, not excluded, in its own home set --
    its `CONNECTOR` function was already drawn before this change (model-0040, spec B1)."""
    plant = Plant()
    board_part = plant.board_part()
    unit = plant.unit("io-board-unit")
    board = plant.item("board", part=board_part, designation="A1", unit=unit)
    connector_fn = plant.function(board, "x1", kind=FunctionKind.CONNECTOR)
    relay = plant.item("relay", parent=board, designation="K1", unit=unit)
    coil_fn = plant.function(relay, "coil", kind=FunctionKind.COIL)
    model = plant.model()
    assert len(model.tables["function"]) == _BOARD_UNIT_FUNCTION_COUNT
    result = schematic_functions(model)
    assert coil_fn in result
    assert result == tuple(sorted((connector_fn, coil_fn)))


def test_schematic_functions_excludes_a_board_functions_when_the_board_is_not_its_own_unit() -> (
    None
):
    """The discriminating twin: the board shares a *larger* unit with another root item
    (the cabinet's own top-level item), so the board is NOT the sole root of that unit --
    B1's exclusion still applies. A predicate that only checked "shares a unit with an
    ancestor board" would wrongly include this case, since the board's `unit` is set here too;
    only "is the sole root" tells the two apart."""
    plant = Plant()
    board_part = plant.board_part()
    unit = plant.unit("cabinet-unit")
    other_root = plant.item("other-root", designation="X1", unit=unit)
    board = plant.item("board", part=board_part, designation="A1", unit=unit)
    relay = plant.item("relay", parent=board, designation="K1", unit=unit)
    coil_fn = plant.function(relay, "coil", kind=FunctionKind.COIL)
    plain_item = plant.item("plain", designation="K2")
    plain_fn = plant.function(plain_item, "coil")
    model = plant.model()
    assert model.tables["item"][other_root] is not None
    result = schematic_functions(model)
    assert coil_fn not in result
    assert result == (plain_fn,)


def test_is_sole_unit_root_true_when_item_is_the_only_root_of_its_unit() -> None:
    plant = Plant()
    unit = plant.unit("solo-unit")
    board = plant.item("board", designation="A1", unit=unit)
    plant.item("child", parent=board, designation="R1", unit=unit)
    model = plant.model()
    assert is_sole_unit_root(model, board) is True


def test_is_sole_unit_root_false_when_another_item_also_roots_the_unit() -> None:
    plant = Plant()
    unit = plant.unit("shared-unit")
    board = plant.item("board", designation="A1", unit=unit)
    plant.item("other-root", designation="X1", unit=unit)
    model = plant.model()
    assert is_sole_unit_root(model, board) is False


def test_is_sole_unit_root_false_with_no_unit_at_all() -> None:
    plant = Plant()
    item = plant.item("plain", designation="K1")
    model = plant.model()
    assert is_sole_unit_root(model, item) is False


# -- effective_placement (model-0040, spec B1's amendment) ------------------------------


def test_effective_placement_reads_the_items_own_placement() -> None:
    plant = Plant()
    item = plant.item("k1", designation="K1")
    node = make_node("c1", None)
    plant.add(node, make_placement("p1", item, node.id))
    model = plant.model()
    assert effective_placement(model, item, Aspect.LOCATION) == node.id


def test_effective_placement_falls_back_to_the_nearest_placed_ancestor() -> None:
    """A board connector nested under a placed board, with no placement of its own, reads
    the board's placement -- the gap B1's spec named, now closed."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    connector = plant.item("conn", parent=board, designation="X1")
    node = make_node("c1", None)
    plant.add(node, make_placement("p-board", board, node.id))
    model = plant.model()
    assert effective_placement(model, connector, Aspect.LOCATION) == node.id


def test_effective_placement_is_none_when_neither_the_item_nor_an_ancestor_is_placed() -> None:
    plant = Plant()
    board = plant.item("board", designation="A1")
    connector = plant.item("conn", parent=board, designation="X1")
    model = plant.model()
    assert effective_placement(model, connector, Aspect.LOCATION) is None


def test_effective_placement_an_id_that_is_not_an_item_is_a_schema_error() -> None:
    plant = Plant()
    model = plant.model()
    absent = make_id(Item, ("nowhere",))
    with pytest.raises(SchemaError, match="is not a item") as excinfo:
        effective_placement(model, absent, Aspect.LOCATION)
    assert excinfo.value.record_id == absent


def _item_only_placement(model, item, aspect):
    """The pre-model-0040 behaviour: the item's own placement only, no ancestor walk."""
    idx = build_indexes(model)
    nodes = aspect_nodes(model)
    all_placements = placements(model)
    found = sorted(
        placement_id
        for placement_id in idx.placements_by_item.get(item, ())
        if nodes[all_placements[placement_id].node].aspect is aspect
    )
    return all_placements[found[0]].node if found else None


def test_effective_placement_can_fail_a_board_connector_with_no_placement_of_its_own() -> None:
    """Can-fail: the pre-model-0040 item-only lookup misses the board's placement entirely
    (`_item_only_placement`, a scratch stand-in for the deleted private logic, not a
    monkeypatch of model code); `effective_placement` is the fix."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    connector = plant.item("conn", parent=board, designation="X1")
    node = make_node("c1", None)
    plant.add(node, make_placement("p-board", board, node.id))
    model = plant.model()
    assert _item_only_placement(model, connector, Aspect.LOCATION) is None
    assert effective_placement(model, connector, Aspect.LOCATION) == node.id
