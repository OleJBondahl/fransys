"""What net closure joins and what it leaves apart."""

from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.derive.facts import closure as vocab_closure
from fransys_model.elecdef import LinkKind
lazy from fransys_model.vocab.core import Port

if TYPE_CHECKING:
    from fransys_model.kernel import Id


def _fuse(kind: LinkKind, *names: str) -> tuple[Plant, dict[str, tuple[Id[Port], Id[Port]]]]:
    """A part whose two pins are linked as `kind`, and one instance of it per name."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, kind)
    ports = {}
    for name in names:
        function = plant.function(plant.item(name, part=part.id), "fn", template=template.id)
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
    assert derive.drawn_groups(model) == derive.required_groups(model)

    loose, three, four = _board_with_two_parts(sole_root=False)
    loose.net("sig", (three, four))
    assert derive.required_groups(loose.model()) == ()
