"""WP12 tests: every finding code of `check_connectivity`, firing and not firing
(design/connectivity.md)."""

import dataclasses
import re
from typing import Any

from plant import Plant

from fransys_model.kernel import Finding, Id, Model, Severity, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import LinkKind
from fransys_model.vocab.validators.connectivity import (
    CONDUCTOR_ON_UNINSTALLED,
    NET_POTENTIAL_CONFLICT,
    NET_SHORTED,
    NET_UNREALISED,
    PORT_UNCONNECTED,
    check_connectivity,
)


def _of(plant: Plant, code: str) -> list[Finding]:
    return [f for f in check_connectivity(plant.model()) if f.code == code]


def _sorted(*ids: Id[Any]) -> tuple[Id[Any], ...]:
    return tuple(sorted(ids))


# ---- NET_UNREALISED -----------------------------------------------------------------------


def test_a_net_split_in_two_is_one_warning_about_the_net() -> None:
    """Three declared ports, two of them wired: two physical nets."""
    plant = Plant()
    a, b, c = (plant.pin(name, "f", "1") for name in "abc")
    plant.wire(a, b, key="w")
    net = plant.net("supply", (a, b, c), name="24V")
    (finding,) = _of(plant, NET_UNREALISED)
    assert (finding.severity, finding.subjects) == (Severity.WARNING, (net,))
    assert "24V" in finding.message
    assert "2 physical nets" in finding.message


def test_a_net_with_no_name_is_called_by_its_key() -> None:
    """The message names things a person wrote."""
    plant = Plant()
    a, b = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    plant.net("supply-key", (a, b))
    (finding,) = _of(plant, NET_UNREALISED)
    assert "supply-key" in finding.message


def test_a_net_of_one_port_or_none_is_never_unrealised() -> None:
    """Nothing to join."""
    plant = Plant()
    only = plant.pin("a", "f", "1")
    plant.net("one", (only,))
    plant.net("none", ())
    assert _of(plant, NET_UNREALISED) == []


def test_a_net_joined_through_a_link_or_a_mate_is_realised() -> None:
    """Closure, not just conductors, realises a net."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, LinkKind.CONDUCTIVE)
    function = plant.function(plant.item("f1", part=part.id), "fn", template=template.id)
    one = plant.port(function, "1", template=first.id)
    two = plant.port(function, "2", template=second.id)
    plant.net("through-fuse", (one, two))
    board, harness = plant.pin("board", "j1", "1"), plant.pin("harness", "p1", "1")
    plant.mate(plant.function_id("board", "j1"), plant.function_id("harness", "p1"))
    plant.net("through-mate", (board, harness))
    assert _of(plant, NET_UNREALISED) == []


# ---- board realisation --------------------------------------------------------------------


def _board_plant() -> tuple[Plant, Id[Item]]:
    plant = Plant()
    board = plant.item("board", part=plant.board_part())
    return plant, board


def test_ports_under_a_board_realise_their_net() -> None:
    """Children of a `pcb`-facet item need no conductors."""
    plant, board = _board_plant()
    ports = [
        plant.port(plant.function(plant.item(name, parent=board), "f"), "1")
        for name in ("r1", "r2")
    ]
    plant.net("on-board", tuple(ports))
    assert _of(plant, NET_UNREALISED) == []


def test_the_board_item_itself_counts_as_its_own_ancestor() -> None:
    """A board-edge connector is a function of the board: its port and a child's are one net."""
    plant, board = _board_plant()
    edge = plant.port(plant.function(board, "j1"), "1")
    child = plant.port(plant.function(plant.item("r1", parent=board), "f"), "1")
    plant.net("edge-to-r1", (edge, child))
    assert _of(plant, NET_UNREALISED) == []


def test_a_port_off_the_board_leaves_the_net_unrealised() -> None:
    """One port outside the board: not board-realised."""
    plant, board = _board_plant()
    inside = plant.port(plant.function(plant.item("r1", parent=board), "f"), "1")
    outside = plant.pin("cabinet-part", "f", "1")
    plant.net("half-on-board", (inside, outside))
    assert len(_of(plant, NET_UNREALISED)) == 1


