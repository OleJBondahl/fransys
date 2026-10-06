"""RATINGS-1 step 1, model-0075: `port_rails`, the rail closure (spec model-review Q2, Q3).

Built from `examples/demo-parts` only. A rail spreads from its declared nets through conductors,
mates, `conductive`, `switched` (every contact closed) and `protective` links (a fuse closed in
service), and never enters another declared net.

Can-fail probes, each one Edit in `vocab/closure.py`, run and undone: `_RAIL_LINKS` without
`SWITCHED` fails the contactor and motor tests; `_blocks` returning `False` fails the reversing
starter test; dropping `net.potential in supplied` from `_rails` fails the unsupplied
potential test.
"""

import dataclasses
import random
from typing import TYPE_CHECKING

import fransys_parts
import pytest
from fransys_author import Design, Port

from fransys_model.derive import PhysicalNet, net_of, physical_nets, port_rails
from fransys_model.kernel import Id, Model, evolve, freeze, merge
from fransys_model.vocab import LinkKind, closure
from fransys_model.vocab import Port as ModelPort
from fransys_model.vocab.tables import conductors, internal_links, ports

if TYPE_CHECKING:
    from collections.abc import Callable

_RAILS = {
    "L1": ("230", 0),
    "L2": ("230", 120),
    "L3": ("230", 240),
    "N": ("0", None),
}


def _design() -> tuple[Design, Callable[[Port, Port], None]]:
    """A design over the demo parts with the 400 V supply declared, and a wire maker."""
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("400V", current="ac", rails=_RAILS)
    return d, d.wiring(colour="BK", gauge="1.5")


def _freeze(d: Design) -> Model:
    return freeze(merge(fransys_parts.load("demo_parts"), d.draft()))


def _rails(model: Model, port: Port) -> list[str]:
    return sorted(port_rails(model, port.id))


def _line_motor(*, named: bool = False, potential: str | None = None) -> tuple[Model, dict]:
    """L1, L2, L3 into contactor Q1 (1, 3, 5), then one MCB per phase (the overload stand-in),
    then the motor's U, V, W. `named` puts each MCB output and motor pole on a declared net of
    `potential` (`None`: an ordinary power net)."""
    d, wire = _design()
    q1 = d.item("DEMO-CTR-3P-24", name="q1")
    fuses = [d.item("DEMO-MCB-C6", name=f"f{n}") for n in (1, 2, 3)]
    m1 = d.item("DEMO-MOTOR-4KW", name="m1")
    main = q1.fn("main")
    for rail, pole in (("L1", "1"), ("L2", "3"), ("L3", "5")):
        d.net(rail, main[pole], cls="power", potential=rail)
    for out, fuse, motor_pole in (("2", fuses[0], "U"), ("4", fuses[1], "V"), ("6", fuses[2], "W")):
        wire(main[out], fuse["1"])
        wire(fuse["2"], m1[motor_pole])
        if named:
            d.net(f"M1-{motor_pole}", fuse["2"], m1[motor_pole], cls="power", potential=potential)
    return _freeze(d), {"q1": q1, "f": fuses, "m1": m1}


def _changeover() -> tuple[Model, dict]:
    """A relay contact `co_1` whose 12 is on the declared L1 net and 14 on the declared L2 net."""
    d, _ = _design()
    k1 = d.item("DEMO-RLY-2CO-24", name="k1")
    contact = k1.fn("co_1")
    d.net("L1", contact["12"], cls="power", potential="L1")
    d.net("L2", contact["14"], cls="power", potential="L2")
    return _freeze(d), {"contact": contact}


