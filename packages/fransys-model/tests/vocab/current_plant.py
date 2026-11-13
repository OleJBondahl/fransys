"""Builders for the current-chain tests: strings of two-port devices on a `Plant`.

Invented data only. Every device is an item `key` with one function `f`; a hub is a one-port
wiring point, so several ports may be wired to one node. A device is rated in DC and in AC, and
"""

from typing import TYPE_CHECKING

from rating_plant import figures, rated, states_block
lazy from plant import Plant

from fransys_model.elecdef import Fuse, LinkKind, PinRole, Range, Role, Side, Unit
from fransys_model.kernel import make_id
from fransys_model.vocab import Operating, OperatingFacet, PartRatingFacet
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import FunctionKind, PortBoundary
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Port
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
    amps_ac: str | None = None,
) -> Id[Part]:
    """The part of item `key`, rated `amps` DC and `amps_ac` AC when given."""
    part = plant.part(key)
    if amps is not None or amps_ac is not None:
        facet = PartRatingFacet(id=make_id(PartRatingFacet, (key,)), key=(key,), subject=part, rating=rated(amps_ac=amps_ac, amps_dc=amps))
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
    sided: bool = False,
    rails: Sequence[Sequence[str]] = (),
) -> Ports:
    """Item `key`: one function `f` with ports `1` and `2`, rated `amps`, limited `limit`.

    The `_ac` keywords give the AC values. With `link` the two pins are tied by an internal
    link of that kind; `sided` puts them on line and load; without, the function is a two-port source or load. `rails` names, per
    """
    part = rate(plant, key, amps, amps_ac=amps_ac)
    template = FunctionTemplate(id=make_id(FunctionTemplate, (key, "f")), key=(key, "f"), part=part, name="f", kind=kind)
    pins = [
        PortTemplate(
            id=make_id(PortTemplate, (key, "f", name)),
            key=(key, "f", name),
            function=template.id,
            name=name,
            boundary=PortBoundary.GENERIC,
            side=side if sided else None,
        )
        for name, side in (("1", Side.A), ("2", Side.B))
    ]
    plant.add(template, *pins)
    if partial:
        states_block(plant, template.id, Fuse(breaking_capacity=(Range(Role.RATED, min=Unit.A(4000)),)))
    if link is not None:
        plant.link(pins[0], pins[1], link, key=f"link-{key}")
    if limit is not None or limit_ac is not None:
        operating = Operating(max_current=figures(Unit.A, limit_ac, limit))
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


def changeover(plant: Plant, key: str, amps: str | None = "500") -> tuple[Id[Port], Id[Port], Id[Port]]:
    """A changeover contact `key`: `com` switched to `no` (made when operated) and to `nc`
    (closed at rest), rated `amps` DC (`None`: unrated, so both links are plain wires).

    The port templates carry the roles `COMMON`, `MAKE` and `BREAK`, which `link_state` reads.
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
            boundary=role if isinstance(role, PortBoundary) else PortBoundary.GENERIC,
            pin_role=role if isinstance(role, PinRole) else None,
        )
        for name, role in (
            ("com", PinRole.COMMON),
            ("no", PinRole.MAKE),
            ("nc", PinRole.BREAK),
        )
    ]
    plant.add(template, *pins)
    plant.link(pins[0], pins[1], LinkKind.SWITCHED, key=f"link-{key}-no")
    plant.link(pins[0], pins[2], LinkKind.SWITCHED, key=f"link-{key}-nc")
    function = plant.function(plant.item(key, part=part), "f", template=template.id, kind=FunctionKind.CONTACT_CO)
    com, no, nc = (plant.port(function, pin.name, template=pin.id) for pin in pins)
    return com, no, nc