def test_two_boards_do_not_realise_a_net_between_them() -> None:
    """The ancestor must be one item: the intersection over the ports is empty."""
    plant = Plant()
    part = plant.board_part()
    first, second = plant.item("board-1", part=part), plant.item("board-2", part=part)
    a = plant.port(plant.function(plant.item("r1", parent=first), "f"), "1")
    b = plant.port(plant.function(plant.item("r2", parent=second), "f"), "1")
    plant.net("across-boards", (a, b))
    assert len(_of(plant, NET_UNREALISED)) == 1


def test_an_inner_board_inside_an_outer_one_realises_a_net_on_the_outer() -> None:
    """Nested boards: the outer is a common ancestor even where the inner is not."""
    plant = Plant()
    part = plant.board_part()
    outer = plant.item("outer", part=part)
    inner = plant.item("inner", part=part, parent=outer)
    a = plant.port(plant.function(plant.item("r1", parent=inner), "f"), "1")
    b = plant.port(plant.function(plant.item("r2", parent=outer), "f"), "1")
    plant.net("nested", (a, b))
    assert _of(plant, NET_UNREALISED) == []


def test_an_item_whose_part_has_no_pcb_facet_is_not_a_board() -> None:
    """Only the facet makes a board."""
    plant = Plant()
    part, *_ = plant.relay_part()
    holder = plant.item("holder", part=part.id)
    a = plant.port(plant.function(plant.item("r1", parent=holder), "f"), "1")
    b = plant.port(plant.function(plant.item("r2", parent=holder), "f"), "1")
    plant.net("not-a-board", (a, b))
    assert len(_of(plant, NET_UNREALISED)) == 1


def test_a_parent_cycle_ends_the_walk_without_a_finding_about_it() -> None:
    """`CONTAINMENT_CYCLE` is the structure validator's; here the walk must terminate."""
    plant = Plant()
    first = plant.item("first", parent=make_id(Item, ("second",)))
    second = plant.item("second", parent=first)
    a = plant.port(plant.function(first, "f"), "1")
    b = plant.port(plant.function(second, "f"), "1")
    plant.net("in-a-cycle", (a, b))
    assert len(_of(plant, NET_UNREALISED)) == 1


def test_board_realisation_suppresses_only_net_unrealised() -> None:
    """A board net that is also shorted to another net is still shorted."""
    plant, board = _board_plant()
    a = plant.port(plant.function(plant.item("r1", parent=board), "f"), "1")
    b = plant.port(plant.function(plant.item("r2", parent=board), "f"), "1")
    other = plant.pin("cabinet", "f", "1")
    plant.net("board-net", (a, b))
    plant.net("cabinet-net", (other,))
    plant.wire(a, other, key="bridge")
    assert _of(plant, NET_UNREALISED) == []
    assert len(_of(plant, NET_SHORTED)) == 1


# ---- NET_SHORTED and NET_POTENTIAL_CONFLICT -----------------------------------------------


def test_two_nets_joined_by_a_wire_are_one_error_naming_both() -> None:
    """One finding per physical net, subjects the declared nets."""
    plant = Plant()
    a, b, c, d = (plant.pin(name, "f", "1") for name in "abcd")
    first = plant.net("net-a", (a, b), name="A")
    second = plant.net("net-b", (c, d), name="B")
    plant.wire(a, b, key="w1")
    plant.wire(c, d, key="w2")
    plant.wire(b, c, key="bridge")
    (finding,) = _of(plant, NET_SHORTED)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _sorted(first, second))
    assert "A, B" in finding.message


def test_three_nets_in_one_physical_net_are_one_finding_not_three() -> None:
    """The finding is about the physical net."""
    plant = Plant()
    ports = [plant.pin(name, "f", "1") for name in "abc"]
    nets = [plant.net(f"n{i}", (port,)) for i, port in enumerate(ports)]
    plant.wire(ports[0], ports[1], key="w1")
    plant.wire(ports[1], ports[2], key="w2")
    (finding,) = _of(plant, NET_SHORTED)
    assert finding.subjects == _sorted(*nets)


