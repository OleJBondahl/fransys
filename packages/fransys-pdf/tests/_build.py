"""A minimal hand-built model for this package's own tests (not the root fixtures).

`fransys_pdf` may only import `fransys_model` (`tests/test_boundaries.py`), but that
rule applies to `src/`, not to a package's own `tests/`, so building here with
`fransys_author` would be allowed too -- this stays on `fransys_model.kernel` directly
because a document record needs no authoring syntax, only a few records by hand, matching the
pattern `packages/fransys-kicad/tests/conftest.py` uses for its own invented board.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Orientation,
    Page,
    PageGroup,
    PageRole,
    Route,
    RoutePoint,
    SheetFormat,
    SymbolPlacement,
)
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Conductor,
    ConductorKind,
    ConnectorFacet,
    Document,
    DocumentPreset,
    Function,
    FunctionKind,
    FunctionTemplate,
    Gender,
    Item,
    PageKind,
    Part,
    PartCategory,
    PcbFacet,
    Placement,
    PlcChannelFacet,
    Port,
    PortRole,
    Project,
    Revision,
    SignalType,
    TerminalFacet,
    Unit,
    UnitRelease,
    WireFacet,
)
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab import Net

_ORIGIN = Origin(file="packages/fransys-pdf/tests/_build.py", line=1, note="invented document")

# The release `unit()` made for each unit, by release id, for `model()` to add.
_RELEASES: dict[Id[UnitRelease], UnitRelease] = {}


def project(  # noqa: PLR0913 -- one keyword per invented fact, each independently overridable
    *,
    title: str = "Demo cabinet",
    number: str = "DEMO-1",
    customer: str = "Demo Co",
    revision: int = 1,
    author: str = "demo",
    notice: str = "",
) -> Project:
    """A `Project` record; every field has an invented default, overridable by keyword.

    The printed revision date is the `Revision` entry's (`revision_entry(..., unit=None)`), not
    the project's: add one to the model where a test needs a date.

    `notice` (spec page-frame R11.4, decision model-0051) defaults to `""`, `Project`'s own
    default -- an empty title-block notice cell, the same "invented default" every other
    field here already follows.
    """
    return Project(
        id=make_id(Project, ("project",)),
        key=("project",),
        title=title,
        number=number,
        customer=customer,
        revision=revision,
        author=author,
        notice=notice,
    )


def location(label: str, description: str) -> AspectNode:
    """A `LOCATION` aspect node, standing in for a cabinet."""
    key = ("location", label)
    return AspectNode(
        id=make_id(AspectNode, key),
        key=key,
        aspect=Aspect.LOCATION,
        parent=None,
        label=label,
        description=description,
    )


def function_node(label: str, description: str) -> AspectNode:
    """A `FUNCTION` aspect node, standing in for a page's own `=` group (spec R3, R11.7)."""
    key = ("function_node", label)
    return AspectNode(
        id=make_id(AspectNode, key),
        key=key,
        aspect=Aspect.FUNCTION,
        parent=None,
        label=label,
        description=description,
    )


def part(key_part: str, *, description: str) -> Part:
    """A bare `Part`, invented (root CLAUDE.md invariant 6)."""
    key = ("part", key_part)
    return Part(
        id=make_id(Part, key),
        key=key,
        mpn=f"SIM-{key_part.upper()}",
        manufacturer="Example Co",
        description=description,
        category=PartCategory.GENERIC,
        class_code="A",
    )


def item(
    key_part: str,
    *,
    description: str,
    part: Id[Part] | None = None,
    parent: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
) -> Item:
    """A bare `Item`, standing in for a harness, a board or a harness cable; no function."""
    key = ("item", key_part)
    return Item(
        id=make_id(Item, key),
        key=key,
        part=part,
        parent=parent,
        position=None,
        tag=key_part.upper(),
        description=description,
        unit=unit,
    )


def unit(  # noqa: PLR0913 -- one keyword per invented fact, as `document()` below
    key_part: str,
    *,
    name: str,
    revision: int = 1,
    interface: str = "1",
    parent: Id[Unit] | None = None,
    title: str = "",
    number: str = "",
) -> Unit:
    """A `Unit` instance (units spec U1), standing in for a nested cabinet, board or the like.

    `title` and `number` (UNIT-ID I1) default to `""`, `UnitRelease`'s own default. The unit's
    release (version 1) is remembered here and added to the model by `model()` below.
    """
    release_key = ("unit_release", name, "1", str(revision))
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name=name,
        version=1,
        revision=revision,
        interface=interface,
        title=title,
        number=number,
    )
    _RELEASES[release.id] = release
    key = ("unit", key_part)
    return Unit(id=make_id(Unit, key), key=key, release=release.id, parent=parent)


