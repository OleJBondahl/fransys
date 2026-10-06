"""Helpers both synthetic designs share: stamp parts and items, wire ports by name (WP17).

Every id comes from `make_id` over a key the design chooses, and instance keys are the ones
`instantiate` builds, so no design hand-writes a hex id or a second key rule. All data is
invented (CLAUDE.md invariant, red flag "Real project data in fixtures").
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_model.kernel import Draft, Id, Origin, make_id
from fransys_model.vocab import PartBundle, instantiate
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import Aspect, ConductorKind, Current, NetClass
from fransys_model.vocab.facets.cable import CoreFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.supply_system import Rail, SupplySystem
from fransys_model.vocab.templates import (
    FunctionTemplate,
    InternalLink,
    Part,
    PartLibrary,
    PortTemplate,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Record
    from fransys_model.vocab.enums import FunctionKind, LinkKind, PartCategory, PortRole

type Pins = tuple[tuple[str, PortRole], ...]
type Functions = dict[str, tuple[FunctionKind, Pins]]
type Links = tuple[tuple[tuple[str, str], tuple[str, str], LinkKind], ...]


@dataclass(frozen=True, slots=True)
class PartSpec:
    """What a part is: identity, class letter, and the functions and links its templates hold."""

    key: str
    mpn: str
    letter: str
    category: PartCategory
    functions: Functions = field(default_factory=dict)
    links: Links = ()


@dataclass(frozen=True, slots=True)
class Slot:
    """Where an item sits and whether it is installed."""

    designation: str | None
    parent: Id[Item] | None = None
    position: int | None = None
    installed: bool = True


@dataclass(frozen=True, slots=True)
class Node:
    """An aspect node the design placed items at."""

    id: Id[AspectNode]
    key: str


@dataclass(frozen=True, slots=True)
class Ref:
    """A stamped item: its id and, by name, its functions and ports."""

    item: Id[Item]
    key: tuple[str, ...]
    functions: dict[str, Id[Function]]
    function_keys: dict[str, tuple[str, ...]]
    ports: dict[tuple[str, str], Id[Port]]

    def function(self, name: str) -> Id[Function]:
        """The function called `name`."""
        return self.functions[name]

    def port(self, function: str, pin: str) -> Id[Port]:
        """The port called `pin` of the function called `function`."""
        return self.ports[function, pin]


def _supplies() -> tuple[SupplySystem, ...]:
    """The two invented supplies every design's net potentials name (POTENTIAL_WITHOUT_SUPPLY)."""
    dc = {
        name: Rail(max_v=Decimal(volts), phase=None)
        for name, volts in (("+24V", 24), ("+5V", 5), ("0V", 0))
    }
    ac = {f"L{n}": Rail(max_v=Decimal(230), phase=(n - 1) * 120) for n in (1, 2, 3)}
    return tuple(
        SupplySystem(
            id=make_id(SupplySystem, (name,)),
            key=(name,),
            name=name,
            current=current,
            rails=frozendict(rails),
        )
        for name, current, rails in (("24V", Current.DC, dc), ("400V", Current.AC, ac))
    )


