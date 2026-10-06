"""Builders for the current-chain tests: strings of two-port devices on a `Plant`.

Invented data only. Every device is an item `key` with one function `f`; a hub is a one-port
wiring point, so several ports may be wired to one node. A device is rated in DC and in AC, and
may state a source limit in either kind. A port may stand on rails (a `Net` with that potential),
as `rating_plant.load` does, so a check test can put a string on a supply.
"""

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.kernel import make_id
from fransys_model.vocab import Operating, OperatingFacet, PartRatingFacet, Rating
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import FunctionKind, LinkKind, PortRole
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Port, Unit
    from fransys_model.vocab.templates import Part

Ports = tuple["Id[Port]", "Id[Port]"]


def wire(plant: Plant, first: Id[Port], second: Id[Port]) -> None:
    """Add a conductor between two ports, keyed by how many records the plant holds."""
    plant.wire(first, second, key=f"w{len(plant.records)}")


def rate(
    plant: Plant,
    key: str,
    amps: str | None,
    *,
    partial: bool = False,
    amps_ac: str | None = None,
) -> Id[Part]:
    """The part of item `key`, rated `amps` DC and `amps_ac` AC when given.

    A partial-range fuse when `partial`.
    """
    part = plant.part(key)
    if amps is not None or amps_ac is not None:
        rating = Rating(
            current_dc_a=None if amps is None else Decimal(amps),
            current_ac_a=None if amps_ac is None else Decimal(amps_ac),
            min_breaking_current_a=Decimal(4000) if partial else None,
        )
        facet = PartRatingFacet(
            id=make_id(PartRatingFacet, (key,)), key=(key,), subject=part, rating=rating
        )
        plant.add(facet)
    return part


def device(  # noqa: PLR0913 -- one keyword per thing a test varies
    plant: Plant,
    key: str,
    *,
    amps: str | None = None,
    amps_ac: str | None = None,
    limit: str | None = None,
    limit_ac: str | None = None,
    link: LinkKind | None = None,
    kind: FunctionKind = FunctionKind.GENERIC,
    partial: bool = False,
    rails: Sequence[Sequence[str]] = (),
) -> Ports:
    """Item `key`: one function `f` with ports `1` and `2`, rated `amps`, limited `limit`.

    The `_ac` keywords give the AC values. With `link` the two pins are tied by an internal
    link of that kind; without, the function is a two-port source or load. `rails` names, per
    port, the potentials it stands on (none by default).
    """
    part = rate(plant, key, amps, partial=partial, amps_ac=amps_ac)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "f")), key=(key, "f"), part=part, name="f", kind=kind
    )
    pins = [
        PortTemplate(
            id=make_id(PortTemplate, (key, "f", name)),
            key=(key, "f", name),
            function=template.id,
            name=name,
            role=PortRole.GENERIC,
        )
        for name in ("1", "2")
    ]
    plant.add(template, *pins)
    if link is not None:
        plant.link(pins[0], pins[1], link, key=f"link-{key}")
    if limit is not None or limit_ac is not None:
        operating = Operating(
            max_current_dc_a=None if limit is None else Decimal(limit),
            max_current_ac_a=None if limit_ac is None else Decimal(limit_ac),
        )
        facet_id = make_id(OperatingFacet, (key,))
        plant.add(OperatingFacet(id=facet_id, key=(key,), subject=template.id, operating=operating))
    function = plant.function(plant.item(key, part=part), "f", template=template.id, kind=kind)
    ports = (
        plant.port(function, "1", template=pins[0].id),
        plant.port(function, "2", template=pins[1].id),
    )
    for index, (port, potentials) in enumerate(zip(ports, rails, strict=False)):
        for potential in potentials:
            plant.net(f"{key}-{index}-{potential}", (port,), potential=potential)
    return ports


def fuse(
    plant: Plant,
    key: str,
    amps: str | None = "400",
    *,
    partial: bool = False,
    amps_ac: str | None = None,
) -> Ports:
    """A `protection` device with a conductive link, rated `amps` DC (`partial`: partial-range)."""
    kind = FunctionKind.PROTECTION
    link = LinkKind.CONDUCTIVE
    return device(plant, key, amps=amps, amps_ac=amps_ac, link=link, kind=kind, partial=partial)


