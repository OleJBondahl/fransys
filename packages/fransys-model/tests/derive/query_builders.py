"""Invented plants for the WP16 query tests: strips, PLC racks, cables, boards, trees.

Every id comes from `make_id` over a key the caller chooses; nothing names a real project.
"""

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    Aspect,
    ConductorKind,
    FunctionKind,
    PartCategory,
    PortRole,
    SignalType,
)
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.facets.pcb import FootprintFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import FunctionTemplate, Part

if TYPE_CHECKING:
    from plant import Plant

    from fransys_model.vocab.connectivity import Net


@dataclasses.dataclass(frozen=True)
class Terminal:
    """A terminal item and its two ports."""

    item: Id[Item]
    internal: Id[Port]
    external: Id[Port]


def make_terminal(plant: Plant, strip_key: str, label: str, *, group: str, index: int) -> Terminal:
    """A terminal under the strip item keyed `strip_key`, which the caller adds."""
    key = (strip_key, label)
    item = Item(
        id=make_id(Item, key),
        key=key,
        part=None,
        parent=make_id(Item, (strip_key,)),
        position=None,
        tag=f"{group}:{index}",
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
    ports = [
        Port(
            id=make_id(Port, (*function.key, role.value)),
            key=(*function.key, role.value),
            function=function.id,
            template=None,
            name=role.value,
            role=role,
        )
        for role in (PortRole.INTERNAL, PortRole.EXTERNAL)
    ]
    facet = TerminalFacet(
        id=make_id(TerminalFacet, (*key, "facet")),
        key=(*key, "facet"),
        subject=item.id,
        group=group,
        index=index,
    )
    plant.add(item, function, *ports, facet)
    return Terminal(item.id, ports[0].id, ports[1].id)


def make_pin(
    plant: Plant, key: str, designation: str | None, *, parent: Id[Item] | None = None
) -> Id[Port]:
    """A numbered item with one function and one port `1`."""
    item = plant.item(key, designation=designation, parent=parent)
    return plant.port(plant.function(item, "f"), "1")


def item_of(plant: Plant, port: Id[Port]) -> Id[Item]:
    """The item that owns `port`."""
    function = next(r for r in plant.records if r.id == port).function
    return next(r for r in plant.records if r.id == function).item


def make_strip(plant: Plant) -> tuple[Id[Item], tuple[Terminal, ...]]:
    """Strip `x1`: L 2, L 1 and N 1 (authored in that order), one jumper L1-L2, one wire."""
    strip = plant.item("x1", designation="X1")
    l2 = make_terminal(plant, "x1", "t-l2", group="L", index=2)
    l1 = make_terminal(plant, "x1", "t-l1", group="L", index=1)
    n1 = make_terminal(plant, "x1", "t-n1", group="N", index=1)
    plant.wire(l1.internal, l2.internal, key="x1-jumper", kind=ConductorKind.JUMPER)
    plant.wire(make_pin(plant, "field-a", "B1"), l1.external, key="x1-field-a")
    plant.wire(make_pin(plant, "panel-a", "K1"), l1.internal, key="x1-panel-a")
    return strip, (l2, l1, n1)


def make_channels(
    plant: Plant, key: str, designation: str | None, signals: tuple[SignalType, ...]
) -> list[Id[Function]]:
    """A numbered module item with one channel function per signal, numbered from 1."""
    part = Part(
        id=make_id(Part, (key, "part")),
        key=(key, "part"),
        mpn=f"EXAMPLE-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    plant.add(part)
    module = plant.item(key, designation=designation, part=part.id)
    found = []
    for number, signal in enumerate(signals, start=1):
        template = FunctionTemplate(
            id=make_id(FunctionTemplate, (key, "part", f"ch{number}")),
            key=(key, "part", f"ch{number}"),
            part=part.id,
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
        plant.add(template, facet)
        found.append(plant.function(module, f"ch{number}", template=template.id))
    return found


def bind_device(
    plant: Plant, device: str, designation: str | None, channel: Id[Function]
) -> Id[Function]:
    """A numbered field device whose function `signal` is bound to `channel`."""
    function = plant.function(plant.item(device, designation=designation), "signal")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, (device, "signal", "request")),
            key=(device, "signal", "request"),
            subject=function,
            signal=SignalType.DI,
            signal_name=f"tag_{device}",
            priority=1,
        ),
        PlcBindingFacet(
            id=make_id(PlcBindingFacet, (device, "signal", "plc_binding")),
            key=(device, "signal", "plc_binding"),
            subject=function,
            channel=channel,
        ),
    )
    return function