def revision_entry(  # noqa: PLR0913 -- one keyword per invented fact, as `document()` above
    key_part: str,
    *,
    unit: Unit | None,
    revision: int,
    date: str,
    text: str = "Release",
    created: str = "OJB",
    checked: str = "",
    approved: str = "",
) -> Revision:
    """A `Revision` history entry (units spec U4): of `unit`'s release, or the project (`None`)."""
    key = ("revision", key_part)
    return Revision(
        id=make_id(Revision, key),
        key=key,
        release=None if unit is None else unit.release,
        version=1,
        revision=revision,
        date=date,
        text=text,
        created=created,
        checked=checked,
        approved=approved,
    )


def cable_facet(key_part: str, *, subject: Id[Item], length_mm: int | None) -> CableFacet:
    """A `cable` facet on `subject`, the as-installed length of a harness cable item."""
    key = ("cable", key_part)
    return CableFacet(id=make_id(CableFacet, key), key=key, subject=subject, length_mm=length_mm)


def cable_product_facet(
    key_part: str,
    *,
    subject: Id[Part],
    core_count: int = 4,
    gauge_mm2: Decimal = Decimal("0.5"),
    shielded: bool = False,
) -> CableProductFacet:
    """A `cable_product` facet on `subject`, an invented cable `Part`'s catalog facts."""
    key = ("cable_product", key_part)
    return CableProductFacet(
        id=make_id(CableProductFacet, key),
        key=key,
        subject=subject,
        core_colours=("brown", "black", "grey", "blue")[:core_count],
        gauge_mm2=gauge_mm2,
        shielded=shielded,
    )


def sheet_format(
    key_part: str,
    *,
    width_mm: int,
    height_mm: int,
    frame_columns: int = 6,
    frame_rows: int = 4,
) -> SheetFormat:
    """A minimal authored `SheetFormat`, distinct from the house sheet."""
    key = ("sheet_format", key_part)
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name=key_part,
        width_mm=width_mm,
        height_mm=height_mm,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm - 20,
        content_height_mm=height_mm - 40,
        frame_columns=frame_columns,
        frame_rows=frame_rows,
        module_mm=Decimal("2.5"),
    )


def drawing_set(
    key_part: str,
    *,
    location: AspectNode | None = None,
    unit: Unit | None = None,
    number: int = 1,
) -> DrawingSet:
    """A `layout.drawing_set` for `location` and/or `unit` (model-0024, amended by model-0041)."""
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key),
        key=key,
        location=None if location is None else location.id,
        unit=None if unit is None else unit.id,
        number=number,
        produced_by="test",
    )


def layout_page(
    key_part: str,
    *,
    drawing_set: DrawingSet,
    number: int,
    sheet_format: SheetFormat | None = None,
    groups: tuple[PageGroup, ...] = (),
) -> Page:
    """A `layout.page` of `drawing_set`, naming `sheet_format` (or the house sheet).

    `groups` (spec page-frame R3/R11.7's page-title rule) defaults to `()`, unchanged.
    """
    key = ("page", key_part)
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=None if sheet_format is None else sheet_format.id,
        groups=groups,
        produced_by="test",
    )


def page_group(*, node: AspectNode, index: int) -> PageGroup:
    """One `=` group drawn on a page (spec page-frame R3/R11.7), `node`'s own aspect node."""
    return PageGroup(group=node.id, index=index)


def document(  # noqa: PLR0913 -- one keyword per thing a test varies, as the kicad conftest does
    key_part: str,
    *,
    preset: DocumentPreset,
    subject: AspectNode | Item | Unit | None = None,
    cover: str,
    notes: str | None = None,
    add: tuple[PageKind, ...] = (),
    remove: tuple[PageKind, ...] = (),
    logo: str | None = None,
) -> Document:
    """A `Document` record about `subject` (a location node, an item or a unit).

    `subject=None` is the `SYSTEM` preset's own case (units spec U3): none of the three.
    `logo` (spec page-frame R11.3, decision model-0051) defaults to `None`, `Document`'s own
    default -- an empty title-block logo cell, the same "invented default" every other field
    here already follows.
    """
    key = ("document", key_part)
    return Document(
        id=make_id(Document, key),
        key=key,
        preset=preset,
        location=subject.id if isinstance(subject, AspectNode) else None,
        item=subject.id if isinstance(subject, Item) else None,
        unit=subject.id if isinstance(subject, Unit) else None,
        add=add,
        remove=remove,
        cover=cover,
        notes=notes,
        logo=logo,
    )