class Kit:
    """A `Draft` and the small vocabulary the two designs are written in."""

    def __init__(self, source: str) -> None:
        """Start a draft holding the invented part library; records are attributed to `source`."""
        self.draft = Draft()
        self._origin = Origin(file=source, line=1, note="synthetic use case")
        self._library = PartLibrary(
            id=make_id(PartLibrary, ("part_library", "invented-parts")),
            key=("part_library", "invented-parts"),
            name="invented-parts",
            version="1.0.0",
        )
        self.add(self._library, *_supplies())

    def add(self, *records: Record) -> None:
        """Add ready-made records."""
        self.draft.extend(records, origin=self._origin)

    def facet(self, cls: Any, key: tuple[str, ...], **fields: Any) -> None:
        """Add a facet of type `cls`, whose id is derived from `key`."""
        self.add(cls(id=make_id(cls, key), key=key, **fields))

    def part(self, spec: PartSpec) -> PartBundle:
        """A part with its function templates, port templates and internal links."""
        part = Part(
            id=make_id(Part, (spec.key,)),
            key=(spec.key,),
            mpn=spec.mpn,
            manufacturer="Example Co",
            description=f"Invented {spec.mpn}",
            category=spec.category,
            class_code=spec.letter,
            library=self._library.id,
        )
        function_templates = []
        port_templates = []
        for name, (kind, pins) in spec.functions.items():
            template = FunctionTemplate(
                id=make_id(FunctionTemplate, (spec.key, name)),
                key=(spec.key, name),
                part=part.id,
                name=name,
                kind=kind,
            )
            function_templates.append(template)
            port_templates.extend(
                PortTemplate(
                    id=make_id(PortTemplate, (spec.key, name, pin)),
                    key=(spec.key, name, pin),
                    function=template.id,
                    name=pin,
                    role=role,
                )
                for pin, role in pins
            )
        by_key = {template.key: template.id for template in port_templates}
        internal_links = tuple(
            InternalLink(
                id=make_id(InternalLink, (spec.key, "link", str(number))),
                key=(spec.key, "link", str(number)),
                a=by_key[spec.key, *a],
                b=by_key[spec.key, *b],
                kind=link_kind,
            )
            for number, (a, b, link_kind) in enumerate(spec.links, start=1)
        )
        return PartBundle(
            part=part,
            function_templates=tuple(function_templates),
            port_templates=tuple(port_templates),
            internal_links=internal_links,
        )

    def stamp(self, bundle: PartBundle, key: tuple[str, ...], slot: Slot) -> Ref:
        """Add the bundle's own records (again: an identical record is a no-op) and one item."""
        self.add(
            bundle.part,
            *bundle.function_templates,
            *bundle.port_templates,
            *bundle.internal_links,
        )
        stamped = instantiate(
            bundle,
            key,
            tag=slot.designation,
            parent=slot.parent,
            position=slot.position,
            description=bundle.part.description,
            installed=slot.installed,
        )
        self.add(*stamped)
        names = {r.id: r.name for r in stamped if isinstance(r, Function)}
        return Ref(
            item=make_id(Item, key),
            key=key,
            functions={name: function for function, name in names.items()},
            function_keys={r.name: r.key for r in stamped if isinstance(r, Function)},
            ports={(names[r.function], r.name): r.id for r in stamped if isinstance(r, Port)},
        )

    def container(self, key: tuple[str, ...], designation: str) -> Ref:
        """A part-less item that only holds children (a terminal strip)."""
        item = Item(
            id=make_id(Item, key),
            key=key,
            part=None,
            parent=None,
            position=None,
            tag=designation,
            description="Invented container",
            installed=True,
        )
        self.add(item)
        return Ref(item=item.id, key=key, functions={}, function_keys={}, ports={})

    def wire(
        self,
        a: Id[Port],
        b: Id[Port],
        key: tuple[str, ...],
        kind: ConductorKind = ConductorKind.WIRE,
    ) -> Id[Conductor]:
        """A conductor of `kind` between two ports (a `jumper` bridges two terminals).

        A `wire` gets a `wire` facet labelled with its key, so every panel wire has a label.
        """
        conductor = self._conductor((a, b), key, kind, None)
        if kind is ConductorKind.WIRE:
            self.facet(
                WireFacet,
                (*key, "wire"),
                subject=conductor,
                colour="BU",
                gauge_mm2=Decimal("0.75"),
                length_mm=None,
                label="-".join(key).upper(),
            )
        return conductor

    def core(self, cable: Ref, index: int, ends: tuple[Id[Port], Id[Port]]) -> None:
        """Core `index` of `cable` between `ends`; its colour is the cable product's."""
        key = (*cable.key, "core", str(index))
        conductor = self._conductor(ends, key, ConductorKind.CORE, cable.item)
        self.facet(CoreFacet, (*key, "facet"), subject=conductor, index=index)

    def _conductor(
        self,
        ends: tuple[Id[Port], Id[Port]],
        key: tuple[str, ...],
        kind: ConductorKind,
        carrier: Id[Item] | None,
    ) -> Id[Conductor]:
        a, b = ends
        conductor = Conductor(
            id=make_id(Conductor, key), key=key, a=a, b=b, kind=kind, carrier=carrier
        )
        self.add(conductor)
        return conductor.id

    def net(
        self,
        key: str,
        ports: tuple[Id[Port], ...],
        *,
        net_class: NetClass,
        potential: str | None = None,
    ) -> None:
        """A declared net named `key`."""
        self.add(
            Net(
                id=make_id(Net, (key,)),
                key=(key,),
                name=key,
                net_class=net_class,
                ports=ports,
                potential=potential,
            )
        )

    def node(self, key: str, aspect: Aspect, label: str, description: str) -> Node:
        """A root aspect node."""
        node = AspectNode(
            id=make_id(AspectNode, (key,)),
            key=(key,),
            aspect=aspect,
            parent=None,
            label=label,
            description=description,
        )
        self.add(node)
        return Node(id=node.id, key=key)

    def mate(self, a: Id[Function], b: Id[Function], key: tuple[str, ...]) -> None:
        """Plug two connector functions together."""
        self.add(Mate(id=make_id(Mate, key), key=key, a=a, b=b))

    def place(self, item: Ref, *nodes: Node) -> None:
        """Place `item` at each of `nodes`."""
        for node in nodes:
            key = (*item.key, "at", node.key)
            self.add(Placement(id=make_id(Placement, key), key=key, item=item.item, node=node.id))


def template_of(bundle: PartBundle, name: str) -> Id[FunctionTemplate]:
    """The id of the function template called `name` in `bundle`."""
    return next(template.id for template in bundle.function_templates if template.name == name)
