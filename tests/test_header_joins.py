"""HA4 (parts-0017): a header pin `joins` a function port, and the model reads the join as a wire.

Built through `import fransys as fr` from `examples/demo-parts` (DEMO-RELAY-MOD-2) and one
throwaway one-header part. The join puts the header pin and the function port on one physical
net, reaches the rail closure, counts as a connection, and prints the pin as `-M1-J1:1`.
"""

from typing import TYPE_CHECKING

import fransys as fr
import fransys_parts
from fransys_author import Design

from fransys_model.derive import net_of, port_designation, port_is_unused, port_rails
from fransys_model.kernel import Id, Model, freeze, merge
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_model.vocab import Port

_PORT_UNCONNECTED = "PORT_UNCONNECTED"
_ONE_HEADER = """schema = 1

[part]
mpn = "ONE-HEADER-MOD"
manufacturer = "Demo"
description = "One coil on one male header"
category = "generic"
class_code = "M"

[[function]]
name = "k1"
kind = "coil"
symbol = "operating-device"
ports = [
    { name = "A1", role = "generic", symbol_port = "in" },
    { name = "A2", role = "generic", symbol_port = "out" },
]

[[function]]
name = "j1"
kind = "connector"
symbol = "connector-fixed"
ports = [
    { name = "1", role = "generic", symbol_port = "in", joins = "k1.A1" },
    { name = "2", role = "generic", symbol_port = "out", joins = "k1.A2" },
]

[function.connector]
style = "header-2p"
pincount = 2
gender = "male"
"""


def _module(*, mate: bool) -> tuple[fr.BuildResult, fr.Device, fr.Device]:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    module = d.device("M1", "DEMO-RELAY-MOD-2")
    plug = d.device("P1", "DEMO-CONN-4P")
    if mate:
        d.mate(plug, module.j1)
    return fr.build(d), module, plug


def _port(model: Model, designation: str) -> Id[Port]:
    """The port whose printed form is `designation`."""
    (found,) = (p for p in ports(model) if port_designation(model, p) == designation)
    return found


def _net_designations(model: Model, designation: str) -> set[str]:
    net = net_of(model, _port(model, designation))
    assert net is not None
    return {port_designation(model, p) for p in net.ports}


def test_a_mated_plug_pin_the_header_pin_and_the_relay_port_share_one_net() -> None:
    """Acceptance 4: pin n of the plug, header pin n and the relay port are one physical net."""
    result, *_ = _module(mate=True)
    model = result.model
    for pin, relay_port in [("1", "A1"), ("2", "A2"), ("3", "B1"), ("4", "B2")]:
        # MUTATION: closure `_join_mates` returns without unioning (the relay ports leave the net)
        assert _net_designations(model, f"-M1-J1:{pin}") == {
            f"-P1:{pin}",
            f"-M1-J1:{pin}",
            f"-M1:{relay_port}",
        }


def test_a_header_pin_not_mated_still_joins_the_relay_port() -> None:
    """With no plug, the header pin and the relay port still form a two-port net."""
    result, *_ = _module(mate=False)
    model = result.model
    assert _net_designations(model, "-M1-J1:1") == {"-M1-J1:1", "-M1:A1"}
    assert _net_designations(model, "-M1-J2:2") == {"-M1-J2:2", "-M1:M"}


def _unconnected(result: fr.BuildResult, model: Model) -> set[str]:
    return {
        port_designation(model, f.subjects[0])
        for f in result.findings
        if f.code == _PORT_UNCONNECTED
    }


def test_a_joined_relay_port_is_connected_and_an_unjoined_one_is_not() -> None:
    """The join counts as a connection for PORT_UNCONNECTED; a plain relay coil still reports."""
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.device("M1", "DEMO-RELAY-MOD-2")
    d.device("K1", "DEMO-RLY-2CO-24")
    result = fr.build(d)
    model = result.model
    unconnected = _unconnected(result, model)
    # MUTATION: connectivity `_unconnected` ignores joins (-M1:A1 then reports)
    assert "-M1:A1" not in unconnected
    assert "-M1:L+" not in unconnected
    assert {"-K1:A1", "-K1:A2"} <= unconnected


def test_a_joined_relay_port_is_in_use_and_an_unjoined_one_is_unused() -> None:
    """`port_is_unused` reads the join; the same coil on a part with no joins is unused."""
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.device("M1", "DEMO-RELAY-MOD-2")
    d.device("K1", "DEMO-RLY-2CO-24")
    model = fr.build(d).model
    # MUTATION: unused.py ignores joins (A1 reads unused)
    assert port_is_unused(model, _port(model, "-M1:A1")) is False
    assert port_is_unused(model, _port(model, "-K1:A1")) is True


def test_a_two_header_module_prints_its_pins_with_the_header_segment() -> None:
    """Acceptance 12: two headers J1, J2 print `-M1-J1:1` and `-M1-J2:1`; a relay port `-M1:A1`."""
    result, *_ = _module(mate=False)
    printed = {port_designation(result.model, p) for p in ports(result.model)}
    assert {"-M1-J1:1", "-M1-J2:1", "-M1:A1"} <= printed


def test_a_one_header_module_prints_its_pin_without_a_segment(tmp_path: Path) -> None:
    """Acceptance 12: a lone header adds no segment, so its pin reads `-M1:1`."""
    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "m.toml").write_text(_ONE_HEADER)
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(tmp_path))
    d = fr.Design(draft, place="C1")
    d.location("C1", "Cabinet")
    d.device("M1", "ONE-HEADER-MOD")
    model = fr.build(d).model
    printed = {port_designation(model, p) for p in ports(model)}
    # MUTATION: connector_segments `<= 1` -> `<= 0` (the lone header prints `-M1-J1:1`)
    assert "-M1:1" in printed
    assert "-M1-J1:1" not in printed
    assert {f.name for f in functions(model).values()} >= {"k1", "j1"}


def test_a_rail_on_the_plug_side_crosses_the_join_to_the_relay_port() -> None:
    """A rail on plug pin 1 reaches relay port A1 through the mate and the join, not A2."""
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("24V", current="dc", rails={"P24": ("24", None)})
    module = d.item("DEMO-RELAY-MOD-2", name="m1")
    plug = d.item("DEMO-CONN-4P", name="p1")
    d.mate(plug.fn("x1"), module.fn("j1"))
    d.net("P24", plug.fn("x1")["1"], cls="power", potential="P24")
    model = freeze(merge(fransys_parts.load("demo_parts"), d.draft()))
    # MUTATION: closure `_join_mates` returns without unioning (A1 carries no rail)
    assert port_rails(model, module.fn("k1")["A1"].id) == {"P24"}
    assert port_rails(model, module.fn("k1")["A2"].id) == frozenset()
