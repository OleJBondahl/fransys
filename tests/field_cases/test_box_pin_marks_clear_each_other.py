"""Field case: a box with ten wired pins named SIGNAL_CHANNEL_NN, each to a terminal of its own strip.
The bug: the layout sets the pin x from the neighbour's keep-out, so neighbouring pin markings print over each other.
Fixed by layout-0572, a pin's keep-out on a box side holds its measured marking (G05-PIN-LINE)."""

import itertools
lazy from pathlib import Path

import fransys as fr
import fransys_parts
from _drawn_extent import page_ink
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.kernel import merge

_LIBRARY = 'schema = 2\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_FUNCTION = """
[[function]]
name = "c{n}"
kind = "load"
ports = [{{ name = "SIGNAL_CHANNEL_{n:02d}", role = "generic" }}, {{ name = "RET_{n:02d}", role = "generic" }}]
"""
_HEAD = 'schema = 2\n\n[part]\nmpn = "FLD-LONG-MARKS"\nmanufacturer = "Demo"\ndescription = "d"\ncategory = "generic"\nclass_code = "K"\n'


def _built(tmp_path: Path, count: int) -> fr.BuildResult:
    (tmp_path / "parts").mkdir()
    (tmp_path / "library.toml").write_text(_LIBRARY)
    (tmp_path / "parts" / "marks.toml").write_text(_HEAD + "".join(_FUNCTION.format(n=n) for n in range(1, count + 1)))
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(tmp_path))
    d = fr.Design(draft, place="CAB")
    cab = d.location("CAB", "Cabinet")
    box = d.device("K1", "FLD-LONG-MARKS")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    for n in range(1, count + 1):
        fn = getattr(box, f"c{n}")
        d.series(fn[f"SIGNAL_CHANNEL_{n:02d}"], strip[2 * n - 1], wire=(BU, 0.5))
        d.series(fn[f"RET_{n:02d}"], strip[2 * n], wire=(BU, 0.5))
    (tmp_path / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "cover.md"))


def _clear(result: fr.BuildResult, count: int) -> None:
    """The ink of the box's `2 * count` markings, turned ones as drawn, meets no other, and no OVERLAP is found (R2076 D1, D2)."""
    marks = [i for svg in result.page_svgs.values() for i in page_ink(svg) if i.text.startswith(("SIGNAL_CHANNEL_", "RET_"))]
    assert len(marks) == 2 * count
    for one, other in itertools.combinations(marks, 2):
        apart = one.box[2] <= other.box[0] or other.box[2] <= one.box[0] or one.box[3] <= other.box[1] or other.box[3] <= one.box[1]
        assert apart, f"{one.text} and {other.text} overlap"
    assert [f.code for f in result.findings if f.code == "OVERLAP"] == []
    (box,) = [s for d in drawn_pages(result.model).values() for s in d.symbols if s.key == "generic-box"]
    assert len([slot for slot, _ in box.slot_ink if slot.startswith("marking.")]) == 2 * count  # the OVERLAP check sees every marking


def test_no_two_pin_markings_of_the_box_overlap(tmp_path: Path) -> None:
    """The ink of the ten markings meets no other: neighbours on one side stand a measured marking apart."""
    _clear(_built(tmp_path, 5), 5)


def test_a_box_wider_than_the_row_when_widened_turns_its_markings_at_the_base_pitch(tmp_path: Path) -> None:
    """R2069: forty pins widened to their markings would pass the row, so the box keeps 2 M and reads them bottom-up; no error stands."""
    result = _built(tmp_path, 20)
    (box,) = [s for d in drawn_pages(result.model).values() for s in d.symbols if s.key == "generic-box"]
    assert box.turn
    xs = sorted({x for _, x in box.offsets})
    assert min(b - a for a, b in itertools.pairwise(xs)) == 16  # the base pitch, not the 88 G the markings would need
    assert [f.code for f in result.findings if f.severity is fr.Severity.ERROR] == []
    _clear(result, 20)