def make_plc(plant: Plant) -> tuple[list[Id[Function]], Id[Function], Terminal]:
    """A DI, an AI and a DI channel; device `dev` on the first, wired to a terminal, at `+C1`."""
    channels = make_channels(
        plant, "mod", "A1", (SignalType.DI, SignalType.AI_CURRENT, SignalType.DI)
    )
    device = bind_device(plant, "dev", "B7", channels[0])
    plant.item("x2", designation="X2")
    terminal = make_terminal(plant, "x2", "t1", group="S", index=1)
    plant.wire(plant.port(device, "1"), terminal.external, key="dev-wire")
    location = AspectNode(
        id=make_id(AspectNode, ("c1",)),
        key=("c1",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="Invented",
    )
    product = AspectNode(
        id=make_id(AspectNode, ("k9",)),
        key=("k9",),
        aspect=Aspect.PRODUCT,
        parent=None,
        label="-K9",
        description="Invented",
    )
    dev_item = make_id(Item, ("dev",))
    plant.add(
        location,
        product,
        make_placement("dev-product", dev_item, product.id),
        make_placement("dev-location", dev_item, location.id),
    )
    return channels, device, terminal


def make_placement(key: str, item: Id[Item], node: Id[AspectNode]) -> Placement:
    """A placement of `item` at `node`."""
    return Placement(id=make_id(Placement, (key,)), key=(key,), item=item, node=node)


def make_node(
    key: str, parent: Id[AspectNode] | None, aspect: Aspect = Aspect.LOCATION
) -> AspectNode:
    """An aspect node labelled with its upper-cased key."""
    return AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=aspect,
        parent=parent,
        label=key.upper(),
        description="Invented",
    )


