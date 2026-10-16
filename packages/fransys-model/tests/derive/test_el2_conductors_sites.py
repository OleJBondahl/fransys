"""EL-2 conductors: the public output of each switched derive module is pinned on planted models.

A strip of three terminals with a jumper, and the all-kinds plant of `roles_plants`. The switch
of a site from a kind read to a role read must leave every value here as it is.
"""

from typing import Any

from plant import Plant
from roles_plants import roles_plant

from fransys_model.derive.bundles import bundles
from fransys_model.derive.line_fact import draws_as_line, line_conductors
from fransys_model.derive.loose import function_is_loose
from fransys_model.derive.reports import cable_rows, designation_list, wire_rows
from fransys_model.derive.unused import (
    function_is_reached,
    function_is_unused,
    port_is_reached,
    port_is_unused,
)
from fransys_model.derive.wiring import (
    conductors_on_item,
    terminal_rows,
    unconnected_ports,
    unused_terminals,
)
from fransys_model.derive.wiring_ends import ends_without_jumpers, strip_side_headings
from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import ConductorKind, FunctionKind, PortRole
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import functions, items, ports

EXPECTED_ROWS = [
    ("X", 1, 1, ["jumper"], ["w1"], ("-X1:X:2",), ("-K1:a",)),
    ("X", 2, 1, ["jumper"], ["j2"], ("-X1:X:1",), ("-K1:c",)),
    ("X", 3, None, ["w2"], [], ("-K1:b",), ()),
]
EXPECTED_KEPT = [((), ("-K1:a",)), ((), ()), (("-K1:b",), ())]
EXPECTED_HEADINGS = ("Side A", "Side B")
EXPECTED_UNCONNECTED = ["t3.t3.ext"]
EXPECTED_UNUSED_TERMINALS: list[str] = []
EXPECTED_PORT_UNUSED = [False, False, False, True, False, False, False, False, False]
EXPECTED_PORT_REACHED = [True, True, True, False, False, False, False, False, True]
EXPECTED_FUNCTION_UNUSED = [False, False, False, False]
EXPECTED_FUNCTION_REACHED = [False, True, True, True]
EXPECTED_LOOSE = [False, False, False, False]
EXPECTED_ON_ITEM = {
    "t3": [("internal", ["w2"])],
    "t1": [("external", ["w1"]), ("internal", ["jumper"])],
    "t2": [("external", ["j2"]), ("internal", ["jumper"])],
}
EXPECTED_DESIGNATIONS = [
    ("-K1", "-K1"),
    ("-X1", "-X1"),
    ("-X1:X:1", "-X1:X:1"),
    ("-X1:X:2", "-X1:X:2"),
    ("-X1:X:3", "-X1:X:3"),
]


def _strip_plant() -> tuple[Model, dict[str, Id[Any]]]:
    """Strip `X` of terminals 1..3 (internal and external port each), a device, a jumper."""
    plant = Plant()
    ids: dict[str, Id[Any]] = {}
    strip = plant.item("X", designation="X1")
    ids["strip"] = strip
    for index in (1, 2, 3):
        key = f"t{index}"
        item = plant.item(key, parent=strip)
        plant.add(
            TerminalFacet(
                id=make_id(TerminalFacet, (key,)), key=(key,), subject=item, group="X", index=index
            )
        )
        function = plant.function(item, key, kind=FunctionKind.TERMINAL)
        for name, role in (("int", PortRole.INTERNAL), ("ext", PortRole.EXTERNAL)):
            port = Port(
                id=make_id(Port, (key, key, name)),
                key=(key, key, name),
                function=function,
                template=None,
                name=name,
                role=role,
            )
            plant.add(port)
            ids[f"{key}.{name}"] = port.id
    device = plant.function(plant.item("D", designation="K1"), "D")
    ids["D"] = device
    for name in ("a", "b", "c"):
        ids[f"D.{name}"] = plant.port(device, name)
    plant.wire(ids["t1.int"], ids["t2.int"], key="jumper", kind=ConductorKind.JUMPER)
    plant.wire(ids["t1.ext"], ids["D.a"], key="w1")
    plant.wire(ids["t3.int"], ids["D.b"], key="w2")
    plant.wire(ids["D.c"], ids["t2.ext"], key="j2", kind=ConductorKind.JUMPER)
    return plant.model(), ids


def _names(model: Model, ids: tuple[Any, ...]) -> list[str]:
    """Readable keys of `ids`, whatever table they come from."""
    from fransys_model.vocab.tables import conductors

    table = {**conductors(model), **ports(model), **items(model), **functions(model)}
    return [".".join(table[i].key) for i in ids]


def test_terminal_rows_bridge_the_jumper_and_keep_the_wires() -> None:
    """`t1` and `t2` share a jumper group; the jumper is no wire end; `D.c` is a lone jumper."""
    model, ids = _strip_plant()
    rows = terminal_rows(model, ids["strip"])
    got = [
        (
            r.group,
            r.index,
            r.jumper_group,
            _names(model, r.internal),
            _names(model, r.external),
            r.internal_ends,
            r.external_ends,
        )
        for r in rows
    ]
    assert got == EXPECTED_ROWS
    kept = [ends_without_jumpers(model, r) for r in rows]
    assert kept == EXPECTED_KEPT
    assert strip_side_headings(model, ids["strip"]) == EXPECTED_HEADINGS


def test_unused_reached_and_unconnected_pin_the_jumper_exclusion() -> None:
    """A port reached only by a jumper is not reached."""
    model, ids = _strip_plant()
    every = tuple(ports(model))
    assert _names(model, unconnected_ports(model)) == EXPECTED_UNCONNECTED
    assert _names(model, unused_terminals(model, ids["strip"])) == EXPECTED_UNUSED_TERMINALS
    assert [port_is_unused(model, p) for p in every] == EXPECTED_PORT_UNUSED
    assert [port_is_reached(model, p) for p in every] == EXPECTED_PORT_REACHED
    every_f = tuple(functions(model))
    assert [function_is_unused(model, f) for f in every_f] == EXPECTED_FUNCTION_UNUSED
    assert [function_is_reached(model, f) for f in every_f] == EXPECTED_FUNCTION_REACHED
    assert [function_is_loose(model, f) for f in every_f] == EXPECTED_LOOSE
    on_item = conductors_on_item(model, ids["strip"])
    got = {
        ".".join(items(model)[i].key): [(r.value, _names(model, c)) for r, c in g.items()]
        for i, g in on_item.items()
    }
    assert got == EXPECTED_ON_ITEM


def test_the_all_kinds_plant_pins_reports_lines_and_bundles() -> None:
    """Reports, line owners and bundles over one conductor of every kind."""
    model, ids = roles_plant()
    assert wire_rows(model) == ()
    assert cable_rows(model, ids["item:cable"]) == ()
    assert line_conductors(model) == {}
    assert not any(draws_as_line(model, i) for i in items(model))
    assert bundles(model) == ()


def test_designation_list_names_the_strip_and_its_terminals() -> None:
    """The designation list of the strip plant, jumper conductors present."""
    model, _ = _strip_plant()
    got = [(r.designation, r.reference) for r in designation_list(model)]
    assert got == EXPECTED_DESIGNATIONS
    assert wire_rows(model) == ()
