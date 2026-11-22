"""What net closure joins and what it leaves apart."""

from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.derive.facts import closure as vocab_closure
from fransys_model.elecdef import LinkKind
from fransys_model.kernel import make_id
from fransys_model.vocab import FunctionKind
lazy from fransys_model.vocab.core import Item, Port

if TYPE_CHECKING:
    from fransys_model.kernel import Id


def _fuse(kind: LinkKind, *names: str, function_kind: FunctionKind = FunctionKind.GENERIC) -> tuple[Plant, dict[str, tuple[Id[Port], Id[Port]]]]:
    """A part whose two pins are linked as `kind`, and one instance of it per name."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, kind)
    ports = {}
    for name in names:
        function = plant.function(plant.item(name, part=part.id), "fn", template=template.id, kind=function_kind)
        ports[name] = (
            plant.port(function, "1", template=first.id),
            plant.port(function, "2", template=second.id),
        )
    return plant, ports


def test_condition_needs_nothing_for_a_both_link() -> None:
    """A switched link of a non-contact function is `link_state` `"both"`: no condition."""
    plant, _ports = _fuse(LinkKind.SWITCHED, "g1")
    model = plant.model()
    (group,) = vocab_closure.link_groups(model, lambda role: role.switched)
    assert vocab_closure._condition(model, group) == vocab_closure._ALWAYS


def test_only_a_conductive_link_joins_the_physical_net() -> None:
    """A conductive link makes its two pins one net; a switched or protective one leaves two."""
    for kind, joined in (
        (LinkKind.CONDUCTIVE, True),
        (LinkKind.SWITCHED, False),
        (LinkKind.PROTECTIVE, False),
    ):
        plant, ports = _fuse(kind, "g1")
        model = plant.model()
        first, second = ports["g1"]
        net = vocab_closure.net_of(model, first)
        assert net is not None
        assert (second in net.ports) is joined


# ---- the shape of the result -------------------------------------------------------------


# ---- the cache ---------------------------------------------------------------------------


def test_link_groups_is_a_derive_name_that_names_the_linked_ports() -> None:
    """`derive.link_groups` yields, per item, the ports of a link the selector accepts."""
    from fransys_model import derive

    plant, ports = _fuse(LinkKind.CONDUCTIVE, "g1")
    model = plant.model()
    (group,) = derive.link_groups(model, lambda role: role.joins_net)
    assert isinstance(group, derive.LinkGroup)
    assert set(group.ports) == set(ports["g1"])
    assert not list(derive.link_groups(model, lambda role: role.switched))


def test_required_groups_lists_each_conductor_each_conductive_link_and_each_mate_join() -> None:
    """The physical nets close over `required_groups`; a dropped source splits a net."""
    from fransys_model import derive

    plant, ports = _fuse(LinkKind.CONDUCTIVE, "g1")
    other = plant.pin("plug", "J1", "1")
    mated = plant.pin("socket", "J1", "1")
    plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
    plant.wire(ports["g1"][0], other, key="w1")
    groups = {frozenset(g) for g in derive.required_groups(plant.model())}
    assert groups == {frozenset(ports["g1"]), frozenset((ports["g1"][0], other)), frozenset((other, mated))}


def test_drawn_groups_leave_out_a_bridge_that_the_physical_nets_keep() -> None:
    """model-0402: a JUMPER joins the physical net, never the drawn groups; a wire and a mate join both."""
    from fransys_model import derive
    from fransys_model.vocab.enums import ConductorKind

    plant = Plant()
    one, two, three = (plant.pin("plug", "J1", name) for name in ("1", "2", "3"))
    plant.wire(one, two, key="a-jumper", kind=ConductorKind.JUMPER)
    plant.wire(two, three, key="b-wire")
    model = plant.model()
    assert {frozenset(g) for g in derive.drawn_groups(model)} == {frozenset((two, three))}
    assert {frozenset(g) for g in derive.required_groups(model)} == {frozenset((one, two)), frozenset((two, three))}
    assert [net.ports for net in derive.physical_nets(model)] == [tuple(sorted((one, two, three)))]
    drawn = derive.drawn_net_of(model, two)
    assert drawn is not None
    assert drawn.ports == tuple(sorted((two, three)))  # R1625: the bridge leaves `one` out of the drawn net


def test_drawn_groups_leave_out_a_group_no_drawn_conductor_ends_in() -> None:
    """KI-732, NET-END-THROUGH: a pole's link group with no conductor at its pins draws no wire; one wired pin makes it a through net."""
    from fransys_model import derive

    plant, ports = _fuse(LinkKind.CONDUCTIVE, "g1")
    model = plant.model()
    assert {frozenset(g) for g in derive.required_groups(model)} == {frozenset(ports["g1"])}
    assert derive.drawn_groups(model) == ()

    wired, pins = _fuse(LinkKind.CONDUCTIVE, "g1")
    wired.wire(pins["g1"][0], wired.pin("plug", "J1", "1"), key="w1")
    assert frozenset(pins["g1"]) in {frozenset(g) for g in derive.drawn_groups(wired.model())}