def contactor(plant: Plant, key: str, amps: str | None = "150") -> Ports:
    """A contact device with a switched link (counted closed), rated `amps` DC."""
    return device(plant, key, amps=amps, link=LinkKind.SWITCHED, kind=FunctionKind.CONTACT_NO)


def connector(plant: Plant, key: str, *, amps: str | None = None) -> Id[Port]:
    """Item `key`: a connector function `f` with the one port `p`."""
    part = rate(plant, key, amps)
    function = plant.function(plant.item(key, part=part), "f", kind=FunctionKind.CONNECTOR)
    return plant.port(function, "p")


def mated(plant: Plant, plug: str, socket: str, *, amps: str | None = None) -> Ports:
    """A plug and its socket, mated; the plug is rated `amps`. Returns the two ports."""
    ports = connector(plant, plug, amps=amps), connector(plant, socket)
    plant.mate(Plant.function_id(plug, "f"), Plant.function_id(socket, "f"), key=f"mate-{plug}")
    return ports


def run(plant: Plant, start: Id[Port], devices: Sequence[Ports], end: Id[Port] | None) -> None:
    """Wire `start`, each device's two ports in turn, then `end`, into one line."""
    at = start
    for first, second in devices:
        wire(plant, at, first)
        at = second
    if end is not None:
        wire(plant, at, end)


def hub(plant: Plant, key: str) -> Id[Port]:
    """A one-port wiring point, so several ports may be wired to one node."""
    return plant.pin(key, "f", "p")


def external(plant: Plant, key: str) -> Id[Port]:
    """An external item `key` with one function `f` and one port `p`: somewhere current may leave.

    Returns the port. A string that ends here is open, so the outside closes its loop.
    """
    item = Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None,
        parent=None,
        position=None,
        tag=None,
        description="Invented",
        external=True,
    )
    plant.add(item)
    return plant.port(plant.function(item.id, "f"), "p")


def open_string(plant: Plant, source: Ports, devices: Sequence[Ports], key: str = "T") -> None:
    """Both ends of the line `source`, then `devices` open: each ends at an external item.

    The items are `key` + `0` (on the source's first port) and `key` + `1` (the far end).
    """
    wire(plant, source[0], external(plant, f"{key}0"))
    run(plant, source[1], devices, external(plant, f"{key}1"))


def sense_pin(plant: Plant, key: str) -> None:
    """Give item `key` (made by `device`) a second function `m` with one pin `p`, linked to the
    first port of its function `f` by an internal link: a link from a port to another function."""
    part = plant.part(key)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "m")),
        key=(key, "m"),
        part=part,
        name="m",
        kind=FunctionKind.GENERIC,
    )
    pin = PortTemplate(
        id=make_id(PortTemplate, (key, "m", "p")),
        key=(key, "m", "p"),
        function=template.id,
        name="p",
        role=PortRole.GENERIC,
    )
    link_key = (key, "m-link")
    link = InternalLink(
        id=make_id(InternalLink, link_key),
        key=link_key,
        a=pin.id,
        b=make_id(PortTemplate, (key, "f", "1")),
        kind=LinkKind.CONDUCTIVE,
    )
    plant.add(template, pin, link)
    function = plant.function(make_id(Item, (key,)), "m", template=template.id)
    plant.port(function, "p", template=pin.id)


