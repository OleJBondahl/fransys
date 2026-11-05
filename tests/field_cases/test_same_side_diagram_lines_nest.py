"""Field case: a hub cabled to four boxes in a column, and in a ring twelve boards with a hub cabled to four of them and a second cable.
The bug: the farther target did not take the outer end and track, so the spans interleaved (one crossing in the column, two in the ring).
Fixed by layout-0201, same-column ends and tracks nest and take the tracks nearest the column."""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
import pytest
from _field_shared import crossings, diagram_lines

type Edges = tuple[tuple[str, str], ...]

_COLUMN: Edges = (("H", "A"), ("H", "B"), ("H", "C"), ("H", "D"), ("A", "B"), ("A", "C"))
_RING: Edges = (
    *((f"B{i:02d}", f"B{(i + 1) % 12:02d}") for i in range(12)),
    *(("H", f"B{i:02d}") for i in (0, 1, 2, 4)),
    ("B00", "B01"),
)


@cache
def _built(edges: Edges) -> fr.BuildResult:
    tags = sorted({t for edge in edges for t in edge})
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Nest\n", encoding="utf-8")
        d = fr.design("demo_parts")
        devices = {tag: d.device(tag, "DEMO-CONN-2P") for tag in tags}
        for n, (a, b) in enumerate(edges, start=1):
            d.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])
        return fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))


@pytest.mark.parametrize("edges", [_COLUMN, _RING], ids=["column", "ring"])
def test_same_side_lines_draw_with_no_crossing(edges: Edges) -> None:
    result = _built(edges)
    assert len(diagram_lines(result)) == len(edges)
    assert crossings(result) == 0
