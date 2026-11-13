"""Field case: a tree of seven connector devices joined by six cables draws on the block diagram with no crossings.
The bug: two lines left the hub's east side, and the lower-starting one's first run crossed the other's vertical run.
Fixed by no decision record named; the rule: no two lines of a cable tree cross at the system top."""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
from _field_shared import crossings, diagram_lines

_EDGES = (("P7", "P2"), ("P1", "P7"), ("P5", "P1"), ("P3", "P1"), ("P4", "P1"), ("P6", "P1"))
_TAGS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")


def _wire(d: Any, external: tuple[str, ...]) -> None:
    devices = {tag: d.device(tag, "DEMO-CONN-2P", external=tag in external) for tag in _TAGS}
    for n, (a, b) in enumerate(_EDGES, start=1):
        d.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])


@cache
def _built(external: tuple[str, ...] = ()) -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Tree\n", encoding="utf-8")
        d = fr.design("demo_parts")
        _wire(d, external)
        return fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))


def test_a_tree_of_cables_draws_with_no_crossing() -> None:
    result = _built()
    assert len(diagram_lines(result)) == len(_EDGES)
    assert crossings(result) == 0