def test_two_separate_shorts_are_two_findings() -> None:
    """One per physical net."""
    plant = Plant()
    a, b, c, d = (plant.pin(name, "f", "1") for name in "abcd")
    for number, (x, y) in enumerate(((a, b), (c, d))):
        plant.net(f"left{number}", (x,))
        plant.net(f"right{number}", (y,))
        plant.wire(x, y, key=f"w{number}")
    assert len(_of(plant, NET_SHORTED)) == 2


def test_a_port_listed_in_two_nets_is_a_short_without_any_conductor() -> None:
    """Both declarations claim one port: their nets are one physical net."""
    plant = Plant()
    shared, other = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    plant.net("first", (shared,))
    plant.net("second", (shared, other))
    assert len(_of(plant, NET_SHORTED)) == 1


def test_a_net_alone_in_its_physical_net_is_not_shorted() -> None:
    """One declared net per physical net is the healthy case."""
    plant = Plant()
    a, b = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    plant.net("n", (a, b))
    plant.wire(a, b, key="w")
    assert _of(plant, NET_SHORTED) == []


def _rails(plant: Plant) -> tuple[Any, ...]:
    ports = [plant.pin(name, "f", "1") for name in "abcdef"]
    return tuple(ports)


def test_different_potentials_in_one_physical_net_are_a_conflict_naming_the_rails() -> None:
    """24V bridged to 0V, and a plain net on the same wire: only the rails are subjects."""
    plant = Plant()
    a, b, c = _rails(plant)[:3]
    plus = plant.net("plus", (a,), potential="24V")
    minus = plant.net("minus", (b,), potential="0V")
    plant.net("plain", (c,))
    plant.wire(a, b, key="w1")
    plant.wire(b, c, key="w2")
    (finding,) = _of(plant, NET_POTENTIAL_CONFLICT)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _sorted(plus, minus))
    assert "0V, 24V" in finding.message
    assert len(_of(plant, NET_SHORTED)) == 1


def test_equal_potentials_or_a_missing_one_are_no_conflict() -> None:
    """Two 24V nets bridged, and a 24V net bridged to a plain one: shorted, not a conflict."""
    plant = Plant()
    a, b, c, d = _rails(plant)[:4]
    plant.net("plus-1", (a,), potential="24V")
    plant.net("plus-2", (b,), potential="24V")
    plant.net("plus-3", (c,), potential="24V")
    plant.net("plain", (d,))
    plant.wire(a, b, key="w1")
    plant.wire(c, d, key="w2")
    assert _of(plant, NET_POTENTIAL_CONFLICT) == []
    assert len(_of(plant, NET_SHORTED)) == 2


# ---- PORT_UNCONNECTED ---------------------------------------------------------------------


def test_a_port_with_nothing_is_an_info_about_it() -> None:
    """A spare contact is normal, hence `INFO`."""
    plant = Plant()
    lone = plant.pin("a", "f", "1")
    (finding,) = _of(plant, PORT_UNCONNECTED)
    assert (finding.severity, finding.subjects) == (Severity.INFO, (lone,))


def test_a_net_a_conductor_or_a_mate_each_connect_a_port() -> None:
    """Any one of the three is enough; a pin on a mated connector needs a partner of its name."""
    plant = Plant()
    in_net = plant.pin("a", "f", "1")
    plant.net("n", (in_net,))
    wired, other = plant.pin("b", "f", "1"), plant.pin("c", "f", "1")
    plant.wire(wired, other, key="w")
    plant.pin("d", "j", "1")
    plant.pin("e", "j", "1")
    plant.pin("e", "j", "9")
    plant.mate(plant.function_id("d", "j"), plant.function_id("e", "j"))
    unconnected = {finding.subjects[0] for finding in _of(plant, PORT_UNCONNECTED)}
    assert unconnected == {make_id(Port, ("e", "j", "9"))}


