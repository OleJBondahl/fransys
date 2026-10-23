"""The KiCad check's finding codes (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="NET_NAME_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="kicad",
        who="consumer",
        cause="Two or more KiCad netlist nets share a name, so KiCad would merge them on import.",
        fix="Give each net a distinct name. Write: d.detail.net(<distinct name>, *ports)",
        page="findings-kicad",
    ),
    CodeInfo(
        code="NET_SINGLE_PIN",
        severities=(Severity.INFO,),
        stage="kicad",
        who="note",
        cause="A KiCad netlist net has one pin.",
        fix="Nothing is wrong; wire a second end only if one was meant.",
        page="findings-kicad",
    ),
    CodeInfo(
        code="NODE_WITHOUT_COMPONENT",
        severities=(Severity.WARNING,),
        stage="kicad",
        who="consumer",
        cause=(
            "A netlist pin belongs to an item with no footprint (or is the board's own pin), "
            "so KiCad drops it on import."
        ),
        fix=(
            "No call clears this: give the item's part a footprint, or model the connector as a "
            "child item with one."
        ),
        page="findings-kicad",
    ),
    CodeInfo(
        code="PAD_ON_MULTIPLE_NETS",
        severities=(Severity.ERROR,),
        stage="kicad",
        who="consumer",
        cause="One component pad is in more than one KiCad netlist net.",
        fix="No call clears this: fix the wiring so each pad is on exactly one net.",
        page="findings-kicad",
    ),
    CodeInfo(
        code="PART_WITHOUT_FOOTPRINT",
        severities=(Severity.WARNING,),
        stage="kicad",
        who="consumer",
        cause="A board item's part has no footprint, so the KiCad netlist omits it.",
        fix="No call clears this: add a footprint to the part's data.",
        page="findings-kicad",
    ),
    CodeInfo(
        code="PIN_ID_COLLISION",
        severities=(Severity.ERROR,),
        stage="kicad",
        who="part author",
        cause=(
            "Two pins of one board part would write one KiCad pin id, because KiCad keys a pin by "
            "its name, which is the footprint pad name. A labelled connector may repeat a pin name "
            "in the drawing; the netlist cannot."
        ),
        fix=(
            "No call clears this: rename the part's pins so each is its footprint pad name, "
            "in the part file."
        ),
        page="findings-kicad",
    ),
    CodeInfo(
        code="REFERENCE_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="kicad",
        who="consumer",
        cause="Two board parts share one reference designation in the KiCad netlist.",
        fix=(
            "Give each part a distinct tag, which sets its designation. Write: "
            "d.device(<tag>, <mpn>)"
        ),
        page="findings-kicad",
    ),
    CodeInfo(
        code="UNCONNECTED_PIN",
        severities=(Severity.INFO,),
        stage="kicad",
        who="note",
        cause="A pin of a board part is in no net in the KiCad netlist.",
        fix="Usually nothing to fix unless a connection was meant.",
        page="findings-kicad",
    ),
)

_BY_CODE: dict[str, CodeInfo] = {info.code: info for info in FINDING_CODES}


def fix_text(code: str, **values: str) -> str:
    """The `fix` of one finding of `code`: the code's template filled with `values`."""
    return _BY_CODE[code].filled(**values)