def symbol_placement(key_part: str, *, function: Id[Function], page: Id[Page]) -> SymbolPlacement:
    """A `layout.symbol_placement` of `function` on `page` (units spec U1's black-box reader)."""
    key = ("symbol_placement", key_part)
    return SymbolPlacement(
        id=make_id(SymbolPlacement, key),
        key=key,
        function=function,
        page=page,
        x=0,
        y=0,
        orientation=Orientation.R0,
        poles=1,
        symbol="test",
        library_version="1",
        produced_by="test",
    )


def route(  # noqa: PLR0913 -- one keyword per invented fact, as `document()` above
    key_part: str,
    *,
    page: Id[Page],
    a: Id[Port],
    b: Id[Port],
    conductor: Id[Conductor] | None = None,
    net: Id[Net] | None = None,
) -> Route:
    """A `layout.route` on `page` between ports `a` and `b` (STEP 4 addition's conductor check)."""
    key = ("route", key_part)
    return Route(
        id=make_id(Route, key),
        key=key,
        page=page,
        conductor=conductor,
        net=net,
        a=a,
        b=b,
        points=(RoutePoint(index=0, x=0, y=0), RoutePoint(index=1, x=10, y=10)),
        produced_by="test",
    )


def link_marker_pair(
    key_part: str, *, page_a: Id[Page], port_a: Id[Port], page_b: Id[Page], port_b: Id[Port]
) -> tuple[LinkMarker, LinkMarker]:
    """A paired `layout.link_marker` (one signal severed by a page boundary, spec R6-adjacent).

    Real pairing matters: `freeze()` resolves `partner` as an ordinary reference.
    """
    key_a = ("link_marker", key_part, "a")
    key_b = ("link_marker", key_part, "b")
    id_a = make_id(LinkMarker, key_a)
    id_b = make_id(LinkMarker, key_b)
    marker_a = LinkMarker(
        id=id_a,
        key=key_a,
        page=page_a,
        port=port_a,
        side=MarkerSide.OWNER,
        partner=id_b,
        x=0,
        y=0,
        width=10,
        height=8,
        produced_by="test",
    )
    marker_b = LinkMarker(
        id=id_b,
        key=key_b,
        page=page_b,
        port=port_b,
        side=MarkerSide.USER,
        partner=id_a,
        x=0,
        y=0,
        width=10,
        height=8,
        produced_by="test",
    )
    return marker_a, marker_b


def place(key_part: str, *, item: Id[Item], node: Id[AspectNode]) -> Placement:
    """A `Placement` of `item` at `node` (spec P9 terminal-strip/board location scoping)."""
    key = ("placement", key_part)
    return Placement(id=make_id(Placement, key), key=key, item=item, node=node)


def terminal(
    key_part: str, *, strip: Id[Item], group: str, index: int
) -> tuple[Item, TerminalFacet]:
    """An unused terminal `group:index`, child of `strip` (spec P9 TERMINAL_LIST)."""
    key = ("item", key_part)
    child = Item(
        id=make_id(Item, key),
        key=key,
        part=None,
        parent=strip,
        position=None,
        tag=None,
        description="Invented terminal",
    )
    facet_key = ("terminal", key_part)
    facet = TerminalFacet(
        id=make_id(TerminalFacet, facet_key),
        key=facet_key,
        subject=child.id,
        group=group,
        index=index,
    )
    return child, facet


def bridged_terminal(
    key_part: str, *, strip: Id[Item], group: str, index: int
) -> tuple[Item, TerminalFacet, Function, Port]:
    """A terminal `group:index` with one real `internal` port, child of `strip` (spec T2).

    `terminal()` above builds an unused terminal with no function at all; a `jumper`
    conductor needs a real port to land on (`conductor()` below, `kind=ConductorKind.JUMPER`),
    so this is a second, additive helper only the Bridge-column tests use.
    """
    child, facet = terminal(key_part, strip=strip, group=group, index=index)
    function_key = ("function", key_part)
    fn = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=child.id,
        template=None,
        name="terminal",
        kind=FunctionKind.TERMINAL,
    )
    port_key = (*function_key, "internal")
    internal = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=fn.id,
        template=None,
        name="internal",
        role=PortRole.INTERNAL,
    )
    return child, facet, fn, internal


def external_port(key_part: str) -> Port:
    """The `external` port of the terminal `bridged_terminal(key_part, ...)` built (item 4).

    Same `Function`, role `EXTERNAL`: the terminal's other side, so a conductor can land on it.
    """
    function_key = ("function", key_part)
    port_key = (*function_key, "external")
    return Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=make_id(Function, function_key),
        template=None,
        name="external",
        role=PortRole.EXTERNAL,
    )


