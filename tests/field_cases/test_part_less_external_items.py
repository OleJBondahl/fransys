"""Field case: an external cabinet connects to equipment known only by terminal names, with no part file for them.
The bug (v0.13.1): external strips and devices with part None raised 'part must be an MPN string' (AuthorError).
Fixed by author-0033, model-0183 and layout-0161, an external device or strip may take None for its part and needs a tag."""

from typing import TYPE_CHECKING, Any
lazy from pathlib import Path

import fransys as fr
import pytest
from _drawn_facts import Placed, PlacedText, symbol_subjects, text_subjects
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BK

from fransys_model.derive import strip_of, terminal_items, terminal_rows
from fransys_model.derive.drawing_text import external_note
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

_NO_PART = "part must be an MPN string"


def _plant(d: fr.Design) -> tuple[fr.TerminalStrip, fr.Device]:
    x8 = d.terminal_strip("X8", None, 4, external=True)
    q8 = d.device("Q8", None, external=True, pins=("L1", "L2", "L3", "N", "PE"))
    d.ac_supply("S", 400, q8["L1"], q8["L2"], q8["L3"], n=q8["N"])
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(x8[1].outer, motor["U"], wire=(BK, 1.5))
    d.series(q8["PE"], motor["PE"], wire=(BK, 1.5))
    return x8, q8


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        _plant(d)
    doc = unit_document(cab)
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


def _drawn(model: Model, key: tuple[str, ...]) -> tuple[Placed, list[PlacedText]]:
    """The symbol drawn for the function with this authoring key, and the texts it owns."""
    (fid,) = (f.id for f in functions(model).values() if tuple(model.key_of(f.id) or ()) == key)
    (symbol,) = (s for s in symbol_subjects(model) if s.owner == fid.value)
    texts = [t for t in text_subjects(model) if t.function == fid]
    return symbol, texts


def test_the_schematic_draws_q8_as_a_box_of_five_pins_and_x8_as_terminals() -> None:
    model = _built().model
    box, box_texts = _drawn(model, ("G/Q8", "fn", "box"))
    assert box.key == "generic-box"
    terminal, terminal_texts = _drawn(model, ("X8", "terminal", "1", "fn", "terminal"))
    assert terminal.key == "terminal"
    assert {t.kind for t in terminal_texts} == {"TAG"}
    assert [t.kind for t in box_texts] == ["TAG"]
    pins = {slot for slot in dict(box.slots) if slot.startswith("marking.")}
    assert pins == {f"marking.{pin}" for pin in ("L1", "L2", "L3", "N", "PE")}


def test_each_external_item_draws_one_by_others_note() -> None:
    model = _built().model
    notes = [t for d in drawn_pages(model).values() for t in d.texts if t.text == external_note()]
    assert len(notes) == 2  # one per external item


def test_a_part_less_strip_offers_only_its_outer_side() -> None:
    d = fr.design("demo_parts", place="CAB")
    x8 = d.terminal_strip("X8", None, 4, external=True)
    with pytest.raises(fr.AuthorError, match=r"strip X8, terminal 1: no internal port.*write X8\[1\]\.outer"):
        _ = x8[1].inner


def test_a_part_less_strip_bridges_separate_adjacent_pairs_in_the_table_only() -> None:
    """R1767: the jumper joins the terminals' own ports; the terminal table shows the groups, and a far-off pair is refused."""
    d = fr.design("demo_parts", place="CAB")
    d.terminal_strip("X2", None, 4, bridged=((1, 2), (3, 4)), external=True)
    model = fr.build(d).model
    rows = [
        (r.designation, r.jumper_group, r.external_ends)
        for s in terminal_items(model)
        if (strip := strip_of(model, s))
        for r in terminal_rows(model, strip)
        if r.terminal == s
    ]
    assert sorted(set(rows)) == [
        ("-X2:1", 1, ("+CAB-X2:2",)),
        ("-X2:2", 1, ("+CAB-X2:1",)),
        ("-X2:3", 2, ("+CAB-X2:4",)),
        ("-X2:4", 2, ("+CAB-X2:3",)),
    ]
    with pytest.raises(fr.AuthorError, match=r"X2: bridged=\(1, 5\).*number the new terminal next to its partner"):
        fr.design("demo_parts", place="CAB").terminal_strip("X2", None, 4, bridged=(1, 5), external=True)


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
    d.series(q9["L+"], d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 1.5))
    assert not [f for f in fr.build(d).findings if f.severity.value == "error"]
