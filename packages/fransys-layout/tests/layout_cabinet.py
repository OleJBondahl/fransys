"""Synthetic use case: a small cabinet with its groups and relays.

All parts, designations and groups are invented for this repo; none describe a real
product or project. This repo keeps its own fixture until fransys-model's use-case
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_author.instantiate import instantiate

from fransys_model.elecdef import LinkKind
from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.layout import (
    GroupHint,
    SymbolChoice,
)
from fransys_model.layout import Profile as ModelProfile
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    CableProductFacet,
    Conductor,
    ConductorKind,
    CoreFacet,
    Function,
    FunctionKind,
    FunctionTemplate,
    InternalLink,
    Item,
    Net,
    NetClass,
    Part,
    PartBundle,
    PartCategory,
    PartLibrary,
    PcbFacet,
    Placement,
    Port,
    PortBoundary,
    PortTemplate,
    TerminalFacet,
    WireFacet,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Record


_ORIGIN = Origin(file="tests/layout_cabinet.py", line=1, note="synthetic cabinet")
_ROLES = {"internal": PortBoundary.INTERNAL, "external": PortBoundary.EXTERNAL}
_CONDUCTIVE, _SWITCHED = LinkKind.CONDUCTIVE, LinkKind.SWITCHED

type Key = tuple[str, ...]
type Cabinet = dict[str, _Ref]


@dataclass(frozen=True, slots=True)
class _PartSpec:
    """A part: identity, class letter, `(name, kind, pins)` per function, and its links.

    A link is `(function name, pin, pin, kind)`; a pin named `internal` or `external` has
    that `PortBoundary`, any other is generic.
    """

    key: str
    mpn: str
    letter: str
    category: PartCategory
    functions: tuple[tuple[str, FunctionKind, tuple[str, ...]], ...]
    links: tuple[tuple[str, str, str, LinkKind], ...] = ()


@dataclass(frozen=True, slots=True)
class _Ref:
    """A stamped item: its id and key and, by name, its functions and ports."""

    item: Id[Item]
    key: Key
    functions: dict[str, Id[Function]]
    ports: dict[tuple[str, str], Id[Port]]

    def port(self, function: str, pin: str) -> Id[Port]:
        """The port called `pin` of the function called `function`."""
        return self.ports[function, pin]


def _specs() -> tuple[_PartSpec, ...]:
    """Every part of the cabinet, declared once."""
    coil = ("coil", FunctionKind.COIL, ("A1", "A2"))
    sides = ("internal", "external")
    terminal = (("terminal", FunctionKind.TERMINAL, sides),)
    link_terminal = (("terminal", "internal", "external", _CONDUCTIVE),)
    element = (("element", FunctionKind.PROTECTION, ("1", "2")),)
    link_element = (("element", "1", "2", _CONDUCTIVE),)
    contact_no = FunctionKind.CONTACT_NO
    contact_nc = FunctionKind.CONTACT_NC
    return (
        _PartSpec("terminal", "EX-TERMINAL-2.5", "X", PartCategory.TERMINAL, terminal, link_terminal),
        _PartSpec("fuse", "EX-FUSE-2A", "F", PartCategory.PROTECTION, element, link_element),
        _PartSpec("breaker", "EX-BREAKER-1P-10A", "Q", PartCategory.PROTECTION, element, link_element),
        _PartSpec(
            "contactor",
            "EX-CONTACTOR-3P",
            "K",
            PartCategory.ELECTROMECHANICAL,
            (
                coil,
                ("main", contact_no, ("1", "2", "3", "4", "5", "6")),
                ("aux", contact_no, ("13", "14")),
            ),
            (
                ("main", "1", "2", _SWITCHED),
                ("main", "3", "4", _SWITCHED),
                ("main", "5", "6", _SWITCHED),
                ("aux", "13", "14", _SWITCHED),
            ),
        ),
        _PartSpec(
            "relay",
            "EX-RELAY-1NO",
            "K",
            PartCategory.ELECTROMECHANICAL,
            (coil, ("no_1", contact_no, ("13", "14"))),
            (("no_1", "13", "14", _SWITCHED),),
        ),
        _PartSpec(
            "pushbutton",
            "EX-PUSHBUTTON-NC",
            "S",
            PartCategory.GENERIC,
            (("nc_1", contact_nc, ("11", "12")),),
            (("nc_1", "11", "12", _SWITCHED),),
        ),
        _PartSpec(
            "estop",
            "EX-ESTOP-2NC",
            "S",
            PartCategory.GENERIC,
            (("nc_1", contact_nc, ("11", "12")), ("nc_2", contact_nc, ("21", "22"))),
            (("nc_1", "11", "12", _SWITCHED), ("nc_2", "21", "22", _SWITCHED)),
        ),
        _PartSpec(
            "lamp",
            "EX-LAMP-24V",
            "H",
            PartCategory.GENERIC,
            (("lamp", FunctionKind.LOAD, ("1", "2")),),
        ),
        _PartSpec(
            "cable",
            "EX-CABLE-2X0.75",
            "W",
            PartCategory.CABLE,
            (("screen", FunctionKind.GENERIC, ("shield",)),),
        ),
        _PartSpec(
            "board",
            "EX-BOARD-A",
            "A",
            PartCategory.BOARD,
            (("edge", FunctionKind.CONNECTOR, ("1", "2")),),
        ),
    )


class _Builder:
    """The records of the cabinet, in construction order, and the vocabulary to write them in."""

    def __init__(self, *, second_location: bool) -> None:
        """Start with the part library, the group nodes and the location node(s)."""
        self.records: list[Record] = []
        self.wires = 0
        self.library = PartLibrary(
            id=make_id(PartLibrary, ("part_library", "invented-parts")),
            key=("part_library", "invented-parts"),
            name="invented-parts",
            version="1.0.0",
        )
        self.add(self.library)
        for group in ("sup", "p1", "p2", "es"):
            self._node(group, Aspect.FUNCTION, group.upper())
        self._node("c1", Aspect.LOCATION, "C1")
        # `=P2` is the group that may live in a second drawing set
        self.location = {"sup": "c1", "p1": "c1", "es": "c1", "p2": "c1"}
        if second_location:
            self._node("c2", Aspect.LOCATION, "C2")
            self.location["p2"] = "c2"

    def add(self, *records: Record) -> None:
        """Add ready-made records."""
        self.records.extend(records)

    def facet(self, cls: Any, key: Key, **fields: Any) -> None:
        """Add a facet of type `cls`, whose id is derived from `key`."""
        self.add(cls(id=make_id(cls, key), key=key, **fields))

    def _node(self, key: str, aspect: Aspect, label: str) -> None:
        """A root aspect node with the one-element key `(key,)`."""
        self.add(
            AspectNode(
                id=make_id(AspectNode, (key,)),
                key=(key,),
                aspect=aspect,
                parent=None,
                label=label,
                description=f"invented {label}",
            )
        )

    def place(self, item: Id[Item], key: Key, group: str) -> None:
        """Place an item at the function node `group` and at that group's location."""
        for node in (group, self.location[group]):
            placement_key = (*key, "at", node)
            self.add(
                Placement(
                    id=make_id(Placement, placement_key),
                    key=placement_key,
                    item=item,
                    node=make_id(AspectNode, (node,)),
                )
            )

    def part(self, spec: _PartSpec) -> PartBundle:
        """A part with its function templates, port templates and internal links."""
        part = Part(
            id=make_id(Part, (spec.key,)),
            key=(spec.key,),
            mpn=spec.mpn,
            manufacturer="Example Co",
            description=f"Invented {spec.mpn}",
            category=spec.category,
            class_code=spec.letter,
            library=self.library.id,
        )
        templates = {
            name: FunctionTemplate(
                id=make_id(FunctionTemplate, (spec.key, name)),
                key=(spec.key, name),
                part=part.id,
                name=name,
                kind=kind,
            )
            for name, kind, _ in spec.functions
        }
        pins = {
            (name, pin): PortTemplate(
                id=make_id(PortTemplate, (spec.key, name, pin)),
                key=(spec.key, name, pin),
                function=templates[name].id,
                name=pin,
                boundary=_ROLES.get(pin, PortBoundary.GENERIC),
            )
            for name, _, names in spec.functions
            for pin in names
        }
        links = tuple(
            InternalLink(
                id=make_id(InternalLink, (spec.key, "link", str(number))),
                key=(spec.key, "link", str(number)),
                a=pins[name, a].id,
                b=pins[name, b].id,
                kind=kind,
            )
            for number, (name, a, b, kind) in enumerate(spec.links, start=1)
        )
        return PartBundle(
            part=part,
            function_templates=tuple(templates.values()),
            port_templates=tuple(pins.values()),
            internal_links=links,
        )

    def stamp(  # noqa: PLR0913 -- one call site shape: key, designation, group and two options
        self,
        bundle: PartBundle,
        key: Key,
        designation: str | None,
        group: str,
        *,
        parent: Id[Item] | None = None,
        installed: bool = True,
    ) -> _Ref:
        """Add the bundle's records (an identical record is a no-op) and one placed item."""
        self.add(bundle.part, *bundle.function_templates, *bundle.port_templates, *bundle.internal_links)
        stamped = instantiate(
            bundle,
            key,
            tag=designation,
            parent=parent,
            description=bundle.part.description,
            installed=installed,
        )
        self.add(*stamped)
        self.place(make_id(Item, key), key, group)
        names = {r.id: r.name for r in stamped if isinstance(r, Function)}
        return _Ref(
            item=make_id(Item, key),
            key=key,
            functions={name: function for function, name in names.items()},
            ports={(names[r.function], r.name): r.id for r in stamped if isinstance(r, Port)},
        )

    def strip(self, tag: str) -> _Ref:
        """A part-less terminal strip `tag` that only holds terminals, placed at `=SUP`."""
        key = ("cabinet", tag.lower())
        self.add(
            Item(
                id=make_id(Item, key),
                key=key,
                part=None,
                parent=None,
                position=None,
                tag=tag,
                description="Invented terminal strip",
            )
        )
        self.place(make_id(Item, key), key, "sup")
        return _Ref(item=make_id(Item, key), key=key, functions={}, ports={})

    def terminal(self, bundle: PartBundle, strip: _Ref, index: int, group: str) -> _Ref:
        """Terminal `index` of `strip`; its designation renders as `X1:2`, not stored."""
        key = (*strip.key, str(index))
        terminal = self.stamp(bundle, key, None, group, parent=strip.item)
        self.facet(TerminalFacet, (*key, "terminal"), subject=terminal.item, group="", index=index)
        return terminal

    def wire(self, a: Id[Port], b: Id[Port], *, label: bool = True) -> None:
        """A wire between two ports, numbered in construction order; `label` names it `W10nn`."""
        self.wires += 1
        key = ("cabinet", "wire", str(self.wires))
        conductor = self._conductor(key, (a, b), ConductorKind.WIRE, None)
        self.facet(
            WireFacet,
            (*key, "facet"),
            subject=conductor,
            colour="blue",
            gauge_mm2=Decimal("0.75"),
            length_mm=None,
            label=f"W{1000 + self.wires}" if label else None,
        )

    def core(self, cable: _Ref, index: int, ends: tuple[Id[Port], Id[Port]]) -> None:
        """Core `index` of `cable` between `ends`; its colour is the cable product's."""
        key = (*cable.key, "core", str(index))
        conductor = self._conductor(key, ends, ConductorKind.CORE, cable.item)
        self.facet(CoreFacet, (*key, "facet"), subject=conductor, index=index)

    def _conductor(
        self,
        key: Key,
        ends: tuple[Id[Port], Id[Port]],
        kind: ConductorKind,
        carrier: Id[Item] | None,
    ) -> Id[Conductor]:
        """A conductor of `kind` between two ports."""
        conductor = Conductor(
            id=make_id(Conductor, key),
            key=key,
            a=ends[0],
            b=ends[1],
            kind=kind,
            carrier=carrier,
        )
        self.add(conductor)
        return conductor.id

    def rail(self, key: Key, potential: str, port: Id[Port]) -> None:
        """A declared `Net` naming one port, giving it `potential` (model decision 0011).

        The port itself carries no conductor of its own: it is the open end a project
        would feed from outside the drawing (the incoming supply, a return busbar).
        """
        self.add(
            Net(
                id=make_id(Net, key),
                key=key,
                name=None,
                net_class=NetClass.CONTROL,
                ports=(port,),
                potential=potential,
            )
        )

    def choice(self, kind: FunctionKind, symbol: str, port_map: dict[str, str]) -> None:
        """A `layout.symbol_choice` for every function of `kind`, with a port map."""
        record_key = ("cabinet", "symbol", kind.value)
        self.add(
            SymbolChoice(
                id=make_id(SymbolChoice, record_key),
                key=record_key,
                function=None,
                template=None,
                part=None,
                kind=kind,
                symbol=symbol,
                port_map=frozendict(port_map),
            )
        )


