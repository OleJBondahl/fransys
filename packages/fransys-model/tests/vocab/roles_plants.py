"""One planted model that holds every `FunctionKind`, `NetClass` and `ConductorKind` member.

`roles_plant()` builds it with `Plant`, plus the item shapes the kind and role readers branch on:
a strip with two terminals, a bar, a connector, a cable, a PLC channel and a breaking-rated
protection. The ids it returns name each record by a key the tests use. Nothing here names a
real project.
"""

from decimal import Decimal
from enum import Enum
from typing import Any

from plant import Plant

from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.connectivity import Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    LinkKind,
    NetClass,
    PartCategory,
    PortRole,
    ProtectionType,
    SignalType,
)
from fransys_model.vocab.facets.cable import CableProductFacet
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.facets.rating import RatingFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.ratings import BreakingPoint, Rating
from fransys_model.vocab.tables import functions
from fransys_model.vocab.templates import FunctionTemplate, Part


def every_kind_member[E: Enum](enum_cls: type[E]) -> tuple[E, ...]:
    """Every member of `enum_cls`, in declaration order."""
    return tuple(enum_cls)


def function_of(model: Model, name: str) -> Function:
    """The one `Function` of `model` named `name`; `AssertionError` when there is not one."""
    found = [f for f in functions(model).values() if f.name == name]
    if len(found) != 1:
        message = f"expected one function named {name!r}, found {len(found)}"
        raise AssertionError(message)
    return found[0]


def _port(plant: Plant, function: Id[Function], name: str, role: PortRole) -> Id[Port]:
    """A port of `function` with `role`; `Plant.port` only makes generic ones."""
    function_key = next(r.key for r in plant.records if r.id == function)
    key = (*function_key, name)
    port = Port(
        id=make_id(Port, key),
        key=key,
        function=function,
        template=None,
        name=name,
        role=role,
    )
    plant.add(port)
    return port.id


def _device(
    plant: Plant,
    ids: dict[str, Id[Any]],
    key: str,
    kind: FunctionKind,
    *,
    ports: tuple[str, ...] = ("1", "2"),
) -> Id[Function]:
    """An item keyed `key` with one function of `kind`, named `key`, and generic ports."""
    item = plant.item(key)
    function = plant.function(item, key, kind=kind)
    for name in ports:
        plant.port(function, name)
    ids[key] = function
    ids[f"item:{key}"] = item
    return function


def _strip(plant: Plant, ids: dict[str, Id[Any]]) -> Id[Item]:
    """A strip item with two terminal items, each with a `terminal` facet and a function."""
    strip = plant.item("strip")
    ids["item:strip"] = strip
    for index in (1, 2):
        key = f"terminal_{index}"
        item = plant.item(key, parent=strip)
        plant.add(
            TerminalFacet(
                id=make_id(TerminalFacet, (key,)),
                key=(key,),
                subject=item,
                group="strip",
                index=index,
            )
        )
        function = plant.function(item, key, kind=FunctionKind.TERMINAL)
        _port(plant, function, "internal", PortRole.INTERNAL)
        _port(plant, function, "external", PortRole.EXTERNAL)
        ids[key] = function
        ids[f"item:{key}"] = item
    return strip


def _contact_co(plant: Plant, ids: dict[str, Id[Any]]) -> None:
    """A changeover contact whose ports carry `COMMON`, `BREAK` and `MAKE`."""
    function = _device(plant, ids, "co", FunctionKind.CONTACT_CO, ports=())
    for name, role in (
        ("common", PortRole.COMMON),
        ("break", PortRole.BREAK),
        ("make", PortRole.MAKE),
    ):
        ids[f"port:co:{name}"] = _port(plant, function, name, role)


def _switch_links(plant: Plant, ids: dict[str, Id[Any]]) -> None:
    """A switch function whose template holds a `SWITCHED` and a `PROTECTIVE` internal link."""
    _part, template, pin_a, pin_b = plant.relay_part()
    item = plant.item("switch")
    ids["switch"] = plant.function(item, "switch", template=template.id, kind=FunctionKind.SWITCH)
    ids["item:switch"] = item
    plant.link(pin_a, pin_b, LinkKind.SWITCHED, key="switched")
    plant.link(pin_a, pin_b, LinkKind.PROTECTIVE, key="protective")