def _reversing_starter(*, reverse: bool = False) -> tuple[Model, dict]:
    """K1: L1 to U, L3 to W; K2: L1 to W, L3 to U; the motor's V on L2 through both; a lamp on
    L1 and N. `reverse` declares everything after the items in the opposite order."""
    d, wire = _design()
    names = [
        ("k1", "DEMO-CTR-3P-24"),
        ("k2", "DEMO-CTR-3P-24"),
        ("m1", "DEMO-MOTOR-4KW"),
        ("h1", "DEMO-LAMP-24"),
    ]
    items = {name: d.item(mpn, name=name) for name, mpn in (reversed(names) if reverse else names)}
    k1, k2 = items["k1"].fn("main"), items["k2"].fn("main")
    m1, h1 = items["m1"], items["h1"]
    steps: list[Callable[[], None]] = [
        lambda: d.net("L1", k1["1"], k2["1"], h1["1"], cls="power", potential="L1"),
        lambda: d.net("L2", k1["3"], k2["3"], cls="power", potential="L2"),
        lambda: d.net("L3", k1["5"], k2["5"], cls="power", potential="L3"),
        lambda: d.net("N", h1["2"], cls="power", potential="N"),
        lambda: wire(k1["2"], m1["U"]),
        lambda: wire(k1["4"], m1["V"]),
        lambda: wire(k1["6"], m1["W"]),
        lambda: wire(k2["2"], m1["W"]),
        lambda: wire(k2["4"], m1["V"]),
        lambda: wire(k2["6"], m1["U"]),
    ]
    for step in reversed(steps) if reverse else steps:
        step()
    return _freeze(d), {"k1": k1, "k2": k2, "m1": m1, "h1": h1}


def test_a_motor_after_a_contactor_and_mcbs_carries_the_rails_through_the_switched_links() -> None:
    model, p = _line_motor()
    main, m1 = p["q1"].fn("main"), p["m1"]
    assert [_rails(model, main[pole]) for pole in "135"] == [["L1"], ["L2"], ["L3"]]
    assert [_rails(model, main[pole]) for pole in "246"] == [["L1"], ["L2"], ["L3"]]
    assert [_rails(model, m1[pole]) for pole in ("U", "V", "W")] == [["L1"], ["L2"], ["L3"]]
    assert _rails(model, m1["PE"]) == []


def test_removing_the_switched_links_leaves_the_motor_without_a_rail() -> None:
    """The spec's probe, by `evolve`: the contactor's `switched` links are gone."""
    model, p = _line_motor()
    switched = [i for i, link in internal_links(model).items() if link.kind is LinkKind.SWITCHED]
    assert switched
    stripped = evolve(model, remove=switched)
    m1 = p["m1"]
    assert [_rails(stripped, m1[pole]) for pole in ("U", "V", "W", "PE")] == [[], [], [], []]
    assert _rails(stripped, p["q1"].fn("main")["1"]) == ["L1"]
    assert _rails(stripped, p["q1"].fn("main")["2"]) == []


def test_a_changeovers_common_keeps_both_rails_and_its_throws_only_their_own() -> None:
    model, p = _changeover()
    contact = p["contact"]
    assert _rails(model, contact["11"]) == ["L1", "L2"]
    assert _rails(model, contact["12"]) == ["L1"]
    assert _rails(model, contact["14"]) == ["L2"]


def test_a_part_that_declares_no_link_carries_no_rail_through_it() -> None:
    d, wire = _design()
    lamp = d.item("DEMO-LAMP-24", name="h1")
    motor = d.item("DEMO-MOTOR-4KW", name="m1")
    d.net("L1", lamp["1"], cls="power", potential="L1")
    wire(lamp["2"], motor["U"])
    model = _freeze(d)
    assert _rails(model, lamp["1"]) == ["L1"]
    assert _rails(model, lamp["2"]) == []
    assert [_rails(model, motor[pole]) for pole in ("U", "V", "W", "PE")] == [[], [], [], []]


def test_a_potential_in_no_declared_supply_is_not_a_rail() -> None:
    d, wire = _design()
    lamp = d.item("DEMO-LAMP-24", name="h1")
    fuse = d.item("DEMO-MCB-C6", name="f1")
    d.net("X", lamp["1"], cls="power", potential="X9")
    d.net("L1", lamp["2"], cls="power", potential="L1")
    wire(lamp["1"], fuse["1"])
    model = _freeze(d)
    assert [_rails(model, port) for port in (lamp["1"], fuse["1"], fuse["2"])] == [[], [], []]
    assert _rails(model, lamp["2"]) == ["L1"]


