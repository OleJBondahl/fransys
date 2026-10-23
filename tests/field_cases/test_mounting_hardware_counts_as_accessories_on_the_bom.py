"""Field case: mounting hardware on a bolted part is an accessory and reaches the BOM with a count.

The engineering shape: a board carries two bolted fuses F1 and F2, each tag on a press-fit
threaded sleeve. The four sleeves are mounting hardware: they are bought, counted and fitted, but
they are no circuit device. The author states each once, as a part with no function put in its
fuse: `d.device(None, part, name=..., parent=f1)`. A name is unique in the design,
so each sleeve has its own.

The ask: the sleeves must reach the BOM with a count per part, and draw nothing.

The answer is the accessory spelling that already exists (guide parts.md, "An accessory in its
holder"): one BOM line for the sleeve part, count 4, designations the holders' (F1 and F2), and no
symbol. No code changed; the case pins the behaviour and the guide now shows it.
"""

import csv
lazy from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.derive import bom_lines, item_designation, item_functions

_SLEEVE = "DEMO-JUMPER-BAR-3P"  # a functionless demo part, standing in for a press-fit sleeve


def _built(root: Path) -> tuple[fr.BuildResult, list[fr.Device]]:
    """F1 and F2 feeding the lamp H1, two sleeves on each fuse."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Board"):
        h1 = d.device("H1", "DEMO-LAMP-24")
        fuses = [d.device(tag, "DEMO-FUSE-HOLDER-PCB") for tag in ("F1", "F2")]
        sleeves = [
            d.device(None, _SLEEVE, name=f"{tag}_sleeve_{n}", parent=fuse)
            for tag, fuse in zip(("f1", "f2"), fuses, strict=True)
            for n in "ab"
        ]
        d.detail.wire(fuses[0][2], h1[1], wire=("BK", 1.5))
        d.detail.wire(fuses[1][2], h1[2], wire=("BU", 1.5))
    (root / "cover.md").write_text("# board\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=root / "cover.md")
    return fr.build(d, doc), sleeves


def test_four_sleeves_make_one_bom_line_printing_their_holders(tmp_path: Path) -> None:
    """One line, count 4, designations F1 and F2."""
    result, sleeves = _built(tmp_path)
    for sleeve, holder in zip(sleeves, ("F1", "F1", "F2", "F2"), strict=True):
        assert item_designation(result.model, sleeve.id) == holder
    (line,) = [ln for ln in bom_lines(result.model) if ln.mpn == _SLEEVE]
    assert line.count == 4
    assert line.designations == ("-F1", "-F2")


def test_the_written_bom_csv_has_the_sleeve_row(tmp_path: Path) -> None:
    """The exported BOM carries the same line."""
    result, _ = _built(tmp_path)
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "im")
    with (tmp_path / "out" / "data" / "bom.csv").open(encoding="utf-8", newline="") as f:
        (row,) = [r for r in csv.DictReader(f) if r["mpn"] == _SLEEVE]
    assert row["count"] == "4"
    assert row["designations"] == "-F1; -F2"


def test_the_sleeves_draw_nothing(tmp_path: Path) -> None:
    """The sleeves own no function; the fuses' and the lamp's symbols are drawn and none else."""
    result, sleeves = _built(tmp_path)
    model = result.model
    owned = item_functions(model)
    assert all(s.id not in owned for s in sleeves)
    drawn = sorted(
        symbol.key for drawing in drawn_pages(model).values() for symbol in drawing.symbols
    )
    assert drawn == ["fuse", "fuse", "lamp"]  # F1, F2 and H1: no symbol for a sleeve
