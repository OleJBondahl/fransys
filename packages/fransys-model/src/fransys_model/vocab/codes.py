"""The model's finding codes raised by its passes and the block diagram (BUILD-MESSAGES M1)."""

from typing import Any, Final
lazy from collections.abc import Iterable

from fransys_model.kernel import CodeInfo, Finding, Id, Severity

from . import codes_drawn, codes_structure, codes_wiring, codes_wiring_more

ORDER_HINT_CYCLE: Final[str] = "ORDER_HINT_CYCLE"

_OWN: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="DESIGNATION_DUPLICATE",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=(
            "Two items or unit instances under one parent print one designation: a tag equal to a sibling's text, or a retired or moved released one."
        ),
        fix=(
            'Give each item or unit instance under one parent its own tag, one no released revision reserved. Write: d.device("X2", "DEMO-CONN-2P")'
        ),
        page="findings-build",
    ),
    CodeInfo(
        code="DIAGRAM_CABLE_FANOUT",
        severity=Severity.INFO,
        stage="render",
        who="note",
        cause=("A cable reaches three or more boxes, so the block diagram draws a line from its first box to each other."),
        fix="Nothing is wrong; split the cable only if a line per pair is not wanted.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_CABLE_ONE_BOX",
        severity=Severity.INFO,
        stage="render",
        who="note",
        cause="A cable's ends reach one box or none, so the block diagram draws no line for it.",
        fix="Usually nothing to fix: the cable runs inside one box, or an end is an unmated plug.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_LOOSE_WIRE",
        severity=Severity.INFO,
        stage="render",
        who="note",
        cause="In the system reading, a wire with no cable joins two boxes and is not drawn.",
        fix=("Usually nothing to fix: the unit pages show it as stubs. Put it in a cable to give it a line."),
        page="findings-render",
    ),
    CodeInfo(
        code="HARNESS_END_AMBIGUOUS",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause="Two or more ends of one cable print the same text in its drawing.",
        fix=('Give each cable end its own text with distinct locations or distinct tags. Write: d.device("X2", "DEMO-CONN-2P", place="A2")'),
        page="findings-build",
    ),
    CodeInfo(
        code="PART_LIBRARY_VERSION_CONFLICT",
        severity=Severity.ERROR,
        stage="library load",
        who="consumer",
        cause="Two `PartLibrary` records share a name but declare different versions.",
        fix='Load one version of each named part library. Write: fr.design("demo-parts")',
        page="findings-build",
    ),
    CodeInfo(
        code="PLC_CHANNEL_CONTESTED",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=(
            "Two or more PLC requests of the channel's signal are wired to the same channel. "
            "The finding names the channel's pins and every request; none of them binds, and "
            "none goes to the free queue."
        ),
        fix=('Keep one PLC request per channel and wire each other request to a channel of its own. Write: d.series(k1.coil["A1"], a1.di_1)'),
        page="findings-build",
    ),
    CodeInfo(
        code="PLC_REQUEST_AMBIGUOUS",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=(
            "A PLC request is wired so that several free channels of its signal tie: its net "
            "reaches them all, or all by a direct conductor. It gets no binding."
        ),
        fix=('Wire the request straight to one channel of its signal, or free the other channels. Write: d.series(k1.coil["A1"], a1.di_1)'),
        page="findings-build",
    ),
    CodeInfo(
        code="PLC_REQUEST_UNSERVABLE",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=("No free PLC channel of the requested signal type on the request's unit chain (its unit declares none, or every one is taken)."),
        fix=(
            "Add a PLC module with a free channel of the requested signal type to the unit or"
            ' a parent unit, or move another request off one. Write: d.device("A1", "DEMO-'
            'PLC-DI-16")'
        ),
        page="findings-build",
    ),
    CodeInfo(
        code="PORT_DESIGNATION_DUPLICATE",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=("Two or more ports of one item print the same designation text, so a drawing or list cannot tell them apart."),
        fix=('Give each port of one item its own printed pin marking in the part file. Write: marking = "A2"'),
        page="findings-build",
    ),
    CodeInfo(
        code="PRODUCT_DESIGNATION_DUPLICATE",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=(
            "Two items print the same product designation (location plus own label): both at "
            "one location or, unplaced, both unnumbered alike in one unit instance."
        ),
        fix=('Give each item a distinct location or label: place one elsewhere, or tag it. Write: d.device("X2", "DEMO-CONN-2P", place="A2")'),
        page="findings-build",
    ),
    CodeInfo(
        code="REFERENCE_DESIGNATION_DUPLICATE",
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=("Two items in the function or location aspect print the same full reference designation (e.g. two unit instances at one location)."),
        fix=('Place the two items at different locations so their designations differ. Write: d.device("X2", "DEMO-CONN-2P", place="A2")'),
        page="findings-build",
    ),
    CodeInfo(
        code=ORDER_HINT_CYCLE,
        severity=Severity.ERROR,
        stage="build",
        who="consumer",
        cause=("Authored `d.layout.order` hints contradict each other in a cycle (a before b, b before a), so no page order can honour them."),
        fix=("Drop one hint of the cycle the message names. Write: d.layout.order(a, b) for one direction only"),
        page="findings-build",
    ),
    CodeInfo(
        code="DESIGNATION_MOVED",
        severity=Severity.ERROR,
        stage="release",
        who="consumer",
        cause=("An item or unit instance pinned in the previous release now prints a different designation, written or numbered."),
        fix=("No call clears this: restore the released tag on {subject}; only a new version may change it."),
        page="findings-build",
    ),
    CodeInfo(
        code="DESIGNATION_NEW_IN_REVISION",
        severity=Severity.INFO,
        stage="build, release",
        who="note",
        cause="A new untagged item or unit instance took the next free number in a later revision.",
        fix="Nothing is wrong; tag it if its number must stay fixed.",
        page="findings-build",
    ),
)

FINDING_CODES: tuple[CodeInfo, ...] = (
    *_OWN,
    *codes_drawn.FINDING_CODES,
    *codes_structure.FINDING_CODES,
    *codes_wiring.FINDING_CODES,
    *codes_wiring_more.FINDING_CODES,
)

_BY_CODE: dict[str, CodeInfo] = {info.code: info for info in FINDING_CODES}


def finding(code: str, subjects: Iterable[Id[Any]], message: str, **fix_values: str) -> Finding:
    """The `Finding` of `code`: its one severity, its fix filled from `fix_values`."""
    return _BY_CODE[code].finding(subjects, message, **fix_values)