def test_a_rail_never_enters_another_declared_net_in_a_reversing_starter() -> None:
    model, p = _reversing_starter()
    k1, k2, m1, h1 = p["k1"], p["k2"], p["m1"], p["h1"]
    assert [_rails(model, k1[pole]) for pole in "135"] == [["L1"], ["L2"], ["L3"]]
    assert [_rails(model, k2[pole]) for pole in "135"] == [["L1"], ["L2"], ["L3"]]
    assert [_rails(model, h1[pole]) for pole in "12"] == [["L1"], ["N"]]
    assert [_rails(model, m1[pole]) for pole in ("U", "V", "W")] == [
        ["L1", "L3"],
        ["L2"],
        ["L1", "L3"],
    ]
    assert _rails(model, k1["2"]) == ["L1", "L3"]


def _shuffled(model: Model, seed: int) -> Model:
    """The same model, same digest, with every table in another insertion order."""
    rng = random.Random(seed)  # noqa: S311 -- a reproducible shuffle, not cryptography

    def shuffled(mapping):
        pairs = list(mapping.items())
        rng.shuffle(pairs)
        return type(mapping)(pairs)

    tables = type(model.tables)((kind, shuffled(t)) for kind, t in shuffled(model.tables).items())
    return dataclasses.replace(model, tables=tables, hashes=shuffled(model.hashes))


def _all_rails(model: Model) -> dict[Id[ModelPort], frozenset[str]]:
    closure._rails.cache_clear()  # the cache answers by digest, so twins would share it
    return {port: port_rails(model, port) for port in ports(model)}


def test_the_rails_do_not_depend_on_authoring_order_or_table_order() -> None:
    forward, _ = _reversing_starter()
    backward, _ = _reversing_starter(reverse=True)
    expected = _all_rails(forward)
    assert any(len(rails) == 2 for rails in expected.values())
    assert _all_rails(backward) == expected
    for seed in range(3):
        twin = _shuffled(forward, seed)
        assert list(conductors(twin)) != list(conductors(forward))
        assert _all_rails(twin) == expected


def test_physical_nets_join_a_conductive_link_and_never_a_switched_or_protective_one() -> None:
    """After `port_rails` ran, a recomputed `physical_nets` is the hand-stated grouping: Q1's
    pole 2 (wired to the terminal's internal port) and the terminal's two ends are one net;
    Q1's switched 1 to 2 and F1's protective 1 to 2 are not."""
    d, wire = _design()
    q1 = d.item("DEMO-CTR-3P-24", name="q1")
    f1 = d.item("DEMO-MCB-C6", name="f1")
    x1 = d.item("DEMO-TB-2.5", name="x1").fn("terminal")
    d.net("L1", q1.fn("main")["1"], cls="power", potential="L1")
    wire(q1.fn("main")["2"], x1["internal"])
    wire(x1["external"], f1["1"])
    model = _freeze(d)
    assert _all_rails(model)
    closure._closure.cache_clear()
    joined = {q1.fn("main")["2"].id, x1["internal"].id, x1["external"].id, f1["1"].id}
    expected = {frozenset(joined)} | {
        frozenset({port}) for port in ports(model) if port not in joined
    }
    assert {frozenset(net.ports) for net in physical_nets(model)} == expected
    assert len(expected) == len(ports(model)) - 3
    assert net_of(model, q1.fn("main")["1"].id) == PhysicalNet(ports=(q1.fn("main")["1"].id,))
    assert net_of(model, f1["2"].id) == PhysicalNet(ports=(f1["2"].id,))


def test_a_mate_carries_a_rail_into_the_mated_connector_by_port_name() -> None:
    d, _ = _design()
    c1 = d.item("DEMO-CONN-2P", name="c1")
    c2 = d.item("DEMO-CONN-2P", name="c2")
    d.net("L1", c1["1"], cls="power", potential="L1")
    d.mate(c1, c2)
    model = _freeze(d)
    assert [_rails(model, port) for port in (c1["1"], c2["1"])] == [["L1"], ["L1"]]
    assert [_rails(model, port) for port in (c1["2"], c2["2"])] == [[], []]


