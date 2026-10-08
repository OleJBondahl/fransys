"""Field case: a cabinet connects to equipment that other parties supplied, known by terminals only.

The engineering shape: an alarm system's input terminals `X8` (4 of them) and a switchboard's
outgoing feeder `Q8` (pins L1 L2 L3 N PE) feed a cabinet's motor and supply. No part file exists
for either: only the terminal names are known, and for the feeder its voltage and earthing.

The bug (v0.13.1): `d.terminal_strip("X8", None, 4, external=True)` and `d.device("Q8", None,
external=True, pins=...)` raised `AuthorError: part must be an MPN string or a part class with an
mpn, not None`. The rule (PATCH-0132 E1 to E6, decisions author-0033, model-0183, layout-0161): an
external device or strip may take `None` for its part, needs a tag, has no BOM line and draws as
a generic box or as terminals.
"""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

_NO_PART = "part must be an MPN string"


def _plant(d: fr.Design) -> tuple[fr.TerminalStrip, fr.Device]:
    x8 = d.terminal_strip("X8", None, 4, external=True)
    q8 = d.device("Q8", None, external=True, pins=("L1", "L2", "L3", "N", "PE"))
    d.ac_supply("S", 400, q8["L1"], q8["L2"], q8["L3"], n=q8["N"])
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    d.wire(x8[1].outer, motor["U"], wire=(BK, 1.5))
    d.wire(q8["PE"], motor["PE"], wire=(BK, 1.5))
    return x8, q8


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        _plant(d)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _keys(model: Model, ids: tuple[Id[Any], ...]) -> list[tuple[str, ...]]:
    return [model.key_of(i) or () for i in ids]


def test_a_part_less_external_strip_and_device_build_and_write(tmp_path: Path) -> None:
    result = _built()
    model = result.model
    assert not [f for f in result.findings if f.severity.value == "error"]
    for finding in result.findings:
        if finding.code in {"ITEM_WITHOUT_PART", "SYMBOL_DEFAULTED"}:
            assert not [k for k in _keys(model, finding.subjects) if k[0] in {"X8", "Q8"}]
    files = fr.write(result, tmp_path)
    bom = next(p for p in files if p.name.endswith("bom.csv")).read_text(encoding="utf-8")
    assert "DEMO-MOTOR-4KW" in bom
    assert "X8" not in bom
    assert "Q8" not in bom


def test_the_schematic_draws_q8_as_a_box_of_five_pins_and_x8_as_terminals() -> None:
    model = _built().model
    layout = stage_results(model, read_inputs(model))[0].layout
    drawn = {tuple(model.key_of(p.function) or ()): p for p in layout.placed}
    box = drawn[("G/Q8", "fn", "box")]
    assert box.geometry.key == "generic-box"
    terminal = drawn[("X8", "terminal", "1", "fn", "terminal")]
    assert terminal.geometry.key == "terminal"
    assert {lb.kind.value for lb in layout.labels if lb.subject == terminal.function} == {"tag"}
    labels = [lb for lb in layout.labels if lb.subject == box.function]
    assert [lb.kind.value for lb in labels] == ["tag"]
    pins = {
        lb.slot
        for lb in layout.labels
        if lb.kind.value == "marking" and (model.key_of(lb.subject) or ())[:2] == ("G/Q8", "fn")
    }
    assert pins == {f"marking.{pin}" for pin in ("L1", "L2", "L3", "N", "PE")}


def test_a_part_less_strip_offers_only_its_outer_side() -> None:
    d = fr.design("demo_parts", place="CAB")
    x8 = d.terminal_strip("X8", None, 4, external=True)
    with pytest.raises(fr.AuthorError, match="no internal port"):
        _ = x8[1].inner


def _raises(call, match: str = "") -> None:
    with pytest.raises(fr.AuthorError, match=match):
        call(fr.design("demo_parts", place="CAB"))


def test_none_for_the_part_needs_external_and_the_right_form() -> None:
    _raises(lambda d: d.device("Q8", None, pins=("L1",)), "external")
    _raises(lambda d: d.terminal_strip("X8", None, 4), "external")
    _raises(lambda d: d.cable("W1", None, external=True), _NO_PART)
    _raises(lambda d: d.device("Q8", "DEMO-MOTOR-4KW", external=True, pins=("L1",)), "pins")
    _raises(lambda d: d.device("Q8", None, external=True), "pins")


def test_a_part_less_item_with_a_floating_tag_raises() -> None:
    _raises(
        lambda d: d.device(None, None, name="q", external=True, pins=("L1",)),
        "an item with no part needs a tag",
    )
    _raises(
        lambda d: d.terminal_strip(None, None, 2, name="x", external=True),
        "an item with no part needs a tag",
    )


def test_a_part_less_device_pins_take_a_dc_supply() -> None:
    """E7: `plus=`, `minus=` and `voltage=` on a box's pins build with no ERROR."""
    d = fr.design("demo_parts", place="CAB")
    q9 = d.device("Q9", None, external=True, pins=("L+", "L-"))
    d.dc_supply("D", plus=q9["L+"], minus=q9["L-"], voltage=24)
    d.wire(q9["L+"], d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 1.5))
    assert not [f for f in fr.build(d).findings if f.severity.value == "error"]
