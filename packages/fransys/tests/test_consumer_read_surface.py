"""A consumer's walk over `fr.derive`'s top level: the nine tables, their records and enums.

The consumer imports only `fransys`. Every name below is one `fr.derive` exports at its top
level: the table accessors (`items`, `functions`, `ports`, `nets`, `conductors`, `placements`,
`aspect_nodes`, `units`, `boundaries`), the enums and the query `boundary`. No
`fr.derive.<submodule>` attribute is reached (a type checker cannot see a submodule that nothing
imported), no ignore comment is needed, and an id is only ever a key the tables returned.

Built through the facade from `examples/demo-parts`: two nested units `outer` and `inner`, two
locations, two groups, a strip terminal, two relays, two wires, one declared net, and
`inner.boundary(terminal)`, so that every table holds records.
"""

from typing import Any

import fransys as fr
import fransys_author
import pytest

_PROJECT: dict[str, Any] = {
    "title": "Read surface",
    "number": "P-1010",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


@pytest.fixture(scope="module")
def result() -> fr.BuildResult:
    """The design of the module docstring, built through the facade."""
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    outer = d.scope("outer").unit("outer", revision=1, interface="1")
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    inner = outer.scope("in", at=outer.location("BOX", "Box")).unit(
        "inner", revision=1, interface="1"
    )
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    field = inner.location("FIELD", "Field side")
    group_a, group_b = inner.group("GA", "Group A"), inner.group("GB", "Group B")
    terminal = inner.strip("X1", at=field).terminal("DEMO-TB-2.5", group=group_a)
    ka = inner.item("DEMO-RLY-2CO-24", name="Ka", at=field, group=group_a)
    k1 = inner.item("DEMO-RLY-2CO-24", name="K1", at=field, group=group_b)
    wire = inner.wiring(colour="BU", gauge="0.5")
    wire(ka.fn("coil")["A1"], terminal.function["external"])
    wire(k1.fn("coil")["A1"], terminal.inner)
    inner.net("N24", ka.fn("coil")["A2"], k1.fn("coil")["A2"], cls="power", potential="24V")
    inner.break_before(group_b)
    inner.boundary(terminal)
    return fr.build(parts, d.draft())


def test_every_table_is_non_empty(result: fr.BuildResult) -> None:
    """The walk below cannot pass vacuously: each of the nine tables holds records."""
    model = result.model
    sizes = {
        "items": len(fr.derive.items(model)),
        "functions": len(fr.derive.functions(model)),
        "ports": len(fr.derive.ports(model)),
        "nets": len(fr.derive.nets(model)),
        "conductors": len(fr.derive.conductors(model)),
        "placements": len(fr.derive.placements(model)),
        "aspect_nodes": len(fr.derive.aspect_nodes(model)),
        "units": len(fr.derive.units(model)),
        "boundaries": len(fr.derive.boundaries(model)),
    }
    assert sizes == {
        "items": 4,
        "functions": 7,
        "ports": 18,
        "nets": 1,
        "conductors": 2,
        "placements": 6,
        "aspect_nodes": 4,
        "units": 2,
        "boundaries": 1,
    }


def test_items_and_their_functions(result: fr.BuildResult) -> None:
    """An item's name is `key[-1]`; a function points back at its item by id."""
    model = result.model
    items = fr.derive.items(model)
    by_name = {item.key[-1]: item_id for item_id, item in items.items()}
    assert set(by_name) == {"Ka", "K1", "X1", "1"}

    functions = fr.derive.functions(model)
    ka_functions = {fn.name: fn for fn in functions.values() if fn.item == by_name["Ka"]}
    assert set(ka_functions) == {"coil", "co_1", "co_2"}
    assert ka_functions["coil"].kind is fr.derive.FunctionKind.COIL
    assert ka_functions["co_1"].kind is fr.derive.FunctionKind.CONTACT_CO

    (terminal_fn,) = (fn for fn in functions.values() if fn.kind is fr.derive.FunctionKind.TERMINAL)
    assert terminal_fn.item == by_name["1"]
    assert all(fn.item in items for fn in functions.values())


def test_ports_of_a_function(result: fr.BuildResult) -> None:
    """A port names its function by id; the terminal's two ports carry the two roles."""
    model = result.model
    functions = fr.derive.functions(model)
    ports = fr.derive.ports(model)
    (terminal_id,) = (
        fn_id for fn_id, fn in functions.items() if fn.kind is fr.derive.FunctionKind.TERMINAL
    )
    roles = {port.name: port.role for port in ports.values() if port.function == terminal_id}
    assert roles == {
        "external": fr.derive.PortRole.EXTERNAL,
        "internal": fr.derive.PortRole.INTERNAL,
    }
    assert all(port.function in functions for port in ports.values())


def test_nets_resolve_in_ports(result: fr.BuildResult) -> None:
    """A net's ports are ids in the ports table: here the two relay coils' `A2` ports."""
    model = result.model
    ports = fr.derive.ports(model)
    functions = fr.derive.functions(model)
    items = fr.derive.items(model)
    (net,) = fr.derive.nets(model).values()
    assert net.name == "N24"
    assert net.net_class is fr.derive.NetClass.POWER
    assert net.potential == "24V"
    assert {ports[p].name for p in net.ports} == {"A2"}
    assert {items[functions[ports[p].function].item].key[-1] for p in net.ports} == {"Ka", "K1"}


def test_conductors_join_ports(result: fr.BuildResult) -> None:
    """Both wires are `WIRE` conductors whose ends are ids in the ports table."""
    model = result.model
    ports = fr.derive.ports(model)
    conductors = fr.derive.conductors(model).values()
    assert {c.kind for c in conductors} == {fr.derive.ConductorKind.WIRE}
    assert sorted(sorted((ports[c.a].name, ports[c.b].name)) for c in conductors) == [
        ["A1", "external"],
        ["A1", "internal"],
    ]


def test_aspect_nodes_and_placements(result: fr.BuildResult) -> None:
    """Locations are `LOCATION` nodes; a placement joins an item to a node by id."""
    model = result.model
    items = fr.derive.items(model)
    nodes = fr.derive.aspect_nodes(model)
    locations = {n.label for n in nodes.values() if n.aspect is fr.derive.Aspect.LOCATION}
    assert locations == {"BOX", "FIELD"}
    groups = {n.label for n in nodes.values() if n.aspect is fr.derive.Aspect.FUNCTION}
    assert groups == {"GA", "GB"}

    placements = fr.derive.placements(model).values()
    assert all(p.item in items and p.node in nodes for p in placements)
    at_field = {items[p.item].key[-1] for p in placements if nodes[p.node].label == "FIELD"}
    assert at_field == {"Ka", "K1", "X1"}
    in_group_a = {items[p.item].key[-1] for p in placements if nodes[p.node].label == "GA"}
    assert in_group_a == {"Ka", "1"}


def test_units_and_boundaries(result: fr.BuildResult) -> None:
    """Units by name and parent, and the boundary of `inner`."""
    model = result.model
    units = fr.derive.units(model)
    by_name = {fr.derive.unit_release(model, unit_id).name: unit_id for unit_id in units}
    assert set(by_name) == {"outer", "inner"}
    assert units[by_name["outer"]].parent is None
    assert units[by_name["inner"]].parent == by_name["outer"]

    functions = fr.derive.functions(model)
    (boundary,) = fr.derive.boundaries(model).values()
    assert boundary.unit == by_name["inner"]
    assert functions[boundary.function].kind is fr.derive.FunctionKind.TERMINAL
    assert fr.derive.boundary(model, by_name["inner"]) == (boundary.function,)
    assert fr.derive.boundary(model, by_name["outer"]) == ()
