"""WP14 synthetic use case: a small cabinet with chain hints (ROADMAP WP14, package-layout.md 9).

All parts, designations and groups are invented for this repo; none describe a real
product or project. This repo keeps its own fixture until fransys-model's use-case
fixtures exist (its WP17); then WP14 switches to those, extended with chain hints.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.layout import Chain, ChainEntry, GroupHint, SymbolChoice, default_sheet_format
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import SheetFormat as ModelSheetFormat
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
    LinkKind,
    Net,
    NetClass,
    Part,
    PartBundle,
    PartCategory,
    PartLibrary,
    PcbFacet,
    Placement,
    Port,
    PortRole,
    PortTemplate,
    TerminalFacet,
    Unit,
    UnitRelease,
    WireFacet,
    instantiate,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Record

_ORIGIN = Origin(file="tests/layout_cabinet.py", line=1, note="synthetic cabinet")
_ROLES = {"internal": PortRole.INTERNAL, "external": PortRole.EXTERNAL}
_CONDUCTIVE, _SWITCHED = LinkKind.CONDUCTIVE, LinkKind.SWITCHED

type Key = tuple[str, ...]
type Cabinet = dict[str, _Ref]


@dataclass(frozen=True, slots=True)
class _PartSpec:
    """A part: identity, class letter, `(name, kind, pins)` per function, and its links.

    A link is `(function name, pin, pin, kind)`; a pin named `internal` or `external` has
    that `PortRole`, any other is generic.
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
        _PartSpec(
            "terminal", "EX-TERMINAL-2.5", "X", PartCategory.TERMINAL, terminal, link_terminal
        ),
        _PartSpec("fuse", "EX-FUSE-2A", "F", PartCategory.PROTECTION, element, link_element),
        _PartSpec(
            "breaker", "EX-BREAKER-1P-10A", "Q", PartCategory.PROTECTION, element, link_element
        ),
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

    def __init__(self, *, second_location: bool, chains_enabled: bool = True) -> None:
        """Start with the part library, the group nodes and the location node(s).

        `chains_enabled=False` (WP16, `discovery=True`) makes `chain` a no-op, the same
        suppression the WP15 spike used, so the fixture's functions are left for
        `discover_chains` to find instead of an authored `layout.chain`.
        """
        self.records: list[Record] = []
        self.wires = 0
        self.chains_enabled = chains_enabled
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
                role=_ROLES.get(pin, PortRole.GENERIC),
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
        self.add(
            bundle.part, *bundle.function_templates, *bundle.port_templates, *bundle.internal_links
        )
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

    def chain(self, key: Key, *cells: tuple[_Ref, str]) -> None:
        """A `layout.chain` of `(item, function name)` cells, indexed 0, 1, 2 ... in order.

        A no-op when `chains_enabled` is `False` (WP16).
        """
        if not self.chains_enabled:
            return
        entries = tuple(
            ChainEntry(function=ref.functions[name], index=index)
            for index, (ref, name) in enumerate(cells)
        )
        self.add(Chain(id=make_id(Chain, key), key=key, entries=entries))

    def rail(self, key: Key, potential: str, port: Id[Port]) -> None:
        """A declared `Net` naming one port, giving it `potential` (WP16, model decision 0011).

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
    """Group `=SUP`: feed terminal `X1:1`, fuse `F1`, rail terminal `X2:1`, in one chain."""
    feed = cab["x1/1"] = b.terminal(parts["terminal"], cab["x1"], 1, "sup")
    fuse = cab["f1"] = b.stamp(parts["fuse"], ("cabinet", "f1"), "F1", "sup")
    rail = cab["x2/1"] = b.terminal(parts["terminal"], cab["x2"], 1, "sup")
    b.wire(feed.port("terminal", "internal"), fuse.port("element", "1"))
    b.wire(fuse.port("element", "2"), rail.port("terminal", "internal"))
    b.chain(("cabinet", "sup"), (feed, "terminal"), (fuse, "element"), (rail, "terminal"))


def _pump(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet, n: int) -> None:
    """Group `=Pn`: a power chain and a control chain around contactor `Kn`.

    `inlet` and `field` are also kept in `cab` (`x1/<n+1>`, `x3/<n>`), unused by the
    default cabinet: WP16's `discovery=True` extras declare distribution rails there.
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
    b.chain(
        ("cabinet", group, "power"),
        (inlet, "terminal"),
        (breaker, "element"),
        (contactor, "main"),
        (field, "terminal"),
    )
    b.wire(rail.port("terminal", "external"), stop.port("nc_1", "11"))
    b.wire(stop.port("nc_1", "12"), contactor.port("coil", "A1"))
    b.wire(contactor.port("coil", "A2"), zero.port("terminal", "internal"))
    # the rail terminal has one home, the `sup` chain: this chain only wires to it
    b.chain(("cabinet", group, "control"), (stop, "nc_1"), (contactor, "coil"), (zero, "terminal"))


