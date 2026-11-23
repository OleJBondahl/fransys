"""Fixtures for the report tests: an invented plant built with the model API only.

Every id comes from `make_id` over a key chosen here; nothing names a real project. `Plant`
collects records and `model()` freezes them, in the order given or in any other. The tests take
"""

from decimal import Decimal

import pytest
from plant import Plant as BasePlant

from fransys_model.elecdef import Connector, Gender
from fransys_model.kernel import Id, Model, Origin, make_id
from fransys_model.refdef import Aspect
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Function, Item, Port, Unit
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    PartCategory,
    PortBoundary,
    SignalType,
)
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import FunctionTemplate, Part
lazy from fransys_model.vocab.connectivity import Conductor

_ORIGIN = Origin(file="conftest.py", line=1, note="fixture")


class Plant(BasePlant):
    """Collects records; `model()` freezes them."""

    def numbered_pin(
        self,
        key: str,
        designation: str,
        *,
        part: Id[Part] | None = None,
        unit: Id[Unit] | None = None,
    ) -> Id[Port]:
        """A numbered item with one function `f` and one port `1`."""
        item = self.item(key, designation=designation, part=part, unit=unit)
        return self.port(self.function(item, "f"), "1")

    def terminal(self, strip: Id[Item], group: str, index: int) -> tuple[Id[Port], Id[Port]]:
        """A terminal `group:index` under `strip`; returns its (internal, external) ports."""
        key = (*self._key_of(strip), f"{group}{index}")
        item = Item(
            id=make_id(Item, key),
            key=key,
            part=None,
            parent=strip,
            position=None,
            tag=None,
            description="Invented",
            installed=True,
        )
        function = Function(
            id=make_id(Function, (*key, "terminal")),
            key=(*key, "terminal"),
            item=item.id,
            template=None,
            name="terminal",
            kind=FunctionKind.TERMINAL,
        )
        self.add(
            item,
            function,
            TerminalFacet(
                id=make_id(TerminalFacet, (*key, "facet")),
                key=(*key, "facet"),
                subject=item.id,
                group=group,
                index=index,
            ),
        )
        internal = self._boundary_port(function, "internal", PortBoundary.INTERNAL)
        external = self._boundary_port(function, "external", PortBoundary.EXTERNAL)
        return internal, external

    def _boundary_port(self, function: Function, name: str, boundary: PortBoundary) -> Id[Port]:
        """Add a port of `function` on `boundary`."""
        key = (*function.key, name)
        port = Port(id=make_id(Port, key), key=key, function=function.id, template=None, name=name, marking=None, boundary=boundary)
        self.add(port)
        return port.id

    def label(self, conductor: Id[Conductor], label: str | None) -> None:
        """Give `conductor` a `wire` facet carrying `label`, which may be `None`."""
        key = (*self._key_of(conductor), "facet")
        self.add(
            WireFacet(
                id=make_id(WireFacet, key),
                key=key,
                subject=conductor,
                colour="black",
                gauge_mm2=Decimal("0.75"),
                length_mm=None,
                label=label,
            )
        )

    def location(self, key: str, label: str) -> Id[AspectNode]:
        """Add a LOCATION node."""
        node = AspectNode(
            id=make_id(AspectNode, (key,)),
            key=(key,),
            aspect=Aspect.LOCATION,
            parent=None,
            label=label,
            description="Invented",
        )
        self.add(node)
        return node.id

    def place(self, item: Id[Item], node: Id[AspectNode]) -> None:
        """Place `item` at `node`."""
        key = (*self._key_of(item), "at", *self._key_of(node))
        self.add(Placement(id=make_id(Placement, key), key=key, item=item, node=node))

    def channels(
        self,
        key: str,
        designation: str,
        signals: tuple[SignalType, ...],
        *,
        unit: Id[Unit] | None = None,
    ) -> list[Id[Function]]:
        """A module item with one channel function per signal, numbered from 1."""
        part = self.part("K", key=f"{key}-part", mpn=f"EXAMPLE-{key}", category=PartCategory.PLC_MODULE, description="Module")
        module = self.item(key, designation=designation, part=part, unit=unit)
        found = []
        for number, signal in enumerate(signals, start=1):
            template = FunctionTemplate(
                id=make_id(FunctionTemplate, (key, f"ch{number}")),
                key=(key, f"ch{number}"),
                part=part,
                name=f"ch{number}",
                kind=FunctionKind.PLC_CHANNEL,
            )
            facet = PlcChannelFacet(
                id=make_id(PlcChannelFacet, (key, str(number), "facet")),
                key=(key, str(number), "facet"),
                subject=template.id,
                signal=signal,
                channel=number,
            )
            self.add(template, facet)
            function = self.function(module, f"ch{number}", template=template.id)
            self.port(function, str(number))
            found.append(function)
        return found

    def bind(self, device: Id[Item], channel: Id[Function], signal_name: str) -> Id[Function]:
        """Add a function `signal` of `device`, bound to `channel`."""
        key = self._key_of(device)
        function = self.function(device, "signal")
        self.add(
            PlcRequestFacet(
                id=make_id(PlcRequestFacet, (*key, "request")),
                key=(*key, "request"),
                subject=function,
                signal=SignalType.DI,
                signal_name=signal_name,
                priority=1,
            ),
            PlcBindingFacet(
                id=make_id(PlcBindingFacet, (*key, "binding")),
                key=(*key, "binding"),
                subject=function,
                channel=channel,
            ),
        )
        return function

    def connector(  # noqa: PLR0913  (a `ConnectorFacet`'s own fields)
        self,
        item: Id[Item],
        name: str,
        markings: tuple[str, ...],
        *,
        gender: Gender | None = Gender.MALE,
        style: str = "header",
        pincount: int | None = None,
    ) -> tuple[Id[Function], dict[str, Id[Port]]]:
        """A connector function `name` of `item`: a port per marking, and a `connector` facet."""
        key = (*self._key_of(item), name)
        part = self.part("K", key=f"{'-'.join(key)}-part", mpn=f"CP-{'-'.join(key)}")
        template = FunctionTemplate(
            id=make_id(FunctionTemplate, (*key, "template")),
            key=(*key, "template"),
            part=part,
            name=name,
            kind=FunctionKind.CONNECTOR,
        )
        function = Function(
            id=make_id(Function, key),
            key=key,
            item=item,
            template=template.id,
            name=name,
            kind=FunctionKind.CONNECTOR,
        )
        facet = ConnectorFacet(
            id=make_id(ConnectorFacet, (*key, "connector")),
            key=(*key, "connector"),
            subject=template.id,
            style=style,
            connector=Connector(poles=len(markings) if pincount is None else pincount, gender=gender),
        )
        self.add(template, function, facet)
        return function.id, {marking: self.port(function.id, marking) for marking in markings}