def _protection(plant: Plant, ids: dict[str, Id[Any]]) -> None:
    """A fuse-like protection whose template is rated to break 10 kA at 250 V AC."""
    part = Part(
        id=make_id(Part, ("fuse",)),
        key=("fuse",),
        mpn="EXAMPLE-F",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PROTECTION,
        class_code="F",
    )
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("fuse", "fn")),
        key=("fuse", "fn"),
        part=part.id,
        name="fn",
        kind=FunctionKind.PROTECTION,
        protection_type=ProtectionType.MCB,
    )
    rating = RatingFacet(
        id=make_id(RatingFacet, ("fuse", "rating")),
        key=("fuse", "rating"),
        subject=template.id,
        rating=Rating(
            breaking_ac=(BreakingPoint(voltage_v=Decimal(250), current_a=Decimal(10000)),),
        ),
    )
    plant.add(part, template, rating)
    item = plant.item("protection", part=part.id)
    ids["protection"] = plant.function(
        item, "protection", template=template.id, kind=FunctionKind.PROTECTION
    )
    ids["item:protection"] = item


def _plc_function(plant: Plant, ids: dict[str, Id[Any]], key: str, kind: FunctionKind) -> None:
    """A function of `kind` whose template carries a `PlcChannelFacet` (DI, channel 1)."""
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key,)),
        key=(key,),
        part=plant.part("PLC"),
        name=key,
        kind=kind,
    )
    facet = PlcChannelFacet(
        id=make_id(PlcChannelFacet, (key,)),
        key=(key,),
        subject=template.id,
        signal=SignalType.DI,
        channel=1,
    )
    plant.add(template, facet)
    item = plant.item(key)
    ids[key] = plant.function(item, key, template=template.id, kind=kind)
    ids[f"item:{key}"] = item


def _cable(plant: Plant, ids: dict[str, Id[Any]]) -> Id[Item]:
    """A cable item: its part carries a `cable_product` facet."""
    part = Part(
        id=make_id(Part, ("cable",)),
        key=("cable",),
        mpn="EXAMPLE-CABLE",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    facet = CableProductFacet(
        id=make_id(CableProductFacet, ("cable",)),
        key=("cable",),
        subject=part.id,
        core_colours=("BK", "BU"),
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    plant.add(part, facet)
    cable = plant.item("cable", part=part.id)
    ids["item:cable"] = cable
    return cable


def _conductors_and_nets(plant: Plant, ids: dict[str, Id[Any]], cable: Id[Item]) -> None:
    """One `Conductor` per `ConductorKind` (cores carried by `cable`) and one `Net` per class."""
    wiring = _device(plant, ids, "wiring", FunctionKind.GENERIC, ports=())
    for kind in every_kind_member(ConductorKind):
        a = plant.port(wiring, f"{kind.value}_a")
        b = plant.port(wiring, f"{kind.value}_b")
        key = f"conductor_{kind.value}"
        if kind is ConductorKind.CORE:
            ids[key] = plant.core(a, b, key=key, carrier=cable)
        else:
            ids[key] = plant.wire(a, b, key=key, kind=kind)
    for net_class in every_kind_member(NetClass):
        key = f"net_{net_class.value}"
        net = Net(
            id=make_id(Net, (key,)),
            key=(key,),
            name=None,
            net_class=net_class,
            ports=(),
            potential=None,
        )
        plant.add(net)
        ids[key] = net.id


def roles_plant() -> tuple[Model, dict[str, Id[Any]]]:
    """Build the planted model and the ids of its records, keyed by name.

    Function keys are the function names: `coil`, `no`, `nc`, `co`, `terminal_1`, `terminal_2`,
    `connector`, `plc_channel`, `channel_by_facet`, `bar`, `protection`, `switch`, `wiring`, and
    one per other `FunctionKind` (`supply`, `load`, `sensor`, `actuator`, `generic`). Item keys
    are `item:<name>` (`item:strip`, `item:cable`, `item:terminal_1`, ...). Ports are
    `port:co:<name>`, conductors `conductor_<kind>`, nets `net_<class>`.
    """
    plant = Plant()
    ids: dict[str, Id[Any]] = {}
    _device(plant, ids, "coil", FunctionKind.COIL)
    _device(plant, ids, "no", FunctionKind.CONTACT_NO)
    _device(plant, ids, "nc", FunctionKind.CONTACT_NC)
    _contact_co(plant, ids)
    _strip(plant, ids)
    _device(plant, ids, "connector", FunctionKind.CONNECTOR, ports=("1",))
    _plc_function(plant, ids, "plc_channel", FunctionKind.PLC_CHANNEL)
    _plc_function(plant, ids, "channel_by_facet", FunctionKind.GENERIC)
    _device(plant, ids, "bar", FunctionKind.BAR, ports=())
    _protection(plant, ids)
    _switch_links(plant, ids)
    cable = _cable(plant, ids)
    _conductors_and_nets(plant, ids, cable)
    for kind in (
        FunctionKind.SUPPLY,
        FunctionKind.LOAD,
        FunctionKind.SENSOR,
        FunctionKind.ACTUATOR,
        FunctionKind.GENERIC,
    ):
        _device(plant, ids, kind.value, kind, ports=("1",))
    return plant.model(), ids