def reversed_tables(model: Model) -> Model:
    """Tables backwards, under another digest so the model's own cached result is not reused.

    The digest names the model it came from: the caches are keyed by digest alone, so one
    fixed digest for every model would hand one test's cached result to another.
    """
    backwards = dataclasses.replace(
        model,
        digest=f"reversed-{model.digest}",
        tables=type(model.tables)(
            {
                kind: type(table)(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert list(backwards.tables) != list(model.tables)
    return backwards


def make_part(
    plant: Plant, key: str, mpn: str, *, category: PartCategory = PartCategory.GENERIC
) -> Id[Part]:
    """A part with this `mpn`, generic unless `category` says otherwise."""
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=mpn,
        manufacturer="Example Co",
        description=f"Invented {key}",
        category=category,
        class_code="K",
    )
    plant.add(part)
    return part.id


def make_core(
    plant: Plant, name: str, cable: Id[Item], ends: tuple[Id[Port], Id[Port]], *, index: int
) -> Id[Any]:
    """A core of `cable` between `ends`, with a `core` facet and a colour `colour-{index}`.

    A core's colour is its cable product's `core_colours[index - 1]` (SC4): `cable` gets a part
    and a product when it has none, and a product with fewer colours than `index` grows.
    """
    conductor = plant.core(*ends, key=name, carrier=cable)
    plant.add(
        CoreFacet(
            id=make_id(CoreFacet, (name, "facet")),
            key=(name, "facet"),
            subject=conductor,
            index=index,
        )
    )
    _colour_core(plant, cable, index)
    return conductor


def _colour_core(plant: Plant, cable: Id[Item], index: int) -> None:
    """Make `cable`'s product hold a colour at `index`, `colour-{index}` when it has none."""
    item = next(r for r in plant.records if r.id == cable)
    if item.part is None:
        name = "-".join(item.key)
        part = make_part(plant, f"{name}-part", f"MPN-{name}")
        plant.records[plant.records.index(item)] = item = dataclasses.replace(item, part=part)
    product = next(
        (r for r in plant.records if isinstance(r, CableProductFacet) and r.subject == item.part),
        None,
    )
    if product is None:
        key = ("-".join(item.key), "auto-product")
        product = CableProductFacet(
            id=make_id(CableProductFacet, key),
            key=key,
            subject=item.part,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        )
        plant.add(product)
    colours = product.core_colours
    colours += tuple(f"colour-{n}" for n in range(len(colours) + 1, index + 1))
    plant.records[plant.records.index(product)] = dataclasses.replace(product, core_colours=colours)


def make_labelled(plant: Plant, key: str, a: Id[Port], b: Id[Port], label: str | None) -> Id[Any]:
    """A wire between `a` and `b` with a `wire` facet carrying `label`."""
    conductor = plant.wire(a, b, key=key)
    plant.add(
        WireFacet(
            id=make_id(WireFacet, (key, "facet")),
            key=(key, "facet"),
            subject=conductor,
            colour="black",
            gauge_mm2=Decimal("0.75"),
            length_mm=None,
            label=label,
        )
    )
    return conductor


def ports_against_ids(plant: Plant, count: int) -> list[Id[Port]]:
    """`count` numbered ports; `K1`, `K2`... run opposite to their ids, so the later one is `a`."""
    keys = [f"i{n}" for n in range(count)]
    by_id = sorted(keys, key=lambda k: make_id(Port, (k, "f", "1")), reverse=True)
    return [make_pin(plant, key, f"K{n}") for n, key in enumerate(by_id, start=1)]


def leg_net(plant: Plant, *, wired_to: int | None) -> tuple[Id[Net], Id[Item], list[Id[Port]]]:
    """Net of one port on `src` and two on other items; `src` wired to candidate `wired_to`."""
    src = make_pin(plant, "src", "S1")
    candidates = sorted(make_pin(plant, f"far-{n}", f"F{n}") for n in (1, 2))
    if wired_to is not None:
        plant.wire(src, candidates[wired_to], key="leg")
    net = plant.net("n", (src, *candidates))
    return net, item_of(plant, src), candidates


def make_footprint(plant: Plant, key: str, name: str) -> Id[Part]:
    """A part with a `footprint` facet."""
    part_id = make_part(plant, f"fp-{key}", f"MPN-{key}")
    plant.add(
        FootprintFacet(
            id=make_id(FootprintFacet, (key, "footprint")),
            key=(key, "footprint"),
            subject=part_id,
            library="ExampleLib",
            name=name,
        )
    )
    return part_id


def make_board(plant: Plant) -> Id[Item]:
    """Board `A1` with resistors `R2` and `R10`."""
    board = plant.item("board", designation="A1")
    resistor = make_footprint(plant, "r", "R_0603")
    for key, designation in (("r2", "R2"), ("r10", "R10")):
        plant.item(key, parent=board, part=resistor, designation=designation)
    return board


def make_tree(plant: Plant) -> dict[str, Id[AspectNode]]:
    """`root` > `left` > `leaf`, `root` > `right` (a PRODUCT node), and a separate `lone`."""
    nodes = {
        "root": make_node("root", None),
        "left": make_node("left", make_id(AspectNode, ("root",))),
        "leaf": make_node("leaf", make_id(AspectNode, ("left",))),
        "right": make_node("right", make_id(AspectNode, ("root",)), Aspect.PRODUCT),
        "lone": make_node("lone", None),
    }
    plant.add(*nodes.values())
    return {name: node.id for name, node in nodes.items()}


def with_ext(plant: Plant, record_id: Id[Any], ext: dict[str, Any]) -> None:
    """Give the record `ext` (replaced in place; records are frozen)."""
    record = next(r for r in plant.records if r.id == record_id)
    plant.records.remove(record)
    plant.add(dataclasses.replace(record, ext=frozendict(ext)))