def small_plant(*, k3_installed: bool = False) -> Plant:
    """A small invented cabinet, already numbered.

    Strip `X1` holds terminals L:1, L:2 (jumpered), N:1 (unused) and S:1. Relays `K1` and
    `K2` are installed; `K3` is not, unless `k3_installed`. A DI/AI/DI module `A1` has device
    """
    plant = Plant()
    relay = plant.part("K", key="relay", mpn="R-1", description="Relay, 24 V")
    k1 = plant.numbered_pin("k1", "K1", part=relay)
    plant.item("k2", designation="K2", part=relay)
    plant.item("k3", designation="K3", part=relay, installed=k3_installed)

    strip = plant.item("x1", designation="X1")
    l1_in, l1_out = plant.terminal(strip, "L", 1)
    l2_in, _ = plant.terminal(strip, "L", 2)
    plant.terminal(strip, "N", 1)
    s1_in, s1_out = plant.terminal(strip, "S", 1)
    plant.wire(l1_in, l2_in, key="x1-jumper", kind=ConductorKind.JUMPER)
    plant.label(plant.wire(plant.numbered_pin("field-a", "B1"), l1_out, key="field-a"), "W1")
    plant.label(plant.wire(k1, l1_in, key="panel-a"), "W2")
    plant.label(plant.wire(s1_in, plant.numbered_pin("spare", "F1"), key="spare"), None)

    channels = plant.channels("mod", "A1", (SignalType.DI, SignalType.AI_CURRENT, SignalType.DI))
    device = plant.item("dev", designation="B7")
    signal = plant.bind(device, channels[0], "tag_dev")
    plant.wire(plant.port(signal, "1"), s1_out, key="dev-wire")
    plant.place(device, plant.location("c1", "C1"))
    return plant


def board_plant() -> Plant:
    """An invented board `JB1`, its connectors and a housing `H1` mated to one of them.

    Connector `J1` (male, markings 1, 2, 10, A1) is mated to housing connector `P1`, which has
    the pins 1, 2, 10, A1 and Z9. The board's child `X1` holds `J2` (female, pins 1 and 2),
    """
    plant = Plant()
    pcb = plant.part("K", key="pcb", mpn="PCB-1")
    plant.add(PcbFacet(id=make_id(PcbFacet, ("pcb", "pcb")), key=("pcb", "pcb"), subject=pcb, revision="A"))
    board = plant.item("jb1", designation="JB1", part=pcb)
    j1_item = plant.item("j1", designation="J1", parent=board)
    j1, j1_ports = plant.connector(j1_item, "x", ("10", "2", "A1", "1"))
    child = plant.item("x1", designation="X1", parent=board)
    j2_item = plant.item("j2", designation="J2", parent=child)
    _, j2_ports = plant.connector(j2_item, "x", ("2", "1"), gender=Gender.FEMALE)
    j3_item = plant.item("j3", designation="J3", parent=board)
    plant.connector(j3_item, "x", (), pincount=2)
    housing = plant.item("h1", designation="H1")
    p1_item = plant.item("p1", designation="P1", parent=housing)
    p1, _ = plant.connector(p1_item, "x", ("Z9", "1", "2", "10", "A1"), gender=Gender.FEMALE)
    plant.mate(j1, p1, key="mate")
    plant.net("v5", (j1_ports["1"], j2_ports["1"]), name="V5")
    plant.net("gnd", (j1_ports["2"], j2_ports["2"]))
    return plant


@pytest.fixture
def new_plant() -> type[Plant]:
    """The `Plant` class: call it for an empty plant."""
    return Plant


@pytest.fixture
def cabinet_plant() -> Plant:
    """The small invented cabinet, not yet frozen."""
    return small_plant()


@pytest.fixture
def cabinet(cabinet_plant: Plant) -> Model:
    """The small invented cabinet, frozen."""
    return cabinet_plant.model()


@pytest.fixture
def cabinet_k3_installed() -> Model:
    """The small invented cabinet with relay `K3` installed too."""
    return small_plant(k3_installed=True).model()


@pytest.fixture
def board_draft() -> Plant:
    """The invented board `JB1`, not yet frozen."""
    return board_plant()


@pytest.fixture
def board_model(board_draft: Plant) -> Model:
    """The invented board `JB1`, frozen."""
    return board_draft.model()


@pytest.fixture
def board() -> Id[Item]:
    """The board `JB1` of the invented board plant."""
    return make_id(Item, ("jb1",))
