"""Hand-built models with laid-out cable blocks (the layout engine is not used).

Every coordinate is a multiple of `WIRING_GRID`. A core runs from the top end box to the bottom
one (`wire`), or is a row link whose two pins stand in one end box (`link`, CD5 at L1).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from electrical_symbols import WIRING_GRID
from fransys_model.kernel import Draft, Model, Origin, freeze, make_id
from fransys_model.layout import (
    BlockRow,
    BoxKind,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    EndStyle,
    PinCell,
    RoutePoint,
    SheetFormat,
)
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Conductor,
    ConductorKind,
    Function,
    FunctionKind,
    Item,
    Part,
    PartCategory,
    Placement,
    Port,
    PortRole,
    Unit,
    UnitRelease,
    WireFacet,
)
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet

if TYPE_CHECKING:
    from fransys_model.kernel import Id

G = WIRING_GRID
_ORIGIN = Origin(file="packages/fransys-render/tests/_cable_build.py", line=1, note="invented")
_BY = "test"


class World:
    """Collects invented records; `model()` freezes them."""

    def __init__(self) -> None:
        """Start empty."""
        self.records: list[Any] = []

    def item(  # noqa: PLR0913 -- one keyword per Item field the tests vary
        self,
        key: str,
        tag: str | None,
        *,
        parent: Id[Item] | None = None,
        part: Id[Part] | None = None,
        unit: Id[Unit] | None = None,
        external_at: Id[AspectNode] | None = None,
    ) -> Id[Item]:
        """An item `tag`; `external_at` makes it external, placed at that location node."""
        item = Item(
            id=make_id(Item, (key,)),
            key=(key,),
            part=part,
            parent=parent,
            position=None,
            tag=tag,
            description="Invented",
            installed=True,
            unit=unit,
            external=external_at is not None,
        )
        self.records.append(item)
        if external_at is not None:
            place = Placement(
                id=make_id(Placement, (key, "at")), key=(key, "at"), item=item.id, node=external_at
            )
            self.records.append(place)
        return item.id

    def device(
        self, key: str, tag: str, *names: str, **kwargs: Any
    ) -> tuple[Id[Item], dict[str, Id[Port]]]:
        """A device `tag` with one function and a port per name."""
        item = self.item(key, tag, **kwargs)
        function = Function(
            id=make_id(Function, (key, "f")),
            key=(key, "f"),
            item=item,
            template=None,
            name="f",
            kind=FunctionKind.GENERIC,
        )
        self.records.append(function)
        ports = {}
        for name in names:
            port = Port(
                id=make_id(Port, (key, "f", name)),
                key=(key, "f", name),
                function=function.id,
                template=None,
                name=name,
                role=PortRole.GENERIC,
            )
            self.records.append(port)
            ports[name] = port.id
        return item, ports

    def location(self, label: str) -> Id[AspectNode]:
        """A location node, printed `+LABEL`."""
        node = AspectNode(
            id=make_id(AspectNode, (label,)),
            key=(label,),
            aspect=Aspect.LOCATION,
            parent=None,
            label=label,
            description="Invented",
        )
        self.records.append(node)
        return node.id

    def unit(self, key: str, *, parent: Id[Unit] | None = None) -> Id[Unit]:
        """A unit of its own release."""
        rkey = ("unit_release", key, "1", "1")
        release = UnitRelease(
            id=make_id(UnitRelease, rkey),
            key=rkey,
            name=key,
            version=1,
            revision=1,
            interface="1",
            class_code="",
        )
        unit = Unit(
            id=make_id(Unit, (key,)), key=(key,), release=release.id, parent=parent, tag=None
        )
        self.records.extend((release, unit))
        return unit.id

    def cable(  # noqa: PLR0913 -- one keyword per cable fact the tests vary
        self,
        key: str,
        tag: str,
        colours: tuple[str, ...],
        *,
        parent: Id[Item] | None = None,
        unit: Id[Unit] | None = None,
        shielded: bool = False,
        length: int | None = None,
    ) -> Id[Item]:
        """A cable item `tag` with a part whose core colours are `colours`."""
        part = Part(
            id=make_id(Part, (key, "part")),
            key=(key, "part"),
            mpn=f"MPN-{key}",
            manufacturer="Example Co",
            description="Invented",
            category=PartCategory.CABLE,
            class_code="W",
        )
        product = CableProductFacet(
            id=make_id(CableProductFacet, (key, "product")),
            key=(key, "product"),
            subject=part.id,
            core_colours=colours,
            gauge_mm2=Decimal("0.5"),
            shielded=shielded,
        )
        item = self.item(key, tag, parent=parent, unit=unit, part=part.id)
        facet = CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=length,
        )
        self.records.extend((part, product, facet))
        return item

    def core(
        self, key: str, cable: Id[Item], ends: tuple[Id[Port], Id[Port]], index: int,
        label: str | None = None,
    ) -> Id[Conductor]:  # fmt: skip
        """A core of `cable` between `ends`, with its index and, when given, its label."""
        conductor = Conductor(
            id=make_id(Conductor, (key,)),
            key=(key,),
            a=ends[0],
            b=ends[1],
            kind=ConductorKind.CORE,
            carrier=cable,
        )
        facet = CoreFacet(
            id=make_id(CoreFacet, (key, "facet")),
            key=(key, "facet"),
            subject=conductor.id,
            index=index,
        )
        self.records.extend((conductor, facet))
        if label is not None:
            self.records.append(
                WireFacet(
                    id=make_id(WireFacet, (key, "wire")),
                    key=(key, "wire"),
                    subject=conductor.id,
                    colour="black",
                    gauge_mm2=Decimal("0.5"),
                    length_mm=None,
                    label=label,
                )
            )
        return conductor.id

    def sheet(self, module_mm: Decimal) -> Id[SheetFormat]:
        """An authored sheet format of the given module."""
        sheet = SheetFormat(
            id=make_id(SheetFormat, ("small",)),
            key=("small",),
            name="small",
            width_mm=200,
            height_mm=150,
            content_x_mm=10,
            content_y_mm=10,
            content_width_mm=180,
            content_height_mm=130,
            frame_columns=4,
            frame_rows=3,
            module_mm=module_mm,
        )
        self.records.append(sheet)
        return sheet.id

    def block(
        self,
        subject: Id[Item],
        *,
        unit: Id[Unit] | None = None,
        sheet: Id[SheetFormat] | None = None,
        width: int = 10 * G,
        height: int = 17 * G,
    ) -> CableBlock:
        """The record of one block, pitch two wiring-grid steps."""
        key = ("block", str(unit), str(subject))
        block = CableBlock(
            id=make_id(CableBlock, key),
            key=key,
            subject=subject,
            unit=unit,
            width=width,
            height=height,
            pitch=2 * G,
            sheet_format=sheet,
            produced_by=_BY,
        )
        self.records.append(block)
        return block

    def box(
        self, block: CableBlock, item: Id[Item], kind: BoxKind, at: tuple[int, int, int, int]
    ) -> None:
        """A cable or harness box at `at` (x, y, width, height), in grid units."""
        key = ("box", str(block.id), str(item))
        x, y, width, height = at
        self.records.append(
            CableBox(
                id=make_id(CableBox, key),
                key=key,
                block=block.id,
                item=item,
                kind=kind,
                external=False,
                x=x,
                y=y,
                width=width,
                height=height,
                produced_by=_BY,
            )
        )

    def end(  # noqa: PLR0913 -- a keyword width joins the five fixture parts
        self,
        block: CableBlock,
        item: Id[Item],
        row: BlockRow,
        style: EndStyle,
        pins: tuple[tuple[Id[Port], int], ...],
        *,
        width: int = 6 * G,
    ) -> None:
        """An end box in `row`, `width` wide, at its row's y, one landed cell per `pins`."""
        key = ("end", str(block.id), str(item))
        y = 2 * G if row is BlockRow.TOP else 13 * G
        self.records.append(
            EndBox(
                id=make_id(EndBox, key),
                key=key,
                block=block.id,
                item=item,
                row=row,
                style=style,
                x=2 * G,
                y=y,
                width=width,
                height=2 * G,
                pins=tuple(
                    PinCell(index=n, port=port, x=x, landed=True)
                    for n, (port, x) in enumerate(pins)
                ),
                produced_by=_BY,
            )
        )

    def wire(  # noqa: PLR0913 -- the cable box edges default to the tests' common box
        self,
        block: CableBlock,
        conductor: Id[Conductor],
        x: int,
        *,
        stub_b: bool = False,
        box_top: int = 6 * G,
        box_bottom: int = 11 * G,
    ) -> None:
        """A vertical core at `x`: run a from the top end to the cable box, run b below it."""
        key = ("wire", str(block.id), str(conductor))
        bottom = 12 * G if stub_b else 13 * G
        self.records.append(
            CoreWire(
                id=make_id(CoreWire, key),
                key=key,
                block=block.id,
                conductor=conductor,
                run_a=(RoutePoint(index=0, x=x, y=4 * G), RoutePoint(index=1, x=x, y=box_top)),
                run_b=(RoutePoint(index=0, x=x, y=box_bottom), RoutePoint(index=1, x=x, y=bottom)),
                text_x=x,
                text_y=7 * G,
                stub_a=False,
                stub_b=stub_b,
                produced_by=_BY,
            )
        )

    def link(
        self,
        block: CableBlock,
        conductor: Id[Conductor],
        xs: tuple[int, int],
        *,
        corner: int = 5 * G,
    ) -> None:
        """A row link between two top-row pins at `xs`: run a through both corners, run b to one.

        The text stands level at the middle of the straight run, on the corner row.
        """
        key = ("wire", str(block.id), str(conductor))
        pin_y = 4 * G
        a = (RoutePoint(index=0, x=xs[0], y=pin_y), RoutePoint(index=1, x=xs[0], y=corner))
        a += (RoutePoint(index=2, x=xs[1], y=corner),)
        b = (RoutePoint(index=0, x=xs[1], y=pin_y), RoutePoint(index=1, x=xs[1], y=corner))
        self.records.append(
            CoreWire(
                id=make_id(CoreWire, key),
                key=key,
                block=block.id,
                conductor=conductor,
                run_a=a,
                run_b=b,
                text_x=(xs[0] + xs[1]) // 2,
                text_y=corner,
                stub_a=False,
                stub_b=False,
                produced_by=_BY,
            )
        )

    def model(self) -> Model:
        """Freeze everything added."""
        draft = Draft()
        draft.extend(self.records, origin=_ORIGIN)
        return freeze(draft)
