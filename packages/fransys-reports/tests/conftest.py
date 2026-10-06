"""Fixtures for the report tests: an invented plant built with the model API only.

Every id comes from `make_id` over a key chosen here; nothing names a real project. `Plant`
collects records and `model()` freezes them, in the order given or in any other. The tests take
their models from the fixtures at the bottom; this workspace resolves no test-directory imports.
"""

from decimal import Decimal
from random import Random
from typing import Any

import pytest
from hypothesis import settings

from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.core import Function, Item, Port, Unit, UnitRelease
from fransys_model.vocab.enums import (
    Aspect,
    ConductorKind,
    FunctionKind,
    Gender,
    NetClass,
    PartCategory,
    PortRole,
    SignalType,
)
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import FunctionTemplate, Part

# Decision 0020: same profile as fransys-model's conftest (registering it again under the
# same name with the same settings is a no-op); see that file's comment.
settings.register_profile("fransys", deadline=None, derandomize=True, max_examples=25)
settings.load_profile("fransys")

_ORIGIN = Origin(file="conftest.py", line=1, note="fixture")


class Plant:
    """Collects records; `model()` freezes them."""

    def __init__(self) -> None:
        """Start with no records."""
        self.records: list[Any] = []

    def add(self, *records: Any) -> None:
        """Add ready-made records."""
        self.records.extend(records)

    def part(
        self,
        key: str,
        mpn: str,
        *,
        description: str = "Invented",
        category: PartCategory = PartCategory.GENERIC,
    ) -> Id[Part]:
        """Add a part keyed `(key,)`."""
        part = Part(
            id=make_id(Part, (key,)),
            key=(key,),
            mpn=mpn,
            manufacturer="Example Co",
            description=description,
            category=category,
            class_code="K",
        )
        self.add(part)
        return part.id

    def unit(
        self, key: str, name: str, *, revision: int = 1, interface: str = "1", version: int = 1
    ) -> Id[Unit]:
        """Add a top-level `Unit` keyed `(key,)`, an instance of `(name, version, revision)`."""
        release_key = ("unit_release", name, str(version), str(revision))
        release = UnitRelease(
            id=make_id(UnitRelease, release_key),
            key=release_key,
            name=name,
            version=version,
            revision=revision,
            interface=interface,
        )
        unit = Unit(id=make_id(Unit, (key,)), key=(key,), release=release.id, parent=None)
        self.add(release, unit)
        return unit.id

    def item(  # noqa: PLR0913  (an `Item`'s own fields)
        self,
        key: str,
        designation: str | None,
        *,
        part: Id[Part] | None = None,
        parent: Id[Item] | None = None,
        installed: bool = True,
        description: str = "Invented",
        unit: Id[Unit] | None = None,
    ) -> Id[Item]:
        """Add an item keyed `(key,)`."""
        item = Item(
            id=make_id(Item, (key,)),
            key=(key,),
            part=part,
            parent=parent,
            position=None,
            tag=designation,
            description=description,
            installed=installed,
            unit=unit,
        )
        self.add(item)
        return item.id

    def function(
        self, item: Id[Item], name: str, *, template: Id[FunctionTemplate] | None = None
    ) -> Id[Function]:
        """Add a function of `item`, keyed by the item's key and `name`."""
        key = (*self._key_of(item), name)
        function = Function(
            id=make_id(Function, key),
            key=key,
            item=item,
            template=template,
            name=name,
            kind=FunctionKind.GENERIC,
        )
        self.add(function)
        return function.id

    def port(
        self, function: Id[Function], name: str, role: PortRole = PortRole.GENERIC
    ) -> Id[Port]:
        """Add a port of `function` called `name`."""
        key = (*self._key_of(function), name)
        port = Port(
            id=make_id(Port, key),
            key=key,
            function=function,
            template=None,
            name=name,
            role=role,
        )
        self.add(port)
        return port.id

    def pin(
        self,
        key: str,
        designation: str,
        *,
        part: Id[Part] | None = None,
        unit: Id[Unit] | None = None,
    ) -> Id[Port]:
        """A numbered item with one function `f` and one port `1`."""
        item = self.item(key, designation, part=part, unit=unit)
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
        internal = self.port(function.id, "internal", PortRole.INTERNAL)
        external = self.port(function.id, "external", PortRole.EXTERNAL)
        return internal, external

    def wire(
        self,
        a: Id[Port],
        b: Id[Port],
        key: str,
        *,
        kind: ConductorKind = ConductorKind.WIRE,
    ) -> Id[Conductor]:
        """Add a conductor between two ports."""
        conductor = Conductor(
            id=make_id(Conductor, (key,)), key=(key,), a=a, b=b, kind=kind, carrier=None
        )
        self.add(conductor)
        return conductor.id

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
        part = self.part(
            f"{key}-part", f"EXAMPLE-{key}", category=PartCategory.PLC_MODULE, description="Module"
        )
        module = self.item(key, designation, part=part, unit=unit)
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
            found.append(self.function(module, f"ch{number}", template=template.id))
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
        part = self.part(f"{'-'.join(key)}-part", f"CP-{'-'.join(key)}")
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
            pincount=len(markings) if pincount is None else pincount,
            gender=gender,
        )
        self.add(template, function, facet)
        return function.id, {marking: self.port(function.id, marking) for marking in markings}

    def mate(self, a: Id[Function], b: Id[Function]) -> None:
        """Plug connector `a` into connector `b`."""
        key = ("mate", *self._key_of(a), *self._key_of(b))
        self.add(Mate(id=make_id(Mate, key), key=key, a=a, b=b))

    def net(self, key: str, ports: tuple[Id[Port], ...], name: str | None = None) -> None:
        """Declare a net over `ports`; without a `name` it goes by its key."""
        self.add(
            Net(
                id=make_id(Net, (key,)),
                key=(key,),
                name=name,
                net_class=NetClass.GENERIC,
                ports=ports,
            )
        )

    def insertion_order(self, shuffled: int | None = None) -> list[Any]:
        """The records as `model` inserts them; `shuffled` is a seed for another order."""
        records = list(self.records)
        if shuffled is not None:
            Random(shuffled).shuffle(records)  # noqa: S311  (test data order, not a secret)
        return records

    def model(self, *, shuffled: int | None = None) -> Model:
        """Freeze everything added; `shuffled` is a seed for the draft's insertion order."""
        draft = Draft()
        draft.extend(self.insertion_order(shuffled), origin=_ORIGIN)
        return freeze(draft)

    def _key_of(self, record_id: Id[Any]) -> tuple[str, ...]:
        return next(record.key for record in self.records if record.id == record_id)