def test_a_conductive_link_alone_does_not_connect_a_port() -> None:
    """The fuse's own link is inside the part: nothing outside is attached."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, LinkKind.CONDUCTIVE)
    function = plant.function(plant.item("f1", part=part.id), "fn", template=template.id)
    one = plant.port(function, "1", template=first.id)
    two = plant.port(function, "2", template=second.id)
    assert {f.subjects[0] for f in _of(plant, PORT_UNCONNECTED)} == {one, two}


# ---- CONDUCTOR_ON_UNINSTALLED -------------------------------------------------------------


def test_a_conductor_on_a_pulled_item_is_a_warning_naming_the_item() -> None:
    """Subjects: the conductor and the uninstalled item."""
    plant = Plant()
    pulled = plant.item("pulled", installed=False)
    a = plant.port(plant.function(pulled, "f"), "1")
    b = plant.pin("b", "f", "1")
    wire = plant.wire(a, b, key="w")
    (finding,) = _of(plant, CONDUCTOR_ON_UNINSTALLED)
    assert (finding.severity, finding.subjects) == (Severity.WARNING, _sorted(wire, pulled))
    assert "pulled" in finding.message


def test_two_pulled_items_on_one_conductor_are_one_finding() -> None:
    """One per conductor, both items among the subjects."""
    plant = Plant()
    first, second = plant.item("p1", installed=False), plant.item("p2", installed=False)
    a = plant.port(plant.function(first, "f"), "1")
    b = plant.port(plant.function(second, "f"), "1")
    wire = plant.wire(a, b, key="w")
    (finding,) = _of(plant, CONDUCTOR_ON_UNINSTALLED)
    assert finding.subjects == _sorted(wire, first, second)


def test_both_ends_on_one_pulled_item_name_it_once() -> None:
    """A jumper inside a pulled item."""
    plant = Plant()
    pulled = plant.item("pulled", installed=False)
    function = plant.function(pulled, "f")
    a, b = plant.port(function, "1"), plant.port(function, "2")
    wire = plant.wire(a, b, key="w")
    (finding,) = _of(plant, CONDUCTOR_ON_UNINSTALLED)
    assert finding.subjects == _sorted(wire, pulled)


def test_installed_items_and_uninstalled_ones_off_the_conductor_are_no_finding() -> None:
    """Only a landing counts; a pulled item with no wire is not this validator's business."""
    plant = Plant()
    plant.port(plant.function(plant.item("pulled", installed=False), "f"), "1")
    a, b = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    plant.wire(a, b, key="w")
    assert _of(plant, CONDUCTOR_ON_UNINSTALLED) == []


# ---- the shape of the result --------------------------------------------------------------


def _mixed() -> Plant:
    plant = Plant()
    a, b, c, d, e = (plant.pin(name, "f", "1") for name in "abcde")
    plant.net("n1", (a, b), potential="24V")
    plant.net("n2", (c,), potential="0V")
    plant.wire(b, c, key="bridge")
    plant.wire(a, d, key="w")
    plant.item("pulled", installed=False)
    plant.wire(plant.port(plant.function(make_id(Item, ("pulled",)), "f"), "1"), e, key="p")
    return plant


def test_findings_are_sorted_by_code_subjects_and_message() -> None:
    """No order of a table leaks out."""
    findings = check_connectivity(_mixed().model())
    assert len({f.code for f in findings}) >= 4
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))


def test_the_findings_do_not_depend_on_the_order_of_a_models_tables() -> None:
    """Tables backwards: the same findings, in the same order."""
    model = _mixed().model()
    backwards: Model = dataclasses.replace(
        model,
        digest="reversed-tables-test-connectivity-findings",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert check_connectivity(backwards) == check_connectivity(model)


def test_no_message_prints_an_id() -> None:
    """Ids are opaque: messages name keys and net names."""
    for finding in check_connectivity(_mixed().model()):
        assert finding.message
        assert not re.search(r"[0-9a-f]{32}", finding.message)


def test_an_empty_model_has_no_finding() -> None:
    """Nothing declared, nothing to compare."""
    assert check_connectivity(Plant().model()) == ()
