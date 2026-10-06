"""WP8 tests: connectivity vocab kinds (ROADMAP WP8, design/vocabulary.md 6 "Connectivity")."""

import pytest

from fransys_model.kernel import Id, SchemaError
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.enums import ConductorKind, NetClass


def test_net_has_the_designed_fields() -> None:
    """`Net` carries `name`, `net_class`, `ports`."""
    port_a = Id(kind="port", value="1" * 32)
    port_b = Id(kind="port", value="2" * 32)
    net = Net(
        id=Id(kind="net", value="3" * 32),
        key=("examples", "supply-24v"),
        name="24V",
        net_class=NetClass.POWER,
        ports=(port_a, port_b),
    )
    assert net.net_class is NetClass.POWER
    assert set(net.ports) == {port_a, port_b}
    assert net.potential is None


def test_net_ports_normalise_order_at_construction() -> None:
    """`Net.ports` is stored sorted by id regardless of construction order (design/vocabulary.md
    6)."""
    low = Id(kind="port", value="1" * 32)
    high = Id(kind="port", value="9" * 32)
    net = Net(
        id=Id(kind="net", value="3" * 32),
        key=("examples", "supply-24v"),
        name="24V",
        net_class=NetClass.POWER,
        ports=(high, low),
    )
    assert net.ports == (low, high)


def test_conductor_has_the_designed_fields() -> None:
    """`Conductor` carries `a`, `b`, `kind`, `net`, `carrier`."""
    port_a = Id(kind="port", value="1" * 32)
    port_b = Id(kind="port", value="2" * 32)
    carrier = Id(kind="item", value="4" * 32)
    core = Conductor(
        id=Id(kind="conductor", value="5" * 32),
        key=("examples", "w012", "core-1"),
        a=port_a,
        b=port_b,
        kind=ConductorKind.CORE,
        carrier=carrier,
    )
    assert core.kind is ConductorKind.CORE
    assert core.carrier == carrier


def test_conductor_ends_normalise_order_at_construction() -> None:
    """`Conductor.a`/`b` are stored in id order; direction is not a fact (vocabulary.md 6)."""
    low = Id(kind="port", value="1" * 32)
    high = Id(kind="port", value="9" * 32)
    core = Conductor(
        id=Id(kind="conductor", value="5" * 32),
        key=("examples", "w012", "core-1"),
        a=high,
        b=low,
        kind=ConductorKind.CORE,
        carrier=None,
    )
    assert (core.a, core.b) == (low, high)


def test_mate_has_the_designed_fields() -> None:
    """`Mate` carries two `Function` ids; equal-named ports become conductive (vocabulary.md 6)."""
    housing_connector = Id(kind="function", value="6" * 32)
    board_connector = Id(kind="function", value="7" * 32)
    mate = Mate(
        id=Id(kind="mate", value="8" * 32),
        key=("examples", "harness", "j1-mate"),
        a=housing_connector,
        b=board_connector,
    )
    assert {mate.a, mate.b} == {housing_connector, board_connector}


def test_net_potential_names_the_rail() -> None:
    """`Net.potential` carries the rail name; it defaults to `None` for an ordinary net."""
    net = Net(
        id=Id(kind="net", value="3" * 32),
        key=("examples", "supply-24v"),
        name="24V",
        net_class=NetClass.POWER,
        ports=(Id(kind="port", value="1" * 32),),
        potential="24V",
    )
    assert net.potential == "24V"


def test_net_refuses_a_port_listed_twice() -> None:
    """A net listing the same port twice is refused with `kind="net"` (design/vocabulary.md 6)."""
    port = Id(kind="port", value="1" * 32)
    with pytest.raises(SchemaError) as excinfo:
        Net(
            id=Id(kind="net", value="3" * 32),
            key=("examples", "supply-24v"),
            name="24V",
            net_class=NetClass.POWER,
            ports=(port, port),
        )
    assert excinfo.value.kind == "net"


def test_conductor_refuses_the_same_port_at_both_ends() -> None:
    """A conductor joining a port to itself is refused with `kind="conductor"` (vocabulary.md 6)."""
    port = Id(kind="port", value="1" * 32)
    with pytest.raises(SchemaError) as excinfo:
        Conductor(
            id=Id(kind="conductor", value="5" * 32),
            key=("examples", "w012", "core-1"),
            a=port,
            b=port,
            kind=ConductorKind.CORE,
            carrier=None,
        )
    assert excinfo.value.kind == "conductor"


def test_mate_refuses_the_same_function_at_both_ends() -> None:
    """A mate joining a function to itself is refused with `kind="mate"` (vocabulary.md 6)."""
    function = Id(kind="function", value="6" * 32)
    with pytest.raises(SchemaError) as excinfo:
        Mate(
            id=Id(kind="mate", value="8" * 32),
            key=("examples", "harness", "j1-mate"),
            a=function,
            b=function,
        )
    assert excinfo.value.kind == "mate"