def _board_with_two_parts(*, sole_root: bool) -> tuple[Plant, Id[Port], Id[Port]]:
    """A board with two parts under it, alone in its unit or beside another root item; one pin on each part."""
    plant = Plant()
    unit = plant.unit("u1")
    board = plant.item("a1", part=plant.board_part(), unit=unit)
    if not sole_root:
        plant.item("k1", unit=unit)
    pins = []
    for key in ("j1", "h1"):
        item = plant.item(key, parent=board, unit=unit)
        pins.append(plant.port(plant.function(item, "f"), "1"))
    return plant, pins[0], pins[1]


def test_a_sole_root_boards_declared_net_is_required_but_not_a_declared_net_off_a_board() -> None:
    """R1195: a net on a board that is its unit's only root device is its traces, a required group; a net elsewhere is intent."""
    from fransys_model import derive

    plant, one, two = _board_with_two_parts(sole_root=True)
    plant.net("sig", (one, two))
    model = plant.model()
    assert {frozenset(g) for g in derive.required_groups(model)} == {frozenset((one, two))}
    assert {frozenset(g) for g in derive.drawn_groups(model)} == {frozenset((one, two))}  # R2620: a trace has no conductor and is drawn

    loose, three, four = _board_with_two_parts(sole_root=False)
    loose.net("sig", (three, four))
    assert derive.required_groups(loose.model()) == ()


def test_board_of_ports_is_the_innermost_whole_unit_board_holding_every_port() -> None:
    """R2484: a sole-root board holds ports under it; a board beside another root, or a port off the board, gives `None`."""
    from fransys_model.derive.facts.closure import board_of_ports

    plant, one, two = _board_with_two_parts(sole_root=True)
    model = plant.model()
    assert board_of_ports(model, (one, two)) == make_id(Item, ("a1",))
    loose, three, four = _board_with_two_parts(sole_root=False)
    assert board_of_ports(loose.model(), (three, four)) is None
    outside = plant.pin("x", "f", "1")
    assert board_of_ports(plant.model(), (one, outside)) is None


def test_port_joins_is_on_the_derive_door_and_gives_a_header_join() -> None:
    from dataclasses import replace

    from fransys_model import derive

    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.records[plant.records.index(first)] = replace(first, joins=second.id)
    function = plant.function(plant.item("K1", part=part.id), "fn", template=template.id)
    header = plant.port(function, "1", template=first.id)
    target = plant.port(function, "2", template=second.id)
    assert derive.port_joins(plant.model()) == ((header, target),)


def test_a_terminal_functions_conductive_link_joins_its_ports_in_the_drawn_net_and_a_poles_does_not() -> None:
    """KI-1067: a panel receptacle's terminal function draws as one node, so a wire at one port is a wire at both."""
    from fransys_model import derive

    for kind, joined in ((FunctionKind.TERMINAL, True), (FunctionKind.GENERIC, False)):
        plant, ports = _fuse(LinkKind.CONDUCTIVE, "g1", function_kind=kind)
        plant.wire(ports["g1"][0], plant.pin("plug", "J1", "1"), key="w1")
        model = plant.model()
        first, second = (derive.drawn_net_of(model, p) for p in ports["g1"])
        assert (first == second) is joined, kind


def test_drawn_groups_come_in_print_order_under_every_id_salt() -> None:
    """A group's ports and the groups follow the printed designations, never an Id (a salt must not move a cut's pieces)."""
    from fransys_model import derive
    from fransys_model.kernel import id_namespace
    from fransys_model.vocab.tables import ports

    seen = []
    for salt in ("a", "b", "c", "d", "e"):
        with id_namespace(salt):
            plant = Plant()
            pins = {name: plant.pin("plug", "J1", name) for name in "12345678"}
            for key, (one, two) in {"w1": "21", "w2": "43", "w3": "65", "w4": "87"}.items():
                plant.wire(pins[one], pins[two], key=key)
            model = plant.model()
            seen.append([[ports(model)[p].name for p in g] for g in derive.drawn_groups(model)])
    assert seen == [[["1", "2"], ["3", "4"], ["5", "6"], ["7", "8"]]] * 5
