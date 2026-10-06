"""Reusable invented example data for vocab acceptance tests (ROADMAP WP8-WP13).

All data here is invented for this repo's tests; nothing names a real project or
component (CLAUDE.md).
"""

from dataclasses import replace
from typing import Any

from fransys_model.kernel import Draft, Id, Model, Origin, Record, freeze, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    Aspect,
    ConductorKind,
    FunctionKind,
    LinkKind,
    NetClass,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.instantiate import PartBundle
from fransys_model.vocab.project import Project
from fransys_model.vocab.templates import (
    FunctionTemplate,
    InternalLink,
    Part,
    PartLibrary,
    PortTemplate,
)


def relay_part_bundle() -> PartBundle:
    """An invented relay: coil `A1`/`A2`, NO contact `13`/`14`, CO contact `11`/`12`/`14`."""
    part_key = ("examples", "relay")
    part = Part(
        id=make_id(Part, part_key),
        key=part_key,
        mpn="EXAMPLE-RELAY-1",
        manufacturer="Example Co",
        description="Invented example relay for tests",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )

    coil_key = (*part_key, "fn", "coil")
    coil = FunctionTemplate(
        id=make_id(FunctionTemplate, coil_key),
        key=coil_key,
        part=part.id,
        name="coil",
        kind=FunctionKind.COIL,
    )
    no_1_key = (*part_key, "fn", "no_1")
    no_1 = FunctionTemplate(
        id=make_id(FunctionTemplate, no_1_key),
        key=no_1_key,
        part=part.id,
        name="no_1",
        kind=FunctionKind.CONTACT_NO,
    )
    co_1_key = (*part_key, "fn", "co_1")
    co_1 = FunctionTemplate(
        id=make_id(FunctionTemplate, co_1_key),
        key=co_1_key,
        part=part.id,
        name="co_1",
        kind=FunctionKind.CONTACT_CO,
    )

    def port(
        function: FunctionTemplate, name: str, role: PortRole = PortRole.GENERIC
    ) -> PortTemplate:
        key = (*function.key, "port", name)
        return PortTemplate(
            id=make_id(PortTemplate, key), key=key, function=function.id, name=name, role=role
        )

    a1, a2 = port(coil, "A1"), port(coil, "A2")
    p13, p14 = port(no_1, "13"), port(no_1, "14")
    p11, p12, p14_co = port(co_1, "11"), port(co_1, "12"), port(co_1, "14")

    link_11_14_key = (*co_1_key, "link", "11-14")
    link_11_14 = InternalLink(
        id=make_id(InternalLink, link_11_14_key),
        key=link_11_14_key,
        a=p11.id,
        b=p14_co.id,
        kind=LinkKind.SWITCHED,
    )
    link_12_14_key = (*co_1_key, "link", "12-14")
    link_12_14 = InternalLink(
        id=make_id(InternalLink, link_12_14_key),
        key=link_12_14_key,
        a=p12.id,
        b=p14_co.id,
        kind=LinkKind.SWITCHED,
    )

    return PartBundle(
        part=part,
        function_templates=(coil, no_1, co_1),
        port_templates=(a1, a2, p13, p14, p11, p12, p14_co),
        internal_links=(link_11_14, link_12_14),
    )


def lamp_part_bundle() -> PartBundle:
    """An invented indicator lamp: one `lamp` function with ports `X1` and `X2`."""
    part_key = ("examples", "lamp")
    part = Part(
        id=make_id(Part, part_key),
        key=part_key,
        mpn="EXAMPLE-LAMP-1",
        manufacturer="Example Co",
        description="Invented example lamp for tests",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="H",
    )
    lamp_key = (*part_key, "fn", "lamp")
    lamp = FunctionTemplate(
        id=make_id(FunctionTemplate, lamp_key),
        key=lamp_key,
        part=part.id,
        name="lamp",
        kind=FunctionKind.LOAD,
    )
    ports = tuple(
        PortTemplate(
            id=make_id(PortTemplate, (*lamp_key, "port", name)),
            key=(*lamp_key, "port", name),
            function=lamp.id,
            name=name,
            role=PortRole.GENERIC,
        )
        for name in ("X1", "X2")
    )
    return PartBundle(
        part=part, function_templates=(lamp,), port_templates=ports, internal_links=()
    )


def bundle_records(bundle: PartBundle) -> tuple[Record, ...]:
    """The records a model needs before it can hold an instance of `bundle`'s part."""
    return (
        bundle.part,
        *bundle.function_templates,
        *bundle.port_templates,
        *bundle.internal_links,
    )


def terminal_block_part() -> Part:
    """An invented feed-through terminal-block `Part` (design/examples.md 11, strip
    `X03`)."""
    key = ("examples", "terminal_block")
    return Part(
        id=make_id(Part, key),
        key=key,
        mpn="EXAMPLE-TB-1",
        manufacturer="Example Co",
        description="Invented example feed-through terminal block for tests",
        category=PartCategory.TERMINAL,
        class_code="X",
    )