def changeover(
    plant: Plant, key: str, amps: str | None = "500"
) -> tuple[Id[Port], Id[Port], Id[Port]]:
    """A changeover contact `key`: `com` switched to `no` (made when operated) and to `nc`
    (closed at rest), rated `amps` DC (`None`: unrated, so both links are plain wires).

    The port templates carry the roles `COMMON`, `MAKE` and `BREAK`, which `link_state` reads.
    Returns the ports (`com`, `no`, `nc`).
    """
    part = rate(plant, key, amps)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "f")),
        key=(key, "f"),
        part=part,
        name="f",
        kind=FunctionKind.CONTACT_CO,
    )
    pins = [
        PortTemplate(
            id=make_id(PortTemplate, (key, "f", name)),
            key=(key, "f", name),
            function=template.id,
            name=name,
            role=role,
        )
        for name, role in (
            ("com", PortRole.COMMON),
            ("no", PortRole.MAKE),
            ("nc", PortRole.BREAK),
        )
    ]
    plant.add(template, *pins)
    plant.link(pins[0], pins[1], LinkKind.SWITCHED, key=f"link-{key}-no")
    plant.link(pins[0], pins[2], LinkKind.SWITCHED, key=f"link-{key}-nc")
    function = plant.function(
        plant.item(key, part=part), "f", template=template.id, kind=FunctionKind.CONTACT_CO
    )
    com, no, nc = (plant.port(function, pin.name, template=pin.id) for pin in pins)
    return com, no, nc


def make_and_break(plant: Plant, key: str) -> tuple[Ports, Ports]:
    """One item `key` with two contacts in one part: a make contact `no` and a break contact `nc`.

    Each is a function with two ports (`1`, `2`) and one switched link, rated 500 A DC. Returns
    the ports of `no` (closed when operated) and of `nc` (closed at rest): CS1 moves them together.
    """
    part = rate(plant, key, "500")
    item = plant.item(key, part=part)
    made = []
    for name, kind in (("no", FunctionKind.CONTACT_NO), ("nc", FunctionKind.CONTACT_NC)):
        template = FunctionTemplate(
            id=make_id(FunctionTemplate, (key, name)),
            key=(key, name),
            part=part,
            name=name,
            kind=kind,
        )
        pins = [
            PortTemplate(
                id=make_id(PortTemplate, (key, name, pin)),
                key=(key, name, pin),
                function=template.id,
                name=pin,
                role=PortRole.GENERIC,
            )
            for pin in ("1", "2")
        ]
        plant.add(template, *pins)
        plant.link(pins[0], pins[1], LinkKind.SWITCHED, key=f"link-{key}-{name}")
        function = plant.function(item, name, template=template.id, kind=kind)
        made.append(
            (
                plant.port(function, "1", template=pins[0].id),
                plant.port(function, "2", template=pins[1].id),
            )
        )
    return made[0], made[1]


def switch_string(
    plant: Plant, tag: str, count: int, *, tap: bool = False, through: str = "make"
) -> None:
    """`T0 - S - C0 - C1 - ... - D - T1`: a 186 A source, `count` unrated changeovers in series
    and a 20 A load; item keys start with `tag`. With `tap` a second external item sits after `S`.

    Each changeover passes its `through` throw into the next node (`make`, closed when
    operated, or `break`, closed at rest); the other throw is wired to nothing. So the line is a
    loop through the outside only when every changeover is in the state that closes it.
    """
    source = device(plant, f"{tag}S", limit="186")
    wire(plant, source[0], external(plant, f"{tag}T0"))
    node = source[1]
    for at in range(count):
        common, make, brk = changeover(plant, f"{tag}C{at:02d}", None)
        wire(plant, node, common)
        node = make if through == "make" else brk
    load = device(plant, f"{tag}D", amps="20")
    wire(plant, node, load[0])
    wire(plant, load[1], external(plant, f"{tag}T1"))
    if tap:
        wire(plant, source[1], external(plant, f"{tag}Ta"))