def _supply(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """Group `=SUP`: feed terminal `X1:1`, fuse `F1`, rail terminal `X2:1`."""
    feed = cab["x1/1"] = b.terminal(parts["terminal"], cab["x1"], 1, "sup")
    fuse = cab["f1"] = b.stamp(parts["fuse"], ("cabinet", "f1"), "F1", "sup")
    rail = cab["x2/1"] = b.terminal(parts["terminal"], cab["x2"], 1, "sup")
    b.wire(feed.port("terminal", "internal"), fuse.port("element", "1"))
    b.wire(fuse.port("element", "2"), rail.port("terminal", "internal"))


def _pump(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet, n: int) -> None:
    """Group `=Pn`: a power path and a control path around contactor `Kn`.

    `inlet` and `field` are also kept in `cab` (`x1/<n+1>`, `x3/<n>`), unused by the
    default cabinet: the `discovery=True` extras declare distribution rails there.
    """
    group = f"p{n}"
    inlet = cab[f"x1/{n + 1}"] = b.terminal(parts["terminal"], cab["x1"], n + 1, group)
    breaker = b.stamp(parts["breaker"], ("cabinet", f"q{n}"), f"Q{n}", group)
    contactor = cab[f"k{n}"] = b.stamp(parts["contactor"], ("cabinet", f"k{n}"), f"K{n}", group)
    field = cab[f"x3/{n}"] = b.terminal(parts["terminal"], cab["x3"], n, group)
    stop = b.stamp(parts["pushbutton"], ("cabinet", f"s{n}"), f"S{n}", group)
    zero = cab[f"x4/{n}"] = b.terminal(parts["terminal"], cab["x4"], n, group)
    rail = cab["x2/1"]
    # only pole 1 of the contactor main contact is wired
    b.wire(inlet.port("terminal", "internal"), breaker.port("element", "1"))
    b.wire(breaker.port("element", "2"), contactor.port("main", "1"))
    b.wire(contactor.port("main", "2"), field.port("terminal", "internal"))
    b.wire(rail.port("terminal", "external"), stop.port("nc_1", "11"))
    b.wire(stop.port("nc_1", "12"), contactor.port("coil", "A1"))
    b.wire(contactor.port("coil", "A2"), zero.port("terminal", "internal"))


def _estop_and_signal(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """Group `=ES`: e-stop `S0`, whose second contact is hinted into `=P1`; plus the signal.

    The contact string runs rail, `S0` contact 1, `S0` contact 2 (drawn in `=P1`), then the
    auxiliary contact of `K1`, and on to the auxiliary contact of `K2` in `=P2` with no
    """
    estop = b.stamp(parts["estop"], ("cabinet", "s0"), "S0", "es")
    k1, k2 = cab["k1"], cab["k2"]
    b.wire(cab["x2/1"].port("terminal", "external"), estop.port("nc_1", "11"), label=False)
    b.wire(estop.port("nc_1", "12"), estop.port("nc_2", "21"), label=False)
    b.wire(estop.port("nc_2", "22"), k1.port("aux", "13"), label=False)
    b.wire(k1.port("aux", "14"), k2.port("aux", "13"), label=False)
    key = (*estop.key, "nc_2", "group_hint")
    b.add(
        GroupHint(
            id=make_id(GroupHint, key),
            key=key,
            function=estop.functions["nc_2"],
            group=make_id(AspectNode, ("p1",)),
        )
    )


def _extras(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """Lamp `H1`, cable `W1`, spare relay `K8` with its net, and board `A1`, all in `=SUP`."""
    lamp = cab["h1"] = b.stamp(parts["lamp"], ("cabinet", "h1"), "H1", "sup")
    cable = b.stamp(parts["cable"], ("cabinet", "w1"), "W1", "sup")
    b.facet(
        CableProductFacet,
        ("cable", "cable_product"),
        subject=parts["cable"].part.id,
        core_colours=("brown", "blue"),
        gauge_mm2=Decimal("0.75"),
        shielded=True,
    )
    b.core(cable, 1, (cab["x2/1"].port("terminal", "external"), lamp.port("lamp", "1")))
    b.core(cable, 2, (cab["x4/1"].port("terminal", "external"), lamp.port("lamp", "2")))
    # not installed, still drawn; unwired, so its declared net has no conductor
    spare = cab["k8"] = b.stamp(parts["relay"], ("cabinet", "k8"), "K8", "sup", installed=False)
    b.add(
        Net(
            id=make_id(Net, ("cabinet", "latch")),
            key=("cabinet", "latch"),
            name="LATCH",
            net_class=NetClass.CONTROL,
            ports=(spare.port("coil", "A1"), spare.port("no_1", "13")),
        )
    )
    # a board and its parts: the engine draws only its CONNECTOR function `edge` (model-0040);
    # its fuse `F10` stays undrawn
    board = b.stamp(parts["board"], ("cabinet", "a1"), "A1", "sup")
    b.facet(PcbFacet, ("board", "pcb"), subject=parts["board"].part.id, revision="A")
    b.stamp(parts["fuse"], ("cabinet", "a1", "f1"), "F10", "sup", parent=board.item)


def _extra_relay(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """Relay `K9` in `=P2`: its coil, and one contact to terminal `X5:1`."""
    relay = b.stamp(parts["relay"], ("cabinet", "k9"), "K9", "p2")
    output = b.terminal(parts["terminal"], b.strip("X5"), 1, "p2")
    rail, zero = cab["x2/1"], cab["x4/2"]
    b.wire(rail.port("terminal", "external"), relay.port("coil", "A1"))
    b.wire(relay.port("coil", "A2"), zero.port("terminal", "internal"))
    b.wire(rail.port("terminal", "external"), relay.port("no_1", "13"))
    b.wire(relay.port("no_1", "14"), output.port("terminal", "internal"))


def _fan_net(b: _Builder, parts: dict[str, PartBundle]) -> None:
    """Terminals `X6:1..4` in `=SUP`, `=P1`, `=ES`, `=SUP`, the first wired to the other three.

    One net of four ends, none in `=P2`: its markers print a ` +k` (model-0139), so the
    set's boxes already carry the +k room before `extra_relay` adds an end (model-0196).
    """
    strip = b.strip("X6")
    hub, *rest = (b.terminal(parts["terminal"], strip, i, group) for i, group in enumerate(("sup", "p1", "es", "sup"), 1))
    for end in rest:
        b.wire(hub.port("terminal", "external"), end.port("terminal", "internal"))


def _discovery_extras(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """With `discovery=True`: potentials on the rail nets, and the three invented circuits
    ladder discovery needs that no hinted chain in this fixture exercises (layout-0034,
    "What the fixture lacks").
    """
    b.rail(("cabinet", "rail", "l1", "feed"), "L1", cab["x1/1"].port("terminal", "external"))
    b.rail(("cabinet", "rail", "l1", "p1"), "L1", cab["x1/2"].port("terminal", "external"))
    b.rail(("cabinet", "rail", "l1", "p2"), "L1", cab["x1/3"].port("terminal", "external"))
    b.rail(("cabinet", "rail", "24v"), "24V", cab["x2/1"].port("terminal", "external"))
    b.rail(("cabinet", "rail", "0v", "p1"), "0V", cab["x4/1"].port("terminal", "external"))
    b.rail(("cabinet", "rail", "0v", "p2"), "0V", cab["x4/2"].port("terminal", "external"))
    b.rail(("cabinet", "rail", "m1"), "M1", cab["x3/1"].port("terminal", "external"))
    b.rail(("cabinet", "rail", "m2"), "M2", cab["x3/2"].port("terminal", "external"))

    # a wired second pole of K1's main contact, in parallel with pole 1: its ports do not
    # count on Q1's outlet net, the chain runs on (layout-0050)
    k1 = cab["k1"]
    b.wire(k1.port("main", "1"), k1.port("main", "3"))
    b.wire(k1.port("main", "2"), k1.port("main", "4"))

    # a second, dedicated 24V terminal, so the two circuits below do not crowd X2:1's own
    # port further: exercises two rails with one text for the source end
    x6 = b.terminal(parts["terminal"], b.strip("X6"), 1, "sup")
    b.rail(("cabinet", "rail", "24v", "2"), "24V", x6.port("terminal", "external"))

    # a shared terminal fed from the second 24V terminal, fanning through two contacts to
    # two 0V terminals: the branch case
    x7 = b.terminal(parts["terminal"], b.strip("X7"), 1, "sup")
    s10 = b.stamp(parts["pushbutton"], ("cabinet", "s10"), "S10", "sup")
    s11 = b.stamp(parts["pushbutton"], ("cabinet", "s11"), "S11", "sup")
    x8 = b.strip("X8")
    x8_1 = b.terminal(parts["terminal"], x8, 1, "sup")
    x8_2 = b.terminal(parts["terminal"], x8, 2, "sup")
    b.wire(x6.port("terminal", "external"), x7.port("terminal", "internal"))
    b.wire(x7.port("terminal", "external"), s10.port("nc_1", "11"))
    b.wire(x7.port("terminal", "external"), s11.port("nc_1", "11"))
    b.wire(s10.port("nc_1", "12"), x8_1.port("terminal", "internal"))
    b.wire(s11.port("nc_1", "12"), x8_2.port("terminal", "internal"))
    b.rail(("cabinet", "rail", "0v", "x8", "1"), "0V", x8_1.port("terminal", "external"))
    b.rail(("cabinet", "rail", "0v", "x8", "2"), "0V", x8_2.port("terminal", "external"))

    # two relays in parallel between the second 24V terminal and one coil: reconvergent,
    # hint-mandatory
    k20 = b.stamp(parts["relay"], ("cabinet", "k20"), "K20", "sup")
    k21 = b.stamp(parts["relay"], ("cabinet", "k21"), "K21", "sup")
    k22 = b.stamp(parts["relay"], ("cabinet", "k22"), "K22", "sup")
    x9 = b.terminal(parts["terminal"], b.strip("X9"), 1, "sup")
    b.wire(x6.port("terminal", "external"), k20.port("no_1", "13"))
    b.wire(x6.port("terminal", "external"), k21.port("no_1", "13"))
    b.wire(k20.port("no_1", "14"), k22.port("coil", "A1"))
    b.wire(k21.port("no_1", "14"), k22.port("coil", "A1"))
    b.wire(k22.port("coil", "A2"), x9.port("terminal", "internal"))
    b.rail(("cabinet", "rail", "0v", "x9"), "0V", x9.port("terminal", "external"))


def build_cabinet(  # noqa: PLR0913 -- one keyword per fixture variant
    *,
    reverse: bool = False,
    extra_relay: bool = False,
    second_location: bool = False,
    discovery: bool = False,
    side_terminals: bool = False,
    fan_net: bool = False,
) -> Draft:
    """Build the cabinet fixture: a `Draft`, not yet frozen.

    The invented design this must produce, in location `+C1`. Groups are the top-level
    `FUNCTION` nodes `SUP`, `P1`, `P2`, `ES`; every item is placed at one of them and at
    """
    b = _Builder(second_location=second_location)
    parts = {spec.key: b.part(spec) for spec in _specs()}
    cab = {tag: b.strip(tag.upper()) for tag in ("x1", "x2", "x3", "x4")}
    # `side_terminals`: a terminal draws its ports on its W and E sides (an E or W reference)
    terminal_ports = {"internal": "w", "external": "e"} if side_terminals else None
    b.choice(FunctionKind.TERMINAL, "terminal", terminal_ports or {"internal": "n", "external": "s"})
    b.choice(FunctionKind.COIL, "operating-device", {"A1": "in", "A2": "out"})
    _supply(b, parts, cab)
    _pump(b, parts, cab, 1)
    _pump(b, parts, cab, 2)
    _estop_and_signal(b, parts, cab)
    _extras(b, parts, cab)
    if fan_net:
        _fan_net(b, parts)
    if extra_relay:
        _extra_relay(b, parts, cab)
    if discovery:
        _discovery_extras(b, parts, cab)
        profile_key = ("cabinet", "discovery", "profile")
        b.add(ModelProfile(id=make_id(ModelProfile, profile_key), key=profile_key))
    draft = Draft()
    draft.extend(reversed(b.records) if reverse else b.records, origin=_ORIGIN)
    return draft