def _estop_and_signal(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """Group `=ES`: e-stop `S0`, whose second contact is hinted into `=P1`; plus the signal.

    The contact string runs rail, `S0` contact 1, `S0` contact 2 (drawn in `=P1`), then the
    auxiliary contact of `K1`, and on to the auxiliary contact of `K2` in `=P2` with no
    terminal between: the severed signal.
    """
    estop = b.stamp(parts["estop"], ("cabinet", "s0"), "S0", "es")
    k1, k2 = cab["k1"], cab["k2"]
    b.wire(cab["x2/1"].port("terminal", "external"), estop.port("nc_1", "11"), label=False)
    b.wire(estop.port("nc_1", "12"), estop.port("nc_2", "21"), label=False)
    b.wire(estop.port("nc_2", "22"), k1.port("aux", "13"), label=False)
    b.wire(k1.port("aux", "14"), k2.port("aux", "13"), label=False)
    b.chain(("cabinet", "es"), (estop, "nc_1"), (estop, "nc_2"))
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
    # a board and its parts: the engine draws only its CONNECTOR function `edge` (model-0040,
    # spec B1); its fuse `F10` stays undrawn
    board = b.stamp(parts["board"], ("cabinet", "a1"), "A1", "sup")
    b.facet(PcbFacet, ("board", "pcb"), subject=parts["board"].part.id, revision="A")
    b.stamp(parts["fuse"], ("cabinet", "a1", "f1"), "F10", "sup", parent=board.item)


def _extra_relay(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """Relay `K9` in `=P2`: a coil chain and, in its own chain, one contact to terminal `X5:1`."""
    relay = b.stamp(parts["relay"], ("cabinet", "k9"), "K9", "p2")
    output = b.terminal(parts["terminal"], b.strip("X5"), 1, "p2")
    rail, zero = cab["x2/1"], cab["x4/2"]
    b.wire(rail.port("terminal", "external"), relay.port("coil", "A1"))
    b.wire(relay.port("coil", "A2"), zero.port("terminal", "internal"))
    b.chain(("cabinet", "k9", "coil"), (relay, "coil"))
    b.wire(rail.port("terminal", "external"), relay.port("no_1", "13"))
    b.wire(relay.port("no_1", "14"), output.port("terminal", "internal"))
    b.chain(("cabinet", "k9", "contact"), (relay, "no_1"), (output, "terminal"))


def _discovery_extras(b: _Builder, parts: dict[str, PartBundle], cab: Cabinet) -> None:
    """WP16 (`discovery=True`): potentials on the rail nets, and the three invented circuits
    ladder discovery needs that no hinted chain in this fixture exercises (layout-0034,
    "What the fixture lacks").

    Rails: `L1` on the incoming feed and each pump's own inlet (the natural feed and the
    two distribution points read as one physical net through the fuse pass-through,
    Finding 1); `24V` on the control-bus rail terminal and on a second, dedicated terminal
    `X6:1` (so the branch and reconvergent circuits below do not further crowd `X2:1`,
    already fanning out to five existing devices); `0V` on both zero-volt returns (two
    rails, one text); `M1`/`M2` on each pump's own field terminal. A wired second pole of
    `K1`'s main contact, in parallel with pole 1 (a side element, D1: the chain runs on
    through it, layout-0050). A terminal `X7:1`
    fed from the second `24V` terminal, fanning through two invented contacts `S10`/`S11`
    to two invented `0V` terminals (the branch case, a shared device before the fork,
    Finding 4). Two invented relays `K20`/`K21`, their `no_1` contacts wired in parallel
    between the second `24V` terminal and one coil `K22`'s `A1`, `A2` to one invented `0V`
    terminal (the reconvergent case, hint-mandatory, 13.5, Finding 5).
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
    # count on Q1's outlet net, the chain runs on (D1, layout-0050)
    k1 = cab["k1"]
    b.wire(k1.port("main", "1"), k1.port("main", "3"))
    b.wire(k1.port("main", "2"), k1.port("main", "4"))

    # a second, dedicated 24V terminal, so the two circuits below do not crowd X2:1's own
    # port further: exercises Finding 1 again (two rails, one text) for the source end
    x6 = b.terminal(parts["terminal"], b.strip("X6"), 1, "sup")
    b.rail(("cabinet", "rail", "24v", "2"), "24V", x6.port("terminal", "external"))

    # a shared terminal fed from the second 24V terminal, fanning through two contacts to
    # two 0V terminals: the branch case (Finding 4)
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
    # hint-mandatory (13.5, Finding 5)
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


def unit_with_release(
    key: Key, *, name: str, parent: Id[Unit] | None = None
) -> tuple[Unit, UnitRelease]:
    """A `Unit` keyed `key` and the version 1, revision `"1"` `UnitRelease` it instantiates."""
    release_key = ("unit_release", name, "1", "1")
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name=name,
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(id=make_id(Unit, key), key=key, release=release.id, parent=parent)
    return unit, release


def build_cabinet(
    *,
    reverse: bool = False,
    extra_relay: bool = False,
    broken_chain: bool = False,
    second_location: bool = False,
    discovery: bool = False,
) -> Draft:
    """Build the WP14 cabinet fixture: a `Draft`, not yet frozen (WP14).

    The invented design this must produce, in location `+C1`. Groups are the top-level
    `FUNCTION` nodes `SUP`, `P1`, `P2`, `ES`; every item is placed at one of them and at
    a location node.

    - Group `=SUP` (supply): supply terminal `-X1:1`, fuse `-F1`, 24 V rail terminal
      `-X2:1`, in one chain.
    - Groups `=P1`, `=P2` (two pump starters, siblings of equal shape). Each has a power
      chain (supply terminal `-X1:n+1`, breaker `-Qn`, contactor main contact `-Kn`,
      field terminal `-X3:n`) and a control chain (stop contact `-Sn`, contactor coil
      `-Kn`, 0 V rail terminal `-X4:n`), wired from the 24 V rail terminal `-X2:1`.
      `-X2:1` is one terminal with one home, the `sup` chain, and is in no other chain
      (a function is in one chain, layout-0021); both control chains wire to it from
      another group, so the engine replicates it. The contactor `Kn` is one item of the
      part `EX-CONTACTOR-3P` with three function templates: `coil` (`A1`, `A2`), `main`
      (three poles, ports `1`-`2`, `3`-`4`, `5`-`6`, three `switched` links) and `aux`
      (`13`-`14`, one `switched` link).
      Coil and main contact are two `Function`s of one `Item`, so they give a tag echo
      between a control page and a power page. Only pole 1 of `main` is wired.
    - Group `=ES` (e-stop): item `-S0` with two contacts `nc_1` and `nc_2` in one chain;
      the function `nc_2` carries a `layout.group_hint` to `=P1`, the straddling case.
    - One control signal from `-K1` `aux` (in `=P1`) to `-K2` `aux` (in `=P2`) with no
      terminal between them: a severed signal with one marker pair.
    - Functions in no chain (`FUNCTION_UNPLACED_IN_COLUMN`): lamp `-H1`, the two `aux`
      contacts (their wires carry the e-stop signal) and the relay `-K8`.
    - One cable item `W1` (its part has a `cable_product` facet, one `screen` function)
      with two cores from the rails to lamp `-H1`, and one relay `K8` with
      `installed=False` (drawn all the same).
    - One board item `A1` (its part has a `pcb` facet) with one board-edge connector
      function and a child fuse item `A1/F1`: functions of these are not drawn here.
    - One declared `Net`, `LATCH`, with no conductor on either port (both are ports of
      `-K8`), so the engine reads one `NetGroup` of exactly two ports.
    - Every chain link is a wire with a `wire` facet; the chain wires carry labels `W1001`
      and on, the e-stop and signal wires none.
    - Item authoring keys are `("cabinet", <tag in lower case>)`, for example
      `("cabinet", "w1")`, `("cabinet", "k8")`, `("cabinet", "a1")`, `("cabinet", "a1", "f1")`;
      a terminal is `("cabinet", "x1", "2")`. Tests find items by these keys, never by
      designation.
    - No `layout.profile`, `layout.sheet_format`, and `layout.symbol_choice` only where
      the default symbol table needs a port map: every terminal (`terminal` has no
      through path; `internal` is drawn at `n`, `external` at `s`) and every coil (a coil
      has no internal link, so no pole pair). A breaker or fuse needs none: `circuit-breaker`
      has a through path and the part's conductive link gives the pole pair.
    - The model validators find exactly one warning, `NET_UNREALISED` for the declared net
      (it has no conductor by design); every `layout.chain` link but the `broken_chain`
      one joins its two functions in one physical net.

    `reverse=True` adds the same records in the opposite order, for the shuffle test: the
    frozen models have one digest. `extra_relay=True` adds one relay `-K9` (its coil alone in a
    chain and one contact in its own chain, to terminal `-X5:1`) to `=P2` only, for the stability
    test. `broken_chain=True` adds a `layout.chain` (lamp `-H1`, contact of `-K8`) whose two
    functions share no connection, which must raise `HintError`. `second_location=True`
    adds a second location node `+C2` and places the items of `=P2` (and only those) there,
    so `=P2` is drawn in another drawing set. The shared terminal `-X2:1` stays in `=SUP`
    at `+C1`, so the control chain of `=P2` then crosses locations.

    `discovery=True` (WP16) leaves out every `layout.chain` above (`chain` becomes a no-op,
    the WP15 spike's own method) and authors a `layout.profile` with a wider sheet,
    the house numbers otherwise unchanged, so ladder discovery must find every rung this
    fixture's chains would otherwise have hinted, plus `_discovery_extras`' three invented
    circuits. Not combined with `broken_chain` or `extra_relay`: nothing here reads that
    combination, so it is unspecified.
    """
    b = _Builder(second_location=second_location, chains_enabled=not discovery)
    parts = {spec.key: b.part(spec) for spec in _specs()}
    cab = {tag: b.strip(tag.upper()) for tag in ("x1", "x2", "x3", "x4")}
    b.choice(FunctionKind.TERMINAL, "terminal", {"internal": "n", "external": "s"})
    b.choice(FunctionKind.COIL, "operating-device", {"A1": "in", "A2": "out"})
    _supply(b, parts, cab)
    _pump(b, parts, cab, 1)
    _pump(b, parts, cab, 2)
    _estop_and_signal(b, parts, cab)
    _extras(b, parts, cab)
    if extra_relay:
        _extra_relay(b, parts, cab)
    if broken_chain:
        b.chain(("cabinet", "broken"), (cab["h1"], "lamp"), (cab["k8"], "no_1"))
    if discovery:
        _discovery_extras(b, parts, cab)
        # The house sheet's own values, doubled in width and a third taller, authored under
        # a fresh key: its own fixed id is never put into a model (model decision 0029), but
        # `layout.profile.sheet_format` must name an authored `layout.sheet_format` record.
        # This fixture's extra circuits, all undirected by a chain, need the room: at the
        # house width, `=SUP` no longer fits one page (`GROUP_SPLIT`), which severs a wire
        # onto a port's own lane and trips open-questions.md 13.18's known, open `ROUTE_FAILED` --
        # not a discovery defect, so this sidesteps it rather than exercising it here.
        house = default_sheet_format()
        sheet_key = ("cabinet", "discovery", "sheet")
        sheet = ModelSheetFormat(
            id=make_id(ModelSheetFormat, sheet_key),
            key=sheet_key,
            name=house.name,
            width_mm=house.width_mm * 2,
            height_mm=house.height_mm + 100,
            content_x_mm=house.content_x_mm,
            content_y_mm=house.content_y_mm,
            content_width_mm=house.content_width_mm * 2,
            content_height_mm=house.content_height_mm + 100,
            frame_columns=house.frame_columns,
            frame_rows=house.frame_rows,
            module_mm=house.module_mm,
        )
        b.add(sheet)
        profile_key = ("cabinet", "discovery", "profile")
        b.add(
            ModelProfile(
                id=make_id(ModelProfile, profile_key),
                key=profile_key,
                sheet_format=sheet.id,
                column_gap=DEFAULT_PROFILE.column_gap,
                row_gap=DEFAULT_PROFILE.row_gap,
                route_margin=DEFAULT_PROFILE.route_margin,
                text_height=DEFAULT_PROFILE.text_height,
                marker_padding=DEFAULT_PROFILE.marker_padding,
                route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
                route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
                band_ranks=DEFAULT_PROFILE.band_ranks,
            )
        )
    draft = Draft()
    draft.extend(reversed(b.records) if reverse else b.records, origin=_ORIGIN)
    return draft