def plc_channel(
    key_part: str, *, module: Id[Item], name: str, signal: SignalType, channel: int
) -> tuple[Part, FunctionTemplate, Function, PlcChannelFacet]:
    """An unbound PLC channel `name` of `module`, with its own invented module `Part` (P9)."""
    module_part = part(f"{key_part}-part", description="Invented PLC module")
    template_key = ("plc_channel_template", key_part)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, template_key),
        key=template_key,
        part=module_part.id,
        name=name,
        kind=FunctionKind.PLC_CHANNEL,
    )
    function_key = ("function", key_part)
    fn = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=module,
        template=template.id,
        name=name,
        kind=FunctionKind.PLC_CHANNEL,
    )
    facet_key = ("plc_channel_facet", key_part)
    facet = PlcChannelFacet(
        id=make_id(PlcChannelFacet, facet_key),
        key=facet_key,
        subject=template.id,
        signal=signal,
        channel=channel,
    )
    return module_part, template, fn, facet


def pcb_facet(key_part: str, *, subject: Id[Part], revision: str = "A") -> PcbFacet:
    """A `pcb` facet on `subject`, marking its item a board (spec P9 CONNECTOR_LIST)."""
    key = ("pcb_facet", key_part)
    return PcbFacet(id=make_id(PcbFacet, key), key=key, subject=subject, revision=revision)


def connector(  # noqa: PLR0913 -- one keyword per invented fact, as `document()` above
    key_part: str,
    *,
    item: Id[Item],
    name: str,
    markings: tuple[str, ...],
    gender: Gender = Gender.MALE,
    style: str = "header",
) -> tuple[Part, FunctionTemplate, Function, ConnectorFacet, tuple[Port, ...]]:
    """A connector function `name` of `item`, one port per marking, with its own `Part` (P9)."""
    connector_part = part(f"{key_part}-part", description="Invented connector")
    template_key = ("connector_template", key_part)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, template_key),
        key=template_key,
        part=connector_part.id,
        name=name,
        kind=FunctionKind.CONNECTOR,
    )
    function_key = ("function", key_part)
    fn = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item,
        template=template.id,
        name=name,
        kind=FunctionKind.CONNECTOR,
    )
    facet_key = ("connector_facet", key_part)
    facet = ConnectorFacet(
        id=make_id(ConnectorFacet, facet_key),
        key=facet_key,
        subject=template.id,
        style=style,
        pincount=len(markings),
        gender=gender,
    )
    ports = tuple(
        Port(
            id=make_id(Port, (*function_key, marking)),
            key=(*function_key, marking),
            function=fn.id,
            template=None,
            name=marking,
            role=PortRole.GENERIC,
        )
        for marking in markings
    )
    return connector_part, template, fn, facet, ports


def conductor(
    key_part: str,
    *,
    a: Id[Port],
    b: Id[Port],
    kind: ConductorKind = ConductorKind.WIRE,
    carrier: Id[Item] | None = None,
) -> Conductor:
    """A conductor between ports `a` and `b` (spec P9 WIRE_LABEL_LIST); `carrier` is the cable
    item for a `CORE` conductor (spec P8 CONTENTS "Ends"), `None` for a loose wire or jumper."""
    key = ("conductor", key_part)
    return Conductor(id=make_id(Conductor, key), key=key, a=a, b=b, kind=kind, carrier=carrier)


def core_facet(key_part: str, *, subject: Id[Conductor], index: int) -> CoreFacet:
    """A `core` facet on `subject`, marking a `CORE` conductor as a cable's own core."""
    key = ("core_facet", key_part)
    return CoreFacet(id=make_id(CoreFacet, key), key=key, subject=subject, index=index)


def wire_facet(key_part: str, *, subject: Id[Conductor], label: str | None) -> WireFacet:
    """A `wire` facet on `subject`, carrying `label` (spec P9 WIRE_LABEL_LIST)."""
    key = ("wire_facet", key_part)
    return WireFacet(
        id=make_id(WireFacet, key),
        key=key,
        subject=subject,
        colour="black",
        gauge_mm2=Decimal("0.75"),
        length_mm=None,
        label=label,
    )


def pin(
    key_part: str, designation: str, *, unit: Id[Unit] | None = None
) -> tuple[Item, Function, Port]:
    """A numbered item with one function `f` and one port `1` (spec P9 WIRE_LABEL_LIST ends)."""
    item_key = ("item", key_part)
    subject = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="Invented",
        unit=unit,
    )
    function_key = ("function", key_part)
    fn = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=subject.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port_key = (*function_key, "1")
    a_port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=fn.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    return subject, fn, a_port


def model(*records):
    """The frozen model of `records`, all attributed to one invented origin.

    Each `Unit` among `records` brings the release `unit()` made for it.
    """
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    draft.extend(
        {r.release: _RELEASES[r.release] for r in records if isinstance(r, Unit)}.values(),
        origin=_ORIGIN,
    )
    return freeze(draft)