def cable_4_core_part() -> Part:
    """An invented 4-core cable `Part` (design/examples.md 11, cable `W012`)."""
    key = ("examples", "cable_4core")
    return Part(
        id=make_id(Part, key),
        key=key,
        mpn="EXAMPLE-CABLE-4G1.5",
        manufacturer="Example Co",
        description="Invented example 4x1.5mm2 control cable for tests",
        category=PartCategory.CABLE,
        class_code="W",
    )


_EXAMPLE_ORIGIN = Origin(file="examples.py", line=1, note="core_model")


def _key(cls: type, *key: str) -> Id[Any]:
    return make_id(cls, key)


def core_model() -> Model:
    """A frozen model holding one record of every core kind, the relay `Part` included."""
    bundle = relay_part_bundle()
    relay = _key(Item, "plant", "k1")
    coil = _key(Function, "plant", "k1", "fn", "coil")
    a1, a2 = bundle.port_templates[0], bundle.port_templates[1]
    port_a1 = _key(Port, "plant", "k1", "coil", "a1")
    port_a2 = _key(Port, "plant", "k1", "coil", "a2")
    housing = _key(Item, "plant", "housing")
    board = _key(Item, "plant", "board")
    housing_j1 = _key(Function, "plant", "housing", "j1")
    board_j1 = _key(Function, "plant", "board", "j1")
    housing_pin = _key(Port, "plant", "housing", "j1", "1")
    location = _key(AspectNode, "plant", "c1")
    net = _key(Net, "plant", "24v")
    library = PartLibrary(
        id=_key(PartLibrary, "part_library", "invented-parts"),
        key=("part_library", "invented-parts"),
        name="invented-parts",
        version="1.4.0",
    )
    records: list[Any] = [
        library,
        replace(bundle.part, library=library.id),
        *bundle.function_templates,
        *bundle.port_templates,
        *bundle.internal_links,
        Item(
            id=relay,
            key=("plant", "k1"),
            part=bundle.part.id,
            parent=None,
            position=None,
            tag="-K1",
            description="Invented relay",
        ),
        Item(
            id=housing,
            key=("plant", "housing"),
            part=None,
            parent=None,
            position=1,
            tag=None,
            description="Invented harness housing",
            installed=False,
        ),
        Item(
            id=board,
            key=("plant", "board"),
            part=None,
            parent=None,
            position=None,
            tag="A1",
            description="Invented board",
        ),
        Function(
            id=coil,
            key=("plant", "k1", "fn", "coil"),
            item=relay,
            template=bundle.function_templates[0].id,
            name="coil",
            kind=FunctionKind.COIL,
        ),
        Function(
            id=housing_j1,
            key=("plant", "housing", "j1"),
            item=housing,
            template=None,
            name="J1",
            kind=FunctionKind.CONNECTOR,
        ),
        Function(
            id=board_j1,
            key=("plant", "board", "j1"),
            item=board,
            template=None,
            name="J1",
            kind=FunctionKind.CONNECTOR,
        ),
        Port(
            id=port_a1,
            key=("plant", "k1", "coil", "a1"),
            function=coil,
            template=a1.id,
            name="A1",
            role=PortRole.GENERIC,
        ),
        Port(
            id=port_a2,
            key=("plant", "k1", "coil", "a2"),
            function=coil,
            template=a2.id,
            name="A2",
            role=PortRole.GENERIC,
        ),
        Port(
            id=housing_pin,
            key=("plant", "housing", "j1", "1"),
            function=housing_j1,
            template=None,
            name="1",
            role=PortRole.EXTERNAL,
        ),
        Net(
            id=net,
            key=("plant", "24v"),
            name="24V",
            net_class=NetClass.POWER,
            ports=tuple(reversed(sorted((port_a1, port_a2)))),
            potential="24V",
        ),
        Conductor(
            id=_key(Conductor, "plant", "w1"),
            key=("plant", "w1"),
            a=housing_pin,
            b=port_a1,
            kind=ConductorKind.WIRE,
            carrier=None,
        ),
        Mate(id=_key(Mate, "plant", "mate"), key=("plant", "mate"), a=housing_j1, b=board_j1),
        AspectNode(
            id=location,
            key=("plant", "c1"),
            aspect=Aspect.LOCATION,
            parent=None,
            label="C1",
            description="Invented enclosure",
        ),
        Placement(
            id=_key(Placement, "plant", "k1", "c1"),
            key=("plant", "k1", "c1"),
            item=relay,
            node=location,
        ),
        Project(
            id=_key(Project, "plant"),
            key=("plant",),
            title="Invented pump station",
            number="P-0001",
            customer="Invented Customer AS",
            revision=1,
            author="N. N.",
        ),
    ]
    draft = Draft()
    draft.extend(records, origin=_EXAMPLE_ORIGIN)
    return freeze(draft)
