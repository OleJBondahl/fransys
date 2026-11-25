"""Fixtures for the overview tests: an invented plant built with the model API.

Every part, MPN and designation here is invented (CLAUDE.md invariant 6). The builder holds
records, not a frozen model, so a test can reorder them before they reach a `Draft`.
"""

from typing import TYPE_CHECKING

import pytest
from plant import Plant as BasePlant

from fransys_model.kernel import Model, Origin, make_id
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    PartCategory,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Record


_ORIGIN = Origin(file="packages/fransys-overview/tests/conftest.py", line=1, note="invented")


class Plant:
    """The invented plant: items with one auto `main` function, ports and wires by `(item, port name)`."""

    def __init__(self) -> None:
        self._plant = BasePlant()
        self._keys: dict[Id[Item], tuple[str, ...]] = {}

    @property
    def records(self) -> list[Record]:
        """The records so far, which a test may replace before it freezes."""
        return self._plant.records

    @records.setter
    def records(self, records: list[Record]) -> None:
        self._plant.records = records

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
        part = None if mpn is None else self._plant.part("X", key=mpn, mpn=mpn, description=f"Invented {mpn}", category=category)
        item = self._plant.item(key, designation=designation, part=part, parent=parent, installed=installed, description=description)
        self._keys[item] = (key,)
        return item

    def function(self, item: Id[Item]) -> Id[Function]:
        """The one function `main` of `item`, added on first use."""
        function = make_id(Function, (*self._keys[item], "main"))
        return function if self._plant.has(function) else self._plant.function(item, "main")

    def port(self, item: Id[Item], name: str) -> Id[Port]:
        """The port `name` of `item`'s function `main`, added on first use."""
        port = make_id(Port, (*self._keys[item], "main", name))
        return port if self._plant.has(port) else self._plant.port(self.function(item), name)

    def wire(self, a: tuple[Id[Item], str], b: tuple[Id[Item], str], key: str) -> None:
        """A wire between two ports, each given as `(item, port name)`."""
        self._plant.wire(self.port(*a), self.port(*b), key=key)

    def core(self, cable: Id[Item], a: tuple[Id[Item], str], b: tuple[Id[Item], str], key: str) -> None:
        """One core of `cable` between two ports."""
        self._plant.core(self.port(*a), self.port(*b), key=key, carrier=cable)

    def mate(self, a: Id[Item], b: Id[Item], key: str) -> None:
        """Plug the `main` functions of two items together."""
        self._plant.mate(self.function(a), self.function(b), key=key)

    def place(self, item: Id[Item], label: str) -> None:
        """Place `item` at the location node `label`, made on first use."""
        self._plant.place(item, self._plant.location(f"loc-{label}", label))

    def freeze(self, seed: int | None = None) -> Model:
        """The frozen model of every record so far, in the order of `seed` when there is one."""
        return self._plant.model(shuffled=seed)


def build_demo() -> Plant:
    """An invented plant of about thirty items: a cabinet at `+C1`, a field site at `+F2`.

    - Cabinet `A1` holds a supply `G1`, two breakers, four relays (`K4` not installed), a terminal
      strip `X1` with four terminals, and a PLC `A2` with two modules.
    """
    plant = Plant()
    cab = plant.item("a1", "A1", description="Control cabinet")
    plant.place(cab, "+C1")
    psu = plant.item("g1", "G1", mpn="SIM-PSU-24V", parent=cab)
    breakers = [plant.item(f"f{n}", f"F{n}", mpn="SIM-MCB-2A", parent=cab) for n in (1, 2)]
    relays = [plant.item(f"k{n}", f"K{n}", mpn="SIM-RELAY-24V", parent=cab, installed=n != 4) for n in (1, 2, 3, 4)]
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