def small_plant(*, k3_installed: bool = False) -> Plant:
    """A small invented cabinet, already numbered.

    Strip `X1` holds terminals L:1, L:2 (jumpered), N:1 (unused) and S:1. Relays `K1` and
    `K2` are installed; `K3` is not, unless `k3_installed`. A DI/AI/DI module `A1` has device
    `B7` on its first channel, wired to S:1 and placed at `+C1`. Three wires: `W1` and `W2`
    labelled, one not.
    """
    plant = Plant()
    relay = plant.part("relay", "R-1", description="Relay, 24 V")
    k1 = plant.pin("k1", "K1", part=relay)
    plant.item("k2", "K2", part=relay)
    plant.item("k3", "K3", part=relay, installed=k3_installed)

    strip = plant.item("x1", "X1")
    l1_in, l1_out = plant.terminal(strip, "L", 1)
    l2_in, _ = plant.terminal(strip, "L", 2)
    plant.terminal(strip, "N", 1)
    s1_in, s1_out = plant.terminal(strip, "S", 1)
    plant.wire(l1_in, l2_in, "x1-jumper", kind=ConductorKind.JUMPER)
    plant.label(plant.wire(plant.pin("field-a", "B1"), l1_out, "field-a"), "W1")
    plant.label(plant.wire(k1, l1_in, "panel-a"), "W2")
    plant.label(plant.wire(s1_in, plant.pin("spare", "F1"), "spare"), None)

    channels = plant.channels("mod", "A1", (SignalType.DI, SignalType.AI_CURRENT, SignalType.DI))
    device = plant.item("dev", "B7")
    signal = plant.bind(device, channels[0], "tag_dev")
    plant.wire(plant.port(signal, "1"), s1_out, "dev-wire")
    plant.place(device, plant.location("c1", "C1"))
    return plant


def board_plant() -> Plant:
    """An invented board `JB1`, its connectors and a housing `H1` mated to one of them.

    Connector `J1` (male, markings 1, 2, 10, A1) is mated to housing connector `P1`, which has
    the pins 1, 2, 10, A1 and Z9. The board's child `X1` holds `J2` (female, pins 1 and 2),
    unmated, and the board holds `J3`, a connector with no pins. Each connector is its own item,
    as a real connector part numbers it (decision model-0049); its row's designation is that
    item's own -- `J1`, `J2`, `J3`, `P1` -- never `JB1`, `X1` or `H1` with the connector
    function's own internal name tacked on. Net `V5` joins `J1:1` and `J2:1`; an unnamed net
    `gnd` joins `J1:2` and `J2:2`.
    """
    plant = Plant()
    board = plant.item("jb1", "JB1")
    j1_item = plant.item("j1", "J1", parent=board)
    j1, j1_ports = plant.connector(j1_item, "x", ("10", "2", "A1", "1"))
    child = plant.item("x1", "X1", parent=board)
    j2_item = plant.item("j2", "J2", parent=child)
    _, j2_ports = plant.connector(j2_item, "x", ("2", "1"), gender=Gender.FEMALE)
    j3_item = plant.item("j3", "J3", parent=board)
    plant.connector(j3_item, "x", (), pincount=2)
    housing = plant.item("h1", "H1")
    p1_item = plant.item("p1", "P1", parent=housing)
    p1, _ = plant.connector(p1_item, "x", ("Z9", "1", "2", "10", "A1"), gender=Gender.FEMALE)
    plant.mate(j1, p1)
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
def strip() -> Id[Item]:
    """The terminal strip `X1` of the small invented cabinet."""
    return make_id(Item, ("x1",))


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