def capped_changeover(plant: Plant, others: int, source: Ports, d_amps: str = "150") -> None:
    """The plant where opening an unrated changeover's links gives a false bound.

    An unrated changeover `CO` (the one of `others + 1` with the LARGEST item id, so the one
    above the enumeration cap when they are more than the cap) with `D` (rated `d_amps`) from its
    common to `X`, `P` from `X` to its break port, `R` from there to its make port, `source`
    (limited to 400 A) from the make port to `Y`, `Q` from `Y` to the common, and a 100 A
    full-range fuse `L` from `X` to `Y`. The `others` unrated changeovers hang their commons on
    `Y`. Every real state of `CO` has `L` on each loop through `D` (bound 100 A); with all its
    links open the loop `D, P, R, source, Q` avoids `L` (bound 400 A).
    """
    names = [f"C{n}" for n in range(others + 1)]
    chosen = max(names, key=lambda name: make_id(Item, (name,)))
    x, y = hub(plant, "X"), hub(plant, "Y")
    common, make, brk = changeover(plant, chosen, None)
    for name in names:
        if name != chosen:
            wire(plant, y, changeover(plant, name, None)[0])

    def between(pair: Ports, first: Id[Port], second: Id[Port]) -> None:
        wire(plant, first, pair[0])
        wire(plant, pair[1], second)

    between(device(plant, "D", amps=d_amps), common, x)
    between(device(plant, "P", amps="500"), x, brk)
    between(device(plant, "R", amps="500"), brk, make)
    between(source, make, y)
    between(device(plant, "Q", amps="500"), y, common)
    between(fuse(plant, "L", "100"), x, y)


def shorted_when_closed(plant: Plant, source: Ports, d_amps: str = "100") -> None:
    """`T0 - source - CO.common`, `D` from the common to the make port, `T1` on the make port.

    `CO` is an unrated changeover: at rest its common joins its break port and `D` lies on the
    loop with the source; operated, the common joins the make port and shorts `D`. With every
    link closed `D` is shorted too, yet it has its bound at rest.
    """
    common, make, _ = changeover(plant, "CO", None)
    wire(plant, source[0], external(plant, "T0"))
    wire(plant, source[1], common)
    load = device(plant, "D", amps=d_amps)
    wire(plant, common, load[0])
    wire(plant, load[1], make)
    wire(plant, make, external(plant, "T1"))


def in_unit(plant: Plant, unit: Id[Unit]) -> None:
    """Put every item of the plant into `unit`, so that the plant is that unit built alone."""
    plant.records[:] = [
        dataclasses.replace(record, unit=unit) if isinstance(record, Item) else record
        for record in plant.records
    ]


def with_role(plant: Plant, port: Id[Port], role: PortRole) -> None:
    """Give the port `port` of the plant the role `role` (the plant's ports are `GENERIC`)."""
    plant.records[:] = [
        dataclasses.replace(record, role=role) if record.id == port else record
        for record in plant.records
    ]


def bypass_plant(
    *, fuse_in_branch: bool = False, prefix: str = "", main_fuse: str = "400"
) -> Plant:
    """Source, fuse, a contactor with a precharge branch around it, plug, load; unrated leads.

    `S - F - N1 - [K || (R - PK)] - N2 - plug ~ sock - Z`, an unrated sense lead on each node
    and an unrated insulation monitor between them. The source `S` is limited to 186 A and the
    fuse `F` rated `main_fuse` A. With `fuse_in_branch` the branch holds its own 10 A full-range
    fuse `PF` and `PK` is rated 20 A. Every item key gets `prefix`, which changes the ids and so
    their order without changing the plant.
    """

    def k(name: str) -> str:
        return prefix + name

    plant = Plant()
    source = device(plant, k("S"), limit="186")
    wire(plant, source[0], external(plant, k("T0")))
    n1, n2 = hub(plant, k("N1")), hub(plant, k("N2"))
    run(plant, source[1], [fuse(plant, k("F"), main_fuse)], n1)
    run(plant, n1, [contactor(plant, k("K"))], n2)
    branch = [
        device(plant, k("R"), amps="5", link=LinkKind.CONDUCTIVE),
        contactor(plant, k("PK"), "20" if fuse_in_branch else "5"),
    ]
    if fuse_in_branch:
        branch.append(fuse(plant, k("PF"), "10"))
    run(plant, n1, branch, n2)
    run(plant, n1, [device(plant, k("sense1"))], None)
    run(plant, n2, [device(plant, k("sense2"))], None)
    run(plant, n1, [device(plant, k("imd"))], n2)
    plug, socket = mated(plant, k("plug"), k("sock"), amps="100")
    wire(plant, n2, plug)
    load = device(plant, k("Z"), amps="20")
    wire(plant, socket, load[0])
    wire(plant, load[1], external(plant, k("T1")))
    return plant
