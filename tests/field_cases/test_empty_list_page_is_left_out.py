"""Field case: a list page with no rows is not in the PDF.

The engineering shape: a cabinet of two power supplies, a redundancy module and two terminal
strips, drawn as a CABINET_SCHEMATIC. It has no PLC channel, so the PLC list has no rows.

The bug: the PDF held a page for the PLC list that said only "None.", and counted it in the
page numbers ("3 of 6").
The rule (decision pdf-0019, amending pdf-0011): a list page whose list has no rows is not
emitted; page numbers count only the emitted pages.
"""

import re
import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU


def _plant(d) -> None:
    """Two supplies and a redundancy module, one 24 V feed through two strips (the I3 plant)."""
    with d.function("G", "Group"):
        psus = {tag: d.device(tag, "DEMO-PSU-24") for tag in ("T1", "T2")}
        module = d.device("U1", "DEMO-RED-2IN")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.wire(module.out["+"], live[1].outer, wire=(BU, 0.5))
    d.wire(module.out["-"], zero[1].outer, wire=(BU, 0.5))
    for tag, group, n in (("T1", module.in_1, "1"), ("T2", module.in_2, "2")):
        d.wire(psus[tag].output["+"], group[f"{n}+"], wire=(BU, 0.5))
        d.wire(psus[tag].output["-"], group[f"{n}-"], wire=(BU, 0.5))


def _pdf_and_source() -> tuple[bytes, str]:
    """The I3 cabinet's PDF bytes and the Typst source it was compiled from."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant(d)
    work = Path(tempfile.mkdtemp())
    (work / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=work / "cover.md")
    result = fr.build(d, doc)
    fr.write(result, work / "out", intermediates=work / "im")
    (pdf,) = (work / "out").glob("*.pdf")
    (typ,) = (work / "im").glob("*.typ")
    return pdf.read_bytes(), typ.read_text(encoding="utf-8")


def test_the_cabinet_with_no_plc_channel_has_five_pages_and_no_none_page() -> None:
    """Cover, schematic, two strips and the BOM: five pages, and no "None." anywhere."""
    pdf, source = _pdf_and_source()
    assert len(re.findall(rb"/Type\s*/Page\b(?!s)", pdf)) == 5
    assert "None." not in source
