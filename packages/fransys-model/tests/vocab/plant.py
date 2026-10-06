"""A small builder of invented plants for the connectivity tests (closure and validator).

Every id comes from `make_id` over a key the test chooses, so nothing depends on a hand-made
hex string. Nothing here names a real project.
"""

from typing import Any

from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.core import Function, Item, Port, Unit, UnitRelease
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    LinkKind,
    NetClass,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.revision import Revision
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate
from fransys_model.vocab.units import Boundary, UnusedBoundary

_ORIGIN = Origin(file="plant.py", line=1, note="fixture")


class Plant:
    """Collects records; `model()` freezes them."""

    def __init__(self) -> None:
        """Start with no records."""
        self.records: list[Any] = []

    def add(self, *records: Any) -> None:
        """Add ready-made records."""
        self.records.extend(records)

    def has(self, record_id: Id[Any]) -> bool:
        """Whether a record with this id was added."""
        return any(record.id == record_id for record in self.records)

    def item(  # noqa: PLR0913 -- one param per Item field the tests vary, kept explicit
        self,
        key: str,
        *,
        installed: bool = True,
        parent: Id[Item] | None = None,
        part: Id[Part] | None = None,
        designation: str | None = None,
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
            description="Invented",
            installed=installed,
            unit=unit,
        )
        self.add(item)
        return item.id

    def release(
        self,
        name: str = "unit",
        revision: int = 1,
        interface: str = "1",
        version: int = 1,
        class_code: str = "",
    ) -> Id[UnitRelease]:
        """Add (once) the release `(name, version, revision)` and return its id."""
        release_key = ("unit_release", name, str(version), str(revision))
        release = UnitRelease(
            id=make_id(UnitRelease, release_key),
            key=release_key,
            name=name,
            version=version,
            revision=revision,
            interface=interface,
            class_code=class_code,
        )
        if not self.has(release.id):
            self.add(release)
        return release.id

    def unit(  # noqa: PLR0913 -- one param per Unit/UnitRelease field the tests vary
        self,
        key: str,
        *,
        name: str = "unit",
        revision: int = 1,
        interface: str = "1",
        parent: Id[Unit] | None = None,
        version: int = 1,
        tag: str | None = None,
        class_code: str = "",
    ) -> Id[Unit]:
        """Add a unit keyed `(key,)`, an instance of the release `(name, version, revision)`."""
        release = self.release(name, revision, interface, version, class_code)
        unit = Unit(id=make_id(Unit, (key,)), key=(key,), release=release, parent=parent, tag=tag)
        self.add(unit)
        return unit.id

    def revision(self, unit: Id[Unit], revision: int = 1, version: int = 1) -> Id[Revision]:
        """Add the history entry for `unit`'s release at `(version, revision)` (missing: ERROR)."""
        key = (*self._key_of(unit), "revision", str(revision))
        release = next(record.release for record in self.records if record.id == unit)
        entry = Revision(
            id=make_id(Revision, key),
            key=key,
            release=release,
            version=version,
            revision=revision,
            date="2026-01-01",
            text="First release",
            created="XX",
        )
        self.add(entry)
        return entry.id

    def part(self, class_code: str) -> Id[Part]:
        """Add (once) a part of `class_code`, keyed by it."""
        part_id = make_id(Part, (f"part-{class_code}",))
        if not self.has(part_id):
            self.add(
                Part(
                    id=part_id,
                    key=(f"part-{class_code}",),
                    mpn=f"EXAMPLE-{class_code}",
                    manufacturer="Example Co",
                    description="Invented",
                    category=PartCategory.GENERIC,
                    class_code=class_code,
                )
            )
        return part_id

    def function(
        self,
        item: Id[Item],
        name: str,
        *,
        template: Id[FunctionTemplate] | None = None,
        kind: FunctionKind = FunctionKind.GENERIC,
    ) -> Id[Function]:
        """Add a function of `item`, keyed by the item's key and `name`."""
        key = (*self._key_of(item), name)
        function = Function(
            id=make_id(Function, key),
            key=key,
            item=item,
            template=template,
            name=name,
            kind=kind,
        )
        self.add(function)
        return function.id

    def port(
        self,
        function: Id[Function],
        name: str,
        *,
        template: Id[PortTemplate] | None = None,
        again: str = "",
    ) -> Id[Port]:
        """Add a port called `name`; `again` tells the key of a second port of that name apart."""
        key = (*self._key_of(function), name + again)
        port = Port(
            id=make_id(Port, key),
            key=key,
            function=function,
            template=template,
            name=name,
            role=PortRole.GENERIC,
        )
        self.add(port)
        return port.id

    def pin(self, item: str, function: str, port: str) -> Id[Port]:
        """A port by three names, making the item and function on first use."""
        item_id = make_id(Item, (item,))
        if not self.has(item_id):
            self.item(item)
        function_id = make_id(Function, (item, function))
        if not self.has(function_id):
            self.function(item_id, function)
        port_id = make_id(Port, (item, function, port))
        if not self.has(port_id):
            self.port(function_id, port)
        return port_id

    @staticmethod
    def function_id(item: str, function: str) -> Id[Function]:
        """The id `pin` gives the function of item `item` called `function`."""
        return make_id(Function, (item, function))

    def wire(
        self,
        a: Id[Port],
        b: Id[Port],
        *,
        key: str,
        kind: ConductorKind = ConductorKind.WIRE,
    ) -> Id[Conductor]:
        """Add a conductor between two ports."""
        conductor = Conductor(
            id=make_id(Conductor, (key,)),
            key=(key,),
            a=a,
            b=b,
            kind=kind,
            carrier=None,
        )
        self.add(conductor)
        return conductor.id

    def core(self, a: Id[Port], b: Id[Port], *, key: str, carrier: Id[Item]) -> Id[Conductor]:
        """Add a core conductor carried by the cable item `carrier`."""
        conductor = Conductor(
            id=make_id(Conductor, (key,)),
            key=(key,),
            a=a,
            b=b,
            kind=ConductorKind.CORE,
            carrier=carrier,
        )
        self.add(conductor)
        return conductor.id

    def net(
        self,
        key: str,
        ports: tuple[Id[Port], ...],
        *,
        potential: str | None = None,
        name: str | None = None,
    ) -> Id[Net]:
        """Add a declared net."""
        net = Net(
            id=make_id(Net, (key,)),
            key=(key,),
            name=name,
            net_class=NetClass.GENERIC,
            ports=ports,
            potential=potential,
        )
        self.add(net)
        return net.id

    def mate(self, a: Id[Function], b: Id[Function], *, key: str = "mate") -> Id[Mate]:
        """Add a mate between two connector functions."""
        mate = Mate(id=make_id(Mate, (key,)), key=(key,), a=a, b=b)
        self.add(mate)
        return mate.id

    def boundary(
        self, unit: Id[Unit], function: Id[Function], *, key: str = "boundary"
    ) -> Id[Boundary]:
        """Add a `Boundary`: `function` is part of `unit`'s interface."""
        boundary = Boundary(id=make_id(Boundary, (key,)), key=(key,), unit=unit, function=function)
        self.add(boundary)
        return boundary.id

    def unused(self, function: Id[Function], *, key: str = "unused") -> Id[UnusedBoundary]:
        """Add an `UnusedBoundary`: `function` is left unconnected on purpose."""
        unused = UnusedBoundary(id=make_id(UnusedBoundary, (key,)), key=(key,), function=function)
        self.add(unused)
        return unused.id

    def relay_part(self) -> tuple[Part, FunctionTemplate, PortTemplate, PortTemplate]:
        """Add a part with one function template of two ports; the caller adds links."""
        part = Part(
            id=make_id(Part, ("relay",)),
            key=("relay",),
            mpn="EXAMPLE-1",
            manufacturer="Example Co",
            description="Invented",
            category=PartCategory.ELECTROMECHANICAL,
            class_code="K",
        )
        template = FunctionTemplate(
            id=make_id(FunctionTemplate, ("relay", "fn")),
            key=("relay", "fn"),
            part=part.id,
            name="fn",
            kind=FunctionKind.GENERIC,
        )
        pins = tuple(
            PortTemplate(
                id=make_id(PortTemplate, ("relay", "fn", name)),
                key=("relay", "fn", name),
                function=template.id,
                name=name,
                role=PortRole.GENERIC,
            )
            for name in ("1", "2")
        )
        self.add(part, template, *pins)
        return part, template, pins[0], pins[1]

    def link(
        self, a: PortTemplate, b: PortTemplate, kind: LinkKind, *, key: str = "link"
    ) -> InternalLink:
        """Add an internal link between two port templates."""
        link = InternalLink(id=make_id(InternalLink, (key,)), key=(key,), a=a.id, b=b.id, kind=kind)
        self.add(link)
        return link

    def board_part(self) -> Id[Part]:
        """Add a part that carries the `pcb` facet."""
        part = Part(
            id=make_id(Part, ("board",)),
            key=("board",),
            mpn="EXAMPLE-BOARD",
            manufacturer="Example Co",
            description="Invented",
            category=PartCategory.BOARD,
            class_code="A",
        )
        facet = PcbFacet(
            id=make_id(PcbFacet, ("board", "pcb")),
            key=("board", "pcb"),
            subject=part.id,
            revision="A",
        )
        self.add(part, facet)
        return part.id

    def model(self) -> Model:
        """Freeze everything added."""
        draft = Draft()
        draft.extend(self.records, origin=_ORIGIN)
        return freeze(draft)

    def _key_of(self, record_id: Id[Any]) -> tuple[str, ...]:
        return next(record.key for record in self.records if record.id == record_id)
