"""Fixtures for the overview tests: an invented plant built with the model API.

Every part, MPN and designation here is invented (CLAUDE.md invariant 6). The builder holds
records, not a frozen model, so a test can reorder them before they reach a `Draft`.
"""

import random
from typing import TYPE_CHECKING

import pytest

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor, Mate
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    Aspect,
    ConductorKind,
    FunctionKind,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.templates import Part

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model, Record

_ORIGIN = Origin(file="packages/fransys-overview/tests/conftest.py", line=1, note="invented")


class Plant:
    """Records of an invented plant, added one item, wire and mate at a time."""

    def __init__(self) -> None:
        self.records: list[Record] = []
        self._functions: dict[Id[Item], Id[Function]] = {}
        self._ports: dict[tuple[Id[Item], str], Id[Port]] = {}
        self._parts: dict[str, Id[Part]] = {}
        self._keys: dict[Id[Item], tuple[str, ...]] = {}

    def part(self, mpn: str, category: PartCategory = PartCategory.GENERIC) -> Id[Part]:
        """A part with this `mpn`, added once."""
        if mpn not in self._parts:
            part = Part(
                id=make_id(Part, (mpn,)),
                key=(mpn,),
                mpn=mpn,
                manufacturer="Example Co",
                description=f"Invented {mpn}",
                category=category,
                class_code="X",
            )
            self.records.append(part)
            self._parts[mpn] = part.id
        return self._parts[mpn]

    def item(  # noqa: PLR0913 -- one keyword per thing a test varies
        self,
        key: str,
        designation: str | None,
        *,
        mpn: str | None = None,
        parent: Id[Item] | None = None,
        installed: bool = True,
        description: str = "Invented item",
        category: PartCategory = PartCategory.GENERIC,
    ) -> Id[Item]:
        """One item, with a part when it has an `mpn`."""
        item = Item(
            id=make_id(Item, (key,)),
            key=(key,),
            part=None if mpn is None else self.part(mpn, category),
            parent=parent,
            position=None,
            tag=designation,
            description=description,
            installed=installed,
        )
        self.records.append(item)
        self._keys[item.id] = item.key
        return item.id

    def function(self, item: Id[Item]) -> Id[Function]:
        """The one function `main` of `item`, added on first use."""
        if item not in self._functions:
            function = Function(
                id=make_id(Function, (*self._keys[item], "main")),
                key=(*self._keys[item], "main"),
                item=item,
                template=None,
                name="main",
                kind=FunctionKind.GENERIC,
            )
            self.records.append(function)
            self._functions[item] = function.id
        return self._functions[item]

    def port(self, item: Id[Item], name: str) -> Id[Port]:
        """The port `name` of `item`'s function `main`, added on first use."""
        if (item, name) not in self._ports:
            function = self.function(item)
            port = Port(
                id=make_id(Port, (*self._keys[item], "main", name)),
                key=(*self._keys[item], "main", name),
                function=function,
                template=None,
                name=name,
                role=PortRole.GENERIC,
            )
            self.records.append(port)
            self._ports[item, name] = port.id
        return self._ports[item, name]

    def wire(self, a: tuple[Id[Item], str], b: tuple[Id[Item], str], key: str) -> None:
        """A wire between two ports, each given as `(item, port name)`."""
        self._conductor(a, b, key, ConductorKind.WIRE, None)

    def core(
        self, cable: Id[Item], a: tuple[Id[Item], str], b: tuple[Id[Item], str], key: str
    ) -> None:
        """One core of `cable` between two ports."""
        self._conductor(a, b, key, ConductorKind.CORE, cable)

    def _conductor(
        self,
        a: tuple[Id[Item], str],
        b: tuple[Id[Item], str],
        key: str,
        kind: ConductorKind,
        carrier: Id[Item] | None,
    ) -> None:
        self.records.append(
            Conductor(
                id=make_id(Conductor, (key,)),
                key=(key,),
                a=self.port(*a),
                b=self.port(*b),
                kind=kind,
                carrier=carrier,
            )
        )

    def mate(self, a: Id[Item], b: Id[Item], key: str) -> None:
        """Plug the `main` functions of two items together."""
        self.records.append(
            Mate(id=make_id(Mate, (key,)), key=(key,), a=self.function(a), b=self.function(b))
        )

    def place(self, item: Id[Item], label: str) -> None:
        """Place `item` at the location node `label`, made on first use."""
        node = AspectNode(
            id=make_id(AspectNode, ("loc", label)),
            key=("loc", label),
            aspect=Aspect.LOCATION,
            parent=None,
            label=label,
            description=f"Invented location {label}",
        )
        placement = Placement(
            id=make_id(Placement, (*self._keys[item], "at", label)),
            key=(*self._keys[item], "at", label),
            item=item,
            node=node.id,
        )
        if node not in self.records:
            self.records.append(node)
        self.records.append(placement)

    def draft(self, seed: int | None = None) -> Draft:
        """The records in a `Draft`, shuffled by `seed` when there is one."""
        records = list(self.records)
        if seed is not None:
            random.Random(seed).shuffle(records)  # noqa: S311 -- a test shuffle, not security
        draft = Draft()
        draft.extend(records, origin=_ORIGIN)
        return draft

    def freeze(self, seed: int | None = None) -> Model:
        """The frozen model of every record so far."""
        return freeze(self.draft(seed))


