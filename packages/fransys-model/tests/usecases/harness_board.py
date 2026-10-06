"""WP17 synthetic use case: a harness with a board (ROADMAP WP17).

All parts, MPNs and designations are invented for this repo; none describe a real
product or project (CLAUDE.md invariant, red flag "Real project data in fixtures").
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from kit import Kit, PartSpec, Slot, template_of

from fransys_model.kernel import make_id
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    Aspect,
    FunctionKind,
    Gender,
    LinkKind,
    NetClass,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.facets.pcb import FootprintFacet, PcbFacet

if TYPE_CHECKING:
    from fransys_model.kernel import Draft

_FOUR_PINS = tuple((str(number), PortRole.GENERIC) for number in range(1, 5))
_CORE_COLOURS = ("BN", "WH", "BU", "SH")


def build_harness_board() -> Draft:
    """Build the WP17 harness-and-board fixture: a `Draft`, not yet frozen.

    The invented design (the fan-out cable is the one item left unnumbered, so
    `passes.numbering` has a `W`-class item to number):

    - Board `JB1` (`SIM-BOARD-IOEXP`, a `pcb` facet, `class_code="A"`) with the board-edge
      connector `J1` as a function (`connector` facet, male, 4 pins), a fuse `F1`
      (`SIM-FUSE-1A-SMD`) and a relay `K10` (`SIM-RELAY-SMD-5V`) as child items, both parts
      with a `footprint` facet. The board's traces are the declared nets `V5`, `V5_RET`
      and `OUT` (no conductor models a trace; a board-realised net is not a finding).
    - Harness `WH1`, a part-less item (decision 0026): its children by `parent` are the
      housing and the fan-out cable below. The sensors and the board are the plant's, not its
      children. The designation is `WH1` and not `W1`, which the cabinet design already holds
      among the parentless items of the merged design.
    - Harness housing `H1` (`SIM-CONN-HOUSING-4P`, female, 4 pins), a child of `WH1`, mated to
      `J1`: ports of equal name become conductive.
    - Fan-out cable (`SIM-CABLE-4X0.5`, `designation=None`, a child of `WH1`, a `cable`
      facet of 1500 mm): four cores, one
      end each on the housing's pins `P1:1` to `P1:4`; three run on to remote sensors `B10`,
      `B11`, `B12` (part-less items, one `signal` port each) and the fourth, the shield, to the
      housing's `shell:PE` port.
    - Board-side items placed at product node `-JB1` and location node `+C2`.
    """
    kit = Kit("tests/usecases/harness_board.py")
    board = kit.part(
        PartSpec(
            "board",
            "SIM-BOARD-IOEXP",
            "A",
            PartCategory.BOARD,
            {"J1": (FunctionKind.CONNECTOR, _FOUR_PINS)},
        )
    )
    fuse = kit.part(
        PartSpec(
            "fuse-1a",
            "SIM-FUSE-1A-SMD",
            "F",
            PartCategory.PROTECTION,
            {
                "element": (
                    FunctionKind.PROTECTION,
                    (("1", PortRole.GENERIC), ("2", PortRole.GENERIC)),
                )
            },
            ((("element", "1"), ("element", "2"), LinkKind.CONDUCTIVE),),
        )
    )
    relay = kit.part(
        PartSpec(
            "relay-smd",
            "SIM-RELAY-SMD-5V",
            "K",
            PartCategory.ELECTROMECHANICAL,
            {
                "coil": (FunctionKind.COIL, (("A1", PortRole.GENERIC), ("A2", PortRole.GENERIC))),
                "no_1": (
                    FunctionKind.CONTACT_NO,
                    (("13", PortRole.GENERIC), ("14", PortRole.GENERIC)),
                ),
            },
            ((("no_1", "13"), ("no_1", "14"), LinkKind.SWITCHED),),
        )
    )
    housing = kit.part(
        PartSpec(
            "housing-4p",
            "SIM-CONN-HOUSING-4P",
            "H",
            PartCategory.CONNECTOR,
            {
                "P1": (FunctionKind.CONNECTOR, _FOUR_PINS),
                "shell": (FunctionKind.CONNECTOR, (("PE", PortRole.PE),)),
            },
        )
    )
    cable_part = kit.part(PartSpec("cable-4x05", "SIM-CABLE-4X0.5", "W", PartCategory.CABLE))

    kit.facet(PcbFacet, ("board", "pcb"), subject=board.part.id, revision="A")
    for bundle, name in ((fuse, "F_1206"), (relay, "K_SMD_5V")):
        kit.facet(
            FootprintFacet,
            (bundle.part.key[0], "footprint"),
            subject=bundle.part.id,
            library="ExampleLib",
            name=name,
        )
    for bundle, function, gender in ((board, "J1", Gender.MALE), (housing, "P1", Gender.FEMALE)):
        kit.facet(
            ConnectorFacet,
            (bundle.part.key[0], function, "connector"),
            subject=template_of(bundle, function),
            style="header-4p",
            pincount=4,
            gender=gender,
        )
    # model-0071: the shell prints no label of its own, its `PE` pin prints under the housing.
    kit.facet(
        ConnectorFacet,
        (housing.part.key[0], "shell", "connector"),
        subject=template_of(housing, "shell"),
        style="shell",
        pincount=1,
        gender=Gender.NEUTRAL,
        marking="",
    )
    kit.facet(
        CableProductFacet,
        ("cable-4x05", "cable_product"),
        subject=cable_part.part.id,
        core_colours=_CORE_COLOURS,
        gauge_mm2=Decimal("0.5"),
        shielded=True,
    )

    jb1 = kit.stamp(board, ("jb1",), Slot("JB1"))
    f1 = kit.stamp(fuse, ("jb1", "f1"), Slot("F1", parent=jb1.item))
    k10 = kit.stamp(relay, ("jb1", "k10"), Slot("K10", parent=jb1.item))
    harness = kit.container(("w-harness",), "WH1")
    h1 = kit.stamp(housing, ("h1",), Slot("H1", parent=harness.item))
    cable = kit.stamp(cable_part, ("w-fanout",), Slot(None, parent=harness.item))
    kit.facet(CableFacet, ("w-fanout", "cable"), subject=cable.item, length_mm=1500)
    kit.mate(jb1.function("J1"), h1.function("P1"), ("j1-p1",))

    sensors = []
    for number in (10, 11, 12):
        key = (f"b{number}",)
        item = Item(
            id=make_id(Item, key),
            key=key,
            part=None,
            parent=None,
            position=None,
            tag=f"B{number}",
            description="Invented remote sensor",
            installed=True,
        )
        function = Function(
            id=make_id(Function, (*key, "signal")),
            key=(*key, "signal"),
            item=item.id,
            template=None,
            name="signal",
            kind=FunctionKind.SENSOR,
        )
        port = Port(
            id=make_id(Port, (*key, "signal", "signal")),
            key=(*key, "signal", "signal"),
            function=function.id,
            template=None,
            name="signal",
            role=PortRole.GENERIC,
        )
        kit.add(item, function, port)
        sensors.append(port.id)
    far_ends = (*sensors, h1.port("shell", "PE"))
    for index, far in enumerate(far_ends, start=1):
        kit.core(cable, index, (h1.port("P1", str(index)), far))

    kit.net(
        "V5",
        (
            jb1.port("J1", "1"),
            f1.port("element", "1"),
            f1.port("element", "2"),
            k10.port("coil", "A1"),
            k10.port("no_1", "13"),
        ),
        net_class=NetClass.POWER,
        potential="+5V",
    )
    kit.net(
        "V5_RET",
        (k10.port("coil", "A2"), jb1.port("J1", "2")),
        net_class=NetClass.POWER,
        potential="0V",
    )

    kit.net("OUT", (k10.port("no_1", "14"), jb1.port("J1", "3")), net_class=NetClass.SIGNAL)

    product = kit.node("jb1-product", Aspect.PRODUCT, "JB1", "board")
    location = kit.node("c2", Aspect.LOCATION, "C2", "remote panel")
    for placed in (jb1, f1, k10):
        kit.place(placed, product, location)
    return kit.draft