def test_a_port_in_two_rail_nets_carries_both_and_neither_enters_the_others_ports() -> None:
    d, _ = _design()
    h1 = d.item("DEMO-LAMP-24", name="h1")
    h2 = d.item("DEMO-LAMP-24", name="h2")
    shared, on_l1, on_l2 = h1["1"], h2["1"], h2["2"]
    d.net("L1", shared, on_l1, cls="power", potential="L1")
    d.net("L2", shared, on_l2, cls="power", potential="L2")
    model = _freeze(d)
    assert _rails(model, shared) == ["L1", "L2"]
    assert _rails(model, on_l1) == ["L1"]
    assert _rails(model, on_l2) == ["L2"]


def test_a_wire_between_two_rail_nets_gives_every_port_on_it_both_rails() -> None:
    """model-0140: a rail's physical net is the rail's, so a wire across two is a short."""
    d, wire = _design()
    h1 = d.item("DEMO-LAMP-24", name="h1")
    h2 = d.item("DEMO-LAMP-24", name="h2")
    d.net("L1", h1["1"], cls="power", potential="L1")
    d.net("L2", h2["1"], cls="power", potential="L2")
    wire(h1["1"], h2["1"])
    model = _freeze(d)
    assert _rails(model, h1["1"]) == _rails(model, h2["1"]) == ["L1", "L2"]


def test_a_changeover_wired_to_two_supplies_keeps_each_throw_on_its_own_rail() -> None:
    """model-0140: NC wired to supply A's pin and NO to supply B's, neither listed in a net.

    The common reaches both. Before, A spread through the common to the NO port, which no
    declared net listed, so NO carried both rails (a wrong fact in a valid circuit).
    """
    d, wire = _design()
    k1, h1, h2 = (
        d.item("DEMO-RLY-2CO-24", name="k1"),
        d.item("DEMO-LAMP-24", name="h1"),
        d.item("DEMO-LAMP-24", name="h2"),
    )
    contact = k1.fn("co_1")
    d.net("L1", h1["1"], cls="power", potential="L1")
    d.net("L2", h2["1"], cls="power", potential="L2")
    wire(contact["12"], h1["1"])
    wire(contact["14"], h2["1"])
    model = _freeze(d)
    assert _rails(model, contact["12"]) == ["L1"]
    assert _rails(model, contact["14"]) == ["L2"]
    assert _rails(model, contact["11"]) == ["L1", "L2"]


@pytest.mark.parametrize("potential", [None, "X9"], ids=["no-potential", "no-supply"])
def test_a_net_that_carries_no_supplied_rail_is_transparent(potential: str | None) -> None:
    """Rule B (spec Q3, ruling 2026-09-25): only a net of another supplied rail blocks."""
    model, p = _line_motor(named=True, potential=potential)
    q1, fuses, m1 = p["q1"].fn("main"), p["f"], p["m1"]
    assert [_rails(model, m1[pole]) for pole in ("U", "V", "W")] == [["L1"], ["L2"], ["L3"]]
    assert [_rails(model, fuse["2"]) for fuse in fuses] == [["L1"], ["L2"], ["L3"]]
    assert [_rails(model, q1[pole]) for pole in "135"] == [["L1"], ["L2"], ["L3"]]


def test_a_port_not_in_the_model_carries_nothing() -> None:
    model, _ = _changeover()
    assert port_rails(model, Id(kind="port", value="0" * 32)) == frozenset()


@pytest.mark.parametrize(
    "build",
    [_line_motor, _changeover, _reversing_starter],
    ids=["motor", "changeover", "reversing"],
)
def test_the_conditional_rail_table_reaches_what_port_rails_reaches_on_the_demo_plants(
    build: Callable[[], tuple[Model, dict]],
) -> None:
    """CS4: every contact of an item moves together, so no demo path needs one item in two
    states, and the table `rail_pairs` reads holds exactly the pairs of `port_rails`."""
    model, _ = build()
    table = {port: frozenset(rails) for port, rails in closure._rail_states(model).at_port.items()}
    assert table == dict(closure._rails(model))