def build_demo() -> Plant:
    """An invented plant of about thirty items: a cabinet at `+C1`, a field site at `+F2`.

    - Cabinet `A1` holds a supply `G1`, two breakers, four relays (`K4` not installed), a terminal
      strip `X1` with four terminals, and a PLC `A2` with two modules.
    - The field site has a pump `M10`, a valve `Y10`, three sensors and a harness `H1` mated to a
      board `JB1` (at the field site too) through the board's edge connector `J1`, a child item;
      the board carries three resistors and a chip.
    - Cable `W1` joins the terminal strip to the valve and one sensor; cable `W2` joins the harness
      to two sensors. One relay is left without a designation.
    """
    plant = Plant()
    cab = plant.item("a1", "A1", description="Control cabinet")
    plant.place(cab, "+C1")
    psu = plant.item("g1", "G1", mpn="SIM-PSU-24V", parent=cab)
    breakers = [plant.item(f"f{n}", f"F{n}", mpn="SIM-MCB-2A", parent=cab) for n in (1, 2)]
    relays = [
        plant.item(f"k{n}", f"K{n}", mpn="SIM-RELAY-24V", parent=cab, installed=n != 4)
        for n in (1, 2, 3, 4)
    ]
    spare = plant.item("k-spare", None, mpn="SIM-RELAY-24V", parent=cab, description="Spare relay")
    strip = plant.item("x1", "X1", parent=cab, description="Terminal strip")
    terminals = [plant.item(f"x1-{n}", f"X1:{n}", parent=strip) for n in (1, 2, 3, 4)]
    plc = plant.item("a2", "A2", mpn="SIM-PLC-CPU", parent=cab)
    modules = [plant.item(f"a2-m{n}", f"A2.{n}", mpn="SIM-DI-8", parent=plc) for n in (1, 2)]
    for item in (psu, *breakers, *relays, strip, plc):
        plant.place(item, "+C1")

    plant.wire((psu, "1"), (breakers[0], "1"), "w-psu-f1")
    plant.wire((psu, "2"), (breakers[1], "1"), "w-psu-f2")
    plant.wire((breakers[0], "2"), (relays[0], "1"), "w-f1-k1")
    plant.wire((breakers[0], "2"), (relays[1], "1"), "w-f1-k2")
    plant.wire((breakers[1], "2"), (relays[2], "1"), "w-f2-k3")
    plant.wire((breakers[1], "2"), (relays[3], "1"), "w-f2-k4")
    plant.wire((relays[0], "2"), (terminals[0], "1"), "w-k1-t1")
    plant.wire((relays[1], "2"), (terminals[1], "1"), "w-k2-t2")
    plant.wire((relays[2], "2"), (terminals[2], "1"), "w-k3-t3")
    plant.wire((relays[3], "2"), (terminals[3], "1"), "w-k4-t4")
    plant.wire((modules[0], "1"), (relays[0], "3"), "w-m1-k1")
    plant.wire((modules[1], "1"), (relays[1], "3"), "w-m2-k2")
    plant.wire((spare, "1"), (breakers[1], "2"), "w-spare")

    pump = plant.item("m10", "M10", mpn="SIM-MOTOR-1KW")
    valve = plant.item("y10", "Y10", mpn="SIM-VALVE-24V")
    sensors = [plant.item(f"b{n}", f"B{n}", mpn="SIM-SENSOR-NPN") for n in (10, 11, 12)]
    harness = plant.item("h1", "H1", mpn="SIM-HOUSING-4P")
    board = plant.item("jb1", "JB1", mpn="SIM-BOARD-IOEXP")
    chips = [plant.item(f"jb1-r{n}", f"R{n}", mpn="SIM-R-0603", parent=board) for n in (1, 2, 3)]
    chip = plant.item("jb1-u1", "U1", mpn="SIM-MCU", parent=board)
    edge = plant.item("jb1-j1", "J1", mpn="SIM-HDR-4P", parent=board)
    for item in (pump, valve, *sensors, harness, board):
        plant.place(item, "+F2")

    cable_1 = plant.item("w1", "W1", mpn="SIM-CABLE-4X0.5", category=PartCategory.CABLE)
    cable_2 = plant.item("w2", "W2", mpn="SIM-CABLE-2X0.5", category=PartCategory.CABLE)
    plant.core(cable_1, (terminals[0], "2"), (valve, "1"), "w1-c1")
    plant.core(cable_1, (terminals[1], "2"), (valve, "2"), "w1-c2")
    plant.core(cable_1, (terminals[2], "2"), (sensors[0], "1"), "w1-c3")
    plant.core(cable_1, (terminals[1], "3"), (valve, "3"), "w1-c4")
    plant.core(cable_2, (harness, "1"), (sensors[1], "1"), "w2-c1")
    plant.core(cable_2, (harness, "2"), (sensors[2], "1"), "w2-c2")
    plant.mate(harness, edge, "h1-j1")
    plant.wire((edge, "1"), (chips[0], "1"), "jb1-w1")
    plant.wire((chips[0], "2"), (chips[1], "1"), "jb1-w2")
    plant.wire((chips[1], "2"), (chips[2], "1"), "jb1-w3")
    plant.wire((chips[2], "2"), (chip, "1"), "jb1-w4")
    plant.wire((pump, "1"), (relays[3], "4"), "w-pump")
    return plant


@pytest.fixture
def plant() -> Plant:
    """A fresh, empty plant, for a test that builds its own."""
    return Plant()


@pytest.fixture
def demo_plant() -> Plant:
    """A fresh copy of the invented plant, for a test that adds to it or shuffles it."""
    return build_demo()


@pytest.fixture
def demo_cabinet(demo_plant: Plant) -> Model:
    """The invented plant, frozen. The name is the acceptance skeletons' own."""
    return demo_plant.freeze()
